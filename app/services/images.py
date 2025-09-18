from http import HTTPStatus
import os
from asyncer import asyncify
from fastapi import HTTPException, logger
from app.core.pagination import Paginated
from app.core.postgres import db_pg
from app.core.config import settings
from app.core.queries.main import Queries
import urllib.parse
from datetime import datetime

from app.services.schema import ImageType


async def get_all_images(pagination: Paginated):
    query = Queries()

    base_url = f"{settings.CONTENT_URL}/"
    images = await db_pg.execute_query(
        query.get_images, pagination.limit, pagination.skip
    )

    results = []
    username = "user unknown"
    for row in images:
        results.append(
            {
                "username": username,
                "image_id": row["id"],
                "drawpoint_name": row["drawpoint_name"],
                "raw_image_url": urllib.parse.urljoin(
                    base_url,
                    (
                        row["raw_image_path"].lstrip("/")
                        if row["raw_image_path"]
                        else ""
                    ),
                ),
                "predicted_image_url": urllib.parse.urljoin(
                    base_url,
                    (
                        row["predicted_image_path"].lstrip("/")
                        if row["predicted_image_path"]
                        else ""
                    ),
                ),
                "fine_area": row["fine_area"],
                "large_area": row["large_area"],
                "small_area": row["small_area"],
                "medium_area": row["medium_area"],
                "oversized_area": row["oversized_area"],
                "bbox": urllib.parse.urljoin(
                    base_url,
                    (
                        row["bbox_image_path"].lstrip("/")
                        if row["bbox_image_path"]
                        else ""
                    ),
                ),
                "edited": row["is_edited"],
                "image_status": row["image_status"],
                "bund": row["has_bund"],
                "wetness": row["wetness"],
                "condition": row["dp_condition"],
                "drawpointConditionComment": row["drawpointconditioncomment"],
                "fragmentationComment": row["fragmentationcomment"],
                "wetnessCommentnd": row["wetnesscomment"],
                "dp_condition": row["dp_condition"],
                "uploaded_date": (
                    row["created_date"].isoformat()
                    if isinstance(row["created_date"], datetime)
                    else row["created_date"]
                ),
                "image_taken_date": (
                    row["imagetaken_date"].isoformat()
                    if isinstance(row["imagetaken_date"], datetime)
                    else row["imagetaken_date"]
                ),
            }
        )
    return results


async def delete_image(image_id: int):
    query = Queries()
    image = await db_pg.execute_one(query.get_image_by_id, image_id)

    if not image:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="NOT FOUND HEHE")
    image = ImageType(**image)
    await db_pg.execute_command(query.delete_image, image_id)
    await db_pg.execute_command(query.delete_from_approved_images, image_id)

    deleted = await asyncify(delete_files)(image)

    if deleted != "success":
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Image not found on path."
        )

    return {"detail": "Image deleted successfully"}


async def get_image_by_id(image_id: str):
    query = Queries()
    image = await db_pg.execute_one(query.get_image_by_id, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    return image


def delete_files(record: ImageType):
    original_path = record.raw_image_path
    bbox_path = record.bbox_image_path
    processed_path = record.predicted_image_path

    try:
        if original_path and os.path.exists(original_path):
            os.remove(original_path)

        if processed_path and os.path.exists(processed_path):
            os.remove(processed_path)

        if bbox_path and os.path.exists(bbox_path):
            os.remove(bbox_path)

    except Exception as e:
        logger.logger.error(f"Error deleting file: {e}")

    return "success"
