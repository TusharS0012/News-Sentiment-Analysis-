from email.mime import image
from pydoc_data import topics
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, func
from sqlalchemy import ARRAY
from sqlalchemy.orm import relationship
from app.core.db import Base

class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True)
    source = Column(String(128), nullable=True)
    url = Column(String(1000), unique=True, nullable=True)
    title = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    tickers = Column(ARRAY(String), nullable=True)
    sector_id = Column(Integer, nullable=True)
    language = Column(String(16), nullable=True)
    raw_payload = Column(JSON, nullable=True)
    topics = Column(ARRAY(String), nullable=True)

    sentiment_score = Column(Float, nullable=True)
    sentiment_label = Column(String(32), nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    impact_label = Column(String, nullable=True)
    impact_confidence = Column(Float, nullable=True)
    impact_summary = Column(Text, nullable=True)
    image_url = Column(String(1000), nullable=True)
    ticker_sentiments= Column(JSON, nullable=True)
