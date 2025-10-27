from sqlmodel import create_engine, Session
from ..core.config import config
from typing import Generator
from sqlmodel import SQLModel

engine = create_engine(config.db_url)


def init_db():
    SQLModel.metadata.create_all(bind=engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
