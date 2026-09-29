from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.cli import main as cli

TWIST = {
    "amount": 1_200_000,
    "monthly_income": 2_500_000,
    "employment_months": 0,
    "external_score": 620,
    "product": "TWIST",
}


def test_reevaluate_without_changes_keeps_the_decision_and_logs_it(client: TestClient) -> None:
    created = client.post("/applications", json=TWIST).json()

    response = client.post(f"/applications/{created['id']}/reevaluate")

    assert response.status_code == 200
    assert response.json()["status"] == "APPROVED"
    history = client.get(f"/applications/{created['id']}/evaluations").json()
    assert [e["trigger"] for e in history] == ["CREATION", "REEVALUATION"]


def test_reevaluate_applies_a_newly_published_policy(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    created = client.post("/applications", json=TWIST).json()
    exit_code = cli(
        [
            "publish-policy",
            "TWIST",
            "--name",
            "Estándar",
            "--rules",
            '{"all_of": [{"min_score": 650}, {"max_installment_to_income": "0.35"}]}',
        ],
        session_factory=session_factory,
    )
    assert exit_code == 0

    reevaluated = client.post(f"/applications/{created['id']}/reevaluate").json()

    assert (created["status"], reevaluated["status"]) == ("APPROVED", "REJECTED")
    assert reevaluated["policy"] == {"name": "Estándar", "version": 2}
    assert [r["code"] for r in reevaluated["reasons"]] == ["SCORE_BELOW_MINIMUM"]
    assert client.get(f"/applications/{created['id']}").json() == reevaluated
    listed = client.get("/applications", params={"status": "REJECTED"}).json()
    assert [a["id"] for a in listed] == [created["id"]]


def test_reevaluate_unknown_application_is_404(client: TestClient) -> None:
    assert client.post(f"/applications/{uuid4()}/reevaluate").status_code == 404


def test_cli_refuses_invalid_rules(session_factory: sessionmaker[Session]) -> None:
    args = ["publish-policy", "CARD", "--name", "Agresiva", "--rules", '{"min_score": "x"}']
    assert cli(args, session_factory=session_factory) == 1
    assert cli([*args[:-1], "no es json"], session_factory=session_factory) == 1
