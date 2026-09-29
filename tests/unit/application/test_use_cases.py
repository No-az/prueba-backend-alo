from uuid import uuid4

import pytest

from app.application.errors import ApplicationNotFoundError
from app.application.ports import ApplicationFilters
from app.application.use_cases import (
    GetApplication,
    GetEvaluationHistory,
    ListApplications,
    SubmitApplication,
)
from app.domain.enums import Decision, Product
from tests.factories import StepClock, make_request
from tests.fakes import FakeUnitOfWork


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def test_submit_evaluates_saves_and_commits(uow: FakeUnitOfWork) -> None:
    application = SubmitApplication(uow, StepClock())(
        make_request(product=Product.CARD, external_score=560)
    )

    assert application.status is Decision.APPROVED
    assert uow.applications.items == {application.id: application}
    assert uow.commits == 1


def test_get_returns_the_saved_application(uow: FakeUnitOfWork) -> None:
    saved = SubmitApplication(uow, StepClock())(make_request())
    assert GetApplication(uow)(saved.id) == saved


def test_get_unknown_application_raises(uow: FakeUnitOfWork) -> None:
    with pytest.raises(ApplicationNotFoundError):
        GetApplication(uow)(uuid4())


def test_list_applies_the_filters(uow: FakeUnitOfWork) -> None:
    submit = SubmitApplication(uow, StepClock())
    approved = submit(make_request(product=Product.TWIST, external_score=800))
    submit(make_request(product=Product.TWIST, external_score=100))

    found = ListApplications(uow)(ApplicationFilters(status=Decision.APPROVED))

    assert found == [approved]


def test_history_of_unknown_application_raises(uow: FakeUnitOfWork) -> None:
    with pytest.raises(ApplicationNotFoundError):
        GetEvaluationHistory(uow)(uuid4())
