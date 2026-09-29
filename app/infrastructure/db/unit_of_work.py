from __future__ import annotations

from types import TracebackType
from typing import Self

from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.repositories import (
    SqlAlchemyApplicationRepository,
    SqlAlchemyPolicyRepository,
)


class SqlAlchemyUnitOfWork:
    """Una transacción por caso de uso: o se guarda todo, o no se guarda nada."""

    applications: SqlAlchemyApplicationRepository
    policies: SqlAlchemyPolicyRepository

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def __enter__(self) -> Self:
        self._session = self._session_factory()
        self.policies = SqlAlchemyPolicyRepository(self._session)
        self.applications = SqlAlchemyApplicationRepository(self._session, self.policies)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        # Lo que no se confirmó explícitamente con commit() se descarta.
        self._session.rollback()
        self._session.close()

    def commit(self) -> None:
        self._session.commit()
