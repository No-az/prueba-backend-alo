class DomainError(Exception):
    """Error base del dominio: siempre es un problema del negocio, no de infraestructura."""


class InvalidValueError(DomainError, ValueError):
    """Un value object recibió un valor que no tiene sentido para el negocio."""


class InvalidPolicyError(DomainError):
    """La configuración de una política no se puede convertir en reglas."""


class PolicyNotFoundError(DomainError):
    """No hay una política configurada para el producto pedido."""
