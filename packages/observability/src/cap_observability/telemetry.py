"""One call wires a service's telemetry to the field standard (WP-OBS-001 slice C).

    from cap_observability.telemetry import configure
    telemetry = configure("manufacturing-core", "0.1.0")
    logging.getLogger(__name__).info(
        "query finished",
        extra={"event_name": "core.query_completed", "correlation_id": cid},
    )
    telemetry.shutdown()  # flush on exit

What ``configure`` does:

* builds the ``cap.resource/v1`` identity from the environment
  (``CAP_ENVIRONMENT``, ``CAP_ENVIRONMENT_CLASS``, ``CAP_RELEASE_ID``,
  ``CAP_DEPLOYMENT_ID``, ``CAP_RUNTIME_PROFILE``) and refuses invalid values;
* writes every log record to stdout as one ``cap.log/v1`` JSON line — container
  logs stay structured even without a Collector (Item 47 §27);
* when ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set (for example
  ``http://127.0.0.1:54318``), also ships the same records to the Collector, and
  sets up OpenTelemetry tracing and metrics exporters to it.

Logs are shipped by ``OtlpLogHandler`` rather than OpenTelemetry's Python log
SDK: that SDK is still experimental and its ``LoggingHandler`` is deprecated
(opentelemetry-sdk 1.45). Traces and metrics use the stable OpenTelemetry APIs.

The handlers never raise into the application and never block it: records that
do not fit the standard are corrected (invalid context dropped, secrets
redacted, sizes bounded) and a full or unreachable exporter drops records with
a warning on stderr instead of slowing the service down.
"""

from __future__ import annotations

import json
import logging
import os
import queue
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import IO, Any

from cap_observability.otlp import logs_request
from cap_observability.standard import (
    ENVIRONMENT_CLASSES,
    MAX_RECORD_BYTES,
    SECRET_KEY,
    SECRET_VALUE,
    load_schema,
)

CONTEXT_FIELDS = (
    "correlation_id",
    "causation_id",
    "request_id",
    "world_id",
    "simulation_run_id",
    "workflow_instance_id",
    "agent_run_id",
    "scheduling_run_id",
    "data_pipeline_run_id",
    "evaluation_run_id",
    "deployment_id",
)
IDENTIFIER = re.compile(r"[A-Za-z0-9_.:-]{1,128}")
EVENT_NAME = re.compile(r"[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+")
ERROR_CODE = re.compile(r"[A-Z][A-Z0-9_]{2,63}")
ERROR_TYPE = re.compile(r"[A-Za-z_][A-Za-z0-9_.]{0,127}")
ATTRIBUTE_KEY = re.compile(r"[a-z][a-z0-9_.]{0,63}")
ENTITY_TYPE = re.compile(r"[A-Z][A-Za-z0-9]{1,63}")
UNCLASSIFIED_ERROR = "UNCLASSIFIED_ERROR"
REDACTED = "[REDACTED]"
_MARK = "_cap_observability"


# ---------------------------------------------------------------- resource ---


