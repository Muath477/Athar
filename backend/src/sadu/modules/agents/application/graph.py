"""The observation run as a LangGraph state graph (docs/03-architecture.md §8).

plan -> identify -> [ask_visitor] -> [monitor -> verify] -> guide -> [await_review]

Each node opens its own transaction, so the visitor sees status changes as they happen and a
crash loses at most one step; the checkpointer resumes the run from the last finished node.
"""

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import asdict, dataclass
from typing import Any, TypedDict
from uuid import UUID

import structlog
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from sqlalchemy.ext.asyncio import AsyncSession

from sadu.modules.agents.application.evidence import evidence_keys, judged_regions, unjudged_regions
from sadu.modules.agents.application.orchestrator import plan_steps
from sadu.modules.agents.domain.identification import FacadeCandidate, identify_facade
from sadu.modules.agents.domain.planning import ObservationContext, Step
from sadu.modules.capture import api as capture
from sadu.modules.capture.api import ObservationStatus
from sadu.modules.inspection import api as inspection
from sadu.modules.missions import api as missions
from sadu.modules.passport import api as passport
from sadu.modules.sites import api as sites
from sadu.modules.sites.domain.geometry import heading_score
from sadu.modules.stories import api as stories
from sadu.modules.verification import api as verification
from sadu.modules.verification.domain.labels import Action
from sadu.shared.ports.embeddings import EmbeddingPort
from sadu.shared.ports.llm import LLMPort, LLMRefused, LLMUnavailable
from sadu.shared.ports.speech import SpeechUnavailable, TextToSpeechPort
from sadu.shared.storage import ObjectStore
from sadu.shared.vocabulary import DamageType, ModelConfidence, Severity

log = structlog.get_logger()

type UnitOfWork = Callable[[], AbstractAsyncContextManager[AsyncSession]]


@dataclass(frozen=True)
class Dependencies:
    unit_of_work: UnitOfWork
    store: ObjectStore
    llm: LLMPort
    tts: TextToSpeechPort
    embedder: EmbeddingPort | None = None
    voice: str = stories.DEFAULT_VOICE


class RunState(TypedDict, total=False):
    observation_id: str
    plan: list[str]
    site_id: str | None
    facade_id: str | None
    question_options: list[str]
    retake_reason: str | None
    inspection: dict[str, Any] | None
    findings: list[dict[str, Any]]
    pending_review: list[str]
    story_id: str | None


def build_graph(deps: Dependencies) -> StateGraph[RunState]:
    nodes = _Nodes(deps)
    graph = StateGraph(RunState)
    graph.add_node("plan", nodes.plan)
    graph.add_node("identify", nodes.identify)
    graph.add_node("ask_visitor", nodes.ask_visitor)
    graph.add_node("monitor", nodes.monitor)
    graph.add_node("verify", nodes.verify)
    graph.add_node("guide", nodes.guide)
    graph.add_node("await_review", nodes.await_review)

    graph.add_edge(START, "plan")
    graph.add_conditional_edges("plan", _after_plan, ["identify", "guide", END])
    graph.add_conditional_edges("identify", _after_identify, ["ask_visitor", "monitor", "guide"])
    graph.add_conditional_edges("ask_visitor", _after_facade_known, ["monitor", "guide"])
    graph.add_conditional_edges("monitor", _after_monitor, ["verify", "guide"])
    graph.add_edge("verify", "guide")
    graph.add_conditional_edges("guide", _after_guide, ["await_review", END])
    graph.add_edge("await_review", END)
    return graph


def _after_plan(state: RunState) -> str:
    if state.get("site_id") is None:
        return END
    return "identify" if Step.IDENTIFY in state["plan"] else "guide"


def _after_identify(state: RunState) -> str:
    if state.get("facade_id") is None and state.get("question_options"):
        return "ask_visitor"
    return _after_facade_known(state)


def _after_facade_known(state: RunState) -> str:
    return "monitor" if Step.MONITOR in state["plan"] and state.get("facade_id") else "guide"


def _after_monitor(state: RunState) -> str:
    return "verify" if state.get("inspection") else "guide"


