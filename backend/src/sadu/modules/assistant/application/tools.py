import asyncio
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sadu.modules.admin import api as admin
from sadu.modules.assistant.application.audit_file import build_audit_report
from sadu.modules.assistant.application.context import (
    AttachmentRef,
    NewAction,
    NewAttachment,
    ToolOutcome,
    TurnContext,
)
from sadu.modules.assistant.domain.arabic_text import digits_ar, elements_ar
from sadu.modules.assistant.domain.conversation import ActionKind, AttachmentKind
from sadu.modules.assistant.domain.decision import ToolCall, ToolName
from sadu.modules.mapping import api as mapping
from sadu.modules.reports import api as reports
from sadu.modules.sites import api as sites
from sadu.modules.treatments import api as treatments
from sadu.modules.watch import api as watch
from sadu.shared.errors import NotFound
from sadu.shared.storage import ObjectStore, new_object_key
from sadu.shared.vocabulary import DamageType, Severity
from sadu.shared.web import UnitOfWork

NOMINAL_WALL_HEIGHT_M = 3.0
DEFAULT_PHOTO_ASPECT = 4 / 3
RECENT_SCANS = 10
MAX_NOTE_CHARS = 500

type Handler = Callable[[dict[str, Any], TurnContext, Sequence[ToolOutcome]], Awaitable[ToolOutcome]]


@dataclass(frozen=True)
class ToolDeps:
    unit_of_work: UnitOfWork
    store: ObjectStore
    detector: mapping.DamageDetector
    catalog_path: Path
    map_rows: int


class ToolError(Exception):
    def __init__(self, code: str, summary_ar: str) -> None:
        super().__init__(code)
        self.code = code
        self.summary_ar = summary_ar


