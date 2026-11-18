from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, Request

from sadu.modules.admin import api as admin
from sadu.modules.admin.api import AuthenticatedSession, Permission, UserView
from sadu.shared.errors import Forbidden, Unauthorized
from sadu.shared.web import Session

SESSION_COOKIE = "sadu_session"
CSRF_HEADER = "X-CSRF-Token"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


async def current_session(request: Request, session: Session) -> AuthenticatedSession:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise Unauthorized("not_authenticated")
    auth = await admin.authenticate(session, token)
    if request.method not in SAFE_METHODS and request.headers.get(CSRF_HEADER) != auth.csrf_token:
        raise Forbidden("csrf_failed")
    request.state.user_id = auth.user.id
    return auth


SignedIn = Annotated[AuthenticatedSession, Depends(current_session)]


def require(*permissions: Permission) -> Callable[[AuthenticatedSession], Awaitable[UserView]]:
    async def dependency(auth: SignedIn) -> UserView:
        if auth.user.must_change_password:
            raise Forbidden("password_change_required")
        if not all(auth.user.role.allows(permission) for permission in permissions):
            raise Forbidden("forbidden")
        return auth.user

    dependency.__name__ = "require_" + "_".join(p.value for p in permissions)
    return dependency


Staff = Annotated[UserView, Depends(require(Permission.READ))]
Inspector = Annotated[UserView, Depends(require(Permission.SURVEY))]
Expert = Annotated[UserView, Depends(require(Permission.REVIEW))]
SiteManager = Annotated[UserView, Depends(require(Permission.MANAGE_SITE))]
DeviceManager = Annotated[UserView, Depends(require(Permission.MANAGE_DEVICES))]
Exporter = Annotated[UserView, Depends(require(Permission.EXPORT))]
AssistantUser = Annotated[UserView, Depends(require(Permission.ASSIST))]
ModelManager = Annotated[UserView, Depends(require(Permission.MANAGE_MODELS))]
AuditReader = Annotated[UserView, Depends(require(Permission.READ_AUDIT))]
AuditExporter = Annotated[UserView, Depends(require(Permission.READ_AUDIT, Permission.EXPORT))]
Admin = Annotated[UserView, Depends(require(Permission.ADMINISTER))]
