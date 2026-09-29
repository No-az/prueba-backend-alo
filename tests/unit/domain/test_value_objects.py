from decimal import Decimal

import pytest

from app.domain.errors import InvalidValueError
from app.domain.value_objects import InstallmentRatio, Money, Score


class TestMoney:
    def test_accepts_int_str_and_decimal(self) -> None:
        assert Money.cop(1000) == Money.cop("1000") == Money.cop(Decimal("1000"))

    @pytest.mark.parametrize("value", [0.1, True, None])
    def test_rejects_floats_and_other_types(self, value: object) -> None:
        with pytest.raises(TypeError):
            Money.cop(value)  # type: ignore[arg-type]

    def test_rejects_negative_amounts(self) -> None:
        with pytest.raises(InvalidValueError):
            Money.cop(-1)

    def test_rejects_non_finite_amounts(self) -> None:
        with pytest.raises(InvalidValueError):
            Money.cop("Infinity")

    def test_division_keeps_full_precision(self) -> None:
        installment = Money.cop(1000).divided_by(12)
        assert installment.amount == Decimal(1000) / 12
        assert installment.rounded() == Money.cop("83.33")

    @pytest.mark.parametrize("parts", [0, -3, True])
    def test_division_requires_positive_integer_parts(self, parts: int) -> None:
        with pytest.raises(InvalidValueError):
            Money.cop(1000).divided_by(parts)

    def test_arithmetic_and_ordering(self) -> None:
        assert Money.cop(100) + Money.cop(50) == Money.cop(150)
        assert Money.cop(1_000_000).times("0.25") == Money.cop(250_000)
        assert Money.cop(1) < Money.cop(2)

    def test_readable_representation(self) -> None:
        assert str(Money.cop(1000).divided_by(12)) == "83.33 COP"


class TestScore:
    @pytest.mark.parametrize("value", [0, 500, 1000])
    def test_accepts_values_in_range(self, value: int) -> None:
        assert Score(value).value == value

    @pytest.mark.parametrize("value", [-1, 1001])
    def test_rejects_values_out_of_range(self, value: int) -> None:
        with pytest.raises(InvalidValueError):
            Score(value)

    @pytest.mark.parametrize("value", ["700", 700.0, True])
    def test_rejects_non_integers(self, value: object) -> None:
        with pytest.raises(TypeError):
            Score(value)  # type: ignore[arg-type]


class TestInstallmentRatio:
    def test_is_installment_over_income(self) -> None:
        ratio = InstallmentRatio.between(Money.cop(250_000), Money.cop(1_000_000))
        assert ratio.value == Decimal("0.25")

    def test_rounds_for_display(self) -> None:
        ratio = InstallmentRatio.between(Money.cop(1), Money.cop(3))
        assert ratio.rounded() == Decimal("0.3333")

    def test_income_must_be_positive(self) -> None:
        with pytest.raises(InvalidValueError):
            InstallmentRatio.between(Money.cop(1), Money.cop(0))
