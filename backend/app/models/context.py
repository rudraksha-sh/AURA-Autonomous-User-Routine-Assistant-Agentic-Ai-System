"""Storage for explicitly authorized, tenant-scoped context."""
from sqlalchemy import DDL, cast, ForeignKey, String, Text, UniqueConstraint, event
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import UserDefinedType

from app.db.session import Base


class Vector384(UserDefinedType):
    cache_ok = True

    def get_col_spec(self, **kwargs):
        return "vector(384)"

    def bind_expression(self, bindvalue):
        return cast(bindvalue, self)


class ContextSource(Base):
    __tablename__ = "context_sources"
    __table_args__ = (UniqueConstraint("user_id", "source_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    goal_id: Mapped[int | None] = mapped_column(ForeignKey("goals.id", ondelete="CASCADE"), index=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(10))
    source_key: Mapped[str] = mapped_column(String(64))
    version: Mapped[str] = mapped_column(String(36))
    digest: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(64))
    stale: Mapped[bool] = mapped_column(default=False)


class ContextChunk(Base):
    __tablename__ = "context_chunks"

    source_id: Mapped[str] = mapped_column(ForeignKey("context_sources.id", ondelete="CASCADE"), primary_key=True)
    ordinal: Mapped[int] = mapped_column(primary_key=True)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[str] = mapped_column(Text().with_variant(Vector384(), "postgresql"))


# Update triggers also catch bulk SQL and changes outside the HTTP API.
INVALIDATION = (
    ("goals", "title, description, user_id",
     "OLD.title IS DISTINCT FROM NEW.title OR OLD.description IS DISTINCT FROM NEW.description "
     "OR OLD.user_id IS DISTINCT FROM NEW.user_id",
     "goal_id = OLD.id AND (kind = 'goal' OR OLD.user_id IS DISTINCT FROM NEW.user_id)"),
    ("tasks", "title, description, goal_id",
     "OLD.title IS DISTINCT FROM NEW.title OR OLD.description IS DISTINCT FROM NEW.description "
     "OR OLD.goal_id IS DISTINCT FROM NEW.goal_id", "task_id = OLD.id"),
)


def create_invalidation_v1(dialect: str):
    for table, columns, changed, sources in INVALIDATION:
        name = f"context_invalidate_{table}"
        body = (
            f"UPDATE context_sources SET stale = true WHERE {sources}; "
            f"DELETE FROM context_chunks WHERE source_id IN (SELECT id FROM context_sources WHERE {sources});"
        )
        if dialect == "postgresql":
            yield f"CREATE FUNCTION {name}() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN {body} RETURN NEW; END; $$"
            yield (f"CREATE TRIGGER {name} AFTER UPDATE OF {columns} ON {table} FOR EACH ROW "
                   f"WHEN ({changed}) EXECUTE FUNCTION {name}()")
        elif dialect == "sqlite":
            yield f"CREATE TRIGGER {name} AFTER UPDATE OF {columns} ON {table} WHEN {changed} BEGIN {body} END"
            # Some isolated SQLite fixtures do not enable foreign-key cascades.
            yield (f"CREATE TRIGGER {name}_delete AFTER DELETE ON {table} BEGIN "
                   f"DELETE FROM context_sources WHERE {table[:-1]}_id = OLD.id; END")
    if dialect == "sqlite":
        yield ("CREATE TRIGGER context_delete_chunks AFTER DELETE ON context_sources BEGIN "
               "DELETE FROM context_chunks WHERE source_id = OLD.id; END")
        yield ("CREATE TRIGGER context_delete_user AFTER DELETE ON users BEGIN "
               "DELETE FROM context_sources WHERE user_id = OLD.id; END")


def drop_invalidation_v1(dialect: str):
    for table, *_ in INVALIDATION:
        name = f"context_invalidate_{table}"
        if dialect == "postgresql":
            yield f"DROP TRIGGER IF EXISTS {name} ON {table}"
            yield f"DROP FUNCTION IF EXISTS {name}()"
        elif dialect == "sqlite":
            yield f"DROP TRIGGER IF EXISTS {name}"
            yield f"DROP TRIGGER IF EXISTS {name}_delete"
    if dialect == "sqlite":
        yield "DROP TRIGGER IF EXISTS context_delete_chunks"
        yield "DROP TRIGGER IF EXISTS context_delete_user"


for backend in ("sqlite", "postgresql"):
    for statement in create_invalidation_v1(backend):
        event.listen(ContextChunk.__table__, "after_create", DDL(statement).execute_if(dialect=backend))
    for statement in drop_invalidation_v1(backend):
        event.listen(ContextChunk.__table__, "before_drop", DDL(statement).execute_if(dialect=backend))
