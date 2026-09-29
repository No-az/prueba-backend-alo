from fastapi import FastAPI

from app.database import Base, engine

# Simple setup: create tables on startup. In production, use Alembic.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Credit Evaluation Service")


@app.get("/health")
def health():
    return {"status": "ok"}


# TODO: register your applications router here.
