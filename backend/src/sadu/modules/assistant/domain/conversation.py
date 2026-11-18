import re
from enum import StrEnum

MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
MAX_ATTACHMENTS_PER_MESSAGE = 6
MAX_FILE_NAME_CHARS = 120
PDF_SIGNATURE = b"%PDF-"
TITLE_CHARS = 60
UNSAFE_NAME_CHARS = re.compile(r"[\x00-\x1f\x7f/\\]")


class MessageRole(StrEnum):
    USER = "user"
    AGENT = "agent"
    TOOL = "tool"


class AttachmentKind(StrEnum):
    PHOTO = "photo"
    DOCUMENT = "document"
    AUDIT_REPORT = "audit_report"


class ActionKind(StrEnum):
    SEND_REPORT = "send_report"


class ActionStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class ActionAlreadySettled(ValueError):
    pass


def is_pdf(head: bytes) -> bool:
    return head.startswith(PDF_SIGNATURE)


def settle(status: ActionStatus, *, confirm: bool) -> ActionStatus:
    if status is not ActionStatus.PENDING:
        raise ActionAlreadySettled(f"Action is already {status}")
    return ActionStatus.CONFIRMED if confirm else ActionStatus.CANCELLED


def safe_file_name(name: str | None, fallback: str) -> str:
    cleaned = UNSAFE_NAME_CHARS.sub("", (name or "").rsplit("/", 1)[-1].rsplit("\\", 1)[-1]).strip()
    return cleaned[:MAX_FILE_NAME_CHARS] or fallback


def title_from(text: str, fallback: str) -> str:
    words = " ".join(text.split())
    if not words:
        return fallback
    return words if len(words) <= TITLE_CHARS else words[: TITLE_CHARS - 1].rstrip() + "…"
