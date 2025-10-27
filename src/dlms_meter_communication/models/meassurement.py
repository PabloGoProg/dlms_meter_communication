from __future__ import annotations

from typing import Optional
from datetime import datetime
from uuid import UUID
from .base import BaseModel

from sqlmodel import Field
from sqlalchemy import Column, DateTime, ForeignKey, Text, text, Index
from .enums import Quantity, Direction, Phase
from sqlalchemy.dialects.postgresql import (
    UUID as PGUUID,
    ENUM as PGEnum,
    DOUBLE_PRECISION,
)


class Measurement(BaseModel, table=True):
    __tablename__ = "measurements"

    __table_args__ = (
        Index(
            "measurements_dev_time_idx",
            "device_id",
            text("ts_meter DESC"),
        ),
        Index(
            "measurements_quantity_idx",
            "quantity",
            "direction",
            "phase",
        ),
    )

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
    endpoint_id: Optional[UUID] = Field(
        default=None,
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("comm_endpoints.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    obis: str = Field(sa_column=Column(Text, nullable=False))
    quantity: Quantity = Field(
        sa_column=Column(
            PGEnum(Quantity, name="quantity_enum", native_enum=True, create_type=False),
            nullable=False,
        )
    )
    direction: Direction = Field(
        sa_column=Column(
            PGEnum(
                Direction, name="direction_enum", native_enum=True, create_type=False
            ),
            nullable=False,
        )
    )
    phase: Phase = Field(
        sa_column=Column(
            PGEnum(Phase, name="phase_enum", native_enum=True, create_type=False),
            nullable=False,
        )
    )
    value: float = Field(sa_column=Column(DOUBLE_PRECISION, nullable=False))
    unit: str = Field(sa_column=Column(Text, nullable=False))
    ts_meter: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=False), nullable=True),
    )
    ts_captured: datetime = Field(
        sa_column=Column(
            DateTime(timezone=False),
            nullable=False,
            server_default=text("now()"),
        )
    )
