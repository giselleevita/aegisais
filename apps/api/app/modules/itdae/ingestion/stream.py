import asyncio

from app.core.logging import logger
from app.services.workers.heartbeat import WorkerHeartbeat

HEARTBEAT = WorkerHeartbeat("/tmp/worker_itdae_heartbeat")


class ITDAEStreamManager:
    def __init__(self):
        self.is_running = False

    async def start(self):
        if self.is_running:
            logger.info("ITDAE stream is already running.")
            return
        self.is_running = True
        logger.info("ITDAE stream started.")
        # TODO: Implement actual aisstream.io connection

    async def stop(self):
        if not self.is_running:
            logger.info("ITDAE stream is not running.")
            return
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
