"""Combinadores: permiten armar políticas completas a partir de reglas simples."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain.entities import CreditRequest
from app.domain.errors import InvalidValueError
from app.domain.rules.base import RejectionReason, Rule, RuleResult


def _unique(reasons: list[RejectionReason]) -> tuple[RejectionReason, ...]:
    seen: list[RejectionReason] = []
    for reason in reasons:
        if reason not in seen:
            seen.append(reason)
    return tuple(seen)


@dataclass(frozen=True, slots=True)
class AllOf:
    """Aprueba solo si todas las reglas pasan.

    Evalúa todas (no se detiene en la primera que falla) para que el rechazo
    traiga la lista completa de motivos.
    """

    rules: tuple[Rule, ...]

    def __post_init__(self) -> None:
        if not self.rules:
            raise InvalidValueError("all_of necesita al menos una regla")

    def evaluate(self, request: CreditRequest) -> RuleResult:
        results = [rule.evaluate(request) for rule in self.rules]
        if all(result.passed for result in results):
            return RuleResult.ok()
        return RuleResult.rejected(*_unique([r for result in results for r in result.reasons]))

    def to_config(self) -> dict[str, Any]:
        return {"all_of": [rule.to_config() for rule in self.rules]}


@dataclass(frozen=True, slots=True)
class AnyOf:
    """Aprueba si al menos una alternativa pasa.

    Si ninguna pasa, el rechazo incluye los motivos de todas las alternativas.
    """

    rules: tuple[Rule, ...]

    def __post_init__(self) -> None:
        if not self.rules:
            raise InvalidValueError("any_of necesita al menos una regla")

    def evaluate(self, request: CreditRequest) -> RuleResult:
        results = [rule.evaluate(request) for rule in self.rules]
        if any(result.passed for result in results):
            return RuleResult.ok()
        return RuleResult.rejected(*_unique([r for result in results for r in result.reasons]))

    def to_config(self) -> dict[str, Any]:
        return {"any_of": [rule.to_config() for rule in self.rules]}
