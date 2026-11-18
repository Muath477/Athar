from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from sadu.modules.admin import api as admin
from sadu.modules.admin.api import ManagedUser, Role
from sadu.modules.admin.interface.auth import Admin
from sadu.shared.web import Session

router = APIRouter(tags=["users"])

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
MAX_ASSIGNED_SITES = 500


class UserOut(BaseModel):
    id: str
    email: str
    display_name: str
    role: str
    site_ids: list[str]
    is_active: bool
    must_change_password: bool
    last_login_at: datetime | None
    created_at: datetime


class NewUserIn(BaseModel):
    email: str = Field(min_length=3, max_length=320, pattern=EMAIL_PATTERN)
    display_name: str = Field(default="", max_length=120)
    role: Role
    password: str = Field(min_length=1, max_length=200)
    site_ids: list[UUID] = Field(default_factory=list, max_length=MAX_ASSIGNED_SITES)


class RoleIn(BaseModel):
    role: Role


class SitesIn(BaseModel):
    site_ids: list[UUID] = Field(max_length=MAX_ASSIGNED_SITES)


class ActiveIn(BaseModel):
    active: bool


class PasswordResetIn(BaseModel):
    temporary_password: str = Field(min_length=1, max_length=200)


def user_out(user: ManagedUser) -> UserOut:
    return UserOut(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        site_ids=[str(site_id) for site_id in user.site_ids],
        is_active=user.is_active,
        must_change_password=user.must_change_password,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


@router.get("/admin/users")
async def list_users(_: Admin, session: Session) -> list[UserOut]:
    return [user_out(u) for u in await admin.list_users(session)]


@router.post("/admin/users", status_code=201)
async def create_user(body: NewUserIn, user: Admin, session: Session, request: Request) -> UserOut:
    created = await admin.create_user(
        session,
        body.email,
        body.password,
        body.role,
        display_name=body.display_name,
        must_change_password=True,
    )
    managed = await admin.assign_sites(session, created.id, body.site_ids)
    await _audit(
        session,
        request,
        user,
        "user.create",
        managed.id,
        {"role": managed.role, "sites": [str(s) for s in managed.site_ids]},
    )
    return user_out(managed)


@router.post("/admin/users/{user_id}/role")
async def change_role(
    user_id: UUID, body: RoleIn, user: Admin, session: Session, request: Request
) -> UserOut:
    before = await admin.get_user(session, user_id)
    managed = await admin.change_role(session, user, user_id, body.role)
    await _audit(session, request, user, "user.role", user_id, {"from": before.role, "to": managed.role})
    return user_out(managed)


@router.post("/admin/users/{user_id}/sites")
async def assign_sites(
    user_id: UUID, body: SitesIn, user: Admin, session: Session, request: Request
) -> UserOut:
    managed = await admin.assign_sites(session, user_id, body.site_ids)
    await _audit(session, request, user, "user.sites", user_id, {"sites": [str(s) for s in managed.site_ids]})
    return user_out(managed)


@router.post("/admin/users/{user_id}/active")
async def set_active(
    user_id: UUID, body: ActiveIn, user: Admin, session: Session, request: Request
) -> UserOut:
    managed = await admin.set_active(session, user, user_id, body.active)
    action = "user.reactivate" if body.active else "user.deactivate"
    await _audit(session, request, user, action, user_id)
    return user_out(managed)


@router.post("/admin/users/{user_id}/password")
async def reset_password(
    user_id: UUID, body: PasswordResetIn, user: Admin, session: Session, request: Request
) -> UserOut:
    managed = await admin.reset_password(session, user_id, body.temporary_password)
    await _audit(session, request, user, "user.password_reset", user_id)
    return user_out(managed)


async def _audit(
    session: AsyncSession,
    request: Request,
    actor: admin.UserView,
    action: str,
    user_id: UUID,
    details: dict[str, Any] | None = None,
) -> None:
    await admin.audit(
        session,
        actor_id=actor.id,
        action=action,
        target_type="user",
        target_id=str(user_id),
        details=details,
        request_id=getattr(request.state, "request_id", None),
    )
