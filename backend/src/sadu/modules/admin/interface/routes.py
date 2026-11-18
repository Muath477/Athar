from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel, Field

from sadu.modules.admin import api as admin
from sadu.modules.admin.api import UserView
from sadu.modules.admin.interface.audit import router as audit_router
from sadu.modules.admin.interface.auth import SESSION_COOKIE, Admin, SignedIn, Staff
from sadu.modules.admin.interface.users import router as users_router
from sadu.shared.web import Session, State, limit_per_ip, public

router = APIRouter(tags=["auth"])
router.include_router(users_router)
router.include_router(audit_router)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=200)


class Me(BaseModel):
    id: str
    email: str
    display_name: str
    role: str
    permissions: list[str]
    site_ids: list[str]
    must_change_password: bool
    csrf_token: str | None = None


class PasswordChangeIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=1, max_length=200)


class RoleOut(BaseModel):
    role: str
    permissions: list[str]


class AgentCostOut(BaseModel):
    agent: str
    calls: int
    cost_usd: float
    mean_latency_ms: float


class CostsOut(BaseModel):
    cost_per_photo_usd: float
    by_agent: list[AgentCostOut]


@router.post("/auth/login", dependencies=[Depends(public), Depends(limit_per_ip("login", 5, 60))])
async def login(body: LoginRequest, response: Response, session: Session, state: State) -> Me:
    result = await admin.login(session, body.email, body.password)
    response.set_cookie(
        SESSION_COOKIE,
        result.session_token,
        httponly=True,
        secure=state.settings.is_prod,
        samesite="strict",
        expires=result.expires_at,
        path="/",
    )
    await admin.audit(
        session, actor_id=result.user.id, action="login", target_type="user", target_id=str(result.user.id)
    )
    return me_out(result.user, result.csrf_token)


@router.post("/auth/logout", status_code=204, dependencies=[Depends(public)])
async def logout(request: Request, response: Response, session: Session) -> None:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        await admin.logout(session, token)
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/auth/me")
async def me(auth: SignedIn) -> Me:
    return me_out(auth.user, auth.csrf_token)


@router.post("/auth/password", status_code=204, dependencies=[Depends(limit_per_ip("password", 5, 60))])
async def change_password(body: PasswordChangeIn, auth: SignedIn, request: Request, session: Session) -> None:
    await admin.change_password(
        session,
        auth.user.id,
        current=body.current_password,
        new=body.new_password,
        session_token=request.cookies[SESSION_COOKIE],
    )
    await admin.audit(
        session,
        actor_id=auth.user.id,
        action="user.password_change",
        target_type="user",
        target_id=str(auth.user.id),
        request_id=getattr(request.state, "request_id", None),
    )


def me_out(user: UserView, csrf_token: str) -> Me:
    return Me(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        permissions=sorted(user.role.permissions),
        site_ids=sorted(str(site_id) for site_id in user.site_ids),
        must_change_password=user.must_change_password,
        csrf_token=csrf_token,
    )


@router.get("/auth/roles")
async def roles(_: Staff) -> list[RoleOut]:
    return [RoleOut(role=role, permissions=sorted(role.permissions)) for role in admin.Role]


@router.get("/admin/costs")
async def costs(
    _: Admin,
    session: Session,
    start: Annotated[datetime | None, Query(alias="from")] = None,
    end: Annotated[datetime | None, Query(alias="to")] = None,
) -> CostsOut:
    end = end or datetime.now(UTC)
    start = start or end - timedelta(days=1)
    return CostsOut(
        cost_per_photo_usd=await admin.cost_per_photo(session, start, end),
        by_agent=[AgentCostOut(**vars(c)) for c in await admin.costs_by_agent(session, start, end)],
    )
