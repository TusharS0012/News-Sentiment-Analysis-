from app.sentiment.llm_client import HFClient
from typing import Optional


class SentimentService:
    """
    Handles sentiment scoring + normalized output
    """

    @staticmethod
    async def analyze_text(text: str) -> Optional[dict]:
        """
        Returns normalized sentiment result:
        {
            "score": float (-1 to 1),
            "label": "Bullish/Bearish/Neutral",
            "confidence": 0.0 - 1.0,
            "rationale": str
        }
        """

        if not text or len(text.strip()) < 20:
            return None  # Avoid sending junk to API

        try:
            raw = await HFClient.analyze_text(text)
            score = float(raw.get("sentiment", 0))
            confidence = float(raw.get("confidence", 0))

            label = (
                "Bullish" if score > 0.15 else
                "Bearish" if score < -0.15 else
                "Neutral"
            )

            return {
                "score": round(score, 3),
                "label": label,
                "confidence": round(confidence, 3),
                "rationale": raw.get("rationale", ""),
            }

        except Exception as e:
            print(f"⚠ SentimentService error: {e}")
            return None
