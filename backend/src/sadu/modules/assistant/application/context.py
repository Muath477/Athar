from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sadu.modules.assistant.domain.conversation import ActionKind, AttachmentKind, MessageRole
from sadu.modules.assistant.domain.decision import ToolName

ELEMENT_SOURCES = (ToolName.ANALYSE_PHOTO, ToolName.GET_MAP)


@dataclass(frozen=True)
class AttachmentRef:
    id: UUID
    kind: AttachmentKind
    file_name: str
    object_key: str
    width: int | None = None
    height: int | None = None


@dataclass(frozen=True)
class NewAttachment:
    id: UUID
    kind: AttachmentKind
    file_name: str
    media_type: str
    object_key: str
    size_bytes: int


@dataclass(frozen=True)
class NewAction:
    id: UUID
    kind: ActionKind
    payload: dict[str, Any]


@dataclass(frozen=True)
class ToolOutcome:
    tool: ToolName
    ok: bool
    summary_ar: str
    data: dict[str, Any] = field(default_factory=dict)
    attachment: NewAttachment | None = None
    action: NewAction | None = None


@dataclass(frozen=True)
class HistoryEntry:
    role: MessageRole
    text: str
    tool: ToolName | None = None
    ok: bool = True
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TurnContext:
    conversation_id: UUID
    user_id: UUID
    request_id: str | None
    message: str
    attachments: tuple[AttachmentRef, ...]
    latest_attachment_ids: tuple[UUID, ...]
    history: tuple[HistoryEntry, ...]
    can_save_maps: bool = False

    def attachment(self, attachment_id: UUID) -> AttachmentRef | None:
        return next((a for a in self.attachments if a.id == attachment_id), None)

    @property
    def latest_kinds(self) -> frozenset[AttachmentKind]:
        return frozenset(a.kind for a in self.attachments if a.id in self.latest_attachment_ids)

    def element_results(self, earlier: Iterable[ToolOutcome]) -> list[dict[str, Any]]:
        results: dict[str, dict[str, Any]] = {}
        past = [(entry.tool, entry.ok, entry.data) for entry in self.history]
        for tool, ok, data in [*past, *((o.tool, o.ok, o.data) for o in earlier)]:
            if tool in ELEMENT_SOURCES and ok and "elements" in data:
                key = str(data.get("map_id") or data.get("attachment_id"))
                results.pop(key, None)
                results[key] = data
        return list(results.values())

    def audit_reports(self, earlier: Iterable[ToolOutcome]) -> list[AttachmentRef]:
        stored = [a for a in self.attachments if a.kind is AttachmentKind.AUDIT_REPORT]
        drafted = [
            AttachmentRef(o.attachment.id, o.attachment.kind, o.attachment.file_name, o.attachment.object_key)
            for o in earlier
            if o.attachment is not None and o.attachment.kind is AttachmentKind.AUDIT_REPORT
        ]
        return [*stored, *drafted]
