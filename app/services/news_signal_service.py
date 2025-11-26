# app/services/news_signal_service.py

from __future__ import annotations
import json
import textwrap
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from google.genai import Client
from app.models.news import News
from app.services.sector_service import SectorService
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize Gemini client
client = Client(api_key=settings.GEMINI_API_KEY).aio

@dataclass
class NewsSignal:
    news_id: int
    tickers: List[str]
    impact_label: str
    impact_confidence: float
    impact_summary: str
    topics: List[str] | None = None


# ------------------------------------------------------------
# Fetch unenriched news
# ------------------------------------------------------------
async def fetch_unenriched_news(db: AsyncSession, *, limit: int = 10) -> List[News]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
    q = (
        select(News)
        .where(News.processed_at.isnot(None))
        .where((News.impact_label.is_(None)) | (func.cardinality(News.tickers) == 0))
        .where(News.published_at >= cutoff)
        .order_by(News.processed_at.desc())
        .limit(limit)
    )
    return (await db.execute(q)).scalars().all() #type: ignore


# ------------------------------------------------------------
# Gemini prompt
# ------------------------------------------------------------
def build_llm_prompt(news_batch: List[News]) -> str:
    items = [
        {
            "id": n.id,
            "headline": n.title or "",
            "snippet": (n.content or "")[:600],
            "published_at": n.published_at.isoformat() if n.published_at else "unknown"  # type: ignore
        }
        for n in news_batch
    ]

    prompt = f"""
You are an AI financial analyst.

For EACH news item, return ONLY valid JSON, in the following exact structure:

{{
  "results": [
    {{
      "id": <news_id>,
      "tickers": ["AAPL", "RELIANCE.NS"],
      "impact_label": "bullish" | "bearish" | "neutral" | "uncertain",
      "impact_confidence": 0.0 - 1.0,
      "impact_summary": "1-2 sentences explaining market impact",
      "topics": ["Earnings", "AI", "Regulation"]
    }}
  ]
}}

⚠ Rules:
• Return ONLY valid JSON – no markdown, no code blocks, no explanation text.
• Use only valid stock tickers (US: AAPL, TSLA; Indian: TCS.NS, HDFCBANK.NS).
• tickers must be uppercase.
• If unsure → tickers: [], impact_label: "uncertain", impact_confidence: 0.5
• DO NOT wrap in triple backticks or add comments.

Here is the news batch:
{json.dumps(items, indent=2)}

Now return exactly:
{{
  "results": [
    {{
      "id": <news_id>,
      "tickers": [],
      "impact_label": "uncertain",
      "impact_confidence": 0.5,
      "impact_summary": "",
      "topics": []
    }}
  ]
}}
"""
    return textwrap.dedent(prompt).strip()


# ------------------------------------------------------------
# Call Gemini (correct version)
# ------------------------------------------------------------
async def call_llm_for_signals(prompt: str) -> dict:
    try:
        response = await client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        raw_text = response.text.strip() # type: ignore

        logger.info(f"Gemini raw response:\n{raw_text}")

        # Try direct JSON decode
        try:
            data = json.loads(raw_text)

            # If response is already a list, wrap it like {"results": [...]}
            if isinstance(data, list):
                return {"results": data}

            # If it's a dict, keep as is
            if isinstance(data, dict):
                return data

        except json.JSONDecodeError:
            # Attempt to recover by extracting first valid JSON object/array
            match = re.search(r'(\[.*\]|\{.*\})', raw_text, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(0))
                    if isinstance(data, list):
                        return {"results": data}
                    if isinstance(data, dict):
                        return data
                except Exception:
                    pass

        logger.error("Failed to parse Gemini response.")
        return {}

    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return {}

# ------------------------------------------------------------
# Parse response safely
# ------------------------------------------------------------
def parse_llm_signals(raw: Dict[str, Any]) -> List[NewsSignal]:
    return [
        NewsSignal(
            news_id=int(item.get("id")),
            tickers=[t.upper() for t in item.get("tickers", [])],
            impact_label=item.get("impact_label", "uncertain"),
            impact_confidence=float(item.get("impact_confidence") or 0),
            impact_summary=item.get("impact_summary", ""),
            topics=item.get("topics", [])
        )
        for item in raw.get("results", [])
        if item.get("id")
    ]


# ------------------------------------------------------------
# Apply to DB
# ------------------------------------------------------------
async def enrich_news_batch(db: AsyncSession, *, batch_size: int = 10) -> int:
    news_batch = await fetch_unenriched_news(db, limit=batch_size)
    if not news_batch:
        logger.info("No news to enrich.")
        return 0

    prompt = build_llm_prompt(news_batch)
    raw_output = await call_llm_for_signals(prompt)
    signals = parse_llm_signals(raw_output)

    updated = 0
    for sig in signals:
        news_item = next((n for n in news_batch if n.id == sig.news_id), None) #type: ignore
        if not news_item:
            continue

        news_item.tickers = list(set((news_item.tickers or []) + sig.tickers)) #type: ignore
        news_item.impact_label = sig.impact_label #type: ignore
        news_item.impact_confidence = sig.impact_confidence #type: ignore
        news_item.impact_summary = sig.impact_summary #type: ignore
        news_item.topics = sig.topics

        sector_id = await SectorService.map_tickers_to_sector(db, sig.tickers)
        if sector_id:
            news_item.sector_id = sector_id #type: ignore

        db.add(news_item)
        updated += 1

    if updated:
        await db.commit()

    logger.info(f"✨ Enriched {updated} news records.")
    return updated


# ------------------------------------------------------------
# Spotlight API
# ------------------------------------------------------------
async def get_spotlight_signals(db: AsyncSession, min_confidence: float = 0.6):
    q = (
        select(News)
        .where(News.impact_confidence >= min_confidence)
        .where(func.cardinality(News.tickers) > 0)
        .order_by(News.processed_at.desc())
        .limit(20)
    )
    items = (await db.execute(q)).scalars().all()

    return [
        {
            "id": n.id,
            "title": n.title,
            "tickers": n.tickers,
            "sentiment": n.sentiment_score,
            "impact_summary": n.impact_summary,
            "impact_label": n.impact_label,
            "impact_confidence": n.impact_confidence,
            "topics": n.topics,
            "published_at": n.published_at,
            "source": n.source,
            "image_url": n.image_url,
        }
        for n in items
    ]
