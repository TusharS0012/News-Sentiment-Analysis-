# main.py

from fastapi import FastAPI
from app.core.config import settings
from app.core.db import init_db
from app.api.routes import router as api_router
from app.tasks.scheduler import start_scheduler


app = FastAPI(
    title="News Sentiment Trading",
    version="1.0.0",
    description="Backend service for market news sentiment, analytics and trading signals."
)

# Register all API routes
app.include_router(api_router, prefix="/api")


# ---------------------------------------------------------
# STARTUP EVENTS
# ---------------------------------------------------------
@app.on_event("startup")
async def on_startup():
    print("Starting News Sentiment Trading Backend...")

    # Initialize database (create tables)
    await init_db()

    # Start APScheduler background tasks
    start_scheduler()

    print("✔ Startup completed.")


# ---------------------------------------------------------
# SHUTDOWN EVENTS
# ---------------------------------------------------------
@app.on_event("shutdown")
async def on_shutdown():
    print("Shutting down News Sentiment Trading Backend...")
    # APScheduler stops automatically
    print("✔ Shutdown complete.")
