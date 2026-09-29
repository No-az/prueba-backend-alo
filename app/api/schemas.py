"""Contratos HTTP (DTOs).

Son distintos de las entidades del dominio a propósito: la API puede cambiar
de forma sin tocar las reglas de negocio, y viceversa.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.applications import CreditApplication
from app.domain.entities import CreditRequest
from app.domain.enums import Decision, Product
from app.domain.rules.base import RejectionReason
from app.domain.value_objects import Money, Score

# Tope razonable para montos en COP: evita valores absurdos o desbordes.
MAX_COP = 10_000_000_000


class HealthResponse(BaseModel):
    status: str


class ApplicationCreate(BaseModel):
    # strict: "700" o true no se convierten en números; extra: campos desconocidos = 422.
    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "amount": 1_200_000,
                    "monthly_income": 2_500_000,
                    "employment_months": 18,
                    "external_score": 720,
                    "product": "PHONE",
                }
            ]
        },
    )

    amount: int = Field(gt=0, le=MAX_COP, description="Monto solicitado en COP")
    monthly_income: int = Field(gt=0, le=MAX_COP, description="Ingresos mensuales en COP")
    employment_months: int = Field(ge=0, le=1200, description="Antigüedad laboral en meses")
    external_score: int = Field(ge=0, le=1000, description="Score externo (0 a 1000)")
    # FastAPI valida el JSON ya convertido a dict, donde el producto llega como texto;
    # el modo laxo del enum igual solo acepta los valores exactos (PHONE, TWIST, CARD).
    product: Product = Field(strict=False, description="Tipo de producto")

    def to_domain(self) -> CreditRequest:
        return CreditRequest(
            amount=Money.cop(self.amount),
            monthly_income=Money.cop(self.monthly_income),
            employment_months=self.employment_months,
            external_score=Score(self.external_score),
            product=self.product,
        )


class RejectionReasonOut(BaseModel):
    code: str = Field(description="Código estable del motivo")
    message: str
    details: dict[str, str | int]

    @classmethod
    def from_domain(cls, reason: RejectionReason) -> RejectionReasonOut:
        return cls(code=reason.code, message=reason.message, details=dict(reason.details))


class PolicyRefOut(BaseModel):
    name: str
    version: int


class ApplicationOut(BaseModel):
    id: UUID
    amount: int
    monthly_income: int
    employment_months: int
    external_score: int
    product: Product
    status: Decision
    reasons: list[RejectionReasonOut] = Field(description="Vacío cuando la solicitud se aprueba")
    installment: Decimal = Field(description="Cuota mensual (monto / 12), en COP")
    installment_to_income: Decimal = Field(description="Proporción cuota / ingreso")
    policy: PolicyRefOut = Field(description="Política y versión que tomaron la decisión")
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, application: CreditApplication) -> ApplicationOut:
        request = application.request
        evaluation = application.latest_evaluation
        return cls(
            id=application.id,
            amount=int(request.amount.amount),
            monthly_income=int(request.monthly_income.amount),
            employment_months=request.employment_months,
            external_score=request.external_score.value,
            product=request.product,
            status=application.status,
            reasons=[RejectionReasonOut.from_domain(r) for r in evaluation.reasons],
            installment=evaluation.installment.rounded().amount,
            installment_to_income=evaluation.installment_ratio.rounded(),
            policy=PolicyRefOut(name=evaluation.policy_name, version=evaluation.policy_version),
            created_at=application.created_at,
            updated_at=application.updated_at,
        )
