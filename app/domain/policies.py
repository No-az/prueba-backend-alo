from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from app.domain.entities import CreditRequest
from app.domain.enums import Decision, Product
from app.domain.errors import DomainError, PolicyNotFoundError
from app.domain.rules.base import RejectionReason, Rule
from app.domain.rules.factory import build_rule


@dataclass(frozen=True, slots=True)
class PolicyOutcome:
    decision: Decision
    reasons: tuple[RejectionReason, ...]


@dataclass(frozen=True, slots=True)
class Policy:
    """Una versión concreta de la política de crédito de un producto."""

    product: Product
    name: str
    version: int
    rule: Rule

    @classmethod
    def from_config(
        cls, *, product: Product, name: str, version: int, rules: Mapping[str, Any]
    ) -> Policy:
        return cls(product=product, name=name, version=version, rule=build_rule(rules))

    def evaluate(self, request: CreditRequest) -> PolicyOutcome:
        if request.product is not self.product:
            raise DomainError(
                f"La política de {self.product} no puede evaluar una solicitud de {request.product}"
            )
        result = self.rule.evaluate(request)
        decision = Decision.APPROVED if result.passed else Decision.REJECTED
        return PolicyOutcome(decision=decision, reasons=result.reasons)


class PolicyCatalog:
    """Encuentra la política de cada producto con un diccionario, sin if/elif.

    Agregar un producto nuevo es agregar una entrada, no tocar este código.
    """

    def __init__(self, policies: Iterable[Policy]) -> None:
        self._by_product = {policy.product: policy for policy in policies}

    def for_product(self, product: Product) -> Policy:
        try:
            return self._by_product[product]
        except KeyError:
            raise PolicyNotFoundError(f"No hay política configurada para {product}") from None
