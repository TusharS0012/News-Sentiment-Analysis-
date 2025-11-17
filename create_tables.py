import asyncio

# ⭐ THIS IS THE FIX — IMPORT ALL MODELS
from app.models import news, sector, sentiment_aggregate, stock

from app.core.db import engine, Base


async def create():
    print("Loaded tables:", Base.metadata.tables.keys())

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("Tables created successfully!")


asyncio.run(create())
