from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, Request

from sadu.modules.admin import api as admin
from sadu.modules.admin.api import Permission, UserView
from sadu.shared.errors import Forbidden, Unauthorized
from sadu.shared.web import Session

SESSION_COOKIE = "sadu_session"
CSRF_HEADER = "X-CSRF-Token"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def require(permission: Permission) -> Callable[[Request, Session], Awaitable[UserView]]:
    async def dependency(request: Request, session: Session) -> UserView:
        token = request.cookies.get(SESSION_COOKIE)
        if not token:
            raise Unauthorized("not_authenticated")
        auth = await admin.authenticate(session, token)
        if request.method not in SAFE_METHODS and request.headers.get(CSRF_HEADER) != auth.csrf_token:
            raise Forbidden("csrf_failed")
        if not auth.user.role.allows(permission):
            raise Forbidden("forbidden")
        request.state.user_id = auth.user.id
        return auth.user

    dependency.__name__ = f"require_{permission.value}"
    return dependency


Staff = Annotated[UserView, Depends(require(Permission.READ))]
Inspector = Annotated[UserView, Depends(require(Permission.SURVEY))]
Expert = Annotated[UserView, Depends(require(Permission.REVIEW))]
SiteManager = Annotated[UserView, Depends(require(Permission.MANAGE_SITE))]
Admin = Annotated[UserView, Depends(require(Permission.ADMINISTER))]