def _sanitize_id(value: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")[:40] or "dev"


def resource_from_env(
    service_name: str, service_version: str, environ: Mapping[str, str]
) -> dict[str, str]:
    """``cap.resource/v1`` attributes; raises ValueError on any invalid value.

    LOCAL is the only class with a default EnvironmentID (``local-<user>``);
    every shared environment must name itself (DX-INV-10: explicit config).
    """
    env_class = environ.get("CAP_ENVIRONMENT_CLASS", "LOCAL")
    env_id = environ.get("CAP_ENVIRONMENT")
    if env_id is None and env_class == "LOCAL":
        env_id = "local-" + _sanitize_id(environ.get("USER", "dev"))
    resource: dict[str, str] = {
        "service.name": service_name,
        "service.version": service_version,
        "deployment.environment.name": env_id or "",
        "cap.environment.class": env_class,
    }
    for variable, attribute in (
        ("CAP_RELEASE_ID", "cap.release.id"),
        ("CAP_DEPLOYMENT_ID", "cap.deployment.id"),
        ("CAP_RUNTIME_PROFILE", "cap.runtime.profile"),
        ("CAP_SERVICE_INSTANCE_ID", "service.instance.id"),
    ):
        if environ.get(variable):
            resource[attribute] = environ[variable]
    problems = _resource_problems(resource)
    if problems:
        raise ValueError("invalid telemetry resource: " + "; ".join(problems))
    return resource


def _resource_problems(resource: Mapping[str, str]) -> list[str]:
    """Check the flat string rules of the schema without needing jsonschema."""
    properties: dict[str, Any] = load_schema("resource.schema.json")["properties"]
    problems: list[str] = []
    for key, value in resource.items():
        rule: dict[str, Any] = properties[key]
        if "enum" in rule and value not in rule["enum"]:
            problems.append(f"{key}={value!r} is not one of {rule['enum']}")
        if "pattern" in rule and not re.search(rule["pattern"], value):
            problems.append(f"{key}={value!r} does not match {rule['pattern']}")
        if "maxLength" in rule and not 1 <= len(value) <= rule["maxLength"]:
            problems.append(f"{key} length must be 1..{rule['maxLength']}")
    if (
        resource["cap.environment.class"] in ("EVALUATION", "DEMO")
        and "cap.release.id" not in resource
    ):
        problems.append("EVALUATION and DEMO require CAP_RELEASE_ID")
    if not resource["deployment.environment.name"]:
        problems.append(
            f"CAP_ENVIRONMENT is required for {resource['cap.environment.class']}"
        )
    return problems


# ------------------------------------------------------------------ record ---


def _redact(text: str) -> str:
    for _label, pattern in SECRET_VALUE:
        text = pattern.sub(REDACTED, text)
    return text


def _severity(levelno: int) -> str:
    if levelno >= logging.CRITICAL:
        return "FATAL"
    if levelno >= logging.ERROR:
        return "ERROR"
    if levelno >= logging.WARNING:
        return "WARN"
    if levelno >= logging.INFO:
        return "INFO"
    return "DEBUG"


def _timestamp(created: float) -> str:
    moment = datetime.fromtimestamp(created, UTC)
    return moment.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _event_name(record: logging.LogRecord) -> str:
    given = getattr(record, "event_name", None)
    if isinstance(given, str) and len(given) <= 128 and EVENT_NAME.fullmatch(given):
        return given
    domain = re.sub(r"[^a-z0-9_]+", "_", record.name.lower()).strip("_") or "app"
    if not domain[0].isalpha():
        domain = "app_" + domain
    return f"{domain[:100]}.log"


def _trace_context() -> tuple[str, str] | None:
    try:
        from opentelemetry import trace
    except ImportError:  # pragma: no cover - only without opentelemetry-api
        return None
    context = trace.get_current_span().get_span_context()
    if not context.is_valid:
        return None
    return format(context.trace_id, "032x"), format(context.span_id, "016x")


def _attributes(value: object) -> dict[str, str | int | float | bool | None]:
    if not isinstance(value, Mapping):
        return {}
    clean: dict[str, str | int | float | bool | None] = {}
    for key, item in value.items():  # type: ignore[reportUnknownVariableType]
        if len(clean) == 16:
            break
        if not (isinstance(key, str) and ATTRIBUTE_KEY.fullmatch(key)):
            continue
        if SECRET_KEY.search(key):
            continue  # §36: a secret-bearing key never leaves the process
        if isinstance(item, str):
            clean[key] = _redact(item)[:256]
        elif item is None or isinstance(item, bool | int | float):
            clean[key] = item
    return clean


def _entity_refs(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    refs: list[dict[str, str]] = []
    for item in value[:10]:  # type: ignore[reportUnknownVariableType]
        if not isinstance(item, Mapping):
            continue
        kind, ident = item.get("type"), item.get("id")  # type: ignore[reportUnknownMemberType]
        if (
            isinstance(kind, str)
            and isinstance(ident, str)
            and ENTITY_TYPE.fullmatch(kind)
            and IDENTIFIER.fullmatch(ident)
        ):
            refs.append({"type": kind, "id": ident})
    return refs


def build_record(
    record: logging.LogRecord, resource: Mapping[str, str]
) -> dict[str, Any]:
    """A conforming ``cap.log/v1`` dict for one stdlib log record."""
    message = _redact(record.getMessage()) or "(empty message)"
    out: dict[str, Any] = {
        "timestamp": _timestamp(record.created),
        "severity": _severity(record.levelno),
        "service": resource["service.name"],
        "environment": resource["deployment.environment.name"],
        "event_name": _event_name(record),
        "message": message[:2048],
    }
    for attribute, name in (
        ("service.version", "service_version"),
        ("cap.environment.class", "environment_class"),
        ("cap.release.id", "release"),
    ):
        if attribute in resource:
            out[name] = resource[attribute]
    context = _trace_context()
    if context:
        out["trace_id"], out["span_id"] = context
    for name in CONTEXT_FIELDS:
        value = getattr(record, name, None)
        if isinstance(value, str) and IDENTIFIER.fullmatch(value):
            out[name] = value
    code = getattr(record, "error_code", None)
    if isinstance(code, str) and ERROR_CODE.fullmatch(code):
        out["error_code"] = code
    error_type = getattr(record, "error_type", None)
    if record.exc_info and record.exc_info[0] is not None and not error_type:
        exc = record.exc_info[0]
        error_type = f"{exc.__module__}.{exc.__qualname__}".removeprefix("builtins.")
    if isinstance(error_type, str) and ERROR_TYPE.fullmatch(error_type):
        out["error_type"] = error_type
    if out["severity"] in ("ERROR", "FATAL"):
        out.setdefault("error_code", UNCLASSIFIED_ERROR)  # §32: always a stable code
    refs = _entity_refs(getattr(record, "entity_refs", None))
    if refs:
        out["entity_refs"] = refs
    attributes = _attributes(getattr(record, "attributes", None))
    if attributes:
        out["attributes"] = attributes
    if len(json.dumps(out, ensure_ascii=False).encode()) > MAX_RECORD_BYTES:
        out.pop("attributes", None)  # §34: keep the record, shed the payload
        out["message"] = out["message"][:512]
    return out


class JsonFormatter(logging.Formatter):
    """Formats each record as one ``cap.log/v1`` JSON line."""

    def __init__(self, resource: Mapping[str, str]) -> None:
        super().__init__()
        self.resource = dict(resource)

    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            build_record(record, self.resource),
            ensure_ascii=False,
            separators=(",", ":"),
        )


# ---------------------------------------------------------- OTLP shipping ---

Poster = Callable[[str, bytes, float], int]


def _post(url: str, body: bytes, timeout: float) -> int:
    request = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return int(response.status)


class OtlpLogHandler(logging.Handler):
    """Ships ``cap.log/v1`` records to the Collector as OTLP/HTTP JSON batches.

    A bounded queue and one background thread: ``emit`` never blocks or raises.
    When the queue is full or the Collector is unreachable, records are dropped
    and counted, with at most one stderr warning per minute.
    """

    def __init__(
        self,
        endpoint: str,
        resource: Mapping[str, str],
        *,
        batch_size: int = 100,
        interval_s: float = 1.0,
        queue_size: int = 2048,
        timeout_s: float = 5.0,
        post: Poster = _post,
    ) -> None:
        super().__init__()
        self.url = endpoint.rstrip("/") + "/v1/logs"
        self.resource = dict(resource)
        self.batch_size = batch_size
        self.interval_s = interval_s
        self.timeout_s = timeout_s
        self.post = post
        self.dropped = 0
        self.sent = 0
        self._queue: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=queue_size)
        self._stop = threading.Event()
        self._send_lock = threading.Lock()
        # A fresh CI runner can have a monotonic clock below the throttle
        # interval. An explicit unset sentinel keeps the first warning
        # independent of the clock origin.
        self._last_warning: float | None = None
        self._thread = threading.Thread(
            target=self._run, name="cap-otlp-logs", daemon=True
        )
        self._thread.start()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._queue.put_nowait(build_record(record, self.resource))
        except queue.Full:
            self.dropped += 1
            self._warn("log queue full")
        except Exception:  # pragma: no cover - defensive; logging must not raise
            self.handleError(record)

    def _drain(self, limit: int) -> list[dict[str, Any]]:
        batch: list[dict[str, Any]] = []
        while len(batch) < limit:
            try:
                batch.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return batch

    def _send(self, batch: list[dict[str, Any]]) -> None:
        if not batch:
            return
        body = json.dumps(logs_request(self.resource, batch, "cap_observability"))
        try:
            status = self.post(self.url, body.encode(), self.timeout_s)
        except (OSError, urllib.error.URLError) as exc:
            status = 0
            reason = str(exc)
        else:
            reason = f"HTTP {status}"
        if 200 <= status < 300:
            self.sent += len(batch)
        else:
            self.dropped += len(batch)
            self._warn(f"collector rejected or unreachable ({reason})")

    def _run(self) -> None:
        while not self._stop.wait(self.interval_s):
            self.flush()

    def flush(self) -> None:
        with self._send_lock:
            while batch := self._drain(self.batch_size):
                self._send(batch)

    def close(self) -> None:
        self._stop.set()
        self._thread.join(timeout=self.timeout_s + self.interval_s)
        self.flush()
        super().close()

    def _warn(self, what: str) -> None:
        now = time.monotonic()
        if self._last_warning is None or now - self._last_warning >= 60:
            self._last_warning = now
            print(
                f"cap_observability: {what}; {self.dropped} log records dropped so far",
                file=sys.stderr,
            )


