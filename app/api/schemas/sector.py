from pydantic import BaseModel

class SectorRead(BaseModel):
    id: int
    name: str
    description: str | None

    class Config:
        orm_mode = True
