from fastapi import FastAPI

from app.api.routes.tasks import router as tasks_router

from app.api.routes.auth import router as auth_router
from app.core.config import settings

from app.api.routes.ai import router as ai_router

from app.api.routes.goals import router as goals_router

app = FastAPI(
    title=settings.app_name,
)

app.include_router(ai_router)

app.include_router(
    goals_router,
    prefix="/api",
)

app.include_router(
    tasks_router,
    prefix="/api",
)

app.include_router(
    auth_router,
    prefix="/api",
)


@app.get("/")
def root():
    return {"message": "AURA API is running"}