from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api import dependencies as deps
from app.api.schemas import ApplicationCreate, ApplicationOut
from app.application.errors import ApplicationNotFoundError
from app.application.use_cases import GetApplication, SubmitApplication

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ApplicationOut)
def create_application(
    payload: ApplicationCreate,
    response: Response,
    submit: Annotated[SubmitApplication, Depends(deps.submit_application)],
) -> ApplicationOut:
    """Evalúa la solicitud con la política vigente de su producto, la guarda y devuelve la
    decisión."""
    application = submit(payload.to_domain())
    response.headers["Location"] = f"/applications/{application.id}"
    return ApplicationOut.from_domain(application)


@router.get("/{application_id}", response_model=ApplicationOut)
def read_application(
    application_id: UUID,
    get: Annotated[GetApplication, Depends(deps.get_application)],
) -> ApplicationOut:
    try:
        return ApplicationOut.from_domain(get(application_id))
    except ApplicationNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
