from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, func
from app.core.db import Base

class SentimentAggregate(Base):
    __tablename__ = "sentiment_aggregates"

    id = Column(Integer, primary_key=True)
    sector_id = Column(Integer, nullable=False)
    window_start = Column(DateTime(timezone=True), nullable=False)
    window_end = Column(DateTime(timezone=True), nullable=False)
    avg_sentiment = Column(Float, nullable=True)
    news_count = Column(Integer, nullable=True)
    avg_relevance = Column(Float, nullable=True)
    avg_price_change = Column(Float, nullable=True)
    computed_at = Column(DateTime(timezone=True), server_default=func.now())
