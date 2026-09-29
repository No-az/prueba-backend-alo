from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.orm import Session, sessionmaker

from app.api.errors import register_error_handlers
from app.api.rate_limit import RateLimiter
from app.api.routers import applications
from app.api.schemas import HealthResponse
from app.application.ports import Clock
from app.infrastructure.clock import SystemClock
from app.infrastructure.db.engine import make_engine, make_session_factory
from app.infrastructure.settings import Settings, get_settings


def create_app(
    settings: Settings | None = None,
    *,
    session_factory: sessionmaker[Session] | None = None,
    clock: Clock | None = None,
) -> FastAPI:
    """Arma la aplicación. Los tests pasan su propia base y su propio reloj.

    El esquema lo crean las migraciones de Alembic (alembic upgrade head), no la
    aplicación al arrancar.
    """
    settings = settings or get_settings()
    engine = None
    if session_factory is None:
        engine = make_engine(settings.database_url)
        session_factory = make_session_factory(engine)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        if engine is not None:
            engine.dispose()

    app = FastAPI(
        title="Credit Evaluation Service",
        description="Evalúa solicitudes de crédito según la política de cada producto.",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.session_factory = session_factory
    app.state.clock = clock or SystemClock()
    app.state.rate_limiter = RateLimiter(settings)

    @app.get("/health", response_model=HealthResponse, tags=["health"])
    def health() -> HealthResponse:
        return HealthResponse(status="ok")

    app.include_router(applications.router)
    register_error_handlers(app)
    return app


app = create_app()
