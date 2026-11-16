from dataclasses import dataclass
from enum import StrEnum


class SourceKind(StrEnum):
    OFFICIAL = "official"
    ORAL_REVIEWED = "oral_reviewed"


class ClaimLabel(StrEnum):
    CONFIRMED = "confirmed"
    ORAL_ACCOUNT = "oral_account"
    INTERPRETATION = "interpretation"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    source_id: str
    source_kind: SourceKind
    text: str


@dataclass(frozen=True)
class Claim:
    claim_id: str
    text: str
    chunk_id: str | None


@dataclass(frozen=True)
class ClaimVerdict:
    claim_id: str
    supported: bool
    label: ClaimLabel
    source_id: str | None = None

    @property
    def publishable(self) -> bool:
        return self.supported and self.label is not ClaimLabel.UNKNOWN


def label_for(kind: SourceKind) -> ClaimLabel:
    return ClaimLabel.CONFIRMED if kind is SourceKind.OFFICIAL else ClaimLabel.ORAL_ACCOUNT


def supported_verdict(claim: Claim, chunk: Chunk) -> ClaimVerdict:
    return ClaimVerdict(claim.claim_id, True, label_for(chunk.source_kind), chunk.source_id)


def unsupported_verdict(claim: Claim) -> ClaimVerdict:
    return ClaimVerdict(claim.claim_id, False, ClaimLabel.UNKNOWN)


def verbatim_fallback(claims: list[Claim], chunks: list[Chunk]) -> list[ClaimVerdict]:
    by_id = {c.chunk_id: c for c in chunks}
    verdicts = []
    for claim in claims:
        chunk = by_id.get(claim.chunk_id or "")
        quoted = (
            chunk is not None
            and chunk.source_kind is SourceKind.OFFICIAL
            and _normalize(claim.text) in _normalize(chunk.text)
        )
        verdicts.append(supported_verdict(claim, chunk) if quoted and chunk else unsupported_verdict(claim))
    return verdicts


def _normalize(text: str) -> str:
    return " ".join(text.split())
