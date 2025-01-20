import os
import uvicorn
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from spotispy.config import SESSION_SECRET_KEY
from spotispy.routers import auth, user


# Initalize FastAPI app
app = FastAPI()
# Add session middleware for user authentication
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY)
# Include routers
app.include_router(auth.router, tags=["auth"])
app.include_router(user.router, tags=["user"])

# Use the PORT environment variable, default to 8000 for local development
port = int(os.environ.get("PORT", 8000))
# Run the FastAPI app with the uvicorn server
uvicorn.run(app, host="0.0.0.0", port=port)
