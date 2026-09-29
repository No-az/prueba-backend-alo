# ADR 0004 · SQLite con migraciones de Alembic

**Estado:** aceptada

## Contexto

El esqueleto usa SQLite y crea las tablas con `create_all` al importar `main.py`. Los evaluadores levantan todo con `docker compose up --build`.

## Decisión

- Se mantiene SQLite: cumple lo que se pide y no agrega servicios a `docker compose`.
- Se reemplaza `create_all` por migraciones de Alembic, que el contenedor aplica al arrancar (`scripts/start.sh`).
- Las migraciones no importan código de la aplicación, así una migración vieja hace siempre lo mismo.
- Se aprovechan características de la base: `CHECK` constraints, foreign keys (activadas explícitamente en SQLite), índices compuestos y triggers.
- Las fechas se guardan en UTC con zona horaria, y los decimales como texto para no perder precisión.

## Consecuencias

- Los tests verifican que las migraciones producen exactamente el esquema de los modelos, que la siembra coincide con las políticas del dominio y que se pueden revertir.
- Pasar a PostgreSQL requiere cambiar `DATABASE_URL`, agregar el driver y portar los triggers de la migración `0003`, que hoy solo se crean en SQLite.