class Toolbox:
    def __init__(self, deps: ToolDeps) -> None:
        self._deps = deps
        self._handlers: dict[ToolName, Handler] = {
            ToolName.ANALYSE_PHOTO: self.analyse_photo,
            ToolName.GET_SITE_CONDITION: self.get_site_condition,
            ToolName.LIST_SITES: self.list_sites,
            ToolName.GET_MAP: self.get_map,
            ToolName.GET_WATCH_STATUS: self.get_watch_status,
            ToolName.FIND_TREATMENTS: self.find_treatments,
            ToolName.DRAFT_AUDIT_REPORT: self.draft_audit_report,
            ToolName.SEND_REPORT: self.send_report,
        }

    async def run(self, call: ToolCall, context: TurnContext, earlier: Sequence[ToolOutcome]) -> ToolOutcome:
        try:
            return await self._handlers[call.tool](call.arguments, context, earlier)
        except ToolError as error:
            return ToolOutcome(call.tool, False, error.summary_ar, {"error": error.code})
        except NotFound:
            return ToolOutcome(call.tool, False, "لم أجد العنصر المطلوب.", {"error": "not_found"})

    async def analyse_photo(
        self, arguments: dict[str, Any], context: TurnContext, earlier: Sequence[ToolOutcome]
    ) -> ToolOutcome:
        photo = context.attachment(_uuid(arguments, "attachment_id"))
        if photo is None or photo.kind is not AttachmentKind.PHOTO:
            raise ToolError("photo_not_found", "لم أجد هذه الصورة بين مرفقات المحادثة.")
        facade_id = _optional_uuid(arguments, "facade_id")
        async with self._deps.unit_of_work() as session:
            facade = await sites.get_facade(session, facade_id) if facade_id else None
            site = await sites.get_site(session, facade.site_id) if facade else None
        wall = _wall_for(photo, facade)
        jpeg = await self._deps.store.get(photo.object_key)
        prepared = await asyncio.to_thread(
            mapping.prepare_wall, jpeg, mapping.Quad.full_frame(), wall.size, self._deps.map_rows
        )
        run = await _detect(self._deps.detector, prepared)

        map_id = None
        if facade is not None and context.can_save_maps:
            view = await self._save_draft_map(context, wall, prepared, run)
            map_id, elements = view.id, view.elements
        else:
            elements = mapping.draft_elements(prepared, run)
        rows = [_element_row(e, prepared.grid, wall.size if facade else None) for e in elements]
        return ToolOutcome(
            ToolName.ANALYSE_PHOTO,
            True,
            _analysis_summary(rows, saved=map_id is not None, facade_named=facade is not None),
            {
                "attachment_id": str(photo.id),
                "map_id": str(map_id) if map_id else None,
                "map_url": f"/dashboard/maps/{map_id}" if map_id else None,
                "wall_name": wall.name,
                "site_id": str(site.id) if site else None,
                "site_name": site.name_ar if site else None,
                "facade_id": str(facade.id) if facade else None,
                "measured": facade is not None,
                "detector": run.detector,
                "model_summary_ar": run.output.summary_ar,
                "elements": rows,
            },
        )

    async def _save_draft_map(
        self,
        context: TurnContext,
        wall: mapping.WallSpec,
        prepared: mapping.PreparedWall,
        run: mapping.DetectionRun,
    ) -> mapping.MapView:
        async with self._deps.unit_of_work() as session:
            view = await mapping.save_map(
                session, self._deps.store, wall=wall, prepared=prepared, run=run, created_by=context.user_id
            )
            await admin.audit(
                session,
                actor_id=context.user_id,
                action="map.create",
                target_type="damage_map",
                target_id=str(view.id),
                details={
                    "via": "assistant",
                    "conversation_id": str(context.conversation_id),
                    "detector": run.detector,
                    "elements": len(view.elements),
                },
                request_id=context.request_id,
            )
        return view

    async def get_site_condition(
        self, arguments: dict[str, Any], context: TurnContext, earlier: Sequence[ToolOutcome]
    ) -> ToolOutcome:
        site_id = _uuid(arguments, "site_id")
        async with self._deps.unit_of_work() as session:
            condition = await reports.site_condition(session, site_id, self._catalog(), datetime.now(UTC))
        walls = [
            {
                "name_ar": w.name_ar,
                "status": w.status,
                "map_id": str(w.map_id) if w.map_id else None,
                "elements": w.elements,
                "urgent": w.urgent,
                "needs_review": w.needs_review,
                "needs_specialist": w.needs_specialist,
                "survey_due": w.survey_due,
            }
            for w in condition.walls
        ]
        summary = (
            f"حالة {condition.site.name_ar}: {digits_ar(condition.urgent)} عاجل معتمد، "
            f"{digits_ar(condition.awaiting_approval)} بانتظار الاعتماد، "
            f"{digits_ar(condition.walls_due)} يحتاج مسحًا."
        )
        return ToolOutcome(
            ToolName.GET_SITE_CONDITION,
            True,
            summary,
            {
                "site_id": str(site_id),
                "site_name": condition.site.name_ar,
                "urgent": condition.urgent,
                "awaiting_approval": condition.awaiting_approval,
                "walls_due": condition.walls_due,
                "walls": walls,
            },
        )

    async def list_sites(
        self, arguments: dict[str, Any], context: TurnContext, earlier: Sequence[ToolOutcome]
    ) -> ToolOutcome:
        async with self._deps.unit_of_work() as session:
            listed = [
                {
                    "id": str(site.id),
                    "name_ar": site.name_ar,
                    "facades": [
                        {"id": str(f.id), "code": f.code, "name_ar": f.name_ar}
                        for f in await sites.list_facades(session, site.id)
                    ],
                }
                for site in await sites.list_sites(session)
            ]
        return ToolOutcome(
            ToolName.LIST_SITES, True, f"عُرضت المواقع: {digits_ar(len(listed))}.", {"sites": listed}
        )

    async def get_map(
        self, arguments: dict[str, Any], context: TurnContext, earlier: Sequence[ToolOutcome]
    ) -> ToolOutcome:
        async with self._deps.unit_of_work() as session:
            view = await mapping.get_map(session, _uuid(arguments, "map_id"))
            site = await sites.get_site(session, view.site_id) if view.site_id else None
        rows = [_element_row(e, view.grid, view.wall) for e in view.elements]
        status_ar = "معتمد" if view.status is mapping.MapStatus.APPROVED else "مسودة"
        return ToolOutcome(
            ToolName.GET_MAP,
            True,
            f"مخطط {view.wall_name} ({status_ar}): {elements_ar(len(rows))}.",
            {
                "map_id": str(view.id),
                "map_url": f"/dashboard/maps/{view.id}",
                "wall_name": view.wall_name,
                "site_id": str(view.site_id) if view.site_id else None,
                "site_name": site.name_ar if site else None,
                "status": view.status.value,
                "field_inspected": view.field_inspected_at is not None,
                "measured": True,
                "elements": rows,
            },
        )

    async def get_watch_status(
        self, arguments: dict[str, Any], context: TurnContext, earlier: Sequence[ToolOutcome]
    ) -> ToolOutcome:
        site_id = _uuid(arguments, "site_id")
        async with self._deps.unit_of_work() as session:
            site = await sites.get_site(session, site_id)
            history = await watch.site_scans(session, site_id, limit=RECENT_SCANS)
        latest = next((scan for scan in history if scan.status is watch.ScanStatus.OK), None)
        if latest is None:
            return ToolOutcome(
                ToolName.GET_WATCH_STATUS,
                True,
                f"لا مسح فضائي صالح بعد لموقع {site.name_ar}.",
                {"site_id": str(site_id), "site_name": site.name_ar, "scanned": False},
            )
        warning = watch.site_warning(history)
        level_ar = watch.LEVEL_AR[latest.level]
        return ToolOutcome(
            ToolName.GET_WATCH_STATUS,
            True,
            f"آخر رصد فضائي لموقع {site.name_ar}: {level_ar} بدرجة {digits_ar(latest.score)}.",
            {
                "site_id": str(site_id),
                "site_name": site.name_ar,
                "scanned": True,
                "scanned_at": latest.created_at.isoformat(),
                "is_sample": latest.is_sample,
                "level": latest.level.value,
                "level_ar": level_ar,
                "score": latest.score,
                "trend": warning.trend.value if warning else None,
                "confirmed": bool(warning and warning.confidence is watch.Confidence.CONFIRMED),
                "alert": bool(warning and warning.alert),
                "threats": [
                    {
                        "threat": s.threat.value,
                        "threat_ar": watch.THREAT_AR[s.threat],
                        "zone": s.zone.value,
                        "area_m2": round(s.area_m2, 1),
                    }
                    for s in latest.signals
                ],
            },
        )

    async def find_treatments(
        self, arguments: dict[str, Any], context: TurnContext, earlier: Sequence[ToolOutcome]
    ) -> ToolOutcome:
        catalog = self._catalog()
        wanted = _wanted_damage(arguments, context, earlier)
        if not wanted:
            raise ToolError("no_damage_named", "حدد نوع التلف أو حلّل صورة أولًا لأبحث عن معالجته.")
        items, unmatched = [], []
        for damage_type, severity in wanted:
            treatment = catalog.treatment_for(damage_type, severity)
            if treatment is None:
                unmatched.append({"damage_type": damage_type.value, "severity": severity.value})
                continue
            items.append(
                {
                    "code": treatment.code,
                    "title_ar": treatment.title_ar,
                    "damage_type": damage_type.value,
                    "severity": severity.value,
                    "specialist_required": treatment.specialist_required,
                    "steps_ar": list(treatment.steps_ar),
                }
            )
        summary = f"وُجدت {digits_ar(len(items))} معالجة في الدليل"
        summary += f"، و{digits_ar(len(unmatched))} تلف بلا معالجة." if unmatched else "."
        return ToolOutcome(
            ToolName.FIND_TREATMENTS,
            True,
            summary,
            {"catalog_review_status": catalog.review_status.value, "items": items, "unmatched": unmatched},
        )

    async def draft_audit_report(
        self, arguments: dict[str, Any], context: TurnContext, earlier: Sequence[ToolOutcome]
    ) -> ToolOutcome:
        results = context.element_results(earlier)
        summary_ar = _text(arguments, "summary_ar")
        if not results and not summary_ar:
            raise ToolError("nothing_to_report", "لا نتائج فحص في المحادثة بعد. حلّل صورة أو اقرأ مخططًا أولًا.")
        photos = {
            a.id: await self._deps.store.get(a.object_key)
            for a in context.attachments
            if a.kind is AttachmentKind.PHOTO and any(r.get("attachment_id") == str(a.id) for r in results)
        }
        report = build_audit_report(
            results,
            catalog=self._catalog(),
            photos={str(key): jpeg for key, jpeg in photos.items()},
            documents=[a.file_name for a in context.attachments if a.kind is AttachmentKind.DOCUMENT],
            title_ar=_text(arguments, "title_ar"),
            summary_ar=summary_ar,
            recommendations_ar=_texts(arguments, "recommendations_ar"),
            reference=context.conversation_id.hex[:8],
            generated_at=datetime.now(UTC),
        )
        pdf = await reports.audit_report_pdf(report)
        attachment = NewAttachment(
            id=uuid4(),
            kind=AttachmentKind.AUDIT_REPORT,
            file_name=f"athar-audit-{report.generated_at:%Y-%m-%d}-{report.reference}.pdf",
            media_type="application/pdf",
            object_key=new_object_key("assistant/reports", "pdf"),
            size_bytes=len(pdf),
        )
        await self._deps.store.put(attachment.object_key, pdf, attachment.media_type)
        async with self._deps.unit_of_work() as session:
            await admin.audit(
                session,
                actor_id=context.user_id,
                action="assistant.audit_report",
                target_type="assistant_attachment",
                target_id=str(attachment.id),
                details={"conversation_id": str(context.conversation_id), "elements": len(report.elements)},
                request_id=context.request_id,
            )
        return ToolOutcome(
            ToolName.DRAFT_AUDIT_REPORT,
            True,
            f"صيغ ملف التدقيق: {elements_ar(len(report.elements))}، ويتطلب اعتماد المختص.",
            {
                "attachment_id": str(attachment.id),
                "file_name": attachment.file_name,
                "elements": len(report.elements),
                "urgent": report.urgent,
                "field_visits": len(report.field_visits),
            },
            attachment=attachment,
        )

    async def send_report(
        self, arguments: dict[str, Any], context: TurnContext, earlier: Sequence[ToolOutcome]
    ) -> ToolOutcome:
        drafted = context.audit_reports(earlier)
        wanted = _optional_uuid(arguments, "attachment_id")
        report = next((r for r in reversed(drafted) if wanted in (None, r.id)), None)
        if report is None:
            raise ToolError("no_audit_report", "لا يوجد ملف تدقيق لإرساله. اطلب صياغة ملف التدقيق أولًا.")
        action = NewAction(
            id=uuid4(),
            kind=ActionKind.SEND_REPORT,
            payload={
                "attachment_id": str(report.id),
                "file_name": report.file_name,
                "note_ar": (_text(arguments, "note_ar") or "")[:MAX_NOTE_CHARS],
            },
        )
        return ToolOutcome(
            ToolName.SEND_REPORT,
            True,
            f"طلب إرسال «{report.file_name}» إلى المختصين ينتظر تأكيدك.",
            {"action_id": str(action.id), "attachment_id": str(report.id), "file_name": report.file_name},
            action=action,
        )

    def _catalog(self) -> treatments.Catalog:
        return treatments.catalog_at(self._deps.catalog_path)


