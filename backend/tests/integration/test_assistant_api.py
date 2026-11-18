import json

import httpx
import pytest
from langgraph.checkpoint.memory import InMemorySaver
from sqlalchemy import select

from sadu.main import create_app
from sadu.modules.admin import api as admin
from sadu.modules.admin.infrastructure.orm import AuditLogRow
from sadu.modules.agents import api as agents
from sadu.modules.agents.api import AgentRunner, Dependencies
from sadu.modules.assistant import api as assistant
from sadu.modules.assistant.application.ports import ReportNotice
from sadu.shared.adapters.azure_speech import NoSpeech
from sadu.shared.config import get_settings
from sadu.shared.ports.llm import LLMPort
from sadu.shared.vocabulary import DamageType, Severity
from sadu.shared.web import AppState
from tests.fakes import FakeLLM
from tests.integration.conftest import PACK_DIR
from tests.integration.test_maps_api import LONG_TEST_PHRASE, PHOTO, ScriptedDetector, login

PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"


class RecordingChannel:
    def __init__(self) -> None:
        self.notices: list[ReportNotice] = []

    @property
    def name(self) -> str:
        return "recording"

    async def deliver(self, notice: ReportNotice) -> bool:
        self.notices.append(notice)
        return True


@pytest.fixture
def channel() -> RecordingChannel:
    return RecordingChannel()


@pytest.fixture
def detector() -> ScriptedDetector:
    scripted = ScriptedDetector()
    scripted.cells = [
        ("H1", DamageType.BASAL_EROSION, Severity.URGENT),
        ("B2", DamageType.CRACK, Severity.MODERATE),
        ("D5", DamageType.PLASTER_LOSS, Severity.WATCH),
    ]
    return scripted


def build_app(unit_of_work, store, detector, channel, llm: LLMPort):
    app = create_app()
    deps = Dependencies(unit_of_work=unit_of_work, store=store, llm=FakeLLM(), tts=NoSpeech())
    settings = get_settings()
    app.state.sadu = AppState(
        settings=settings,
        unit_of_work=unit_of_work,
        store=store,
        runner=AgentRunner(deps, InMemorySaver(), max_concurrent=1),
    )
    app.state.damage_detector = detector
    app.state.assistant = assistant.Assistant(
        assistant.Dependencies(
            unit_of_work=unit_of_work,
            store=store,
            llm=llm,
            detector=detector,
            channel=channel,
            catalog_path=settings.treatment_catalog_path,
            map_rows=settings.sadu_map_rows,
            public_origin="https://athar.example",
        ),
        assistant.load_skills(),
    )
    return app


@pytest.fixture
async def users(committed_unit_of_work, store):
    async with committed_unit_of_work() as session:
        await agents.seed_region_pack(session, store, PACK_DIR)
        for email, role in (
            ("inspector@example.org", admin.Role.INSPECTOR),
            ("authority@example.org", admin.Role.AUTHORITY),
            ("expert@example.org", admin.Role.EXPERT),
            ("ml@example.org", admin.Role.ML_ENGINEER),
        ):
            await admin.create_user(session, email, LONG_TEST_PHRASE, role)


async def client_for(app):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test/api/v1")


@pytest.fixture
async def client(committed_unit_of_work, store, detector, channel, users):
    llm = assistant.ScriptedPlanner(assistant.load_skills())
    async with await client_for(build_app(committed_unit_of_work, store, detector, channel, llm)) as http:
        yield http


@pytest.fixture
async def offline_client(committed_unit_of_work, store, detector, channel, users):
    llm = agents.RecordingLLM(assistant.ScriptedPlanner(assistant.load_skills()), daily_budget_usd=0.0)
    async with await client_for(build_app(committed_unit_of_work, store, detector, channel, llm)) as http:
        yield http


def read_events(body: str) -> list[tuple[str, dict]]:
    events = []
    for block in body.replace("\r\n", "\n").split("\n\n"):
        fields = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        if "event" in fields:
            events.append((fields["event"], json.loads(fields.get("data", "{}"))))
    return events


async def start_conversation(client: httpx.AsyncClient, headers: dict[str, str]) -> str:
    created = await client.post("/assistant/conversations", json={}, headers=headers)
    assert created.status_code == 201, created.text
    return created.json()["id"]


async def send(
    client: httpx.AsyncClient, headers: dict[str, str], conversation_id: str, text: str, files=()
) -> httpx.Response:
    return await client.post(
        f"/assistant/conversations/{conversation_id}/messages",
        headers=headers,
        data={"text": text},
        files=[("files", f) for f in files],
    )


