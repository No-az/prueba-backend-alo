from decimal import Decimal

import pytest

from app.domain.errors import InvalidValueError
from app.domain.rules.atomic import (
    MaxInstallmentToIncome,
    MinEmploymentMonths,
    MinMonthlyIncome,
    MinScore,
)
from app.domain.rules.composite import AllOf, AnyOf
from app.domain.value_objects import Money, Score
from tests.factories import make_request


class TestMinScore:
    def test_passes_at_exact_minimum(self) -> None:
        assert MinScore(Score(700)).evaluate(make_request(external_score=700)).passed

    def test_fails_below_minimum_and_explains_why(self) -> None:
        result = MinScore(Score(700)).evaluate(make_request(external_score=699))
        assert not result.passed
        (reason,) = result.reasons
        assert reason.code == "SCORE_BELOW_MINIMUM"
        assert reason.details == {"minimum": 700, "actual": 699}


class TestMinEmploymentMonths:
    def test_passes_at_exact_minimum(self) -> None:
        assert MinEmploymentMonths(12).evaluate(make_request(employment_months=12)).passed

    def test_fails_below_minimum(self) -> None:
        result = MinEmploymentMonths(12).evaluate(make_request(employment_months=11))
        assert [r.code for r in result.reasons] == ["EMPLOYMENT_TOO_SHORT"]


class TestMaxInstallmentToIncome:
    def test_passes_when_installment_is_exactly_the_limit(self) -> None:
        # 12.000.000 / 12 = 1.000.000, exactamente el 25 % de 4.000.000
        request = make_request(amount=12_000_000, monthly_income=4_000_000)
        assert MaxInstallmentToIncome(Decimal("0.25")).evaluate(request).passed

    def test_fails_one_peso_over_the_limit(self) -> None:
        request = make_request(amount=12_000_012, monthly_income=4_000_000)
        result = MaxInstallmentToIncome(Decimal("0.25")).evaluate(request)
        (reason,) = result.reasons
        assert reason.code == "INSTALLMENT_TOO_HIGH"
        assert reason.details["max_ratio"] == "0.25"

    def test_exact_limit_with_non_round_numbers(self) -> None:
        # Monto no divisible por 12: con floats esta frontera es frágil.
        request = make_request(amount=3_000_003, monthly_income=1_000_001)
        assert MaxInstallmentToIncome(Decimal("0.25")).evaluate(request).passed

    @pytest.mark.parametrize("ratio", ["0", "-0.1", "1.01"])
    def test_ratio_must_be_between_zero_and_one(self, ratio: str) -> None:
        with pytest.raises(InvalidValueError):
            MaxInstallmentToIncome(Decimal(ratio))


class TestMinMonthlyIncome:
    def test_passes_at_exact_minimum(self) -> None:
        rule = MinMonthlyIncome(Money.cop(3_000_000))
        assert rule.evaluate(make_request(monthly_income=3_000_000)).passed

    def test_fails_below_minimum(self) -> None:
        rule = MinMonthlyIncome(Money.cop(3_000_000))
        result = rule.evaluate(make_request(monthly_income=2_999_999))
        assert [r.code for r in result.reasons] == ["INCOME_BELOW_MINIMUM"]


class TestAllOf:
    def test_collects_every_failure_instead_of_stopping_at_the_first(self) -> None:
        rule = AllOf((MinScore(Score(700)), MinEmploymentMonths(12)))
        result = rule.evaluate(make_request(external_score=600, employment_months=3))
        assert [r.code for r in result.reasons] == ["SCORE_BELOW_MINIMUM", "EMPLOYMENT_TOO_SHORT"]

    def test_passes_when_every_rule_passes(self) -> None:
        rule = AllOf((MinScore(Score(700)), MinEmploymentMonths(12)))
        assert rule.evaluate(make_request(external_score=700, employment_months=12)).passed

    def test_needs_at_least_one_rule(self) -> None:
        with pytest.raises(InvalidValueError):
            AllOf(())


class TestAnyOf:
    def test_passes_when_one_alternative_passes(self) -> None:
        rule = AnyOf((MinScore(Score(800)), MinEmploymentMonths(12)))
        assert rule.evaluate(make_request(external_score=100, employment_months=12)).passed

    def test_reports_reasons_from_every_alternative_without_duplicates(self) -> None:
        rule = AnyOf(
            (
                MinScore(Score(550)),
                AllOf((MinScore(Score(550)), MinMonthlyIncome(Money.cop(3_000_000)))),
            )
        )
        result = rule.evaluate(make_request(external_score=400, monthly_income=1_000_000))
        assert [r.code for r in result.reasons] == ["SCORE_BELOW_MINIMUM", "INCOME_BELOW_MINIMUM"]

    def test_needs_at_least_one_rule(self) -> None:
        with pytest.raises(InvalidValueError):
            AnyOf(())


def test_rules_describe_themselves_in_config_format() -> None:
    rule = AnyOf(
        (
            MinScore(Score(550)),
            AllOf((MaxInstallmentToIncome(Decimal("0.35")), MinMonthlyIncome(Money.cop(10)))),
        )
    )
    assert rule.to_config() == {
        "any_of": [
            {"min_score": 550},
            {"all_of": [{"max_installment_to_income": "0.35"}, {"min_monthly_income": 10}]},
        ]
    }
