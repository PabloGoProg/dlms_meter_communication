from __future__ import annotations

from .base import BaseModel
from .enums import Medium, Profile
from typing import Optional
from datetime import datetime
from sqlmodel import Field
from sqlalchemy import (
    Column,
    text,
    DateTime,
    CheckConstraint,
    ForeignKey,
    Integer,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, ENUM as PGENUM, INET
from uuid import UUID


class CommunicationEndpoint(BaseModel, table=True):
    __tablename__ = "comm_endpoints"

    __table_args__ = (
        CheckConstraint(
            "(medium <> 'TCP') OR (ip IS NOT NULL AND port IS NOT NULL)",
            name="comm_endpoints_tcp_requires_ip_port",
        ),
        CheckConstraint(
            "(medium <> 'SERIAL') OR (serial_port IS NOT NULL AND baud_rate IS NOT NULL)",
            name="comm_endpoints_serial_requires_params",
        ),
        Index(
            "comm_endpoints_tcp_uniq",
            "device_id",
            "medium",
            "profile",
            "ip",
            "port",
            unique=True,
            postgresql_where=text("medium = 'TCP'"),
        ),
        Index(
            "comm_endpoints_serial_uniq",
            "device_id",
            "medium",
            "profile",
            "serial_port",
            "baud_rate",
            unique=True,
            postgresql_where=text("medium = 'SERIAL'"),
        ),
        Index("comm_endpoints_device_idx", "device_id"),
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
    medium: Medium = Field(
        sa_column=Column(
            PGENUM(Medium, name="comm_medium_enum", create_type=True), nullable=False
        )
    )
    profile: Profile = Field(
        sa_column=Column(
            PGENUM(Profile, name="comm_profile_enum", create_type=True), nullable=False
        )
    )
    ip: Optional[str] = Field(
        default=None,
        sa_column=Column(INET, nullable=True),
    )
    port: Optional[int] = Field(default=None, sa_column=Column(Integer))
    serial_port: Optional[str] = None
    baud_rate: Optional[int] = None

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
