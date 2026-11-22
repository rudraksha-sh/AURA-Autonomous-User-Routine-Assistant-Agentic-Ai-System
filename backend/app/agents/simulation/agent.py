from sqlalchemy.orm import Session

from app.agents.simulation.schemas import WhatIfRequest, WhatIfResponse
from app.services.what_if_service import simulate_daily_schedule


def simulate(db: Session, user_id: int, request: WhatIfRequest) -> WhatIfResponse:
    return simulate_daily_schedule(db, user_id, request)
