from collections.abc import Collection, Sequence
from dataclasses import dataclass

from sadu.modules.assistant.domain.arabic_text import normalize_ar
from sadu.modules.assistant.domain.conversation import AttachmentKind
from sadu.modules.assistant.domain.decision import ToolName

REQUIRED_FIELDS = ("name", "title", "when", "keywords", "tools")
REQUIRED_SECTIONS = ("## الخطوات", "## الفحوص", "## مخطط المخرجات")
FRONT_MATTER_FENCE = "---"
DEFAULT_SKILL = "wall-photo-inspection"
ATTACHMENT_MATCH_WEIGHT = 2


@dataclass(frozen=True)
class Skill:
    name: str
    title_ar: str
    when_ar: str
    keywords: tuple[str, ...]
    tools: tuple[ToolName, ...]
    attachments: frozenset[AttachmentKind]
    body: str

    def score(self, text: str, attachment_kinds: Collection[AttachmentKind]) -> int:
        normalized = normalize_ar(text)
        hits = sum(1 for keyword in self.keywords if normalize_ar(keyword) in normalized)
        if self.attachments & set(attachment_kinds):
            hits += ATTACHMENT_MATCH_WEIGHT
        return hits


def parse_skill(text: str) -> Skill:
    fields, body = _split_front_matter(text)
    missing = [name for name in REQUIRED_FIELDS if not fields.get(name)]
    if missing:
        raise ValueError(f"Skill front matter is missing {', '.join(missing)}")
    absent = [section for section in REQUIRED_SECTIONS if section not in body]
    if absent:
        raise ValueError(f"Skill {fields['name']} is missing sections {', '.join(absent)}")
    return Skill(
        name=fields["name"],
        title_ar=fields["title"],
        when_ar=fields["when"],
        keywords=_list(fields["keywords"]),
        tools=tuple(ToolName(tool) for tool in _list(fields["tools"])),
        attachments=frozenset(AttachmentKind(kind) for kind in _list(fields.get("attachments", ""))),
        body=body.strip(),
    )


def route_by_keywords(
    skills: Sequence[Skill], text: str, attachment_kinds: Collection[AttachmentKind]
) -> Skill:
    if not skills:
        raise ValueError("No skills to route to")
    scored = [(skill.score(text, attachment_kinds), skill) for skill in skills]
    best_score = max(score for score, _ in scored)
    best = [skill for score, skill in scored if score == best_score]
    return next((skill for skill in best if skill.name == DEFAULT_SKILL), best[0])


def _split_front_matter(text: str) -> tuple[dict[str, str], str]:
    lines = text.strip().splitlines()
    if not lines or lines[0].strip() != FRONT_MATTER_FENCE:
        raise ValueError("Skill file must start with a front matter block")
    try:
        end = next(i for i, line in enumerate(lines[1:], start=1) if line.strip() == FRONT_MATTER_FENCE)
    except StopIteration as error:
        raise ValueError("Skill front matter is not closed") from error
    fields = {}
    for line in lines[1:end]:
        key, separator, value = line.partition(":")
        if not separator:
            raise ValueError(f"Front matter line has no key: {line!r}")
        fields[key.strip()] = value.strip()
    return fields, "\n".join(lines[end + 1 :])


def _list(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.replace("،", ",").split(",") if item.strip())
