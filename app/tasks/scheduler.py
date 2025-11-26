from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timezone

from app.ingestion.news_ingestor import NewsIngestor
from app.analytics.aggregator import compute_and_store_sentiment_aggregates
from app.sentiment.llm_client import HFClient
from app.core.db import AsyncSessionLocal
from app.services.news_service import NewsService
from app.services.sector_detection import detect_sector
from app.services.news_signal_service import enrich_news_batch

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

    # 🔹 Fetch articles from ALL sources
    mediastack = await ingestor.fetch_from_mediastack(limit=15)
    alpha = await ingestor.fetch_from_alpha_vantage()
    yahoo = await ingestor.fetch_from_yahoo()

    # 🔹 Normalize them
    articles = (
        [ingestor.normalize_mediastack(a) for a in mediastack] +
        [ingestor.normalize_alpha(a) for a in alpha] +
        [ingestor.normalize_yahoo(a) for a in yahoo]
    )
    print(f"📰 Total normalized articles: {len(articles)}")

    async with AsyncSessionLocal() as db:
        for article in articles:
            try:
                news = await NewsService.create(db, article)

                text = f"{article.get('title', '')}\n\n{article.get('content', '')}"

                # Step 1: Sentiment
                res = await HFClient.analyze_text(text)
                await NewsService.update_sentiment(
                    db,
                    news_id=news.id,  # type: ignore
                    score=res.get("sentiment", 0.0),
                    label=res.get("label", "neutral")
                )

                # Step 2: Sector Detection
                sector_id = await detect_sector(db, text)
                await NewsService.update_enrichment(
                    db=db,
                    news_id=news.id,  # type: ignore
                    sector_id=sector_id
                )

            except Exception as e:
                print("⛔ ingestion error:", e)
                await db.rollback()

        # Step 3: LLM-based enrichment
        try:
            updated_count = await enrich_news_batch(db, batch_size=10)
            print(f"💡 LLM enrichment complete for {updated_count} news items.")
        except Exception as e:
            print("⛔ LLM enrichment error:", e)


async def run_aggregator():
    try:
        async with AsyncSessionLocal() as db:
            await compute_and_store_sentiment_aggregates(db)
            await db.commit()
    except Exception as e:
        print("⛔ aggregator error:", e)
