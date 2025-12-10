from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timezone

from app.ingestion.news_ingestor import NewsIngestor
from app.analytics.aggregator import compute_and_store_sentiment_aggregates
from app.sentiment.llm_client import HFClient
from app.core.db import AsyncSessionLocal
from app.services.news_service import NewsService
from app.services.news_signal_service import enrich_news_batch
from app.services.sector_detection import detect_sector


scheduler = AsyncIOScheduler()


def start_scheduler():
    scheduler.add_job(
        run_ingest_and_analyze,
        "interval",
        minutes=30,  
        id="ingest_job",
        next_run_time=datetime.now(timezone.utc),
        misfire_grace_time=120,
    )

    scheduler.add_job(
        run_aggregator,
        "interval",
        minutes=60, 
        id="agg_job",
        next_run_time=datetime.now(timezone.utc),
        misfire_grace_time=120,
    )

    scheduler.start()


async def run_ingest_and_analyze():
    ingestor = NewsIngestor()

    mediastack = await ingestor.fetch_from_mediastack(limit=15)
    alpha = await ingestor.fetch_from_alpha_vantage()
    yahoo = await ingestor.fetch_from_yahoo()

    articles = (
        [ingestor.normalize_mediastack(a) for a in mediastack]
        + [ingestor.normalize_alpha(a) for a in alpha]
        + [ingestor.normalize_yahoo(a) for a in yahoo]
    )

    print(f"📰 Total normalized articles: {len(articles)}")

    async with AsyncSessionLocal() as db:
        inserted_news = []

        # Step 1️⃣ Insert news + Sentiment
        for article in articles:
            if not article.get("title") or not article.get("url"):
                continue

            try:
                news = await NewsService.create(db, article)
                if not news:
                    continue  # duplicate skipped

                text = f"{news.title}\n\n{news.content or ''}"
                res = await HFClient.analyze_text(text)

                await NewsService.update_sentiment(
                    db,
                    news_id=news.id,  # type: ignore
                    score=res.get("sentiment", 0.0),
                    label=res.get("label", "neutral"),
                )

                inserted_news.append(news.id)  # type: ignore

            except Exception as e:
                print("⛔ ingestion error:", e)
                await db.rollback()

        # Step 2️⃣ Enrichment: tickers + impact + topics
        enriched_count = await enrich_news_batch(db, batch_size=10)
        print(f"💡 Enrichment: {enriched_count} updated")

        # Step 3️⃣ Sector detection AFTER tickers are finalized
        for nid in inserted_news:
            try:
                news = await NewsService.get_by_id(db, nid) #type: ignore
                if not news:
                    continue

                text = f"{news.title} {news.content or ''}"
                sector_id = await detect_sector(db, text)

                if sector_id:
                    await NewsService.update_enrichment(
                        db=db,
                        news_id=nid,
                        sector_id=sector_id,
                    )

            except Exception as e:
                print(f"⚠ Sector mapping failed for {nid}: {e}")


async def run_aggregator():
    try:
        async with AsyncSessionLocal() as db:
            await compute_and_store_sentiment_aggregates(db)
            await db.commit()
            print("📊 Aggregates updated")
    except Exception as e:
        print("⛔ aggregator error:", e)
