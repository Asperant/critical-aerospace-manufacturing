"""Credential inheritance and non-overwrite boundaries for shared-GUI helpers."""
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('developer_workspace', Path(__file__).resolve().parents[3] / 'tools/operations/developer_workspace.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def test_isolated_environment_removes_reference_credentials(tmp_path):
    source = {'GH_TOKEN': 'secret', 'GITHUB_TOKEN': 'secret', 'OPENAI_API_KEY': 'secret',
              'PLANE_API_KEY': 'secret', 'SSH_AUTH_SOCK': '/agent', 'GIT_CONFIG_COUNT': '1',
              'GIT_CONFIG_KEY_0': 'credential.helper', 'GIT_CONFIG_VALUE_0': 'shared', 'PATH': '/bin'}
    env = helper.environment(tmp_path, source)
    assert 'secret' not in env.values()
    assert 'SSH_AUTH_SOCK' not in env and 'GIT_CONFIG_COUNT' not in env
    assert env['GH_CONFIG_DIR'] == str(tmp_path / 'gh')
    assert env['CODEX_HOME'] == str(tmp_path / 'codex')
    assert env['GIT_CONFIG_GLOBAL'] == '/dev/null'
    assert source['GH_TOKEN'] == 'secret'


def test_existing_workspace_never_overwritten(tmp_path):
    target = tmp_path / 'workspaces/selman/project'
    target.mkdir(parents=True)
    with pytest.raises(ValueError, match='never overwrite'):
        helper.prepare('selman', tmp_path, tmp_path / 'missing-source')
    assert target.is_dir()
