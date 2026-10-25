"""Scoped, short-lived read access to one artifact version (WP-OBJ-001, slice 4).

02 access model: Client -> BFF/Artifact Access API -> Authorization ->
Short-Lived Scoped Access -> Object Storage. The browser never holds a storage
credential; it gets a pre-signed URL that allows exactly one GET of exactly one
object for a few minutes. The URL is signed with the *reader* identity, which
can only read artifact buckets, so even a leaked URL cannot write or list.

The issuer checks, at issuance time, that the version is AVAILABLE (per the
registry when one is configured) and that the caller's authorization callback
allows this actor to read it. Capabilities are never stored: they are returned
to the caller and expire on their own. The issuance record carries no URL.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import cast
from urllib.parse import urlencode, urlsplit

from cap_artifacts.errors import StoreError
from cap_artifacts.reference import ArtifactReference
from cap_artifacts.sigv4 import canonical_uri, presign
from cap_artifacts.store import ArtifactStore, StoreConfig

DEFAULT_TTL = timedelta(minutes=5)
MAX_TTL = timedelta(minutes=15)
LOG = logging.getLogger("cap_artifacts.access")


class AccessDenied(StoreError):
    """The actor may not read this artifact, or it is not readable now."""


@dataclass(frozen=True)
class ReadCapability:
    """A bearer capability for one GET of one artifact version."""

    url: str = field(repr=False)
    artifact_id: str
    version: int
    actor: str
    expires_at: datetime

    def __repr__(self) -> str:  # the URL is a bearer token
        return (
            f"ReadCapability(artifact_id={self.artifact_id!r}, version={self.version}, "
            f"actor={self.actor!r}, expires_at={self.expires_at.isoformat()}, url=<redacted>)"
        )


Authorize = Callable[[str, ArtifactReference], bool]


class AccessIssuer:
    """Issues read capabilities; authorization is the caller's policy (BFF)."""

    def __init__(
        self,
        store: ArtifactStore,
        reader: StoreConfig,
        authorize: Authorize,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.store = store
        self.reader = reader
        self.authorize = authorize
        self.clock = clock

    def issue(
        self, ref: ArtifactReference, actor: str, ttl: timedelta = DEFAULT_TTL
    ) -> ReadCapability:
        if not actor.strip():
            raise AccessDenied("an actor identity is required")
        if not timedelta(seconds=1) <= ttl <= MAX_TTL:
            raise AccessDenied(f"capability lifetime must be between 1 s and {MAX_TTL}")
        current = self.store.current(ref)
        if not current.consumable:
            raise AccessDenied(
                f"artifact {current.artifact_id} is {current.lifecycle_status}; only AVAILABLE is readable"
            )
        if not self.authorize(actor, current):
            LOG.info(
                "artifact read capability denied",
                extra={"artifact_id": current.artifact_id, "actor": actor},
            )
            raise AccessDenied(
                f"actor {actor!r} may not read artifact {current.artifact_id}"
            )
        storage = cast(dict[str, str], current.data["storage"])
        path = f"/{storage['bucket']}/{storage['key']}"
        now = self.clock()
        endpoint = urlsplit(self.reader.endpoint)
        query = presign(
            method="GET",
            host=endpoint.netloc,
            path=path,
            credentials=self.reader.credentials,
            region=self.reader.region,
            now=now,
            expires_s=int(ttl.total_seconds()),
        )
        url = f"{endpoint.scheme}://{endpoint.netloc}{canonical_uri(path)}?{urlencode(query)}"
        version = cast(int, current.data["version"])
        expires_at = now + ttl
        LOG.info(
            "artifact read capability issued",
            extra={
                "artifact_id": current.artifact_id,
                "version": version,
                "actor": actor,
                "expires_at": expires_at.isoformat(),
            },
        )
        return ReadCapability(url, current.artifact_id, version, actor, expires_at)
