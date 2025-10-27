from __future__ import annotations

from typing import Optional, Sequence
from uuid import UUID
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..models.device import Device
from ..schemas.device import DeviceCreate, DeviceUpdate


class DeviceNotFoundError(Exception):
    pass


class DeviceRepository:
    def __init__(self, session: Session):
        self._session = session

    def index(
        self, *, offset: int = 0, limit: int = 50, order_desc: bool = True
    ) -> list[Device]:
        try:
            stmt = select(Device)
            stmt = stmt.order_by(
                Device.created_at.desc() if order_desc else Device.created_at
            )
            stmt = stmt.offset(offset).limit(limit)
            devices = self._session.exec(stmt).all()

            return devices
        except Exception as e:
            raise e

    def show(self, device_id: UUID) -> Optional[Device]:
        return self._session.get(Device, device_id)

    def store(self, data: DeviceCreate) -> Device:
        entity = Device(**data.model_dump())
        self._session.add(entity)
        self._session.flush()
        self._session.refresh(entity)
        return entity

    def update(self, device_id: UUID, patch: DeviceUpdate) -> Device:
        entity = self.show(device_id)

        if entity is None:
            raise DeviceNotFoundError(str(device_id))

        update_data = patch.model_dump(exclude_unset=True)

        for k, v in update_data.items():
            setattr(entity, k, v)

        self._session.flush()
        self._session.refresh(entity)
        return entity

    def remove(self, device_id: UUID) -> None:
        entity = self.show(device_id)

        if entity is None:
            raise DeviceNotFoundError(str(device_id))

        self._session.delete(entity)
        self._session.flush()

    def destroy(self, device_id: UUID) -> None:
        entity = self.show(device_id)

        if entity is None:
            raise DeviceNotFoundError(str(device_id))

        self._session.delete(entity)
        self._session.flush()
