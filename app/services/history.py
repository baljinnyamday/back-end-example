from app.core.postgres import db_pg
from app.core.config import settings
from app.core.queries.main import Queries
import urllib.parse
from datetime import datetime


async def get_image_history():
    query = Queries()

    base_url = f"{settings.CONTENT_URL}/"
    images = await db_pg.execute_query(query.get_history)

    results = []
    username = "user unknown"
    for row in images:
        original_image_path = row["raw_image_path"].replace("\\", "/")
        processed_image_path = row["predicted_image_path"].replace("\\", "/")
        # original_image_path = original_image_path.split("C:/Users/KhangerelN/photogrammetry_web/main_be")[-1]
        original_image_url = urllib.parse.urljoin(base_url, original_image_path)
        processed_image_url = urllib.parse.urljoin(base_url, processed_image_path)

        results.append(
            {
                "original_image_name": row["drawpoint_name"],
                "original_image_url": original_image_url,
                "upload_time": (
                    row["created_date"].isoformat()
                    if isinstance(row["created_date"], datetime)
                    else row["created_date"]
                ),
                "processed_image_url": processed_image_url,
                "fine_area": row["fine_area"],
                "large_area": row["large_area"],
                "small_area": row["small_area"],
                "medium_area": row["medium_area"],
                "oversized_area": row["oversized_area"],
                "id": row["id"],
                "username": row["username"],
            }
        )
    return results
