from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app.models.news import News
from app.models.sentiment_aggregate import SentimentAggregate

WINDOW_MINUTES = 240  # For testing (4 hours)

async def compute_and_store_15min_aggregates(db: AsyncSession):
    print(f"\n📊 Aggregating last {WINDOW_MINUTES} minutes from DB time...")

    # Use DB time instead of Python UTC time
    q = (
        select(
            News.sector_id,
            func.avg(News.sentiment_score).label("avg_sentiment"),
            func.count(News.id).label("news_count")
        )
        .where(News.processed_at != None)
        .where(News.processed_at >= func.now() - timedelta(minutes=WINDOW_MINUTES))
        .group_by(News.sector_id)
    )

    result = await db.execute(q)
    rows = result.all()

    if not rows:
        print("⚠ Still no matching sentiment data. Check timestamp alignment.")
        return

    for row in rows:
        sector_id = row.sector_id or 0
        avg_sentiment = float(row.avg_sentiment or 0.0)
        news_count = int(row.news_count or 0)

        print(f"📁 Saving aggregate → Sector {sector_id}, Avg {avg_sentiment:.2f}, Count {news_count}")

        aggregate = SentimentAggregate(
            sector_id=sector_id,
            window_start=func.now() - timedelta(minutes=WINDOW_MINUTES),
            window_end=func.now(),
            avg_sentiment=avg_sentiment,
            news_count=news_count,
            avg_relevance=0.0,
            avg_price_change=0.0
        )
        db.add(aggregate)

    await db.commit()
    print("💾 Aggregates committed to DB successfully.")
