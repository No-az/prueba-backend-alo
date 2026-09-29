"""Protege el historial de evaluaciones contra cambios y borrados.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-29

Una evaluación explica por qué se tomó una decisión en un momento dado. Si se
pudiera editar, dejaría de servir como auditoría. La aplicación nunca hace
UPDATE ni DELETE sobre esta tabla, y con estos triggers la base tampoco lo
permite aunque alguien lo intente por fuera de la aplicación.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "sqlite":
        return
    op.execute(
        "CREATE TRIGGER evaluations_no_update BEFORE UPDATE ON evaluations "
        "BEGIN SELECT RAISE(ABORT, 'evaluations is append-only'); END"
    )
    op.execute(
        "CREATE TRIGGER evaluations_no_delete BEFORE DELETE ON evaluations "
        "BEGIN SELECT RAISE(ABORT, 'evaluations is append-only'); END"
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "sqlite":
        return
    op.execute("DROP TRIGGER IF EXISTS evaluations_no_delete")
    op.execute("DROP TRIGGER IF EXISTS evaluations_no_update")
