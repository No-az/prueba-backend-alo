"""Lo que pide el enunciado, probado de punta a punta por HTTP.

- Una aprobación y un rechazo por cada política.
- El flujo completo: crear, consultar por id y encontrarla en el listado.
- El mismo flujo sobre una base creada con las migraciones reales.
"""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from app.infrastructure.settings import Settings
from app.main import create_app

ROOT = Path(__file__).resolve().parents[2]


def payload(product: str, **changes: int) -> dict[str, Any]:
    base = {
        "amount": 1_200_000,  # cuota de 100.000
        "monthly_income": 2_000_000,
        "employment_months": 24,
        "external_score": 750,
        "product": product,
    }
    return {**base, **changes}


@pytest.mark.parametrize(
    ("product", "changes", "policy"),
    [
        ("PHONE", {"external_score": 700, "employment_months": 12}, "Conservadora"),
        ("TWIST", {"external_score": 600, "employment_months": 0}, "Estándar"),
        ("CARD", {"external_score": 520, "monthly_income": 3_000_000}, "Agresiva"),
    ],
)
def test_each_policy_approves(
    client: TestClient, product: str, changes: dict[str, int], policy: str
) -> None:
    body = client.post("/applications", json=payload(product, **changes)).json()
    assert (body["status"], body["reasons"], body["policy"]["name"]) == ("APPROVED", [], policy)


@pytest.mark.parametrize(
    ("product", "changes", "expected_reasons"),
    [
        # PHONE: la cuota (1.000.000) supera el 25 % de 2.000.000
        ("PHONE", {"amount": 12_000_000}, ["INSTALLMENT_TOO_HIGH"]),
        # TWIST: score por debajo de 600
        ("TWIST", {"external_score": 599}, ["SCORE_BELOW_MINIMUM"]),
        # CARD: ni score >= 550, ni (score >= 500 e ingreso >= 3.000.000)
        (
            "CARD",
            {"external_score": 540, "monthly_income": 2_999_999},
            ["SCORE_BELOW_MINIMUM", "INCOME_BELOW_MINIMUM"],
        ),
    ],
)
def test_each_policy_rejects_with_its_reasons(
    client: TestClient, product: str, changes: dict[str, int], expected_reasons: list[str]
) -> None:
    body = client.post("/applications", json=payload(product, **changes)).json()
    assert body["status"] == "REJECTED"
    assert [reason["code"] for reason in body["reasons"]] == expected_reasons


def assert_full_flow(client: TestClient) -> None:
    created = client.post("/applications", json=payload("TWIST")).json()

    by_id = client.get(f"/applications/{created['id']}")
    listed = client.get("/applications", params={"status": "APPROVED", "product": "TWIST"})
    other = client.get("/applications", params={"status": "REJECTED"})

    assert by_id.json() == created
    assert created in listed.json()
    assert created not in other.json()


def test_full_flow(client: TestClient) -> None:
    assert_full_flow(client)


@pytest.fixture
def migrated_client(tmp_path: Path) -> Iterator[TestClient]:
    """App real contra un archivo SQLite creado con `alembic upgrade head`."""
    database_url = f"sqlite:///{tmp_path / 'e2e.db'}"
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    config.attributes["configure_logger"] = False
    command.upgrade(config, "head")

    with TestClient(create_app(Settings(database_url=database_url))) as client:
        yield client


def test_full_flow_on_a_migrated_database(migrated_client: TestClient) -> None:
    assert_full_flow(migrated_client)
