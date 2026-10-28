"""Strict wire-level primitives shared by the snapshot consumer and the plan decoder.

Nothing here reads the local clock, trims, case-folds or coerces a value: a payload is
either exactly what the contract spells or it is rejected with a value-free error.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Collection, Mapping
from datetime import UTC, datetime
from typing import Any, NoReturn

from manufacturing_scheduler.errors import ContractError

#: Largest integer magnitude exactly representable by a JSON consumer using doubles.
MAX_SAFE_NUMBER = 9007199254740991

_IDENT = re.compile(r"\S+")
_TIMESTAMP = re.compile(
    r"([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})"
    r"(?:\.([0-9]{1,6}))?(Z|[+-]00:00)"
)


class Reader:
    """Typed, path-tracking field access raising one chosen ``ContractError`` class."""

    def __init__(self, error: type[ContractError]) -> None:
        self._error = error

    def fail(self, code: str, path: str) -> NoReturn:
        raise self._error(code, path)

    def obj(self, value: Any, path: str, keys: Collection[str]) -> Mapping[str, Any]:
        if not isinstance(value, Mapping):
            self.fail("OBJECT_REQUIRED", path)
        fields: Mapping[str, Any] = value
        if any(not isinstance(key, str) for key in fields):
            self.fail("FIELD_NAME_NOT_STRING", path)
        if set(fields) != set(keys):
            code = "FIELD_MISSING" if set(keys) - set(fields) else "FIELD_UNKNOWN"
            self.fail(code, path)
        return fields

    def array(self, value: Any, path: str, *, min_items: int = 0) -> list[Any]:
        if not isinstance(value, list):
            self.fail("ARRAY_REQUIRED", path)
        items: list[Any] = value
        if len(items) < min_items:
            self.fail("ARRAY_TOO_SHORT", path)
        return items

    def ident(self, value: Any, path: str) -> str:
        """An opaque identity or revision: a string without any whitespace."""

        if not isinstance(value, str) or _IDENT.fullmatch(value) is None:
            self.fail("IDENTIFIER_INVALID", path)
        return value

    def text(self, value: Any, path: str) -> str:
        """Free text: nonblank, with no leading or trailing whitespace."""

        if not isinstance(value, str) or not value or value != value.strip():
            self.fail("TEXT_INVALID", path)
        return value

    def integer(self, value: Any, path: str, *, minimum: int = 0) -> int:
        if type(value) is not int or not minimum <= value <= MAX_SAFE_NUMBER:
            self.fail("INTEGER_INVALID", path)
        return value

    def number(self, value: Any, path: str, *, minimum: float | None = None) -> float:
        """A finite JSON number in the safe range; ``bool`` is never a number."""

        if type(value) is not int and type(value) is not float:
            self.fail("NUMBER_INVALID", path)
        # Bound an int before any float conversion: ``math.isfinite`` would raise
        # OverflowError for an arbitrarily large (but valid JSON) integer.
        if type(value) is int:
            if abs(value) > MAX_SAFE_NUMBER:
                self.fail("NUMBER_INVALID", path)
        elif not math.isfinite(value) or abs(value) > MAX_SAFE_NUMBER:
            self.fail("NUMBER_INVALID", path)
        if minimum is not None and value < minimum:
            self.fail("NUMBER_INVALID", path)
        return value

    def enum(self, value: Any, path: str, allowed: Collection[str]) -> str:
        if not isinstance(value, str) or value not in allowed:
            self.fail("ENUM_INVALID", path)
        return value

    def const(self, value: Any, path: str, expected: str) -> str:
        if not isinstance(value, str) or value != expected:
            self.fail("VERSION_UNSUPPORTED", path)
        return value

    def timestamp(self, value: Any, path: str, *, canonical: bool = False) -> datetime:
        """An aware UTC instant; naive values and other offsets are rejected.

        ``canonical`` additionally demands the single spelling ``...Z`` with no
        trailing zero in the fraction, so one instant has exactly one wire form.
        """

        match = _TIMESTAMP.fullmatch(value) if isinstance(value, str) else None
        if match is None:
            self.fail("TIMESTAMP_INVALID", path)
        year, month, day, hour, minute, second, fraction, zone = match.groups()
        if canonical and (zone != "Z" or (fraction or "x").endswith("0")):
            self.fail("TIMESTAMP_NOT_CANONICAL", path)
        try:
            return datetime(
                int(year),
                int(month),
                int(day),
                int(hour),
                int(minute),
                int(second),
                int((fraction or "").ljust(6, "0")),
                tzinfo=UTC,
            )
        except ValueError:
            self.fail("TIMESTAMP_INVALID", path)


def format_timestamp(value: datetime) -> str:
    """The canonical wire spelling of an aware UTC instant."""

    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(None):
        raise ValueError("an aware UTC datetime is required")
    text = value.strftime("%Y-%m-%dT%H:%M:%S")
    if value.microsecond:
        text += f".{value.microsecond:06d}".rstrip("0")
    return text + "Z"


def reject_oracle_fields(
    value: Any, error: type[ContractError], path: str = ""
) -> None:
    """Fail closed on any field name that mentions Simulator Oracle state.

    Iterative, so a deeply nested payload cannot exhaust the interpreter stack.
    """

    stack: list[tuple[str, Any]] = [(path, value)]
    while stack:
        here, node = stack.pop()
        if isinstance(node, Mapping):
            fields: Mapping[Any, Any] = node
            for key, child in fields.items():
                if isinstance(key, str) and "oracle" in key.casefold():
                    raise error("ORACLE_FIELD_REJECTED", here)
                stack.append((f"{here}/{key}", child))
        elif isinstance(node, list):
            items: list[Any] = node
            stack.extend(
                (f"{here}/{index}", child) for index, child in enumerate(items)
            )


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def _reject_constant(_: str) -> NoReturn:
    raise ValueError("non-finite JSON number")


def _finite_float(text: str) -> float:
    value = float(text)
    if not math.isfinite(value):
        raise ValueError("non-finite JSON number")
    return value


def loads_strict(text: str, error: type[ContractError]) -> Any:
    """Decode JSON, rejecting duplicate fields, NaN, Infinity and overflowing floats."""

    if not isinstance(text, str):
        raise error("JSON_INVALID", "")
    try:
        return json.loads(
            text,
            object_pairs_hook=_object_without_duplicates,
            parse_constant=_reject_constant,
            parse_float=_finite_float,
        )
    except ValueError:
        raise error("JSON_INVALID", "") from None


def canonical_json(value: Any) -> str:
    """Sorted, compact, ASCII-only JSON; non-finite numbers are an error."""

    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    )


def sha256_digest(value: Any) -> str:
    """``sha256:<hex>`` over :func:`canonical_json` of the decoded document."""

    encoded = canonical_json(value).encode("ascii")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()
