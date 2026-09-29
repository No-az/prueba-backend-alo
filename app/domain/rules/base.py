from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.domain.entities import CreditRequest

RuleConfig = Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class RejectionReason:
    """Por qué una regla no se cumplió.

    `code` es estable (el frontend o un analista pueden depender de él), `message`
    es para humanos y `details` lleva los números concretos de la decisión.
    """

    code: str
    message: str
    details: Mapping[str, str | int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RuleResult:
    passed: bool
    reasons: tuple[RejectionReason, ...] = ()

    @classmethod
    def ok(cls) -> RuleResult:
        return cls(passed=True)

    @classmethod
    def rejected(cls, *reasons: RejectionReason) -> RuleResult:
        return cls(passed=False, reasons=reasons)


class Rule(Protocol):
    def evaluate(self, request: CreditRequest) -> RuleResult: ...

    def to_config(self) -> dict[str, Any]:
        """Devuelve la regla en el mismo formato con el que se configura."""
        ...
