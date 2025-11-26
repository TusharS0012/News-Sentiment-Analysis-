from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app.models.news import News
from app.models.sentiment_aggregate import SentimentAggregate

WINDOW_MINUTES = 120  # 2 hours

async def compute_and_store_sentiment_aggregates(db: AsyncSession):
    """
    Create sector-level sentiment aggregates using latest processed news.
    Corrected to use one consistent timestamp, avoid unknown sector 0, and include confidence scoring.
    """
    # 🔹 Use one consistent timestamp from Python for accuracy
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=WINDOW_MINUTES)

    print(f"\n📊 Aggregating data from {window_start} to {now}")

    # 🔹 Aggregate only valid (processed) sentiment data
    q = (
        select(
            News.sector_id,
            func.avg(News.sentiment_score).label("avg_sentiment"),
            func.avg(News.impact_confidence).label("avg_confidence"),
            func.count(News.id).label("news_count"),
        )
        .where(News.processed_at >= window_start)
        .where(News.sector_id.isnot(None))  # avoid unassigned
        .where(func.cardinality(News.tickers) > 0)  # ensure relevance
        .group_by(News.sector_id)
    )

    result = await db.execute(q)
    rows = result.all()

    if not rows:
        print("⚠ No relevant sentiment data found in this time window.")
        return

    saved = 0
    for row in rows:
        sector_id = row.sector_id
        avg_sentiment = float(row.avg_sentiment or 0.0)
        avg_confidence = float(row.avg_confidence or 0.0)
        news_count = int(row.news_count or 0)

        print(f"📁 Saving → Sector {sector_id}, Avg sentiment {avg_sentiment}, Confidence {avg_confidence}, Count {news_count}")

        aggregate = SentimentAggregate(
            sector_id=sector_id,
            window_start=window_start,
            window_end=now,
            avg_sentiment=avg_sentiment,
            avg_relevance=avg_confidence,   # reuse impact_confidence as relevance score
            avg_price_change=0.0,           # reserved for future price API integration
            news_count=news_count,
        )
        db.add(aggregate)
        saved += 1

    await db.commit()
    print(f"💾 {saved} aggregates stored successfully.")
