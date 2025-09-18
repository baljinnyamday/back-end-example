import logging
from fastapi import (
    APIRouter,
)
from fastapi.responses import JSONResponse

from app.services.history import get_image_history


router = APIRouter(prefix="/history", tags=["Historical data submitted to cavecad"])
logger = logging.getLogger(__name__)


@router.get("/")
async def get():
    try:
        results = await get_image_history()
        return JSONResponse({"results": results})
    except Exception as e:
        logger.error(e)
        return JSONResponse("ERROR", status_code=500)
