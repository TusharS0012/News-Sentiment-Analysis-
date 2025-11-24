import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL","")
    HF_API_TOKEN: str = os.getenv("HF_API_TOKEN","")
    HF_MODEL: str = os.getenv("HF_MODEL","ProsusAI/finbert")
    NEWS_API_KEY: str = os.getenv("NEWS_API_KEY","271cf5cdc6b71250108e0a111cecf3c1")

settings = Settings()
