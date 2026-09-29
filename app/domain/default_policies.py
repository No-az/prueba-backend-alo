"""Políticas iniciales, tal como las define el enunciado de la prueba.

Son la versión 1 de cada producto. Cambiar un umbral más adelante es
publicar una versión nueva, no editar este archivo.
"""

from typing import Any

from app.domain.enums import Product
from app.domain.policies import Policy, PolicyCatalog

DEFAULT_POLICY_CONFIGS: dict[Product, dict[str, Any]] = {
    Product.PHONE: {
        "name": "Conservadora",
        "rules": {
            "all_of": [
                {"min_score": 700},
                {"min_employment_months": 12},
                {"max_installment_to_income": "0.25"},
            ]
        },
    },
    Product.TWIST: {
        "name": "Estándar",
        "rules": {
            "all_of": [
                {"min_score": 600},
                {"max_installment_to_income": "0.35"},
            ]
        },
    },
    Product.CARD: {
        "name": "Agresiva",
        "rules": {
            "any_of": [
                {"min_score": 550},
                {"all_of": [{"min_score": 500}, {"min_monthly_income": 3_000_000}]},
            ]
        },
    },
}


def default_policies() -> list[Policy]:
    return [
        Policy.from_config(product=product, name=cfg["name"], version=1, rules=cfg["rules"])
        for product, cfg in DEFAULT_POLICY_CONFIGS.items()
    ]


def default_catalog() -> PolicyCatalog:
    return PolicyCatalog(default_policies())
