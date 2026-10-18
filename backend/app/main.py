from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.tasks import router as tasks_router

from app.api.routes.auth import router as auth_router
from app.core.config import settings

from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.ai import router as ai_router

from app.api.routes.goals import router as goals_router

from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging

from app.core.security_headers import register_security_headers

from app.api.routes.integrations import router as integrations_router
from app.api.routes.planner import router as planner_router
from app.db.session import Base, engine
# Register model tables before creating the local SQLite development schema.
from app import models


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.environment == "development" and engine.dialect.name == "sqlite":
        Base.metadata.create_all(bind=engine)
    yield

configure_logging()

app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)

register_exception_handlers(app)

register_security_headers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ai_router)
app.include_router(planner_router)

app.include_router(
    goals_router,
    prefix="/api",
)

app.include_router(
    tasks_router,
    prefix="/api",
)

app.include_router(auth_router)

app.include_router(
    auth_router,
    prefix="/api",
)

app.include_router(integrations_router)

@app.get("/")
def root():
    return {"message": "AURA API is running"}
