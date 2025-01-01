import os

from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth

# Load environment variables from .env file
load_dotenv()

# FastAPI app setup
app = FastAPI()

# Template setup
templates = Jinja2Templates(directory="templates")

# Spotify credentials and OAuth setup
SPOTIPY_CLIENT_ID = os.getenv("CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("CLIENT_SECRET")
SPOTIPY_REDIRECT_URI = os.getenv("REDIRECT_URI")
SCOPE = "user-top-read"  # Scope to read user's top tracks and artists

sp_oauth = SpotifyOAuth(
    client_id=SPOTIPY_CLIENT_ID,
    client_secret=SPOTIPY_CLIENT_SECRET,
    redirect_uri=SPOTIPY_REDIRECT_URI,
    scope=SCOPE,
)

# In-memory store for user tokens (you could replace this with a proper database)
token_storage = {}


@app.get("/")
async def index(request: Request):
    """
    Home page view with login option
    """
    # Check if user is authenticated (if their user_id is in token_storage)
    user_id = None
    for user, token_info in token_storage.items():
        user_id = user
        break  # Assuming there's one user for now (or handle multiple users)

    # If user is authenticated, display a personalized greeting
    if user_id:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "user_id": user_id, "authenticated": True},
        )

    # If user is not authenticated, show a login button
    return templates.TemplateResponse(
        "index.html", {"request": request, "authenticated": False}
    )


@app.get("/login")
async def login() -> RedirectResponse:
    """
    Redirect user to Spotify's login page

    :return: RedirectResponse
    """
    # Redirect user to Spotify's login page
    auth_url = sp_oauth.get_authorize_url()
    return RedirectResponse(auth_url)


@app.get("/callback")
async def callback(request: Request) -> RedirectResponse:
    """
    Callback view to handle authorization code from Spotify

    :param request: FastAPI Request object
    :return: RedirectResponse
    """
    # Get the authorization code from the query parameters
    code = request.query_params.get("code")
    if not code:
        return {"error": "Authorization code missing in the query parameters"}

    # Get the access token using the code
    token_info = sp_oauth.get_access_token(code)

    # Initialize Spotify client with the access token
    sp = Spotify(auth=token_info["access_token"])

    # Fetch user info to get user_id
    user_info = sp.me()  # This will return user info including user_id
    user_id = user_info["id"]

    # Store token info and user_id in token_storage
    token_storage[user_id] = token_info

    # Redirect to the top tracks and artists page
    return RedirectResponse(url=f"/top/{user_id}")


@app.get("/top/{user_id}")
async def top(
    request: Request, user_id: str, time_range: str = "short_term"
) -> Jinja2Templates.TemplateResponse:
    """
    Display user's top tracks and artists

    :param request: FastAPI Request object
    :param user_id: Spotify User ID
    :param time_range: Time range for top tracks and artists and can be:
        - short_term: Last 4 weeks
        - medium_term: Last 6 months
        - long_term: All time
    :return: TemplateResponse
    """
    # Retrieve token info from the storage
    token_info = token_storage.get(user_id)
    if not token_info:
        # If the user is not authenticated, redirect to the login page
        return RedirectResponse(url="/login")

    # Validate the time range
    if time_range not in ["short_term", "medium_term", "long_term"]:
        return {"error": "Invalid time range"}

    # Use the token to access Spotify's API
    sp = Spotify(auth=token_info["access_token"])

    # Fetch top tracks
    top_tracks = sp.current_user_top_tracks(limit=10, time_range=time_range)

    # Fetch top artists
    top_artists = sp.current_user_top_artists(limit=10, time_range=time_range)

    return templates.TemplateResponse(
        "top.html",
        {
            "request": request,
            "top_tracks": top_tracks["items"],
            "top_artists": top_artists["items"],
            "time_range": time_range,  # Pass the selected time range to the template
            "user_id": user_id,  # Pass user_id to the template
        },
    )
