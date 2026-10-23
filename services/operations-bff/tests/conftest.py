"""Shared test hygiene: the access logger is process-global, so restore it."""

from __future__ import annotations

import logging
from collections.abc import Iterator

import pytest
from operations_bff.observability import ACCESS_LOGGER


@pytest.fixture(autouse=True)
def restore_access_logger() -> Iterator[None]:
    logger = logging.getLogger(ACCESS_LOGGER)
    handlers, level, propagate = list(logger.handlers), logger.level, logger.propagate
    yield
    logger.handlers[:] = handlers
    logger.setLevel(level)
    logger.propagate = propagate
