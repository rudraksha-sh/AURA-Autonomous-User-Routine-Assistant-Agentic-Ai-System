from http.client import HTTPConnection
from json import loads
from threading import Event, Thread

from app.agents.execution import worker


def test_worker_polls_once_and_shuts_down_cleanly(monkeypatch, caplog):
    stop = Event()
    sessions = []

    class SessionContext:
        def __enter__(self):
            class Connection:
                def exec_driver_sql(self, _query):
                    return None
            class Session:
                def connection(self):
                    return Connection()
            return Session()

        def __exit__(self, *_):
            stop.set()

    monkeypatch.setattr(worker, "SessionLocal", lambda: SessionContext())
    monkeypatch.setattr(worker, "metrics", lambda _session: {
        "pending_count": 0, "unknown_count": 0, "failed_count": 0,
        "retry_count": 0, "oldest_pending_seconds": 0,
    })
    monkeypatch.setattr(worker, "dispatch_ready", lambda _session, _limit: sessions.append(1) or 2)

    worker.run(stop, poll_seconds=0.1)

    assert sessions == [1]
    assert "worker_started" in caplog.text
    assert "worker_stopped" in caplog.text


def test_worker_poll_crash_marks_not_ready(monkeypatch, caplog):
    stop = Event()

    class SessionContext:
        def __enter__(self):
            raise RuntimeError("database unavailable")

        def __exit__(self, *_):
            return False

    monkeypatch.setattr(worker, "SessionLocal", lambda: SessionContext())
    monkeypatch.setattr(stop, "wait", lambda _seconds: stop.set())
    worker.run(stop, poll_seconds=0.1)

    status = worker.health()
    assert status["live"] is False
    assert status["ready"] is False
    assert status["database_ready"] is False
    assert status["last_error"] == "poll_failed"
    assert "worker_poll_failed" in caplog.text
    assert "database unavailable" not in caplog.text



def test_probes_track_poll_failure_recovery_and_stall(monkeypatch, caplog):
    import logging

    caplog.set_level(logging.INFO, logger=worker.logger.name)
    monkeypatch.setenv("AURA_WORKER_ALERT_UNKNOWN", "1")
    stop = Event()
    now = [10.0]
    monkeypatch.setattr(worker.time, "monotonic", lambda: now[0])
    outcomes = iter([RuntimeError("do not log this"), 2])
    observations = []

    class SessionContext:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def connection(self):
            return self

        def exec_driver_sql(self, _query):
            pass

    def dispatch(*_args):
        outcome = next(outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def after_poll(_delay):
        observations.append(worker.health())
        if len(observations) == 2:
            now[0] += 91
            observations.append(worker.health())
            stop.set()

    monkeypatch.setattr(worker, "SessionLocal", SessionContext)
    monkeypatch.setattr(worker, "dispatch_ready", dispatch)
    monkeypatch.setattr(worker, "metrics", lambda _db: {
        "pending_count": 0, "unknown_count": 1, "failed_count": 0,
        "retry_count": 0, "oldest_pending_seconds": 0,
    })
    monkeypatch.setattr(stop, "wait", after_poll)
    worker.run(stop)
    failed, recovered, stalled = observations
    assert failed["live"] and failed["database_ready"] and not failed["ready"]
    assert recovered["ready"] and recovered["last_success_at"] and recovered["processed"] == 2
    assert not stalled["ready"] and not stalled["live"]
    assert "worker_threshold_exceeded" in caplog.text and "do not log this" not in caplog.text


def test_http_probes_use_status_codes_and_report_only_safe_state(monkeypatch):
    status = {"live": True, "ready": False, "metrics": None}
    monkeypatch.setattr(worker, "health", lambda: status)
    with worker.ProbeServer(("127.0.0.1", 0), worker.ProbeHandler) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            connection = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
            for path, expected in [("/livez", 200), ("/readyz", 503), ("/unknown", 404)]:
                connection.request("GET", path)
                response = connection.getresponse()
                assert response.status == expected
                body = response.read()
                if expected != 404:
                    assert loads(body) == status and response.getheader("Cache-Control") == "no-store"
            connection.close()
        finally:
            server.shutdown()
            thread.join(timeout=3)
