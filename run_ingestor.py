import asyncio
from app.ingestion.news_ingestor import NewsIngestor

async def main():
    ingestor = NewsIngestor()
    await ingestor.ingest_once("stock market")

asyncio.run(main())
