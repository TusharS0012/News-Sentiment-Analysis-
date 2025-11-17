# app/schemas/news.py

from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


# -----------------------------------------------------
# CREATE SCHEMA (incoming payload for POST /news)
# -----------------------------------------------------
class NewsCreate(BaseModel):
    source: Optional[str] = None
    url: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    published_at: Optional[datetime] = None


# -----------------------------------------------------
# READ SCHEMA (what API returns)
# -----------------------------------------------------
class NewsRead(BaseModel):
    id: int
    source: Optional[str] = None
    url: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    published_at: Optional[datetime] = None
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = None

    # Pydantic V2 replacement for orm_mode = True
    model_config = {"from_attributes": True}
