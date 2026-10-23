import json
import logging

import pytest
from manufacturing_core.observability import correlation, health


@pytest.mark.parametrize("value", ["", "bad\nvalue", "x" * 129])
def test_invalid_correlation(value: str) -> None:
    with pytest.raises(ValueError):
        correlation(value)


def test_unavailable_health_is_explicit_and_secret_free(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="manufacturing_core"):
        result = health("", correlation_id="health-1")
    assert result.status == "UNAVAILABLE"
    assert result.correlation_id == "health-1"
    event = json.loads(caplog.records[-1].message)
    assert set(event) == {
        "service",
        "correlation_id",
        "operation",
        "outcome",
        "duration_ms",
    }
    assert event["outcome"] == "UNAVAILABLE"
    assert event["correlation_id"] == "health-1"
