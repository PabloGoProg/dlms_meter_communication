from pydantic import BaseModel, Field
from datetime import datetime


class ReadSingleRequest(BaseModel):
    obis: str


class ProfileByDateRangeRequest(BaseModel):
    """
    Esquema de petición para leer un perfil genérico por rango de fechas.

    Attributes:
        obis: Código OBIS del perfil genérico (ej: "1.0.99.1.0.255")
        start_date: Fecha y hora de inicio del rango (formato ISO 8601)
        end_date: Fecha y hora de fin del rango (formato ISO 8601)
    """

    obis: str = Field(
        ...,
        description="Código OBIS del perfil genérico",
        examples=["1.0.99.1.0.255", "1.0.99.2.0.255"],
    )
    start_date: datetime = Field(
        ...,
        description="Fecha y hora de inicio del rango (ISO 8601)",
        examples=["2024-01-01T00:00:00"],
    )
    end_date: datetime = Field(
        ...,
        description="Fecha y hora de fin del rango (ISO 8601)",
        examples=["2024-01-31T23:59:59"],
    )
