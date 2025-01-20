from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from spotipy import Spotify
from sqlalchemy.orm import Session
from typing import Union

from spotispy.database import User, get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    time_range: str = "short_term",
    limit: int = 5,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """
    Home page view with login option.
    If the user is authenticated, display personalized content;
    otherwise, show the login button.

    :param request: FastAPI Request object
    :param time_range: Time range for fetching top tracks and artists:
        - short_term: a month
        - medium_term: 6 months
        - long_term: All time
    :param limit: Number of top tracks and artists to display
    :param db: Database session object
    :return: Rendered HTML template
    """
    # Fetch user_id from the session
    user_id = request.session.get("user_id")

    if not user_id:
        # Render the template with login option for unauthenticated users
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "authenticated": False},
        )

    # Fetch user-specific information from the database
    user = db.query(User).filter(User.id == user_id).first()

    if user:
        # Fetch user-specific information
        user_info = user.user_info
        user_name = user_info.get("display_name", user_id)
        user_profile_url = user_info.get("external_urls", {}).get("spotify")

        # Check if the user has profile images, if not, set a default placeholder
        user_pfp = "https://via.placeholder.com/150"  # Default image
        if user_info.get("images"):
            user_pfp = user_info["images"][0].get("url", user_pfp)

        # Validate the requested time range
        if time_range not in ["short_term", "medium_term", "long_term"]:
            raise HTTPException(status_code=400, detail="Invalid time range")

        # Fetch the user's token information
        token_info = user.token_info

        # Initialize Spotify client with the access token
        sp = Spotify(auth=token_info["access_token"])

        # Fetch the user's top tracks and artists
        top_tracks = sp.current_user_top_tracks(limit=limit, time_range=time_range)
        top_artists = sp.current_user_top_artists(limit=limit, time_range=time_range)

        # Render the template with personalized content
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "user_name": user_name,
                "user_profile_url": user_profile_url,
                "user_pfp": user_pfp,
                "top_tracks": top_tracks["items"],
                "top_artists": top_artists["items"],
                "time_range": time_range,
                "limit": limit,
                "authenticated": True,
            },
        )

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "authenticated": False},
    )
