"""Explicit API v1 discovery. This adapter has no mutation methods."""
from dataclasses import dataclass, field
from pathlib import Path
import os
import re
import shlex
import math
from urllib.parse import urlsplit
from uuid import UUID

from .plane_transport import PlaneError, PlaneStream


@dataclass(frozen=True)
class PlaneConfig:
    base_url: str
    api_key: str = field(repr=False)
    workspace_slug: str
    project_id: str
    api_version: str = "v1"
    request_interval_seconds: float = 1.25

    def __post_init__(self):
        parts = urlsplit(self.base_url)
        if (parts.scheme not in {"http", "https"} or not parts.netloc or parts.username
                or parts.password or parts.query or parts.fragment or parts.path not in {"", "/"}):
            raise PlaneError("Invalid PLANE_BASE_URL; use an origin without credentials or API path")
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", self.workspace_slug):
            raise PlaneError("Invalid PLANE_WORKSPACE_SLUG")
        try:
            UUID(self.project_id)
        except (ValueError, TypeError):
            raise PlaneError("Invalid PLANE_PROJECT_ID") from None
        if not self.api_key or any(c in self.api_key for c in "\r\n"):
            raise PlaneError("Invalid PLANE_API_KEY")
        if self.api_version != "v1":
            raise PlaneError("This installation supports explicit API v1 only; no version fallback")
        if not math.isfinite(self.request_interval_seconds) or self.request_interval_seconds < 1.25:
            raise PlaneError("PLANE_REQUEST_INTERVAL_SECONDS must be finite and at least 1.25")


def load_config(path: Path | None = None, environ=None) -> PlaneConfig:
    values = {}
    required = {"PLANE_BASE_URL", "PLANE_API_KEY", "PLANE_WORKSPACE_SLUG", "PLANE_PROJECT_ID"}
    keys = required | {"PLANE_REQUEST_INTERVAL_SECONDS"}
    if path is not None and path.is_file():
        try:
            for line in path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                key, sep, raw = line.removeprefix("export ").partition("=")
                key = key.strip()
                if key not in keys:
                    continue
                parts = shlex.split(raw, comments=True)
                if not sep or len(parts) != 1 or key in values:
                    raise PlaneError("Invalid or duplicate local Plane configuration entry")
                values[key] = parts[0]  # Literal data; never source/eval or expand shell syntax.
        except (OSError, UnicodeError, ValueError):
            raise PlaneError("Cannot parse local Plane configuration (details redacted)") from None
    env = os.environ if environ is None else environ
    values.update({k: env[k] for k in keys if k in env})
    missing = sorted(k for k in required if not values.get(k))
    if missing:
        raise PlaneError("PLANE_READ_CREDENTIALS_REQUIRED: missing " + ", ".join(missing))
    try:
        interval = float(values.get("PLANE_REQUEST_INTERVAL_SECONDS", "1.25"))
    except ValueError:
        raise PlaneError("Invalid PLANE_REQUEST_INTERVAL_SECONDS") from None
    return PlaneConfig(values["PLANE_BASE_URL"], values["PLANE_API_KEY"],
                       values["PLANE_WORKSPACE_SLUG"], values["PLANE_PROJECT_ID"], request_interval_seconds=interval)


