"""Crea las tablas y siembra las políticas iniciales del enunciado.

Revision ID: 0001
Revises:
Create Date: 2026-09-29

La migración no importa código de la aplicación a propósito: si mañana
cambian los modelos o las políticas por defecto, esta migración tiene que
seguir haciendo exactamente lo mismo que hizo el día que se escribió.
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PRODUCTS = "('PHONE', 'TWIST', 'CARD')"
DECISIONS = "('APPROVED', 'REJECTED')"

INITIAL_POLICIES = [
    {
        "product": "PHONE",
        "name": "Conservadora",
        "rules": {
            "all_of": [
                {"min_score": 700},
                {"min_employment_months": 12},
                {"max_installment_to_income": "0.25"},
            ]
        },
    },
    {
        "product": "TWIST",
        "name": "Estándar",
        "rules": {"all_of": [{"min_score": 600}, {"max_installment_to_income": "0.35"}]},
    },
    {
        "product": "CARD",
        "name": "Agresiva",
        "rules": {
            "any_of": [
                {"min_score": 550},
                {"all_of": [{"min_score": 500}, {"min_monthly_income": 3000000}]},
            ]
        },
    },
]


def upgrade() -> None:
    op.create_table(
        "applications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("monthly_income", sa.BigInteger(), nullable=False),
        sa.Column("employment_months", sa.Integer(), nullable=False),
        sa.Column("external_score", sa.Integer(), nullable=False),
        sa.Column("product", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(f"product IN {PRODUCTS}", name=op.f("ck_applications_product")),
        sa.CheckConstraint(f"status IN {DECISIONS}", name=op.f("ck_applications_status")),
        sa.CheckConstraint("amount > 0", name=op.f("ck_applications_amount")),
        sa.CheckConstraint("monthly_income > 0", name=op.f("ck_applications_monthly_income")),
        sa.CheckConstraint(
            "employment_months >= 0", name=op.f("ck_applications_employment_months")
        ),
        sa.CheckConstraint(
            "external_score BETWEEN 0 AND 1000", name=op.f("ck_applications_external_score")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_applications")),
    )
    policy_versions = op.create_table(
        "policy_versions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("product", sa.String(length=16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("rules", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(f"product IN {PRODUCTS}", name=op.f("ck_policy_versions_product")),
        sa.CheckConstraint("version >= 1", name=op.f("ck_policy_versions_version")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_policy_versions")),
        sa.UniqueConstraint("product", "version", name=op.f("uq_policy_versions_product")),
    )
    op.create_table(
        "evaluations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("policy_version_id", sa.Integer(), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("installment", sa.String(length=40), nullable=False),
        sa.Column("installment_ratio", sa.String(length=40), nullable=False),
        sa.Column("trigger", sa.String(length=16), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(f"decision IN {DECISIONS}", name=op.f("ck_evaluations_decision")),
        sa.CheckConstraint(
            "trigger IN ('CREATION', 'REEVALUATION')", name=op.f("ck_evaluations_trigger")
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name=op.f("fk_evaluations_application_id_applications"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["policy_version_id"],
            ["policy_versions.id"],
            name=op.f("fk_evaluations_policy_version_id_policy_versions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evaluations")),
    )

    now = datetime.now(UTC)
    op.bulk_insert(
        policy_versions,
        [{**policy, "version": 1, "created_at": now} for policy in INITIAL_POLICIES],
    )


def downgrade() -> None:
    op.drop_table("evaluations")
    op.drop_table("policy_versions")
    op.drop_table("applications")
