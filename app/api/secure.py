from fastapi import APIRouter, Depends

from app.api.deps import cookie_scheme
from app.api.routes import cavecad, images, login, private, websocket, history
from app.core.config import settings

secure_router = APIRouter(dependencies=[Depends(cookie_scheme)])

secure_router.include_router(images.router)
secure_router.include_router(history.router)
secure_router.include_router(cavecad.router)
