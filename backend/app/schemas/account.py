from typing import Literal

from pydantic import BaseModel


class AccountDeleteRequest(BaseModel):
    confirmation: Literal["DELETE"]
