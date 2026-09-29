"""Adaptadores en memoria para probar los casos de uso sin base de datos.

Que existan (y sean tan cortos) es la prueba de que los casos de uso dependen
de los puertos y no de SQLAlchemy.
"""

from __future__ import annotations

from datetime import datetime
from types import TracebackType
from typing import Any, Self
from uuid import UUID

from app.application.ports import ApplicationFilters
from app.domain.applications import CreditApplication, Evaluation
from app.domain.default_policies import default_catalog
from app.domain.enums import Product
from app.domain.policies import Policy, PolicyCatalog


class InMemoryApplicationRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, CreditApplication] = {}
        self.evaluations: list[Evaluation] = []

    def add(self, application: CreditApplication) -> None:
        self.items[application.id] = application
        self.evaluations.append(application.latest_evaluation)

    def record_reevaluation(self, application: CreditApplication) -> None:
        self.items[application.id] = application
        self.evaluations.append(application.latest_evaluation)

    def history(self, application_id: UUID) -> list[Evaluation]:
        return [e for e in self.evaluations if e.application_id == application_id]

    def get(self, application_id: UUID) -> CreditApplication | None:
        return self.items.get(application_id)

    def find(self, filters: ApplicationFilters) -> list[CreditApplication]:
        matches = [
            a
            for a in sorted(self.items.values(), key=lambda a: a.created_at, reverse=True)
            if filters.status in (None, a.status) and filters.product in (None, a.request.product)
        ]
        return matches[filters.offset : filters.offset + filters.limit]


class InMemoryPolicyRepository:
    def __init__(self, catalog: PolicyCatalog | None = None) -> None:
        self._catalog = catalog or default_catalog()
        self._published: dict[Product, Policy] = {}

    def current_for(self, product: Product) -> Policy:
        return self._published.get(product) or self._catalog.for_product(product)

    def publish(self, product: Product, name: str, rules: dict[str, Any], at: datetime) -> Policy:
        version = self.current_for(product).version + 1
        policy = Policy.from_config(product=product, name=name, version=version, rules=rules)
        self._published[product] = policy
        return policy


class FakeUnitOfWork:
    def __init__(self) -> None:
        self._applications = InMemoryApplicationRepository()
        self._policies = InMemoryPolicyRepository()
        self.commits = 0

    @property
    def applications(self) -> InMemoryApplicationRepository:
        return self._applications

    @property
    def policies(self) -> InMemoryPolicyRepository:
        return self._policies

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    def commit(self) -> None:
        self.commits += 1
