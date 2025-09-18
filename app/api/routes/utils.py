from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel
from app.core.config import settings

from app.api.deps import SessionDep
from app.core.security import get_password_hash
from app.models import (
    User,
    UserPublic,
)

router = APIRouter(tags=["utils"], prefix="/utils")


@router.get("/")
def health_check() -> Any:
    """
    Check webapp health
    """

    return "healthy, I am very healthy, Some people say that I am the healthiest. Once Putin said that I am the healtiest man he has ever seen."