async def _detect(detector: mapping.DamageDetector, prepared: mapping.PreparedWall) -> mapping.DetectionRun:
    try:
        run = await mapping.detect_damage(detector, prepared)
    except mapping.PhotoUnusable as error:
        raise ToolError("photo_unusable", f"الصورة لا تصلح للتحليل: {error.params['reason_ar']}") from error
    if run.status is mapping.DetectorStatus.FAILED:
        raise ToolError(
            "detector_unavailable", "كاشف التلف غير متاح الآن. أعد المحاولة لاحقًا أو ارسم المخطط يدويًا."
        )
    return run


def _analysis_summary(rows: Sequence[dict[str, Any]], *, saved: bool, facade_named: bool) -> str:
    summary = f"حُللت الصورة: {elements_ar(len(rows))}"
    urgent = sum(1 for row in rows if row["severity"] == Severity.URGENT)
    if urgent:
        summary += f"، منها {digits_ar(urgent)} عاجل"
    if saved:
        return summary + "، وحُفظت مسودة مخطط تنتظر مراجعة المختص."
    if facade_named:
        return summary + ". لم تُحفظ مسودة مخطط لأن حفظ المخططات يحتاج صلاحية المسح الميداني."
    return summary + "."


def _wall_for(photo: AttachmentRef, facade: sites.FacadeView | None) -> mapping.WallSpec:
    if facade is not None:
        plane = facade.plane
        size = mapping.WallSize(plane.width_m, plane.height_m)
        return mapping.WallSpec(facade.name_ar, size, facade.site_id, facade.id)
    aspect = photo.width / photo.height if photo.width and photo.height else DEFAULT_PHOTO_ASPECT
    size = mapping.WallSize(NOMINAL_WALL_HEIGHT_M * aspect, NOMINAL_WALL_HEIGHT_M)
    return mapping.WallSpec(photo.file_name, size)


