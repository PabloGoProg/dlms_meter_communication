from typing import List, Optional, TYPE_CHECKING
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship
from uuid import UUID
from sqlalchemy import Column, text, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID

if TYPE_CHECKING:
    from .communication_endpoint import CommunicationEndpoint
    from .device_addressing import DeviceAddressing


class Device(SQLModel, table=True):
    __tablename__ = "devices"

    id: Optional[UUID] = Field(
        default=None,
        sa_column=Column(
            PGUUID(as_uuid=True), primary_key=True, default=text("gen_random_uuid()")
        ),
    )
    name: str = Field(nullable=False, max_length=255)
    description: str = Field(sa_column=Column(Text, nullable=True))
    serial_number: str = Field(nullable=True, max_length=255, unique=True)
    brand: str = Field(nullable=True, default=None, max_length=255)
    model: str = Field(nullable=True, default=None, max_length=255)

    communication_endpoints: List["CommunicationEndpoint"] = Relationship(
        back_populates="device"
    )
    device_addressings: List["DeviceAddressing"] = Relationship(
        back_populates="device",
    )

    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True), nullable=False, server_default=text("now()")
        )
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True), nullable=False, server_onupdate=text("now()")
        ),
        default=text("now()"),
    )
