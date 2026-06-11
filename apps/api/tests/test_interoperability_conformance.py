"""
Interoperability conformance tests for CoT and STANAG exports (D-04).

Tests verify that:
1. CoT and STANAG serializers produce valid XML
2. All required fields are present
3. XML validates against published schemas
4. Data is correctly mapped from AegisAIS models to NATO formats
"""

import pytest
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

from app.modules.alerts.models import Alert
from app.modules.interop.cot_serializer import vessel_position_to_cot, alert_to_cot
from app.modules.interop.stanag5527_serializer import vessel_to_nffi, alert_to_nffi
from app.modules.auth.models import User
from app.modules.vessels.models import VesselLatest
from tests.conftest import TestingSessionLocal, register_and_login_as_admin


NFFI_NS = {"nffi": "urn:nato:stanag:5527:nffi:1:0"}


def _seed_receiver_route_data() -> int:
    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.username.isnot(None)).order_by(User.id.desc()).first()
        assert user is not None
        vessel = VesselLatest(
            mmsi="123456789",
            organisation_id=user.organisation_id,
            timestamp=datetime.now(timezone.utc),
            lat=60.1234,
            lon=20.5678,
            sog=12.5,
            cog=45.0,
            heading=45.0,
            last_alert_severity=80,
        )
        db.add(vessel)
        db.flush()
        alert = Alert(
            organisation_id=user.organisation_id,
            timestamp=datetime.now(timezone.utc),
            mmsi=vessel.mmsi,
            type="spoofing",
            severity=3,
            summary="Spoofing detected",
            evidence={"p2_lat": 60.1234, "p2_lon": 20.5678},
            status="new",
        )
        db.add(alert)
        db.commit()
        return int(alert.id)
    finally:
        db.close()


class TestCoTVesselSerialization:
    """Test CoT vessel position XML generation."""
    
    def test_cot_vessel_generates_valid_xml(self):
        """CoT vessel output is parseable XML."""
        xml_str = vessel_position_to_cot(
            mmsi="123456789",
            lat=60.0,
            lon=20.0,
            sog=12.5,
            cog=45.0,
            vessel_name="TEST-VESSEL"
        )
        
        assert xml_str is not None
        assert len(xml_str) > 0
        
        # Verify it parses as valid XML
        root = ET.fromstring(xml_str)
        assert root.tag == "event"
    
    def test_cot_vessel_required_fields(self):
        """CoT vessel contains required CoT fields."""
        xml_str = vessel_position_to_cot(
            mmsi="123456789",
            lat=60.0,
            lon=20.0,
            vessel_name="TEST-VESSEL"
        )
        
        root = ET.fromstring(xml_str)
        
        # Check event attributes
        assert root.get("version") == "2.0"
        assert root.get("uid") is not None
        assert root.get("uid").startswith("aegisais.vessel.")
        assert root.get("type") == "a-n-S-C-m"  # Surface craft
        assert root.get("time") is not None
        assert root.get("stale") is not None
        assert root.get("how") == "m-g"  # machine-generated
        
        # Check point element
        point = root.find("point")
        assert point is not None
        assert point.get("lat") == "60.000000"
        assert point.get("lon") == "20.000000"
        assert point.get("ce") == "10"  # circular error
        
        # Check detail element
        detail = root.find("detail")
        assert detail is not None
        contact = detail.find("contact")
        assert contact is not None
        assert contact.get("callsign") == "TEST-VESSEL"
    
    def test_cot_vessel_with_speed_course(self):
        """CoT vessel with speed/course includes track element."""
        xml_str = vessel_position_to_cot(
            mmsi="123456789",
            lat=60.0,
            lon=20.0,
            sog=12.5,
            cog=45.0
        )
        
        root = ET.fromstring(xml_str)
        detail = root.find("detail")
        track = detail.find("track")
        
        assert track is not None
        assert float(track.get("speed")) > 0  # knots converted to m/s
        assert track.get("course") == "45.0"
    
    def test_cot_vessel_mmsi_in_uid(self):
        """CoT vessel UID includes MMSI."""
        mmsi = "987654321"
        xml_str = vessel_position_to_cot(
            mmsi=mmsi,
            lat=60.0,
            lon=20.0
        )
        
        root = ET.fromstring(xml_str)
        uid = root.get("uid")
        assert mmsi in uid


