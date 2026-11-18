import asyncio
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from sadu.modules.admin import api as admin
from sadu.modules.admin.interface.auth import Expert, Inspector
from sadu.modules.capture import api as capture
from sadu.modules.mapping import api as mapping
from sadu.modules.mapping.interface.schemas import (
    AccuracyOut,
    CorrectionsIn,
    ElementEditsIn,
    FieldInspectionIn,
    GlossaryEntryOut,
    MapOut,
    MapSummaryOut,
    NewMapMeta,
    accuracy_out,
    glossary_out,
    map_out,
    summary_out,
)
from sadu.modules.sites import api as sites
from sadu.modules.treatments import api as treatments
from sadu.shared.errors import SaduError
from sadu.shared.web import AppState, Session, State

router = APIRouter(tags=["maps"])

MAPS_PER_USER_PER_HOUR = 30


def damage_detector(request: Request) -> mapping.DamageDetector:
    detector: mapping.DamageDetector = request.app.state.damage_detector
    return detector


Detector = Annotated[mapping.DamageDetector, Depends(damage_detector)]


@router.post("/maps", status_code=201)
async def create_map(
    request: Request,
    user: Inspector,
    state: State,
    detector: Detector,
    meta: Annotated[str, Form(max_length=4000)],
    photo: Annotated[UploadFile | None, File()] = None,
) -> MapOut:
    state.rate_limiter.check(f"maps:{user.id}", MAPS_PER_USER_PER_HOUR, 3600)
    try:
        parsed = NewMapMeta.model_validate_json(meta)
    except ValidationError as error:
        raise SaduError("validation_failed", status=422) from error
    quad = _quad(parsed.corners)

    async with state.unit_of_work() as session:
        wall = await _wall_spec(session, parsed)
        photo_jpeg = await _photo(session, state, photo, parsed.observation_id)

    prepared = await asyncio.to_thread(
        mapping.prepare_wall, photo_jpeg, quad, wall.size, state.settings.sadu_map_rows
    )
    run = await mapping.detect_damage(detector, prepared)

    async with state.unit_of_work() as session:
        view = await mapping.save_map(
            session, state.store, wall=wall, prepared=prepared, run=run, created_by=user.id
        )
        await admin.audit(
            session,
            actor_id=user.id,
            action="map.create",
            target_type="damage_map",
            target_id=str(view.id),
            details={"detector": run.detector, "detector_status": run.status, "cells": len(view.cells)},
            request_id=getattr(request.state, "request_id", None),
        )
        previous = await mapping.previous_approved(session, view)
    return map_out(view, state.store, _catalog(state), previous)


@router.get("/maps")
async def list_maps(
    _: Inspector, session: Session, state: State, site_id: UUID | None = None, facade_id: UUID | None = None
) -> list[MapSummaryOut]:
    summaries = await mapping.list_maps(session, site_id=site_id, facade_id=facade_id)
    return [summary_out(s, state.store) for s in summaries]


@router.get("/maps/accuracy")
async def map_accuracy(_: Inspector, session: Session, site_id: UUID | None = None) -> AccuracyOut:
    return accuracy_out(await mapping.accuracy(session, site_id))


@router.get("/maps/glossary")
async def map_glossary(_: Inspector) -> list[GlossaryEntryOut]:
    return glossary_out()


@router.get("/maps/{map_id}")
async def get_map(map_id: UUID, _: Inspector, session: Session, state: State) -> MapOut:
    view = await mapping.get_map(session, map_id)
    return map_out(view, state.store, _catalog(state), await mapping.previous_approved(session, view))


@router.post("/maps/{map_id}/cells")
async def correct_cells(
    map_id: UUID, body: CorrectionsIn, user: Expert, session: Session, state: State, request: Request
) -> MapOut:
    current = await mapping.get_map(session, map_id)
    try:
        corrections = [
            mapping.CellCorrection(current.grid.parse(c.cell), c.damage_type, c.severity)
            for c in body.corrections
        ]
    except ValueError as error:
        raise SaduError("validation_failed", status=422) from error
    view = await mapping.correct_cells(session, map_id, corrections)
    await admin.audit(
        session,
        actor_id=user.id,
        action="map.correct",
        target_type="damage_map",
        target_id=str(map_id),
        details={"cells": [c.cell for c in body.corrections]},
        request_id=getattr(request.state, "request_id", None),
    )
    return map_out(view, state.store, _catalog(state), await mapping.previous_approved(session, view))


