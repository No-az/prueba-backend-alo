from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

VALID: dict[str, Any] = {
    "amount": 1_200_000,
    "monthly_income": 2_500_000,
    "employment_months": 18,
    "external_score": 720,
    "product": "PHONE",
}


def test_create_returns_the_decision_and_where_to_find_it(client: TestClient) -> None:
    response = client.post("/applications", json=VALID)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "APPROVED"
    assert body["reasons"] == []
    assert body["installment"] == "100000.00"
    assert body["installment_to_income"] == "0.0400"
    assert body["policy"] == {"name": "Conservadora", "version": 1}
    assert response.headers["Location"] == f"/applications/{body['id']}"


def test_rejection_includes_the_reasons(client: TestClient) -> None:
    response = client.post("/applications", json={**VALID, "external_score": 650})

    body = response.json()
    assert body["status"] == "REJECTED"
    assert body["reasons"] == [
        {
            "code": "SCORE_BELOW_MINIMUM",
            "message": "El score 650 es menor al mínimo de 700",
            "details": {"minimum": 700, "actual": 650},
        }
    ]


def test_created_application_can_be_read_back(client: TestClient) -> None:
    created = client.post("/applications", json=VALID).json()

    response = client.get(f"/applications/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_unknown_application_is_404(client: TestClient) -> None:
    assert client.get(f"/applications/{uuid4()}").status_code == 404


def test_non_uuid_id_is_422(client: TestClient) -> None:
    assert client.get("/applications/123").status_code == 422


@pytest.mark.parametrize(
    "change",
    [
        {"external_score": "720"},
        {"external_score": 720.0},
        {"amount": True},
        {"amount": 0},
        {"monthly_income": -1},
        {"employment_months": -1},
        {"external_score": 1001},
        {"amount": 10_000_000_001},
        {"product": "LOAN"},
        {"product": "phone"},
        {"is_admin": True},
    ],
)
def test_invalid_payloads_are_rejected(client: TestClient, change: dict[str, Any]) -> None:
    assert client.post("/applications", json={**VALID, **change}).status_code == 422


@pytest.mark.parametrize("missing", list(VALID))
def test_every_field_is_required(client: TestClient, missing: str) -> None:
    payload = {k: v for k, v in VALID.items() if k != missing}
    assert client.post("/applications", json=payload).status_code == 422
