"""Errors shared by the store and the registry (WP-OBJ-001)."""

from __future__ import annotations


class StoreError(RuntimeError):
    """The object store or registry answered unexpectedly or is unreachable."""


class MissingObjectError(StoreError):
    """A reference points at bytes (or a registry row) that do not exist."""


class OverwriteError(StoreError):
    """The artifact version already exists; new bytes need a new version."""