async def reply(client: httpx.AsyncClient, headers: dict[str, str], conversation_id: str):
    response = await client.post(f"/assistant/conversations/{conversation_id}/reply", headers=headers)
    assert response.status_code == 200, response.text
    return read_events(response.text)


async def audit_actions(unit_of_work) -> list[str]:
    async with unit_of_work() as session:
        actions = await session.scalars(select(AuditLogRow.action).order_by(AuditLogRow.at))
        return [action for action in actions if action != "login"]


async def test_inspector_photo_becomes_draft_map_and_audit_file_sent_only_after_confirm(
    client, channel, committed_unit_of_work
):
    inspector = await login(client, "inspector@example.org")
    conversation_id = await start_conversation(client, inspector)
    posted = await send(
        client,
        inspector,
        conversation_id,
        "حلّل صورة الواجهة الشمالية واكتب ملف التدقيق وأرسله للمختصين",
        [("north.jpg", PHOTO, "image/jpeg")],
    )
    assert posted.status_code == 201, posted.text
    [photo] = posted.json()["attachments"]
    assert photo["kind"] == "photo" and photo["media_type"] == "image/jpeg"

    events = await reply(client, inspector, conversation_id)
    names = [name for name, _ in events]
    assert names[0] == "skill" and events[0][1]["name"] == "wall-photo-inspection"
    assert [data["tool"] for name, data in events if name == "tool_call"] == [
        "list_sites",
        "analyse_photo",
        "draft_audit_report",
        "send_report",
    ]
    assert names[-2:] == ["message", "done"]
    results = {data["message"]["tool"]: data["message"] for name, data in events if name == "tool_result"}

    analysis = results["analyse_photo"]["data"]
    assert analysis["ok"] and analysis["measured"] and len(analysis["elements"]) == 3
    map_view = await client.get(f"/maps/{analysis['map_id']}")
    assert map_view.json()["status"] == "draft"

    [report] = results["draft_audit_report"]["attachments"]
    pdf = await client.get(f"http://test{report['url']}")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")

    action = results["send_report"]["action"]
    assert action["status"] == "pending" and channel.notices == []
    final = events[-2][1]["message"]
    assert final["role"] == "agent" and final["skill_title"] == "فحص صورة جدار"

    confirmed = await client.post(f"/assistant/actions/{action['id']}/confirm", headers=inspector)
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["data"] == {
        "ok": True,
        "action_id": action["id"],
        "status": "confirmed",
        "delivered": True,
    }
    [notice] = channel.notices
    assert notice.link == f"https://athar.example/api/v1/assistant/attachments/{report['id']}"
    again = await client.post(f"/assistant/actions/{action['id']}/confirm", headers=inspector)
    assert again.status_code == 409 and again.json()["code"] == "action_already_decided"

    actions = await audit_actions(committed_unit_of_work)
    assert actions == ["map.create", "assistant.audit_report", "assistant.report_sent"]

    conversation = (await client.get(f"/assistant/conversations/{conversation_id}")).json()
    assert [m["role"] for m in conversation["messages"]] == ["user", *["tool"] * 4, "agent", "tool"]
    assert conversation["messages"][4]["action"]["status"] == "confirmed"

    expert = await login(client, "expert@example.org")
    assert (await client.get(f"http://test{report['url']}", headers=expert)).status_code == 200
    assert (await client.get(f"/assistant/attachments/{photo['id']}", headers=expert)).status_code == 404


async def test_authority_can_use_the_assistant_but_maps_are_not_saved_for_it(client, channel):
    authority = await login(client, "authority@example.org")
    conversation_id = await start_conversation(client, authority)
    await send(
        client, authority, conversation_id, "حلّل صورة الواجهة الشمالية", [("w.jpg", PHOTO, "image/jpeg")]
    )
    events = await reply(client, authority, conversation_id)
    analysis = next(
        d["message"]["data"]
        for n, d in events
        if n == "tool_result" and d["message"]["tool"] == "analyse_photo"
    )
    assert analysis["map_id"] is None and analysis["measured"] is True
    assert len(analysis["elements"]) == 3

    action_free = [d["tool"] for n, d in events if n == "tool_call"]
    assert "send_report" not in action_free and channel.notices == []

    others = await client.get("/assistant/conversations", headers=authority)
    assert [c["id"] for c in others.json()] == [conversation_id]


