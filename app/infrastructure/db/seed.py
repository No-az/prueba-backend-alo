from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.default_policies import DEFAULT_POLICY_CONFIGS
from app.infrastructure.db.orm_models import PolicyVersionRow


def seed_default_policies(session: Session) -> None:
    """Publica la versión 1 de cada política si todavía no existe.

    En producción lo hace la primera migración; esto sirve para bases creadas
    sin Alembic, como la base en memoria de los tests.
    """
    existing = set(session.scalars(select(PolicyVersionRow.product)))
    now = datetime.now(UTC)
    for product, config in DEFAULT_POLICY_CONFIGS.items():
        if product.value not in existing:
            session.add(
                PolicyVersionRow(
                    product=product.value,
                    version=1,
                    name=config["name"],
                    rules=config["rules"],
                    created_at=now,
                )
            )
    session.commit()
