from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import inspect, text

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
from app.api.routes.daily_planner import router as daily_planner_router
from app.api.routes.assistant import router as assistant_router
from app.api.routes.profile import router as profile_router
from app.api.routes.notifications import router as notifications_router
from app.db.session import Base, engine
# Register model tables before creating the local SQLite development schema.
from app import models


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.environment == "development" and engine.dialect.name == "sqlite":
        Base.metadata.create_all(bind=engine)
        task_columns = {column["name"] for column in inspect(engine).get_columns("tasks")}
        if "notes" not in task_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE tasks ADD COLUMN notes TEXT"))
        user_columns = {column["name"] for column in inspect(engine).get_columns("users")}
        appearance_columns = {
            "accent_color": "VARCHAR(20) NOT NULL DEFAULT 'blue'",
            "density": "VARCHAR(20) NOT NULL DEFAULT 'comfortable'",
            "font_size": "VARCHAR(20) NOT NULL DEFAULT 'medium'",
            "use_ai_planning": "BOOLEAN NOT NULL DEFAULT 1",
            # Additive local-development compatibility: preserve existing accounts.
            "email_verified": "BOOLEAN NOT NULL DEFAULT 1",
            "two_factor_enabled": "BOOLEAN NOT NULL DEFAULT 0",
            "token_version": "INTEGER NOT NULL DEFAULT 0",
        }
        with engine.begin() as connection:
            for column, definition in appearance_columns.items():
                if column not in user_columns:
                    connection.execute(text(f"ALTER TABLE users ADD COLUMN {column} {definition}"))
        integration_columns = {column["name"] for column in inspect(engine).get_columns("integrations")}
        if "last_synced_at" not in integration_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE integrations ADD COLUMN last_synced_at DATETIME"))
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
app.include_router(daily_planner_router)
app.include_router(assistant_router)

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
app.include_router(profile_router, prefix="/api")
app.include_router(notifications_router)

app.include_router(integrations_router)

@app.get("/")
def root():
    return {"message": "AURA API is running"}
