import os
from dotenv import load_dotenv

load_dotenv()

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import socketio

from app.core.database import engine, Base
from app.routers import conversations, tickets, knowledge, agents_config, analytics, webhooks, documents
from app.routers import memory as memory_router
from app.routers import products as products_router
from app.core.socket_manager import sio

# Create tables
Base.metadata.create_all(bind=engine)

# Mount Socket.IO
app = FastAPI(
    title="AI Customer Service Agent",
    description="Hệ thống chăm sóc khách hàng đa sàn (Shopee, TikTok, Facebook, Instagram)",
    version="2.0.0"
)

frontend_url = os.getenv("FRONTEND_URL", "")
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
if frontend_url:
    origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Include routers
app.include_router(webhooks.router, prefix="/webhook", tags=["Webhooks"])
app.include_router(conversations.router, prefix="/api/conversations", tags=["Conversations"])
app.include_router(tickets.router, prefix="/api/tickets", tags=["Tickets"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["Knowledge Base"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(agents_config.router, prefix="/api/agents", tags=["Agent Config"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(memory_router.router, prefix="/api/memory", tags=["Customer Memory"])
app.include_router(products_router.router, prefix="/api/products", tags=["Products"])

# Wrap with Socket.IO
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)

@app.get("/")
async def root():
    return {"message": "AI Customer Operations Agent — Thời Trang TMĐT", "version": "2.0.0", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("main:socket_app", host="0.0.0.0", port=8000, reload=True)
