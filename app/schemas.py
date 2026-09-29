"""
Pydantic schemas.

Example schema below — feel free to modify, remove, or add more.
"""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
