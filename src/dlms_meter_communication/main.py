from fastapi import FastAPI
from contextlib import asynccontextmanager

# from dlms_meter_communication.db.database import
from dlms_meter_communication.core.config import config
from dlms_meter_communication.core.logging import setup_logging
from dlms_meter_communication.db.database import init_db
from dlms_meter_communication.services.reader_service import ReaderService

from .api.v1.routers import devices

logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Before the application starts
    logger.info("Starting up...")
    init_db()
    app.state.reader_service = ReaderService()
    yield
    # After the application starts
    app.state.reader_service.session_manager.close_all_sessions()
    logger.info("Shutting down...")


app = FastAPI(
    title=config.project_title,
    description=config.project_description,
    version=config.project_version,
    contact={
        "name": config.project_contact_name,
        "email": config.project_contact_email,
    },
    lifespan=lifespan,
)

app.include_router(devices.router)
