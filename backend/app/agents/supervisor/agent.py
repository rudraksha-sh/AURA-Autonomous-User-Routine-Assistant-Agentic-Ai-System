from app.agents.supervisor.schemas import Intent


def route_intent(state) -> Intent:
    intent = state["intent"]
    if intent not in ("plan_goal", "simulate"):
        raise ValueError("Unsupported workflow intent")
    return intent
