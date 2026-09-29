from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import inspect, select

from app.domain.default_policies import DEFAULT_POLICY_CONFIGS
from app.infrastructure.db.base import Base
from app.infrastructure.db.engine import make_engine
from app.infrastructure.db.orm_models import PolicyVersionRow

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def database_url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'migrations.db'}"


@pytest.fixture
def alembic_config(database_url: str) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    config.attributes["configure_logger"] = False
    return config


def test_migrations_build_exactly_the_schema_of_the_models(
    alembic_config: Config, database_url: str
) -> None:
    command.upgrade(alembic_config, "head")
    engine = make_engine(database_url)
    with engine.connect() as connection:
        diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    engine.dispose()
    assert diff == []


def test_initial_policies_match_the_domain_defaults(
    alembic_config: Config, database_url: str
) -> None:
    command.upgrade(alembic_config, "head")
    engine = make_engine(database_url)
    with engine.connect() as connection:
        rows = connection.execute(select(PolicyVersionRow.__table__)).mappings().all()
    engine.dispose()

    seeded = {row["product"]: {"name": row["name"], "rules": row["rules"]} for row in rows}
    assert seeded == {product.value: cfg for product, cfg in DEFAULT_POLICY_CONFIGS.items()}
    assert {row["version"] for row in rows} == {1}


def test_migrations_can_be_rolled_back(alembic_config: Config, database_url: str) -> None:
    command.upgrade(alembic_config, "head")
    command.downgrade(alembic_config, "base")
    engine = make_engine(database_url)
    assert inspect(engine).get_table_names() == ["alembic_version"]
    engine.dispose()
