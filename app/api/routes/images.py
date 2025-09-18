import logging
import os
from fastapi import (
    APIRouter,
    HTTPException,
    UploadFile,
)
from fastapi.responses import JSONResponse
import aiofiles

from app.core.pagination import Paginated
from app.core.config import settings

from app.services.images import get_all_images, delete_image as del_img_service

router = APIRouter(prefix="/images", tags=["Getting Image Results"])
logger = logging.getLogger(__name__)


@router.get("/")
async def get(pagination: Paginated):
    try:

        results = await get_all_images(pagination)
        return JSONResponse({"results": results})

    except Exception as e:
        logger.error(e)
        return JSONResponse("ERROR", status_code=500)


@router.post("/upload/")
async def upload_images(files: list[UploadFile]):
    try:
        saved_files = []
        for file in files:

            drawpoint_name, _ = (
                file.filename.split("_", 1) if file.filename else "XXXXX"
            )
            dir_to_write = f"{settings.RAW_DIR}/P0/XD{drawpoint_name[:2]}/"
            raw_path_folder = dir_to_write + "raw/"

            _raw = os.path.join(raw_path_folder, drawpoint_name)
            os.makedirs(_raw, exist_ok=True)
            prefixed_filename = (
                str(file.filename) if file.filename is not None else "unnamed_file"
            )

            original_file_path = os.path.abspath(os.path.join(_raw, prefixed_filename))

            try:
                async with aiofiles.open(original_file_path, "wb") as out_file:
                    content = await file.read()  # read file
                    await out_file.write(content)  # write to disk
            except Exception as e:
                logger.error(e)
                raise HTTPException(500, f"Failed to save {file.filename}") from e

            saved_files.append({file.filename, original_file_path})
        return {"saved": saved_files}
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail="Failed to upload image")


@router.delete("/{image_id}")
async def delete_image(image_id: int):
    try:
        response = await del_img_service(image_id)
        return response

    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail="Failed to delete image")
