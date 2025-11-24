from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.ingestion.news_ingestor import NewsIngestor
from app.analytics.aggregator import compute_and_store_15min_aggregates
from app.sentiment.llm_client import HFClient
from app.core.db import AsyncSessionLocal
from app.services.news_service import NewsService
from app.services.sector_detection import detect_sector
from datetime import datetime, timezone

scheduler = AsyncIOScheduler()

def start_scheduler():
    scheduler.add_job(
        run_ingest_and_analyze,
        "interval",
        minutes=10,
        id="ingest_job",
        next_run_time=datetime.now(timezone.utc),
        misfire_grace_time=300
    )

    scheduler.add_job(
        run_aggregator,
        "interval",
        minutes=15,
        id="agg_job",
        next_run_time=datetime.now(timezone.utc),
        misfire_grace_time=120
    )

    scheduler.start()


async def run_ingest_and_analyze():
    ingestor = NewsIngestor()
    articles = await ingestor.fetch_from_mediastack(limit=20)

    async with AsyncSessionLocal() as db:
        for a in articles:

            # Fixing date parsing
            raw_date = a.get("published_at") or a.get("publishedAt")
            published_at = None
            if raw_date:
                try:
                    published_at = datetime.fromisoformat(
                        raw_date.replace("Z", "+00:00")
                    ).astimezone(timezone.utc)  # ensure timezone-aware
                except:
                    published_at = None

            payload = {
                "source": a.get("source"),
                "url": a.get("url"),
                "title": a.get("title"),
                "content": a.get("content") or a.get("description"),
                "published_at": published_at,
            }

            try:
                news = await NewsService.create(db, payload)

                text = f"{payload.get('title', '')}\n\n{payload.get('content', '')}"

                # FinBERT sentiment
                res = await HFClient.analyze_text(text)
                print("FinBERT sentiment:", res)

                label = res.get("label", "neutral")
                score = res.get("sentiment", 0.0)

                # Sector Detection
                sector_id = await detect_sector(db, text)

                # Update news record
                await NewsService.update_sentiment(
                    db=db,
                    news_id=news.id, # type: ignore
                    score=score,
                    label=label,
                    sector_id=sector_id
                )

            except Exception as e:
                print("⛔ ingestion error:", e)
                await db.rollback()


async def run_aggregator():
    try:
        async with AsyncSessionLocal() as db:
            await compute_and_store_15min_aggregates(db)
            await db.commit()
    except Exception as e:
        print("⛔ aggregator error:", e)
 