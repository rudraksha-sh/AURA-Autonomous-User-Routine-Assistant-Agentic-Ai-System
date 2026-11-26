from sqlalchemy.exc import OperationalError

from app import main


def test_private_api_health_endpoints(client, monkeypatch):
    assert client.get("/livez").json() == {"status": "live"}
    assert client.get("/readyz").json() == {"status": "ready"}

    def unavailable():
        raise OperationalError("probe", None, RuntimeError("synthetic database detail"))

    monkeypatch.setattr(main.readiness_engine, "connect", unavailable)
    failure = client.get("/readyz")
    assert failure.status_code == 503
    assert failure.json()["message"] == "Database unavailable."
    assert client.get("/livez").status_code == 200
