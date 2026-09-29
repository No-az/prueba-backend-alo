from typing import Any

import pytest
from fastapi.testclient import TestClient


def create(client: TestClient, product: str, score: int) -> dict[str, Any]:
    payload = {
        "amount": 1_200_000,
        "monthly_income": 2_500_000,
        "employment_months": 18,
        "external_score": score,
        "product": product,
    }
    body: dict[str, Any] = client.post("/applications", json=payload).json()
    return body


@pytest.fixture
def created(client: TestClient) -> list[dict[str, Any]]:
    return [
        create(client, "PHONE", 800),  # aprobada
        create(client, "PHONE", 100),  # rechazada
        create(client, "TWIST", 800),  # aprobada
        create(client, "TWIST", 100),  # rechazada
        create(client, "CARD", 800),  # aprobada
    ]


def ids(response: Any) -> list[str]:
    assert response.status_code == 200
    return [item["id"] for item in response.json()]


def test_lists_everything_newest_first(client: TestClient, created: list[dict[str, Any]]) -> None:
    assert ids(client.get("/applications")) == [a["id"] for a in reversed(created)]


def test_filters_by_status_and_product(client: TestClient, created: list[dict[str, Any]]) -> None:
    response = client.get("/applications", params={"status": "APPROVED", "product": "TWIST"})
    assert ids(response) == [created[2]["id"]]


def test_filters_by_status_only(client: TestClient, created: list[dict[str, Any]]) -> None:
    response = client.get("/applications", params={"status": "REJECTED"})
    assert ids(response) == [created[3]["id"], created[1]["id"]]


def test_filters_by_product_only(client: TestClient, created: list[dict[str, Any]]) -> None:
    response = client.get("/applications", params={"product": "PHONE"})
    assert ids(response) == [created[1]["id"], created[0]["id"]]


def test_no_matches_is_an_empty_list(client: TestClient) -> None:
    assert client.get("/applications", params={"product": "CARD"}).json() == []


def test_limit_and_offset(client: TestClient, created: list[dict[str, Any]]) -> None:
    newest_first = [a["id"] for a in reversed(created)]
    response = client.get("/applications", params={"limit": 2, "offset": 1})
    assert ids(response) == newest_first[1:3]


@pytest.mark.parametrize(
    "params",
    [{"status": "PENDING"}, {"product": "LOAN"}, {"limit": 0}, {"limit": 101}, {"offset": -1}],
)
def test_invalid_filters_are_422(client: TestClient, params: dict[str, Any]) -> None:
    assert client.get("/applications", params=params).status_code == 422
