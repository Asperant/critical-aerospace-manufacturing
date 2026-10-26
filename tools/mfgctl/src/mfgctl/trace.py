"""``mfgctl trace`` (WP-GOV-002, 03 §18 query surface).

Thin orchestration (DX-INV-03): the trace registry, linter and view generator
live in ``tools/trace`` (``cap_trace``); mfgctl only finds the repository and
runs the same command, so the CLI and CI can never disagree.
"""

from __future__ import annotations

import importlib
import os
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import cast

TRACE_SRC = "tools/trace/src"

Main = Callable[[list[str]], int]


class TraceUnavailableError(RuntimeError):
    """tools/trace is missing from this checkout."""


def load_main(root: Path) -> Main:
    source = root / TRACE_SRC
    if not (source / "cap_trace").is_dir():
        raise TraceUnavailableError(f"{TRACE_SRC}/cap_trace not found under {root}")
    if str(source) not in sys.path:
        sys.path.insert(0, str(source))
    module = importlib.import_module("cap_trace.__main__")
    return cast(Main, module.main)


def run(
    root: Path, args: Sequence[str], loader: Callable[[Path], Main] = load_main
) -> int:
    """Run ``python -m cap_trace ARGS`` in the repository root; return its exit code."""
    main = loader(root)
    previous = Path.cwd()
    os.chdir(root)
    try:
        return main(list(args))
    finally:
        os.chdir(previous)
