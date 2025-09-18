from dataclasses import dataclass
from datetime import datetime


@dataclass
class ImageType:
    id: int
    drawpoint_name: str
    edited_dp_name: str
    fine_area: int
    small_area: int
    medium_area: int
    large_area: int
    oversized_area: int
    raw_image_path: str
    predicted_image_path: str
    bbox_image_path: str
    has_bund: str
    image_status: str
    is_edited: str
    imagetaken_date: datetime
    created_date: datetime
    updated_date: datetime
