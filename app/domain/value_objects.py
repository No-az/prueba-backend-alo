"""Value objects del dominio de crédito.

Son inmutables y se validan al construirse: si existe un `Money` o un `Score`,
su valor es válido. Las reglas de negocio trabajan con estos tipos y nunca con
enteros o floats sueltos.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.domain.errors import InvalidValueError

_CENTS = Decimal("0.01")


def _to_decimal(value: int | str | Decimal) -> Decimal:
    # float y bool quedan fuera a propósito: 0.1 + 0.2 no debería decidir un crédito.
    if isinstance(value, bool) or not isinstance(value, int | str | Decimal):
        raise TypeError(f"Se esperaba int, str o Decimal, no {type(value).__name__}")
    return Decimal(value)


@dataclass(frozen=True, slots=True, order=True)
class Money:
    """Cantidad no negativa de pesos colombianos (COP)."""

    amount: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            raise TypeError("Money.amount debe ser Decimal; usa Money.cop(...)")
        if not self.amount.is_finite():
            raise InvalidValueError("El monto debe ser un número finito")
        if self.amount < 0:
            raise InvalidValueError("El monto no puede ser negativo")

    @classmethod
    def cop(cls, value: int | str | Decimal) -> Money:
        return cls(_to_decimal(value))

    def __add__(self, other: Money) -> Money:
        return Money(self.amount + other.amount)

    def times(self, factor: int | str | Decimal) -> Money:
        return Money(self.amount * _to_decimal(factor))

    def divided_by(self, parts: int) -> Money:
        if isinstance(parts, bool) or not isinstance(parts, int) or parts <= 0:
            raise InvalidValueError("Solo se puede dividir en un número entero positivo de partes")
        return Money(self.amount / parts)

    def rounded(self) -> Money:
        """Redondea a centavos. Se usa solo para mostrar o guardar, nunca antes de comparar."""
        return Money(self.amount.quantize(_CENTS, rounding=ROUND_HALF_UP))

    def __str__(self) -> str:
        return f"{self.rounded().amount} COP"


@dataclass(frozen=True, slots=True, order=True)
class Score:
    """Score de riesgo entregado por un buró externo, en escala 0 a 1000."""

    MIN = 0
    MAX = 1000

    value: int

    def __post_init__(self) -> None:
        if isinstance(self.value, bool) or not isinstance(self.value, int):
            raise TypeError("El score debe ser un entero")
        if not self.MIN <= self.value <= self.MAX:
            raise InvalidValueError(f"El score debe estar entre {self.MIN} y {self.MAX}")


@dataclass(frozen=True, slots=True, order=True)
class InstallmentRatio:
    """Proporción del ingreso mensual que se va en la cuota (0.25 = 25 %)."""

    value: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.value, Decimal) or not self.value.is_finite():
            raise TypeError("InstallmentRatio.value debe ser un Decimal finito")
        if self.value < 0:
            raise InvalidValueError("La proporción no puede ser negativa")

    @classmethod
    def between(cls, installment: Money, monthly_income: Money) -> InstallmentRatio:
        if monthly_income.amount == 0:
            raise InvalidValueError("El ingreso mensual debe ser mayor que cero")
        return cls(installment.amount / monthly_income.amount)

    def rounded(self, places: int = 4) -> Decimal:
        return self.value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
