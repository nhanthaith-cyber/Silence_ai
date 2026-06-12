"""
Startup script for Railway deployment.
Reads PORT from environment variable (Railway sets this automatically).
"""
import os
import uvicorn

port = int(os.environ.get("PORT", 8000))
print(f"[Startup] Starting server on port {port}")

uvicorn.run("main:socket_app", host="0.0.0.0", port=port)
