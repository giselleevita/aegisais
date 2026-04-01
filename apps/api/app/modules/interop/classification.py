"""NATO classification marking and data labeling (GAP-07).

Implements STANAG 4774 metadata marking for all data objects.
Classification levels: UNCLASSIFIED, RESTRICTED, CONFIDENTIAL, SECRET, TOP SECRET

All AegisAIS data defaults to NATO UNCLASSIFIED unless explicitly marked.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

_log = logging.getLogger("aegisais.classification")


class NATOClassification(str, Enum):
    """NATO security classification levels per STANAG 4774."""
    UNCLASSIFIED = "NATO UNCLASSIFIED"
    RESTRICTED = "NATO RESTRICTED"
    CONFIDENTIAL = "NATO CONFIDENTIAL"
    SECRET = "NATO SECRET"
    TOP_SECRET = "COSMIC TOP SECRET"


class TLPMarking(str, Enum):
    """Traffic Light Protocol markings for information sharing."""
    WHITE = "TLP:CLEAR"
    GREEN = "TLP:GREEN"
    AMBER = "TLP:AMBER"
    AMBER_STRICT = "TLP:AMBER+STRICT"
    RED = "TLP:RED"


DEFAULT_CLASSIFICATION = NATOClassification.UNCLASSIFIED
DEFAULT_TLP = TLPMarking.GREEN


def apply_classification(
    data: dict[str, Any],
    classification: NATOClassification = DEFAULT_CLASSIFICATION,
    tlp: TLPMarking = DEFAULT_TLP,
    releasable_to: Optional[list[str]] = None,
    originator: str = "AEGISAIS",
) -> dict[str, Any]:
    """Apply STANAG 4774 security marking to a data object.

    Adds a ``_classification`` metadata block to the dictionary.
    """
    data["_classification"] = {
        "classification": classification.value,
        "tlp": tlp.value,
        "releasable_to": releasable_to or ["NATO"],
        "originator": originator,
        "marking_standard": "STANAG 4774",
        "marked_at": datetime.now(timezone.utc).isoformat(),
    }
    return data


def classify_alert(
    alert_data: dict[str, Any],
    severity: int,
) -> dict[str, Any]:
    """Auto-classify alerts based on severity.

    - severity >= 90: RESTRICTED + TLP:AMBER
    - severity >= 60: RESTRICTED + TLP:GREEN
    - default: UNCLASSIFIED + TLP:GREEN
    """
    if severity >= 90:
        return apply_classification(
            alert_data,
            classification=NATOClassification.RESTRICTED,
            tlp=TLPMarking.AMBER,
        )
    elif severity >= 60:
        return apply_classification(
            alert_data,
            classification=NATOClassification.RESTRICTED,
            tlp=TLPMarking.GREEN,
        )
    return apply_classification(alert_data)


def classify_vessel_data(
    vessel_data: dict[str, Any],
    is_sanctions_flagged: bool = False,
) -> dict[str, Any]:
    """Classify vessel data based on sensitivity."""
    if is_sanctions_flagged:
        return apply_classification(
            vessel_data,
            classification=NATOClassification.RESTRICTED,
            tlp=TLPMarking.AMBER,
        )
    return apply_classification(vessel_data)


def classify_intelligence_product(
    product: dict[str, Any],
    product_type: str = "INTSUM",
) -> dict[str, Any]:
    """Classify intelligence products."""
    if product_type in ("INTSUM", "VESSEL_DOSSIER"):
        return apply_classification(
            product,
            classification=NATOClassification.RESTRICTED,
            tlp=TLPMarking.AMBER,
        )
    return apply_classification(product)
