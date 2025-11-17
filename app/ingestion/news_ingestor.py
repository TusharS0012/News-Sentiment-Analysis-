import httpx
from datetime import datetime
from app.core.config import settings
from app.services.news_service import NewsService
from app.core.db import AsyncSessionLocal


MEDIASTACK_ENDPOINT = "http://api.mediastack.com/v1/news"


class NewsIngestor:
    def __init__(self, api_key: str = settings.NEWS_API_KEY):
        self.api_key = api_key

    async def fetch_from_mediastack(self, limit: int = 10):
        params = {
            "access_key": self.api_key,
            "countries": "in",
            "languages": "en",
            "categories": "business",
            "limit": limit,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(MEDIASTACK_ENDPOINT, params=params)
            r.raise_for_status()
            data = r.json()
            return data.get("data", [])

    async def ingest_once(self, keywords: str = "stock market"):
        articles = await self.fetch_from_mediastack(limit=10)

        async with AsyncSessionLocal() as db:
            for a in articles:

                # parse datetime safely
                published_raw = a.get("published_at")
                published_at = None
                if published_raw:
                    try:
                        published_at = datetime.fromisoformat(published_raw.replace("Z", "+00:00"))
                    except:
                        published_at = None

                payload = {
                    "source": a.get("source"),
                    "url": a.get("url"),
                    "title": a.get("title"),
                    "content": a.get("description") or a.get("content"),
                    "published_at": published_at,
                }

                try:
                    await NewsService.create(db, payload)
                except Exception as e:
                    print("Ingest Error:", e)
                    continue
