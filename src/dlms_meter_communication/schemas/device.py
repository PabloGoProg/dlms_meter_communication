from pydantic import BaseModel
from typing import Optional, List


class Device(BaseModel):
    id: int
    name: str
    description: str = None
    serial_number: str
    brand: str = None
    model: str = None


class DeviceList(BaseModel):
    devices: List[Device]


class DeviceCreate(BaseModel):
    name: str
    description: str = None
    serial_number: str
    brand: str = None
    model: str = None


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    serial_number: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
