#!/usr/bin/env python3
"""Repository-supported, exact-origin Tailscale exposure for the demo runtime."""

from __future__ import annotations

import argparse
import json
import os
import ssl
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import (
    HTTPRedirectHandler,
    HTTPSHandler,
    Request,
    build_opener,
    urlopen,
)

CLIENT_ID = "command-center-web"
REALM = "cap-platform"
STATE_NAME = "tailscale-exposure.json"


class ExposureError(RuntimeError):
    pass


def _run(command: list[str], *, input_text: str | None = None) -> str:
    try:
        result = subprocess.run(
            command,
            check=True,
            input=input_text,
            text=True,
            capture_output=True,
        )
    except FileNotFoundError as exc:
        raise ExposureError(f"missing command: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        raise ExposureError(f"{' '.join(command)} failed: {detail}") from exc
    return result.stdout


def _state_path(state_dir: Path) -> Path:
    return state_dir / STATE_NAME


def _read_state(state_dir: Path) -> dict[str, Any]:
    path = _state_path(state_dir)
    if not path.is_file():
        raise ExposureError(f"exposure state is missing: {path}")
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ExposureError(f"exposure state is unreadable: {path}") from exc
    if not isinstance(value, dict):
        raise ExposureError("exposure state must be an object")
    required = ("hostname", "ui_url", "keycloak_url", "ui_redirect_uri", "keycloak_issuer")
    if any(not isinstance(value.get(key), str) or not value[key] for key in required):
        raise ExposureError("exposure state is incomplete")
    return value


def _write_state(state_dir: Path, value: dict[str, Any]) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    path = _state_path(state_dir)
    fd, temporary = tempfile.mkstemp(prefix=f"{path.name}.", dir=state_dir)
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _tailscale_identity() -> tuple[str, dict[str, Any]]:
    try:
        document = json.loads(_run(["tailscale", "status", "--json"]))
    except json.JSONDecodeError as exc:
        raise ExposureError("tailscale status returned invalid JSON") from exc
    self_node = document.get("Self") if isinstance(document, dict) else None
    hostname = self_node.get("DNSName") if isinstance(self_node, dict) else None
    if not isinstance(hostname, str) or not hostname.strip():
        raise ExposureError("tailscale DNS name is unavailable")
    return hostname.rstrip("."), document


def _serve_config() -> dict[str, Any]:
    try:
        document = json.loads(_run(["tailscale", "serve", "status", "--json"]))
    except json.JSONDecodeError as exc:
        raise ExposureError("tailscale serve status returned invalid JSON") from exc
    if not isinstance(document, dict):
        raise ExposureError("tailscale serve status was not an object")
    return document


def _proxy_for(config: dict[str, Any], key: str) -> str | None:
    web = config.get("Web")
    if not isinstance(web, dict):
        return None
    entry = web.get(key)
    if not isinstance(entry, dict):
        return None
    handlers = entry.get("Handlers")
    if not isinstance(handlers, dict):
        return None
    root = handlers.get("/")
    return root.get("Proxy") if isinstance(root, dict) else None


def _ensure_serve(hostname: str, ui_port: int, keycloak_port: int, local_keycloak_port: int) -> None:
    config = _serve_config()
    ui_key = f"{hostname}:443"
    keycloak_key = f"{hostname}:{keycloak_port}"
    if _proxy_for(config, ui_key) != f"http://127.0.0.1:{ui_port}":
        _run(["tailscale", "serve", "--bg", f"http://127.0.0.1:{ui_port}"])
    config = _serve_config()
    if _proxy_for(config, keycloak_key) != f"http://127.0.0.1:{local_keycloak_port}":
        _run(
            [
                "tailscale",
                "serve",
                "--bg",
                "--https",
                str(keycloak_port),
                f"http://127.0.0.1:{local_keycloak_port}",
            ]
        )
    final = _serve_config()
    if _proxy_for(final, ui_key) != f"http://127.0.0.1:{ui_port}":
        raise ExposureError("Tailscale UI Serve route did not converge")
    if _proxy_for(final, keycloak_key) != f"http://127.0.0.1:{local_keycloak_port}":
        raise ExposureError("Tailscale Keycloak Serve route did not converge")


def _credentials(state_dir: Path) -> dict[str, str]:
    path = state_dir / "credentials.env"
    if not path.is_file():
        raise ExposureError(f"demo credentials are missing: {path}")
    values: dict[str, str] = {}
    for line in path.read_text().splitlines():
        name, separator, value = line.partition("=")
        if separator and name and value:
            values[name] = value
    password = values.get("CAP_KEYCLOAK_ADMIN_PASSWORD")
    if not password:
        raise ExposureError("Keycloak admin password is missing")
    return values


def _request(
    url: str,
    *,
    method: str = "GET",
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
    insecure_tls: bool = False,
) -> tuple[int, bytes]:
    request = Request(url, data=body, headers=headers or {}, method=method)
    context = ssl._create_unverified_context() if insecure_tls else None
    try:
        with urlopen(request, timeout=8, context=context) as response:  # noqa: S310 - exact configured demo URLs
            return response.status, response.read()
    except HTTPError as exc:
        return exc.code, exc.read()
    except URLError as exc:
        raise ExposureError(f"URL unavailable: {url}") from exc


def _admin_token(state_dir: Path, keycloak_local_url: str) -> str:
    password = _credentials(state_dir)["CAP_KEYCLOAK_ADMIN_PASSWORD"]
    body = urlencode(
        {
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": "cap-admin",
            "password": password,
        }
    ).encode()
    status, payload = _request(
        f"{keycloak_local_url}/realms/master/protocol/openid-connect/token",
        method="POST",
        body=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if status != 200:
        raise ExposureError("Keycloak admin token request failed")
    document = json.loads(payload)
    token = document.get("access_token") if isinstance(document, dict) else None
    if not isinstance(token, str) or not token:
        raise ExposureError("Keycloak admin token was not returned")
    return token


def _client(state_dir: Path, keycloak_local_url: str) -> tuple[str, dict[str, Any]]:
    token = _admin_token(state_dir, keycloak_local_url)
    status, payload = _request(
        f"{keycloak_local_url}/admin/realms/{REALM}/clients?clientId={CLIENT_ID}",
        headers={"Authorization": f"Bearer {token}"},
    )
    if status != 200:
        raise ExposureError("Keycloak client lookup failed")
    document = json.loads(payload)
    if not isinstance(document, list) or len(document) != 1 or not isinstance(document[0], dict):
        raise ExposureError("Keycloak demo client lookup was not unique")
    internal_id = document[0].get("id")
    if not isinstance(internal_id, str) or not internal_id:
        raise ExposureError("Keycloak demo client has no internal id")
    return token, document[0]


def _reconcile(state_dir: Path, ui_port: int, keycloak_port: int, *, check_only: bool) -> None:
    state = _read_state(state_dir)
    local_ui = f"http://localhost:{ui_port}"
    local_keycloak = f"http://localhost:{keycloak_port}"
    redirects = [f"{local_ui}/v1/session/callback", state["ui_redirect_uri"]]
    origins = [local_ui, state["ui_url"]]
    token, client = _client(state_dir, local_keycloak)
    actual_redirects = client.get("redirectUris")
    actual_origins = client.get("webOrigins")
    if not isinstance(actual_redirects, list) or not isinstance(actual_origins, list):
        raise ExposureError("Keycloak demo client has invalid origin fields")
    missing_redirects = [item for item in redirects if item not in actual_redirects]
    missing_origins = [item for item in origins if item not in actual_origins]
    if check_only:
        if missing_redirects or missing_origins:
            raise ExposureError("Keycloak demo client is missing exact exposure origins")
        return
    client["redirectUris"] = list(dict.fromkeys([*actual_redirects, *redirects]))
    client["webOrigins"] = list(dict.fromkeys([*actual_origins, *origins]))
    status, _ = _request(
        f"{local_keycloak}/admin/realms/{REALM}/clients/{client['id']}",
        method="PUT",
        body=json.dumps(client).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    if status not in (200, 204):
        raise ExposureError("Keycloak demo client reconciliation failed")


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


def _login_redirect(url: str, *, insecure_tls: bool) -> tuple[str, dict[str, list[str]]]:
    handlers: list[Any] = [_NoRedirect()]
    if insecure_tls:
        handlers.append(HTTPSHandler(context=ssl._create_unverified_context()))
    opener = build_opener(*handlers)
    request = Request(url)
    try:
        with opener.open(request, timeout=8) as response:
            status = response.status
            location = response.headers.get("Location", "")
    except HTTPError as exc:
        status = exc.code
        location = exc.headers.get("Location", "")
    except URLError as exc:
        raise ExposureError(f"login endpoint unavailable: {url}") from exc
    if status != 302 or not location:
        raise ExposureError(f"login endpoint did not return a redirect: {url}")
    parsed = urlparse(location)
    from urllib.parse import parse_qs

    return location, parse_qs(parsed.query)


def _check_local(ui_port: int, keycloak_port: int) -> None:
    location, query = _login_redirect(
        f"http://localhost:{ui_port}/v1/session/login", insecure_tls=False
    )
    expected_redirect = f"http://localhost:{ui_port}/v1/session/callback"
    if query.get("redirect_uri", [""])[0] != expected_redirect:
        raise ExposureError("localhost login redirect is not localhost-bound")
    if f"http://localhost:{keycloak_port}/" not in location:
        raise ExposureError("localhost login did not use the local Keycloak origin")


def _check(state_dir: Path, ui_port: int, keycloak_port: int) -> None:
    state = _read_state(state_dir)
    ui_url = state["ui_url"].rstrip("/")
    keycloak_url = state["keycloak_url"].rstrip("/")
    for url in (f"http://localhost:{ui_port}/", f"{ui_url}/"):
        status, _ = _request(url, insecure_tls=url.startswith("https://"))
        if status != 200:
            raise ExposureError(f"UI did not return HTTP 200: {url}")
    status, _ = _request(
        f"{keycloak_url}/realms/{REALM}", insecure_tls=keycloak_url.startswith("https://")
    )
    if status != 200:
        raise ExposureError("Tailscale Keycloak realm did not return HTTP 200")
    local_location, local_query = _login_redirect(
        f"http://localhost:{ui_port}/v1/session/login", insecure_tls=False
    )
    public_location, public_query = _login_redirect(
        f"{ui_url}/v1/session/login", insecure_tls=True
    )
    local_redirect = local_query.get("redirect_uri", [""])[0]
    public_redirect = public_query.get("redirect_uri", [""])[0]
    if local_redirect != f"http://localhost:{ui_port}/v1/session/callback":
        raise ExposureError("localhost login redirect is not localhost-bound")
    if public_redirect != state["ui_redirect_uri"]:
        raise ExposureError("Tailscale login redirect is not Tailscale-bound")
    if (
        f"localhost:{keycloak_port}" not in local_location
        or state["keycloak_url"].split("://", 1)[1] not in public_location
    ):
        raise ExposureError("login endpoint did not use the configured Keycloak origin")
    _reconcile(state_dir, ui_port, keycloak_port, check_only=True)


def _env(state_dir: Path, ui_port: int, keycloak_port: int) -> None:
    local_keycloak = f"http://localhost:{keycloak_port}"
    values = {
        "CAP_DEMO_OIDC_DYNAMIC_REDIRECT": "1",
        "CAP_DEMO_OIDC_BROWSER_ISSUER": f"{local_keycloak}/realms/{REALM}",
        "CAP_DEMO_OIDC_REDIRECT_URIS": "",
        "CAP_DEMO_OIDC_BROWSER_ISSUERS": "",
    }
    path = _state_path(state_dir)
    if path.is_file():
        state = _read_state(state_dir)
        values.update(
            {
                "CAP_DEMO_PUBLIC_UI_URL": state["ui_url"].rstrip("/"),
                "CAP_DEMO_PUBLIC_KEYCLOAK_URL": state["keycloak_url"].rstrip("/"),
                "CAP_DEMO_OIDC_REDIRECT_URIS": state["ui_redirect_uri"],
                "CAP_DEMO_OIDC_BROWSER_ISSUERS": state["keycloak_issuer"],
                "CAP_DEMO_KEYCLOAK_PROXY_HEADERS": "xforwarded",
            }
        )
    for name, value in values.items():
        print(f"{name}={value}")


def configure(args: argparse.Namespace) -> None:
    hostname, _ = _tailscale_identity()
    _ensure_serve(
        hostname,
        args.ui_port,
        args.tailscale_keycloak_port,
        args.keycloak_port,
    )
    state = {
        "hostname": hostname,
        "ui_url": f"https://{hostname}",
        "keycloak_url": f"https://{hostname}:{args.tailscale_keycloak_port}",
        "ui_redirect_uri": f"https://{hostname}/v1/session/callback",
        "keycloak_issuer": f"https://{hostname}:{args.tailscale_keycloak_port}/realms/{REALM}",
        "localhost_ui_url": f"http://localhost:{args.ui_port}",
        "localhost_keycloak_url": f"http://localhost:{args.keycloak_port}",
    }
    _write_state(args.state_dir, state)
    print(f"Tailscale UI: {state['ui_url']}")
    print(f"Tailscale Keycloak: {state['keycloak_url']}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=("configure", "restore", "reconcile", "check", "check-local", "env"),
    )
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--ui-port", type=int, required=True)
    parser.add_argument("--keycloak-port", type=int, required=True)
    parser.add_argument("--tailscale-keycloak-port", type=int, default=9443)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    try:
        if args.command in ("configure", "restore"):
            configure(args)
        elif args.command == "reconcile":
            _reconcile(args.state_dir, args.ui_port, args.keycloak_port, check_only=args.check_only)
            print("Keycloak demo client exact origins reconciled")
        elif args.command == "check":
            _check(args.state_dir, args.ui_port, args.keycloak_port)
            print("Tailscale UI, Keycloak and exact login redirects verified")
        elif args.command == "check-local":
            _check_local(args.ui_port, args.keycloak_port)
            print("localhost UI and exact login redirect verified")
        else:
            _env(args.state_dir, args.ui_port, args.keycloak_port)
        return 0
    except (ExposureError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
