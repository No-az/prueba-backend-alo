from uuid import uuid4

from fastapi.testclient import TestClient

VALID = {
    "amount": 1_200_000,
    "monthly_income": 2_500_000,
    "employment_months": 18,
    "external_score": 650,
    "product": "PHONE",
}


def test_history_of_a_new_application_has_one_evaluation(client: TestClient) -> None:
    created = client.post("/applications", json=VALID).json()

    response = client.get(f"/applications/{created['id']}/evaluations")

    assert response.status_code == 200
    (evaluation,) = response.json()
    assert evaluation["trigger"] == "CREATION"
    assert evaluation["status"] == created["status"] == "REJECTED"
    assert evaluation["reasons"] == created["reasons"]
    assert evaluation["policy"] == {"name": "Conservadora", "version": 1}
    assert evaluation["evaluated_at"] == created["created_at"]


def test_history_of_unknown_application_is_404(client: TestClient) -> None:
    assert client.get(f"/applications/{uuid4()}/evaluations").status_code == 404
