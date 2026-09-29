"""Reglas del enunciado, con énfasis en los bordes exactos de cada umbral."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.domain.default_policies import default_catalog
from app.domain.enums import Decision, Product
from app.domain.errors import DomainError, PolicyNotFoundError
from app.domain.policies import PolicyCatalog
from tests.factories import make_request

catalog = default_catalog()


def decide(product: Product, **fields: int) -> tuple[Decision, list[str]]:
    outcome = catalog.for_product(product).evaluate(make_request(product=product, **fields))
    return outcome.decision, [reason.code for reason in outcome.reasons]


class TestPhoneConservative:
    """score >= 700 AND employment_months >= 12 AND cuota <= 25 % del ingreso."""

    def test_approves_when_every_condition_holds(self) -> None:
        assert decide(Product.PHONE, external_score=700, employment_months=12) == (
            Decision.APPROVED,
            [],
        )

    @pytest.mark.parametrize(
        ("fields", "expected"),
        [
            ({"external_score": 699}, ["SCORE_BELOW_MINIMUM"]),
            ({"employment_months": 11}, ["EMPLOYMENT_TOO_SHORT"]),
            ({"amount": 6_000_012, "monthly_income": 2_000_000}, ["INSTALLMENT_TOO_HIGH"]),
            (
                {"external_score": 300, "employment_months": 0, "amount": 50_000_000},
                ["SCORE_BELOW_MINIMUM", "EMPLOYMENT_TOO_SHORT", "INSTALLMENT_TOO_HIGH"],
            ),
        ],
    )
    def test_rejects_and_lists_every_reason(
        self, fields: dict[str, int], expected: list[str]
    ) -> None:
        assert decide(Product.PHONE, **fields) == (Decision.REJECTED, expected)

    def test_installment_exactly_at_25_percent_is_approved(self) -> None:
        # 6.000.000 / 12 = 500.000 = 25 % de 2.000.000
        decision, _ = decide(Product.PHONE, amount=6_000_000, monthly_income=2_000_000)
        assert decision is Decision.APPROVED


class TestTwistStandard:
    """score >= 600 AND cuota <= 35 % del ingreso. La antigüedad no importa."""

    def test_approves_without_looking_at_employment(self) -> None:
        decision, _ = decide(Product.TWIST, external_score=600, employment_months=0)
        assert decision is Decision.APPROVED

    def test_rejects_below_600(self) -> None:
        assert decide(Product.TWIST, external_score=599) == (
            Decision.REJECTED,
            ["SCORE_BELOW_MINIMUM"],
        )

    def test_installment_exactly_at_35_percent_is_approved(self) -> None:
        # 8.400.000 / 12 = 700.000 = 35 % de 2.000.000
        decision, _ = decide(Product.TWIST, amount=8_400_000, monthly_income=2_000_000)
        assert decision is Decision.APPROVED

    def test_rejects_installment_over_35_percent(self) -> None:
        assert decide(Product.TWIST, amount=8_400_012, monthly_income=2_000_000) == (
            Decision.REJECTED,
            ["INSTALLMENT_TOO_HIGH"],
        )


class TestCardAggressive:
    """score >= 550 OR (score >= 500 AND ingreso >= 3.000.000). La cuota no importa."""

    def test_approves_with_score_550_even_with_a_huge_installment(self) -> None:
        decision, _ = decide(Product.CARD, external_score=550, amount=500_000_000)
        assert decision is Decision.APPROVED

    @pytest.mark.parametrize(
        ("score", "income", "expected"),
        [
            (549, 3_000_000, Decision.APPROVED),
            (500, 3_000_000, Decision.APPROVED),
            (500, 2_999_999, Decision.REJECTED),
            (499, 10_000_000, Decision.REJECTED),
        ],
    )
    def test_high_income_alternative(self, score: int, income: int, expected: Decision) -> None:
        decision, _ = decide(Product.CARD, external_score=score, monthly_income=income)
        assert decision is expected

    def test_rejection_explains_both_alternatives(self) -> None:
        assert decide(Product.CARD, external_score=520, monthly_income=2_000_000) == (
            Decision.REJECTED,
            ["SCORE_BELOW_MINIMUM", "INCOME_BELOW_MINIMUM"],
        )


class TestCatalog:
    def test_every_product_has_a_policy(self) -> None:
        for product in Product:
            assert catalog.for_product(product).product is product

    def test_policy_names_and_versions(self) -> None:
        names = {p: (catalog.for_product(p).name, catalog.for_product(p).version) for p in Product}
        assert names == {
            Product.PHONE: ("Conservadora", 1),
            Product.TWIST: ("Estándar", 1),
            Product.CARD: ("Agresiva", 1),
        }

    def test_missing_product_raises_a_domain_error(self) -> None:
        with pytest.raises(PolicyNotFoundError):
            PolicyCatalog([]).for_product(Product.CARD)

    def test_a_policy_refuses_requests_for_other_products(self) -> None:
        with pytest.raises(DomainError):
            catalog.for_product(Product.PHONE).evaluate(make_request(product=Product.CARD))


# Propiedades que deben cumplirse para cualquier solicitud, no solo para los
# ejemplos de arriba: un mejor perfil nunca debería empeorar la decisión.
requests = st.fixed_dictionaries(
    {
        "amount": st.integers(1, 200_000_000),
        "monthly_income": st.integers(1, 50_000_000),
        "employment_months": st.integers(0, 600),
        "external_score": st.integers(0, 1000),
        "product": st.sampled_from(Product),
    }
)


def _approved(fields: dict[str, int]) -> bool:
    request = make_request(**fields)  # type: ignore[arg-type]
    return catalog.for_product(request.product).evaluate(request).decision is Decision.APPROVED


@given(requests, st.integers(0, 1000))
def test_a_higher_score_never_turns_an_approval_into_a_rejection(
    fields: dict[str, int], bonus: int
) -> None:
    better = {**fields, "external_score": min(1000, fields["external_score"] + bonus)}
    if _approved(fields):
        assert _approved(better)


@given(requests, st.integers(0, 50_000_000))
def test_more_income_never_turns_an_approval_into_a_rejection(
    fields: dict[str, int], raise_: int
) -> None:
    if _approved(fields):
        assert _approved({**fields, "monthly_income": fields["monthly_income"] + raise_})


@given(requests, st.integers(0, 199_999_999))
def test_asking_for_less_never_turns_an_approval_into_a_rejection(
    fields: dict[str, int], discount: int
) -> None:
    smaller = {**fields, "amount": max(1, fields["amount"] - discount)}
    if _approved(fields):
        assert _approved(smaller)
