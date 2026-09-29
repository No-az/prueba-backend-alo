"""Solicitudes de crédito y sus evaluaciones."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from uuid import UUID, uuid4

from app.domain.entities import CreditRequest
from app.domain.enums import Decision, EvaluationTrigger
from app.domain.policies import Policy
from app.domain.rules.base import RejectionReason
from app.domain.value_objects import InstallmentRatio, Money


@dataclass(frozen=True, slots=True)
class Evaluation:
    """El resultado de aplicar una versión de política a una solicitud.

    Guarda la versión exacta de la política y los números con los que se
    decidió, para poder explicar cualquier decisión tiempo después.
    """

    id: UUID
    application_id: UUID
    decision: Decision
    reasons: tuple[RejectionReason, ...]
    policy_name: str
    policy_version: int
    installment: Money
    installment_ratio: InstallmentRatio
    trigger: EvaluationTrigger
    evaluated_at: datetime

    @classmethod
    def run(
        cls,
        *,
        application_id: UUID,
        request: CreditRequest,
        policy: Policy,
        trigger: EvaluationTrigger,
        at: datetime,
    ) -> Evaluation:
        outcome = policy.evaluate(request)
        return cls(
            id=uuid4(),
            application_id=application_id,
            decision=outcome.decision,
            reasons=outcome.reasons,
            policy_name=policy.name,
            policy_version=policy.version,
            installment=request.installment,
            installment_ratio=request.installment_ratio,
            trigger=trigger,
            evaluated_at=at,
        )


@dataclass(frozen=True, slots=True)
class CreditApplication:
    id: UUID
    request: CreditRequest
    created_at: datetime
    latest_evaluation: Evaluation

    @classmethod
    def submit(cls, request: CreditRequest, policy: Policy, at: datetime) -> CreditApplication:
        application_id = uuid4()
        evaluation = Evaluation.run(
            application_id=application_id,
            request=request,
            policy=policy,
            trigger=EvaluationTrigger.CREATION,
            at=at,
        )
        return cls(id=application_id, request=request, created_at=at, latest_evaluation=evaluation)

    def reevaluate(self, policy: Policy, at: datetime) -> CreditApplication:
        """Vuelve a evaluar los mismos datos con otra versión de la política.

        No modifica nada: devuelve la solicitud con una evaluación nueva, y la
        anterior queda en el historial.
        """
        evaluation = Evaluation.run(
            application_id=self.id,
            request=self.request,
            policy=policy,
            trigger=EvaluationTrigger.REEVALUATION,
            at=at,
        )
        return replace(self, latest_evaluation=evaluation)

    @property
    def status(self) -> Decision:
        return self.latest_evaluation.decision

    @property
    def updated_at(self) -> datetime:
        return self.latest_evaluation.evaluated_at
