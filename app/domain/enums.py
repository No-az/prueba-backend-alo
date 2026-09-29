from enum import StrEnum


class Product(StrEnum):
    PHONE = "PHONE"
    TWIST = "TWIST"
    CARD = "CARD"


class Decision(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class EvaluationTrigger(StrEnum):
    """Qué originó una evaluación: la solicitud inicial o una reevaluación."""

    CREATION = "CREATION"
    REEVALUATION = "REEVALUATION"
