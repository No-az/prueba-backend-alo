from app.domain.applications import CreditApplication
from app.domain.default_policies import default_catalog
from app.domain.enums import Decision, EvaluationTrigger, Product
from app.domain.value_objects import Money
from tests.factories import StepClock, make_request

catalog = default_catalog()


def test_submitting_evaluates_with_the_product_policy() -> None:
    request = make_request(product=Product.TWIST, external_score=550)
    at = StepClock().now()

    application = CreditApplication.submit(request, catalog.for_product(Product.TWIST), at)

    evaluation = application.latest_evaluation
    assert application.status is Decision.REJECTED
    assert evaluation.application_id == application.id
    assert evaluation.trigger is EvaluationTrigger.CREATION
    assert (evaluation.policy_name, evaluation.policy_version) == ("Estándar", 1)
    assert evaluation.installment == request.installment == Money.cop(100_000)
    assert application.created_at == application.updated_at == at
