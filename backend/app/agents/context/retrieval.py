"""Bounded, opt-in corpus for the Context Agent."""
import json
import re
from hashlib import sha256
from uuid import uuid4

from sqlalchemy import cast, delete, func, literal, or_, select
from sqlalchemy.orm import Session

from app.agents.context import embeddings
from app.core.config import settings
from app.models.context import ContextChunk, ContextSource, Vector384
from app.models.goal import Goal
from app.models.task import Task
from app.models.user import User

MAX_TEXT = 16_000
MAX_QUERY = 1000
MAX_SOURCES = 100
MAX_TOP_K = 8
CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
CREDENTIAL = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|\bBearer\s+[\w.~-]+|"
    r"(?<!\w)1//[\w-]+|\beyJ[\w-]+\.eyJ[\w-]+\.[\w-]+|\b(?:gh[pousr]_|sk-|AIza|AKIA|ASIA|ya29\.)[\w-]+|"
    r"\b(?:password|passwd|client[_ -]?secret|(?:access|refresh|oauth)[_ -]?token|api[_ -]?key)"
    r"""\s*["']?\s*[:=]\s*["']?\S+|://[^\s/@:]+:[^\s/@]+@""",
    re.IGNORECASE,
)


def _require_storage(db: Session) -> None:
    dialect = db.get_bind().dialect.name
    if dialect != "postgresql" and not (dialect == "sqlite" and settings.environment == "test"):
        raise embeddings.EmbeddingUnavailable("Context storage is unavailable.")


def _source_query(user_id: int):
    return select(ContextSource).where(ContextSource.user_id == user_id)


def _lock_corpus(db: Session, user_id: int) -> None:
    _require_storage(db)
    db.scalar(select(User.id).where(User.id == user_id).with_for_update(key_share=True))
    if db.get_bind().dialect.name == "postgresql":
        # Serialize per-owner mutations without locking user rows against foreign-key checks.
        db.execute(select(func.pg_advisory_xact_lock(70404, user_id)))


def _local_text(db: Session, user_id: int, kind: str, local_id: int) -> tuple[int, str]:
    if kind == "goal":
        query = select(Goal.id, Goal.title, Goal.description).where(Goal.id == local_id)
    else:
        query = (select(Goal.id, Task.title, Task.description)
                 .join(Task, Task.goal_id == Goal.id).where(Task.id == local_id))
    row = db.execute(query.where(Goal.user_id == user_id).with_for_update(read=True)).one_or_none()
    if row is None:
        raise LookupError("Context source not found.")
    return row.id, "\n".join(value for value in (row.title, row.description) if value)


