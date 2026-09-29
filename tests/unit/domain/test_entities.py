from decimal import Decimal

import pytest

from app.domain.errors import InvalidValueError
from app.domain.value_objects import Money
from tests.factories import make_request


def test_installment_is_amount_over_twelve_months() -> None:
    request = make_request(amount=1_200_000)
    assert request.installment == Money.cop(100_000)


def test_installment_ratio_against_income() -> None:
    request = make_request(amount=1_200_000, monthly_income=400_000)
    assert request.installment_ratio.value == Decimal("0.25")


@pytest.mark.parametrize(
    "overrides",
    [{"amount": 0}, {"monthly_income": 0}, {"employment_months": -1}],
)
def test_rejects_requests_that_make_no_sense(overrides: dict[str, int]) -> None:
    with pytest.raises(InvalidValueError):
        make_request(**overrides)  # type: ignore[arg-type]
