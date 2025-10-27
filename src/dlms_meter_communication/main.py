from fastapi import FastAPI
from contextlib import asynccontextmanager

# from dlms_meter_communication.db.database import
from dlms_meter_communication.core.config import config
from dlms_meter_communication.core.logging import setup_logging

logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Before the application starts
    logger.info("Starting up...")
    yield
    # After the application starts
    logger.info("Shutting down...")


app = FastAPI(
    title=config.project_title,
    description=config.project_description,
    version=config.project_version,
    contact={
        "name": config.project_contact_name,
        "email": config.project_contact_email,
    },
)
