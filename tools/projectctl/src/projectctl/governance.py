"""Static CHG-018 advisory review policy; no execution/acceptance certification."""
import json
from pathlib import Path
import re

from .diagnostics import Diagnostic
from .enums import Severity

POLICY_PATH = '09_change/development_review_policy.json'
POLICY_ID = 'DEV-REVIEW-2026-10-15-FINAL'
BINDINGS = ('docs/01_Master_Project_Specification.md',
            'docs/08_Definition_of_Ready_and_Done.md', 'docs/09_Change_Control_Process.md')


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate policy key')
        result[key] = value
    return result


def read_review_policy(root: Path) -> dict:
    """Require the final all-development zero/advisory decision and bindings."""
    data = json.loads((root / POLICY_PATH).read_text(), object_pairs_hook=unique)
    expected = {'schema_version','policy_id','effective_date','authority','supersedes',
                'scope','required_human_approvals','review_mode','review_state_is_workflow_input',
                'reviewer_presence_required','product_hitl_unchanged'}
    if not isinstance(data,dict) or set(data)!=expected:
        raise ValueError('Development review policy schema conflict')
    if (data['schema_version']!='development-review-policy-v2' or data['policy_id']!=POLICY_ID
            or data['effective_date']!='2026-10-15' or data['supersedes']!='DEV-REVIEW-2026-10-15'
            or data['scope']!='development_github_repository_only'
            or not isinstance(data['authority'],str) or not data['authority'].strip()):
        raise ValueError('Development review authority/scope conflict')
    if type(data['required_human_approvals']) is not int or data['required_human_approvals']!=0:
        raise ValueError('CHG-018 requires zero human approvals for ALL development PRs')
    if (data['review_mode']!='ADVISORY' or data['review_state_is_workflow_input'] is not False
            or data['reviewer_presence_required'] is not False or data['product_hitl_unchanged'] is not True):
        raise ValueError('Advisory-only development policy / product HITL boundary conflict')
    for name in BINDINGS:
        rows=re.findall(r'^\| '+POLICY_ID+r' \| ALL_DEVELOPMENT \| ([0-9]+) \|$',
                        (root/name).read_text(),re.M)
        if rows!=['0']:
            raise ValueError('Canonical advisory-policy binding conflict: '+name)
    return data


def review_policy_diagnostics(root: Path) -> list[Diagnostic]:
    claimed=(root/POLICY_PATH).exists() or any(
        (root/name).is_file() and POLICY_ID in (root/name).read_text() for name in BINDINGS)
    if not claimed:
        return []
    try:
        read_review_policy(root)
    except (OSError,ValueError,TypeError,AttributeError) as exc:
        return [Diagnostic(code='DEVELOPMENT_REVIEW_POLICY_CONFLICT',severity=Severity.ERROR,
                           message=str(exc),record_id=POLICY_ID)]
    return []