def _chunks(content: str) -> list[str]:
    pieces = []
    start = 0
    while start < len(content):
        end = min(start + CHUNK_SIZE, len(content))
        if end < len(content):
            boundary = content.rfind(" ", start + CHUNK_SIZE // 2, end)
            if boundary > start:
                end = boundary
        pieces.append(content[start:end].strip())
        if end == len(content):
            break
        start = end - CHUNK_OVERLAP
    return list(dict.fromkeys(piece for piece in pieces if piece))


def index(db: Session, user_id: int, kind: str, key: int | str, content: str = "") -> ContextSource:
    _lock_corpus(db, user_id)
    goal_id = None
    if kind != "document":
        goal_id, content = _local_text(db, user_id, kind, int(key))
    if not content.strip() or len(content) > MAX_TEXT or "\0" in content or CREDENTIAL.search(content):
        raise ValueError("Context must be nonempty, within the size limit, and free of credentials.")
    digest = sha256(content.encode()).hexdigest()
    model = embeddings.model_key()
    source_key = f"{kind}:{key}"
    sources = _source_query(user_id)
    source = db.scalar(sources.where(ContextSource.source_key == source_key))
    if source and not source.stale and source.digest == digest and source.model == model:
        return source
    if source is None and db.scalar(select(func.count()).select_from(sources.subquery())) >= MAX_SOURCES:
        raise ValueError("Context source limit reached.")
    pieces = _chunks(content)
    vectors = embeddings.embed(pieces)
    if source is None:
        source = ContextSource(id=str(uuid4()), user_id=user_id, kind=kind, source_key=source_key,
                               goal_id=goal_id, task_id=int(key) if kind == "task" else None)
        db.add(source)
    else:
        db.execute(delete(ContextChunk).where(ContextChunk.source_id == source.id))
    source.goal_id = goal_id
    source.version, source.digest, source.model, source.stale = str(uuid4()), digest, model, False
    db.flush()
    db.add_all(ContextChunk(source_id=source.id, ordinal=ordinal, content=piece,
                            embedding=json.dumps(vector, separators=(",", ":")))
               for ordinal, (piece, vector) in enumerate(zip(pieces, vectors, strict=True)))
    db.flush()
    return source


def owned_source(db: Session, user_id: int, source_id: str) -> ContextSource:
    _require_storage(db)
    source = db.scalar(_source_query(user_id).where(ContextSource.id == source_id))
    if source is None:
        raise LookupError("Context source not found.")
    return source


def revoke(db: Session, user_id: int, source_id: str) -> None:
    _lock_corpus(db, user_id)
    db.delete(owned_source(db, user_id, source_id))
    db.flush()


def reference(source: ContextSource, ordinal: int) -> dict:
    return {"source_id": source.id, "version": source.version, "kind": source.kind, "chunk": ordinal,
            "local_id": source.task_id if source.kind == "task" else source.goal_id}


def search(
    db: Session, user_id: int, query: str, top_k: int, *,
    goal_id: int | None = None, include_text: bool = True,
) -> list[dict]:
    _require_storage(db)
    model = embeddings.model_key()
    top_k = max(1, min(top_k, MAX_TOP_K))
    if CREDENTIAL.search(query):
        raise ValueError("Search queries must be free of credentials.")
    vector, = embeddings.embed([query[:MAX_QUERY]])
    text_column = ContextChunk.content if include_text else literal(None)
    statement = (
        select(ContextSource, ContextChunk.ordinal, text_column)
        .join(ContextChunk, ContextChunk.source_id == ContextSource.id)
        .where(ContextSource.user_id == user_id, ContextSource.model == model, ContextSource.stale.is_(False))
    )
    if goal_id is not None:
        statement = statement.where(or_(ContextSource.goal_id == goal_id, ContextSource.kind == "document"))
    if db.get_bind().dialect.name == "postgresql":
        distance = ContextChunk.embedding.op("<=>")(cast(literal(json.dumps(vector)), Vector384()))
        rows = db.execute(statement.add_columns(distance.label("distance"))
                          .order_by(distance, ContextSource.id, ContextChunk.ordinal).limit(top_k))
        ranked = [(1 - score, source, ordinal, content) for source, ordinal, content, score in rows]
    else:
        rows = db.execute(statement.add_columns(ContextChunk.embedding))
        ranked = sorted(
            ((sum(a * b for a, b in zip(vector, json.loads(encoded), strict=True)), source, ordinal, content)
             for source, ordinal, content, encoded in rows),
            key=lambda item: (-item[0], item[1].id, item[2]),
        )[:top_k]
    return [{**reference(source, ordinal), "score": round(max(-1, min(1, score)), 6),
             **({"text": content} if include_text else {})}
            for score, source, ordinal, content in ranked if score > 0.2]


def check_versions(db: Session, user_id: int, refs: list[dict]) -> None:
    expected = {item["source_id"]: item["version"] for item in refs}
    if not expected:
        return
    try:
        model = embeddings.model_key()
    except embeddings.EmbeddingUnavailable:
        model = ""
    rows = db.execute(
        select(ContextSource.id, ContextSource.version).where(
            ContextSource.user_id == user_id, ContextSource.id.in_(expected),
            ContextSource.stale.is_(False), ContextSource.model == model,
        ).order_by(ContextSource.id).with_for_update(read=True)
    )
    if dict(rows.tuples().all()) != expected:
        raise ValueError("Context changed after the preview. Start a new workflow.")