def _element_row(
    element: mapping.Element, grid: mapping.Grid, wall: mapping.WallSize | None
) -> dict[str, Any]:
    size = mapping.measure(element, wall) if wall is not None else None
    return {
        "id": element.id,
        "damage_type": element.damage_type.value,
        "severity": element.severity.value,
        "confidence": element.confidence.value,
        "damage_class": element.damage_class,
        "location": mapping.location_label(element, grid),
        "area_m2": size.area_m2 if size else None,
        "length_m": size.length_m if size else None,
        "count": size.count if size else None,
        "needs_review": element.needs_review,
    }


def _wanted_damage(
    arguments: dict[str, Any], context: TurnContext, earlier: Sequence[ToolOutcome]
) -> list[tuple[DamageType, Severity]]:
    named = _text(arguments, "damage_type")
    if named:
        try:
            damage_type = DamageType(named)
            severities = [Severity(arguments["severity"])] if arguments.get("severity") else list(Severity)
        except ValueError as error:
            raise ToolError("invalid_argument", "نوع التلف أو شدته غير معروفين في المسرد.") from error
        return [(damage_type, severity) for severity in severities]
    found = {
        (DamageType(row["damage_type"]), Severity(row["severity"]))
        for result in context.element_results(earlier)
        for row in result["elements"]
    }
    return sorted(found, key=lambda pair: (pair[0].value, -pair[1].rank))


def _uuid(arguments: dict[str, Any], name: str) -> UUID:
    value = _optional_uuid(arguments, name)
    if value is None:
        raise ToolError("missing_argument", f"ينقص المعرّف {name}.")
    return value


def _optional_uuid(arguments: dict[str, Any], name: str) -> UUID | None:
    raw = arguments.get(name)
    if raw in (None, ""):
        return None
    try:
        return UUID(str(raw))
    except ValueError as error:
        raise ToolError("invalid_argument", f"المعرّف {name} غير صالح.") from error


def _text(arguments: dict[str, Any], name: str) -> str | None:
    value = arguments.get(name)
    if not isinstance(value, str):
        return None
    return value.strip() or None


def _texts(arguments: dict[str, Any], name: str) -> list[str]:
    values = arguments.get(name) or []
    return [v.strip() for v in values if isinstance(v, str) and v.strip()]
