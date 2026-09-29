from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.settings import Settings
from app.main import create_app
from tests.factories import StepClock

VALID = {
    "amount": 1_200_000,
    "monthly_income": 2_500_000,
    "employment_months": 18,
    "external_score": 720,
    "product": "PHONE",
}


def client_with(session_factory: sessionmaker[Session], **settings: object) -> TestClient:
    app = create_app(
        Settings(rate_limit_write="2/minute", rate_limit_read="3/minute", **settings),  # type: ignore[arg-type]
        session_factory=session_factory,
        clock=StepClock(),
    )
    return TestClient(app)


@pytest.fixture
def limited(session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    with client_with(session_factory) as client:
        yield client


def test_writes_over_the_limit_get_429_with_retry_after(limited: TestClient) -> None:
    assert [limited.post("/applications", json=VALID).status_code for _ in range(3)] == [
        201,
        201,
        429,
    ]
    response = limited.post("/applications", json=VALID)
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["title"] == "Demasiadas peticiones"
    assert 0 < int(response.headers["Retry-After"]) <= 60


def test_reads_and_writes_have_separate_budgets(limited: TestClient) -> None:
    for _ in range(2):
        limited.post("/applications", json=VALID)
    assert [limited.get("/applications").status_code for _ in range(4)] == [200, 200, 200, 429]


def test_health_is_never_limited(limited: TestClient) -> None:
    assert {limited.get("/health").status_code for _ in range(10)} == {200}


def test_limits_can_be_turned_off(session_factory: sessionmaker[Session]) -> None:
    with client_with(session_factory, rate_limit_enabled=False) as client:
        assert {client.post("/applications", json=VALID).status_code for _ in range(5)} == {201}
