# app/core/db.py

import ssl
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base
from collections.abc import AsyncGenerator
from app.core.config import settings

# -----------------------------
# SSL CONTEXT for Neon (Required)
# -----------------------------
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = True
ssl_ctx.verify_mode = ssl.CERT_REQUIRED


# -----------------------------
# DATABASE ENGINE (Async)
# -----------------------------
DATABASE_URL = settings.DATABASE_URL

# asyncpg requires ssl via connect_args
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,              # ✔ Detects dropped connections
    pool_recycle=180,                # ✔ Refresh every 3 minutes
    pool_timeout=30,                 # ✔ Avoid long waits
    connect_args={"ssl": ssl_ctx},
)


# -----------------------------
# SESSION FACTORY
# -----------------------------
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
    class_=AsyncSession
)


# -----------------------------
# BASE CLASS FOR MODELS
# -----------------------------
Base = declarative_base()


# -----------------------------
# DATABASE INITIALIZATION
# -----------------------------
async def init_db():
    """Create all tables on application startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# -----------------------------
# FASTAPI DEPENDENCY
# -----------------------------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
