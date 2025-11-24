import requests
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.sector import Sector
from app.core.config import settings

API_URL = "https://router.huggingface.co/hf-inference/models/facebook/bart-large-mnli"
headers = {"Authorization": f"Bearer {settings.HF_API_TOKEN}"}

async def detect_sector(db: AsyncSession, text: str) -> int | None:
    if not text or len(text) < 15:
        return None

    # Get sector names from DB
    result = await db.execute(select(Sector.name))
    sector_labels = [row[0] for row in result.all()]

    if not sector_labels:
        logging.warning("⚠ No sectors found in DB")
        return None

    try:
        payload = {
            "inputs": text[:500],
            "parameters": {"candidate_labels": sector_labels}
        }

        res = requests.post(API_URL, json=payload, headers=headers).json()

        if isinstance(res, list) and len(res) > 0:
            best = res[0]
            best_label = best["label"]
            best_score = best["score"]
        else:
            logging.error("❌ Unexpected response format")
            return None

        if best_score < 0.55:
            return None

        q = select(Sector).where(Sector.name == best_label)
        result = await db.execute(q)
        sector_obj = result.scalars().first()
        return sector_obj.id if sector_obj else None # type: ignore

    except Exception as e:
        logging.error(f"❌ Sector detection error: {e}")
        return None
