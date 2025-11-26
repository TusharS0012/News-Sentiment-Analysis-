from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import ARRAY
from typing import List, Optional

from app.core.db import get_db
from app.services.sector_service import SectorService
from app.services.news_service import NewsService
from app.services.news_signal_service import get_spotlight_signals
from app.api.schemas.sector import SectorRead
from app.api.schemas.news import NewsCreate, NewsRead
from app.models.sector import Sector
from app.models.sentiment_aggregate import SentimentAggregate
from app.models.news import News

router = APIRouter()

# ----------------------------------------------------
# Health Check
# ----------------------------------------------------
@router.get("/health")
async def health():
    return {"status": "ok", "message": "API running successfully"}


# ----------------------------------------------------
# Sector Endpoints
# ----------------------------------------------------
@router.get("/sectors", response_model=List[SectorRead])
async def get_sectors(db: AsyncSession = Depends(get_db)):
    return await SectorService.get_all(db)


@router.post("/sectors", response_model=SectorRead)
async def create_sector(name: str, description: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    return await SectorService.create(db, name, description)


# ----------------------------------------------------
# News Endpoints
# ----------------------------------------------------
@router.post("/news", response_model=NewsRead)
async def ingest_news(payload: NewsCreate, db: AsyncSession = Depends(get_db)):
    return await NewsService.create(db, payload.dict())


@router.get("/news/recent", response_model=List[NewsRead])
async def recent_news(limit: int = 50, db: AsyncSession = Depends(get_db)):
    return await NewsService.list_recent(db, limit)


@router.get("/news/by-sector/{sector_id}", response_model=List[NewsRead])
async def news_by_sector(sector_id: int, limit: int = 50, db: AsyncSession = Depends(get_db)):
    q = select(News).where(News.sector_id == sector_id).order_by(News.published_at.desc()).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


# ----------------------------------------------------
# Historical Sentiment for Sector
# ----------------------------------------------------
@router.get("/aggregates/historical/{sector_id}")
async def get_sector_history(sector_id: int, db: AsyncSession = Depends(get_db)):
    q = (
        select(
            SentimentAggregate.window_start,
            SentimentAggregate.window_end,
            SentimentAggregate.avg_sentiment,
            SentimentAggregate.news_count,
        )
        .where(SentimentAggregate.sector_id == sector_id)
        .order_by(SentimentAggregate.window_start.asc())
    )
    rows = (await db.execute(q)).all()

    if not rows:
        raise HTTPException(status_code=404, detail="No historical data found")

    return [
        {
            "timestamp": r[0] or r[1],
            "avg_sentiment": r[2],
            "news_count": r[3],
        }
        for r in rows
    ]


# ----------------------------------------------------
# Latest Aggregates
# ----------------------------------------------------
@router.get("/aggregates/latest")
async def get_latest_aggregates(db: AsyncSession = Depends(get_db)):
    subq = (
        select(
            SentimentAggregate.sector_id,
            func.max(SentimentAggregate.id).label("max_id")
        )
        .group_by(SentimentAggregate.sector_id)
        .subquery()
    )

    q = (
        select(SentimentAggregate, Sector.name)
        .join(subq, SentimentAggregate.id == subq.c.max_id)
        .join(Sector, Sector.id == SentimentAggregate.sector_id, isouter=True)
        .order_by(SentimentAggregate.avg_sentiment.desc())
    )

    rows = (await db.execute(q)).all()

    if not rows:
        raise HTTPException(status_code=404, detail="No aggregates found")

    return [
        {
            "sector": row[1] or "Unknown",
            "sector_id": row[0].sector_id,
            "avg_sentiment": round(row[0].avg_sentiment, 3),
            "news_count": row[0].news_count,
            "window_start": row[0].window_start,
            "window_end": row[0].window_end,
        }
        for row in rows
    ]


# ----------------------------------------------------
# Dashboard Overview (🚀 FIXED query issue)
@router.get("/dashboard/overview")
async def dashboard_overview(ticker: str, db: AsyncSession = Depends(get_db)):
    ticker = ticker.upper().strip()

    # 🔥 Trending Stocks
    trending_query = (
        select(func.unnest(News.tickers).label("ticker"), func.count(News.id).label("mentions"))
        .where(News.tickers != None)
        .group_by("ticker")
        .order_by(func.count(News.id).desc())
        .limit(10)
    )
    trending = [
        {"ticker": row[0], "mentions": row[1]}
        for row in (await db.execute(trending_query)).all() if row[0]
    ]

    # 📰 News for this ticker
    news_query = (
        select(News)
        .where(func.upper(ticker) == func.any(func.cast(News.tickers, ARRAY(String))))
        .order_by(News.processed_at.desc())
        .limit(10)
    )
    news = [
        {
            "id": n.id,
            "title": n.title,
            "source": n.source,
            "url": n.url,
            "tickers": n.tickers,
            "sentiment_score": n.sentiment_score,
            "impact_label": n.impact_label,
            "impact_confidence": n.impact_confidence,
            "impact_summary": n.impact_summary,
            "published_at": n.published_at,
            "sector_id": n.sector_id,
        }
        for n in (await db.execute(news_query)).scalars().all()
    ]

    # 📊 Ticker sentiment averages
    sentiment_query = (
        select(
            func.avg(News.sentiment_score),
            func.avg(News.impact_confidence)
        )
        .where(func.upper(ticker) == func.any(func.cast(News.tickers, ARRAY(String))))
    )
    avg_sentiment, avg_confidence = (await db.execute(sentiment_query)).one_or_none() or (0, 0)

    sentiment_label = (
        "Bullish" if avg_sentiment > 0.15 else
        "Bearish" if avg_sentiment < -0.15 else
        "Neutral"
    )

    spotlight = await get_spotlight_signals(db, min_confidence=0.6)

    return {
        "ticker": ticker,
        "avg_sentiment": round(avg_sentiment or 0, 3),
        "impact_confidence": round(avg_confidence or 0, 3),
        "sentiment_label": sentiment_label,
        "news": news,
        "spotlight": spotlight,
        "trending": trending,
    }

# ----------------------------------------------------
# Ticker Sentiment History (🚀 FIXED)
# ----------------------------------------------------
@router.get("/ticker/sentiment-history")
async def get_sentiment_history(ticker: str, db: AsyncSession = Depends(get_db)):
    ticker = ticker.upper().strip()

    q = (
        select(
            News.processed_at.label("timestamp"),
            News.sentiment_score,
            News.impact_confidence,
            News.impact_label,
        )
        .where(func.upper(ticker) == func.any(func.cast(News.tickers, ARRAY(String))))
        .order_by(News.processed_at.desc())
        .limit(50)
    )
    rows = (await db.execute(q)).all()

    return [
        {
            "timestamp": r.timestamp,
            "sentiment_score": r.sentiment_score,
            "impact_label": r.impact_label,
            "impact_confidence": r.impact_confidence,
        }
        for r in rows
    ]


# ----------------------------------------------------
# Sector Summary
# ----------------------------------------------------
@router.get("/insights/sector-summary")
async def sector_summary(db: AsyncSession = Depends(get_db)):
    q = (
        select(
            Sector.name,
            func.avg(News.sentiment_score),
            func.count(News.id),
        )
        .join(News, News.sector_id == Sector.id)
        .group_by(Sector.name)
        .order_by(func.avg(News.sentiment_score).desc())
    )
    result = await db.execute(q)

    return [
        {
            "sector": r[0],
            "avg_sentiment": round(r[1] or 0, 3),
            "news_count": r[2],
        }
        for r in result.fetchall()
    ]


# ----------------------------------------------------
# Top Bullish / Bearish Stocks
# ----------------------------------------------------
@router.get("/insights/top-stocks")
async def get_top_stocks(db: AsyncSession = Depends(get_db), limit: int = 5):
    q = (
        select(
            func.unnest(News.tickers).label("ticker"),
            func.avg(News.sentiment_score),
            func.count(News.id).label("mentions"),
        )
        .group_by("ticker")
        .having(func.count(News.id) >= 2)
        .limit(limit * 2)
    )

    rows = (await db.execute(q)).all()

    sorted_rows = sorted(rows, key=lambda x: x[1] or 0)
    return {
        "top_bullish": [{"ticker": r[0], "avg_sentiment": round(r[1], 3), "mentions": r[2]} for r in sorted_rows[-limit:]],
        "top_bearish": [{"ticker": r[0], "avg_sentiment": round(r[1], 3), "mentions": r[2]} for r in sorted_rows[:limit]],
    }


# ----------------------------------------------------
# Spotlight Signals
# ----------------------------------------------------
@router.get("/signals/spotlight")
async def get_spotlight(
    limit: int = 20,
    min_confidence: float = 0.6,
    db: AsyncSession = Depends(get_db),
):
    data = await get_spotlight_signals(db, min_confidence=min_confidence)
    if not data:
        raise HTTPException(status_code=404, detail="No signals found")
    return {"results": data}


# ----------------------------------------------------
# Hot Stocks (Trending + Sentiment)
# ----------------------------------------------------
@router.get("/signals/hot")
async def get_hot_stocks(db: AsyncSession = Depends(get_db), limit: int = 10):
    q = (
        select(
            func.unnest(News.tickers).label("ticker"),
            func.count(News.id).label("mentions"),
            func.coalesce(func.avg(News.sentiment_score), 0).label("avg_sentiment")
        )
        .group_by("ticker")
        .order_by(func.count(News.id).desc())
        .limit(limit)
    )

    rows = (await db.execute(q)).all()

    return [
        {
            "ticker": r[0],
            "mentions": r[1],
            "avg_sentiment": round(r[2] or 0, 3),
        }
        for r in rows if r[0]
    ]
