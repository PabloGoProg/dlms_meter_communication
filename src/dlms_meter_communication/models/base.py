from sqlmodel import SQLModel


class BaseModel(SQLModel, table=True):
    __abstract__ = True
