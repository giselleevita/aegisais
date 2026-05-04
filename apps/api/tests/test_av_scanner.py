"""Unit tests for the AV scanner (Issue #2).

All ClamAV I/O is mocked — no real ClamAV daemon required.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import patch

import pytest


def _make_clamd_mock(scan_return, raise_exc=None):
    clamd_mod = types.ModuleType("clamd")

    class FakeSocket:
        def scan(self, path: str):
            if raise_exc:
                raise raise_exc
            return scan_return

    clamd_mod.ClamdNetworkSocket = lambda host, port: FakeSocket()
    clamd_mod.ClamdUnixSocket = lambda path: FakeSocket()
    return clamd_mod


def test_scan_clean_file(tmp_path):
    f = tmp_path / "ais_data.csv"
    f.write_text("mmsi,timestamp,lat,lon\n123456789,2024-01-01,55.0,12.0\n")

    clamd_mock = _make_clamd_mock({str(f): ("OK", None)})
    with patch.dict(sys.modules, {"clamd": clamd_mock}):
        from app.services.av_scanner import _ClamAVScanner
        result = _ClamAVScanner().scan(f)

    assert not result.infected
    assert result.error is None


def test_scan_infected_file(tmp_path):
    f = tmp_path / "malware.csv"
    f.write_text("X5O!P%@AP")

    clamd_mock = _make_clamd_mock({str(f): ("FOUND", "Eicar-Test-Signature")})
    with patch.dict(sys.modules, {"clamd": clamd_mock}):
        from app.services.av_scanner import _ClamAVScanner
        result = _ClamAVScanner().scan(f)

    assert result.infected
    assert result.virus_name == "Eicar-Test-Signature"


def test_scan_clamav_unavailable(tmp_path):
    """When ClamAV is unreachable, returns non-infected with error message."""
    f = tmp_path / "data.csv"
    f.write_text("mmsi,timestamp,lat,lon\n")

    clamd_mock = _make_clamd_mock(None, raise_exc=ConnectionRefusedError("ClamAV down"))
    with patch.dict(sys.modules, {"clamd": clamd_mock}):
        from app.services.av_scanner import _ClamAVScanner
        result = _ClamAVScanner().scan(f)

    assert not result.infected
    assert result.error is not None


def test_scan_clamd_not_installed(tmp_path):
    """If clamd package missing, returns non-infected with error."""
    f = tmp_path / "data.csv"
    f.write_text("mmsi,timestamp,lat,lon\n")

    with patch.dict(sys.modules, {"clamd": None}):
        saved = sys.modules.pop("clamd", None)
        try:
            from app.services.av_scanner import _ClamAVScanner
            result = _ClamAVScanner().scan(f)
        finally:
            if saved is not None:
                sys.modules["clamd"] = saved

    assert not result.infected


def test_scan_none_return_means_clean(tmp_path):
    """clamd.scan() returning None means no infection found."""
    f = tmp_path / "data.csv"
    f.write_text("mmsi,timestamp,lat,lon\n")

    clamd_mock = _make_clamd_mock(None)
    with patch.dict(sys.modules, {"clamd": clamd_mock}):
        from app.services.av_scanner import _ClamAVScanner
        result = _ClamAVScanner().scan(f)

    assert not result.infected
