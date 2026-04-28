# SpotiSpy

A FastAPI web app that connects to your Spotify account and visualizes your top tracks, artists, albums, and genres across different time ranges.

## Features

- Spotify OAuth login/logout
- Top 50 tracks with album art and rank
- Top 50 artists with profile images and rank
- Top albums derived from your top tracks (weighted by track rank)
- Top genres derived from your top artists
- Filter by time range: Last 4 Weeks / Last 6 Months / All Time

## Tech Stack

- **Backend**: Python, FastAPI, Uvicorn
- **Auth**: Spotify OAuth 2.0 via Spotipy
- **Database**: SQLite via SQLAlchemy (stores user tokens and profile info)
- **Sessions**: Starlette `SessionMiddleware` (server-side cookie)
- **Templating**: Jinja2
- **Styling**: Tailwind CSS (CDN)

## Setup

### Prerequisites

- Python 3.10+
- A [Spotify Developer](https://developer.spotify.com/dashboard) app with `user-top-read` scope

### Environment Variables

Create a `.env` file in the project root:

```
CLIENT_ID=your_spotify_client_id
CLIENT_SECRET=your_spotify_client_secret
REDIRECT_URI=http://localhost:8000/callback
SESSION_SECRET_KEY=a_random_secret_string
DATABASE_URL=sqlite:///./spotispy.db   # optional, defaults to this
```

### Install and Run

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run.py
```

The app runs at `http://localhost:8000`.

## Deployment

A `Procfile` is included for Heroku-compatible platforms:

```
web: python run.py
```

The app reads the `PORT` environment variable, so it works out of the box on Heroku, Railway, Render, etc. Make sure to set all `.env` variables as platform environment variables and update `REDIRECT_URI` to your deployed URL.

## License

MIT — see [LICENSE](LICENSE).
