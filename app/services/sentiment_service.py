from app.sentiment.llm_client import HFClient

class SentimentService:
    @staticmethod
    async def analyze_text(text: str) -> dict:
        # HF client returns a dict with `sentiment` (-1..1) and `confidence` and `rationale`
        return await HFClient.analyze_text(text)
