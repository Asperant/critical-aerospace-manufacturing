import logging

import pytest
from cap_observability.standard import check_health_report
from manufacturing_core.observability import (
    core_health_report,
    correlation,
    health,
)


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
    event = caplog.records[-1]
    assert event.getMessage() == "Core operation"
    assert getattr(event, "event_name", None) == "core.operation"
    assert getattr(event, "correlation_id", None) == "health-1"
    attributes = getattr(event, "attributes", {})
    assert attributes["operation"] == "health"
    assert attributes["outcome"] == "UNAVAILABLE"
    assert event.exc_info is None


@pytest.mark.parametrize("status", ["READY", "UNAVAILABLE"])
def test_core_health_report_uses_standard_readiness_semantics(status: str) -> None:
    report = core_health_report(
        environment="core-test",
        database_status=status,  # type: ignore[arg-type]
        correlation_id="health-2",
    )
    assert check_health_report(report) == []
    assert report["schema"] == "cap.health/v1"
    assert report["service"] == "manufacturing-core"
    assert report["correlation_id"] == "health-2"
    assert report["status"] == status
