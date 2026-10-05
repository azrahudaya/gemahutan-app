"""Model info router: laporan nyata dari artefak model yang ada di image."""
from fastapi import APIRouter

from app.services.model_status import get_model_info

router = APIRouter(prefix="/api/v1/model", tags=["model"])


@router.get("/info")
async def model_info():
    return await get_model_info()
