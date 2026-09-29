"""Convierte la configuración de una política (JSON) en un árbol de reglas.

Formato: cada nodo es un objeto con una sola clave.

    {"any_of": [
        {"min_score": 550},
        {"all_of": [{"min_score": 500}, {"min_monthly_income": 3000000}]}
    ]}

Las proporciones se escriben como texto ("0.25") para no pasar por float.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from decimal import Decimal, InvalidOperation
from typing import Any

from app.domain.errors import InvalidPolicyError, InvalidValueError
from app.domain.rules.atomic import (
    MaxInstallmentToIncome,
    MinEmploymentMonths,
    MinMonthlyIncome,
    MinScore,
)
from app.domain.rules.base import Rule
from app.domain.rules.composite import AllOf, AnyOf
from app.domain.value_objects import Money, Score


def _as_int(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidPolicyError(f"Se esperaba un entero y llegó {value!r}")
    return value


def _as_decimal(value: Any) -> Decimal:
    if not isinstance(value, str):
        raise InvalidPolicyError(f"Las proporciones se escriben como texto, llegó {value!r}")
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise InvalidPolicyError(f"{value!r} no es un número válido") from exc


def _as_children(value: Any) -> tuple[Rule, ...]:
    if not isinstance(value, list):
        raise InvalidPolicyError("all_of / any_of esperan una lista de reglas")
    return tuple(build_rule(child) for child in value)


_BUILDERS: Mapping[str, Callable[[Any], Rule]] = {
    "min_score": lambda v: MinScore(Score(_as_int(v))),
    "min_employment_months": lambda v: MinEmploymentMonths(_as_int(v)),
    "max_installment_to_income": lambda v: MaxInstallmentToIncome(_as_decimal(v)),
    "min_monthly_income": lambda v: MinMonthlyIncome(Money.cop(_as_int(v))),
    "all_of": lambda v: AllOf(_as_children(v)),
    "any_of": lambda v: AnyOf(_as_children(v)),
}


def build_rule(config: Any) -> Rule:
    if not isinstance(config, Mapping) or len(config) != 1:
        raise InvalidPolicyError("Cada regla debe ser un objeto con exactamente una clave")
    ((kind, value),) = config.items()
    builder = _BUILDERS.get(kind)
    if builder is None:
        raise InvalidPolicyError(f"Tipo de regla desconocido: {kind!r}")
    try:
        return builder(value)
    except (InvalidValueError, TypeError) as exc:
        raise InvalidPolicyError(f"Configuración inválida en {kind!r}: {exc}") from exc
