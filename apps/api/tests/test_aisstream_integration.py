"""Integration tests for AISStreamClient with a mock WebSocket server (Issue #3).

No real aisstream.io API key required — all WebSocket I/O is mocked.
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

POSITION_REPORT = {
    "MessageType": "PositionReport",
    "MetaData": {
        "MMSI": 123456789,
        "time_utc": "2024-06-01T12:00:00Z",
    },
    "Message": {
        "PositionReport": {
            "UserID": 123456789,
            "Latitude": 55.6761,
            "Longitude": 12.5683,
            "Sog": 8.5,
            "Cog": 270.0,
            "TrueHeading": 268,
        }
    },
}


class _MockWebSocket:
    """Minimal async WebSocket context manager yielding one message then closing."""

    def __init__(self, messages):
        self._messages = messages
        self.sent = []

    async def send(self, msg):
        self.sent.append(msg)

    async def close(self):
        pass

    def __aiter__(self):
        return self._iter()

    async def _iter(self):
        for m in self._messages:
            yield m

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


@pytest.mark.asyncio
async def test_aisstream_client_processes_position_report():
    """Client parses a PositionReport and calls process_point."""
    processed = []

    def fake_process(point):
        processed.append(point)
        return {"alerts": []}

    mock_ws = _MockWebSocket([json.dumps(POSITION_REPORT)])
    websockets_mock = MagicMock()
    websockets_mock.connect = MagicMock(return_value=mock_ws)

    import sys
    with patch.dict(sys.modules, {"websockets": websockets_mock}):
        with patch("app.modules.itdae.ingestion.aisstream_client.process_point", side_effect=fake_process):
            with patch("app.modules.itdae.ingestion.aisstream_client.settings") as mock_settings:
                mock_settings.AISSTREAM_API_KEY = "test-key"
                mock_settings.AISSTREAM_BBOX = ""

                from app.modules.itdae.ingestion import aisstream_client
                import importlib
                importlib.reload(aisstream_client)

                client = aisstream_client.AISStreamClient(api_key="test-key")
                client._running = True
                await client._connect_loop()

    assert len(processed) == 1
    assert processed[0].mmsi == "123456789"
    assert abs(processed[0].lat - 55.6761) < 0.001


@pytest.mark.asyncio
async def test_aisstream_client_handles_connection_error():
    """Client handles ConnectionRefusedError without crashing."""
    class _FailWS:
        async def __aenter__(self):
            raise ConnectionRefusedError("simulated failure")
        async def __aexit__(self, *args):
            pass

    websockets_mock = MagicMock()
    websockets_mock.connect = MagicMock(return_value=_FailWS())

    import sys
    with patch.dict(sys.modules, {"websockets": websockets_mock}):
        with patch("app.modules.itdae.ingestion.aisstream_client.process_point", return_value={"alerts": []}):
            with patch("app.modules.itdae.ingestion.aisstream_client.settings") as mock_settings:
                mock_settings.AISSTREAM_API_KEY = "test-key"
                mock_settings.AISSTREAM_BBOX = ""
                with patch("asyncio.sleep", return_value=None):
                    from app.modules.itdae.ingestion import aisstream_client
                    import importlib
                    importlib.reload(aisstream_client)

                    client = aisstream_client.AISStreamClient(api_key="test-key")
                    client._running = False  # stop after one attempt
                    await client._connect_loop()
