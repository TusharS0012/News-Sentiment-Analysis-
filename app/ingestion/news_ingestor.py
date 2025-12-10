import httpx
import yfinance as yf
from datetime import datetime
from typing import Any, Dict, List
import re
from app.api.schemas import news
from app.core.config import settings
from app.services.news_service import NewsService
from app.core.db import AsyncSessionLocal

MEDIASTACK_ENDPOINT = "http://api.mediastack.com/v1/news"
ALPHA_VANTAGE_ENDPOINT = "https://www.alphavantage.co/query"


class NewsIngestor:
    def __init__(
        self,
        mediastack_key: str = settings.NEWS_API_KEY,
        alpha_key: str = settings.ALPHA_VANTAGE_API_KEY,
    ):
        self.mediastack_key = mediastack_key
        self.alpha_key = alpha_key

    # ----------- MEDIASTACK FETCH -------------
    async def fetch_from_mediastack(self, limit: int = 10) -> List[Dict[str, Any]]:
        params = {
            "access_key": self.mediastack_key,
            "countries": "in",
            "languages": "en",
            "categories": "business",
            "limit": limit,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(MEDIASTACK_ENDPOINT, params=params)
            r.raise_for_status()
            print("Fetched Mediastack news")
            return r.json().get("data", [])

    def normalize_mediastack(self, item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "source": item.get("source"),
            "title": item.get("title"),
            "content": item.get("description") or item.get("content"),
            "url": item.get("url"),
            "published_at": self.parse_dt(item.get("published_at")),
            "tickers": [],
            "language": item.get("language"),
            # Keep original response in raw_payload
            "raw_payload": item,
        }

    # ----------- ALPHA VANTAGE FETCH -------------
    async def fetch_from_alpha_vantage(self, tickers: str = "") -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {
            "function": "NEWS_SENTIMENT",
            "apikey": self.alpha_key,
            "limit": 50,
        }
        if tickers:
            params["tickers"] = tickers

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(ALPHA_VANTAGE_ENDPOINT, params=params)
            r.raise_for_status()
            print("Fetched AlphaVantage news")
            return r.json().get("feed", [])

    def normalize_alpha(self, item: Dict[str, Any]) -> Dict[str, Any]:
        # Convert timestamp (YYYYMMDDTHHMM -> datetime)
        raw_time = item.get("time_published")
        published_at = None
        if raw_time:
            try:
                published_at = datetime.strptime(raw_time, "%Y%m%dT%H%M")
            except Exception:
                published_at = None

        # Extract top ticker by highest relevance
        primary_ticker = None
        if item.get("ticker_sentiment"):
            primary_ticker = max(
                item["ticker_sentiment"],
                key=lambda x: float(x.get("relevance_score", 0)),
            ).get("ticker")

        return {
            "source": item.get("source"),
            "title": item.get("title"),
            "content": item.get("summary"),
            "url": item.get("url"),
            "published_at": published_at,
            "tickers": [primary_ticker] if primary_ticker else [],
            "language": "en",
            "sentiment_score": item.get("overall_sentiment_score"),
            "sentiment_label": item.get("overall_sentiment_label"),
            # Keep the entire AlphaVantage item for future use
            "raw_payload": item,
        }

    # ----------- YAHOO FINANCE FETCH -------------
    async def fetch_from_yahoo(self) -> List[Dict[str, Any]]: 
        try:
            news=yf.Ticker("^NSEI").news
            print("Fetched Yahoo news")
            return news[:10] if news else []
        except Exception:
            return []

    def normalize_yahoo(self, item: Dict[str, Any]) -> Dict[str, Any]:
        content = item.get("content") or {}

        title = content.get("title")
        summary = content.get("summary")

        # Canonical URL > click-through > None
        url = (
            (content.get("canonicalUrl") or {}).get("url")
            or (content.get("clickThroughUrl") or {}).get("url")
        )

        # Publish time can be ISO string or int timestamp
        raw_time = content.get("pubDate") or item.get("providerPublishTime")
        published_at = self.parse_dt(raw_time)

        source = (content.get("provider") or {}).get("displayName")

        # 🔍 Extract tickers from HTML links inside description
        html = content.get("description") or ""
        raw_matches = re.findall(r'quote/([A-Za-z0-9\.\-%]+)', html)

        # Decode URL-encoded symbols like %5E (^)
        tickers = [t.replace('%5E', '^').upper() for t in raw_matches]
        return {
            "source": source,
            "title": title,
            "content": summary,
            "url": url,
            "published_at": published_at,
            "tickers": tickers,   # 🔥 now real values instead of []
            "language": "en",
            "raw_payload": item,
        }
    def parse_dt(self, raw: Any):
        if not raw:
            return None
        try:
            # Yahoo sometimes gives a Unix timestamp or ISO string
            if isinstance(raw, int):
                return datetime.utcfromtimestamp(raw)
            return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except Exception:
            return None
