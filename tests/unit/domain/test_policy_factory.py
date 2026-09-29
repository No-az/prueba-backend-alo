from typing import Any

import pytest

from app.domain.default_policies import DEFAULT_POLICY_CONFIGS
from app.domain.errors import InvalidPolicyError
from app.domain.rules.factory import build_rule


@pytest.mark.parametrize("product", list(DEFAULT_POLICY_CONFIGS))
def test_config_survives_a_round_trip(product: str) -> None:
    config = DEFAULT_POLICY_CONFIGS[product]["rules"]  # type: ignore[index]
    assert build_rule(config).to_config() == config


@pytest.mark.parametrize(
    "config",
    [
        {},
        {"min_score": 700, "min_employment_months": 12},
        {"unknown_rule": 1},
        {"min_score": "700"},
        {"min_score": True},
        {"min_score": 2000},
        {"max_installment_to_income": 0.25},
        {"max_installment_to_income": "abc"},
        {"max_installment_to_income": "1.5"},
        {"all_of": []},
        {"all_of": {"min_score": 1}},
        {"any_of": [{"min_score": 1}, {"nope": 1}]},
        "min_score",
    ],
)
def test_rejects_invalid_configs(config: Any) -> None:
    with pytest.raises(InvalidPolicyError):
        build_rule(config)
