#!/usr/bin/env python3
"""
Generate demo AIS data files that showcase all detection rules.

This script creates sample AIS data with various anomalies that will trigger
all detection rules in the AegisAIS system.
"""
import csv
import sys
from pathlib import Path
from datetime import datetime, timedelta
import random

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def generate_teleport_alert(base_time: datetime, mmsi: str) -> list[dict]:
    """Generate data that triggers TELEPORT alert (Tier 1)."""
    points = []
    # Point 1: New York
    points.append({
        'mmsi': mmsi,
        'timestamp': base_time.isoformat(),
        'lat': 40.7128,
        'lon': -74.0060,
        'sog': 12.5,
        'cog': 45.0,
        'heading': 45.0,
    })
    
    # Point 2: 60 seconds later, 200km away (implied speed ~200 kn - triggers alert)
    next_time = base_time + timedelta(seconds=60)
    points.append({
        'mmsi': mmsi,
        'timestamp': next_time.isoformat(),
        'lat': 41.5,  # ~111 km north
        'lon': -72.5,  # ~111 km east (total ~157 km)
        'sog': 12.5,
        'cog': 45.0,
        'heading': 45.0,
    })
    
    return points

def generate_teleport_t2_alert(base_time: datetime, mmsi: str) -> list[dict]:
    """Generate data that triggers TELEPORT_T2 alert (Tier 2 - suspicious)."""
    points = []
    # Point 1
    points.append({
        'mmsi': mmsi,
        'timestamp': base_time.isoformat(),
        'lat': 40.7128,
        'lon': -74.0060,
        'sog': 8.0,
        'cog': 90.0,
        'heading': 90.0,
    })
    
    # Point 2: 300 seconds later, moderate speed violation (Tier 2)
    next_time = base_time + timedelta(seconds=300)
    points.append({
        'mmsi': mmsi,
        'timestamp': next_time.isoformat(),
        'lat': 40.8,  # ~10 km north
        'lon': -73.5,  # ~40 km east (total ~41 km, ~50 kn implied)
        'sog': 8.0,
        'cog': 90.0,
        'heading': 90.0,
    })
    
    return points

def generate_turn_rate_alert(base_time: datetime, mmsi: str) -> list[dict]:
    """Generate data that triggers TURN_RATE alert (Tier 1)."""
    points = []
    # Point 1: High speed, heading 0°
    points.append({
        'mmsi': mmsi,
        'timestamp': base_time.isoformat(),
        'lat': 40.7128,
        'lon': -74.0060,
        'sog': 25.0,  # High speed
        'cog': 0.0,
        'heading': 0.0,
    })
    
    # Point 2: 10 seconds later, heading changed 60° (6°/s - triggers alert)
    next_time = base_time + timedelta(seconds=10)
    points.append({
        'mmsi': mmsi,
        'timestamp': next_time.isoformat(),
        'lat': 40.7150,  # Small movement north
        'lon': -74.0060,
        'sog': 25.0,
        'cog': 60.0,
        'heading': 60.0,  # 60° change in 10s = 6°/s
    })
    
    return points

def generate_turn_rate_t2_alert(base_time: datetime, mmsi: str) -> list[dict]:
    """Generate data that triggers TURN_RATE_T2 alert (Tier 2 - suspicious)."""
    points = []
    # Point 1: Moderate speed
    points.append({
        'mmsi': mmsi,
        'timestamp': base_time.isoformat(),
        'lat': 40.7128,
        'lon': -74.0060,
        'sog': 15.0,
        'cog': 0.0,
        'heading': 0.0,
    })
    
    # Point 2: Moderate turn rate (Tier 2 threshold)
    next_time = base_time + timedelta(seconds=20)
    points.append({
        'mmsi': mmsi,
        'timestamp': next_time.isoformat(),
        'lat': 40.7140,
        'lon': -74.0060,
        'sog': 15.0,
        'cog': 30.0,
        'heading': 30.0,  # 30° in 20s = 1.5°/s (Tier 2)
    })
    
    return points

