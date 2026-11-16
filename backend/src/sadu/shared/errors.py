from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from sadu.shared.i18n import translate

PROBLEM_BASE_URL = "https://sadu.example/problems/"
PROBLEM_MEDIA_TYPE = "application/problem+json"

log = structlog.get_logger()


class SaduError(Exception):
    status = 400

    def __init__(self, code: str, *, status: int | None = None, **params: Any) -> None:
        super().__init__(code)
        self.code = code
        self.params = params
        if status is not None:
            self.status = status


class NotFound(SaduError):
    status = 404


class Conflict(SaduError):
    status = 409


class Forbidden(SaduError):
    status = 403


class Unauthorized(SaduError):
    status = 401


class TooManyRequests(SaduError):
    status = 429

    def __init__(self, code: str, *, retry_after_s: int) -> None:
        super().__init__(code, retry_after_s=retry_after_s)
        self.retry_after_s = retry_after_s


def problem_response(
    request: Request,
    *,
    status: int,
    code: str,
    params: dict[str, Any] | None = None,
    field_errors: list[dict[str, str]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    lang = _preferred_language(request)
    body: dict[str, Any] = {
        "type": PROBLEM_BASE_URL + code.replace("_", "-"),
        "title": translate(f"problem.{code}.title", lang, **(params or {})),
        "status": status,
        "detail": translate(f"problem.{code}.detail", lang, **(params or {})),
        "instance": request.url.path,
        "code": code,
        "request_id": getattr(request.state, "request_id", None),
    }
    if field_errors:
        body["errors"] = field_errors
    return JSONResponse(body, status_code=status, media_type=PROBLEM_MEDIA_TYPE, headers=headers)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(SaduError)
    async def handle_sadu_error(request: Request, exc: SaduError) -> JSONResponse:
        headers = {"Retry-After": str(exc.retry_after_s)} if isinstance(exc, TooManyRequests) else None
        return problem_response(request, status=exc.status, code=exc.code, params=exc.params, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        field_errors = [
            {"field": ".".join(str(part) for part in err["loc"][1:]), "message": err["msg"]}
            for err in exc.errors()
        ]
        return problem_response(request, status=422, code="validation_failed", field_errors=field_errors)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = "not_found" if exc.status_code == 404 else "http_error"
        return problem_response(request, status=exc.status_code, code=code)

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled_error", path=request.url.path)
        return problem_response(request, status=500, code="internal_error")


def _preferred_language(request: Request) -> str:
    header = request.headers.get("accept-language", "")
    return "en" if header.lower().startswith("en") else "ar"
