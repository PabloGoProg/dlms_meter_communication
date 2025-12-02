from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlmodel import Field, SQLModel, Boolean, Relationship
from .enums import Medium, Profile
from sqlalchemy import (
    Column,
    text,
    DateTime,
    CheckConstraint,
    ForeignKey,
    Integer,
    Index,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, ENUM as PGENUM, INET
from uuid import UUID

if TYPE_CHECKING:
    from .device import Device


class CommunicationEndpoint(SQLModel, table=True):
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
            PGENUM(Medium, name="medium_enum", create_type=True), nullable=False
        )
    )
    profile: Profile = Field(
        sa_column=Column(
            PGENUM(Profile, name="profile_enum", create_type=True), nullable=False
        )
    )
    ip: Optional[str] = Field(
        default=None,
        sa_column=Column(INET, nullable=True),
    )
    port: Optional[int] = Field(default=None, sa_column=Column(Integer, nullable=True))
    serial_port: Optional[str] = Field(sa_column=Column(Text, nullable=True))
    baud_rate: Optional[int] = Field(
        default=None, sa_column=Column(Integer, nullable=True)
    )
    is_primary: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, default=False),
    )

    device: Optional["Device"] = Relationship(back_populates="communication_endpoints")

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
