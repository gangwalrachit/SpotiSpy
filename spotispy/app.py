import os
from typing import Union

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from spotipy import Spotify
from starlette.middleware.sessions import SessionMiddleware

from spotispy.config import sp_oauth, SESSION_SECRET_KEY

# Initialize FastAPI app
app = FastAPI()

# Add session middleware for user authentication
app.add_middleware(SessionMiddleware, secret_key="SESSION_SECRET_KEY")

# Setup Jinja2 templates for rendering HTML pages
templates = Jinja2Templates(directory="templates")

# In-memory store for user tokens and data
# TODO: replace this with a proper database
data_store = {}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """
    Home page view with login option.
    If the user is authenticated, display personalized content;
    otherwise, show the login button.

    :param request: FastAPI Request object
    :return: Rendered HTML template
    """
    # Fetch user_id from the session
    user_id = request.session.get("user_id")

    if user_id and user_id in data_store:
        # Fetch user-specific information
        user_info = data_store[user_id]["user_info"]
        user_name = user_info.get("display_name", user_id)
        user_pfp = user_info.get("images", [{}])[0].get("url")
        user_profile_url = user_info.get("external_urls", {}).get("spotify")

        # Render the template with personalized content
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "user_name": user_name,
                "user_pfp": user_pfp,
                "user_profile_url": user_profile_url,
                "authenticated": True,
            },
        )

    # Render the template with login option for unauthenticated users
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "authenticated": False},
    )


@app.get("/login", response_class=RedirectResponse)
async def login() -> RedirectResponse:
    """
    Redirects the user to Spotify's login page to authenticate.

    :return: RedirectResponse to Spotify's login URL
    """
    # Generate Spotify's authorization URL
    auth_url = sp_oauth.get_authorize_url()
    return RedirectResponse(auth_url)


@app.get("/callback", response_class=RedirectResponse)
async def callback(request: Request) -> RedirectResponse:
    """
    Handles the callback from Spotify after the user logs in.
    Saves the user token and user information in the session and redirects to the top tracks page.

    :param request: FastAPI Request object
    :return: RedirectResponse to the user's top tracks page
    :raises: HTTPException if the authorization code is missing
    """
    # Get authorization code from the query parameters
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code missing")

    # Get the access token using the authorization code
    token_info = sp_oauth.get_access_token(code)

    # Initialize Spotify client with the access token
    sp = Spotify(auth=token_info["access_token"])

    # Fetch user information
    user_info = sp.me()
    user_id = user_info["id"]

    # Store user token and information in the data_store
    data_store[user_id] = {"token_info": token_info, "user_info": user_info}

    # Save user_id in the session for authentication
    request.session["user_id"] = user_id

    # Redirect to the top tracks page
    return RedirectResponse(url="/top")


@app.get(
    "/top", response_model=None, response_class=Union[HTMLResponse, RedirectResponse]
)
async def top(
    request: Request,
    time_range: str = "short_term",
    limit: int = 5,
) -> Union[HTMLResponse, RedirectResponse]:
    """
    Displays the user's top tracks and artists for a given time range.

    :param request: FastAPI Request object
    :param time_range: Time range for fetching top tracks and artists:
        - short_term
        - medium_term
        - long_term
    :param limit: Number of top tracks and artists to display
    :return: Rendered HTML template with the user's top tracks and artists
    :raises: HTTPException if the time range is invalid
    """
    # Fetch user_id from the session
    user_id = request.session.get("user_id")

    if not user_id or user_id not in data_store:
        # If the user is not authenticated, redirect to the login page
        return RedirectResponse(url="/login")

    # Validate the requested time range
    if time_range not in ["short_term", "medium_term", "long_term"]:
        raise HTTPException(status_code=400, detail="Invalid time range")

    # Fetch the user's token information
    token_info = data_store[user_id]["token_info"]

    # Initialize Spotify client with the access token
    sp = Spotify(auth=token_info["access_token"])

    # Fetch the user's top tracks and artists
    top_tracks = sp.current_user_top_tracks(limit=limit, time_range=time_range)
    top_artists = sp.current_user_top_artists(limit=limit, time_range=time_range)

    # Render the template with top tracks and artists
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
