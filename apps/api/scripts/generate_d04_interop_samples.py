#!/usr/bin/env python3
"""
Generate sample CoT and STANAG XML payloads for D-04 receiver validation testing.

Usage:
  python scripts/generate_d04_interop_samples.py
  
Output:
  docs/evidence/d04_sample_*.xml files
"""

import sys
import json
from datetime import datetime, timezone
from pathlib import Path

# Add app to path
script_dir = Path(__file__).parent
app_dir = script_dir.parent
sys.path.insert(0, str(app_dir))

from app.modules.interop.cot_serializer import vessel_position_to_cot, alert_to_cot
from app.modules.interop.stanag5527_serializer import vessel_to_nffi, alert_to_nffi


def write_sample_xml(name: str, xml_str: str) -> None:
    """Write sample XML to evidence directory."""
    evidence_dir = Path(__file__).parent.parent / "docs" / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = evidence_dir / f"d04_sample_{name}.xml"
    output_file.write_text(xml_str)
    print(f"✅ Generated: {output_file}")


def main():
    print("Generating D-04 CoT and STANAG sample payloads...\n")
    
    # Sample vessel data (Baltic Sea region)
    vessel_mmsi = "123456789"
    vessel_name = "TEST-VESSEL-AEGIS"
    vessel_lat = 60.1234
    vessel_lon = 20.5678
    vessel_sog = 12.5  # knots
    vessel_cog = 45.0  # degrees
    
    # Sample alert data
    alert_id = 1
    alert_type = "identity_spoofing"
    alert_severity = 3  # 1=low, 5=critical
    alert_mmsi = vessel_mmsi
    alert_lat = vessel_lat
    alert_lon = vessel_lon
    alert_summary = "AIS identity inconsistency detected"
    
    now = datetime.now(timezone.utc)
    
    # 1. CoT Vessel Position
    print("1. Generating CoT vessel position...")
    cot_vessel = vessel_position_to_cot(
        mmsi=vessel_mmsi,
        lat=vessel_lat,
        lon=vessel_lon,
        sog=vessel_sog,
        cog=vessel_cog,
        vessel_name=vessel_name,
        timestamp=now
    )
    write_sample_xml("cot_vessel", cot_vessel)
    
    # 2. CoT Alert
    print("2. Generating CoT alert...")
    cot_alert = alert_to_cot(
        alert_id=alert_id,
        alert_type=alert_type,
        severity=alert_severity,
        mmsi=alert_mmsi,
        lat=alert_lat,
        lon=alert_lon,
        summary=alert_summary,
        timestamp=now
    )
    write_sample_xml("cot_alert", cot_alert)
    
    # 3. STANAG NFFI Vessel
    print("3. Generating STANAG NFFI vessel...")
    nffi_vessel = vessel_to_nffi(
        mmsi=vessel_mmsi,
        lat=vessel_lat,
        lon=vessel_lon,
        sog=vessel_sog,
        cog=vessel_cog,
        vessel_name=vessel_name,
        imo="1234567",
        flag_state="SE",
        vessel_type="Cargo",
        timestamp=now
    )
    write_sample_xml("nffi_vessel", nffi_vessel)
    
    # 4. STANAG NFFI Alert
    print("4. Generating STANAG NFFI alert...")
    nffi_alert = alert_to_nffi(
        alert_id=alert_id,
        alert_type=alert_type,
        severity=alert_severity,
        mmsi=alert_mmsi,
        lat=alert_lat,
        lon=alert_lon,
        summary=alert_summary,
        timestamp=now
    )
    write_sample_xml("nffi_alert", nffi_alert)
    
    # 5. Create metadata file
    print("5. Generating sample metadata...")
    metadata = {
        "generated_at": now.isoformat(),
        "samples": {
            "cot_vessel": {
                "mmsi": vessel_mmsi,
                "name": vessel_name,
                "lat": vessel_lat,
                "lon": vessel_lon,
                "sog_knots": vessel_sog,
                "cog_degrees": vessel_cog,
                "format": "CoT 2.0 (MIL-STD-6040)",
                "purpose": "Vessel position export test"
            },
            "cot_alert": {
                "alert_id": alert_id,
                "type": alert_type,
                "severity": alert_severity,
                "mmsi": alert_mmsi,
                "summary": alert_summary,
                "format": "CoT 2.0 (MIL-STD-6040)",
                "purpose": "Alert export test"
            },
            "nffi_vessel": {
                "mmsi": vessel_mmsi,
                "name": vessel_name,
                "lat": vessel_lat,
                "lon": vessel_lon,
                "sog_knots": vessel_sog,
                "cog_degrees": vessel_cog,
                "flag_state": "SE",
                "format": "STANAG 5527 / NFFI 1.0",
                "purpose": "Vessel position export test"
            },
            "nffi_alert": {
                "alert_id": alert_id,
                "type": alert_type,
                "severity": alert_severity,
                "mmsi": alert_mmsi,
                "summary": alert_summary,
                "format": "STANAG 5527 / NFFI 1.0",
                "purpose": "Alert export test"
            }
        },
        "notes": "These samples are for D-04 receiver conformance validation. Real production data should be exported from live alerts via API endpoints."
    }
    
    evidence_dir = Path(__file__).parent.parent / "docs" / "evidence"
    metadata_file = evidence_dir / "d04_sample_metadata.json"
    metadata_file.write_text(json.dumps(metadata, indent=2))
    print(f"✅ Generated: {metadata_file}")
    
    print("\n✅ All D-04 samples generated successfully!")
    print(f"\nNext steps:\n")
    print(f"1. Validate XML schemas:")
    print(f"   xmllint --schema infra/schemas/cot-2.0.xsd docs/evidence/d04_sample_cot_*.xml")
    print(f"   xmllint --schema infra/schemas/stanag5527-nffi-1.0.xsd docs/evidence/d04_sample_nffi_*.xml")
    print(f"\n2. Test endpoints (when stack is running):")
    print(f"   curl -k https://localhost:443/v1/interop/cot/vessel/123456789?lat=60.1234&lon=20.5678&sog=12.5&vessel_name='TEST'")
    print(f"   curl -k https://localhost:443/v1/interop/nffi/vessel/123456789?lat=60.1234&lon=20.5678")
    print(f"\n3. Run conformance tests:")
    print(f"   pytest tests/test_interoperability_conformance.py -v")


if __name__ == "__main__":
    main()
