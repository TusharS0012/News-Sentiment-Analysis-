from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.sector import Sector
from typing import List

class SectorService:

    @staticmethod
    async def get_all(db: AsyncSession) -> List[Sector]:
        q = select(Sector).order_by(Sector.name)
        result = await db.execute(q)
        return list(result.scalars().all())

    @staticmethod
    async def create(db: AsyncSession, name: str, description: str | None = None) -> Sector:
        sector = Sector(name=name, description=description)
        db.add(sector)
        await db.commit()
        await db.refresh(sector)
        return sector
