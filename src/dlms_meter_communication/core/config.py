from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

load_dotenv()


class Config(BaseSettings):
    project_title: str = Field(default="DLMS Meter Communication System")
    project_version: str = Field(default="0.1.0")
    project_description: str = Field(default="API for DLMS Meter Communication")
    project_contact_name: str = Field(default="PabloGoProg")
    project_contact_email: str = Field(default="pgosorio13@gmail.com")
    project_url: str = Field(
        default="https://github.com/PabloGoProg/dlms-meter-communication"
    )

    node_env: str = Field(..., validation_alias="NODE_ENV")

    DB_HOST: str = Field(..., validation_alias="DB_HOST")
    DB_PORT: int = Field(..., validation_alias="DB_PORT")
    DB_USER: str = Field(..., validation_alias="DB_USER")
    DB_PASSWORD: str = Field(..., validation_alias="DB_PASSWORD")
    DB_NAME: str = Field(..., validation_alias="DB_NAME")

    @property
    def db_url(self) -> str:
        return f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


config = Config()
