from huggingface_hub import InferenceClient
from app.core.config import settings

# Create properly configured inference client
client = InferenceClient(
    api_key=settings.HF_API_TOKEN,
    provider="hf-inference"
)

class HFClient:

    @staticmethod
    async def analyze_text(text: str) -> dict:
        """
        Use ProsusAI/finbert for sentiment (no prompts, no JSON).
        """        
        try:
            results = client.text_classification(
                model=settings.HF_MODEL,
                text=text
            )
            print(results)
            # results is a list of dicts sorted by score
            # Example:
            # [{"label": "neutral", "score": 0.83}, ...]

            # Pick the top result
            top = results[0]
            label = top["label"].lower()
            confidence = float(top["score"])

            # Convert positive/negative/neutral → -1 .. +1
            if label == "positive":
                sentiment = confidence
            elif label == "negative":
                sentiment = -confidence
            else:
                sentiment = 0.0

            return {
                "sentiment": sentiment,
                "confidence": confidence,
                "label": label
            }

        except Exception as e:
            print("FinBERT error:", e)
            return {"sentiment": 0.0, "confidence": 0.0, "label": "neutral"}
