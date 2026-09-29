from fastapi import FastAPI

# El esquema de la base lo crean las migraciones de Alembic (alembic upgrade head),
# no la aplicación al arrancar.
app = FastAPI(title="Credit Evaluation Service")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
