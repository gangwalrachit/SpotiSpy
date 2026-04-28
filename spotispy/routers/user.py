import time
from collections import defaultdict
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from spotipy import Spotify
from spotipy.exceptions import SpotifyException
from sqlalchemy.orm import Session

from spotispy.config import sp_oauth
from spotispy.database import User, get_db

LIMIT = 50
PREVIEW_LIMIT = 10

router = APIRouter()
templates = Jinja2Templates(directory="templates")
templates.env.filters["duration"] = lambda ms: f"{ms // 60000}:{(ms % 60000) // 1000:02d}"


def _unauth(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("base.html", {"request": request, "authenticated": False})


def _auth_context(request: Request, db: Session):
    """Returns (Spotify client, base template ctx) or (None, None) if not authenticated."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None, None

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None, None

    token_info = user.token_info
    if token_info["expires_at"] - int(time.time()) < 60:
        token_info = sp_oauth.refresh_access_token(token_info["refresh_token"])
        user.token_info = token_info
        db.commit()

    user_info = user.user_info
    user_pfp = "https://placehold.co/150"
    if user_info.get("images"):
        user_pfp = user_info["images"][0].get("url", user_pfp)

    return Spotify(auth=token_info["access_token"]), {
        "authenticated": True,
        "user_name": user_info.get("display_name", user_id),
        "user_profile_url": user_info.get("external_urls", {}).get("spotify"),
        "user_pfp": user_pfp,
        "user_followers": user_info.get("followers", {}).get("total"),
    }


@router.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    sp, ctx = _auth_context(request, db)
    if not sp:
        return _unauth(request)

    try:
        top_tracks = sp.current_user_top_tracks(limit=PREVIEW_LIMIT, time_range="short_term")
        top_artists = sp.current_user_top_artists(limit=PREVIEW_LIMIT, time_range="short_term")
    except SpotifyException:
        return _unauth(request)

    return templates.TemplateResponse("index.html", {
        "request": request,
        **ctx,
        "top_tracks": top_tracks["items"],
        "top_artists": top_artists["items"],
        "active_page": "home",
    })


@router.get("/tracks", response_class=HTMLResponse)
async def tracks(
    request: Request,
    time_range: str = "short_term",
    db: Session = Depends(get_db),
) -> HTMLResponse:
    sp, ctx = _auth_context(request, db)
    if not sp:
        return _unauth(request)

    try:
        top_tracks = sp.current_user_top_tracks(limit=LIMIT, time_range=time_range)
    except SpotifyException:
        return _unauth(request)

    return templates.TemplateResponse("tracks.html", {
        "request": request,
        **ctx,
        "top_tracks": top_tracks["items"],
        "time_range": time_range,
        "active_page": "tracks",
    })


@router.get("/artists", response_class=HTMLResponse)
async def artists(
    request: Request,
    time_range: str = "short_term",
    db: Session = Depends(get_db),
) -> HTMLResponse:
    sp, ctx = _auth_context(request, db)
    if not sp:
        return _unauth(request)

    try:
        top_artists = sp.current_user_top_artists(limit=LIMIT, time_range=time_range)
    except SpotifyException:
        return _unauth(request)

    return templates.TemplateResponse("artists.html", {
        "request": request,
        **ctx,
        "top_artists": top_artists["items"],
        "time_range": time_range,
        "active_page": "artists",
    })


@router.get("/albums", response_class=HTMLResponse)
async def albums(
    request: Request,
    time_range: str = "short_term",
    db: Session = Depends(get_db),
) -> HTMLResponse:
    sp, ctx = _auth_context(request, db)
    if not sp:
        return _unauth(request)

    try:
        top_tracks = sp.current_user_top_tracks(limit=LIMIT, time_range=time_range)
    except SpotifyException:
        return _unauth(request)

    return templates.TemplateResponse("albums.html", {
        "request": request,
        **ctx,
        "top_albums": get_top_albums(top_tracks),
        "time_range": time_range,
        "active_page": "albums",
    })


@router.get("/genres", response_class=HTMLResponse)
async def genres(
    request: Request,
    time_range: str = "short_term",
    db: Session = Depends(get_db),
) -> HTMLResponse:
    sp, ctx = _auth_context(request, db)
    if not sp:
        return _unauth(request)

    try:
        top_artists = sp.current_user_top_artists(limit=LIMIT, time_range=time_range)
    except SpotifyException:
        return _unauth(request)

    return templates.TemplateResponse("genres.html", {
        "request": request,
        **ctx,
        "top_genres": get_top_genres(top_artists),
        "time_range": time_range,
        "active_page": "genres",
    })


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
