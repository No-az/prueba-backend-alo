from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Select, func, select, update
from sqlalchemy.orm import Session

from app.application.ports import ApplicationFilters
from app.domain.applications import CreditApplication, Evaluation
from app.domain.enums import Product
from app.domain.errors import PolicyNotFoundError
from app.domain.policies import Policy
from app.infrastructure.db import mappers
from app.infrastructure.db.orm_models import ApplicationRow, EvaluationRow, PolicyVersionRow


class SqlAlchemyPolicyRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def current_for(self, product: Product) -> Policy:
        row = self._session.scalars(
            select(PolicyVersionRow)
            .where(PolicyVersionRow.product == product.value)
            .order_by(PolicyVersionRow.version.desc())
            .limit(1)
        ).first()
        if row is None:
            raise PolicyNotFoundError(f"No hay política publicada para {product}")
        return Policy.from_config(
            product=Product(row.product), name=row.name, version=row.version, rules=row.rules
        )

    def publish(self, product: Product, name: str, rules: dict[str, Any], at: datetime) -> Policy:
        latest = self._session.scalar(
            select(func.max(PolicyVersionRow.version)).where(
                PolicyVersionRow.product == product.value
            )
        )
        # Construirla primero valida la configuración antes de guardar nada.
        policy = Policy.from_config(
            product=product, name=name, version=(latest or 0) + 1, rules=rules
        )
        self._session.add(
            PolicyVersionRow(
                product=product.value,
                version=policy.version,
                name=name,
                rules=policy.rule.to_config(),
                created_at=at,
            )
        )
        self._session.flush()
        return policy

    def id_of(self, product: Product, version: int) -> int:
        policy_id = self._session.scalar(
            select(PolicyVersionRow.id).where(
                PolicyVersionRow.product == product.value, PolicyVersionRow.version == version
            )
        )
        if policy_id is None:
            raise PolicyNotFoundError(f"No existe la versión {version} de la política de {product}")
        return policy_id


class SqlAlchemyApplicationRepository:
    def __init__(self, session: Session, policies: SqlAlchemyPolicyRepository) -> None:
        self._session = session
        self._policies = policies

    def add(self, application: CreditApplication) -> None:
        self._session.add(mappers.application_to_row(application))
        self._add_evaluation(application)

    def get(self, application_id: UUID) -> CreditApplication | None:
        row = self._session.get(ApplicationRow, application_id)
        if row is None:
            return None
        latest = self._latest_evaluations([row.id])
        return mappers.application_from_row(row, latest[row.id])

    def find(self, filters: ApplicationFilters) -> list[CreditApplication]:
        query: Select[tuple[ApplicationRow]] = select(ApplicationRow)
        if filters.status is not None:
            query = query.where(ApplicationRow.status == filters.status.value)
        if filters.product is not None:
            query = query.where(ApplicationRow.product == filters.product.value)
        query = (
            query.order_by(ApplicationRow.created_at.desc(), ApplicationRow.id.desc())
            .limit(filters.limit)
            .offset(filters.offset)
        )
        rows = list(self._session.scalars(query))
        latest = self._latest_evaluations([row.id for row in rows])
        return [mappers.application_from_row(row, latest[row.id]) for row in rows]

    def record_reevaluation(self, application: CreditApplication) -> None:
        self._add_evaluation(application)
        self._session.execute(
            update(ApplicationRow)
            .where(ApplicationRow.id == application.id)
            .values(status=application.status.value, updated_at=application.updated_at)
        )

    def history(self, application_id: UUID) -> list[Evaluation]:
        results = self._session.execute(
            select(EvaluationRow, PolicyVersionRow)
            .join(PolicyVersionRow, PolicyVersionRow.id == EvaluationRow.policy_version_id)
            .where(EvaluationRow.application_id == application_id)
            .order_by(EvaluationRow.evaluated_at)
        ).all()
        return [mappers.evaluation_from_row(evaluation, policy) for evaluation, policy in results]

    def _add_evaluation(self, application: CreditApplication) -> None:
        evaluation = application.latest_evaluation
        policy_id = self._policies.id_of(application.request.product, evaluation.policy_version)
        self._session.add(mappers.evaluation_to_row(evaluation, policy_id))
        self._session.flush()

    def _latest_evaluations(self, application_ids: list[UUID]) -> dict[UUID, Evaluation]:
        """Última evaluación de cada solicitud, en una sola consulta (sin N+1)."""
        if not application_ids:
            return {}
        position = (
            func.row_number()
            .over(
                partition_by=EvaluationRow.application_id,
                order_by=EvaluationRow.evaluated_at.desc(),
            )
            .label("position")
        )
        ranked = (
            select(EvaluationRow.id, position)
            .where(EvaluationRow.application_id.in_(application_ids))
            .subquery()
        )
        results = self._session.execute(
            select(EvaluationRow, PolicyVersionRow)
            .join(ranked, ranked.c.id == EvaluationRow.id)
            .join(PolicyVersionRow, PolicyVersionRow.id == EvaluationRow.policy_version_id)
            .where(ranked.c.position == 1)
        ).all()
        return {
            evaluation.application_id: mappers.evaluation_from_row(evaluation, policy)
            for evaluation, policy in results
        }
