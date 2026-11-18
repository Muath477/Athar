import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import UUID

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from sadu.modules.admin import api as admin
from sadu.modules.agents import api as agents
from sadu.modules.agents.api import AgentRunner, Dependencies
from sadu.modules.capture import api as capture
from sadu.modules.capture.api import ObservationStatus
from sadu.modules.passport import api as passport
from sadu.modules.sites import api as sites
from sadu.modules.stories import api as stories
from sadu.modules.verification import api as verification
from sadu.shared.adapters.azure_speech import NoSpeech
from sadu.shared.errors import NotFound
from tests.fakes import FakeLLM
from tests.integration.conftest import PACK_DIR, RIYADH_PACK_DIR


def scripted_model(confidence: str = "high"):
    def respond(request):
        if request.agent == "orchestrator":
            return {"steps": ["identify", "monitor", "verify", "guide"]}
        if request.agent == "monitor":
            regions = json.loads(request.text.split("\n")[1])
            return {
                "overall_image_usable": True,
                "regions": [
                    {
                        "region_id": r["region_id"],
                        "change_present": True,
                        "damage_type": "crack",
                        "visible_in_baseline": False,
                        "lighting_or_shadow": False,
                        "severity": "moderate",
                        "confidence": confidence,
                        "likely_cause": "",
                        "rationale_ar": "شق جديد في الجدار.",
                    }
                    for r in regions
                ],
            }
        if request.agent == "guide":
            passages = json.loads(request.text.split("Passages:\n")[1].split("\nPrompt version")[0])
            return {"claims": [{"text": passages[0]["text"], "chunk_id": passages[0]["chunk_id"]}]}
        if request.agent == "verifier":
            return {
                "results": [{"claim_id": p["claim_id"], "supported": True} for p in json.loads(request.text)]
            }
        raise AssertionError(request.agent)

    return respond


@pytest.fixture
def runner_for(session, store):
    @asynccontextmanager
    async def unit_of_work():
        async with session.begin_nested():
            yield session

    def build(llm: FakeLLM) -> AgentRunner:
        deps = Dependencies(unit_of_work=unit_of_work, store=store, llm=llm, tts=NoSpeech())
        return AgentRunner(deps, InMemorySaver(), max_concurrent=1)

    return build


async def submit(session, store, photo: str, *, key: str, passport_id: UUID | None = None):
    meta = capture.CaptureMeta(
        captured_at=datetime(2026, 11, 16, tzinfo=UTC), lat=24.7136, lon=46.6753, passport_id=passport_id
    )
    raw = (PACK_DIR / "test-photos" / photo).read_bytes()
    observation, _ = await capture.create_observation(
        session, store, raw_photo=raw, meta=meta, idempotency_key=key
    )
    return observation.id


async def test_crack_photo_is_published_with_evidence_and_a_story(session, store, demo, runner_for):
    passport_id, _ = await passport.create(session)
    observation_id = await submit(session, store, "north-crack.jpg", key="run-1", passport_id=passport_id)
    runner = runner_for(FakeLLM(scripted_model()))

    runner.start(observation_id)
    await runner.wait()

    observation = await capture.get_observation(session, observation_id)
    assert observation.status is ObservationStatus.DONE, observation.status_payload
    assert observation.facade_id == demo.facades["north"].id
    assert not observation.has_location
    payload = observation.status_payload
    assert payload["findings"] and all(f["status"] == "published" for f in payload["findings"])
    assert payload["story_id"] is not None and payload["passport_stamped"]

    pins = await verification.published_for_facades(session, [demo.facades["north"].id])
    assert pins and all(p.baseline_key and p.diff_key and p.photo_key for p in pins)
    story = await stories.cached_story(session, demo.site.id, demo.facades["north"].id)
    assert story is not None and story.claims[0].label == "confirmed"


async def test_unknown_view_asks_the_visitor_then_asks_for_a_retake(session, store, demo, runner_for):
    observation_id = await submit(session, store, "not-a-facade.jpg", key="run-2")
    runner = runner_for(FakeLLM(scripted_model()))

    runner.start(observation_id)
    await runner.wait()
    waiting = await capture.get_observation(session, observation_id)
    assert waiting.status is ObservationStatus.NEEDS_INPUT
    assert len(waiting.status_payload["options"]) == 4

    await runner.answer(session, observation_id, demo.facades["north"].id)
    await runner.wait()
    done = await capture.get_observation(session, observation_id)
    assert done.status is ObservationStatus.NEEDS_RETAKE
    assert done.status_payload["retake_reason"] == "wrong_angle"
    assert done.status_payload["story_id"] is not None


