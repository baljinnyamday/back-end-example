from collections.abc import Generator
from typing import Annotated
import redis.asyncio as redis

import jwt
from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel import Session

from app.core import security
from app.core.config import settings
from app.core.db import engine
from app.models import LDAPUser, TokenPayload, User
from fastapi.security import APIKeyCookie

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]

cookie_scheme = APIKeyCookie(name="access_token")
CookieDep = Annotated[str, Depends(cookie_scheme)]


def get_current_user(access_token: CookieDep) -> LDAPUser:
    try:

        payload = jwt.decode(
            access_token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authenticated",
            )

        token_data = LDAPUser(**payload["sub"])
        if not token_data:
            raise HTTPException(status_code=404, detail="User not found")

        return token_data
    except (InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )


CurrentUser = Annotated[LDAPUser, Depends(get_current_user)]
