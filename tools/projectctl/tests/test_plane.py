import json

import httpx
import pytest
from typer.testing import CliRunner

from projectctl.cli import app
from projectctl.plane import PlaneConfig, PlaneError, PlaneReader, load_config

PROJECT = "beb6dbea-4931-4ce9-b761-a4957c4b33be"
SECRET = "test-secret-do-not-print"


def config():
    return PlaneConfig("http://plane.test", SECRET, "workspace", PROJECT)


def response(path):
    if path.endswith("users/me/"):
        return {"id": "user", "first_name": "asrın", "last_name": "dündar", "email": "private@example.test"}
    project = {"id": PROJECT, "name": "Graduation Project", "identifier": "CAP", "workspace": "workspace-id"}
    if path.endswith(f"projects/{PROJECT}/"):
        return project
    if path.endswith("workspaces/workspace/"):
        return {"id": "workspace-id", "slug": "workspace"}
    if path.endswith("projects/"):
        return [project]
    return []


def test_explicit_v1_get_only_discovery_and_redacted_members():
    calls = []
    def handler(request):
        calls.append(request)
        assert request.method == "GET"
        assert request.url.path.startswith("/api/v1/")
        assert request.headers["X-API-Key"] == SECRET
        payload = response(request.url.path)
        if request.url.path.endswith("members/"):
            payload = [{"id": "user", "email": "private@example.test", "first_name": "asrın", "last_name": "dündar"}]
        return httpx.Response(200, json=payload)
    with PlaneReader(config(), httpx.MockTransport(handler)) as reader:
        audit = reader.audit()
    assert len(calls) == 11
    assert audit["api_version"] == "v1" and audit["mutation_enabled"] is False
    assert SECRET not in json.dumps(audit)
    assert "private@example.test" not in json.dumps(audit)
    assert not any(hasattr(PlaneReader, name) for name in ["post", "put", "patch", "delete", "sync"])


def test_config_literal_loading_and_environment_precedence(tmp_path):
    path = tmp_path / "plane.env"
    path.write_text(f'PLANE_BASE_URL=http://plane.test\nPLANE_API_KEY="literal$(not-executed)`no`"\nPLANE_WORKSPACE_SLUG=workspace\nPLANE_PROJECT_ID={PROJECT}\n')
    loaded = load_config(path, {})
    assert loaded.api_key == "literal$(not-executed)`no`"
    assert loaded.api_key not in repr(loaded)
    assert load_config(path, {"PLANE_API_KEY": SECRET}).api_key == SECRET
    with pytest.raises(PlaneError, match="missing"):
        load_config(None, {})
    path.write_text('PLANE_API_KEY="unclosed')
    with pytest.raises(PlaneError) as error:
        load_config(path, {})
    assert "unclosed" not in str(error.value)


@pytest.mark.parametrize("kwargs", [{"api_version": "v2"}, {"base_url": "http://name:secret@plane.test"},
                                   {"workspace_slug": "../other"}, {"project_id": "wrong"}])
def test_config_rejects_unsafe_or_unsupported_configuration(kwargs):
    values = dict(base_url="http://plane.test", api_key=SECRET, workspace_slug="workspace", project_id=PROJECT)
    values.update(kwargs)
    with pytest.raises(PlaneError):
        PlaneConfig(**values)


def test_pagination_follows_only_cursor_with_fixed_v1_route():
    calls = []
    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(200, json={"results": [{"id": "a"}], "next_page_results": True,
                                           "next_cursor": "http://other.test/api/v2/leak", "total_count": 2})
        assert request.url.host == "plane.test"
        assert request.url.params["cursor"] == "http://other.test/api/v2/leak"
        return httpx.Response(200, json={"results": [{"id": "b"}], "next_page_results": False, "total_count": 2})
    with PlaneReader(config(), httpx.MockTransport(handler)) as reader:
        assert reader._list("list/") == [{"id": "a"}, {"id": "b"}]


@pytest.mark.parametrize("payload", [
    {"results": [{"id": "a"}], "next_page_results": True, "next_cursor": "repeat"},
    {"results": [{"id": "a"}], "next_page_results": False, "total_count": 2},
    {"results": [{"id": "a"}, {"id": "a"}]}, {"results": "bad"},
])
def test_incomplete_or_duplicate_pagination_fails(payload):
    with PlaneReader(config(), httpx.MockTransport(lambda r: httpx.Response(200, json=payload))) as reader:
        with pytest.raises(PlaneError):
            reader._list("list/")


@pytest.mark.parametrize("status", [301, 401, 404, 500])
def test_errors_are_redacted_and_never_fall_back_or_redirect(status):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(status, text=SECRET, headers={"Location": "http://other.test/"})
    with PlaneReader(config(), httpx.MockTransport(handler)) as reader:
        with pytest.raises(PlaneError) as error:
            reader.audit()
    assert len(calls) == 1 and SECRET not in str(error.value)


def test_workspace_access_limitation_and_identity_mismatch():
    def handler(request):
        if request.url.path.endswith("workspaces/workspace/"):
            return httpx.Response(401)
        return httpx.Response(200, json=response(request.url.path))
    with PlaneReader(config(), httpx.MockTransport(handler)) as reader:
        assert reader.audit()["workspace"]["verification"] == "PROJECT_SCOPE_ONLY"
    def wrong(request):
        data = response(request.url.path)
        if request.url.path.endswith(f"projects/{PROJECT}/"):
            data["identifier"] = "WRONG"
        return httpx.Response(200, json=data)
    with PlaneReader(config(), httpx.MockTransport(wrong)) as reader:
        with pytest.raises(PlaneError, match="identity mismatch"):
            reader.audit()


def test_cli_live_audit_is_explicit_and_safe_without_credentials(root, monkeypatch):
    import projectctl.plane as plane
    monkeypatch.setattr(plane, "load_config", lambda *args: (_ for _ in ()).throw(PlaneError("PLANE_READ_CREDENTIALS_REQUIRED")))
    result = CliRunner().invoke(app, ["plane-audit", "--root", str(root)])
    assert result.exit_code == 2 and "PLANE_READ_CREDENTIALS_REQUIRED" in result.output


@pytest.mark.parametrize("null_page", [1, 2])
def test_required_list_rejects_null_on_any_page(null_page):
    calls = []

    def handler(request):
        calls.append(request)
        assert request.method == "GET"
        if len(calls) == null_page:
            return httpx.Response(200, content=b"null")
        return httpx.Response(200, json={
            "results": [{"id": "a"}], "next_page_results": True, "next_cursor": "next",
        })

    with PlaneReader(config(), httpx.MockTransport(handler)) as reader, pytest.raises(PlaneError, match="must not be null"):
        reader._list("list/")
    assert len(calls) == null_page


def test_audit_rejects_null_required_project_list():
    def handler(request):
        if request.url.path.endswith("projects/"):
            return httpx.Response(200, content=b"null")
        return httpx.Response(200, json=response(request.url.path))

    with PlaneReader(config(), httpx.MockTransport(handler)) as reader, pytest.raises(PlaneError, match="must not be null"):
        reader.audit()


@pytest.mark.parametrize("status", [401, 403, 404, 405])
def test_optional_list_denial_remains_unavailable(status):
    transport = httpx.MockTransport(lambda request: httpx.Response(status))
    with PlaneReader(config(), transport) as reader:
        assert reader._list("list/", optional=True) is None


@pytest.mark.parametrize("optional", [False, True])
def test_empty_list_is_valid(optional):
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=[]))
    with PlaneReader(config(), transport) as reader:
        assert reader._list("list/", optional=optional) == []
