from fastapi.testclient import TestClient

from semraa_tts.main import app


def test_worker_reports_ready() -> None:
    with TestClient(app) as client:
        assert client.get("/ready").status_code == 200
