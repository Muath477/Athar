import csv
import io
import json
from uuid import uuid4

import httpx
import pytest

from sadu.modules.admin.api import Role, UserView
from sadu.modules.mapping.domain.workflow import Actor, Detection, StepState, WorkflowFacts, workflow
from sadu.shared.adapters.webhook import WebhookNotifier
from sadu.shared.ports.notify import Notice
from sadu.shared.tabular import csv_bytes

FACTS = WorkflowFacts(
    elements=0,
    low_confidence=0,
    treatments_matched=0,
    treatments_unmatched=0,
    material_lines=0,
    corrections=0,
    field_inspected=False,
    approved=False,
)


def facts(**changes: object) -> WorkflowFacts:
    return WorkflowFacts(**{**FACTS.__dict__, **changes})


def test_a_model_run_keeps_the_agent_steps_done():
    steps = workflow(facts(elements=2))
    assert FACTS.detection is Detection.MODEL and FACTS.model_ran
    assert [s.state for s in steps[:3]] == [StepState.DONE] * 3
    assert steps[0].output_ar == "صورة مقبولة" and steps[2].actor is Actor.AGENT


def test_a_failed_model_asks_the_specialist_to_draw_by_hand():
    steps = workflow(facts(detection=Detection.FAILED))
    detect = steps[2]
    assert detect.state is StepState.FLAGGED and detect.actor is Actor.SPECIALIST
    assert detect.output_ar == "تعذّر التحليل الآلي، ارسم العناصر يدويًا"
    assert "دون فحص آلي" in steps[0].output_ar


def test_hand_drawn_elements_complete_the_detection_step():
    drawn = workflow(facts(detection=Detection.FAILED, elements=3))[2]
    assert drawn.state is StepState.DONE
    assert drawn.output_ar == "تعذّر التحليل الآلي، عناصر رسمها المختص: ٣"


def test_manual_mode_waits_for_the_specialist():
    detect = workflow(facts(detection=Detection.MANUAL))[2]
    assert detect.state is StepState.WAITING and detect.output_ar == "تحديد يدوي"
    assert workflow(facts(detection=Detection.MANUAL, elements=1))[2].state is StepState.DONE


@pytest.mark.parametrize(
    ("role", "scoped", "sees_other_site"),
    [
        (Role.INSPECTOR, False, True),
        (Role.INSPECTOR, True, False),
        (Role.EXPERT, True, False),
        (Role.AUTHORITY, True, True),
        (Role.ADMIN, True, True),
    ],
)
def test_site_scope_rule(role: Role, scoped: bool, sees_other_site: bool):
    assigned, other = uuid4(), uuid4()
    user = UserView(uuid4(), "u@example.org", role, site_ids=frozenset({assigned}) if scoped else frozenset())
    assert user.sees_site(assigned)
    assert user.sees_site(other) is sees_other_site
    assert user.sees_site(None)


def test_csv_starts_with_a_bom_and_neutralises_formulas():
    content = csv_bytes(("الجدار", "العدد"), [("=HYPERLINK(1)", 3), ("سور", None), ("-2", -2)])
    assert content.startswith(b"\xef\xbb\xbf")
    rows = list(csv.reader(io.StringIO(content.decode("utf-8-sig"))))
    assert rows == [["الجدار", "العدد"], ["'=HYPERLINK(1)", "3"], ["سور", ""], ["'-2", "-2"]]


@pytest.mark.anyio
async def test_governance_notice_posts_text_link_and_fields():
    sent: list[dict] = []

    def handle(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content))
        return httpx.Response(204)

    notifier = WebhookNotifier("https://hooks.test/athar", transport=httpx.MockTransport(handle))
    await notifier.send(Notice("notice.map_urgent", "تلف عاجل", "https://athar.test/m", {"urgent": 2}))
    assert sent == [
        {
            "kind": "notice.map_urgent",
            "text": "تلف عاجل · https://athar.test/m",
            "link": "https://athar.test/m",
            "urgent": 2,
        }
    ]

    failing = WebhookNotifier(
        "https://hooks.test/athar", transport=httpx.MockTransport(lambda r: httpx.Response(500))
    )
    await failing.send(Notice("notice.approval_overdue", "x", "https://athar.test/m"))
