"""OFAC SDN and EU consolidated sanctions list downloader/parser.

Downloads real sanctions data from official government sources:
- US OFAC SDN: https://www.treasury.gov/ofac/downloads/sdn.csv
- EU Consolidated: https://webgate.ec.europa.eu/fsd/fsf/public/files/csvFullSanctionsList/content

Parses vessel-specific entries and updates the local watchlist.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from xml.etree import ElementTree as ET

import httpx

from app.core.config import settings

_log = logging.getLogger("aegisais.sanctions.loader")

OFAC_SDN_URL = "https://sanctionslistservice.ofac.treas.gov/api/publicationpreview/exports/sdn.csv"
OFAC_SDN_ALT_URL = "https://www.treasury.gov/ofac/downloads/sdn.csv"
EU_SANCTIONS_CSV_URL = "https://webgate.ec.europa.eu/fsd/fsf/public/files/csvFullSanctionsList/content"
UN_CONSOLIDATED_XML_URL = "https://scsanctions.un.org/resources/xml/en/consolidated.xml"

_HTTP_HEADERS = {
    "User-Agent": "AegisAIS/1.0 (maritime-sanctions-checker)",
    "Accept": "text/csv, text/plain, */*",
}

# Path to local watchlist
_WATCHLIST_PATH = Path(__file__).parent / "data" / "sanctions_watchlist.json"

# IMO number pattern
_IMO_PATTERN = re.compile(r"\bIMO\s*(\d{7})\b", re.IGNORECASE)
# MMSI pattern
_MMSI_PATTERN = re.compile(r"\bMMSI\s*(\d{9})\b", re.IGNORECASE)


def _resolve_watchlist_path(path: Optional[Path | str] = None) -> Path:
    if path is not None:
        return Path(path)

    configured = (settings.SANCTIONS_WATCHLIST_PATH or "").strip()
    if configured:
        return Path(configured)

    return _WATCHLIST_PATH


async def fetch_ofac_sdn() -> dict[str, Any]:
    """Fetch and parse OFAC SDN list for vessel entries.

    The SDN CSV has columns:
    ent_num, SDN_Name, SDN_Type, Program, Title, Call_Sign, Vess_type, Tonnage, GRT, Vess_flag, Vess_owner, Remarks

    We filter for SDN_Type == 'vessel' or '-vessel-' in remarks.
    """
    vessels: dict[str, list] = {"mmsi": [], "imo": [], "names": []}

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=_HTTP_HEADERS) as client:
            resp = await client.get(OFAC_SDN_URL)
            if resp.status_code >= 400:
                # Try alternate URL
                resp = await client.get(OFAC_SDN_ALT_URL)
            resp.raise_for_status()

        reader = csv.reader(io.StringIO(resp.text))
        for row in reader:
            if len(row) < 12:
                continue

            sdn_name = row[1].strip() if len(row) > 1 else ""
            sdn_type = row[2].strip().lower() if len(row) > 2 else ""
            remarks = row[11].strip() if len(row) > 11 else ""

            # Filter for vessels
            is_vessel = sdn_type == "vessel" or "vessel" in sdn_type
            if not is_vessel:
                continue

            # Extract vessel name
            if sdn_name:
                vessels["names"].append(sdn_name.upper())

            # Extract IMO from remarks
            imo_match = _IMO_PATTERN.search(remarks)
            if imo_match:
                vessels["imo"].append(imo_match.group(1))

            # Extract MMSI from remarks
            mmsi_match = _MMSI_PATTERN.search(remarks)
            if mmsi_match:
                vessels["mmsi"].append(mmsi_match.group(1))

        _log.info(
            "OFAC SDN parsed: %d vessels, %d IMOs, %d MMSIs",
            len(vessels["names"]), len(vessels["imo"]), len(vessels["mmsi"]),
        )
        return vessels

    except Exception as e:
        _log.error("Failed to fetch OFAC SDN: %s", e)
        return {"mmsi": [], "imo": [], "names": []}


async def fetch_eu_sanctions() -> dict[str, Any]:
    """Fetch and parse EU consolidated sanctions list for vessel entries.

    The EU CSV includes entity types; we filter for vessels/ships.
    """
    vessels: dict[str, list] = {"mmsi": [], "imo": [], "names": []}

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=_HTTP_HEADERS) as client:
            resp = await client.get(EU_SANCTIONS_CSV_URL)
            resp.raise_for_status()

        reader = csv.DictReader(io.StringIO(resp.text), delimiter=";")
        for row in reader:
            entity_type = (row.get("Entity_SubjectType", "") or "").lower()
            if "vessel" not in entity_type and "ship" not in entity_type:
                continue

            name = (row.get("NameAlias_WholeName", "") or "").strip()
            if name:
                vessels["names"].append(name.upper())

            # EU list includes identification details in a separate field
            ident = row.get("Identification_Number", "") or ""
            imo_match = _IMO_PATTERN.search(ident)
            if imo_match:
                vessels["imo"].append(imo_match.group(1))
            mmsi_match = _MMSI_PATTERN.search(ident)
            if mmsi_match:
                vessels["mmsi"].append(mmsi_match.group(1))

        _log.info(
            "EU sanctions parsed: %d vessels, %d IMOs, %d MMSIs",
            len(vessels["names"]), len(vessels["imo"]), len(vessels["mmsi"]),
        )
        return vessels

    except Exception as e:
        _log.error("Failed to fetch EU sanctions: %s", e)
        return {"mmsi": [], "imo": [], "names": []}


async def fetch_un_sanctions() -> dict[str, Any]:
    """Fetch and parse the UN consolidated sanctions XML for vessel entries."""
    vessels: dict[str, list[str]] = {"mmsi": [], "imo": [], "names": []}

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=_HTTP_HEADERS) as client:
            resp = await client.get(UN_CONSOLIDATED_XML_URL)
            resp.raise_for_status()

        root = ET.fromstring(resp.text)
        for entity in root.findall(".//INDIVIDUAL") + root.findall(".//ENTITY"):
            text_parts = [value.strip() for value in entity.itertext() if value and value.strip()]
            if not text_parts:
                continue

            combined = " ".join(text_parts)
            lowered = combined.lower()
            if "vessel" not in lowered and "ship" not in lowered:
                continue

            name = (
                entity.findtext("FIRST_NAME")
                or entity.findtext("NAME_ORIGINAL_SCRIPT")
                or entity.findtext("UN_LIST_TYPE")
            )
            if name and name.strip():
                vessels["names"].append(name.strip().upper())

            for candidate in text_parts:
                imo_match = _IMO_PATTERN.search(candidate)
                if imo_match:
                    vessels["imo"].append(imo_match.group(1))

                mmsi_match = _MMSI_PATTERN.search(candidate)
                if mmsi_match:
                    vessels["mmsi"].append(mmsi_match.group(1))

        _log.info(
            "UN sanctions parsed: %d vessels, %d IMOs, %d MMSIs",
            len(vessels["names"]), len(vessels["imo"]), len(vessels["mmsi"]),
        )
        return vessels

    except Exception as e:
        _log.error("Failed to fetch UN sanctions: %s", e)
        return {"mmsi": [], "imo": [], "names": []}


async def update_watchlist_from_official_sources() -> dict[str, int]:
    """Fetch OFAC + EU sanctions, merge, and save to local watchlist.

    Returns counts of unique entries per category.
    """
    ofac = await fetch_ofac_sdn()
    eu = await fetch_eu_sanctions()
    un = await fetch_un_sanctions()

    # Merge and deduplicate
    merged = {
        "mmsi": sorted(set(ofac["mmsi"] + eu["mmsi"] + un["mmsi"])),
        "imo": sorted(set(ofac["imo"] + eu["imo"] + un["imo"])),
        "names": sorted(set(ofac["names"] + eu["names"] + un["names"])),
        "_source": "OFAC SDN + EU Consolidated + UN Consolidated",
        "_updated_at": datetime.now(timezone.utc).isoformat(),
    }

    # Write to local file
    watchlist_path = _resolve_watchlist_path()
    watchlist_path.parent.mkdir(parents=True, exist_ok=True)
    with open(watchlist_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2)

    counts = {
        "mmsi": len(merged["mmsi"]),
        "imo": len(merged["imo"]),
        "names": len(merged["names"]),
    }
    _log.info("Watchlist updated from official sources: %s", counts)

    # Reload into the sanctions service memory
    from app.modules.sanctions.service import load_watchlist
    load_watchlist(path=watchlist_path)

    return counts
