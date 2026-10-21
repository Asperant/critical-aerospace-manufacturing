"""TEST-GOV-001/002/003: WP-GOV-001 slices of the planned GOV families."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import socket
import subprocess

from jsonschema import Draft202012Validator
import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from projectctl.cli import app
from projectctl.requirement_catalog import (
    CATALOG, COUNTS, SCHEMA, MASTER, RTM, CatalogFile, catalog_schema, check_history,
    coverage_counts, decode, encode, from_sources, git_baseline, lint_catalog, read_catalog, rtm_counts,
)


@pytest.fixture(scope="module")
def catalog():
    return read_catalog(Path(__file__).resolve().parents[3] / CATALOG)


@pytest.fixture
def sandbox(tmp_path, root):
    for name in [MASTER, RTM, CATALOG, SCHEMA, COUNTS]:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / name, target)
    return tmp_path


def test_gov_001_real_catalog_and_json_schema(root, catalog):
    """TEST-GOV-CATALOG: all 306 actual definitions, not synthetic acceptance data."""
    schema = catalog_schema()
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(catalog.model_dump())
    assert catalog == from_sources(root)
    counts = coverage_counts(catalog)
    assert counts['by_kind'] == {"FR": 186, "NFR": 120}
    assert counts['fr_scope'] == {"F0": 17, "F1": 159, "R1": 10}
    assert counts['nfr_quality'] == {"H0": 52, "A1": 41, "S2": 23, "C3": 4}
    assert counts['by_owner'] == {"Asrın Dündar": 124, "Selman Özdemir": 19, "Batuhan Kaya": 57, "Yavuz Gümüş": 106}
    assert counts['missing_revision'] == counts['missing_status'] == 306
    assert all("statement" not in r for r in catalog.model_dump()['requirements'])
    assert lint_catalog(root)['result'] == "PASS"


@pytest.mark.parametrize("field,value", [
    ("id", "FR-GOV-001-extra"), ("id", "NFR-GOV-001"),
    ("primary_owner", None), ("primary_owner", []),
    ("primary_owner", ["Asrın Dündar", "Yavuz Gümüş"]), ("primary_owner", "Team"),
    ("scope_class", "H0"), ("scope_class", "R2"), ("scope_class", None),
    ("quality_class", "H0"), ("statement", "another SHALL source"),
    ("status", "DONE"), ("revision", 1),
])
def test_gov_001_invalid_fr_schema(catalog, field, value):
    data = catalog.model_dump()
    data['requirements'][0][field] = value
    assert list(Draft202012Validator(catalog_schema()).iter_errors(data))
    with pytest.raises(ValidationError):
        CatalogFile.model_validate(data)


@pytest.mark.parametrize("field,value", [("quality_class", None), ("quality_class", "F1"), ("scope_class", "F1")])
def test_gov_003_nfr_class_inspection(catalog, field, value):
    """INSP-GOV-NFR scope: class/owner/identity only; no measurement completion claim."""
    data = catalog.model_dump()
    next(r for r in data['requirements'] if r['kind'] == 'NFR')[field] = value
    with pytest.raises(ValidationError):
        CatalogFile.model_validate(data)


def test_gov_001_duplicate_identity_and_missing_fields(catalog):
    data = catalog.model_dump()
    data['requirements'].insert(0, deepcopy(data['requirements'][0]))
    with pytest.raises(ValidationError, match="Duplicate ID"):
        CatalogFile.model_validate(data)
    data = catalog.model_dump()
    del data['requirements'][0]['source']
    with pytest.raises(ValidationError):
        CatalogFile.model_validate(data)
    with pytest.raises(ValueError, match="Duplicate JSON key"):
        decode('{"requirements": [], "requirements": []}')


@pytest.mark.parametrize("path,old,new,code", [
    (CATALOG, 'Asrın Dündar', 'Yavuz Gümüş', 'SOURCE_MISMATCH'),
    (CATALOG, '"revision": null', '"revision": "invented"', 'SOURCE_MISMATCH'),
    (CATALOG, '"status": null', '"status": "VERIFIED"', 'SOURCE_MISMATCH'),
    (CATALOG, '"line_start": 169984', '"line_start": 1', 'SOURCE_MISMATCH'),
    (SCHEMA, '"additionalProperties": false', '"additionalProperties": true', 'GENERATED_DRIFT'),
    (COUNTS, '"total": 306', '"total": 305', 'GENERATED_DRIFT'),
    (RTM, '| 306 / 306 |', '| 305 / 306 |', 'RTM_COUNTS_DRIFT'),
    (MASTER, 'globally unique stable RequirementID', 'globally unique permanent RequirementID', 'SOURCE_MISMATCH'),
])
def test_gov_001_source_and_generated_drift(sandbox, path, old, new, code):
    target = sandbox / path
    original = target.read_text()
    assert old in original
    target.write_text(original.replace(old, new, 1))
    report = lint_catalog(sandbox)
    assert report['result'] == 'FAIL'
    assert any(issue.startswith(code) for issue in report['issues'])


def test_gov_001_missing_and_malformed_input_fail_closed(sandbox):
    runner = CliRunner()
    (sandbox / CATALOG).write_text('{broken')
    result = runner.invoke(app, ['catalog-lint', '--root', str(sandbox)])
    assert result.exit_code == 2
    assert 'CATALOG_INPUT_ERROR' in result.output
    (sandbox / CATALOG).unlink()
    assert runner.invoke(app, ['catalog-lint', '--root', str(sandbox)]).exit_code == 2


def test_gov_001_omitted_canonical_record(sandbox, catalog):
    data = catalog.model_dump()
    data['requirements'].pop()
    (sandbox / CATALOG).write_text(encode(data))
    assert 'SOURCE_MISMATCH' in '\n'.join(lint_catalog(sandbox)['issues'])


@pytest.mark.parametrize('remaining', [0, 186])
def test_gov_001_missing_entire_kind_reports_failure(sandbox, catalog, remaining):
    data = catalog.model_dump()
    data['requirements'] = data['requirements'][:remaining]
    (sandbox / CATALOG).write_text(encode(data))
    result = CliRunner().invoke(app, ['catalog-lint', '--root', str(sandbox)])
    assert result.exit_code == 1
    assert 'SOURCE_MISMATCH' in result.output


def test_gov_002_retirement_history(catalog):
    """TEST-GOV-TRACELINT slice: removal, tombstone erasure, replay/resurrection."""
    removed = catalog.model_dump()
    old = removed['requirements'].pop(0)
    without = CatalogFile.model_validate(removed)
    assert check_history(without, catalog) == [f"ID_REMOVED_WITHOUT_RETIREMENT: {old['id']}"]
    tombstone = dict(id=old['id'], status='RETIRED', decision_ref='09_change/CHG-999.yaml')
    removed['retired_ids'] = [tombstone]
    retired = CatalogFile.model_validate(removed)
    assert not check_history(retired, catalog)
    assert any('RETIREMENT_HISTORY' in i for i in check_history(without, retired))
    assert any('RETIRED_ID_REUSE' in i for i in check_history(catalog, retired))
    replay = catalog.model_dump()
    replay['retired_ids'] = [tombstone]
    with pytest.raises(ValidationError, match='Retired-ID reuse'):
        CatalogFile.model_validate(replay)
    changed = deepcopy(removed)
    changed['retired_ids'][0]['decision_ref'] = '09_change/CHG-998.yaml'
    assert any('RETIREMENT_HISTORY' in i for i in check_history(CatalogFile.model_validate(changed), retired))


def test_gov_002_git_baseline_and_invalid_baseline(sandbox):
    def git(*args):
        return subprocess.run(['git', *args], cwd=sandbox, check=True, capture_output=True, text=True).stdout.strip()
    git('init', '-q')
    git('add', CATALOG)
    git('-c', 'user.name=Catalog test', '-c', 'user.email=catalog@example.invalid', 'commit', '-qm', 'Catalog baseline')
    expected = read_catalog(sandbox / CATALOG)
    assert git_baseline(sandbox, 'HEAD') == expected
    assert lint_catalog(sandbox, 'HEAD')['history'] == 'CHECKED'
    with pytest.raises(ValueError, match='Git commit'):
        git_baseline(sandbox, 'not-a-revision')
    result = CliRunner().invoke(app, ['catalog-lint', '--root', str(sandbox), '--base', 'not-a-revision'])
    assert result.exit_code == 2


@pytest.mark.parametrize('status', ['RETIRED', 'SUPERSEDED'])
def test_gov_002_terminal_ids_need_decisions(sandbox, catalog, status):
    data = catalog.model_dump()
    row = data['requirements'].pop(0)
    data['retired_ids'] = [dict(id=row['id'], status=status, decision_ref='09_change/CHG-999.yaml')]
    (sandbox / CATALOG).write_text(encode(data))
    # The still-live canonical definition rejects this fabricated retirement first.
    with pytest.raises(ValidationError, match='Retired-ID reuse'):
        lint_catalog(sandbox)
    data['requirements'].insert(0, {**row, 'status': status})
    current = CatalogFile.model_validate(data)
    assert not check_history(current, catalog)
    assert any('RETIRED_ID_REUSE' in i for i in check_history(catalog, current))
    data = catalog.model_dump()
    data['retired_ids'] = [dict(id='FR-GOV-999', status=status, decision_ref='09_change/CHG-999.yaml')]
    (sandbox / CATALOG).write_text(encode(data))
    assert any('RETIREMENT_DECISION_MISSING' in i for i in lint_catalog(sandbox)['issues'])


def test_gov_001_cli_json_and_failure_exit(sandbox):
    runner = CliRunner()
    result = runner.invoke(app, ['catalog-lint', '--root', str(sandbox), '--json'])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload['history'].startswith('NOT_CHECKED')
    assert payload['readiness'] == payload['evidence'] == 'NOT_CERTIFIED'
    (sandbox / COUNTS).write_text('{}')
    result = runner.invoke(app, ['catalog-lint', '--root', str(sandbox)])
    assert result.exit_code == 1
    assert 'GENERATED_DRIFT' in result.output
    assert runner.invoke(app, ['catalog-export', '--artifact', 'unknown', '--root', str(sandbox)]).exit_code == 2


@pytest.mark.parametrize("command", ["catalog-export", "catalog-lint"])
@pytest.mark.parametrize("yaml_value", ["[private-input", "!!python/object:private.Input {}"])
def test_catalog_yaml_errors_are_controlled(sandbox, command, yaml_value):
    path = sandbox / RTM
    text = path.read_text()
    line = next(line for line in text.splitlines() if line.startswith("  meta:"))
    path.write_text(text.replace(line, "  meta: " + yaml_value, 1))
    result = CliRunner().invoke(app, [command, "--root", str(sandbox)])
    assert result.exit_code == 2
    assert result.output.strip() == "CATALOG_INPUT_ERROR: Invalid embedded YAML (details redacted)"
    assert "private" not in result.output


@pytest.mark.parametrize('artifact', ['catalog', 'schema', 'counts', 'rtm-counts'])
def test_gov_001_exports_deterministic_and_offline(root, catalog, artifact, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Network attempted')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    args = ['catalog-export', '--artifact', artifact, '--root', str(root)]
    first = CliRunner().invoke(app, args)
    second = CliRunner().invoke(app, args)
    assert first.exit_code == second.exit_code == 0, first.output
    assert first.output == second.output
    if artifact == 'rtm-counts':
        assert first.output.strip() == rtm_counts(catalog)
    else:
        expected = {'catalog': catalog.model_dump(), 'schema': catalog_schema(), 'counts': coverage_counts(catalog)}[artifact]
        assert json.loads(first.output) == expected
