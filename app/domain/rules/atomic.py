"""Reglas simples: cada una revisa una sola condición y explica por qué falla."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.domain.entities import CreditRequest
from app.domain.errors import InvalidValueError
from app.domain.rules.base import RejectionReason, RuleResult
from app.domain.value_objects import Money, Score


@dataclass(frozen=True, slots=True)
class MinScore:
    minimum: Score

    def evaluate(self, request: CreditRequest) -> RuleResult:
        actual = request.external_score
        if actual >= self.minimum:
            return RuleResult.ok()
        return RuleResult.rejected(
            RejectionReason(
                code="SCORE_BELOW_MINIMUM",
                message=f"El score {actual.value} es menor al mínimo de {self.minimum.value}",
                details={"minimum": self.minimum.value, "actual": actual.value},
            )
        )

    def to_config(self) -> dict[str, Any]:
        return {"min_score": self.minimum.value}


@dataclass(frozen=True, slots=True)
class MinEmploymentMonths:
    minimum: int

    def __post_init__(self) -> None:
        if self.minimum < 0:
            raise InvalidValueError("La antigüedad mínima no puede ser negativa")

    def evaluate(self, request: CreditRequest) -> RuleResult:
        actual = request.employment_months
        if actual >= self.minimum:
            return RuleResult.ok()
        return RuleResult.rejected(
            RejectionReason(
                code="EMPLOYMENT_TOO_SHORT",
                message=(
                    f"La antigüedad laboral de {actual} meses es menor a los "
                    f"{self.minimum} meses requeridos"
                ),
                details={"minimum": self.minimum, "actual": actual},
            )
        )

    def to_config(self) -> dict[str, Any]:
        return {"min_employment_months": self.minimum}


@dataclass(frozen=True, slots=True)
class MaxInstallmentToIncome:
    """La cuota mensual no puede superar una proporción del ingreso."""

    max_ratio: Decimal

    def __post_init__(self) -> None:
        if not Decimal(0) < self.max_ratio <= Decimal(1):
            raise InvalidValueError("La proporción máxima debe estar entre 0 y 1")

    def evaluate(self, request: CreditRequest) -> RuleResult:
        # Se compara cuota <= ingreso * proporción: la multiplicación es exacta,
        # mientras que dividir cuota / ingreso puede introducir redondeos.
        limit = request.monthly_income.times(self.max_ratio)
        if request.installment <= limit:
            return RuleResult.ok()
        percentage = (self.max_ratio * 100).normalize()
        return RuleResult.rejected(
            RejectionReason(
                code="INSTALLMENT_TOO_HIGH",
                message=(
                    f"La cuota de {request.installment} supera el {percentage:f} % "
                    f"del ingreso mensual ({limit})"
                ),
                details={
                    "max_ratio": str(self.max_ratio),
                    "actual_ratio": str(request.installment_ratio.rounded()),
                    "installment": str(request.installment.rounded().amount),
                    "max_installment": str(limit.rounded().amount),
                },
            )
        )

    def to_config(self) -> dict[str, Any]:
        return {"max_installment_to_income": str(self.max_ratio)}


@dataclass(frozen=True, slots=True)
class MinMonthlyIncome:
    minimum: Money

    def evaluate(self, request: CreditRequest) -> RuleResult:
        actual = request.monthly_income
        if actual >= self.minimum:
            return RuleResult.ok()
        return RuleResult.rejected(
            RejectionReason(
                code="INCOME_BELOW_MINIMUM",
                message=f"El ingreso mensual de {actual} es menor al mínimo de {self.minimum}",
                details={
                    "minimum": str(self.minimum.rounded().amount),
                    "actual": str(actual.rounded().amount),
                },
            )
        )

    def to_config(self) -> dict[str, Any]:
        return {"min_monthly_income": int(self.minimum.amount)}
