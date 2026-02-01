from datetime import datetime

from pydantic import BaseModel, Field


class RebarLengthBase(BaseModel):
    bar_mark: str = Field(..., pattern=r"^#\d+")
    fc_21_mpa_m: float = Field(..., gt=0)
    fc_24_mpa_m: float = Field(..., gt=0)
    fc_28_mpa_m: float = Field(..., gt=0)


class RebarLengthRead(RebarLengthBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
