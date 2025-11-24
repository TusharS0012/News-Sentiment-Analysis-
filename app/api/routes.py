from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.services.sector_service import SectorService
from app.services.news_service import NewsService
from app.api.schemas.sector import SectorRead
from app.api.schemas.news import NewsCreate, NewsRead
from typing import List
from sqlalchemy.future import select
from app.models.sector import Sector
from app.models.sentiment_aggregate import SentimentAggregate

router = APIRouter()

@router.get("/health")
async def health():
    return {"status": "ok"}

# --- sectors ---
@router.get("/sectors", response_model=List[SectorRead])
async def get_sectors(db: AsyncSession = Depends(get_db)):
    return await SectorService.get_all(db)

@router.post("/sectors", response_model=SectorRead)
async def create_sector(name: str, description: str | None = None, db: AsyncSession = Depends(get_db)):
    return await SectorService.create(db, name, description)

# --- news ingestion endpoints ---
@router.post("/news", response_model=NewsRead)
async def ingest_news(payload: NewsCreate, db: AsyncSession = Depends(get_db)):
    created = await NewsService.create(db, payload.dict())
    return created

@router.get("/news/recent", response_model=List[NewsRead])
async def recent_news(limit: int = 50, db: AsyncSession = Depends(get_db)):
    return await NewsService.list_recent(db, limit)

@router.get("/aggregates/latest")
async def get_latest_aggregates(db: AsyncSession = Depends(get_db)):
    q = (
        select(SentimentAggregate, Sector.name)
        .join(Sector, Sector.id == SentimentAggregate.sector_id, isouter=True)
        .order_by(SentimentAggregate.id.desc())
        .limit(5)
    )
    result = await db.execute(q)
    rows = result.all()

    if not rows:
        raise HTTPException(status_code=404, detail="No aggregates found")

    return [
        {
            "sector": row[1] or "Unknown",
            "avg_sentiment": row[0].avg_sentiment,
            "news_count": row[0].news_count,
            "window_start": row[0].window_start,
            "window_end": row[0].window_end,
        }
        for row in rows
    ]