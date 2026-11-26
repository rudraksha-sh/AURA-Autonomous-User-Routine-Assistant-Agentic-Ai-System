"""Supervised polling loop for explicitly confirmed outbox actions."""
import json
import logging
import os
import signal
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from math import isfinite

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.agents.execution import adapters, outbox
from app.db.session import SessionLocal
from app.models.external_action import ExternalAction

logger = logging.getLogger("aura.outbox.worker")
_initial_stats = {
    "alive": False, "database_ready": False, "last_poll_at": None,
    "last_success_at": None, "polls": 0, "processed": 0, "last_error": None,
    "metrics": None, "_last_tick": None, "_stale_seconds": 90,
}
_stats = dict(_initial_stats)
_stats_lock = threading.Lock()


def health():
    with _stats_lock:
        result = dict(_stats)
    tick = result.pop("_last_tick")
    stale_seconds = result.pop("_stale_seconds")
    fresh = tick is not None and time.monotonic() - tick < stale_seconds
    result["live"] = result["alive"] and fresh
    result["ready"] = result["live"] and result["database_ready"] and result["last_error"] is None
    return result


def metrics(db: Session):
    pending = ExternalAction.state.in_(("queued", "dispatching"))
    def count(condition):
        return func.count(case((condition, 1)))

    pending_count, unknown, failed, retries, oldest = db.execute(select(
        count(pending), count(ExternalAction.state == "unknown"),
        count(ExternalAction.state == "failed"),
        func.coalesce(func.sum(case((ExternalAction.attempts > 1, ExternalAction.attempts - 1), else_=0)), 0),
        # The first audit event is the immutable, UTC preview timestamp.
        func.min(case((pending, ExternalAction.audit[0]["at"].as_string()))),
    ).select_from(ExternalAction)).one()
    oldest = datetime.fromisoformat(oldest) if oldest else None
    return {
        "pending_count": pending_count, "unknown_count": unknown, "failed_count": failed,
        "retry_count": retries,
        "oldest_pending_seconds": max(0, int((outbox.now() - oldest).total_seconds())) if oldest else 0,
    }


def _thresholds():
    return {
        metric: max(0, int(os.getenv(name, default)))
        for metric, name, default in (
            ("pending_count", "AURA_WORKER_ALERT_PENDING", "100"),
            ("unknown_count", "AURA_WORKER_ALERT_UNKNOWN", "1"),
            ("failed_count", "AURA_WORKER_ALERT_FAILED", "1"),
            ("oldest_pending_seconds", "AURA_WORKER_ALERT_OLDEST_SECONDS", "300"),
        )
    }


class ProbeHandler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        probe = {"/livez": "live", "/readyz": "ready"}.get(self.path)
        if not probe:
            self.send_error(404)
            return
        status = health()
        body = json.dumps(status).encode()
        self.send_response(200 if status[probe] else 503)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class ProbeServer(HTTPServer):
    def get_request(self):
        request, address = super().get_request()
        request.settimeout(2)
        return request, address


def dispatch_ready(db: Session, limit: int = 10, *, max_seconds: float = 10) -> int:
    deadline = time.monotonic() + max(0.1, min(max_seconds, 30))
    outbox.recover_stale_leases(db)
    if adapters.get_adapter(adapters.PROVIDER, adapters.OPERATION) is None:
        return 0
    current = outbox.now()
    ready = db.execute(select(ExternalAction.user_id, ExternalAction.id, ExternalAction.revision).where(
        ExternalAction.provider == adapters.PROVIDER, ExternalAction.operation == adapters.OPERATION,
        ExternalAction.state == "queued", ExternalAction.consent == "active",
        ExternalAction.due_at <= current, ExternalAction.expires_at > current,
    ).order_by(ExternalAction.due_at, ExternalAction.id).limit(max(1, min(limit, 20)))).all()
    db.rollback()  # Start a fresh transaction for each compare-and-swap claim.
    processed = 0
    for user_id, action_id, revision in ready:
        if time.monotonic() >= deadline:
            break
        try:
            outbox.dispatch(db, outbox.owned(db, user_id, action_id), revision, retire_invalid=True)
            processed += 1
        except (LookupError, PermissionError, ValueError):
            db.rollback()
    return processed


def run(stop_event: threading.Event, *, poll_seconds: float = 2.0, batch_size: int = 10,
        stale_seconds: float = 90.0):
    if not isfinite(poll_seconds) or not isfinite(stale_seconds):
        raise ValueError("Worker timing values must be finite.")
    poll_seconds = max(0.1, min(float(poll_seconds), 60.0))
    stale_seconds = max(poll_seconds + 1, min(stale_seconds, 3600))
    batch_size = max(1, min(int(batch_size), 20))
    thresholds = _thresholds()
    with _stats_lock:
        _stats.update(_initial_stats, alive=True, _last_tick=time.monotonic(), _stale_seconds=stale_seconds)
    logger.info(json.dumps({"event": "worker_started", "poll_seconds": poll_seconds, "batch_size": batch_size}))
    try:
        while not stop_event.is_set():
            database_ready = False
            processed = 0
            try:
                with SessionLocal() as session:
                    session.connection().exec_driver_sql("SELECT 1")
                    database_ready = True
                    processed = dispatch_ready(session, batch_size)
                    observed = metrics(session)
                timestamp = outbox.now().isoformat()
                with _stats_lock:
                    _stats.update(last_success_at=timestamp, metrics=observed)
                exceeded = [key for key, threshold in thresholds.items() if threshold and observed[key] >= threshold]
                logger.log(logging.WARNING if exceeded else logging.INFO, json.dumps({
                    "event": "worker_threshold_exceeded" if exceeded else "worker_metrics",
                    "thresholds_exceeded": exceeded, "last_success_at": timestamp, **observed,
                }))
                error = None
            except Exception as exc:
                # Database and provider exceptions can embed tenant data.
                error = "poll_failed"
                logger.error(json.dumps({"event": "worker_poll_failed", "error_type": type(exc).__name__,
                                         "database_probe_succeeded": database_ready}))
            with _stats_lock:
                _stats.update(database_ready=database_ready, last_error=error,
                              last_poll_at=outbox.now().isoformat(), _last_tick=time.monotonic(),
                              polls=_stats["polls"] + 1, processed=_stats["processed"] + processed)
            stop_event.wait(poll_seconds)
    finally:
        with _stats_lock:
            _stats["alive"] = False
        logger.info(json.dumps({"event": "worker_stopped"}))


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    stop_event = threading.Event()
    poll_seconds = float(os.getenv("AURA_WORKER_POLL_SECONDS", "2"))
    batch_size = int(os.getenv("AURA_WORKER_BATCH_SIZE", "10"))
    stale_seconds = float(os.getenv("AURA_WORKER_STALE_SECONDS", "90"))
    port = int(os.getenv("AURA_WORKER_HEALTH_PORT", "0"))

    def request_shutdown(_signum, _frame):
        stop_event.set()

    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(signal.SIGTERM, request_shutdown)
    server = ProbeServer(("127.0.0.1", port), ProbeHandler) if port else None
    if server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
    try:
        run(stop_event, poll_seconds=poll_seconds, batch_size=batch_size, stale_seconds=stale_seconds)
    finally:
        if server:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    main()
