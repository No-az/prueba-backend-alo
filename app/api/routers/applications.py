from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from fastapi import status as http_status

from app.api import dependencies as deps
from app.api.schemas import ApplicationCreate, ApplicationOut
from app.application.ports import ApplicationFilters
from app.application.use_cases import GetApplication, ListApplications, SubmitApplication
from app.domain.enums import Decision, Product

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("", status_code=http_status.HTTP_201_CREATED, response_model=ApplicationOut)
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


@router.get("", response_model=list[ApplicationOut])
def search_applications(
    search: Annotated[ListApplications, Depends(deps.list_applications)],
    status: Annotated[Decision | None, Query(description="APPROVED o REJECTED")] = None,
    product: Annotated[Product | None, Query(description="PHONE, TWIST o CARD")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Máximo de resultados")] = 100,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
) -> list[ApplicationOut]:
    """Lista solicitudes, las más recientes primero. Los filtros son opcionales.

    El límite evita devolver la tabla completa en una sola respuesta.
    """
    filters = ApplicationFilters(status=status, product=product, limit=limit, offset=offset)
    return [ApplicationOut.from_domain(application) for application in search(filters)]


@router.get("/{application_id}", response_model=ApplicationOut)
def read_application(
    application_id: UUID,
    get: Annotated[GetApplication, Depends(deps.get_application)],
) -> ApplicationOut:
    """Devuelve una solicitud por id. Si no existe responde 404."""
    return ApplicationOut.from_domain(get(application_id))
