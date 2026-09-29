class DomainError(Exception):
    """Error base del dominio: siempre es un problema del negocio, no de infraestructura."""


class InvalidValueError(DomainError, ValueError):
    """Un value object recibió un valor que no tiene sentido para el negocio."""
