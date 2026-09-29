from __future__ import annotations

from dataclasses import dataclass

from app.domain.enums import Product
from app.domain.errors import InvalidValueError
from app.domain.value_objects import InstallmentRatio, Money, Score

# El enunciado fija el plazo: cuota = monto / 12.
INSTALLMENT_TERM_MONTHS = 12


@dataclass(frozen=True, slots=True)
class CreditRequest:
    """Lo que el solicitante pide y la información con la que se evalúa."""

    amount: Money
    monthly_income: Money
    employment_months: int
    external_score: Score
    product: Product

    def __post_init__(self) -> None:
        if self.amount.amount <= 0:
            raise InvalidValueError("El monto solicitado debe ser mayor que cero")
        if self.monthly_income.amount <= 0:
            raise InvalidValueError("El ingreso mensual debe ser mayor que cero")
        if isinstance(self.employment_months, bool) or not isinstance(self.employment_months, int):
            raise TypeError("La antigüedad laboral debe ser un número entero de meses")
        if self.employment_months < 0:
            raise InvalidValueError("La antigüedad laboral no puede ser negativa")

    @property
    def installment(self) -> Money:
        return self.amount.divided_by(INSTALLMENT_TERM_MONTHS)

    @property
    def installment_ratio(self) -> InstallmentRatio:
        return InstallmentRatio.between(self.installment, self.monthly_income)
