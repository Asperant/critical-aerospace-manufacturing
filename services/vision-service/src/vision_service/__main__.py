"""Run the Vision JetStream worker from explicit deployment configuration."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from cap_observability.telemetry import configure

from vision_service.worker import (
    VisionWorker,
    WorkerConfig,
    artifact_store_from_env,
    run_nats,
)


async def serve() -> None:
    telemetry = configure("vision-service", "0.1.0")
    store = None
    try:
        config = WorkerConfig.from_env()
        store = artifact_store_from_env()
        worker = VisionWorker(
            store,
            publisher=_NoopPublisher(),
            config=config,
            clock=lambda: datetime.now(UTC),
        )
        await run_nats(config, worker)
    finally:
        if store is not None:
            store.client.close()
        telemetry.shutdown()


class _NoopPublisher:
    async def publish(self, subject: str, data: bytes) -> None:
        raise RuntimeError("JetStream publisher is installed by run_nats")


if __name__ == "__main__":
    asyncio.run(serve())
