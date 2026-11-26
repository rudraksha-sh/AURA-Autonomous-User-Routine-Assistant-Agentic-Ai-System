from functools import lru_cache
from hashlib import sha256
from math import isfinite, sqrt
from pathlib import Path

from app.core.config import settings

DIMENSION = 384


class EmbeddingUnavailable(Exception):
    pass


def model_key() -> str:
    if not settings.context_model_path or not settings.context_model_revision:
        raise EmbeddingUnavailable("Local context embeddings are unavailable.")
    return sha256(f"{settings.context_model_path}\0{settings.context_model_revision}".encode()).hexdigest()


@lru_cache(maxsize=1)
def load_model(path: str, revision: str):
    directory = Path(path)
    if not directory.is_dir():
        raise EmbeddingUnavailable("Local context embeddings are unavailable.")
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(str(directory.resolve()), local_files_only=True, trust_remote_code=False,
                               device="cpu")


def embed(texts: list[str]) -> list[list[float]]:
    try:
        model_key()
        model = load_model(settings.context_model_path, settings.context_model_revision)
        # Query and document inputs share the same offline encoder.
        values = model.encode(texts, convert_to_numpy=True, show_progress_bar=False).tolist()
        if len(values) != len(texts):
            raise ValueError
        normalized = []
        for vector in values:
            norm = sqrt(sum(value * value for value in vector))
            if len(vector) != DIMENSION or not isfinite(norm) or not norm:
                raise ValueError
            normalized.append([value / norm for value in vector])
        return normalized
    except Exception:
        # Provider exceptions can contain model paths or input text.
        raise EmbeddingUnavailable("Local context embeddings are unavailable.") from None
