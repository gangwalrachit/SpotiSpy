import os
import pathlib
import uvicorn
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from spotispy.config import SESSION_SECRET_KEY
from spotispy.routers import auth, user

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY)
app.include_router(auth.router)
app.include_router(user.router)

port = int(os.environ.get("PORT", 8000))

# Use mkcert-generated certs for local HTTPS if present; plain HTTP on Render
ssl_keyfile = "localhost-key.pem" if pathlib.Path("localhost-key.pem").exists() else None
ssl_certfile = "localhost.pem" if pathlib.Path("localhost.pem").exists() else None

uvicorn.run(app, host="0.0.0.0", port=port, ssl_keyfile=ssl_keyfile, ssl_certfile=ssl_certfile)
