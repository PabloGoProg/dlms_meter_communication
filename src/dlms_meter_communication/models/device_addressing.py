from __future__ import annotations

from uuid import UUID
from typing import Optional, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, Integer, Boolean, ForeignKey, text, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from datetime import datetime

if TYPE_CHECKING:
    from .device import Device


class DeviceAddressing(SQLModel, table=True):
    __tablename__ = "device_addressing"

    id: Optional[UUID] = Field(
        default=None,
        sa_column=Column(
            PGUUID(as_uuid=True), primary_key=True, default=text("gen_random_uuid()")
        ),
    )
    device_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("devices.id", ondelete="CASCADE"),
            nullable=False,
        )
    )

    client_address: int = Field(sa_column=Column(Integer, nullable=False))
    server_address: int = Field(sa_column=Column(Integer, nullable=False))

    device: Device = Relationship(back_populates="device_addressings")

    use_logical_name: bool = Field(
        default=True,
        sa_column=Column(Boolean, nullable=False, default=True),
    )

    password: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))

    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True), nullable=False, server_default=text("now()")
        ),
        default=text("now()"),
    )
