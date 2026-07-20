#!/usr/bin/env python3
"""Generate the deterministic synthetic trajectory baseline dataset."""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path


VESSEL_CLASSES = ("cargo", "tanker", "ferry", "research")


def _point(timestamp: datetime, lat: float, lon: float, sog: float, cog: float) -> dict[str, object]:
    return {
        "ts": timestamp.isoformat().replace("+00:00", "Z"),
        "lat": round(lat, 5),
        "lon": round(lon, 5),
        "sog": round(sog, 2),
        "cog": round(cog % 360, 2),
        "heading": round(cog % 360, 2),
    }


def _normal_track(index: int, start: datetime) -> list[dict[str, object]]:
    base_lat = 55.0 + (index % 5) * 0.22
    base_lon = 10.5 + (index % 4) * 0.35
    track = []
    for hour in range(13):
        course = 66.0 + (index % 3) * 3.0 + math.sin(hour / 3) * 1.5
        track.append(
            _point(
                start + timedelta(hours=hour),
                base_lat + hour * 0.055 + math.sin(hour / 2) * 0.006,
                base_lon + hour * 0.22,
                11.0 + (index % 4) * 0.7 + math.sin(hour) * 0.18,
                course,
            )
        )
    return track


def _anomaly_track(index: int, start: datetime) -> list[dict[str, object]]:
    center_lat = 59.472 + (index % 3) * 0.002
    center_lon = 24.722 + (index % 4) * 0.002
    track = []
    for hour in range(13):
        angle = math.radians((hour * 105 + index * 17) % 360)
        timestamp = start + timedelta(hours=hour + (3 if hour >= 7 and index % 3 == 0 else 0))
        track.append(
            _point(
                timestamp,
                center_lat + math.sin(angle) * 0.012,
                center_lon + math.cos(angle) * 0.018,
                0.35 + (hour % 4) * 0.18,
                math.degrees(angle) + 90,
            )
        )
    return track


def build_dataset() -> dict[str, object]:
    vessels: list[dict[str, object]] = []
    train_start = datetime(2026, 1, 10, tzinfo=timezone.utc)
    validation_start = datetime(2026, 6, 10, tzinfo=timezone.utc)

    for index in range(16):
        vessels.append(
            {
                "mmsi": str(210100000 + index),
                "vessel_class": VESSEL_CLASSES[index % len(VESSEL_CLASSES)],
                "behavior": "normal_transit",
                "split": "train",
                "track": _normal_track(index, train_start + timedelta(days=index)),
            }
        )
    for index in range(10):
        vessels.append(
            {
                "mmsi": str(220100000 + index),
                "vessel_class": VESSEL_CLASSES[index % len(VESSEL_CLASSES)],
                "behavior": "normal_transit",
                "split": "validation",
                "track": _normal_track(index + 30, validation_start + timedelta(days=index)),
            }
        )
    for index in range(12):
        vessels.append(
            {
                "mmsi": str(230100000 + index),
                "vessel_class": VESSEL_CLASSES[index % len(VESSEL_CLASSES)],
                "behavior": "suspicious_loitering",
                "split": "validation",
                "track": _anomaly_track(index, validation_start + timedelta(days=20 + index)),
            }
        )

    return {
        "dataset_version": "festival-trajectory-baseline-v2",
        "generated_at": "2026-07-20T00:00:00+00:00",
        "description": "Deterministic synthetic Baltic trajectory windows for baseline validation; not field data.",
        "licence": "Synthetic repository fixture",
        "vessels": vessels,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(build_dataset(), indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
