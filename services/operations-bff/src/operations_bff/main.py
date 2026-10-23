"""Application entrypoint: ``create_app()`` is an ASGI factory.

Run it with any ASGI server in factory mode, for example
``<server> operations_bff.main:create_app --factory``.
"""

from __future__ import annotations

import os

from fastapi import FastAPI

from .composition import RuntimeSettings, build_app
from .observability import configure_access_log


def create_app() -> FastAPI:
    """Read the process environment and fail fast if configuration is unusable."""
    configure_access_log()
    return build_app(RuntimeSettings.from_environ(os.environ))
