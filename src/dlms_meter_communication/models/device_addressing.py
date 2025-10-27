from __future__ import annotations

from uuid import UUID
from typing import Optional
from sqlmodel import Field
from sqlalchemy import Column, Integer, Boolean, ForeignKey, text, DateTime
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from .base import BaseModel
from datetime import datetime


class DeviceAddressing(BaseModel, table=True):
    __tablename__ = "device_addressing"

    id: Optional[UUID] = Field(
        default=None,
        sa_column=Column(
            PGUUID(as_uuid=True), primary_key=True, default=text("gen_random_uuid()")
        ),
    )
    endpoint_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("comm_endpoints.id", ondelete="CASCADE"),
            nullable=False,
        )
    )

    client_address: int = Field(sa_column=Column(Integer, nullable=False))
    server_address: int = Field(sa_column=Column(Integer, nullable=False))

    use_logical_name: bool = Field(
        default=True,
        sa_column=Column(Boolean, nullable=False, server_default=text("true")),
    )

    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True), nullable=False, server_default=text("now()")
        )
    )
