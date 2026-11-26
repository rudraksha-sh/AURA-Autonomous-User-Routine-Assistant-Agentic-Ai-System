import logging
import sys


class AccessQueryRedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Uvicorn access records carry the path and query as their third argument.
        if isinstance(record.args, tuple) and len(record.args) == 5:
            client, method, path, version, status = record.args
            if isinstance(path, str):
                record.args = (client, method, path.partition("?")[0], version, status)
        return True


def configure_logging() -> None:
    """Configure application-wide logging for AURA."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )
    logging.getLogger("uvicorn.access").addFilter(AccessQueryRedactionFilter())
    # HTTPX INFO records include request query strings, including provider page tokens.
    for client in ("httpx", "httpx2"):
        logging.getLogger(client).setLevel(logging.WARNING)