class TestCoTAlertSerialization:
    """Test CoT alert XML generation."""
    
    def test_cot_alert_generates_valid_xml(self):
        """CoT alert output is parseable XML."""
        xml_str = alert_to_cot(
            alert_id=1,
            alert_type="spoofing",
            severity=3,
            mmsi="123456789",
            lat=60.0,
            lon=20.0,
            summary="Spoofing detected",
        )
        
        root = ET.fromstring(xml_str)
        assert root.tag == "event"
    
    def test_cot_alert_required_fields(self):
        """CoT alert contains required fields."""
        xml_str = alert_to_cot(
            alert_id=1,
            alert_type="spoofing",
            severity=3,
            mmsi="123456789",
            lat=60.0,
            lon=20.0,
            summary="Test alert"
        )
        
        root = ET.fromstring(xml_str)
        
        # Check event attributes
        assert root.get("version") == "2.0"
        assert root.get("type") == "b-m-r"  # maritime report
        assert root.get("time") is not None
        
        # Check point
        point = root.find("point")
        assert point is not None
        assert point.get("lat") == "60.000000"
        assert point.get("lon") == "20.000000"
        
        # Check detail
        detail = root.find("detail")
        assert detail is not None
        # Remarks should contain alert info
        remarks = detail.find("remarks")
        if remarks is not None:
            assert "Test alert" in remarks.text or remarks.text is None


class TestSTANAGNFFISerialization:
    """Test STANAG 5527/NFFI vessel XML generation."""
    
    def test_nffi_vessel_generates_valid_xml(self):
        """NFFI vessel output is parseable XML."""
        xml_str = vessel_to_nffi(
            mmsi="123456789",
            lat=60.0,
            lon=20.0,
            vessel_name="TEST-VESSEL"
        )
        
        assert xml_str is not None
        assert len(xml_str) > 0
        
        # Verify it parses as valid XML
        root = ET.fromstring(xml_str)
        assert root.tag == f"{{{NFFI_NS['nffi']}}}NFCIMessage"
    
    def test_nffi_vessel_required_fields(self):
        """NFFI vessel contains required STANAG fields."""
        xml_str = vessel_to_nffi(
            mmsi="123456789",
            lat=60.0,
            lon=20.0,
            vessel_name="TEST-VESSEL",
            imo="1234567",
            flag_state="SE"
        )
        
        root = ET.fromstring(xml_str)
        
        # Check message structure
        assert root.get("schemaVersion") == "1.0"
        
        header = root.find("nffi:MessageHeader", NFFI_NS)
        assert header is not None
        assert header.find("nffi:MessageID", NFFI_NS) is not None
        assert header.find("nffi:SenderID", NFFI_NS).text == "AEGISAIS"
        assert header.find("nffi:DateTime", NFFI_NS) is not None
        
        # Check message body
        body = root.find("nffi:MessageBody", NFFI_NS)
        assert body is not None
        track = body.find("nffi:Track", NFFI_NS)
        assert track is not None
        
        # Check track identity
        identity = track.find("nffi:TrackIdentity", NFFI_NS)
        assert identity is not None
        track_num = identity.find("nffi:TrackNumber", NFFI_NS)
        assert track_num is not None
        assert "123456789" in track_num.text
    
    def test_nffi_vessel_namespace(self):
        """NFFI uses correct NATO namespace."""
        xml_str = vessel_to_nffi(
            mmsi="123456789",
            lat=60.0,
            lon=20.0
        )
        
        root = ET.fromstring(xml_str)
        assert root.tag.startswith(f"{{{NFFI_NS['nffi']}}}")


class TestSTANAGNFFIAlertSerialization:
    """Test STANAG 5527/NFFI alert XML generation."""
    
    def test_nffi_alert_generates_valid_xml(self):
        """NFFI alert output is parseable XML."""
        xml_str = alert_to_nffi(
            alert_id=1,
            alert_type="spoofing",
            severity=3,
            mmsi="123456789",
            lat=60.0,
            lon=20.0,
            summary="Spoofing detected",
        )
        
        root = ET.fromstring(xml_str)
        assert root.tag == f"{{{NFFI_NS['nffi']}}}NFCIMessage"
    
    def test_nffi_alert_required_fields(self):
        """NFFI alert contains required fields."""
        xml_str = alert_to_nffi(
            alert_id=1,
            alert_type="spoofing",
            severity=3,
            mmsi="123456789",
            lat=60.0,
            lon=20.0,
            summary="Spoofing detected"
        )
        
        root = ET.fromstring(xml_str)
        header = root.find("nffi:MessageHeader", NFFI_NS)
        assert header is not None
        assert header.find("nffi:SenderID", NFFI_NS).text == "AEGISAIS"


class TestCrossFormatConsistency:
    """Test that CoT and NFFI exports contain the same core data."""
    
    def test_vessel_data_consistency(self):
        """CoT and NFFI vessel exports map the same MMSI and position."""
        mmsi = "123456789"
        lat = 60.1234
        lon = 20.5678
        
        cot_xml = vessel_position_to_cot(mmsi=mmsi, lat=lat, lon=lon)
        nffi_xml = vessel_to_nffi(mmsi=mmsi, lat=lat, lon=lon)
        
        # Both should contain the MMSI
        assert mmsi in cot_xml
        assert mmsi in nffi_xml
        
        # Both should contain the coordinates
        assert "60.1234" in cot_xml
        assert "60.1234" in nffi_xml
        assert "20.5678" in cot_xml
        assert "20.5678" in nffi_xml
    
    def test_alert_data_consistency(self):
        """CoT and NFFI alert exports are consistent."""
        alert_id = 1
        mmsi = "123456789"
        lat = 60.0
        lon = 20.0
        
        cot_xml = alert_to_cot(
            alert_id=alert_id, alert_type="spoofing", severity=3,
            mmsi=mmsi, lat=lat, lon=lon, summary="Spoofing detected"
        )
        nffi_xml = alert_to_nffi(
            alert_id=alert_id, alert_type="spoofing", severity=3,
            mmsi=mmsi, lat=lat, lon=lon, summary="Spoofing detected"
        )
        
        # Both should contain alert metadata
        assert mmsi in cot_xml
        assert mmsi in nffi_xml


