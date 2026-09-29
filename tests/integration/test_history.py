import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DatabaseError

from app.domain.applications import CreditApplication
from app.domain.enums import EvaluationTrigger
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from tests.factories import StepClock, make_request


def submit(uow: SqlAlchemyUnitOfWork) -> CreditApplication:
    request = make_request()
    with uow:
        application = CreditApplication.submit(
            request, uow.policies.current_for(request.product), StepClock().now()
        )
        uow.applications.add(application)
        uow.commit()
    return application


def test_history_starts_with_the_creation_evaluation(uow: SqlAlchemyUnitOfWork) -> None:
    application = submit(uow)

    with uow:
        history = uow.applications.history(application.id)

    assert history == [application.latest_evaluation]
    assert history[0].trigger is EvaluationTrigger.CREATION


@pytest.mark.parametrize(
    "statement",
    ["UPDATE evaluations SET decision = 'APPROVED'", "DELETE FROM evaluations"],
)
def test_the_database_refuses_to_rewrite_history(
    uow: SqlAlchemyUnitOfWork, engine: Engine, statement: str
) -> None:
    submit(uow)

    with pytest.raises(DatabaseError, match="append-only"), engine.begin() as connection:
        connection.execute(text(statement))
