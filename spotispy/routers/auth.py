from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from spotipy import Spotify
from sqlalchemy.orm import Session

from spotispy.config import sp_oauth
from spotispy.database import User, get_db

router = APIRouter()


@router.get("/login", response_class=RedirectResponse)
async def login() -> RedirectResponse:
    return RedirectResponse(sp_oauth.get_authorize_url())


@router.get("/logout", response_class=RedirectResponse)
async def logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse(url="/")


@router.get("/callback", response_class=RedirectResponse)
async def callback(request: Request, db: Session = Depends(get_db)) -> RedirectResponse:
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code missing")

    token_info = sp_oauth.get_access_token(code, check_cache=False)
    user_info = Spotify(auth=token_info["access_token"]).me()
    user_id = user_info["id"]

    existing_user = db.query(User).filter(User.id == user_id).first()
    if existing_user:
        existing_user.token_info = token_info
        existing_user.user_info = user_info
    else:
        db.add(User(id=user_id, token_info=token_info, user_info=user_info))

    db.commit()
    request.session["user_id"] = user_id
    return RedirectResponse(url="/")
