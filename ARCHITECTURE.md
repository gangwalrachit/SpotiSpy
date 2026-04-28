# SpotiSpy — Architecture

## Overview

SpotiSpy is a single-page FastAPI app. All rendered HTML comes from one Jinja2 template (`index.html`). The backend fetches data from the Spotify Web API on every page load — there is no client-side JS data fetching, no background jobs, and no caching layer.

```
Browser
  │
  ├─ GET /          → renders index.html (authenticated or login view)
  ├─ GET /login     → redirect to Spotify OAuth
  ├─ GET /callback  → exchanges code for token, saves to DB, sets session cookie
  └─ GET /logout    → clears session cookie
```

## Directory Structure

```
SpotiSpy/
├── run.py                   # App entry point: creates FastAPI app, mounts routes + static files
├── requirements.txt
├── Procfile                 # Heroku/Railway: "web: python run.py"
├── spotispy/
│   ├── config.py            # Reads .env; builds SpotifyOAuth instance
│   ├── database.py          # SQLAlchemy engine, User model, get_db dependency
│   └── routers/
│       ├── auth.py          # /login, /callback, /logout
│       └── user.py          # / (dashboard); get_top_albums(), get_top_genres()
├── templates/
│   └── index.html           # Single Jinja2 template; Tailwind CSS via CDN
└── static/
    └── style.css            # Kept for reference; Tailwind handles all styling
```

## Request Flow

### Unauthenticated visit to `/`

```
Browser → GET /
  → session has no user_id
  → render index.html {authenticated: False}
  → user sees login button
```

### OAuth Login

```
Browser → GET /login
  → sp_oauth.get_authorize_url()
  → 302 redirect to accounts.spotify.com

Spotify → GET /callback?code=...
  → sp_oauth.get_access_token(code)   # exchanges code for token
  → sp.me()                           # fetches user profile
  → upsert User(id, token_info, user_info) in SQLite
  → session["user_id"] = user_id
  → 302 redirect to /
```

### Authenticated visit to `/`

```
Browser → GET /?time_range=short_term
  → session["user_id"] exists
  → load User from SQLite
  → Spotify(auth=token_info["access_token"])
  → current_user_top_tracks(limit=50, time_range=...)
  → current_user_top_artists(limit=50, time_range=...)
  → get_top_albums(top_tracks)   # derived: weighted by track rank
  → get_top_genres(top_artists)  # derived: frequency count across artists
  → render index.html {authenticated: True, user_followers, top_tracks, top_artists, top_albums, top_genres}
```

## Database

Single SQLite file (`spotispy.db`), managed by SQLAlchemy.

**Table: `users`**

| Column     | Type   | Notes                                      |
|------------|--------|--------------------------------------------|
| id         | String | Spotify user ID (primary key)              |
| token_info | JSON   | `{access_token, refresh_token, expires_at, ...}` |
| user_info  | JSON   | Spotify `/me` response                     |

The token is stored as-is from Spotipy's `get_access_token`. Refresh is not currently automated — an expired token causes a `SpotifyException` which falls back to showing the login page.

## Data Derivations

**Top Albums** (`get_top_albums`)
- Iterates top 50 tracks; each track contributes a weighted score to its album: `weight = 1 - index/50`
- Albums with multiple high-ranking tracks score highest
- Returns sorted list of `{name, artist, image, score}`

**Top Genres** (`get_top_genres`)
- Counts genre occurrences across all top artists
- Returns sorted list of `{"name": str, "count": int}` dicts

## Configuration (`spotispy/config.py`)

All config is read from `.env` via `python-decouple`:

| Variable          | Required | Default                    |
|-------------------|----------|----------------------------|
| CLIENT_ID         | Yes      | —                          |
| CLIENT_SECRET     | Yes      | —                          |
| REDIRECT_URI      | Yes      | —                          |
| SESSION_SECRET_KEY| Yes      | —                          |
| DATABASE_URL      | No       | `sqlite:///./spotispy.db`  |

## External Dependencies

- **Spotify Web API** — `user-top-read` scope; called synchronously on every `/` request
- **Tailwind CSS** — loaded from CDN (`cdn.tailwindcss.com`) at runtime

## Known Limitations

- **Synchronous Spotify calls**: The app uses Spotipy (blocking HTTP) inside async FastAPI route handlers. Under load this would block the event loop. Acceptable for a personal-use app.
- **No pagination beyond 50**: Spotify's top items API caps at 50 results per call. The app makes no offset calls.
