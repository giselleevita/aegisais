"""File-based liveness heartbeats for Docker healthchecks (Sprint 2)."""
from __future__ import annotations

import time
from pathlib import Path


class WorkerHeartbeat:
    """
    Touch a heartbeat file every `interval_sec` or every `every_n_messages` successful
    message handlers, whichever comes first (IMPLEMENTATION_PLAN Task 2.3).
    """

    def __init__(
        self,
        path: str | Path,
        *,
        interval_sec: float = 30.0,
        every_n_messages: int = 100,
    ) -> None:
        self.path = Path(path)
        self.interval_sec = interval_sec
        self.every_n_messages = every_n_messages
        self._last_write = 0.0
        self._msg_since_beat = 0

    def on_successful_message(self) -> None:
        """Call after a message is fully processed without fatal error."""
        self._msg_since_beat += 1
        now = time.time()
        if self._msg_since_beat >= self.every_n_messages or (
            now - self._last_write >= self.interval_sec
        ):
            self._write(now)
            self._msg_since_beat = 0

    def on_loop_tick(self) -> None:
        """Call once per consumer loop iteration (keeps heartbeat fresh when idle)."""
        now = time.time()
        if now - self._last_write >= self.interval_sec:
            self._write(now)

    def _write(self, ts: float) -> None:
        self.path.write_text(str(int(ts)), encoding="ascii")
        self._last_write = ts
