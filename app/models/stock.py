from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.core.db import Base

class Stock(Base):
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(16), unique=True, nullable=False, index=True)
    company_name = Column(String(256), nullable=True)
    exchange = Column(String(32), nullable=True)
    sector_id = Column(Integer, ForeignKey("sectors.id"), nullable=True)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    sector = relationship("Sector", lazy="joined")
