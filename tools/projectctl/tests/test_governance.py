"""Final owner policy consistency and anti-bypass checks; entirely offline."""
import json

import pytest

from projectctl.governance import BINDINGS, POLICY_PATH, POLICY_ID, read_review_policy, review_policy_diagnostics


@pytest.fixture
def policy_root(tmp_path, root):
    policy = json.loads((root / POLICY_PATH).read_text())
    destination = tmp_path / POLICY_PATH
    destination.parent.mkdir(parents=True)
    destination.write_text(json.dumps(policy))
    for name in BINDINGS:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'| {POLICY_ID} | ALL_DEVELOPMENT | 0 |\n')
    return tmp_path


def test_real_canonical_policy(root):
    policy = read_review_policy(root)
    assert policy['required_human_approvals'] == 0
    assert policy['review_mode'] == 'ADVISORY'
    assert policy['review_state_is_workflow_input'] is False
    assert not review_policy_diagnostics(root)


@pytest.mark.parametrize('field,value', [
    ('required_human_approvals', 1), ('required_human_approvals', 2),
    ('required_human_approvals', False), ('reviewer_presence_required', True),
    ('review_state_is_workflow_input', True), ('review_mode', 'MANDATORY'),
    ('product_hitl_unchanged', False), ('scope', 'product_runtime'),
    ('required_approvals', {'normal': 0, 'high': 2}),
])
def test_policy_conflict_is_error(policy_root, field, value):
    path = policy_root / POLICY_PATH
    policy = json.loads(path.read_text()); policy[field] = value
    path.write_text(json.dumps(policy))
    with pytest.raises(ValueError): read_review_policy(policy_root)
    assert review_policy_diagnostics(policy_root)[0].code == 'DEVELOPMENT_REVIEW_POLICY_CONFLICT'


@pytest.mark.parametrize('binding', BINDINGS)
def test_canonical_binding_conflicts_not_silently_repaired(policy_root, binding):
    path = policy_root / binding
    path.write_text(path.read_text().replace('ALL_DEVELOPMENT | 0', 'ALL_DEVELOPMENT | 1'))
    assert review_policy_diagnostics(policy_root)


def test_missing_claimed_companion_and_duplicate_keys_rejected(policy_root):
    path = policy_root / POLICY_PATH
    path.unlink()
    assert review_policy_diagnostics(policy_root)
    path.write_text('{"policy_id":"a","policy_id":"b"}')
    assert review_policy_diagnostics(policy_root)


def test_old_minimal_corpus_does_not_claim_new_policy(tmp_path):
    assert not review_policy_diagnostics(tmp_path)


def test_chg017_preserved_as_historical_intermediate_decision(root):
    import hashlib
    assert hashlib.sha256((root/'09_change/CHG-017.yaml').read_bytes()).hexdigest() == '026adf87438dbee71be68d83100b7343963a70d8ab97ad9f14bd8a610f83de9a'
    previous=json.loads((root/'09_change/history/CHG-017-development_review_policy.json').read_text())
    assert previous['required_approvals']=={'normal':0,'high':2}
    assert read_review_policy(root)['supersedes']==previous['policy_id']
