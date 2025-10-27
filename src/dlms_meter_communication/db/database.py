from sqlmodel import create_engine, Session
from ..core.config import config
from typing import Generator

engine = create_engine(config.db_url)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
