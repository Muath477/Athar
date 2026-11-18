import hashlib
import secrets
from collections.abc import Collection
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from sqlalchemy import Select, column, delete, func, select, table
from sqlalchemy.ext.asyncio import AsyncSession

from sadu.modules.admin.infrastructure.orm import AuditLogRow, LlmCallRow, SessionRow, UserRow, UserSiteRow
from sadu.shared.errors import Conflict, NotFound, SaduError, TooManyRequests, Unauthorized

SESSION_LIFETIME = timedelta(hours=12)
MAX_FAILED_LOGINS = 5
LOCKOUT = timedelta(minutes=15)
MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 200

_hasher = PasswordHasher()
_DUMMY_HASH = _hasher.hash(secrets.token_hex(16))


class Permission(StrEnum):
    READ = "read"
    SURVEY = "survey"
    REVIEW = "review"
    MANAGE_SITE = "manage_site"
    MANAGE_DEVICES = "manage_devices"
    EXPORT = "export"
    ASSIST = "assistant"
    MANAGE_MODELS = "manage_models"
    READ_AUDIT = "read_audit"
    ADMINISTER = "administer"


class Role(StrEnum):
    INSPECTOR = "inspector"
    SITE_MANAGER = "site_manager"
    EXPERT = "expert"
    AUTHORITY = "authority"
    ML_ENGINEER = "ml_engineer"
    ADMIN = "admin"

    @property
    def permissions(self) -> frozenset[Permission]:
        return ROLE_PERMISSIONS[self]

    def allows(self, required: Permission) -> bool:
        return required in self.permissions


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.INSPECTOR: frozenset({Permission.READ, Permission.SURVEY, Permission.ASSIST}),
    Role.SITE_MANAGER: frozenset(
        {
            Permission.READ,
            Permission.MANAGE_SITE,
            Permission.MANAGE_DEVICES,
            Permission.EXPORT,
            Permission.ASSIST,
        }
    ),
    Role.EXPERT: frozenset(
        {Permission.READ, Permission.SURVEY, Permission.REVIEW, Permission.EXPORT, Permission.ASSIST}
    ),
    Role.AUTHORITY: frozenset({Permission.READ, Permission.EXPORT, Permission.ASSIST, Permission.READ_AUDIT}),
    Role.ML_ENGINEER: frozenset({Permission.READ, Permission.EXPORT, Permission.MANAGE_MODELS}),
    Role.ADMIN: frozenset(Permission),
}

ROLES_SEEING_EVERY_SITE = frozenset({Role.ADMIN, Role.AUTHORITY})

_SITES = table("sites", column("id"))


@dataclass(frozen=True)
class UserView:
    id: UUID
    email: str
    role: Role
    display_name: str = ""
    site_ids: frozenset[UUID] = field(default_factory=frozenset)
    must_change_password: bool = False

    @property
    def visible_site_ids(self) -> frozenset[UUID] | None:
        if self.role in ROLES_SEEING_EVERY_SITE or not self.site_ids:
            return None
        return self.site_ids

    def sees_site(self, site_id: UUID | None) -> bool:
        visible = self.visible_site_ids
        return visible is None or site_id is None or site_id in visible


@dataclass(frozen=True)
class ManagedUser:
    id: UUID
    email: str
    display_name: str
    role: Role
    site_ids: tuple[UUID, ...]
    is_active: bool
    must_change_password: bool
    last_login_at: datetime | None
    created_at: datetime


@dataclass(frozen=True)
class AuditFilter:
    actor: str | None = None
    action_prefix: str | None = None
    target_type: str | None = None
    start: datetime | None = None
    end: datetime | None = None


@dataclass(frozen=True)
class AuditEntry:
    id: UUID
    at: datetime
    actor_id: UUID | None
    actor_email: str | None
    action: str
    target_type: str
    target_id: str
    details: dict[str, Any]
    request_id: str | None


@dataclass(frozen=True)
class AuditPage:
    entries: list[AuditEntry]
    total: int


@dataclass(frozen=True)
class LoginResult:
    user: UserView
    session_token: str
    csrf_token: str
    expires_at: datetime


@dataclass(frozen=True)
class AuthenticatedSession:
    user: UserView
    csrf_token: str


@dataclass(frozen=True)
class AgentCost:
    agent: str
    calls: int
    cost_usd: float
    mean_latency_ms: float


def ensure_sees_site(user: UserView, site_id: UUID | None) -> None:
    if not user.sees_site(site_id):
        raise NotFound("not_found")


def check_password_policy(password: str) -> None:
    if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
        raise SaduError("weak_password", status=422, min_length=MIN_PASSWORD_LENGTH)


async def create_user(
    session: AsyncSession,
    email: str,
    password: str,
    role: Role,
    *,
    display_name: str = "",
    must_change_password: bool = False,
) -> UserView:
    check_password_policy(password)
    email = _normalize_email(email)
    if await session.scalar(select(UserRow.id).where(UserRow.email == email)):
        raise Conflict("user_exists")
    row = UserRow(
        email=email,
        password_hash=_hasher.hash(password),
        role=role,
        display_name=display_name.strip(),
        is_active=True,
        must_change_password=must_change_password,
    )
    session.add(row)
    await session.flush()
    return _user_view(row, frozenset())


