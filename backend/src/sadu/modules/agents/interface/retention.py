from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel

from sadu.modules.admin.interface.auth import Admin
from sadu.modules.agents import api as agents
from sadu.shared.web import State

router = APIRouter(tags=["retention"])


class RetentionOut(BaseModel):
    observations_deleted: int
    objects_deleted: int


@router.post("/admin/retention/run")
async def run_retention(user: Admin, state: State) -> RetentionOut:
    result = await agents.purge_expired_photos(
        state.unit_of_work, state.store, now=datetime.now(UTC), actor_id=user.id
    )
    return RetentionOut(observations_deleted=result.observations, objects_deleted=result.objects)
