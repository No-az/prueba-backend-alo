"""Comprueba con EXPLAIN QUERY PLAN que el listado usa los índices.

Si alguien cambia el ORDER BY o los filtros sin ajustar los índices, SQLite
volvería a ordenar en memoria ("USE TEMP B-TREE") y este test lo detecta.
"""

import pytest
from sqlalchemy import Engine, text

LIST_QUERY = "SELECT id FROM applications {where} ORDER BY created_at DESC, id DESC LIMIT 20"


def query_plan(engine: Engine, where: str) -> str:
    with engine.connect() as connection:
        rows = connection.execute(text("EXPLAIN QUERY PLAN " + LIST_QUERY.format(where=where)))
        return " | ".join(row[-1] for row in rows)


@pytest.mark.parametrize(
    ("where", "index"),
    [
        (
            "WHERE status = 'APPROVED' AND product = 'TWIST'",
            "ix_applications_status_product_created",
        ),
        ("WHERE status = 'REJECTED'", "ix_applications_status_created"),
        ("WHERE product = 'TWIST'", "ix_applications_product_created"),
        ("", "ix_applications_created"),
    ],
)
def test_listing_uses_an_index_and_does_not_sort_in_memory(
    engine: Engine, where: str, index: str
) -> None:
    plan = query_plan(engine, where)
    assert index in plan
    assert "TEMP B-TREE" not in plan


def test_history_lookup_uses_an_index(engine: Engine) -> None:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "EXPLAIN QUERY PLAN SELECT id FROM evaluations "
                "WHERE application_id = x'00' ORDER BY evaluated_at DESC"
            )
        )
        plan = " | ".join(row[-1] for row in rows)
    assert "ix_evaluations_application_evaluated" in plan
