from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.sector import Sector
from typing import List, Optional, Iterable
import logging


class SectorService:

    # Get all sectors
    @staticmethod
    async def get_all(db: AsyncSession) -> List[Sector]:
        result = await db.execute(select(Sector).order_by(Sector.name))
        return list(result.scalars().all())

    # Create new sector
    @staticmethod
    async def create(db: AsyncSession, name: str, description: str | None = None) -> Sector:
        sector = Sector(name=name, description=description)
        db.add(sector)
        await db.commit()
        await db.refresh(sector)
        return sector

    # 🔹 NEW — Assign sector based on tickers array
    @staticmethod
    async def map_tickers_to_sector(db: AsyncSession, tickers: Iterable[str]) -> Optional[int]:
        """
        Return sector_id for tickers like ["AAPL", "TCS.NS"]
        Requires Sector.tickers column to exist (VARCHAR[])
        """

        if not tickers:
            return None

        try:
            tickers = [t.upper().strip() for t in tickers if t]
            q = (
                select(Sector)
                .where(Sector.tickers.contains(tickers))  # PostgreSQL ARRAY overlap
            )
            result = await db.execute(q)
            sector = result.scalars().first()
            return sector.id if sector else None #type: ignore

        except Exception as e:
            logging.error(f"Sector mapping failed: {e}")
            return None

    # 🔹 NEW — Update list of tickers assigned to sector
    @staticmethod
    async def update_sector_tickers(db: AsyncSession, sector_id: int, tickers: List[str]):
        sector = await db.get(Sector, sector_id)
        if not sector:
            return None

        existing = set(sector.tickers or [])
        sector.tickers = list(existing.union({t.upper() for t in tickers}))

        db.add(sector)
        await db.commit()
        await db.refresh(sector)
        return sector

    # 🔹 NEW — Rule-Based Sector Detection Fallback (keywords)
    @staticmethod
    async def detect_sector_by_keywords(db: AsyncSession, text: str) -> Optional[int]:
        if not text:
            return None

        result = await db.execute(select(Sector))
        sectors = result.scalars().all()

        for sector in sectors:
            if sector.keywords:
                matches = [kw for kw in sector.keywords if kw.lower() in text.lower()]
                if matches:
                    return sector.id #type: ignore
        return None
