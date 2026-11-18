from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from sadu.modules.admin import api as admin
from sadu.modules.admin.interface.auth import ModelManager
from sadu.modules.models import api as models
from sadu.modules.models.interface.schemas import ModelIn, ModelOut, model_out
from sadu.shared.web import Session, State

router = APIRouter(prefix="/ml", tags=["ml"])


@router.get("/models")
async def list_models(_: ModelManager, session: Session) -> list[ModelOut]:
    return [model_out(view) for view in await models.list_models(session)]


@router.post("/models", status_code=201)
async def register_model(body: ModelIn, user: ModelManager, session: Session, request: Request) -> ModelOut:
    view = await models.register_model(
        session,
        models.NewModel(body.name, body.version, body.base_model, body.adapter_uri, body.metrics),
        user.id,
    )
    await _audit(session, request, user.id, "model.register", view)
    return model_out(view)


@router.post("/models/{model_id}/activate")
async def activate_model(model_id: UUID, user: ModelManager, session: Session, request: Request) -> ModelOut:
    view = await models.activate_model(session, model_id)
    await _audit(session, request, user.id, "model.activate", view)
    return model_out(view)


@router.post("/models/{model_id}/retire")
async def retire_model(model_id: UUID, user: ModelManager, session: Session, request: Request) -> ModelOut:
    view = await models.retire_model(session, model_id)
    await _audit(session, request, user.id, "model.retire", view)
    return model_out(view)


@router.get("/training-export")
async def training_export(
    user: ModelManager, state: State, request: Request, weak: bool = False
) -> StreamingResponse:
    async with state.unit_of_work() as session:
        export = await models.training_export(session, state.store, weak=weak)
        await admin.audit(
            session,
            actor_id=user.id,
            action="model.training_export",
            target_type="training_export",
            target_id="damage_maps",
            details={"examples": export.examples, "weak": weak},
            request_id=getattr(request.state, "request_id", None),
        )
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M")
    return StreamingResponse(
        export.chunks,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="athar-training-{stamp}.zip"'},
    )


async def _audit(
    session: AsyncSession, request: Request, actor_id: UUID, action: str, view: models.ModelView
) -> None:
    await admin.audit(
        session,
        actor_id=actor_id,
        action=action,
        target_type="ml_model",
        target_id=str(view.id),
        details={"name": view.name, "version": view.version, "status": view.status},
        request_id=getattr(request.state, "request_id", None),
    )
