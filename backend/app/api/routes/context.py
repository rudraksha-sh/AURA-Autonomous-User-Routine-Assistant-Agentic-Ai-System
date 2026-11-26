from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field, StrictBool
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.agents.context import embeddings, retrieval
from app.agents.context.schemas import SourceReference
from app.models.context import ContextSource
from app.core.rate_limit_dependencies import workflow_limiter
from app.core.security import get_current_user_id
from app.db.session import get_db


def limit_context(user_id: int = Depends(get_current_user_id)) -> None:
    if not workflow_limiter.allow(f"context:{user_id}"):
        raise HTTPException(429, "Too many context requests.", headers={"Retry-After": "60"})


class ContextRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def handle(request: Request):
            try:
                return await handler(request)
            except RequestValidationError:
                # Validation locations can contain keys supplied by the caller.
                raise HTTPException(422, "Invalid context request.") from None

        return handle


router = APIRouter(
    prefix="/api/v1/context", tags=["Context"], dependencies=[Depends(limit_context)], route_class=ContextRoute,
)


class AuthorizedInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    authorized: StrictBool


class LocalSource(AuthorizedInput):
    kind: Literal["goal", "task"]
    local_id: int = Field(gt=0, le=2_147_483_647)


class DocumentSource(AuthorizedInput):
    kind: Literal["document"]
    document_id: UUID
    text: str = Field(min_length=1, max_length=retrieval.MAX_TEXT)


class SearchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=retrieval.MAX_QUERY, pattern=r"\S")
    top_k: int = Field(default=4, ge=1, le=retrieval.MAX_TOP_K)


class IndexStatus(BaseModel):
    source_id: UUID
    kind: Literal["goal", "task", "document"]
    version: UUID
    status: Literal["indexed", "stale"]


class SearchHit(SourceReference):
    score: float
    text: str


class SearchResult(BaseModel):
    hits: list[SearchHit]


def _status(source: ContextSource) -> IndexStatus:
    try:
        current = source.model == embeddings.model_key()
    except embeddings.EmbeddingUnavailable:
        current = False
    return IndexStatus(source_id=source.id, kind=source.kind, version=source.version,
                       status="indexed" if current and not source.stale else "stale")


def _handle(operation, db: Session):
    try:
        return operation()
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from None
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    except embeddings.EmbeddingUnavailable as exc:
        raise HTTPException(503, str(exc)) from None
    except DBAPIError:
        db.rollback()
        raise HTTPException(503, "Context storage is unavailable.") from None


@router.put("/sources", response_model=IndexStatus)
def ingest(body: Annotated[LocalSource | DocumentSource, Field(discriminator="kind")],
           user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    if not body.authorized:
        raise HTTPException(403, "Explicit authorization is required to index context.")

    def operation():
        if isinstance(body, DocumentSource):
            source = retrieval.index(db, user_id, body.kind, str(body.document_id), body.text)
        else:
            source = retrieval.index(db, user_id, body.kind, body.local_id)
        result = _status(source)
        db.commit()
        return result

    return _handle(operation, db)


@router.get("/sources/{source_id}", response_model=IndexStatus)
def indexing_status(source_id: UUID, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    return _handle(lambda: _status(retrieval.owned_source(db, user_id, str(source_id))), db)


@router.delete("/sources/{source_id}", status_code=204)
def revoke(source_id: UUID, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    def operation():
        retrieval.revoke(db, user_id, str(source_id))
        db.commit()

    return _handle(operation, db)


@router.post("/search", response_model=SearchResult)
def search(body: SearchInput, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    return _handle(lambda: {"hits": retrieval.search(db, user_id, body.query, body.top_k)}, db)
