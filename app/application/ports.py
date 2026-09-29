"""Puertos: lo que los casos de uso necesitan del mundo exterior.

Los casos de uso dependen de estas interfaces, no de SQLAlchemy. Cambiar la
base de datos es escribir otro adaptador, sin tocar la lógica.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from types import TracebackType
from typing import Any, Protocol, Self
from uuid import UUID

from app.domain.applications import CreditApplication, Evaluation
from app.domain.enums import Decision, Product
from app.domain.policies import Policy


@dataclass(frozen=True, slots=True)
class ApplicationFilters:
    status: Decision | None = None
    product: Product | None = None
    limit: int = 100
    offset: int = 0


class ApplicationRepository(Protocol):
    def add(self, application: CreditApplication) -> None: ...

    def get(self, application_id: UUID) -> CreditApplication | None: ...

    def find(self, filters: ApplicationFilters) -> list[CreditApplication]: ...

    def record_reevaluation(self, application: CreditApplication) -> None:
        """Guarda la nueva evaluación y actualiza la decisión vigente."""
        ...

    def history(self, application_id: UUID) -> list[Evaluation]:
        """Todas las evaluaciones de la solicitud, de la más antigua a la más reciente."""
        ...


class PolicyRepository(Protocol):
    def current_for(self, product: Product) -> Policy:
        """Última versión publicada de la política del producto."""
        ...

    def publish(self, product: Product, name: str, rules: dict[str, Any], at: datetime) -> Policy:
        """Publica una versión nueva. Las anteriores nunca se modifican."""
        ...


class UnitOfWork(Protocol):
    """Agrupa los cambios de un caso de uso en una sola transacción."""

    @property
    def applications(self) -> ApplicationRepository: ...

    @property
    def policies(self) -> PolicyRepository: ...

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    def commit(self) -> None: ...


class Clock(Protocol):
    def now(self) -> datetime: ...
