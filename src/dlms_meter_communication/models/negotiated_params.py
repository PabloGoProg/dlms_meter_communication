from __future__ import annotations

from typing import Optional
from datetime import datetime
from uuid import UUID
from .base import BaseModel
from sqlmodel import Field
from sqlalchemy import Column, DateTime, Integer, ForeignKey, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID


class NegotiatedParams(BaseModel, table=True):
    __tablename__ = "negotiated_params"

    __table_args__ = (
        UniqueConstraint(
            "device_id",
            "endpoint_id",
            name="negotiated_params_device_endpoint_uniq",
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
        ),
    )
    endpoint_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("comm_endpoints.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    max_info_rx: Optional[int] = Field(
        default=None, sa_column=Column(Integer, nullable=True)
    )
    max_info_tx: Optional[int] = Field(
        default=None, sa_column=Column(Integer, nullable=True)
    )
    win: Optional[int] = Field(default=None, sa_column=Column(Integer, nullable=True))
    max_pdu: Optional[int] = Field(
        default=None, sa_column=Column(Integer, nullable=True)
    )

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