@router.post("/maps/{map_id}/elements")
async def edit_elements(
    map_id: UUID, body: ElementEditsIn, user: Expert, session: Session, state: State, request: Request
) -> MapOut:
    try:
        edits = [
            mapping.ElementEdit(
                edit.action,
                edit.element_id,
                mapping.Element(
                    "new",
                    edit.element.damage_type,
                    tuple((float(p[0]), float(p[1])) for p in edit.element.points),
                    edit.element.severity,
                    mapping.ModelConfidence.HIGH,
                    mapping.CellSource.EXPERT,
                    edit.element.damage_class,
                )
                if edit.element is not None
                else None,
            )
            for edit in body.edits
        ]
    except (ValueError, IndexError) as error:
        raise SaduError("validation_failed", status=422) from error
    view = await mapping.edit_elements(session, map_id, edits, user.id)
    await admin.audit(
        session,
        actor_id=user.id,
        action="map.edit_elements",
        target_type="damage_map",
        target_id=str(map_id),
        details={"edits": [f"{e.action}:{e.element_id or 'new'}" for e in body.edits]},
        request_id=getattr(request.state, "request_id", None),
    )
    return map_out(view, state.store, _catalog(state), await mapping.previous_approved(session, view))


@router.post("/maps/{map_id}/field-inspection")
async def record_field_inspection(
    map_id: UUID, body: FieldInspectionIn, user: Expert, session: Session, state: State, request: Request
) -> MapOut:
    view = await mapping.record_field_inspection(session, map_id, user.id, body.notes.strip())
    await admin.audit(
        session,
        actor_id=user.id,
        action="map.field_inspection",
        target_type="damage_map",
        target_id=str(map_id),
        request_id=getattr(request.state, "request_id", None),
    )
    return map_out(view, state.store, _catalog(state), await mapping.previous_approved(session, view))


@router.post("/maps/{map_id}/approve")
async def approve_map(map_id: UUID, user: Expert, session: Session, state: State, request: Request) -> MapOut:
    view = await mapping.approve_map(session, map_id, user.id)
    await admin.audit(
        session,
        actor_id=user.id,
        action="map.approve",
        target_type="damage_map",
        target_id=str(map_id),
        request_id=getattr(request.state, "request_id", None),
    )
    return map_out(view, state.store, _catalog(state), await mapping.previous_approved(session, view))


def _quad(corners: list[list[float]] | None) -> mapping.Quad:
    if corners is None:
        return mapping.Quad.full_frame()
    try:
        return mapping.Quad.from_list(corners)
    except ValueError as error:
        raise SaduError("invalid_corners", status=422) from error


async def _wall_spec(session: AsyncSession, meta: NewMapMeta) -> mapping.WallSpec:
    if meta.facade_id is not None:
        facade = await sites.get_facade(session, meta.facade_id)
        plane = facade.plane
        size = mapping.WallSize(meta.width_m or plane.width_m, meta.height_m or plane.height_m)
        return mapping.WallSpec(meta.wall_name or facade.name_ar, size, facade.site_id, facade.id)
    if not (meta.wall_name and meta.width_m and meta.height_m):
        raise SaduError("wall_size_required", status=422)
    return mapping.WallSpec(meta.wall_name, mapping.WallSize(meta.width_m, meta.height_m), meta.site_id)


async def _photo(
    session: AsyncSession, state: AppState, photo: UploadFile | None, observation_id: UUID | None
) -> bytes:
    if photo is not None:
        raw = await photo.read(capture.MAX_UPLOAD_BYTES + 1)
        processed = await asyncio.to_thread(capture.process_upload, raw)
        return processed.jpeg
    if observation_id is not None:
        observation = await capture.get_observation(session, observation_id)
        return await state.store.get(observation.object_key)
    raise SaduError("photo_required", status=422)


def _catalog(state: AppState) -> treatments.Catalog:
    return treatments.catalog_at(state.settings.treatment_catalog_path)
