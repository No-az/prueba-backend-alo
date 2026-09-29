"""Índices para filtrar y ordenar el listado de solicitudes.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-29

GET /applications filtra por estado y/o producto y ordena por fecha de
creación descendente. Cada combinación de filtros tiene un índice cuyo
prefijo coincide con el WHERE y cuyo final coincide con el ORDER BY.
Cuatro índices encarecen un poco cada INSERT; en un servicio donde se
consulta mucho más de lo que se crea, es un buen intercambio.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_applications_status_product_created",
        "applications",
        ["status", "product", "created_at", "id"],
    )
    op.create_index(
        "ix_applications_status_created", "applications", ["status", "created_at", "id"]
    )
    op.create_index(
        "ix_applications_product_created", "applications", ["product", "created_at", "id"]
    )
    op.create_index("ix_applications_created", "applications", ["created_at", "id"])
    op.create_index(
        "ix_evaluations_application_evaluated", "evaluations", ["application_id", "evaluated_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_evaluations_application_evaluated", table_name="evaluations")
    op.drop_index("ix_applications_created", table_name="applications")
    op.drop_index("ix_applications_product_created", table_name="applications")
    op.drop_index("ix_applications_status_created", table_name="applications")
    op.drop_index("ix_applications_status_product_created", table_name="applications")
