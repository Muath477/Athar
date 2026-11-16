"""Public facade of the Agents module: start, resume and recover observation runs."""

import asyncio
import json
from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import structlog
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.types import Command
from sqlalchemy.ext.asyncio import AsyncSession

from sadu.modules.agents.application.graph import RunState, build_graph
from sadu.modules.agents.application.guide import Dependencies
from sadu.modules.agents.infrastructure.recording_llm import RecordingLLM, current_observation
from sadu.modules.capture import api as capture
from sadu.modules.capture.api import ObservationStatus
from sadu.modules.inspection import api as inspection
from sadu.modules.missions import api as missions
from sadu.modules.passport import api as passport
from sadu.modules.sites import api as sites
from sadu.modules.stories import api as stories
from sadu.shared.errors import Conflict
from sadu.shared.ports.embeddings import EmbeddingPort
from sadu.shared.storage import ObjectStore

__all__ = ["AgentRunner", "Dependencies", "RecordingLLM"]

log = structlog.get_logger()

STALE_RUN_AGE = timedelta(minutes=2)

type RunInput = RunState | Command[Any] | None


class AgentRunner:
    """Runs at most `max_concurrent` observations at once; the rest wait their turn."""

    def __init__(
        self, deps: Dependencies, checkpointer: BaseCheckpointSaver[Any], max_concurrent: int
    ) -> None:
        self._deps = deps
        self._graph = build_graph(deps).compile(checkpointer=checkpointer)
        self._slots = asyncio.Semaphore(max_concurrent)
        self._tasks: set[asyncio.Task[None]] = set()

    @property
    def deps(self) -> Dependencies:
        return self._deps

    def start(self, observation_id: UUID) -> None:
        """Run in the background; the visitor follows progress through the observation status."""
        self._spawn(observation_id, {"observation_id": str(observation_id)})

    async def answer(self, session: AsyncSession, observation_id: UUID, facade_id: UUID | None) -> None:
        observation = await capture.get_observation(session, observation_id)
        if observation.status is not ObservationStatus.NEEDS_INPUT:
            raise Conflict("observation_not_waiting")
        self._spawn(observation_id, Command(resume=str(facade_id) if facade_id else None))

    async def review_finished(self, observation_id: UUID) -> None:
        """Resume a run parked in await_review. A run that is not parked there is left alone."""
        state = await self._graph.aget_state(_config(observation_id))
        if "await_review" in state.next:
            self._spawn(observation_id, Command(resume="reviewed"))

    async def recover(self) -> None:
        """Startup sweep: resume runs a restart interrupted, so no photo is left processing."""
        async with self._deps.unit_of_work() as session:
            stale = await capture.unfinished_observation_ids(session, STALE_RUN_AGE)
        for observation_id in stale:
            state = await self._graph.aget_state(_config(observation_id))
            self._spawn(observation_id, None if state.next else {"observation_id": str(observation_id)})
        log.info("runs_recovered", count=len(stale))

    async def wait(self) -> None:
        """Wait for every background run; used by tests and on shutdown."""
        while self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)

    def _spawn(self, observation_id: UUID, graph_input: RunInput) -> None:
        task = asyncio.create_task(self._run(observation_id, graph_input))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _run(self, observation_id: UUID, graph_input: RunInput) -> None:
        token = current_observation.set(observation_id)
        try:
            async with self._slots:
                await self._graph.ainvoke(graph_input, _config(observation_id))
        except Exception:
            log.exception("run_failed", observation_id=str(observation_id))
            async with self._deps.unit_of_work() as session:
                await capture.set_status(
                    session, observation_id, ObservationStatus.FAILED, {"error": "internal_error"}
                )
        finally:
            current_observation.reset(token)


async def seed_region_pack(
    session: AsyncSession, store: ObjectStore, pack_dir: Path, embedder: EmbeddingPort | None = None
) -> list[str]:
    """Import a pack's sites, then each site's reviewed sources. Returns the site slugs."""
    slugs = await sites.import_region_pack(session, store, pack_dir)
    spec = json.loads((pack_dir / "pack.json").read_text(encoding="utf-8"))
    for site_spec in spec["sites"]:
        if not site_spec.get("sources_file"):
            continue
        site = await sites.get_site_by_slug(session, site_spec["slug"])
        facade_ids = {f.code: f.id for f in await sites.list_facades(session, site.id)}
        await stories.import_sources(
            session,
            site_id=site.id,
            facade_ids=facade_ids,
            sources_path=pack_dir / site_spec["sources_file"],
            embedder=embedder,
        )
    return slugs


async def dispatch_missions(session: AsyncSession) -> int:
    """Orchestrator's proactive pass: open missions for coverage gaps and unconfirmed findings."""
    opened = 0
    for site in await sites.list_sites(session):
        opened += len(await missions.plan_missions(session, site.id))
    return opened


async def forget_visitor(session: AsyncSession, store: ObjectStore, passport_id: UUID) -> None:
    """PDPL erasure across modules: the passport, its stamps, and its photos unless they are evidence."""
    photos = await capture.release_passport_photos(session, passport_id)
    keys = [*photos.values(), *await inspection.artifact_keys(session, list(photos))]
    await capture.delete_observations(session, list(photos))
    await passport.delete_passport(session, passport_id)
    for key in keys:
        await store.delete(key)


def _config(observation_id: UUID) -> RunnableConfig:
    return {"configurable": {"thread_id": str(observation_id)}}
