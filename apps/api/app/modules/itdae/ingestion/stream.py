import asyncio

from app.core.logging import logger
from app.services.workers.heartbeat import WorkerHeartbeat

HEARTBEAT = WorkerHeartbeat("/tmp/worker_itdae_heartbeat")


class ITDAEStreamManager:
    """Manages live AIS data ingestion.

    When AISSTREAM_API_KEY is configured, delegates to the real
    AISStreamClient (aisstream.io WebSocket).  Otherwise, runs as a
    heartbeat-only stub.
    """

    def __init__(self):
        self.is_running = False
        self._aisstream_client = None

    async def start(self):
        if self.is_running:
            logger.info("ITDAE stream is already running.")
            return
        self.is_running = True

        # Attempt to start real AIS stream client (GAP-02)
        try:
            from app.core.config import settings
            if settings.AISSTREAM_API_KEY:
                from app.modules.itdae.ingestion.aisstream_client import aisstream_client
                self._aisstream_client = aisstream_client
                asyncio.create_task(aisstream_client.connect())
                logger.info("ITDAE stream started with live aisstream.io feed.")
            else:
                logger.info("ITDAE stream started (no AISSTREAM_API_KEY — stub mode).")
        except Exception as e:
            logger.warning("Failed to start AIS stream client: %s — running in stub mode", e)

    async def stop(self):
        if not self.is_running:
            logger.info("ITDAE stream is not running.")
            return
        if self._aisstream_client:
            await self._aisstream_client.disconnect()
            self._aisstream_client = None
        self.is_running = False
        logger.info("ITDAE stream stopped.")

stream_manager = ITDAEStreamManager()


async def main() -> None:
    """Keep the ingestion container alive until the live AIS feed is wired (Sprint 2 liveness)."""
    await stream_manager.start()
    while True:
        HEARTBEAT.on_loop_tick()
        await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
