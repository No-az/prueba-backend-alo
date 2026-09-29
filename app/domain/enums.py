from enum import StrEnum


class Product(StrEnum):
    PHONE = "PHONE"
    TWIST = "TWIST"
    CARD = "CARD"


class Decision(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
