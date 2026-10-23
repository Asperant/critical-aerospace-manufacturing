"""Local transactional deduplication; transport and adapters are caller-owned."""

from cap_event_consumer.ledger import Outcome, ProcessedMessageLedger

__all__ = ["Outcome", "ProcessedMessageLedger"]