# --------------------------------------------------------------- configure ---


@dataclass
class Telemetry:
    resource: dict[str, str]
    endpoint: str | None
    handlers: list[logging.Handler] = field(default_factory=list)
    providers: list[Any] = field(default_factory=list)

    def shutdown(self) -> None:
        """Flush and stop exporters; call once when the service stops."""
        root = logging.getLogger()
        for handler in self.handlers:
            handler.flush()
            root.removeHandler(handler)
            if isinstance(handler, OtlpLogHandler):
                handler.close()
        for provider in self.providers:
            provider.shutdown()


def _otel_providers(resource: Mapping[str, str], endpoint: str) -> list[Any]:
    from opentelemetry import metrics, trace
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
        OTLPMetricExporter,
    )
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
        OTLPSpanExporter,
    )
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    otel_resource = Resource(dict(resource))  # exactly cap.resource/v1, no extras
    tracer_provider = TracerProvider(resource=otel_resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces"))
    )
    reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=f"{endpoint}/v1/metrics"),
        export_interval_millis=5000,
    )
    meter_provider = MeterProvider(resource=otel_resource, metric_readers=[reader])
    trace.set_tracer_provider(tracer_provider)
    metrics.set_meter_provider(meter_provider)
    return [tracer_provider, meter_provider]


