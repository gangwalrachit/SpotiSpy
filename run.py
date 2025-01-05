import os
import uvicorn
from spotispy.app import app

# Use the PORT environment variable, default to 8000 for local development
port = int(os.environ.get("PORT", 8000))

uvicorn.run(app, host="0.0.0.0", port=port)
