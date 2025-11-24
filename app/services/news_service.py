from sqlalchemy.ext.asyncio import AsyncSession
from app.core import db
from app.models.news import News
from sqlalchemy.future import select
from datetime import datetime
from datetime import timezone
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.news import News

class NewsService:

    @staticmethod
    async def create(db: AsyncSession, payload: dict) -> News:
        news = News(
            source=payload.get("source"),
            url=payload.get("url"),
            title=payload.get("title"),
            content=payload.get("content"),
            published_at=payload.get("published_at"),
            sector_id=0  # default sector_id
        )
        db.add(news)
        await db.commit()
        await db.refresh(news)
        return news

    @staticmethod
    async def list_recent(db: AsyncSession, limit: int = 50):
        q = select(News).order_by(News.published_at.desc()).limit(limit)
        res = await db.execute(q)
        return res.scalars().all()

    @staticmethod

    @staticmethod
    async def update_sentiment(
        db: AsyncSession,
        news_id: int,
        score: float,
        label: str,
        sector_id: int | None = None
):
        q = await db.get(News, news_id)
        if q is None:
            return None

        q.sentiment_score = score # type: ignore
        q.sentiment_label = label # type: ignore
        q.processed_at = datetime.now(timezone.utc) # type: ignore

        if sector_id is not None:
            q.sector_id = sector_id  # type: ignore

        db.add(q)
        await db.commit()
        await db.refresh(q)
        return q
