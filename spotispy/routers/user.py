import time
from collections import defaultdict
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from spotipy import Spotify
from spotipy.exceptions import SpotifyException
from sqlalchemy.orm import Session
from fastapi import Depends

from spotispy.config import sp_oauth
from spotispy.database import User, get_db

LIMIT = 50

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def _unauth(request):
    return templates.TemplateResponse(
        "index.html", {"request": request, "authenticated": False}
    )


@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    time_range: str = "short_term",
    db: Session = Depends(get_db),
) -> HTMLResponse:
    user_id = request.session.get("user_id")
    if not user_id:
        return _unauth(request)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return _unauth(request)

    user_info = user.user_info
    user_pfp = "https://placehold.co/150"
    if user_info.get("images"):
        user_pfp = user_info["images"][0].get("url", user_pfp)

    token_info = user.token_info
    if token_info["expires_at"] - int(time.time()) < 60:
        token_info = sp_oauth.refresh_access_token(token_info["refresh_token"])
        user.token_info = token_info
        db.commit()

    sp = Spotify(auth=token_info["access_token"])

    try:
        top_tracks = sp.current_user_top_tracks(limit=LIMIT, time_range=time_range)
        top_artists = sp.current_user_top_artists(limit=LIMIT, time_range=time_range)
    except SpotifyException:
        return _unauth(request)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "authenticated": True,
            "user_name": user_info.get("display_name", user_id),
            "user_profile_url": user_info.get("external_urls", {}).get("spotify"),
            "user_pfp": user_pfp,
            "user_followers": user_info.get("followers", {}).get("total"),
            "top_tracks": top_tracks["items"],
            "top_artists": top_artists["items"],
            "top_albums": get_top_albums(top_tracks),
            "top_genres": get_top_genres(top_artists),
            "time_range": time_range,
        },
    )


def get_top_albums(top_tracks: dict) -> list:
    album_dict = defaultdict(lambda: {"score": 0, "name": "", "artist": "", "image": ""})

    for index, track in enumerate(top_tracks["items"]):
        album_id = track["album"]["id"]
        weight = 1 - index / LIMIT
        album_dict[album_id]["score"] += weight
        album_dict[album_id]["name"] = track["album"]["name"]
        album_dict[album_id]["artist"] = track["artists"][0]["name"]
        album_dict[album_id]["image"] = (
            track["album"]["images"][0]["url"] if track["album"]["images"] else None
        )

    return sorted(album_dict.values(), key=lambda x: x["score"], reverse=True)


def get_top_genres(top_artists: dict) -> list:
    genre_count: dict[str, int] = {}
    for artist in top_artists["items"]:
        for genre in artist["genres"]:
            genre_count[genre] = genre_count.get(genre, 0) + 1

    return [
        {"name": name, "count": count}
        for name, count in sorted(genre_count.items(), key=lambda x: x[1], reverse=True)
    ]
