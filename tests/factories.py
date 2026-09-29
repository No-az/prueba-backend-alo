from datetime import UTC, datetime, timedelta

from app.domain.entities import CreditRequest
from app.domain.enums import Product
from app.domain.value_objects import Money, Score


def make_request(
    *,
    amount: int = 1_200_000,
    monthly_income: int = 2_000_000,
    employment_months: int = 24,
    external_score: int = 750,
    product: Product = Product.PHONE,
) -> CreditRequest:
    """Solicitud válida por defecto; cada test cambia solo lo que le interesa."""
    return CreditRequest(
        amount=Money.cop(amount),
        monthly_income=Money.cop(monthly_income),
        employment_months=employment_months,
        external_score=Score(external_score),
        product=product,
    )


class StepClock:
    """Reloj de prueba: cada llamada avanza un segundo, así el orden es predecible."""

    def __init__(self, start: datetime | None = None) -> None:
        self._current = start or datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    def now(self) -> datetime:
        self._current += timedelta(seconds=1)
        return self._current
