from fastapi.testclient import TestClient

from tests.conftest import register_and_login_as_admin


def test_analyst_and_intel_routes_require_auth(client: TestClient):
    assert client.get("/v1/analyst/status").status_code == 401
    assert client.post(
        "/v1/analyst/chat",
        json={"messages": [{"role": "user", "content": "hello"}]},
    ).status_code == 401
    assert client.get("/v1/intel/intsum").status_code == 401
    assert client.get("/v1/intel/dossier/123456789").status_code == 401
    assert client.get("/v1/intel/sitrep").status_code == 401


def test_admin_can_access_intel_routes(client: TestClient):
    token = register_and_login_as_admin(client)
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/v1/intel/intsum", headers=headers).status_code == 200
    assert client.get("/v1/intel/dossier/123456789", headers=headers).status_code == 200
    assert client.get("/v1/intel/sitrep", headers=headers).status_code == 200


def test_detailed_health_requires_admin_and_ready_hides_errors(client: TestClient):
    assert client.get("/v1/health/detailed").status_code == 401

    ready = client.get("/v1/health/ready")
    assert ready.status_code in {200, 503}
    payload = ready.json()
    assert "error" not in payload["database"]
    assert "error" not in payload["redis"]

    token = register_and_login_as_admin(client)
    detailed = client.get(
        "/v1/health/detailed",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detailed.status_code == 200
    body = detailed.json()
    assert "error" in body["database"]
    assert "error" in body["redis"]