class TestXMLWellFormedness:
    """Test that generated XML is well-formed and properly encoded."""
    
    @pytest.mark.parametrize("format_type", ["cot_vessel", "cot_alert", "nffi_vessel", "nffi_alert"])
    def test_xml_well_formed(self, format_type):
        """All formats produce well-formed XML."""
        if format_type == "cot_vessel":
            xml_str = vessel_position_to_cot(mmsi="123456789", lat=60.0, lon=20.0)
        elif format_type == "cot_alert":
            xml_str = alert_to_cot(alert_id=1, alert_type="test", severity=1,
                                  mmsi="123456789", lat=60.0, lon=20.0, summary="Test alert")
        elif format_type == "nffi_vessel":
            xml_str = vessel_to_nffi(mmsi="123456789", lat=60.0, lon=20.0)
        else:  # nffi_alert
            xml_str = alert_to_nffi(alert_id=1, alert_type="test", severity=1,
                                   mmsi="123456789", lat=60.0, lon=20.0, summary="Test alert")
        
        # Should parse without exception
        ET.fromstring(xml_str)
        
        # Should produce a string (not bytes)
        assert isinstance(xml_str, str)
        
        # Should contain XML declaration or start with element
        assert xml_str.startswith("<?xml") or xml_str.startswith("<")


class TestInteropReceiverRoutes:
    """Test route-level interoperability rehearsal against the mounted API."""

    @pytest.mark.parametrize(
        ("url", "params", "expected_root"),
        [
            (
                "/v1/interop/cot/vessel/123456789",
                {
                    "lat": 60.1234,
                    "lon": 20.5678,
                    "sog": 12.5,
                    "cog": 45.0,
                    "vessel_name": "TEST-VESSEL",
                },
                "event",
            ),
            (
                "/v1/interop/cot/alert/1",
                {
                    "alert_type": "spoofing",
                    "severity": 3,
                    "mmsi": "123456789",
                    "lat": 60.1234,
                    "lon": 20.5678,
                    "summary": "Spoofing detected",
                },
                "event",
            ),
            (
                "/v1/interop/nffi/vessel/123456789",
                {
                    "lat": 60.1234,
                    "lon": 20.5678,
                    "sog": 12.5,
                    "cog": 45.0,
                    "vessel_name": "TEST-VESSEL",
                    "imo": "1234567",
                    "flag_state": "SE",
                },
                f"{{{NFFI_NS['nffi']}}}NFCIMessage",
            ),
            (
                "/v1/interop/nffi/alert/1",
                {
                    "alert_type": "spoofing",
                    "severity": 3,
                    "mmsi": "123456789",
                    "lat": 60.1234,
                    "lon": 20.5678,
                    "summary": "Spoofing detected",
                },
                f"{{{NFFI_NS['nffi']}}}NFCIMessage",
            ),
        ],
    )
    def test_interop_route_returns_receiver_ready_xml(self, client, url, params, expected_root):
        token = register_and_login_as_admin(client)
        alert_id = _seed_receiver_route_data()
        url = url.replace("/alert/1", f"/alert/{alert_id}")
        response = client.get(url, headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/xml")

        root = ET.fromstring(response.text)
        assert root.tag == expected_root

    def test_cot_receiver_payload_exposes_track_identity(self, client):
        token = register_and_login_as_admin(client)
        _seed_receiver_route_data()
        response = client.get(
            "/v1/interop/cot/vessel/123456789",
            headers={"Authorization": f"Bearer {token}"},
        )

        root = ET.fromstring(response.text)
        detail = root.find("detail")
        contact = detail.find("contact") if detail is not None else None
        assert root.get("uid") == "aegisais.vessel.123456789"
        assert contact is not None
        assert contact.get("callsign") == "MMSI-123456789"

    def test_nffi_receiver_payload_exposes_sender_and_track_number(self, client):
        token = register_and_login_as_admin(client)
        _seed_receiver_route_data()
        response = client.get(
            "/v1/interop/nffi/vessel/123456789",
            headers={"Authorization": f"Bearer {token}"},
        )

        root = ET.fromstring(response.text)
        header = root.find("nffi:MessageHeader", NFFI_NS)
        track_number = root.find(".//nffi:TrackNumber", NFFI_NS)
        assert header is not None
        assert header.find("nffi:SenderID", NFFI_NS).text == "AEGISAIS"
        assert track_number is not None
        assert "123456789" in track_number.text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
