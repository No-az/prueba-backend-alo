# ADR 0001 · Arquitectura por capas en lugar de la estructura sugerida

**Estado:** aceptada

## Contexto

El enunciado sugiere `repositories/`, `services/` y `strategies/` y permite cambiarlo si se justifica. Pide dos cosas de diseño: que la política no se elija con `if/elif` en el endpoint y que el acceso a datos no esté acoplado al endpoint.

## Decisión

Cuatro capas con dependencias en una sola dirección:

- `domain/`: reglas, políticas, value objects y entidades. Python puro, sin FastAPI ni SQLAlchemy.
- `application/`: casos de uso (`SubmitApplication`, `ReevaluateApplication`, ...) y los **puertos** que necesitan (`UnitOfWork`, `ApplicationRepository`, `PolicyRepository`, `Clock`).
- `infrastructure/`: adaptadores que implementan los puertos (SQLAlchemy, reloj del sistema, settings).
- `api/`: FastAPI. Traduce HTTP a casos de uso y de vuelta.

Las equivalencias con la estructura sugerida son directas: `strategies/` → `domain/rules` + `domain/policies`, `services/` → `application/use_cases.py` y `repositories/` → `infrastructure/db/repositories.py`.

## Consecuencias

- Las reglas de negocio se prueban sin base de datos ni HTTP (`tests/unit`).
- Los casos de uso se prueban con adaptadores en memoria de pocas líneas (`tests/fakes.py`), lo que demuestra que no dependen de SQLAlchemy.
- Cambiar SQLite por PostgreSQL solo toca `infrastructure/`.
- Hay más archivos que en una solución de un solo módulo. Para un servicio que va a crecer en reglas y productos, vale la pena.
