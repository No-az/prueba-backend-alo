import pytest

from app.application.use_cases import PublishPolicy, ReevaluateApplication, SubmitApplication
from app.domain.enums import Decision, EvaluationTrigger, Product
from app.domain.errors import InvalidPolicyError
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from tests.factories import StepClock, make_request

clock = StepClock()


def test_reevaluation_is_saved_and_updates_the_current_decision(
    uow: SqlAlchemyUnitOfWork,
) -> None:
    application = SubmitApplication(uow, clock)(
        make_request(product=Product.TWIST, external_score=620)
    )
    PublishPolicy(uow, clock)(Product.TWIST, "Estándar", {"min_score": 650})

    ReevaluateApplication(uow, clock)(application.id)

    with uow:
        stored = uow.applications.get(application.id)
        history = uow.applications.history(application.id)
    assert stored is not None
    assert stored.status is Decision.REJECTED
    assert stored.updated_at > stored.created_at
    assert [(e.trigger, e.policy_version, e.decision) for e in history] == [
        (EvaluationTrigger.CREATION, 1, Decision.APPROVED),
        (EvaluationTrigger.REEVALUATION, 2, Decision.REJECTED),
    ]


def test_publishing_increments_the_version(uow: SqlAlchemyUnitOfWork) -> None:
    publish = PublishPolicy(uow, clock)
    assert publish(Product.CARD, "Agresiva", {"min_score": 560}).version == 2
    assert publish(Product.CARD, "Agresiva", {"min_score": 570}).version == 3
    with uow:
        assert uow.policies.current_for(Product.CARD).version == 3


def test_invalid_policies_are_not_published(uow: SqlAlchemyUnitOfWork) -> None:
    with pytest.raises(InvalidPolicyError):
        PublishPolicy(uow, clock)(Product.CARD, "Agresiva", {"min_score": "alto"})
    with uow:
        assert uow.policies.current_for(Product.CARD).version == 1
