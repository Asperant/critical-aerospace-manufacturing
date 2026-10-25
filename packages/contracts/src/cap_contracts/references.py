"""Deterministic, offline expansion of a bounded set of schema references."""

import copy
import re
from collections.abc import Callable
from pathlib import PurePosixPath
from typing import Any, NoReturn

from .errors import ContractError

_SCHEMA_MAPS = {
    "$defs",
    "definitions",
    "properties",
    "patternProperties",
    "dependentSchemas",
}
_SCHEMA_CHILDREN = {
    "items",
    "additionalProperties",
    "unevaluatedProperties",
    "unevaluatedItems",
    "propertyNames",
    "contains",
    "not",
    "if",
    "then",
    "else",
    "contentSchema",
}
_SCHEMA_LISTS = {"allOf", "anyOf", "oneOf", "prefixItems"}


def resolve_references(
    schema: dict[str, Any],
    *,
    document_path: str = "",
    load_local: Callable[[str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return a fresh expanded schema. Never fetch a URI or mutate a document.

    Fragment references use strict JSON Pointers. File references are canonical
    relative paths inside packages/contracts and require an explicit loader that
    checks approval and hashes. Cycles, anchors, rebasing IDs and dynamic references
    are unsupported. Ref siblings retain conjunction semantics via allOf.
    """
    documents = {document_path: schema}
    active: set[tuple[str, str]] = set()
    remaining_nodes = 10000

    def fail(code: str) -> NoReturn:
        raise ContractError(code, "local schema reference cannot be verified")

    def target(ref: object, current: str) -> tuple[str, str, object]:
        if not isinstance(ref, str) or any(c in ref for c in ("%", "\\", "?", ":")):
            fail("SCHEMA_REF_FORBIDDEN")
        filename, sep, fragment = ref.partition("#")
        path = current
        if filename:
            parts = filename.split("/")
            if any(part in {"", ".", ".."} for part in parts):
                fail("SCHEMA_REF_FORBIDDEN")
            path = str(PurePosixPath(current).parent / filename)
            if not path.startswith("packages/contracts/") or load_local is None:
                fail("SCHEMA_REF_FORBIDDEN")
            if path not in documents:
                documents[path] = load_local(path)
        if sep and fragment and not fragment.startswith("/"):
            fail("SCHEMA_REF_FORBIDDEN")
        if re.search(r"~(?![01])", fragment):
            fail("SCHEMA_REF_FORBIDDEN")
        node: Any = documents[path]
        for token in fragment.split("/")[1:] if fragment else ():
            if re.search(r"~(?![01])", token):
                fail("SCHEMA_REF_FORBIDDEN")
            token = token.replace("~1", "/").replace("~0", "~")
            if isinstance(node, dict) and token in node:
                node = node[token]
            elif (
                isinstance(node, list)
                and re.fullmatch(r"0|[1-9][0-9]*", token)
                and int(token) < len(node)
            ):
                node = node[int(token)]
            else:
                fail("SCHEMA_REF_MISSING")
        if not isinstance(node, dict | bool):
            fail("SCHEMA_REF_INVALID")
        return path, fragment, node

    def walk(node: Any, current: str, *, root: bool = False) -> Any:
        nonlocal remaining_nodes
        remaining_nodes -= 1
        if remaining_nodes < 0:
            fail("SCHEMA_REF_LIMIT")
        if isinstance(node, bool):
            return node
        if not isinstance(node, dict):
            fail("SCHEMA_REF_INVALID")
        if (
            "$schema" in node
            and node["$schema"] != "https://json-schema.org/draft/2020-12/schema"
        ):
            fail("SCHEMA_REF_FORBIDDEN")
        if (
            "$dynamicRef" in node
            or "$recursiveRef" in node
            or "$anchor" in node
            or "$dynamicAnchor" in node
        ):
            fail("SCHEMA_REF_FORBIDDEN")
        if "$id" in node and not root:
            fail("SCHEMA_REF_FORBIDDEN")
        # Validate even unused definitions, so hidden missing refs/cycles fail closed.
        result = copy.deepcopy(node)
        for key in sorted(_SCHEMA_MAPS & node.keys()):
            result[key] = {
                name: walk(child, current) for name, child in sorted(node[key].items())
            }
        for key in sorted(_SCHEMA_CHILDREN & node.keys()):
            result[key] = walk(node[key], current)
        for key in sorted(_SCHEMA_LISTS & node.keys()):
            result[key] = [walk(child, current) for child in node[key]]
        if "$ref" in node:
            path, fragment, value = target(node["$ref"], current)
            identity = (path, fragment)
            if identity in active:
                fail("SCHEMA_REF_CYCLE")
            active.add(identity)
            resolved = walk(value, path, root=not fragment)
            active.remove(identity)
            result.pop("$ref")
            if result:
                # Keep siblings at the same evaluation scope, especially unevaluated*.
                result.setdefault("allOf", []).insert(0, resolved)
            else:
                result = resolved
        return result

    try:
        resolved = walk(schema, document_path, root=True)
    except RecursionError:
        raise ContractError(
            "SCHEMA_REF_LIMIT", "schema expansion depth exceeded"
        ) from None
    return resolved if isinstance(resolved, dict) else {"allOf": [resolved]}
