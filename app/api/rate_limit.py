"""Límite de peticiones por IP (ventana deslizante).

Protege el servicio de abusos y de scripts que envían solicitudes en masa.
Usa la librería `limits` (la misma que hay debajo de slowapi) como una
dependencia de FastAPI, así cada ruta declara qué límite le aplica.

El almacenamiento es configurable: "memory://" sirve para una sola instancia;
con varias réplicas se usa uno compartido, por ejemplo "redis://redis:6379".
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable

from fastapi import Request
from limits import RateLimitItem, parse
from limits.storage import storage_from_string
from limits.strategies import MovingWindowRateLimiter

from app.infrastructure.settings import Settings


class RateLimitExceededError(Exception):
    def __init__(self, limit: RateLimitItem, retry_after: int) -> None:
        super().__init__(f"Se superó el límite de {limit}")
        self.limit = limit
        self.retry_after = retry_after


class RateLimiter:
    def __init__(self, settings: Settings) -> None:
        self.enabled = settings.rate_limit_enabled
        self._strategy = MovingWindowRateLimiter(
            storage_from_string(settings.rate_limit_storage_uri)
        )
        self._limits = {
            "write": parse(settings.rate_limit_write),
            "read": parse(settings.rate_limit_read),
        }

    def check(self, scope: str, client: str) -> None:
        if not self.enabled:
            return
        limit = self._limits[scope]
        if not self._strategy.hit(limit, scope, client):
            reset_at = self._strategy.get_window_stats(limit, scope, client).reset_time
            raise RateLimitExceededError(limit, max(1, math.ceil(reset_at - time.time())))


def _client_ip(request: Request) -> str:
    # Si el servicio queda detrás de un proxy, hay que configurar uvicorn con
    # --forwarded-allow-ips para que esta IP sea la real del cliente y no la del proxy.
    return request.client.host if request.client else "unknown"


def limit(scope: str) -> Callable[[Request], None]:
    def dependency(request: Request) -> None:
        limiter: RateLimiter = request.app.state.rate_limiter
        limiter.check(scope, _client_ip(request))

    return dependency


limit_writes = limit("write")
limit_reads = limit("read")
