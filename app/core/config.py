import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL","")
    HF_API_TOKEN: str = os.getenv("HF_API_TOKEN","")
    HF_MODEL: str = os.getenv("HF_MODEL","ProsusAI/finbert")
    NEWS_API_KEY: str = os.getenv("NEWS_API_KEY","")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY","")
    ALPHA_VANTAGE_API_KEY: str = os.getenv("ALPHA_VANTAGE_API_KEY","")

settings = Settings()