async def test_medium_confidence_waits_for_an_expert(session, store, demo, runner_for):
    observation_id = await submit(session, store, "north-crack.jpg", key="run-3")
    runner = runner_for(FakeLLM(scripted_model(confidence="medium")))

    runner.start(observation_id)
    await runner.wait()
    queue = await verification.review_queue(session)
    assert queue and not await verification.published_for_facades(session, [demo.facades["north"].id])

    reviewer = await _expert(session)
    for finding in queue:
        await verification.apply_review(
            session,
            finding.id,
            reviewer_id=reviewer,
            decision=verification.ReviewDecision.CONFIRM,
            reason="ok",
        )
    await runner.review_finished(observation_id)
    await runner.wait()
    published = await verification.published_for_facades(session, [demo.facades["north"].id])
    assert {p.label for p in published} == {"confirmed"}


async def test_model_outage_sends_changes_to_review_not_to_the_map(session, store, demo, runner_for):
    observation_id = await submit(session, store, "north-crack.jpg", key="run-4")
    runner = runner_for(FakeLLM(None))

    runner.start(observation_id)
    await runner.wait()
    observation = await capture.get_observation(session, observation_id)
    assert observation.status is ObservationStatus.DONE
    assert observation.status_payload["story_id"] is None
    assert not await verification.published_for_facades(session, [demo.facades["north"].id])
    assert await verification.review_queue(session)


async def _expert(session) -> UUID:
    user = await admin.create_user(session, "expert@example.org", "a long test password", admin.Role.EXPERT)
    return user.id


async def test_a_second_visitor_confirms_but_the_same_visitor_does_not(session, store, demo, runner_for):
    runner = runner_for(FakeLLM(scripted_model()))
    first_visitor, _ = await passport.create(session)
    second_visitor, _ = await passport.create(session)
    north = demo.facades["north"].id

    for key, visitor in (("c-1", first_visitor), ("c-2", first_visitor)):
        runner.start(await submit(session, store, "north-crack.jpg", key=key, passport_id=visitor))
        await runner.wait()
    assert {
        (p.label, p.confirmations) for p in await verification.published_for_facades(session, [north])
    } == {("likely", 1)}

    runner.start(await submit(session, store, "north-crack.jpg", key="c-3", passport_id=second_visitor))
    await runner.wait()
    assert {
        (p.label, p.confirmations) for p in await verification.published_for_facades(session, [north])
    } == {("confirmed", 2)}


async def test_forgetting_a_visitor_removes_their_plain_photos(session, store, demo, runner_for):
    visitor, _ = await passport.create(session)
    observation_id = await submit(session, store, "north-shadow.jpg", key="f-1", passport_id=visitor)
    object_key = (await capture.get_observation(session, observation_id)).object_key

    await agents.forget_visitor(session, store, visitor)

    assert object_key not in store.objects
    with pytest.raises(NotFound):
        await capture.get_observation(session, observation_id)


async def test_site_without_facades_stamps_the_passport_without_the_model(session, store, runner_for):
    await sites.import_region_pack(session, store, RIYADH_PACK_DIR)
    turaif = await sites.get_site_by_slug(session, "at-turaif")
    passport_id, _ = await passport.create(session)
    meta = capture.CaptureMeta(
        captured_at=datetime(2026, 11, 18, tzinfo=UTC),
        lat=turaif.location.lat,
        lon=turaif.location.lon,
        passport_id=passport_id,
    )
    raw = (PACK_DIR / "test-photos" / "north-crack.jpg").read_bytes()
    observation, _ = await capture.create_observation(
        session, store, raw_photo=raw, meta=meta, idempotency_key="turaif-1"
    )
    model = FakeLLM(scripted_model())
    runner = runner_for(model)

    runner.start(observation.id)
    await runner.wait()

    done = await capture.get_observation(session, observation.id)
    assert done.status is ObservationStatus.DONE, done.status_payload
    assert done.site_id == turaif.id and done.facade_id is None
    assert not done.has_location
    assert done.status_payload["passport_stamped"] and done.status_payload["findings"] == []
    assert [r.agent for r in model.requests] == []
