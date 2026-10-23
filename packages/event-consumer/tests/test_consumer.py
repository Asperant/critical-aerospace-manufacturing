"""Pure admission/configuration checks; real transport acceptance is separate."""

import pytest
from cap_event_consumer.consumer import AdmissionError, identify_json
from cap_event_consumer.jetstream import Binding
from nats.js.api import DeliverPolicy


@pytest.mark.parametrize(
    "data", [b"[]", b"{}", b'{"event_id": null}', b'{"event_id": " "}']
)
def test_identity_required(data: bytes) -> None:
    with pytest.raises(AdmissionError):
        identify_json(data)


def test_original_identity() -> None:
    assert (
        identify_json(b'{"event_id": "original", "sequence": 99}').event_id
        == "original"
    )


def test_explicit_binding() -> None:
    with pytest.raises(ValueError, match="explicit"):
        Binding("", "subject", "durable", 1, 2, DeliverPolicy.ALL).config()
