"""Shared observability support for team-owned services (WP-OBS-001)."""

from cap_observability.standard import (
    ENVIRONMENT_CLASSES,
    MAX_RECORD_BYTES,
    SEVERITIES,
    check_health_report,
    check_log_lines,
    check_log_record,
    check_resource,
    load_schema,
)

__version__ = "0.1.0"
__all__ = [
    "ENVIRONMENT_CLASSES",
    "MAX_RECORD_BYTES",
    "SEVERITIES",
    "check_health_report",
    "check_log_lines",
    "check_log_record",
    "check_resource",
    "load_schema",
]
