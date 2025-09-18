from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class CavecadType(BaseModel):
    username: Optional[str] = "Unknown User"
    image_id: int
    drawpoint_name: str
    raw_image_url: str
    predicted_image_url: str
    fine_area: int = 0
    large_area: int = 0
    small_area: int = 0
    medium_area: int = 0
    oversized_area: int = 0
    bbox: str
    edited: Optional[Any]
    image_status: str
    bund: str
    wetness: Optional[str]
    condition: Optional[str]
    drawpointConditionComment: Optional[str]
    fragmentationComment: Optional[str]
    wetnessCommentnd: Optional[str]
    dp_condition: Optional[str]
    uploaded_date: datetime
    image_taken_date: datetime
    id: int
    upload_time: datetime
    wetnessComment: Optional[str]


class CavecadSubmitElement(BaseModel):
    data: list[CavecadType]