def generate_position_invalid_alert(base_time: datetime, mmsi: str) -> list[dict]:
    """Generate data that triggers POSITION_INVALID alert."""
    points = []
    # Point 1: Valid position
    points.append({
        'mmsi': mmsi,
        'timestamp': base_time.isoformat(),
        'lat': 40.7128,
        'lon': -74.0060,
        'sog': 10.0,
        'cog': 0.0,
        'heading': 0.0,
    })
    
    # Point 2: Invalid position (lat > 90)
    next_time = base_time + timedelta(seconds=30)
    points.append({
        'mmsi': mmsi,
        'timestamp': next_time.isoformat(),
        'lat': 95.0,  # Invalid latitude
        'lon': -74.0060,
        'sog': 10.0,
        'cog': 0.0,
        'heading': 0.0,
    })
    
    return points

def generate_acceleration_alert(base_time: datetime, mmsi: str) -> list[dict]:
    """Generate data that triggers ACCELERATION alert."""
    points = []
    # Point 1: Low speed
    points.append({
        'mmsi': mmsi,
        'timestamp': base_time.isoformat(),
        'lat': 40.7128,
        'lon': -74.0060,
        'sog': 5.0,  # 5 knots
        'cog': 0.0,
        'heading': 0.0,
    })
    
    # Point 2: 10 seconds later, huge speed increase
    next_time = base_time + timedelta(seconds=10)
    points.append({
        'mmsi': mmsi,
        'timestamp': next_time.isoformat(),
        'lat': 40.7130,  # Small movement
        'lon': -74.0060,
        'sog': 50.0,  # 50 knots (impossible acceleration)
        'cog': 0.0,
        'heading': 0.0,
    })
    
    return points

def generate_heading_cog_consistency_alert(base_time: datetime, mmsi: str) -> list[dict]:
    """Generate data that triggers HEADING_COG_CONSISTENCY alert."""
    points = []
    # Point 1: High speed, heading and COG aligned
    points.append({
        'mmsi': mmsi,
        'timestamp': base_time.isoformat(),
        'lat': 40.7128,
        'lon': -74.0060,
        'sog': 20.0,
        'cog': 0.0,
        'heading': 0.0,
    })
    
    # Point 2: Heading and COG wildly different at high speed
    next_time = base_time + timedelta(seconds=10)
    points.append({
        'mmsi': mmsi,
        'timestamp': next_time.isoformat(),
        'lat': 40.7140,  # Moving north
        'lon': -74.0060,
        'sog': 20.0,
        'cog': 0.0,  # Course over ground: north
        'heading': 180.0,  # Heading: south (180° difference!)
    })
    
    return points

def generate_normal_track(base_time: datetime, mmsi: str, num_points: int = 10) -> list[dict]:
    """Generate normal vessel track (no alerts)."""
    points = []
    lat = 40.7128
    lon = -74.0060
    heading = 0.0
    speed = 12.0
    
    for i in range(num_points):
        points.append({
            'mmsi': mmsi,
            'timestamp': (base_time + timedelta(seconds=i * 30)).isoformat(),
            'lat': lat,
            'lon': lon,
            'sog': speed,
            'cog': heading,
            'heading': heading,
        })
        # Move north slowly
        lat += 0.001
        lon += 0.0005
    
    return points

