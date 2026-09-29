"""Tablas de la base de datos.

Son un detalle de infraestructura: el dominio nunca las ve. Los mappers
traducen entre estas filas y las entidades del dominio.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, BigInteger, CheckConstraint, ForeignKey, String, UniqueConstraint
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
