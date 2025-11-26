import logging
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.sector import Sector
from app.core.config import settings

HF_API_URL = "https://router.huggingface.co/hf-inference/models/joeddav/xlm-roberta-large-xnli"
HF_HEADERS = {"Authorization": f"Bearer {settings.HF_API_TOKEN}"}

SECTOR_CONF_THRESHOLD = 0.55  # Adjustable threshold

async def detect_sector(db: AsyncSession, text: str) -> int | None:
    """
    Detect sector using HuggingFace Zero-Shot Classifier.
    Returns sector_id or None.
    """

    if not text or len(text.strip()) < 15:
        return None

    # 🔹 Fetch sector names from database
    sector_query = await db.execute(select(Sector.name))
    sector_labels = [row[0] for row in sector_query.all()]
    if not sector_labels:
        logging.warning("⚠ No sectors found in database")
        return None

    try:
        payload = {
        "inputs": text[:500],
        "parameters": {"candidate_labels": sector_labels, "multi_class": False}
}

        # 🔄 Async request — replaces blocking requests.post
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(HF_API_URL, headers=HF_HEADERS, json=payload)

        response.raise_for_status()
        res = response.json()

        # 🛠 HuggingFace real response format
        # {
        #   "sequence": "...",
        #   "labels": [...],
        #   "scores": [...]
        # }
        
        if not isinstance(res, dict) or "labels" not in res:
            logging.error(f"Unexpected response format: {res}")
            return None

        # 🏆 Pick best label
        best_label = res["labels"][0]
        best_score = float(res["scores"][0])

        logging.info(f"🔍 Sector detected: {best_label} ({best_score:.2f})")

        if best_score < SECTOR_CONF_THRESHOLD:
            logging.info("⚠ Sector confidence too low — skipping")
            return None

        # 🔗 Get sector_id
        q = select(Sector).where(Sector.name == best_label)
        result = await db.execute(q)
        sector_obj = result.scalars().first()
        return sector_obj.id if sector_obj else None #type: ignore

    except Exception as e:
        logging.error(f"❌ Sector detection error: {e}")
        return None
