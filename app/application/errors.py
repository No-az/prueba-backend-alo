from uuid import UUID


class ApplicationNotFoundError(Exception):
    def __init__(self, application_id: UUID) -> None:
        super().__init__(f"No existe una solicitud con id {application_id}")
        self.application_id = application_id
