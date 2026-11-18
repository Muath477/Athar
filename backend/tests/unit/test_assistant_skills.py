import pytest

from sadu.modules.assistant.domain.conversation import AttachmentKind
from sadu.modules.assistant.domain.decision import ToolName
from sadu.modules.assistant.domain.skills import parse_skill, route_by_keywords
from sadu.modules.assistant.infrastructure.skill_files import load_skills

SKILLS = load_skills()

VALID = """---
name: sample
title: مهارة تجريبية
when: للاختبار
keywords: تجربه, اختبار
attachments: photo
tools: list_sites, analyse_photo
---
## الخطوات
1. خطوة.
## الفحوص
- فحص.
## مخطط المخرجات
- رد.
"""


def test_every_shipped_skill_parses_with_steps_checks_and_output_schema():
    names = [skill.name for skill in SKILLS]
    assert names == [
        "audit-report",
        "drone-roof-and-wall-head",
        "satellite-alert-review",
        "treatment-check",
        "wall-photo-inspection",
    ]
    for skill in SKILLS:
        assert skill.title_ar and skill.when_ar and skill.keywords
        assert "## الخطوات" in skill.body and "## مخطط المخرجات" in skill.body
        assert ToolName.LIST_SITES in skill.tools


def test_only_report_skills_can_send_and_none_can_approve():
    senders = {skill.name for skill in SKILLS if ToolName.SEND_REPORT in skill.tools}
    assert senders == {
        "audit-report",
        "drone-roof-and-wall-head",
        "satellite-alert-review",
        "wall-photo-inspection",
    }
    assert not any("approve" in tool for skill in SKILLS for tool in skill.tools)


def test_wall_photo_skill_names_every_glossary_damage_type():
    body = next(s for s in SKILLS if s.name == "wall-photo-inspection").body
    for name in (
        "فقدان اللياسة",
        "التشققات",
        "تآكل القاعدة",
        "أخاديد الأمطار",
        "تزهّر الأملاح",
        "الفجوات والجحور",
    ):
        assert name in body


def test_parse_skill_reads_front_matter():
    skill = parse_skill(VALID)
    assert skill.name == "sample"
    assert skill.tools == (ToolName.LIST_SITES, ToolName.ANALYSE_PHOTO)
    assert skill.attachments == frozenset({AttachmentKind.PHOTO})
    assert skill.keywords == ("تجربه", "اختبار")


@pytest.mark.parametrize(
    ("text", "error"),
    [
        ("## الخطوات", "front matter"),
        (VALID.replace("---\n## الخطوات", "## الخطوات"), "not closed"),
        (VALID.replace("tools: list_sites, analyse_photo\n", ""), "tools"),
        (VALID.replace("## الفحوص", "## ملاحظات"), "## الفحوص"),
        (VALID.replace("analyse_photo", "approve_map"), "approve_map"),
    ],
)
def test_parse_skill_rejects_incomplete_files(text, error):
    with pytest.raises(ValueError, match=error):
        parse_skill(text)


@pytest.mark.parametrize(
    ("message", "kinds", "expected"),
    [
        ("حلّل هذه الصورة", [AttachmentKind.PHOTO], "wall-photo-inspection"),
        ("", [AttachmentKind.PHOTO], "wall-photo-inspection"),
        ("صورة درون لرؤوس الجدران والشرفات", [AttachmentKind.PHOTO], "drone-roof-and-wall-head"),
        ("ما آخر رصد فضائي لحي الطريف؟", [], "satellite-alert-review"),
        ("ما المعالجة المناسبة للتشقق المتوسط؟", [], "treatment-check"),
        ("اكتب ملف التدقيق وأرسله للمختص", [], "audit-report"),
        ("", [AttachmentKind.DOCUMENT], "audit-report"),
        ("مرحبًا", [], "wall-photo-inspection"),
    ],
)
def test_keyword_routing_picks_the_matching_skill(message, kinds, expected):
    assert route_by_keywords(SKILLS, message, kinds).name == expected


def test_routing_needs_skills():
    with pytest.raises(ValueError, match="No skills"):
        route_by_keywords([], "نص", [])
