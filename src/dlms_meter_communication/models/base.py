from sqlmodel import SQLModel, Field
from uuid import UUID
from typing import Optional
from sqlalchemy import Column, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID


class BaseModel(SQLModel, table=True):
    id: Optional[UUID] = Field(
        default=None,
        primary_key=True,
        sa_column=Column(
            PGUUID(as_uuid=True), primary_key=True, default=text("gen_random_uuid()")
        ),
    )