class PlaneReader:
    def __init__(self, config: PlaneConfig, transport=None):
        self.config = config
        self.stream = PlaneStream(config, transport)
        self.reads = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.stream.close()

    def _get(self, path, params=None, optional=False):
        # Paths are internal fixed v1 routes. Pagination accepts only opaque cursor data.
        if path.startswith("/") or ":" in path or ".." in path:
            raise PlaneError("Unsafe Plane resource path")
        response = self.stream.request("GET", path, params=params)
        self.reads.append({"method": "GET", "path": "/api/v1/" + path, "status": response.status_code})
        if optional and response.status_code in {401, 403, 404, 405}:
            return None
        if response.status_code != 200:
            raise PlaneError(f"Plane GET failed: HTTP {response.status_code} (body redacted)")
        try:
            return response.json()
        except ValueError:
            raise PlaneError("Invalid Plane JSON (body redacted)") from None

    def _list(self, path, optional=False):
        rows, cursors = [], set()
        params = None
        for _ in range(1000):
            data = self._get(path, params, optional)
            if data is None:
                return None
            if isinstance(data, list):
                page, more = data, False
            elif isinstance(data, dict) and isinstance(data.get("results"), list):
                page, more = data["results"], data.get("next_page_results", False)
                if not isinstance(more, bool):
                    raise PlaneError("Invalid Plane pagination flag")
            else:
                raise PlaneError("Unsupported Plane list response shape")
            if not all(isinstance(r, dict) and isinstance(r.get("id"), str) for r in page):
                raise PlaneError("Invalid Plane entity records")
            rows.extend(page)
            if not more:
                ids = [r["id"] for r in rows]
                if len(ids) != len(set(ids)):
                    raise PlaneError("Duplicate Plane entity IDs across pages")
                if isinstance(data, dict) and data.get("total_count") is not None and data["total_count"] != len(rows):
                    raise PlaneError("Plane pagination total does not match observed records")
                return sorted(rows, key=lambda r: r["id"])
            cursor = data.get("next_cursor")
            if not isinstance(cursor, str) or not cursor or cursor in cursors:
                raise PlaneError("Missing or repeated Plane pagination cursor")
            cursors.add(cursor)
            params = {"cursor": cursor}
        raise PlaneError("Plane pagination exceeded safety limit; incomplete audit")

    def audit(self):
        c = self.config
        scope = f"workspaces/{c.workspace_slug}/"
        project_path = scope + f"projects/{c.project_id}/"
        user = self._get("users/me/")
        project = self._get(project_path)
        if not isinstance(user, dict) or not user.get("id"):
            raise PlaneError("Authenticated user identity unavailable")
        if (not isinstance(project, dict) or project.get("id") != c.project_id
                or project.get("name") != "Graduation Project" or project.get("identifier") != "CAP"
                or not project.get("workspace")):
            raise PlaneError("Configured project identity mismatch; expected Graduation Project / CAP")
        workspace = self._get(scope, optional=True)
        scoped_projects = self._list(scope + "projects/")
        if not any(p.get("id") == c.project_id and p.get("workspace") == project["workspace"] for p in scoped_projects):
            raise PlaneError("Workspace-scoped project identity mismatch")
        if workspace is not None and (workspace.get("id") != project["workspace"] or workspace.get("slug") != c.workspace_slug):
            raise PlaneError("Workspace identity mismatch")
        resources = {name: self._list(project_path + route + "/") for name, route in
                     [("states", "states"), ("labels", "labels"), ("modules", "modules"),
                      ("cycles", "cycles"), ("work_items", "issues")]}
        resources["project_members"] = self._list(project_path + "members/", optional=True)
        resources["workspace_members"] = self._list(scope + "members/", optional=True)
        # An audit is a reproducible sanitized view, not a local execution database.
        allowed = {"id", "name", "identifier", "workspace", "project", "group", "slug", "default",
                   "external_id", "external_source", "description", "description_html", "state",
                   "assignees", "labels", "cycle", "module", "modules", "first_name", "last_name",
                   "display_name", "start_date", "end_date", "parent"}
        cleaned = {k: None if rows is None else [{f: v for f, v in r.items() if f in allowed} for r in rows]
                   for k, rows in resources.items()}
        return {"schema_version": "plane-v1-audit-v1", "api_version": "v1", "mutation_enabled": False,
                "authenticated_user": {k: user[k] for k in ["id", "first_name", "last_name", "display_name"] if k in user},
                "workspace": {"id": project["workspace"], "slug": c.workspace_slug,
                              "verification": "DIRECT_AND_PROJECT_SCOPE" if workspace else "PROJECT_SCOPE_ONLY",
                              "direct_endpoint_available": workspace is not None},
                "project": {k: project[k] for k in ["id", "name", "identifier", "workspace"]},
                **cleaned, "reads": self.reads.copy()}
