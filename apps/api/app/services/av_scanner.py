"""Pluggable AV/malware scanning interface for uploaded files (Issue #2).

Usage:
    from app.services.av_scanner import scan_file, AVScanResult

    result = scan_file(path)
    if result.infected:
        raise ...

Environment variables:
    CLAMAV_HOST   — ClamAV host (default: clamav)
    CLAMAV_PORT   — ClamAV TCP port (default: 3310)
    CLAMAV_SOCKET — Unix socket path; if set, overrides host/port
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

_log = logging.getLogger("aegisais.av_scanner")


@dataclass
class AVScanResult:
    infected: bool
    virus_name: str | None = None
    error: str | None = None
    details: dict = field(default_factory=dict)


class _ClamAVScanner:
    """ClamAV client via clamd (Unix socket or TCP)."""

    def __init__(self) -> None:
        self._socket = os.environ.get("CLAMAV_SOCKET", "")
        self._host = os.environ.get("CLAMAV_HOST", "clamav")
        self._port = int(os.environ.get("CLAMAV_PORT", "3310"))

    def scan(self, path: Path) -> AVScanResult:
        try:
            import clamd  # type: ignore[import-untyped]
        except ImportError:
            _log.error("clamd package not installed — pip install clamd")
            return AVScanResult(infected=False, error="clamd not installed")

        try:
            if self._socket:
                cd = clamd.ClamdUnixSocket(path=self._socket)
            else:
                cd = clamd.ClamdNetworkSocket(host=self._host, port=self._port)

            result = cd.scan(str(path))
            if result is None:
                return AVScanResult(infected=False)

            file_key = str(path)
            status, virus = result.get(file_key, ("OK", None))
            if status == "FOUND":
                _log.warning("AV scan: INFECTED file=%s virus=%s", path.name, virus)
                return AVScanResult(infected=True, virus_name=virus)
            return AVScanResult(infected=False)

        except Exception as exc:  # noqa: BLE001
            _log.error("AV scan failed for %s: %s", path.name, exc)
            return AVScanResult(infected=False, error=str(exc))


_scanner = _ClamAVScanner()


def scan_file(path: Path) -> AVScanResult:
    """Scan a file for malware. Returns AVScanResult; never raises."""
    _log.info("av_scan_start file=%s", path.name)
    result = _scanner.scan(path)
    _log.info(
        "av_scan_complete file=%s infected=%s error=%s",
        path.name, result.infected, result.error,
    )
    return result
