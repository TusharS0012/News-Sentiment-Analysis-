from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app.core.db import AsyncSessionLocal
from app.models.news import News
from app.models.sentiment_aggregate import SentimentAggregate

async def compute_and_store_15min_aggregates():
    """
    Compute average sentiment per sector for the last 15-minute window,
    and write one row per sector in sentiment_aggregates.
    """
    end = datetime.utcnow()
    start = end - timedelta(minutes=15)

    async with AsyncSessionLocal() as db:
        # group by sector_id
        q = (
            select(
                News.sector_id,
                func.avg(News.sentiment_score).label("avg_sentiment"),
                func.count(News.id).label("news_count"),
                func.avg(News.sentiment_score).label("avg_relevance")  # placeholder
            )
            .where(News.processed_at != None)
            .where(News.processed_at >= start)
            .where(News.processed_at <= end)
            .group_by(News.sector_id)
        )

        result = await db.execute(q)
        rows = result.all()
        for row in rows:
            sector_id = row[0] or 0
            avg_sentiment = float(row[1] or 0.0)
            news_count = int(row[2] or 0)

            aggregate = SentimentAggregate(
                sector_id=sector_id,
                window_start=start,
                window_end=end,
                avg_sentiment=avg_sentiment,
                news_count=news_count,
                avg_relevance=0.0,
                avg_price_change=0.0
            )
            db.add(aggregate)
        await db.commit()