async def login(session: AsyncSession, email: str, password: str) -> LoginResult:
    now = datetime.now(UTC)
    user = await session.scalar(select(UserRow).where(UserRow.email == _normalize_email(email)))
    if user is None:
        _password_matches(_DUMMY_HASH, password)
        raise Unauthorized("invalid_credentials")
    if user.locked_until and user.locked_until > now:
        raise TooManyRequests(
            "account_locked", retry_after_s=int((user.locked_until - now).total_seconds()) + 1
        )
    if not _password_matches(user.password_hash, password):
        user.failed_logins += 1
        if user.failed_logins >= MAX_FAILED_LOGINS:
            user.locked_until, user.failed_logins = now + LOCKOUT, 0
        raise Unauthorized("invalid_credentials")
    if not user.is_active:
        raise Unauthorized("account_disabled")

    user.failed_logins, user.locked_until = 0, None
    user.last_login_at = now
    if _hasher.check_needs_rehash(user.password_hash):
        user.password_hash = _hasher.hash(password)
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    expires_at = now + SESSION_LIFETIME
    session.add(SessionRow(id_hash=_hash(token), user_id=user.id, csrf_token=csrf, expires_at=expires_at))
    await session.flush()
    return LoginResult(_user_view(user, await _site_ids(session, user.id)), token, csrf, expires_at)


async def authenticate(session: AsyncSession, session_token: str) -> AuthenticatedSession:
    now = datetime.now(UTC)
    row = await session.get(SessionRow, _hash(session_token))
    if row is None or row.expires_at <= now:
        raise Unauthorized("session_expired")
    user = await session.get(UserRow, row.user_id)
    if user is None or not user.is_active:
        raise Unauthorized("session_expired")
    row.last_seen_at = now
    return AuthenticatedSession(_user_view(user, await _site_ids(session, user.id)), row.csrf_token)


async def logout(session: AsyncSession, session_token: str) -> None:
    await session.execute(delete(SessionRow).where(SessionRow.id_hash == _hash(session_token)))


async def change_password(
    session: AsyncSession, user_id: UUID, *, current: str, new: str, session_token: str
) -> None:
    user = await _user_row(session, user_id)
    if not _password_matches(user.password_hash, current):
        raise Unauthorized("invalid_credentials")
    check_password_policy(new)
    if new == current:
        raise SaduError("password_unchanged", status=422)
    user.password_hash = _hasher.hash(new)
    user.must_change_password = False
    await session.execute(
        delete(SessionRow).where(SessionRow.user_id == user_id, SessionRow.id_hash != _hash(session_token))
    )


async def list_users(session: AsyncSession) -> list[ManagedUser]:
    users = list(await session.scalars(select(UserRow).order_by(UserRow.email)))
    assignments = await session.execute(select(UserSiteRow.user_id, UserSiteRow.site_id))
    sites_by_user: dict[UUID, list[UUID]] = {}
    for user_id, site_id in assignments.all():
        sites_by_user.setdefault(user_id, []).append(site_id)
    return [_managed(user, sites_by_user.get(user.id, [])) for user in users]


async def get_user(session: AsyncSession, user_id: UUID) -> ManagedUser:
    user = await _user_row(session, user_id)
    return _managed(user, list(await _site_ids(session, user_id)))


async def change_role(session: AsyncSession, acting: UserView, user_id: UUID, role: Role) -> ManagedUser:
    _refuse_own_account(acting, user_id)
    user = await _user_row(session, user_id)
    user.role = role
    await session.flush()
    return await get_user(session, user_id)


async def assign_sites(session: AsyncSession, user_id: UUID, site_ids: Collection[UUID]) -> ManagedUser:
    await _user_row(session, user_id)
    wanted = set(site_ids)
    known = (
        set(await session.scalars(select(_SITES.c.id).where(_SITES.c.id.in_(wanted)))) if wanted else set()
    )
    if known != wanted:
        raise SaduError("unknown_site", status=422)
    await session.execute(delete(UserSiteRow).where(UserSiteRow.user_id == user_id))
    session.add_all(UserSiteRow(user_id=user_id, site_id=site_id) for site_id in wanted)
    await session.flush()
    return await get_user(session, user_id)


async def set_active(session: AsyncSession, acting: UserView, user_id: UUID, active: bool) -> ManagedUser:
    _refuse_own_account(acting, user_id)
    user = await _user_row(session, user_id)
    user.is_active = active
    if not active:
        await _revoke_sessions(session, user_id)
    await session.flush()
    return await get_user(session, user_id)


async def reset_password(session: AsyncSession, user_id: UUID, temporary: str) -> ManagedUser:
    check_password_policy(temporary)
    user = await _user_row(session, user_id)
    user.password_hash = _hasher.hash(temporary)
    user.must_change_password = True
    user.failed_logins, user.locked_until = 0, None
    await _revoke_sessions(session, user_id)
    await session.flush()
    return await get_user(session, user_id)


