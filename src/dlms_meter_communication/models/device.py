from __future__ import annotations

from typing import Optional
from datetime import datetime
from sqlmodel import Field
from uuid import UUID
from sqlalchemy import Column, text, DateTime
from .base import BaseModel
from sqlalchemy.dialects.postgresql import UUID as PGUUID


class Device(BaseModel, table=True):
    __tablename__ = "devices"

    id: Optional[UUID] = Field(
        default=None,
        sa_column=Column(
            PGUUID(as_uuid=True), primary_key=True, default=text("gen_random_uuid()")
        ),
    )
    name: str = Field(nullable=False, max_length=255)
    description: Optional[str] = None
    serial_number: str = Field(nullable=False, max_length=255, unique=True)
    brand: str = Field(nullable=False, default=None, max_length=255)
    model: str = Field(nullable=False, default=None, max_length=255)

    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True), nullable=False, server_default=text("now()")
        )
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True), nullable=False, server_onupdate=text("now()")
        )
    )
