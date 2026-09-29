"""Casos de uso: orquestan el dominio y los puertos. No saben nada de HTTP ni de SQL."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.application.errors import ApplicationNotFoundError
from app.application.ports import ApplicationFilters, Clock, UnitOfWork
from app.domain.applications import CreditApplication, Evaluation
from app.domain.entities import CreditRequest
from app.domain.enums import Product
from app.domain.policies import Policy


class SubmitApplication:
    """Evalúa una solicitud con la política vigente de su producto y la guarda."""

    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    def __call__(self, request: CreditRequest) -> CreditApplication:
        with self._uow as uow:
            policy = uow.policies.current_for(request.product)
            application = CreditApplication.submit(request, policy, self._clock.now())
            uow.applications.add(application)
            uow.commit()
        return application


class GetApplication:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def __call__(self, application_id: UUID) -> CreditApplication:
        with self._uow as uow:
            application = uow.applications.get(application_id)
        if application is None:
            raise ApplicationNotFoundError(application_id)
        return application


class ListApplications:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def __call__(self, filters: ApplicationFilters) -> list[CreditApplication]:
        with self._uow as uow:
            return uow.applications.find(filters)


class GetEvaluationHistory:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def __call__(self, application_id: UUID) -> list[Evaluation]:
        with self._uow as uow:
            if uow.applications.get(application_id) is None:
                raise ApplicationNotFoundError(application_id)
            return uow.applications.history(application_id)


class ReevaluateApplication:
    """Vuelve a evaluar una solicitud con la política vigente (útil si cambian umbrales)."""

    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    def __call__(self, application_id: UUID) -> CreditApplication:
        with self._uow as uow:
            application = uow.applications.get(application_id)
            if application is None:
                raise ApplicationNotFoundError(application_id)
            policy = uow.policies.current_for(application.request.product)
            reevaluated = application.reevaluate(policy, self._clock.now())
            uow.applications.record_reevaluation(reevaluated)
            uow.commit()
        return reevaluated


class PublishPolicy:
    """Publica una versión nueva de la política de un producto."""

    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    def __call__(self, product: Product, name: str, rules: dict[str, Any]) -> Policy:
        with self._uow as uow:
            policy = uow.policies.publish(product, name, rules, self._clock.now())
            uow.commit()
        return policy
