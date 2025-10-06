from fastapi import FastAPI
from dlms_meter_communication.core.config import config
from dlms_meter_communication.core.logging import setup_logging

logger = setup_logging()

app = FastAPI(
    title=config.project_title,
    description=config.project_description,
    version=config.project_version,
    contact={
        "name": config.project_contact_name,
        "email": config.project_contact_email,
    },
)
