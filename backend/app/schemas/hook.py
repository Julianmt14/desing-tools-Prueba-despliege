from datetime import datetime

from pydantic import BaseModel, Field


class HookLengthBase(BaseModel):
    bar_mark: str = Field(..., pattern=r"^#\d+")
    longitudinal_90_m: float = Field(..., gt=0)
    longitudinal_180_m: float = Field(..., gt=0)
    stirrup_135_m: float | None = Field(default=None)


class HookLengthRead(HookLengthBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
