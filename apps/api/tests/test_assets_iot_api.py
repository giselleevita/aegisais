from tests.conftest import register_and_login_as_admin


def test_asset_and_policy_flow(client):
    token = register_and_login_as_admin(client)

    asset_response = client.post(
        "/v1/assets",
        json={
            "asset_type": "cable_segment",
            "name": "Baltic Corridor A",
            "criticality": "critical",
            "geometry_json": {
                "type": "LineString",
                "coordinates": [[20.0, 57.0], [21.0, 57.5]],
            },
            "metadata_json": {"corridor": "A"},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert asset_response.status_code == 200, asset_response.text
    asset = asset_response.json()
    assert asset["asset_type"] == "cable_segment"
    assert asset["criticality"] == "critical"

    policy_response = client.post(
        f"/v1/assets/{asset['id']}/policies",
        json={
            "policy_type": "maintenance_window",
            "name": "Planned maintenance",
            "policy_json": {"suppress_alerts": True},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert policy_response.status_code == 200, policy_response.text
    assert policy_response.json()["policy_type"] == "maintenance_window"

    list_response = client.get(
        "/v1/assets?asset_type=cable_segment",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_response.status_code == 200, list_response.text
    assert len(list_response.json()) == 1


def test_asset_links_require_same_scope(client):
    token = register_and_login_as_admin(client)
    headers = {"Authorization": f"Bearer {token}"}

    landing_station = client.post(
        "/v1/assets",
        json={
            "asset_type": "landing_station",
            "name": "Station North",
            "geometry_json": {"type": "Point", "coordinates": [20.0, 57.0]},
        },
        headers=headers,
    ).json()
    cable_segment = client.post(
        "/v1/assets",
        json={
            "asset_type": "cable_segment",
            "name": "Segment North",
            "geometry_json": {"type": "LineString", "coordinates": [[20.0, 57.0], [20.5, 57.2]]},
        },
        headers=headers,
    ).json()

    link_response = client.post(
        f"/v1/assets/{cable_segment['id']}/links",
        json={"target_asset_id": landing_station["id"], "relation_type": "terminates_at"},
        headers=headers,
    )
    assert link_response.status_code == 200, link_response.text
    assert link_response.json()["relation_type"] == "terminates_at"


def test_device_registration_and_heartbeat_flow(client):
    token = register_and_login_as_admin(client)
    headers = {"Authorization": f"Bearer {token}"}

    asset = client.post(
        "/v1/assets",
        json={
            "asset_type": "sensor_node",
            "name": "Node Alpha",
            "geometry_json": {"type": "Point", "coordinates": [20.1, 57.1]},
        },
        headers=headers,
    ).json()

    device_response = client.post(
        "/v1/iot/devices",
        json={
            "device_type": "gateway",
            "name": "Gateway Alpha",
            "asset_id": asset["id"],
            "connectivity_profile": {"protocol": "mqtt", "qos": 1},
        },
        headers=headers,
    )
    assert device_response.status_code == 200, device_response.text
    device = device_response.json()
    assert device["asset_id"] == asset["id"]
    assert device["device_type"] == "gateway"

    heartbeat_response = client.post(
        f"/v1/iot/devices/{device['id']}/heartbeats",
        json={
            "status": "healthy",
            "battery_level": 91.5,
            "queue_depth": 3,
            "signal_strength": -67.0,
        },
        headers=headers,
    )
    assert heartbeat_response.status_code == 200, heartbeat_response.text
    heartbeat = heartbeat_response.json()
    assert heartbeat["device_id"] == device["id"]
    assert heartbeat["status"] == "healthy"

    list_response = client.get(
        "/v1/iot/devices?status=healthy",
        headers=headers,
    )
    assert list_response.status_code == 200, list_response.text
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["last_seen_at"] is not None

    heartbeat_list = client.get(
        f"/v1/iot/devices/{device['id']}/heartbeats",
        headers=headers,
    )
    assert heartbeat_list.status_code == 200, heartbeat_list.text
    assert len(heartbeat_list.json()) == 1


def test_device_update_can_revoke(client):
    token = register_and_login_as_admin(client)
    headers = {"Authorization": f"Bearer {token}"}

    device = client.post(
        "/v1/iot/devices",
        json={"device_type": "sensor", "name": "Hydrophone 1"},
        headers=headers,
    ).json()

    revoke_response = client.patch(
        f"/v1/iot/devices/{device['id']}",
        json={"status": "revoked", "is_active": False},
        headers=headers,
    )
    assert revoke_response.status_code == 200, revoke_response.text
    body = revoke_response.json()
    assert body["status"] == "revoked"
    assert body["revoked_at"] is not None
    assert body["is_active"] is False