async def test_cancelled_send_is_audited_and_never_delivered(client, channel, committed_unit_of_work):
    inspector = await login(client, "inspector@example.org")
    conversation_id = await start_conversation(client, inspector)
    await send(client, inspector, conversation_id, "حلّل الصورة", [("w.jpg", PHOTO, "image/jpeg")])
    await reply(client, inspector, conversation_id)
    await send(client, inspector, conversation_id, "اكتب ملف التدقيق وأرسله")
    events = await reply(client, inspector, conversation_id)
    action = next(d["message"]["action"] for n, d in events if n == "tool_result" and d["message"]["action"])

    cancelled = await client.post(f"/assistant/actions/{action['id']}/cancel", headers=inspector)
    assert cancelled.status_code == 200 and cancelled.json()["data"]["status"] == "cancelled"
    assert channel.notices == []
    assert (await audit_actions(committed_unit_of_work))[-1] == "assistant.send_cancelled"

    expert = await login(client, "expert@example.org")
    stranger = await client.post(f"/assistant/actions/{action['id']}/confirm", headers=expert)
    assert stranger.status_code == 404


async def test_ml_engineer_cannot_use_the_assistant_and_conversations_stay_private(client):
    engineer = await login(client, "ml@example.org")
    assert (await client.post("/assistant/conversations", json={}, headers=engineer)).status_code == 403
    assert (await client.get("/assistant/conversations")).status_code == 403

    inspector = await login(client, "inspector@example.org")
    conversation_id = await start_conversation(client, inspector)
    authority = await login(client, "authority@example.org")
    assert (await client.get(f"/assistant/conversations/{conversation_id}")).status_code == 404
    assert (await send(client, authority, conversation_id, "مرحبا")).status_code == 404


async def test_uploads_accept_photos_and_pdfs_only(client):
    inspector = await login(client, "inspector@example.org")
    conversation_id = await start_conversation(client, inspector)
    document = await send(
        client, inspector, conversation_id, "", [("تقرير ١٤٤٠.pdf", PDF, "application/pdf")]
    )
    assert document.status_code == 201, document.text
    assert document.json()["attachments"][0]["kind"] == "document"
    assert document.json()["attachments"][0]["file_name"] == "تقرير ١٤٤٠.pdf"

    text_file = await send(client, inspector, conversation_id, "", [("notes.txt", b"hello", "text/plain")])
    assert text_file.status_code == 415
    empty = await send(client, inspector, conversation_id, "   ")
    assert empty.status_code == 422 and empty.json()["code"] == "empty_message"
    seven = [(f"{i}.pdf", PDF, "application/pdf") for i in range(7)]
    assert (await send(client, inspector, conversation_id, "", seven)).status_code == 422

    events = await reply(client, inspector, conversation_id)
    assert events[0] == ("skill", {"name": "audit-report", "title_ar": "صياغة ملف التدقيق"})
    nothing_new = await client.post(f"/assistant/conversations/{conversation_id}/reply", headers=inspector)
    assert nothing_new.status_code == 409 and nothing_new.json()["code"] == "nothing_to_answer"


async def test_when_the_budget_is_spent_the_reply_says_so_and_analysis_still_works(offline_client):
    client = offline_client
    inspector = await login(client, "inspector@example.org")
    conversation_id = await start_conversation(client, inspector)
    posted = await send(client, inspector, conversation_id, "حلّل الصورة", [("w.jpg", PHOTO, "image/jpeg")])
    photo_id = posted.json()["attachments"][0]["id"]

    events = await reply(client, inspector, conversation_id)
    assert [name for name, _ in events] == ["skill", "message", "done"]
    message = events[1][1]["message"]
    assert message["data"] == {"llm_available": False}
    assert "حلّل الصورة" in message["text"]

    [site] = (await client.get("/sites")).json()
    north = next(f["id"] for f in site["facades"] if f["code"] == "north")
    analysed = await client.post(
        f"/assistant/conversations/{conversation_id}/attachments/{photo_id}/analyse",
        json={"facade_id": north},
        headers=inspector,
    )
    assert analysed.status_code == 200, analysed.text
    body = analysed.json()
    assert body["tool"] == "analyse_photo" and body["data"]["ok"] and body["data"]["map_id"]


async def test_satellite_question_reads_the_watch_module_for_the_named_site(client):
    authority = await login(client, "authority@example.org")
    conversation_id = await start_conversation(client, authority)
    await send(client, authority, conversation_id, "ما آخر رصد فضائي لموقع بيت طيني تجريبي؟")
    events = await reply(client, authority, conversation_id)
    assert events[0][1]["name"] == "satellite-alert-review"
    assert [d["tool"] for n, d in events if n == "tool_call"] == ["list_sites", "get_watch_status"]
    status = next(
        d["message"]["data"]
        for n, d in events
        if n == "tool_result" and d["message"]["tool"] == "get_watch_status"
    )
    assert status == {
        "ok": True,
        "site_id": status["site_id"],
        "site_name": "بيت طيني تجريبي",
        "scanned": False,
    }
