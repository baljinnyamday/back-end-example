from datetime import timedelta
import stat
from typing import Annotated, Any, Dict

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import CookieDep, CurrentUser, SessionDep
from app.core import security
from app.core.config import settings
from app.core.ldap import authenticate_ldap
from app.models import LDAPUser, Token, UserPublic
import re

router = APIRouter(tags=["login"])


@router.post("/login/access-token")
def login_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], response: Response
) -> dict[str, Any]:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    username = re.sub(r"@ot\.mn", "", form_data.username.strip(), flags=re.IGNORECASE)
    username = re.sub(r"@riotinto\.com", "", username, flags=re.IGNORECASE)
    password = form_data.password.strip()

    user, detail = authenticate_ldap(username, password)

    if not user:
        raise HTTPException(status_code=400, detail=detail)

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    human_readable_data = LDAPUser(
        **{
            "name": user.get("attributes").get("displayName")[0],
            "title": user.get("attributes").get("title")[0],
            "username": user.get("attributes").get("mailNickname")[0],
            "id": user.get("dn"),
        }
    )

    _token = security.create_access_token(
        human_readable_data.__dict__,
        expires_delta=access_token_expires,
    )

    response.set_cookie(
        key=settings.TOKEN_KEY,
        value=_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert minutes to seconds
        path="/",
    )

    return {**human_readable_data.__dict__, "token": _token}


@router.get("/logout")
def kill_cookie(response: Response):
    response.delete_cookie(key=settings.TOKEN_KEY)
    return {"suxess": True}


@router.get("/me")
def test_token(current_user: CurrentUser) -> CurrentUser:
    """
    Test access token
    """
    return current_user


@router.get("/403")
def return_403(current_user: CookieDep) -> JSONResponse:
    """
    403
    """
    return JSONResponse(status_code=403, content={})


@router.get("/secure-cookie")
def get_my_cookie(response: Response, access_token: CookieDep) -> Any:
    """
    Get your secure ass cookie
    """

    return access_token
