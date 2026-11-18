import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path

import sentry_sdk
import structlog
from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from sqlalchemy import text

import sadu.shared.orm_registry
from sadu.modules.admin.interface.routes import router as admin_router
from sadu.modules.agents import api as agents
from sadu.modules.agents.interface.routes import router as agents_router
from sadu.modules.ingest import api as ingest
from sadu.modules.ingest.interface.routes import router as ingest_router
from sadu.modules.mapping import api as mapping
from sadu.modules.mapping.interface.routes import router as maps_router
from sadu.modules.missions.interface.routes import router as missions_router
from sadu.modules.passport.interface.routes import router as passport_router
from sadu.modules.reports.interface.routes import router as reports_router
from sadu.modules.sites.interface.routes import router as sites_router
from sadu.modules.treatments.interface.routes import router as treatments_router
from sadu.modules.verification.interface.routes import router as findings_router
from sadu.modules.watch import api as watch
from sadu.modules.watch.interface.routes import router as watch_router
from sadu.shared.adapters.anthropic_llm import AnthropicLLM
from sadu.shared.adapters.azure_speech import AzureSpeech, NoSpeech
from sadu.shared.adapters.cached_llm import CachedLLM
from sadu.shared.config import SceneSourceKind, Settings, get_settings
from sadu.shared.db import get_engine, plain_postgres_url, unit_of_work
from sadu.shared.errors import install_error_handlers
from sadu.shared.logging import configure_logging, request_id_middleware
from sadu.shared.ports.llm import LLMPort
from sadu.shared.ports.speech import TextToSpeechPort
from sadu.shared.storage import get_object_store
from sadu.shared.web import API_PREFIX, AppState, Session, public, security_headers_middleware

log = structlog.get_logger()

MISSION_DISPATCH_INTERVAL_S = 15 * 60
WATCH_POLL_INTERVAL_S = 60 * 60
CAMERA_POLL_INTERVAL_S = 15 * 60
INGEST_POLL_INTERVAL_S = 30


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(
        title="Athar API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None if settings.is_prod else "/api/docs",
        redoc_url=None,
        openapi_url=None if settings.is_prod else "/api/openapi.json",
    )
    app.middleware("http")(security_headers_middleware)
    app.middleware("http")(request_id_middleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.sadu_public_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type", "Idempotency-Key", "X-Passport-Token", "X-CSRF-Token", "X-Request-ID"],
    )
    install_error_handlers(app)
    for router in (
        agents_router,
        sites_router,
        findings_router,
        maps_router,
        reports_router,
        watch_router,
        treatments_router,
        missions_router,
        passport_router,
        ingest_router,
        admin_router,
        health_router,
    ):
        app.include_router(router, prefix=API_PREFIX)
    return app


health_router = APIRouter(tags=["health"])


@health_router.get("/healthz", dependencies=[Depends(public)])
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@health_router.get("/readyz", dependencies=[Depends(public)])
async def readyz(session: Session) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    return {"status": "ready"}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(json_output=settings.is_prod)
    if settings.sentry_dsn_api:
        sentry_sdk.init(dsn=settings.sentry_dsn_api, send_default_pii=False, traces_sample_rate=0.1)

    store = get_object_store()
    await store.ensure_bucket()
    llm = build_llm(settings)
    app.state.damage_detector = mapping.build_detector(settings, llm)
    app.state.scan_queue = watch.ScanQueue(
        unit_of_work,
        store,
        watch.build_scene_source(settings),
        notifier=watch.build_notifier(settings),
        public_origin=settings.sadu_public_origin,
    )
    app.state.ingestion = ingest.Ingestion(
        unit_of_work,
        store,
        app.state.damage_detector,
        ingest.build_camera_client(settings),
        map_rows=settings.sadu_map_rows,
        concurrency=settings.sadu_ingest_concurrency,
    )
    deps = agents.Dependencies(
        unit_of_work=unit_of_work,
        store=store,
        llm=llm,
        tts=build_tts(settings),
        voice=settings.sadu_tts_voice,
    )
    async with AsyncPostgresSaver.from_conn_string(plain_postgres_url()) as checkpointer:
        await checkpointer.setup()
        runner = agents.AgentRunner(deps, checkpointer, settings.sadu_max_concurrent_runs)
        app.state.sadu = AppState(settings=settings, unit_of_work=unit_of_work, store=store, runner=runner)
        await runner.recover()
        await app.state.ingestion.recover()
        dispatcher = asyncio.create_task(dispatch_missions_forever())
        watcher = asyncio.create_task(scan_sites_forever(settings, app.state.scan_queue))
        ingester = asyncio.create_task(process_ingest_jobs_forever(app.state.ingestion))
        camera_poller = asyncio.create_task(capture_cameras_forever(settings, app.state.ingestion))
        log.info(
            "api_started",
            env=settings.sadu_env,
            demo_mode=settings.sadu_demo_mode,
            damage_detector=app.state.damage_detector.name,
            scene_source=app.state.scan_queue.source.name,
        )
        try:
            yield
        finally:
            for task in (dispatcher, watcher, ingester, camera_poller):
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
            await runner.wait()
    await get_engine().dispose()


def build_llm(settings: Settings) -> LLMPort:
    llm: LLMPort = agents.RecordingLLM(AnthropicLLM(settings), settings.sadu_daily_llm_budget_usd)
    return CachedLLM(llm, Path(settings.sadu_demo_cache_dir), prefer_cache=settings.sadu_demo_mode)


def build_tts(settings: Settings) -> TextToSpeechPort:
    if settings.azure_speech_key and settings.azure_speech_region:
        return AzureSpeech(settings.azure_speech_key.get_secret_value(), settings.azure_speech_region)
    return NoSpeech()


async def dispatch_missions_forever() -> None:
    while True:
        try:
            async with unit_of_work() as session:
                opened = await agents.dispatch_missions(session)
            log.info("missions_dispatched", opened=opened)
        except Exception:
            log.exception("mission_dispatch_failed")
        await asyncio.sleep(MISSION_DISPATCH_INTERVAL_S)


async def scan_sites_forever(settings: Settings, queue: watch.ScanQueue) -> None:
    if settings.sadu_watch_interval_h == 0 or settings.sadu_scene_source is SceneSourceKind.NONE:
        return
    interval = timedelta(hours=settings.sadu_watch_interval_h)
    while True:
        try:
            async with unit_of_work() as session:
                due = await watch.due_sites(session, interval)
            for site_id in due:
                queue.start(site_id)
            await queue.join()
        except Exception:
            log.exception("site_scan_round_failed")
        await asyncio.sleep(WATCH_POLL_INTERVAL_S)


async def process_ingest_jobs_forever(ingestion: ingest.Ingestion) -> None:
    while True:
        try:
            ingestion.kick()
            await ingestion.join()
        except Exception:
            log.exception("ingest_round_failed")
        await asyncio.sleep(INGEST_POLL_INTERVAL_S)


async def capture_cameras_forever(settings: Settings, ingestion: ingest.Ingestion) -> None:
    if settings.sadu_camera_interval_h == 0:
        return
    interval = timedelta(hours=settings.sadu_camera_interval_h)
    while True:
        try:
            captured = await ingestion.capture_due(interval)
            log.info("cameras_captured", devices=captured)
        except Exception:
            log.exception("camera_round_failed")
        await asyncio.sleep(CAMERA_POLL_INTERVAL_S)


app = create_app()
