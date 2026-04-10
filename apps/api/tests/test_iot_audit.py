from app.modules.audit.models import AuditLog
from tests.conftest import TestingSessionLocal, register_and_login_as_admin


def test_asset_and_iot_actions_emit_audit_events(client):
    token = register_and_login_as_admin(client)
    headers = {"Authorization": f"Bearer {token}"}

    asset = client.post(
        "/v1/assets",
        json={
            "asset_type": "landing_station",
            "name": "Audit Station",
            "geometry_json": {"type": "Point", "coordinates": [19.5, 56.7]},
        },
        headers=headers,
    ).json()
    device = client.post(
        "/v1/iot/devices",
        json={
            "device_type": "gateway",
            "name": "Audit Gateway",
            "asset_id": asset["id"],
        },
        headers=headers,
    ).json()
    heartbeat = client.post(
        f"/v1/iot/devices/{device['id']}/heartbeats",
        json={"status": "healthy", "queue_depth": 2},
        headers=headers,
    )
    assert heartbeat.status_code == 200, heartbeat.text

    db = TestingSessionLocal()
    try:
        actions = {row.action for row in db.query(AuditLog).all()}
        assert "asset.create" in actions
        assert "iot.device.create" in actions
        assert "iot.device.heartbeat" in actions
    finally:
        db.close()