def generate_comprehensive_demo() -> list[dict]:
    """Generate comprehensive demo data with all alert types."""
    all_points = []
    base_time = datetime(2025, 1, 27, 12, 0, 0)
    
    # Normal track (no alerts)
    all_points.extend(generate_normal_track(base_time, "100000001", 5))
    base_time += timedelta(minutes=5)
    
    # TELEPORT (Tier 1)
    all_points.extend(generate_teleport_alert(base_time, "200000001"))
    base_time += timedelta(minutes=2)
    
    # TELEPORT_T2 (Tier 2)
    all_points.extend(generate_teleport_t2_alert(base_time, "200000002"))
    base_time += timedelta(minutes=2)
    
    # TURN_RATE (Tier 1)
    all_points.extend(generate_turn_rate_alert(base_time, "300000001"))
    base_time += timedelta(minutes=2)
    
    # TURN_RATE_T2 (Tier 2)
    all_points.extend(generate_turn_rate_t2_alert(base_time, "300000002"))
    base_time += timedelta(minutes=2)
    
    # POSITION_INVALID
    all_points.extend(generate_position_invalid_alert(base_time, "400000001"))
    base_time += timedelta(minutes=2)
    
    # ACCELERATION
    all_points.extend(generate_acceleration_alert(base_time, "500000001"))
    base_time += timedelta(minutes=2)
    
    # HEADING_COG_CONSISTENCY
    all_points.extend(generate_heading_cog_consistency_alert(base_time, "600000001"))
    
    return all_points

def write_csv(filename: Path, points: list[dict]):
    """Write points to CSV file."""
    if not points:
        return
    
    fieldnames = ['mmsi', 'timestamp', 'lat', 'lon', 'sog', 'cog', 'heading']
    
    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(points)
    
    print(f"✓ Generated {filename} with {len(points)} points")

def main():
    """Generate demo data files."""
    # Create data/raw directory if it doesn't exist
    data_dir = Path(__file__).parent.parent.parent / "data" / "raw"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    print("Generating demo AIS data files...")
    print("=" * 60)
    
    # Comprehensive demo file (all alert types)
    comprehensive_points = generate_comprehensive_demo()
    write_csv(data_dir / "demo_comprehensive.csv", comprehensive_points)
    
    # Individual alert type files
    base_time = datetime(2025, 1, 27, 12, 0, 0)
    
    write_csv(
        data_dir / "demo_teleport_t1.csv",
        generate_teleport_alert(base_time, "200000001")
    )
    
    write_csv(
        data_dir / "demo_teleport_t2.csv",
        generate_teleport_t2_alert(base_time + timedelta(minutes=1), "200000002")
    )
    
    write_csv(
        data_dir / "demo_turn_rate_t1.csv",
        generate_turn_rate_alert(base_time + timedelta(minutes=2), "300000001")
    )
    
    write_csv(
        data_dir / "demo_turn_rate_t2.csv",
        generate_turn_rate_t2_alert(base_time + timedelta(minutes=3), "300000002")
    )
    
    write_csv(
        data_dir / "demo_position_invalid.csv",
        generate_position_invalid_alert(base_time + timedelta(minutes=4), "400000001")
    )
    
    write_csv(
        data_dir / "demo_acceleration.csv",
        generate_acceleration_alert(base_time + timedelta(minutes=5), "500000001")
    )
    
    write_csv(
        data_dir / "demo_heading_cog.csv",
        generate_heading_cog_consistency_alert(base_time + timedelta(minutes=6), "600000001")
    )
    
    # Normal track (no alerts)
    write_csv(
        data_dir / "demo_normal.csv",
        generate_normal_track(base_time + timedelta(minutes=7), "100000001", 20)
    )
    
    print("=" * 60)
    print("✓ Demo files generated successfully!")
    print(f"\nFiles created in: {data_dir}")
    print("\nFiles:")
    print("  - demo_comprehensive.csv    (All alert types)")
    print("  - demo_teleport_t1.csv     (TELEPORT Tier 1)")
    print("  - demo_teleport_t2.csv     (TELEPORT Tier 2)")
    print("  - demo_turn_rate_t1.csv    (TURN_RATE Tier 1)")
    print("  - demo_turn_rate_t2.csv    (TURN_RATE Tier 2)")
    print("  - demo_position_invalid.csv (POSITION_INVALID)")
    print("  - demo_acceleration.csv     (ACCELERATION)")
    print("  - demo_heading_cog.csv     (HEADING_COG_CONSISTENCY)")
    print("  - demo_normal.csv          (Normal track, no alerts)")

if __name__ == "__main__":
    main()
