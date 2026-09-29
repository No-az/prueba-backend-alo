from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.application.ports import ApplicationFilters
from app.domain.applications import CreditApplication
from app.domain.enums import Decision, Product
from app.domain.errors import PolicyNotFoundError
from app.infrastructure.db.orm_models import PolicyVersionRow
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from tests.factories import StepClock, make_request

clock = StepClock()


def submit(uow: SqlAlchemyUnitOfWork, **fields: object) -> CreditApplication:
    request = make_request(**fields)  # type: ignore[arg-type]
    with uow:
        application = CreditApplication.submit(
            request, uow.policies.current_for(request.product), clock.now()
        )
        uow.applications.add(application)
        uow.commit()
    return application


def test_saves_and_reads_back_an_application_unchanged(uow: SqlAlchemyUnitOfWork) -> None:
    saved = submit(uow, product=Product.PHONE, external_score=650, employment_months=3)

    with uow:
        loaded = uow.applications.get(saved.id)

    assert loaded == saved
    assert loaded is not None
    assert loaded.created_at.tzinfo is not None
    assert [r.code for r in loaded.latest_evaluation.reasons] == [
        "SCORE_BELOW_MINIMUM",
        "EMPLOYMENT_TOO_SHORT",
    ]


def test_unknown_id_returns_none(uow: SqlAlchemyUnitOfWork) -> None:
    with uow:
        assert uow.applications.get(uuid4()) is None


def test_changes_are_discarded_without_commit(uow: SqlAlchemyUnitOfWork) -> None:
    request = make_request()
    with uow:
        application = CreditApplication.submit(
            request, uow.policies.current_for(request.product), clock.now()
        )
        uow.applications.add(application)

    with uow:
        assert uow.applications.get(application.id) is None


class TestFind:
    @pytest.fixture(autouse=True)
    def _applications(self, uow: SqlAlchemyUnitOfWork) -> None:
        submit(uow, product=Product.PHONE, external_score=800)  # aprobada
        submit(uow, product=Product.PHONE, external_score=100)  # rechazada
        submit(uow, product=Product.TWIST, external_score=800)  # aprobada
        submit(uow, product=Product.CARD, external_score=100)  # rechazada

    def _find(self, uow: SqlAlchemyUnitOfWork, **filters: object) -> list[CreditApplication]:
        with uow:
            return uow.applications.find(ApplicationFilters(**filters))  # type: ignore[arg-type]

    def test_without_filters_returns_everything_newest_first(
        self, uow: SqlAlchemyUnitOfWork
    ) -> None:
        found = self._find(uow)
        assert [a.request.product for a in found] == [
            Product.CARD,
            Product.TWIST,
            Product.PHONE,
            Product.PHONE,
        ]

    def test_filters_by_status_and_product(self, uow: SqlAlchemyUnitOfWork) -> None:
        found = self._find(uow, status=Decision.APPROVED, product=Product.PHONE)
        assert [(a.status, a.request.product) for a in found] == [
            (Decision.APPROVED, Product.PHONE)
        ]

    def test_filters_by_status_only(self, uow: SqlAlchemyUnitOfWork) -> None:
        assert {a.status for a in self._find(uow, status=Decision.REJECTED)} == {Decision.REJECTED}
        assert len(self._find(uow, status=Decision.REJECTED)) == 2

    def test_limit_and_offset(self, uow: SqlAlchemyUnitOfWork) -> None:
        everything = self._find(uow)
        assert self._find(uow, limit=2, offset=1) == everything[1:3]


class TestPolicies:
    def test_uses_the_latest_published_version(
        self, uow: SqlAlchemyUnitOfWork, session_factory: sessionmaker[Session]
    ) -> None:
        with session_factory() as session:
            session.add(
                PolicyVersionRow(
                    product="TWIST",
                    version=2,
                    name="Estándar",
                    rules={"all_of": [{"min_score": 650}]},
                    created_at=datetime.now(UTC),
                )
            )
            session.commit()

        with uow:
            policy = uow.policies.current_for(Product.TWIST)

        assert policy.version == 2
        assert policy.rule.to_config() == {"all_of": [{"min_score": 650}]}

    def test_missing_policy_is_a_domain_error(
        self, uow: SqlAlchemyUnitOfWork, session_factory: sessionmaker[Session]
    ) -> None:
        with session_factory() as session:
            session.query(PolicyVersionRow).filter_by(product="CARD").delete()
            session.commit()

        with uow, pytest.raises(PolicyNotFoundError):
            uow.policies.current_for(Product.CARD)
