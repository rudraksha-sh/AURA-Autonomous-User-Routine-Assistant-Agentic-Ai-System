from typing import Literal

from pydantic import BaseModel


class VerificationReceipt(BaseModel):
    status: Literal["verified", "unverified"]
    task_ids: list[int]
