from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from spotipy import Spotify
from sqlalchemy import create_engine, Column, String, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from starlette.middleware.sessions import SessionMiddleware
from typing import Union

from spotispy.config import sp_oauth, DATABASE_URL, SESSION_SECRET_KEY

# Initialize FastAPI app
app = FastAPI()

# Add session middleware for user authentication
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY)

# Setup Jinja2 templates for rendering HTML pages
templates = Jinja2Templates(directory="templates")

# Set up SQLAlchemy database connection
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Define SQLAlchemy base class
Base = declarative_base()


# Define the User model
class User(Base):
    """
    SQLAlchemy model for storing user information and tookens.
    """

    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    token_info = Column(JSON)
    user_info = Column(JSON)


# Create the database tables
Base.metadata.create_all(bind=engine)


# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    """
    Home page view with login option.
    If the user is authenticated, display personalized content;
    otherwise, show the login button.

    :param request: FastAPI Request object
    :param db: Database session object
    :return: Rendered HTML template
    """
    # Fetch user_id from the session
    user_id = request.session.get("user_id")

    if user_id:
        # Fetch user-specific information from the database
        user = db.query(User).filter(User.id == user_id).first()

        if user:
            # Fetch user-specific information
            user_info = user.user_info
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


@app.get("/logout", response_class=RedirectResponse)
async def logout(request: Request) -> RedirectResponse:
    """
    Logs the user out by clearing the session and redirects to the home page.

    :param request: FastAPI Request object
    :return: RedirectResponse to the home page
    """
    request.session.pop("user_id", None)
    return RedirectResponse(url="/")


@app.get("/callback", response_class=RedirectResponse)
async def callback(request: Request, db: Session = Depends(get_db)) -> RedirectResponse:
    """
    Handles the callback from Spotify after the user logs in.
    Saves the user token and user information in the session and redirects to the top tracks page.

    :param request: FastAPI Request object
    :param db: Database session object
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

    # Check if the user already exists in the database
    existing_user = db.query(User).filter(User.id == user_id).first()

    if existing_user:
        # Update token_info and user_info for the existing user
        existing_user.token_info = token_info
        existing_user.user_info = user_info
    else:
        # Create a new user record
        new_user = User(id=user_id, token_info=token_info, user_info=user_info)
        db.add(new_user)

    # Commit the changes to the database
    db.commit()

    # Log all users in the database
    users = db.query(User).all()
    print("Current users in the database:")
    for user in users:
        print(f"ID:\t{user.id},\nUser Info:\t{user.user_info}")

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
    db: Session = Depends(get_db),
) -> Union[HTMLResponse, RedirectResponse]:
    """
    Displays the user's top tracks and artists for a given time range.

    :param request: FastAPI Request object
    :param time_range: Time range for fetching top tracks and artists:
        - short_term
        - medium_term
        - long_term
    :param limit: Number of top tracks and artists to display
    :param db: Database session object
    :return: Rendered HTML template with the user's top tracks and artists
    :raises: HTTPException if the time range is invalid
    """
    # Fetch user_id from the session
    user_id = request.session.get("user_id")

    if not user_id:
        # If the user is not authenticated, redirect to the login page
        return RedirectResponse(url="/login")

    # Fetch user from the database
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        # If user not found, redirect to login page
        return RedirectResponse(url="/login")

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