def configure(
    service_name: str,
    service_version: str,
    *,
    environ: Mapping[str, str] | None = None,
    stream: IO[str] | None = None,
    level: int = logging.INFO,
) -> Telemetry:
    """Install standard logging (and OTLP export when configured) on the root logger.

    Calling it again replaces the handlers it installed before, never others.
    """
    env = os.environ if environ is None else environ
    resource = resource_from_env(service_name, service_version, env)
    root = logging.getLogger()
    for handler in list(root.handlers):
        if getattr(handler, _MARK, False):
            root.removeHandler(handler)
            handler.close()
    console = logging.StreamHandler(stream or sys.stdout)
    console.setFormatter(JsonFormatter(resource))
    handlers: list[logging.Handler] = [console]
    endpoint = env.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").rstrip("/") or None
    providers: list[Any] = []
    if endpoint:
        handlers.append(OtlpLogHandler(endpoint, resource))
        providers = _otel_providers(resource, endpoint)
    for handler in handlers:
        setattr(handler, _MARK, True)
        root.addHandler(handler)
    root.setLevel(level)
    return Telemetry(resource, endpoint, handlers, providers)


__all__ = [
    "ENVIRONMENT_CLASSES",
    "JsonFormatter",
    "OtlpLogHandler",
    "Telemetry",
    "build_record",
    "configure",
    "resource_from_env",
]
