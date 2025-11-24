import asyncio
from app.core.db import AsyncSessionLocal
from app.services.sector_service import SectorService

SECTORS = [
    ("Finance", "Stocks, banks, markets, IPOs, investments"),
    ("Technology", "AI, IT, software, cloud, electronics"),
    ("Energy", "Oil, power, renewable energy, utilities"),
    ("Pharma", "Medicine, biotech, healthcare, FDA"),
    ("Automobile", "Cars, EVs, transport, Tesla"),
]

async def seed_sectors():
    async with AsyncSessionLocal() as db:
        for name, desc in SECTORS:
            print(f"Adding sector: {name}")
            await SectorService.create(db, name, desc)
        print("Sectors added successfully!")

asyncio.run(seed_sectors())
