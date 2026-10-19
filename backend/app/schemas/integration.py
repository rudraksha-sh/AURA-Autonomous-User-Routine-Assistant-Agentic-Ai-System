from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class GoogleIntegrationStatus(BaseModel):
    status: Literal["connected", "disconnected"]
    scopes: list[str]
    last_sync_at: datetime | None
