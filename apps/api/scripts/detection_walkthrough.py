"""Exercise real detection rules on synthetic points without starting services.

From apps/api after installing the project:
    python -m scripts.detection_walkthrough

Uses the checkout's configured thresholds. A changed result exits nonzero rather
than printing a successful demonstration for a different policy configuration.
"""

from datetime import datetime, timedelta, timezone

from app.detection.rules import rule_position_invalid, rule_teleport
from app.infrastructure.ingest.loaders import AisPoint


def main() -> None:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    previous = AisPoint("123456789", start, 40.0, -74.0)
    cases = [
        ("normal movement", rule_teleport, 40.001, 60, "NO_ALERT"),
        ("impossible jump", rule_teleport, 41.0, 60, "TELEPORT"),
        ("invalid latitude", rule_position_invalid, 200.0, 60, "POSITION_INVALID"),
        ("out-of-order timestamp", rule_teleport, 41.0, -60, "NO_ALERT"),
    ]
    mismatches = []
    for label, rule, latitude, elapsed, expected in cases:
        current = AisPoint(
            previous.mmsi, start + timedelta(seconds=elapsed), latitude, -74.0
        )
        result = rule(previous, current)
        actual = result["type"] if result else "NO_ALERT"
        print(f"{label}: {actual}")
        if actual != expected:
            mismatches.append(f"{label}: expected {expected}, got {actual}")

    if mismatches:
        raise SystemExit("\n".join(mismatches))


if __name__ == "__main__":
    main()
