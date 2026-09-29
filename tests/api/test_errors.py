from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.main import create_app
from tests.factories import StepClock

VALID = {
    "amount": 1_200_000,
    "monthly_income": 2_500_000,
    "employment_months": 18,
    "external_score": 720,
    "product": "PHONE",
}


def test_not_found_uses_problem_details(client: TestClient) -> None:
    application_id = uuid4()
    response = client.get(f"/applications/{application_id}")

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json() == {
        "type": "about:blank",
        "title": "Solicitud no encontrada",
        "status": 404,
        "instance": f"/applications/{application_id}",
        "detail": f"No existe una solicitud con id {application_id}",
    }


def test_validation_errors_name_the_field_without_echoing_the_value(client: TestClient) -> None:
    response = client.post("/applications", json={**VALID, "monthly_income": "secreto"})

    assert response.status_code == 422
    body = response.json()
    assert body["title"] == "Datos inválidos"
    assert [e["field"] for e in body["errors"]] == ["body.monthly_income"]
    assert "secreto" not in response.text


def test_unknown_route_is_a_problem_too(client: TestClient) -> None:
    response = client.get("/nope")
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"


def test_wrong_method_is_405(client: TestClient) -> None:
    assert client.delete(f"/applications/{uuid4()}").status_code == 405


@pytest.fixture
def broken_client(session_factory: sessionmaker[Session], engine: Engine) -> Iterator[TestClient]:
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP TABLE evaluations")
    app = create_app(session_factory=session_factory, clock=StepClock())
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


def test_unexpected_errors_do_not_leak_internals(broken_client: TestClient) -> None:
    response = broken_client.post("/applications", json=VALID)

    assert response.status_code == 500
    assert response.json()["detail"] == "Ocurrió un error inesperado."
    assert "evaluations" not in response.text
    assert "Traceback" not in response.text


def test_missing_policy_is_503(client: TestClient, engine: Engine) -> None:
    with engine.begin() as connection:
        connection.exec_driver_sql("DELETE FROM policy_versions WHERE product = 'PHONE'")

    response = client.post("/applications", json=VALID)

    assert response.status_code == 503
    assert response.json()["title"] == "Política no disponible"
