import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sadu.modules.admin.infrastructure.orm import AuditLogRow, LlmCallRow, SessionRow, UserRow
from sadu.shared.errors import Conflict, TooManyRequests, Unauthorized

SESSION_LIFETIME = timedelta(hours=12)
MAX_FAILED_LOGINS = 5
LOCKOUT = timedelta(minutes=15)

_hasher = PasswordHasher()
_DUMMY_HASH = _hasher.hash(secrets.token_hex(16))


class Permission(StrEnum):
    READ = "read"
    SURVEY = "survey"
    REVIEW = "review"
    MANAGE_SITE = "manage_site"
    ADMINISTER = "administer"


class Role(StrEnum):
    INSPECTOR = "inspector"
    SITE_MANAGER = "site_manager"
    EXPERT = "expert"
    ADMIN = "admin"

    @property
    def permissions(self) -> frozenset[Permission]:
        return ROLE_PERMISSIONS[self]

    def allows(self, required: Permission) -> bool:
        return required in self.permissions


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.INSPECTOR: frozenset({Permission.READ, Permission.SURVEY}),
    Role.SITE_MANAGER: frozenset({Permission.READ, Permission.MANAGE_SITE}),
    Role.EXPERT: frozenset({Permission.READ, Permission.SURVEY, Permission.REVIEW}),
    Role.ADMIN: frozenset(Permission),
}


@dataclass(frozen=True)
class UserView:
    id: UUID
    email: str
    role: Role


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


async def create_user(session: AsyncSession, email: str, password: str, role: Role) -> UserView:
    email = _normalize_email(email)
    if await session.scalar(select(UserRow.id).where(UserRow.email == email)):
        raise Conflict("user_exists")
    row = UserRow(email=email, password_hash=_hasher.hash(password), role=role)
    session.add(row)
    await session.flush()
    return _user_view(row)


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

    user.failed_logins, user.locked_until = 0, None
    if _hasher.check_needs_rehash(user.password_hash):
        user.password_hash = _hasher.hash(password)
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    expires_at = now + SESSION_LIFETIME
    session.add(SessionRow(id_hash=_hash(token), user_id=user.id, csrf_token=csrf, expires_at=expires_at))
    await session.flush()
    return LoginResult(_user_view(user), token, csrf, expires_at)


async def authenticate(session: AsyncSession, session_token: str) -> AuthenticatedSession:
    now = datetime.now(UTC)
    row = await session.get(SessionRow, _hash(session_token))
    if row is None or row.expires_at <= now:
        raise Unauthorized("session_expired")
    user = await session.get(UserRow, row.user_id)
    if user is None:
        raise Unauthorized("session_expired")
    row.last_seen_at = now
    return AuthenticatedSession(_user_view(user), row.csrf_token)


async def logout(session: AsyncSession, session_token: str) -> None:
    await session.execute(delete(SessionRow).where(SessionRow.id_hash == _hash(session_token)))


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


def _password_matches(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _hash(token: str) -> bytes:
    return hashlib.sha256(token.encode()).digest()


def _user_view(row: UserRow) -> UserView:
    return UserView(row.id, row.email, Role(row.role))
