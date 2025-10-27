from fastapi import APIRouter

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("/")
async def get_devices():
    return {"message": "Hello, World!"}
