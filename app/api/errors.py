"""Errores HTTP con formato RFC 7807 (application/problem+json).

Todas las respuestas de error tienen la misma forma, y ninguna expone trazas,
SQL ni detalles internos: eso queda solo en los logs.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.rate_limit import RateLimitExceededError
from app.application.errors import ApplicationNotFoundError
from app.domain.errors import DomainError, PolicyNotFoundError

logger = logging.getLogger("app.errors")

PROBLEM_JSON = "application/problem+json"


def problem(
    request: Request,
    status: int,
    title: str,
    detail: str | None = None,
    headers: dict[str, str] | None = None,
    **extra: Any,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": "about:blank",
        "title": title,
        "status": status,
        "instance": request.url.path,
    }
    if detail:
        body["detail"] = detail
    body.update(extra)
    return JSONResponse(body, status_code=status, media_type=PROBLEM_JSON, headers=headers)


async def _not_found(request: Request, exc: Exception) -> JSONResponse:
    return problem(request, 404, "Solicitud no encontrada", str(exc))


async def _policy_missing(request: Request, exc: Exception) -> JSONResponse:
    # Es un problema de configuración nuestro, no del cliente.
    logger.error("Política no disponible: %s", exc)
    return problem(request, 503, "Política no disponible", "Intenta de nuevo más tarde.")


async def _domain_error(request: Request, exc: Exception) -> JSONResponse:
    return problem(request, 422, "Solicitud inválida", str(exc))


async def _validation_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    # Solo el campo y el motivo: no se devuelve el valor enviado.
    errors = [
        {"field": ".".join(str(part) for part in error["loc"]), "message": error["msg"]}
        for error in exc.errors()
    ]
    return problem(request, 422, "Datos inválidos", "Revisa los campos indicados.", errors=errors)


async def _http_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    return problem(
        request,
        exc.status_code,
        _TITLES.get(exc.status_code, "Error"),
        str(exc.detail) if exc.detail else None,
        headers=dict(exc.headers) if exc.headers else None,
    )


async def _too_many_requests(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RateLimitExceededError)
    return problem(
        request,
        429,
        "Demasiadas peticiones",
        f"Espera {exc.retry_after} segundos antes de intentar de nuevo.",
        headers={"Retry-After": str(exc.retry_after)},
    )


async def _unexpected(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Error inesperado en %s %s", request.method, request.url.path)
    return problem(request, 500, "Error interno", "Ocurrió un error inesperado.")


_TITLES = {404: "No encontrado", 405: "Método no permitido"}


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApplicationNotFoundError, _not_found)
    app.add_exception_handler(PolicyNotFoundError, _policy_missing)
    app.add_exception_handler(DomainError, _domain_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(RateLimitExceededError, _too_many_requests)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(Exception, _unexpected)
