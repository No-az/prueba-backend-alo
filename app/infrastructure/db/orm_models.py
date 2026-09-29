"""Tablas de la base de datos.

Son un detalle de infraestructura: el dominio nunca las ve. Los mappers
traducen entre estas filas y las entidades del dominio.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    DDL,
    JSON,
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base, DecimalString, UTCDateTime

PRODUCTS = "('PHONE', 'TWIST', 'CARD')"
DECISIONS = "('APPROVED', 'REJECTED')"


class PolicyVersionRow(Base):
    __tablename__ = "policy_versions"
    __table_args__ = (
        UniqueConstraint("product", "version"),
        CheckConstraint(f"product IN {PRODUCTS}", name="product"),
        CheckConstraint("version >= 1", name="version"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product: Mapped[str] = mapped_column(String(16))
    version: Mapped[int]
    name: Mapped[str] = mapped_column(String(64))
    rules: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)


class ApplicationRow(Base):
    __tablename__ = "applications"
    __table_args__ = (
        CheckConstraint(f"product IN {PRODUCTS}", name="product"),
        CheckConstraint(f"status IN {DECISIONS}", name="status"),
        CheckConstraint("amount > 0", name="amount"),
        CheckConstraint("monthly_income > 0", name="monthly_income"),
        CheckConstraint("employment_months >= 0", name="employment_months"),
        CheckConstraint("external_score BETWEEN 0 AND 1000", name="external_score"),
        # Los índices siguen el orden del listado (más recientes primero) para que
        # filtrar y ordenar se resuelva con el índice, sin ordenar en memoria.
        Index("ix_applications_status_product_created", "status", "product", "created_at", "id"),
        Index("ix_applications_status_created", "status", "created_at", "id"),
        Index("ix_applications_product_created", "product", "created_at", "id"),
        Index("ix_applications_created", "created_at", "id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    amount: Mapped[int] = mapped_column(BigInteger)
    monthly_income: Mapped[int] = mapped_column(BigInteger)
    employment_months: Mapped[int]
    external_score: Mapped[int]
    product: Mapped[str] = mapped_column(String(16))
    # Decisión vigente. Se repite aquí (además del historial) para filtrar rápido.
    status: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)


class EvaluationRow(Base):
    __tablename__ = "evaluations"
    __table_args__ = (
        CheckConstraint(f"decision IN {DECISIONS}", name="decision"),
        CheckConstraint("trigger IN ('CREATION', 'REEVALUATION')", name="trigger"),
        Index("ix_evaluations_application_evaluated", "application_id", "evaluated_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="RESTRICT")
    )
    policy_version_id: Mapped[int] = mapped_column(
        ForeignKey("policy_versions.id", ondelete="RESTRICT")
    )
    decision: Mapped[str] = mapped_column(String(16))
    reasons: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    installment: Mapped[Decimal] = mapped_column(DecimalString)
    installment_ratio: Mapped[Decimal] = mapped_column(DecimalString)
    trigger: Mapped[str] = mapped_column(String(16))
    evaluated_at: Mapped[datetime] = mapped_column(UTCDateTime)


# El historial de evaluaciones es de solo inserción: la base misma rechaza
# UPDATE y DELETE. Se registra aquí para las bases creadas con create_all
# (tests); en las demás lo crea la migración 0003.
APPEND_ONLY_TRIGGERS = [
    """
    CREATE TRIGGER evaluations_no_update BEFORE UPDATE ON evaluations
    BEGIN SELECT RAISE(ABORT, 'evaluations is append-only'); END
    """,
    """
    CREATE TRIGGER evaluations_no_delete BEFORE DELETE ON evaluations
    BEGIN SELECT RAISE(ABORT, 'evaluations is append-only'); END
    """,
]
for _statement in APPEND_ONLY_TRIGGERS:
    event.listen(
        EvaluationRow.__table__,
        "after_create",
        DDL(_statement).execute_if(dialect="sqlite"),  # type: ignore[no-untyped-call]
    )
