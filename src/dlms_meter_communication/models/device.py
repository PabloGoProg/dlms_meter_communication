from __future__ import annotations

from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel
from uuid import UUID
from sqlalchemy import Column, text, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID


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