async def audit(
    session: AsyncSession,
    *,
    actor_id: UUID | None,
    action: str,
    target_type: str,
    target_id: str,
    details: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> None:
    session.add(
        AuditLogRow(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details or {},
            request_id=request_id,
        )
    )


async def list_audit(
    session: AsyncSession, filters: AuditFilter, *, offset: int = 0, limit: int = 50
) -> AuditPage:
    query = _filtered_audit(filters)
    total = await session.scalar(select(func.count()).select_from(query.subquery()))
    rows = await session.execute(
        query.order_by(AuditLogRow.at.desc(), AuditLogRow.id).offset(offset).limit(limit)
    )
    return AuditPage([_audit_entry(row, email) for row, email in rows.all()], int(total or 0))


async def was_audited(session: AsyncSession, action: str, target_id: str) -> bool:
    found = await session.scalar(
        select(AuditLogRow.id)
        .where(AuditLogRow.action == action, AuditLogRow.target_id == target_id)
        .limit(1)
    )
    return found is not None


async def record_llm_call(
    session: AsyncSession,
    *,
    observation_id: UUID | None,
    agent: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    latency_ms: int,
    status: str,
) -> None:
    session.add(
        LlmCallRow(
            observation_id=observation_id,
            agent=agent,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            status=status,
        )
    )


async def spent_today_usd(session: AsyncSession) -> float:
    midnight = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    total = await session.scalar(select(func.sum(LlmCallRow.cost_usd)).where(LlmCallRow.at >= midnight))
    return float(total or 0.0)


async def costs_by_agent(session: AsyncSession, start: datetime, end: datetime) -> list[AgentCost]:
    rows = await session.execute(
        select(
            LlmCallRow.agent,
            func.count(),
            func.coalesce(func.sum(LlmCallRow.cost_usd), 0.0),
            func.coalesce(func.avg(LlmCallRow.latency_ms), 0.0),
        )
        .where(LlmCallRow.at >= start, LlmCallRow.at < end)
        .group_by(LlmCallRow.agent)
        .order_by(LlmCallRow.agent)
    )
    return [
        AgentCost(agent, int(calls), float(cost), float(latency))
        for agent, calls, cost, latency in rows.all()
    ]


async def cost_per_photo(session: AsyncSession, start: datetime, end: datetime) -> float:
    photos, cost = (
        await session.execute(
            select(func.count(func.distinct(LlmCallRow.observation_id)), func.sum(LlmCallRow.cost_usd)).where(
                LlmCallRow.at >= start, LlmCallRow.at < end, LlmCallRow.observation_id.is_not(None)
            )
        )
    ).one()
    return float(cost or 0.0) / photos if photos else 0.0


def _filtered_audit(filters: AuditFilter) -> Select[AuditLogRow, str | None]:
    query = select(AuditLogRow, UserRow.email).outerjoin(UserRow, UserRow.id == AuditLogRow.actor_id)
    if filters.actor:
        query = query.where(UserRow.email.contains(_normalize_email(filters.actor), autoescape=True))
    if filters.action_prefix:
        query = query.where(AuditLogRow.action.startswith(filters.action_prefix.strip(), autoescape=True))
    if filters.target_type:
        query = query.where(AuditLogRow.target_type == filters.target_type)
    if filters.start:
        query = query.where(AuditLogRow.at >= filters.start)
    if filters.end:
        query = query.where(AuditLogRow.at < filters.end)
    return query


def _audit_entry(row: AuditLogRow, actor_email: str | None) -> AuditEntry:
    return AuditEntry(
        row.id,
        row.at,
        row.actor_id,
        actor_email,
        row.action,
        row.target_type,
        row.target_id,
        row.details,
        row.request_id,
    )


def _refuse_own_account(acting: UserView, user_id: UUID) -> None:
    if acting.id == user_id:
        raise Conflict("own_account")


async def _user_row(session: AsyncSession, user_id: UUID) -> UserRow:
    user = await session.get(UserRow, user_id)
    if user is None:
        raise NotFound("not_found")
    return user


async def _site_ids(session: AsyncSession, user_id: UUID) -> frozenset[UUID]:
    rows = await session.scalars(select(UserSiteRow.site_id).where(UserSiteRow.user_id == user_id))
    return frozenset(rows)


async def _revoke_sessions(session: AsyncSession, user_id: UUID) -> None:
    await session.execute(delete(SessionRow).where(SessionRow.user_id == user_id))


def _managed(row: UserRow, site_ids: list[UUID]) -> ManagedUser:
    return ManagedUser(
        id=row.id,
        email=row.email,
        display_name=row.display_name,
        role=Role(row.role),
        site_ids=tuple(sorted(site_ids)),
        is_active=row.is_active,
        must_change_password=row.must_change_password,
        last_login_at=row.last_login_at,
        created_at=row.created_at,
    )


def _password_matches(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _hash(token: str) -> bytes:
    return hashlib.sha256(token.encode()).digest()


def _user_view(row: UserRow, site_ids: frozenset[UUID]) -> UserView:
    return UserView(row.id, row.email, Role(row.role), row.display_name, site_ids, row.must_change_password)
