from pydantic import BaseModel


class ReadSingleRequest(BaseModel):
    obis: str
