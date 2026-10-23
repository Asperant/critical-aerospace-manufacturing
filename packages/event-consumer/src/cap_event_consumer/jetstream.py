"""Configurable durable pull boundary; no production stream/subject provisioning."""

import asyncio
import math
from contextlib import suppress
from dataclasses import dataclass, field

from nats.aio.msg import Msg
from nats.js.api import AckPolicy, ConsumerConfig, DeliverPolicy
from nats.js.client import JetStreamContext
from nats.js.errors import NotFoundError

from cap_event_consumer.consumer import Consumer, DeliveryContext
from cap_event_consumer.ledger import Outcome


@dataclass(frozen=True)
class Binding:
    stream: str
    subject: str
    durable: str
    ack_wait: float
    max_deliver: int
    deliver_policy: DeliverPolicy

    def config(self) -> ConsumerConfig:
        if not all(
            value.strip() for value in (self.stream, self.subject, self.durable)
        ):
            raise ValueError("explicit stream, subject and durable required")
        if self.ack_wait <= 0 or self.max_deliver <= 0:
            raise ValueError("explicit positive ACK wait and delivery limit required")
        return ConsumerConfig(
            durable_name=self.durable,
            filter_subject=self.subject,
            ack_policy=AckPolicy.EXPLICIT,
            ack_wait=self.ack_wait,
            max_deliver=self.max_deliver,
            deliver_policy=self.deliver_policy,
        )


@dataclass(frozen=True)
class JetStreamDelivery:
    message: Msg
    ack_timeout: float

    @property
    def data(self) -> bytes:
        return self.message.data

    async def ack(self) -> None:
        await self.message.ack_sync(timeout=self.ack_timeout)

    async def nak(self) -> None:
        await self.message.nak()


@dataclass
class JetStreamConsumer:
    subscription: JetStreamContext.PullSubscription
    consumer: Consumer
    context: DeliveryContext
    ack_timeout: float
    closed: bool = False
    _active: set[asyncio.Task[object]] = field(default_factory=set, init=False)

    @classmethod
    async def bind(
        cls,
        js: JetStreamContext,
        binding: Binding,
        consumer: Consumer,
        context: DeliveryContext,
        *,
        ack_timeout: float,
    ) -> "JetStreamConsumer":
        config = binding.config()
        if ack_timeout <= 0:
            raise ValueError("positive ACK timeout required")
        # Stream ownership/routing belongs to the runtime owner. Never create it.
        await js.stream_info(binding.stream)
        try:
            existing = (await js.consumer_info(binding.stream, binding.durable)).config
        except NotFoundError:
            existing = None
        if existing is not None and any(
            getattr(existing, name) != getattr(config, name)
            for name in (
                "durable_name",
                "filter_subject",
                "ack_policy",
                "ack_wait",
                "max_deliver",
                "deliver_policy",
            )
        ):
            raise ValueError(
                "existing durable configuration differs from approved binding"
            )
        subscription = await js.pull_subscribe(
            binding.subject,
            durable=binding.durable,
            stream=binding.stream,
            config=config,
        )
        return cls(subscription, consumer, context, ack_timeout)

    async def receive_once(self, *, timeout: float) -> Outcome:
        if self.closed:
            raise RuntimeError("consumer is closed")
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("finite positive receive timeout required")
        task = asyncio.current_task()
        if task is None:
            raise RuntimeError("delivery requires an asyncio task")
        self._active.add(task)
        try:
            fetch = asyncio.create_task(
                self.subscription.fetch(batch=1, timeout=timeout)
            )
            try:
                messages = await asyncio.shield(fetch)
            except asyncio.CancelledError:
                # Settle the bounded client fetch before unsubscribing. A message
                # arriving during shutdown remains unACKed for durable redelivery.
                with suppress(Exception):
                    await fetch
                raise
            return await self.consumer.handle(
                JetStreamDelivery(messages[0], self.ack_timeout), self.context
            )
        finally:
            self._active.discard(task)

    async def close(self) -> None:
        # Only stop local delivery. Durable state and unACKed work must survive.
        self.closed = True
        pending = [task for task in self._active if task is not asyncio.current_task()]
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        await self.subscription.unsubscribe()