def _after_guide(state: RunState) -> str:
    return "await_review" if state.get("pending_review") else END


class _Nodes:
    def __init__(self, deps: Dependencies) -> None:
        self.deps = deps

    async def plan(self, state: RunState) -> RunState:
        observation_id = UUID(state["observation_id"])
        async with self.deps.unit_of_work() as session:
            await capture.set_status(
                session, observation_id, ObservationStatus.PROCESSING, {"stage": "planning"}
            )
            observation = await capture.get_observation(session, observation_id)
            mission = (
                await missions.get_mission(session, observation.mission_id)
                if observation.mission_id
                else None
            )
            site_id = mission.site_id if mission else observation.site_id
            if site_id is None and observation.lat is not None and observation.lon is not None:
                nearby = await sites.find_sites_near(session, observation.lat, observation.lon)
                site_id = nearby[0].id if nearby else None
            if site_id is None:
                await capture.attach_location_result(session, observation_id, site_id=None, facade_id=None)
                await capture.set_status(
                    session, observation_id, ObservationStatus.DONE, {"site_found": False}
                )
                return {"site_id": None, "plan": []}
            facade_count = len(await sites.list_facades(session, site_id))

        context = ObservationContext(
            has_location=observation.has_location, has_site=True, on_mission=mission is not None
        )
        steps = await plan_steps(
            self.deps.llm, context, has_heading=observation.heading_deg is not None, facade_count=facade_count
        )
        return {
            "site_id": str(site_id),
            "plan": [s.value for s in steps],
            "facade_id": str(mission.facade_id) if mission else None,
        }

    async def identify(self, state: RunState) -> RunState:
        if state.get("facade_id"):
            await self._attach_location(state)
            return {}
        observation_id, site_id = UUID(state["observation_id"]), UUID(state["site_id"] or "")
        async with self.deps.unit_of_work() as session:
            await capture.set_status(
                session, observation_id, ObservationStatus.PROCESSING, {"stage": "identifying"}
            )
            observation = await capture.get_observation(session, observation_id)
            facades = await sites.list_facades(session, site_id)
            baselines = [await sites.primary_baseline(session, f.id) for f in facades]

        photo = await self.deps.store.get(observation.object_key)
        baseline_images = [await self.deps.store.get(b.object_key) for b in baselines]
        inliers = await inspection.match_inliers(photo, baseline_images)
        candidates = [
            FacadeCandidate(
                facade.id,
                count,
                heading_score(observation.heading_deg, facade.outward_azimuth_deg)
                if observation.heading_deg is not None
                else None,
            )
            for facade, count in zip(facades, inliers, strict=True)
        ]
        result = identify_facade(candidates, observation.heading_accuracy_deg)
        log.info("facade_identified", observation_id=str(observation_id), method=result.method)
        if result.facade_id is None:
            return {"facade_id": None, "question_options": [str(o) for o in result.options]}
        state_update: RunState = {"facade_id": str(result.facade_id)}
        await self._attach_location({**state, **state_update})
        return state_update

    async def ask_visitor(self, state: RunState) -> RunState:
        observation_id = UUID(state["observation_id"])
        options = state["question_options"]
        async with self.deps.unit_of_work() as session:
            choices = [await sites.get_facade(session, UUID(o)) for o in options]
            await capture.set_status(
                session,
                observation_id,
                ObservationStatus.NEEDS_INPUT,
                {
                    "question_id": "which_facade",
                    "options": [
                        {"facade_id": str(f.id), "name_ar": f.name_ar, "name_en": f.name_en} for f in choices
                    ],
                },
            )
        answer = interrupt({"question_id": "which_facade", "options": options})
        facade_id = answer if answer in options else None
        async with self.deps.unit_of_work() as session:
            await capture.set_status(
                session, observation_id, ObservationStatus.PROCESSING, {"stage": "answered"}
            )
        await self._attach_location({**state, "facade_id": facade_id})
        return {"facade_id": facade_id}

    async def monitor(self, state: RunState) -> RunState:
        observation_id, facade_id = UUID(state["observation_id"]), UUID(state["facade_id"] or "")
        async with self.deps.unit_of_work() as session:
            await capture.set_status(
                session, observation_id, ObservationStatus.PROCESSING, {"stage": "monitoring"}
            )
            observation = await capture.get_observation(session, observation_id)
            facade = await sites.get_facade(session, facade_id)
            baseline = await sites.primary_baseline(session, facade_id)
        photo = await self.deps.store.get(observation.object_key)

        async with self.deps.unit_of_work() as session:
            outcome = await inspection.inspect(
                session,
                self.deps.store,
                self.deps.llm,
                observation_id=observation_id,
                photo_jpeg=photo,
                baseline_id=baseline.id,
                baseline_key=baseline.object_key,
            )
        if not outcome.comparable:
            reason = outcome.retake_reason
            return {"inspection": None, "retake_reason": reason.value if reason else None}

        keys = evidence_keys(outcome, observation.object_key)
        judged = judged_regions(outcome, baseline, facade) if not outcome.judge_failed else []
        unjudged = unjudged_regions(outcome, baseline, facade) if outcome.judge_failed else []
        return {
            "inspection": {
                "run_id": str(outcome.run_id),
                "keys": asdict(keys) if keys else None,
                "judged": [asdict(r) for r in judged],
                "unjudged": [list(r) for r in unjudged],
                "mission_id": str(observation.mission_id) if observation.mission_id else None,
                "contributor": str(observation.passport_id)
                if observation.passport_id
                else observation.content_sha256,
            },
            "retake_reason": None,
        }

    async def verify(self, state: RunState) -> RunState:
        observation_id, facade_id = UUID(state["observation_id"]), UUID(state["facade_id"] or "")
        run = state["inspection"] or {}
        keys = verification.EvidenceKeys(**run["keys"]) if run.get("keys") else None
        findings: list[dict[str, Any]] = []
        pending: list[str] = []
        retake_reason = None
        async with self.deps.unit_of_work() as session:
            await capture.set_status(
                session, observation_id, ObservationStatus.PROCESSING, {"stage": "verifying"}
            )
            if keys and run["judged"]:
                verdicts = await verification.record_regions(
                    session,
                    facade_id=facade_id,
                    observation_id=observation_id,
                    inspection_run_id=UUID(run["run_id"]),
                    contributor=run["contributor"],
                    evidence=keys,
                    regions=[_region_from_json(r) for r in run["judged"]],
                )
                for verdict in verdicts:
                    if verdict.verdict.action is Action.RETAKE and verdict.verdict.retake_reason:
                        retake_reason = verdict.verdict.retake_reason.value
                    if verdict.finding_id is None:
                        continue
                    finding = await verification.get_finding(session, verdict.finding_id)
                    findings.append(_finding_summary(finding))
                    if finding.status is verification.FindingStatus.PENDING_REVIEW:
                        pending.append(str(finding.id))
            elif keys and run["unjudged"]:
                ids = await verification.record_unjudged_regions(
                    session,
                    facade_id=facade_id,
                    observation_id=observation_id,
                    inspection_run_id=UUID(run["run_id"]),
                    evidence=keys,
                    regions=[(r[0], tuple(r[1]), tuple(r[2])) for r in run["unjudged"]],
                )
                pending.extend(str(i) for i in ids)
                for finding_id in ids:
                    findings.append(_finding_summary(await verification.get_finding(session, finding_id)))
            if findings:
                await capture.keep_as_evidence(session, observation_id)
            if run.get("mission_id"):
                await missions.fulfill(session, UUID(run["mission_id"]), observation_id)
        return {"findings": findings, "pending_review": pending, "retake_reason": retake_reason}

    async def guide(self, state: RunState) -> RunState:
        observation_id, site_id = UUID(state["observation_id"]), UUID(state["site_id"] or "")
        facade_id = UUID(state["facade_id"]) if state.get("facade_id") else None
        async with self.deps.unit_of_work() as session:
            await capture.set_status(
                session, observation_id, ObservationStatus.PROCESSING, {"stage": "guiding"}
            )
        story = await self._story(site_id, facade_id)

        async with self.deps.unit_of_work() as session:
            observation = await capture.get_observation(session, observation_id)
            stamped = False
            if observation.passport_id:
                stamped = await passport.record_entry(
                    session, observation.passport_id, site_id, observation_id
                )
            retake = state.get("retake_reason")
            await capture.set_status(
                session,
                observation_id,
                ObservationStatus.NEEDS_RETAKE if retake else ObservationStatus.DONE,
                {
                    "site_id": str(site_id),
                    "facade_id": str(facade_id) if facade_id else None,
                    "story_id": str(story.id) if story else None,
                    "retake_reason": retake,
                    "findings": state.get("findings", []),
                    "passport_stamped": stamped,
                },
            )
        return {"story_id": str(story.id) if story else None}

    async def await_review(self, state: RunState) -> RunState:
        """Park the run until an expert has decided every finding it sent for review."""
        interrupt({"finding_ids": state["pending_review"]})
        return {"pending_review": []}

    async def _story(self, site_id: UUID, facade_id: UUID | None) -> stories.StoryView | None:
        async with self.deps.unit_of_work() as session:
            story = await stories.cached_story(session, site_id, facade_id)
            if story is None:
                story = await self._new_story(session, site_id, facade_id)
            if story is not None and story.audio_key is None:
                try:
                    await stories.add_audio(
                        session, self.deps.store, self.deps.tts, story.id, self.deps.voice
                    )
                except SpeechUnavailable as error:
                    log.info("story_audio_skipped", reason=str(error))
        return story

    async def _new_story(
        self, session: AsyncSession, site_id: UUID, facade_id: UUID | None
    ) -> stories.StoryView | None:
        site = await sites.get_site(session, site_id)
        place = site.name_ar
        if facade_id:
            place = f"{place}، {(await sites.get_facade(session, facade_id)).name_ar}"
        query = await stories.embed_query(self.deps.embedder, place)
        chunks = await stories.retrieve_chunks(session, site_id, facade_id, query_embedding=query)
        if not chunks:
            return None
        try:
            drafts = await stories.draft_claims(
                self.deps.llm, place_name=place, passages=[(c.chunk_id, c.text) for c in chunks]
            )
        except (LLMUnavailable, LLMRefused) as error:
            log.warning("story_draft_failed", error=str(error))
            return None
        verdicts = await verification.check_claims(
            self.deps.llm,
            [verification.Claim(d.claim_id, d.text, d.chunk_id) for d in drafts],
            [
                verification.Chunk(c.chunk_id, c.source_id, verification.SourceKind(c.source_kind), c.text)
                for c in chunks
            ],
        )
        kept = [
            (d, v.label.value, v.source_id) for d, v in zip(drafts, verdicts, strict=True) if v.publishable
        ]
        if not kept:
            return None
        return await stories.save_story(session, site_id=site_id, facade_id=facade_id, lang="ar", claims=kept)

    async def _attach_location(self, state: RunState) -> None:
        facade_id = state.get("facade_id")
        async with self.deps.unit_of_work() as session:
            await capture.attach_location_result(
                session,
                UUID(state["observation_id"]),
                site_id=UUID(state["site_id"] or ""),
                facade_id=UUID(facade_id) if facade_id else None,
            )


def _region_from_json(data: dict[str, Any]) -> verification.RegionEvidence:
    """Checkpoints store plain JSON; restore tuples and enums, which the label rule compares by identity."""
    return verification.RegionEvidence(
        **{
            **data,
            "region_uv": tuple(data["region_uv"]),
            "pin_xyz": tuple(data["pin_xyz"]),
            "damage_type": DamageType(data["damage_type"]),
            "model_confidence": ModelConfidence(data["model_confidence"]),
            "model_severity": Severity(data["model_severity"]),
        }
    )


def _finding_summary(finding: verification.FindingView) -> dict[str, Any]:
    return {
        "id": str(finding.id),
        "damage_type": finding.damage_type.value,
        "severity": finding.severity.value,
        "label": finding.label.value,
        "status": finding.status.value,
    }
