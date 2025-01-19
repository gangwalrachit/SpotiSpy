from decouple import config
from spotipy.oauth2 import SpotifyOAuth


# Session secret key for FastAPI app
SESSION_SECRET_KEY = config("SESSION_SECRET_KEY")

# Database details
DATABASE_URL = config("DATABASE_URL", default="sqlite:///./spotispy.db")

# Spotify credentials and OAuth setup
SPOTIFY_CLIENT_ID = config("CLIENT_ID")
SPOTIFY_CLIENT_SECRET = config("CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = config("REDIRECT_URI")
SCOPE = "user-top-read"  # Scope to read user's top tracks and artists

sp_oauth = SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=SPOTIFY_REDIRECT_URI,
    scope=SCOPE,
    cache_path=None,  # Disable cache
)
