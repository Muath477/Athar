from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ReportNotice:
    file_name: str
    link: str
    conversation_title: str
    note_ar: str


class SpecialistChannel(Protocol):
    @property
    def name(self) -> str: ...

    async def deliver(self, notice: ReportNotice) -> bool: ...
