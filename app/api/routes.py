from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.services.sector_service import SectorService
from app.services.news_service import NewsService
from app.api.schemas.sector import SectorRead
from app.api.schemas.news import NewsCreate, NewsRead
from typing import List

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
