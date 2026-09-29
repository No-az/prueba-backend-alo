"""Tareas de administración por línea de comandos.

Publicar una versión nueva de una política (las anteriores no cambian):

    python -m app.cli publish-policy TWIST --name Estándar \\
        --rules '{"all_of": [{"min_score": 650}, {"max_installment_to_income": "0.30"}]}'

    python -m app.cli publish-policy TWIST --name Estándar --rules-file twist_v2.json

Con Docker: docker compose run --rm app python -m app.cli publish-policy ...
Luego POST /applications/{id}/reevaluate aplica la versión nueva.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from app.application.use_cases import PublishPolicy
from app.domain.enums import Product
from app.domain.errors import InvalidPolicyError
from app.infrastructure.clock import SystemClock
from app.infrastructure.db.engine import make_engine, make_session_factory
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from app.infrastructure.settings import get_settings


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)

    publish = commands.add_parser("publish-policy", help="Publica una versión nueva")
    publish.add_argument("product", choices=[p.value for p in Product])
    publish.add_argument("--name", required=True, help="Nombre de la política")
    source = publish.add_mutually_exclusive_group(required=True)
    source.add_argument("--rules", help="Reglas en JSON")
    source.add_argument("--rules-file", type=Path, help="Archivo JSON con las reglas")
    return parser


def _load_rules(args: argparse.Namespace) -> dict[str, Any]:
    raw = args.rules_file.read_text(encoding="utf-8") if args.rules_file else args.rules
    rules = json.loads(raw)
    if not isinstance(rules, dict):
        raise InvalidPolicyError("Las reglas deben ser un objeto JSON")
    return rules


def main(
    argv: Sequence[str] | None = None, *, session_factory: sessionmaker[Session] | None = None
) -> int:
    args = _parser().parse_args(argv)
    if session_factory is None:
        session_factory = make_session_factory(make_engine(get_settings().database_url))

    publish = PublishPolicy(SqlAlchemyUnitOfWork(session_factory), SystemClock())
    try:
        policy = publish(Product(args.product), args.name, _load_rules(args))
    except (InvalidPolicyError, json.JSONDecodeError) as exc:
        print(f"No se publicó la política: {exc}", file=sys.stderr)
        return 1

    print(f"Publicada la versión {policy.version} de la política de {policy.product}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
