from fastapi.testclient import TestClient

from semraa_worker_common import ModelState, create_worker_app


async def _load(state: ModelState) -> None:
    state.loaded = True
    state.model_id = "test-model"


async def _never_loads(state: ModelState) -> None:
    return None


def test_ready_after_model_loads() -> None:
    with TestClient(create_worker_app("test", _load)) as client:
        assert client.get("/health").json()["status"] == "alive"
        ready = client.get("/ready")
        assert ready.status_code == 200
        assert ready.json()["model_id"] == "test-model"


def test_not_ready_until_model_loads() -> None:
    with TestClient(create_worker_app("test", _never_loads)) as client:
        assert client.get("/ready").status_code == 503
