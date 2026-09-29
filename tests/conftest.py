from collections.abc import Iterator

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.base import Base
from app.infrastructure.db.engine import make_engine, make_session_factory
from app.infrastructure.db.seed import seed_default_policies
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork


@pytest.fixture
def engine() -> Iterator[Engine]:
    """Base SQLite en memoria, nueva para cada test y con las políticas v1."""
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed_default_policies(session)
    yield engine
    engine.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return make_session_factory(engine)


@pytest.fixture
def uow(session_factory: sessionmaker[Session]) -> SqlAlchemyUnitOfWork:
    return SqlAlchemyUnitOfWork(session_factory)
