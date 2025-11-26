# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as api_router
from app.core.db import init_db
from app.tasks.scheduler import start_scheduler
from datetime import datetime


app = FastAPI(
    title="News Sentiment Trading API",
    version="1.0.0",
    description="Backend service for market news sentiment, sector analytics, and trading insights.",
)

# ---------------------------------------------------------
# CORS SETTINGS - REQUIRED FOR FRONTEND (React/Vite)
# ---------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite default
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "*",  # allow all (for development only)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# INCLUDE ROUTES
# ---------------------------------------------------------
app.include_router(api_router, prefix="/api")

# ---------------------------------------------------------
# ROOT ENDPOINT
# ---------------------------------------------------------
@app.get("/")
async def root():
    return {
        "status": "running",
        "service": "News Sentiment Trading API",
        "timestamp": datetime.utcnow(),
    }

# ---------------------------------------------------------
# STARTUP EVENTS
# ---------------------------------------------------------
@app.on_event("startup")
async def on_startup():
    print("🚀 Starting News Sentiment Trading Backend...")

    # Create DB tables if not already
    await init_db()

    # Start Background Scheduled Jobs (News Ingestion + Aggregation)
    start_scheduler()

    print("✔ API and Scheduler started successfully.")

# ---------------------------------------------------------
# SHUTDOWN EVENTS
# ---------------------------------------------------------
@app.on_event("shutdown")
async def on_shutdown():
    print("🛑 Shutting down News Sentiment Trading Backend...")
    print("✔ Shutdown complete.")
