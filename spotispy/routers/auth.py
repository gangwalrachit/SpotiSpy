from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from spotipy import Spotify
from sqlalchemy.orm import Session

from spotispy.config import sp_oauth
from spotispy.database import User, get_db

router = APIRouter()


@router.get("/login", response_class=RedirectResponse)
async def login() -> RedirectResponse:
    """
    Redirects the user to Spotify's login page to authenticate.

    :return: RedirectResponse to Spotify's login URL
    """
    # Generate Spotify's authorization URL
    auth_url = sp_oauth.get_authorize_url()
    return RedirectResponse(auth_url)


@router.get("/logout", response_class=RedirectResponse)
async def logout(request: Request) -> RedirectResponse:
    """
    Logs the user out by clearing the session and redirects to the home page.

    :param request: FastAPI Request object
    :return: RedirectResponse to the home page
    """
    request.session.clear()
    return RedirectResponse(url="/")


@router.get("/callback", response_class=RedirectResponse)
async def callback(request: Request, db: Session = Depends(get_db)) -> RedirectResponse:
    """
    Handles the callback from Spotify after the user logs in.
    Saves the user token and user information in the session and redirects to the dashboard.

    :param request: FastAPI Request object
    :param db: Database session object
    :return: RedirectResponse to the user's dashboard
    :raises: HTTPException if the authorization code is missing
    """
    # Get authorization code from the query parameters
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code missing")

    # Get the access token using the authorization code
    token_info = sp_oauth.get_access_token(code, check_cache=False)

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

    # Save user_id in the session for authentication
    request.session["user_id"] = user_id

    # Redirect to the dashboard
    return RedirectResponse(url="/")
