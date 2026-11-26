import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool

from app.api.routes.external_actions import router as external_actions_router
from app.api.routes.autonomy import router as autonomy_router
from app.api.routes.memory import router as memory_router
from app.api.routes.context import router as context_router
from app.api.routes.workflows import router as workflows_router
from app.api.routes.tasks import router as tasks_router

from app.api.routes.auth import router as auth_router
from app.core.config import settings

from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.ai import router as ai_router

from app.api.routes.goals import router as goals_router

from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.ingress import register_ingress_guard

from app.core.security_headers import register_security_headers
from app.core.request_size import RequestSizeLimit

from app.api.routes.integrations import router as integrations_router
from app.api.routes.planner import router as planner_router
from app.api.routes.daily_planner import router as daily_planner_router
from app.api.routes.assistant import router as assistant_router
from app.api.routes.profile import router as profile_router
from app.api.routes.notifications import router as notifications_router
from app.db.session import Base, engine
# Register model tables before creating the local SQLite development schema.
from app import models


readiness_engine = engine
if engine.dialect.name == "postgresql":
    readiness_engine = create_engine(
        engine.url,
        poolclass=NullPool,
        connect_args={
            "connect_timeout": 2,
            "tcp_user_timeout": 2000,
            "options": "-c statement_timeout=2000",
        },
        hide_parameters=True,
    )


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
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

register_exception_handlers(app)

app.add_middleware(RequestSizeLimit)
register_ingress_guard(app)
register_security_headers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ai_router)
app.include_router(planner_router)
app.include_router(workflows_router)
app.include_router(context_router)
app.include_router(memory_router)
app.include_router(autonomy_router)
app.include_router(external_actions_router)
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


@app.get("/livez", include_in_schema=False)
def liveness():
    return {"status": "live"}


readiness_probe: asyncio.Task[bool] | None = None


def database_ready() -> bool:
    try:
        with readiness_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False


@app.get("/readyz", include_in_schema=False)
async def readiness():
    global readiness_probe
    # Share the in-flight probe if DNS or the database is stalled.
    if readiness_probe is None or readiness_probe.done():
        readiness_probe = asyncio.create_task(asyncio.to_thread(database_ready))
    try:
        ready = await asyncio.wait_for(asyncio.shield(readiness_probe), timeout=3)
    except TimeoutError:
        ready = False
    if not ready:
        raise HTTPException(503, "Database unavailable.")
    return {"status": "ready"}
