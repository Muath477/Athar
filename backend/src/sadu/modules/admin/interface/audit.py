import json
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel

from sadu.modules.admin import api as admin
from sadu.modules.admin.interface.auth import AuditExporter, AuditReader
from sadu.shared.tabular import csv_download
from sadu.shared.web import Session

router = APIRouter(tags=["audit"])

MAX_PAGE_SIZE = 200
MAX_EXPORT_ROWS = 10_000
CSV_HEADER = ("الوقت (UTC)", "المنفّذ", "الإجراء", "نوع الهدف", "معرّف الهدف", "التفاصيل", "معرّف الطلب")


class AuditEntryOut(BaseModel):
    id: str
    at: datetime
    actor_id: str | None
    actor_email: str | None
    action: str
    target_type: str
    target_id: str
    details: dict[str, Any]
    request_id: str | None


class AuditPageOut(BaseModel):
    entries: list[AuditEntryOut]
    total: int
    page: int
    page_size: int


def audit_filter(
    actor: Annotated[str | None, Query(max_length=320)] = None,
    action: Annotated[str | None, Query(max_length=64)] = None,
    target_type: Annotated[str | None, Query(max_length=32)] = None,
    start: Annotated[datetime | None, Query(alias="from")] = None,
    end: Annotated[datetime | None, Query(alias="to")] = None,
) -> admin.AuditFilter:
    return admin.AuditFilter(actor, action, target_type, start, end)


Filters = Annotated[admin.AuditFilter, Depends(audit_filter)]


@router.get("/admin/audit")
async def list_audit(
    _: AuditReader,
    session: Session,
    filters: Filters,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 50,
) -> AuditPageOut:
    result = await admin.list_audit(session, filters, offset=(page - 1) * page_size, limit=page_size)
    return AuditPageOut(
        entries=[entry_out(e) for e in result.entries], total=result.total, page=page, page_size=page_size
    )


@router.get("/admin/audit.csv", response_class=Response)
async def export_audit(_: AuditExporter, session: Session, filters: Filters) -> Response:
    result = await admin.list_audit(session, filters, limit=MAX_EXPORT_ROWS)
    rows = [
        (
            e.at.astimezone(UTC).isoformat(timespec="seconds"),
            e.actor_email or "system",
            e.action,
            e.target_type,
            e.target_id,
            json.dumps(e.details, ensure_ascii=False, sort_keys=True) if e.details else "",
            e.request_id,
        )
        for e in result.entries
    ]
    return csv_download(f"athar-audit-{datetime.now(UTC):%Y-%m-%d}.csv", CSV_HEADER, rows)


def entry_out(entry: admin.AuditEntry) -> AuditEntryOut:
    return AuditEntryOut(
        id=str(entry.id),
        at=entry.at,
        actor_id=str(entry.actor_id) if entry.actor_id else None,
        actor_email=entry.actor_email,
        action=entry.action,
        target_type=entry.target_type,
        target_id=entry.target_id,
        details=entry.details,
        request_id=entry.request_id,
    )
