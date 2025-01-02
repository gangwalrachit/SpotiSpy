import os
from typing import Union

from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from spotipy import Spotify

from spotispy.config import sp_oauth

# FastAPI app setup
app = FastAPI()

# Template setup
templates = Jinja2Templates(directory="templates")

# In-memory store for user tokens
# TODO: replace this with a proper database)
data_store = {}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """
    Home page view with login option.

    :param request: FastAPI Request object
    :return: HTMLResponse with the rendered template
    """
    # Check if user is authenticated (if their user_id is in data_store)
    user_id = next(iter(data_store), None)  # Get the first user_id if exists

    # If user is authenticated, display a personalized greeting
    if user_id:
        user_info = data_store[user_id].get("user_info", {})
        user_name = user_info.get("display_name", user_id)
        user_pfp = user_info.get("images", [{}])[0].get("url")
        user_profile_url = user_info.get("external_urls", {}).get("spotify")

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "user_id": user_id,
                "user_name": user_name,
                "user_pfp": user_pfp,
                "user_profile_url": user_profile_url,
                "authenticated": True,
            },
        )
    # Else show a login button
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "authenticated": False},
    )


@app.get("/login")
async def login() -> RedirectResponse:
    """
    Redirect user to Spotify's login page.

    :return: RedirectResponse to Spotify's login URL
    """
    auth_url = sp_oauth.get_authorize_url()
    return RedirectResponse(auth_url)


@app.get("/callback", response_model=None)
async def callback(request: Request) -> Union[RedirectResponse, JSONResponse]:
    """
    Callback view to handle authorization code from Spotify.

    :param request: FastAPI Request object
    :return: RedirectResponse to the user's top tracks page or JSONResponse in case of error
    """
    code = request.query_params.get("code")
    if not code:
        return JSONResponse(
            {"error": "Authorization code missing in the query parameters"}
        )

    # Get the access token using the code
    token_info = sp_oauth.get_access_token(code)

    # Initialize Spotify client with the access token
    sp = Spotify(auth=token_info["access_token"])

    # Fetch user info to get user_id
    user_info = sp.me()
    user_id = user_info["id"]

    # Store token info & user info under user_id in data_store
    data_store[user_id] = token_info
    data_store[user_id]["user_info"] = user_info

    # Redirect to the top tracks and artists page
    return RedirectResponse(url=f"/top/{user_id}")


@app.get("/top/{user_id}", response_model=None, response_class=HTMLResponse)
async def top(
    request: Request, user_id: str, time_range: str = "short_term"
) -> Union[HTMLResponse, RedirectResponse]:
    """
    Display user's top tracks and artists.

    :param request: FastAPI Request object
    :param user_id: Spotify User ID
    :param time_range: Time range for top tracks and artists. Options:
        - short_term: Last 4 weeks
        - medium_term: Last 6 months
        - long_term: All time
    :return: HTMLResponse with the rendered template or RedirectResponse to the login page
    """
    token_info = data_store.get(user_id)
    if not token_info:
        return RedirectResponse(url="/login")

    if time_range not in ["short_term", "medium_term", "long_term"]:
        raise HTTPException(status_code=400, detail="Invalid time range")

    sp = Spotify(auth=token_info["access_token"])

    # Fetch top tracks and artists
    limit = 5
    top_tracks = sp.current_user_top_tracks(limit=limit, time_range=time_range)
    top_artists = sp.current_user_top_artists(limit=limit, time_range=time_range)

    return templates.TemplateResponse(
        "top.html",
        {
            "request": request,
            "top_tracks": top_tracks["items"],
            "top_artists": top_artists["items"],
            "time_range": time_range,
            "user_id": user_id,
        },
    )
