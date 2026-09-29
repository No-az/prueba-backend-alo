"""Traducción entre filas de la base y entidades del dominio (capa anticorrupción).

Ni el dominio conoce las tablas ni las tablas conocen el dominio: todo cruce
pasa por aquí.
"""

from __future__ import annotations

from typing import Any

from app.domain.applications import CreditApplication, Evaluation
from app.domain.entities import CreditRequest
from app.domain.enums import Decision, EvaluationTrigger, Product
from app.domain.rules.base import RejectionReason
from app.domain.value_objects import InstallmentRatio, Money, Score
from app.infrastructure.db.orm_models import ApplicationRow, EvaluationRow, PolicyVersionRow


def _whole_pesos(money: Money) -> int:
    if money.amount != money.amount.to_integral_value():
        raise ValueError(f"Solo se guardan pesos enteros, llegó {money.amount}")
    return int(money.amount)


def reasons_to_json(reasons: tuple[RejectionReason, ...]) -> list[dict[str, Any]]:
    return [{"code": r.code, "message": r.message, "details": dict(r.details)} for r in reasons]


def reasons_from_json(data: list[dict[str, Any]]) -> tuple[RejectionReason, ...]:
    return tuple(
        RejectionReason(code=item["code"], message=item["message"], details=item["details"])
        for item in data
    )


def application_to_row(application: CreditApplication) -> ApplicationRow:
    request = application.request
    return ApplicationRow(
        id=application.id,
        amount=_whole_pesos(request.amount),
        monthly_income=_whole_pesos(request.monthly_income),
        employment_months=request.employment_months,
        external_score=request.external_score.value,
        product=request.product.value,
        status=application.status.value,
        created_at=application.created_at,
        updated_at=application.updated_at,
    )


def evaluation_to_row(evaluation: Evaluation, policy_version_id: int) -> EvaluationRow:
    return EvaluationRow(
        id=evaluation.id,
        application_id=evaluation.application_id,
        policy_version_id=policy_version_id,
        decision=evaluation.decision.value,
        reasons=reasons_to_json(evaluation.reasons),
        installment=evaluation.installment.amount,
        installment_ratio=evaluation.installment_ratio.value,
        trigger=evaluation.trigger.value,
        evaluated_at=evaluation.evaluated_at,
    )


def evaluation_from_row(row: EvaluationRow, policy: PolicyVersionRow) -> Evaluation:
    return Evaluation(
        id=row.id,
        application_id=row.application_id,
        decision=Decision(row.decision),
        reasons=reasons_from_json(row.reasons),
        policy_name=policy.name,
        policy_version=policy.version,
        installment=Money(row.installment),
        installment_ratio=InstallmentRatio(row.installment_ratio),
        trigger=EvaluationTrigger(row.trigger),
        evaluated_at=row.evaluated_at,
    )


def application_from_row(row: ApplicationRow, latest: Evaluation) -> CreditApplication:
    return CreditApplication(
        id=row.id,
        request=CreditRequest(
            amount=Money.cop(row.amount),
            monthly_income=Money.cop(row.monthly_income),
            employment_months=row.employment_months,
            external_score=Score(row.external_score),
            product=Product(row.product),
        ),
        created_at=row.created_at,
        latest_evaluation=latest,
    )
