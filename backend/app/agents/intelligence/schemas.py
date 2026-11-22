from pydantic import BaseModel, Field


class CapacityFinding(BaseModel):
    remaining_minutes: int = Field(ge=0)
    fits_proposed_day: bool
