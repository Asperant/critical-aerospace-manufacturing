"""Real subprocess death at the commit-to-ACK boundary, used only by tests."""

import asyncio
import os

import nats
from cap_event_consumer.consumer import DeliveryContext
from cap_event_consumer.jetstream import JetStreamDelivery
from worker_support import make_consumer


class CrashBeforeAck(JetStreamDelivery):
    async def ack(self) -> None:
        # Consumer.handle only invokes this after the local transaction commits.
        os._exit(71)


async def main() -> None:
    nc = await nats.connect(os.environ["CI_NATS_URL"])
    js = nc.jetstream()
    sub = await js.pull_subscribe(
        os.environ["EVT_TEST_SUBJECT"],
        durable="test-durable",
        stream=os.environ["EVT_TEST_STREAM"],
    )
    message = (await sub.fetch(1, timeout=5))[0]
    await make_consumer(os.environ["EVT_TEST_DSN"]).handle(
        CrashBeforeAck(message, 2), DeliveryContext()
    )


if __name__ == "__main__":
    asyncio.run(main())
