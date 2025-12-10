from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timezone
from typing import List, Optional
import json
from sqlalchemy.exc import IntegrityError

from app.models.news import News


class NewsService:
    # -------------------------------------------------------------
    # GET BY ID
    # -------------------------------------------------------------
    @staticmethod
    async def get_by_id(db: AsyncSession, news_id: int) -> Optional[News]:
        return await db.get(News, news_id)

    # -------------------------------------------------------------
    # CREATE / INSERT NEWS
    # -------------------------------------------------------------
    @staticmethod
    async def create(db: AsyncSession, payload: dict) -> Optional[News]:
        # 🔹 Ensure JSON-safe raw_payload
        safe_payload: dict = {}
        for key, value in payload.items():
            if isinstance(value, datetime):
                safe_payload[key] = value.isoformat()
            else:
                try:
                    json.dumps(value)
                    safe_payload[key] = value
                except TypeError:
                    safe_payload[key] = str(value)

        # 🔹 Ensure tickers is always a proper list
        raw_tickers = payload.get("tickers") or []
        if isinstance(raw_tickers, str):
            try:
                raw_tickers = json.loads(raw_tickers)
            except Exception:
                raw_tickers = []
        if not isinstance(raw_tickers, list):
            raw_tickers = []

        news = News(
            source=safe_payload.get("source"),
            url=safe_payload.get("url"),
            title=safe_payload.get("title"),
            content=safe_payload.get("content"),
            published_at=payload.get("published_at"),
            tickers=raw_tickers,
            sector_id=payload.get("sector_id", 0),
            language=safe_payload.get("language"),
            raw_payload=safe_payload,
            sentiment_score=None,
            sentiment_label=None,
            impact_label=None,
            impact_confidence=None,
            impact_summary=None,
            processed_at=None,
        )

        db.add(news)
        try:
            await db.commit()
            await db.refresh(news)
            return news
        except IntegrityError:
            # ⚠ Duplicate URL (unique constraint) → ignore and rollback
            await db.rollback()
            return None

    # -------------------------------------------------------------
    # LIST RECENT NEWS
    # -------------------------------------------------------------
    @staticmethod
    async def list_recent(db: AsyncSession, limit: int = 50) -> List[News]:
        q = (
            select(News)
            .order_by(News.published_at.desc())
            .limit(limit)
        )
        result = await db.execute(q)
        return result.scalars().all()  # type: ignore

    # -------------------------------------------------------------
    # LIST NEWS BY SECTOR
    # -------------------------------------------------------------
    @staticmethod
    async def list_by_sector(
        db: AsyncSession,
        sector_id: int,
        limit: int = 50
    ) -> List[News]:
        q = (
            select(News)
            .where(News.sector_id == sector_id)
            .order_by(News.published_at.desc())
            .limit(limit)
        )
        result = await db.execute(q)
        return result.scalars().all()  # type: ignore

    # -------------------------------------------------------------
    # UPDATE SENTIMENT
    # -------------------------------------------------------------
    @staticmethod
    async def update_sentiment(
        db: AsyncSession,
        news_id: int,
        score: float,
        label: str,
    ) -> Optional[News]:
        news = await db.get(News, news_id)
        if not news:
            return None

        news.sentiment_score = score  # type: ignore
        news.sentiment_label = label  # type: ignore
        news.processed_at = datetime.now(timezone.utc)  # type: ignore

        db.add(news)
        await db.commit()
        await db.refresh(news)
        return news

    # -------------------------------------------------------------
    # UPDATE ENRICHMENT (Tickers, Impact, Sector)
    # -------------------------------------------------------------
    @staticmethod
    async def update_enrichment(
        db: AsyncSession,
        news_id: int,
        tickers: Optional[List[str]] = None,
        impact_label: Optional[str] = None,
        impact_confidence: Optional[float] = None,
        impact_summary: Optional[str] = None,
        sector_id: Optional[int] = None,
    ) -> Optional[News]:
        news = await db.get(News, news_id)
        if not news:
            return None

        # 🔹 Merge tickers safely
        if tickers:
            if isinstance(tickers, str):
                try:
                    tickers = json.loads(tickers)  # convert string → list
                except Exception:
                    tickers = []

            if isinstance(tickers, list):
                existing = set(news.tickers or [])  # type: ignore
                news.tickers = list(  # type: ignore
                    existing.union({t.upper() for t in tickers})
                )  # type: ignore

        # 🔹 Save impact fields
        if impact_label is not None:
            news.impact_label = impact_label  # type: ignore

        if impact_confidence is not None:
            news.impact_confidence = impact_confidence  # type: ignore

        if impact_summary is not None:
            news.impact_summary = impact_summary  # type: ignore

        # 🔹 Update sector only if not assigned (0 or None)
        if sector_id is not None and (news.sector_id is None or news.sector_id == 0):  # type: ignore
            news.sector_id = sector_id  # type: ignore

        news.processed_at = datetime.now(timezone.utc)  # type: ignore

        db.add(news)
        await db.commit()
        await db.refresh(news)
        return news
