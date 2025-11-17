from pydantic import BaseModel

class StockRead(BaseModel):
    id: int
    ticker: str
    company_name: str | None
    exchange: str | None
    sector_id: int | None

    class Config:
        orm_mode = True
