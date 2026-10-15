#!/usr/bin/python3 -I
"""CTRL-HOST-003: trusted-team, evidence-gated Plane workflow projection.

CAP_PROFILE is an operational guard, not a same-UID security boundary.
Only this module's constructed state/BLOCKED PATCH is possible. No generic API CLI.
"""
import base64
import datetime as dt
import fcntl
import hashlib
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import pwd
import re
import resource
import subprocess
import sys
import time
import urllib.request

def load_support():
    loader = importlib.machinery.SourceFileLoader('cap_queue', '/usr/local/libexec/cap-plane-queue')
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


q = None  # Tests inject the unprivileged source module; production loads only the root-owned path.
ROOT = Path('/etc/cap-plane-queue')
AUDIT = Path('/var/log/cap-plane-transition/audit.jsonl')
REPO = 'repos/Asperant/critical-aerospace-manufacturing'
GITHUB = {'asrin':'Asperant', 'selman':'selorito', 'batuhan':'Ejlonn', 'yavuz':'Yavuzgmus'}
SHA = re.compile(r'[0-9a-f]{40}')
UUID = re.compile(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}')
REF = re.compile(r'(pr|comment|run):([1-9][0-9]{0,9})')
TARGETS = {'BACKLOG','READY','IN_PROGRESS','IN_REVIEW','MERGE_READY','MERGED','VALIDATING','DONE','CANCELED','BLOCKED','UNBLOCKED'}
FORWARD = dict(zip(['BACKLOG','READY','IN_PROGRESS','IN_REVIEW','MERGE_READY','MERGED','VALIDATING'],
                   ['READY','IN_PROGRESS','IN_REVIEW','MERGE_READY','MERGED','VALIDATING','DONE']))
# Edges alone never authorize anything: predicates and canonical confirmations below do.
REWORK = {('IN_REVIEW','IN_PROGRESS'), ('MERGE_READY','IN_REVIEW'), ('DONE','VALIDATING')}
PROTECTED = ('id','name','description_html','assignees','external_id','external_source','project','workspace',
             'parent','priority','start_date','target_date','cycle','module','modules','milestone','type','estimate_point')


class Denied(Exception):
    def __init__(self, code):
        self.code = code


def need(value, code):
    if not value:
        raise Denied(code)


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def safe_text(value, limit=1000):
    need(isinstance(value, str) and value.strip() and len(value) <= limit, 'INVALID_REASON')
    need(bool(q.clean(value).strip()), 'EMPTY_SANITIZED_REASON')
    return q.clean(value)  # Remove controls/formatting; bounded, no terminal escapes.


def parse_input(raw):
    need(len(raw) <= 8192, 'INPUT_TOO_LARGE')
    need(bool(raw.strip()), 'REASON_AND_EVIDENCE_JSON_REQUIRED_ON_STDIN')
    data = json.loads(raw, object_pairs_hook=q.unique)
    need(isinstance(data, dict) and set(data) == {'reason','evidence_refs'}, 'INVALID_EVIDENCE_ENVELOPE')
    reason = safe_text(data['reason'])
    refs = data['evidence_refs']
    need(isinstance(refs, list) and 1 <= len(refs) <= 16 and all(isinstance(r,str) and REF.fullmatch(r) for r in refs), 'INVALID_EVIDENCE_REFS')
    need(len(refs) == len(set(refs)) and sum(r.startswith('pr:') for r in refs) <= 1, 'AMBIGUOUS_EVIDENCE_REFS')
    return {'reason':reason, 'evidence_refs':refs}


class GitHub:
    """Fixed GET API via existing per-profile gh login, always as unprivileged ailab.

    No GitHub credential is copied/exported by the root helper. No repo code runs.
    User-controlled GH configuration is consumed only after dropping root.
    """
    def __init__(self, profile):
        self.profile = profile
        self.cache = {}
        account = pwd.getpwnam('ailab')
        self.uid, self.gid = account.pw_uid, account.pw_gid
        self.env = {'PATH':'/usr/bin:/bin', 'HOME':account.pw_dir, 'USER':'ailab',
                    'GH_CONFIG_DIR':f'/srv/ailab/user-profiles/{profile}/gh',
                    'GH_PROMPT_DISABLED':'1', 'GH_PAGER':'cat', 'GIT_CONFIG_GLOBAL':'/dev/null',
                    'GIT_CONFIG_NOSYSTEM':'1', 'LANG':'C.UTF-8'}
        user = self._get('user')
        need(user.get('login','').casefold() == GITHUB[profile].casefold(), 'GITHUB_PROFILE_LOGIN_MISMATCH')

    def _get(self, route):
        # Private implementation, not an argument/URL/request-body interface.
        if route not in self.cache:
            result = subprocess.run(['/usr/bin/gh','api','--hostname','github.com','--method','GET',route],
                                    env=self.env, cwd='/', user=self.uid, group=self.gid, extra_groups=(),
                                    umask=0o077, capture_output=True, timeout=30)
            need(result.returncode == 0 and len(result.stdout) <= 8_000_000, 'GITHUB_READ_UNAVAILABLE')
            self.cache[route] = json.loads(result.stdout, object_pairs_hook=q.unique)
        return self.cache[route]

    def main_sha(self):
        value=self._get(f'{REPO}/commits/main')
        need(isinstance(value.get('sha'),str) and SHA.fullmatch(value['sha']), 'MAIN_REVISION_UNAVAILABLE')
        return value['sha']

    def pr(self, number):
        need(type(number) is int and 0 < number < 10**10, 'INVALID_PR')
        return self._get(f'{REPO}/pulls/{number}')

    def comment(self, number):
        need(type(number) is int and 0 < number < 10**10, 'INVALID_COMMENT')
        return self._get(f'{REPO}/issues/comments/{number}')

    def run(self, number):
        need(type(number) is int and 0 < number < 10**10, 'INVALID_RUN')
        return self._get(f'{REPO}/actions/runs/{number}')

    def checks(self, sha):
        need(isinstance(sha,str) and SHA.fullmatch(sha), 'INVALID_REVISION')
        value = self._get(f'{REPO}/commits/{sha}/check-runs?per_page=100')
        need(value.get('total_count') == len(value.get('check_runs',[])), 'INCOMPLETE_CI_CHECKS')
        statuses = self._get(f'{REPO}/commits/{sha}/status?per_page=100')
        need(statuses.get('total_count') == len(statuses.get('statuses',[])), 'INCOMPLETE_COMMIT_STATUSES')
        return value['check_runs'], statuses['statuses']

    def reviews(self, number):
        value = self._get(f'{REPO}/pulls/{number}/reviews?per_page=100')
        need(isinstance(value,list) and len(value) < 100, 'INCOMPLETE_REVIEW_PAGINATION')
        return value

    def merged_shape(self,pr):
        branch=pr['head']['ref']
        need(isinstance(branch,str) and re.fullmatch(r'wp/[A-Za-z0-9_./-]+',branch) and '..' not in branch, 'INVALID_PR_BRANCH')
        refs=self._get(f'{REPO}/git/matching-refs/heads/{branch}')
        need(isinstance(refs,list) and not any(r.get('ref')=='refs/heads/'+branch for r in refs), 'MERGED_BRANCH_NOT_DELETED')
        sha=pr['merge_commit_sha']
        need(isinstance(sha,str) and SHA.fullmatch(sha), 'INVALID_MERGE_COMMIT')
        commit=self._get(f'{REPO}/commits/{sha}')
        need(len(commit.get('parents',[]))==1, 'NON_SQUASH_MERGE_SHAPE')

    def contributors(self,number):
        commits=self._get(f'{REPO}/pulls/{number}/commits?per_page=100')
        need(isinstance(commits,list) and len(commits)<100, 'INCOMPLETE_CONTRIBUTOR_HISTORY')
        result=set()
        emails={v[2]:GITHUB[p].casefold() for p,v in q.PEOPLE.items()}
        for commit in commits:
            result.update(c.get('login','').casefold() for c in (commit.get('author') or {},commit.get('committer') or {}) if c.get('login'))
            for email in re.findall(r'(?im)^Co-authored-by:.*<([^>]+)>',commit.get('commit',{}).get('message','')):
                address=email.casefold()
                if address in emails: result.add(emails[address])
                if address.endswith('@users.noreply.github.com'):
                    result.add(address.split('@')[0].split('+')[-1])
        return result

    def artifact(self, ref, sha):
        need(isinstance(ref,str) and len(ref) <= 250, 'INVALID_ARTIFACT_REF')
        if ref.startswith('repo:'):
            path = ref[5:]
            need(re.fullmatch(r'[A-Za-z0-9_./-]+',path) and not path.startswith('/') and
                 all(p not in {'','.','..'} for p in path.split('/')) and SHA.fullmatch(sha), 'INVALID_ARTIFACT_PATH')
            value = self._get(f'{REPO}/contents/{path}?ref={sha}')
            need(isinstance(value,dict) and value.get('type') == 'file' and value.get('size',0) > 0, 'ARTIFACT_NOT_A_FILE')
        elif re.fullmatch(r'artifact:[1-9][0-9]{0,9}',ref):
            value = self._get(f'{REPO}/actions/artifacts/{ref.split(":")[1]}')
            need(not value.get('expired',True) and value.get('workflow_run',{}).get('head_sha') == sha,
                 'ARTIFACT_EXPIRED_OR_WRONG_REVISION')
        else:
            raise Denied('INVALID_ARTIFACT_REF')


class Plane:
    def __init__(self, key):
        self.reader = q.Reader(key)
        self.key = key
        project = self.reader.get('')
        need(project.get('name') == 'Graduation Project' and project.get('identifier') == 'CAP'
             and project.get('id') == q.PREFIX.split('/')[-2], 'PROJECT_IDENTITY_MISMATCH')
        states = self.reader.rows('states/')
        need({s['name'] for s in states} == q.STATES and len(states) == len(q.STATES), 'WORKFLOW_SCHEMA_MISMATCH')
        self.states = {r['name']:r['id'] for r in states}
        self.names = {v:k for k,v in self.states.items()}
        labels = self.reader.rows('labels/')
        blocked = [r['id'] for r in labels if r['name'] == 'BLOCKED']
        need(len(blocked)==1, 'BLOCKED_LABEL_AMBIGUOUS')
        self.blocked = blocked[0]
        self.items = self.reader.rows('issues/')
        self.members = self.reader.rows('members/')

    def _issue(self, identity, body=None):
        need(isinstance(identity,str) and UUID.fullmatch(identity), 'INVALID_PLANE_ID')
        time.sleep(max(0, 1.25-(time.monotonic()-self.reader.last)))
        self.reader.last = time.monotonic()
        request = urllib.request.Request(q.ORIGIN + q.PREFIX + f'issues/{identity}/',
                    headers={'X-API-Key':self.key, 'Content-Type':'application/json'},
                    data=None if body is None else json.dumps(body).encode(), method='GET' if body is None else 'PATCH')
        with self.reader.opener.open(request,timeout=10) as response:
            need(response.status == 200, 'PLANE_RESPONSE_NOT_CONFIRMED')
            raw = response.read(8_000_001)
            need(len(raw) <= 8_000_000, 'PLANE_RESPONSE_TOO_LARGE')
            return json.loads(raw, object_pairs_hook=q.unique)

    def issue(self, identity):
        return self._issue(identity)

    def patch(self, before, target):
        body = patch_body(before, target, self.states, self.blocked)
        # This is the sole mutation call; the caller cannot submit a body or endpoint.
        return self._issue(before['id'],body)


def patch_body(before, target, states, blocked):
    if target in {'BLOCKED','UNBLOCKED'}:
        labels = before['labels']
        need(isinstance(labels,list) and all(isinstance(x,str) for x in labels), 'INVALID_LABELS')
        return {'labels': sorted((set(labels)|{blocked}) if target=='BLOCKED' else (set(labels)-{blocked}))}
    need(target in states, 'INVALID_TARGET_STATE')
    return {'state':states[target]}


def own(item, profile, wp, policy):
    need(wp in policy['contexts'], 'NON_CANONICAL_WP')
    card = policy['contexts'][wp]['work_package']
    need(card['primary_owner']['canonical_name'] == q.PEOPLE[profile][0], 'WRONG_CANONICAL_OWNER')
    need(item.get('external_id') == wp and item.get('external_source') == 'projectctl' and
         item.get('name','').startswith('['+wp+'] '), 'PLANE_CANONICAL_IDENTITY_MISMATCH')
    meta = q.metadata(item.get('description_html'))
    need(meta.get('canonical_wp_id') == wp and meta.get('canonical_owner') == q.PEOPLE[profile][0], 'PLANE_METADATA_OWNER_MISMATCH')
    need(item.get('assignees') == [q.PEOPLE[profile][1]], 'PLANE_ASSIGNEE_MISMATCH')
    return card


def find(plane, profile, wp, policy):
    matches = [r for r in plane.items if r.get('external_id') == wp or r.get('name','').startswith('['+wp+'] ')]
    need(len(matches)==1, 'AMBIGUOUS_OR_MISSING_CANONICAL_WP')
    item = plane.issue(matches[0]['id'])
    own(item,profile,wp,policy)
    need(item.get('state') in plane.names, 'UNKNOWN_PLANE_STATE')
    member = [r for r in plane.members if r.get('id')==q.PEOPLE[profile][1]]
    need(len(member)==1 and member[0].get('email','').casefold()==q.PEOPLE[profile][2], 'PROJECT_MEMBER_IDENTITY_MISMATCH')
    return item


def records(gh, refs):
    result=[]
    for ref in refs:
        kind, number=ref.split(':')
        if kind!='comment': continue
        comment=gh.comment(int(number))
        # A comment is a durable canonical confirmation, not a caller boolean.
        try:
            body=json.loads(comment['body'], object_pairs_hook=q.unique)
        except (ValueError,TypeError):
            raise Denied('INVALID_CONFIRMATION_RECORD') from None
        need(isinstance(body,dict) and set(body)=={'cap_plane_transition'}, 'INVALID_CONFIRMATION_RECORD')
        need(len(comment.get('body',''))<=65536, 'CONFIRMATION_TOO_LARGE')
        data=body['cap_plane_transition']
        need(isinstance(data,dict), 'INVALID_CONFIRMATION_RECORD')
        result.append((comment.get('user',{}).get('login',''),data))
    return result


def pr_fact(gh, refs, wp, profile):
    numbers=[int(r.split(':')[1]) for r in refs if r.startswith('pr:')]
    need(len(numbers)==1, 'ONE_REAL_WP_PR_REQUIRED')
    pr=gh.pr(numbers[0])
    need(pr.get('base',{}).get('repo',{}).get('full_name','').casefold()=='Asperant/critical-aerospace-manufacturing'.casefold()
         and pr['base'].get('ref')=='main', 'WRONG_PR_REPOSITORY_OR_BASE')
    need(pr.get('user',{}).get('login','').casefold()==GITHUB[profile].casefold(), 'PR_AUTHOR_PROFILE_MISMATCH')
    need(pr.get('head',{}).get('ref','').startswith('wp/'+wp+'-') and
         re.search(r'(?<![A-Z0-9-])'+re.escape(wp)+r'(?![A-Z0-9-])',pr.get('title','')+' '+pr.get('body','')), 'PR_WP_BINDING_MISSING')
    need(pr.get('changed_files',0)>0 and SHA.fullmatch(pr.get('head',{}).get('sha','')), 'NO_IMPLEMENTATION_CHANGE')
    return pr


def ci(gh,sha,policy):
    checks,statuses=gh.checks(sha)
    need(checks or statuses, 'CI_EVIDENCE_MISSING')
    need(all(c.get('status')=='completed' and c.get('conclusion')=='success' for c in checks), 'CI_NOT_GREEN')
    need(all(s.get('state')=='success' for s in statuses), 'COMMIT_STATUS_NOT_GREEN')
    observed={c['name'] for c in checks}|{s['context'] for s in statuses}
    need(set(policy['required_ci']) <= observed, 'REQUIRED_CI_MISSING')


def confirmation(rows, authors, wp, source, target, sha, policy):
    matches=[dict(data,_confirming_login=author) for author,data in rows if author.casefold() in {a.casefold() for a in authors}
             and data.get('wp_id')==wp and data.get('from_state')==source and data.get('to_state')==target
             and data.get('head_sha')==sha and data.get('source_manifest')==policy['source_manifest']
             and data.get('policy_digest')==policy['policy_digest']]
    need(len(matches)==1, 'CANONICAL_CONFIRMATION_MISSING_OR_AMBIGUOUS')
    safe_text(matches[0].get('reason'))
    return matches[0]


def criteria(gh,record,ids,sha):
    checks=record.get('checks')
    need(isinstance(checks,dict), 'CANONICAL_CRITERIA_UNCONFIRMED')
    for identity in ids:
        data=checks.get(identity,{})
        need(isinstance(data,dict) and data.get('result') in {'PASS','N/A'}, 'CRITERION_NOT_CONFIRMED')
        mandatory = identity.startswith(('DOR-PR-', 'docs/08#9:')) or identity in {'DOD-WP-01','DOD-WP-02','DOD-WP-03','DOD-WP-12', 'IMPLEMENTATION-STARTED','POST-MERGE-VALIDATION-STARTED','BLOCKER-OBSERVED','BLOCKER-RESOLVED','docs/08#11:EVIDENCE-STALE'}
        need(not mandatory or data['result']=='PASS', 'MANDATORY_CRITERION_CANNOT_BE_NA')
        safe_text(data.get('reason'))
        refs=data.get('evidence_refs')
        need(isinstance(refs,list) and 1<=len(refs)<=8, 'CRITERION_EVIDENCE_MISSING')
        for ref in refs: gh.artifact(ref,sha)


def dependencies(gh, rows, context, record, sha, policy, final=False):
    for edge in context['dependency_edges']:
        semantics=edge['semantics']
        if semantics['strength']!='HARD' or not final and semantics['blocking_stage']!='START': continue
        if final and semantics['blocking_stage'] in {'MILESTONE_EXIT','FREEZE'}:
            # A milestone/freeze gate is not automatically a WP closure gate.
            # Its applicability requires the actual supporting-reviewer assessment.
            disposition=record.get('dependency_stage_dispositions',{}).get(edge['id'])
            need(isinstance(disposition,dict) and type(disposition.get('applies_to_wp_completion')) is bool,
                 'DEPENDENCY_STAGE_APPLICABILITY_UNKNOWN')
            safe_text(disposition.get('reason'))
            artifacts=disposition.get('evidence_refs',[])
            need(isinstance(artifacts,list) and artifacts, 'DEPENDENCY_STAGE_EVIDENCE_MISSING')
            for artifact in artifacts: gh.artifact(artifact,sha)
            if not disposition['applies_to_wp_completion']: continue
        producer=policy['node_owners'].get(edge['predecessor']['node'])
        need(producer in q.PEOPLE, 'DEPENDENCY_CONFIRMING_OWNER_UNKNOWN')
        matches=[data.get('dependency_readiness',{}).get(edge['id']) for author,data in rows
                 if author.casefold()==GITHUB[producer].casefold() and data.get('source_manifest')==policy['source_manifest']
                 and data.get('wp_id')==context['work_package']['id'] and data.get('head_sha')==sha
                 and data.get('policy_digest')==policy['policy_digest']]
        matches=[m for m in matches if isinstance(m,dict)]
        need(len(matches)==1,'DEPENDENCY_READINESS_UNKNOWN')
        data=matches[0]
        levels=policy['node_levels'].get(edge['predecessor']['node'],[])
        required=semantics['required_readiness']
        need(required in levels and data.get('readiness') in levels and
             levels.index(data['readiness'])>=levels.index(required), 'HARD_DEPENDENCY_NOT_READY')
        # Merely marking a producer WP DONE is deliberately not a readiness proof.
        safe_text(data.get('precise_consumer_requirement'))
        refs=data.get('evidence_refs',[])
        need(isinstance(refs,list) and refs, 'DEPENDENCY_ARTIFACTS_MISSING')
        for ref in refs: gh.artifact(ref,sha)


def approvals(gh,pr,record,profile,merging=True):
    need(record.get('review_risk') in {'normal','high'} and isinstance(record.get('high_risk_triggers'),list), 'REVIEW_RISK_UNKNOWN')
    triggers={'authentication_authorization','protected_action_authority','destructive_migration','security_sensitive_infra_secrets','major_authority_boundary'}
    need(all(isinstance(v,str) and v in triggers for v in record['high_risk_triggers']), 'UNKNOWN_HIGH_RISK_TRIGGER')
    high=record['review_risk']=='high'
    need(high == bool(record['high_risk_triggers']), 'REVIEW_RISK_CONFLICT')
    # Risk assessment must itself be confirmed by an independent qualified reviewer.
    # Historical PR#4/#5 owner overrides are bounded to their exact control heads;
    # none authorizes a canonical product WP or a blanket stale-approval exception.
    latest={}
    for review in sorted(gh.reviews(pr['number']),key=lambda r:(r.get('submitted_at') or '',r.get('id',0))):
        login=review.get('user',{}).get('login','').casefold()
        if review.get('state') not in {'COMMENTED','PENDING'}:
            latest[login]=review
    need(not any(r.get('state')=='CHANGES_REQUESTED' for r in latest.values()), 'BLOCKING_REVIEW_FINDING')
    pairers=record.get('pairing_participants')
    need(isinstance(pairers,list) and all(p in GITHUB.values() for p in pairers), 'PAIRING_INDEPENDENCE_UNCONFIRMED')
    contributors=gh.contributors(pr['number'])|{p.casefold() for p in pairers}|{GITHUB[profile].casefold()}
    accepted={login for login,r in latest.items() if r.get('state')=='APPROVED' and
              r.get('commit_id')==pr['head']['sha'] and login not in contributors}
    qualified={x.casefold() for x in record.get('qualified_reviewers',[]) if x in GITHUB.values()}
    need(len(accepted & qualified)>=(2 if high else 1), 'CURRENT_HEAD_APPROVALS_MISSING')
    need(record.get('_confirming_login','').casefold() in accepted & qualified, 'RISK_CONFIRMATION_NOT_FROM_CURRENT_INDEPENDENT_APPROVER')
    if high:
        need(bool(accepted & qualified & {'asperant','yavuzgmus'}), 'HIGH_RISK_EXPERTISE_MISSING')
    if merging: need(pr.get('mergeable') is True and pr.get('mergeable_state')=='clean', 'PR_NOT_MERGE_READY')


def evaluate(profile,wp,source,target,item,plane,policy,gh,envelope,previous=None):
    context=policy['contexts'][wp]
    card=own(item,profile,wp,policy)
    need(source!='CANCELED' or target=='UNBLOCKED', 'CANCELED_IS_TERMINAL')
    need(source!='DONE' or target in {'VALIDATING','UNBLOCKED'}, 'DONE_REQUIRES_STALENESS_REOPEN')
    need(target in {'BLOCKED','UNBLOCKED','CANCELED'} or FORWARD.get(source)==target or (source,target) in REWORK,
         'INVALID_CANONICAL_TRANSITION')
    blocked=plane.blocked in item['labels']
    need(not blocked or target in {'BLOCKED','UNBLOCKED','CANCELED'}, 'ACTIVE_BLOCKER_UNRESOLVED')
    refs=envelope['evidence_refs']
    rows=records(gh,refs)
    # Planning/blocker/cancellation evidence may precede an implementation PR.
    # Requiring code before READY would invert the canonical DoR gate.
    prework=target in {'READY','BLOCKED','UNBLOCKED','CANCELED'}
    pr=pr_fact(gh,refs,wp,profile) if not prework or any(r.startswith('pr:') for r in refs) else None
    post=source in {'MERGED','VALIDATING','DONE'} or target=='MERGED'
    sha=(pr.get('merge_commit_sha') if post else pr['head']['sha']) if pr else gh.main_sha()
    need(isinstance(sha,str) and SHA.fullmatch(sha), 'REVISION_UNAVAILABLE')
    if post and pr: need(pr.get('merged') is True, 'PR_NOT_ACTUALLY_MERGED')
    owner=GITHUB[profile]
    peers=[GITHUB[p] for p in GITHUB if p!=profile and q.PEOPLE[p][0] in
           [r['canonical_name'] for r in card.get('supporting_reviewers') or []]]
    independent=[login for p,login in GITHUB.items() if p!=profile]
    if target=='CANCELED':
        decision=confirmation(rows,['Asperant'],wp,source,target,sha,policy)
        need(decision.get('owner_decision')=='CANCEL', 'EXPLICIT_OWNER_CANCELLATION_REQUIRED')
        return
    if target=='BLOCKED':
        need(source not in {'DONE','CANCELED'}, 'TERMINAL_ITEM_CANNOT_BE_BLOCKED')
        record=confirmation(rows,[owner],wp,source,target,sha,policy)
        blocker=record.get('blocker',{})
        need(isinstance(blocker,dict) and blocker.get('owner') in q.PEOPLE, 'BLOCKER_OWNER_REQUIRED')
        linked=blocker.get('wp_id')
        if linked is not None:
            need(linked in policy['contexts'] and linked!=wp, 'BLOCKER_WP_NOT_CANONICAL')
        else:
            safe_text(blocker.get('external_dependency'))
        criteria(gh,record,['BLOCKER-OBSERVED'],sha)
        return {'blocker':{'owner':blocker['owner'],'wp_id':linked,
                'external_dependency':q.clean(blocker.get('external_dependency',''))}}
    if target=='UNBLOCKED':
        need(previous and previous.get('result')=='VERIFIED' and previous.get('operation')=='BLOCKED', 'BLOCKER_HISTORY_MISSING')
        # A resolution can be corroborated by an actual successful validation run,
        # or by the supporting reviewer; no new per-transition human approval quota.
        runs=[gh.run(int(r.split(':')[1])) for r in refs if r.startswith('run:')]
        def resolved_after_block(run):
            try:
                completed=dt.datetime.fromisoformat(run.get('updated_at','').replace('Z','+00:00'))
                observed=dt.datetime.fromisoformat(previous.get('timestamp','').replace('Z','+00:00'))
                return completed>=observed
            except (ValueError,TypeError):
                return False
        automated=any(r.get('head_sha')==sha and r.get('status')=='completed' and r.get('conclusion')=='success'
                      and resolved_after_block(r) for r in runs)
        record=confirmation(rows,[owner] if automated else peers,wp,source,target,sha,policy)
        need(record.get('resolves_audit_id')==previous['audit_id'], 'WRONG_BLOCKER_RESOLUTION')
        criteria(gh,record,['BLOCKER-RESOLVED'],sha)
        return {'resolves_audit_id':previous['audit_id']}
    if target=='READY':
        need(context['cycle_ids'], 'UNSCHEDULED_WORK_NEEDS_PLANNING_DECISION')
        need(not any(r['id']!=item['id'] and r.get('assignees')==[q.PEOPLE[profile][1]] and
                     r.get('state')==plane.states['READY'] for r in plane.items), 'ANOTHER_READY_WP_EXISTS')
        record=confirmation(rows,[owner],wp,source,target,sha,policy)
        criteria(gh,record,policy['dor_task']+card['dor_refs'],sha)
        dependencies(gh,rows,context,record,sha,policy)
    elif target=='IN_PROGRESS':
        need(not pr.get('merged') and pr.get('state')=='open', 'NO_LIVE_IMPLEMENTATION_PR')
        if source=='IN_REVIEW': need(pr.get('draft') is True, 'REWORK_REQUIRES_DRAFT_PR')
        active=[r for r in plane.items if r.get('assignees')==[q.PEOPLE[profile][1]] and
                r.get('state')==plane.states['IN_PROGRESS'] and r['id']!=item['id']]
        need(len(active)<2, 'IMPLEMENTATION_WIP_LIMIT')
        def heavy(identity):
            c=policy['contexts'][identity]['work_package']
            band=re.fullmatch(r'([SML])(?: \(.*\))?',c.get('size_band') or '')
            need(band is not None, 'WORKLOAD_CLASS_UNKNOWN')
            return band.group(1)=='L' or identity.startswith('WP-CORE-')
        if heavy(wp): need(not any(heavy(r.get('external_id','')) for r in active), 'HEAVY_CORE_WIP_LIMIT')
        record=confirmation(rows,[owner],wp,source,target,sha,policy)
        criteria(gh,record,['IMPLEMENTATION-STARTED'],sha)
        dependencies(gh,rows,context,record,sha,policy)
    elif target=='IN_REVIEW':
        need(pr.get('state')=='open' and not pr.get('draft') and not pr.get('merged'), 'REAL_REVIEWABLE_PR_REQUIRED')
        need(pr.get('requested_reviewers') or pr.get('requested_teams') or gh.reviews(pr['number']), 'REVIEW_NOT_REQUESTED')
        ci(gh,sha,policy)
        record=confirmation(rows,[owner],wp,source,target,sha,policy)
        criteria(gh,record,policy['dor_pr'],sha)
        if source=='MERGE_READY':
            need(not any(r.get('state')=='APPROVED' and r.get('commit_id')==sha for r in gh.reviews(pr['number'])),
                 'NO_STALE_APPROVAL_REVIEW_EVENT')
    elif target=='MERGE_READY':
        need(not pr.get('draft') and not pr.get('merged'), 'REAL_REVIEWABLE_PR_REQUIRED')
        ci(gh,sha,policy)
        record=confirmation(rows,independent,wp,source,target,sha,policy)
        criteria(gh,record,policy['dor_pr']+policy['dod_pr'],sha)
        approvals(gh,pr,record,profile)
    elif target=='MERGED':
        need(pr.get('merged') is True and pr.get('base',{}).get('ref')=='main', 'PR_NOT_ACTUALLY_MERGED')
        ci(gh,pr['head']['sha'],policy)
        gh.merged_shape(pr)
        record=confirmation(rows,independent,wp,source,target,sha,policy)
        criteria(gh,record,policy['dod_pr'],sha)
        approvals(gh,pr,record,profile,merging=False)
    elif target=='VALIDATING':
        record=confirmation(rows,peers if source=='DONE' else [owner],wp,source,target,sha,policy)
        if source=='DONE': criteria(gh,record,['docs/08#11:EVIDENCE-STALE'],sha)
        runs=[gh.run(int(r.split(':')[1])) for r in refs if r.startswith('run:')]
        need(any(r.get('head_sha')==sha and r.get('head_branch')=='main' and r.get('status')=='in_progress'
                 and r.get('event')!='pull_request' for r in runs), 'POST_MERGE_VALIDATION_NOT_RUNNING')
        criteria(gh,record,['POST-MERGE-VALIDATION-STARTED'],sha)
    elif target=='DONE':
        ci(gh,sha,policy)
        gh.merged_shape(pr)
        owner_record=confirmation(rows,[owner],wp,source,target,sha,policy)
        peer_record=confirmation(rows,peers,wp,source,target,sha,policy)
        ids=sorted(set(policy['dod_wp']+card['dod_refs']+context['scope_criteria']))
        if card.get('scope_class')=='R1': ids+=policy['dod_research']
        for record in (owner_record,peer_record): criteria(gh,record,ids,sha)
        approvals(gh,pr,peer_record,profile,merging=False)
        dependencies(gh,rows,context,peer_record,sha,policy,final=True)
        runs=[gh.run(int(r.split(':')[1])) for r in refs if r.startswith('run:')]
        need(any(r.get('head_sha')==sha and r.get('head_branch')=='main' and r.get('status')=='completed'
                 and r.get('conclusion')=='success' and r.get('event')!='pull_request' for r in runs), 'POST_MERGE_VALIDATION_NOT_PASSED')


def verify_readback(before,after,target,plane):
    need(all(before.get(k)==after.get(k) for k in PROTECTED), 'PROTECTED_FIELD_CHANGED')
    body=patch_body(before,target,plane.states,plane.blocked)
    for key,expected in body.items():
        actual=after.get(key)
        need((sorted(actual)==expected if key=='labels' and isinstance(actual,list) else actual==expected), 'MUTATION_READBACK_MISMATCH')
    if target in {'BLOCKED','UNBLOCKED'}: need(before['state']==after['state'], 'WORKFLOW_CHANGED_DURING_BLOCKER_UPDATE')
    else: need(sorted(before['labels'])==sorted(after['labels']), 'LABELS_CHANGED_DURING_STATE_UPDATE')


def append_audit(record,key):
    raw=json.dumps(record,ensure_ascii=True,sort_keys=True)
    need(key not in raw and json.dumps(key)[1:-1] not in raw, 'SECRET_IN_AUDIT_INPUT')
    fd=os.open(AUDIT,os.O_WRONLY|os.O_APPEND|os.O_CREAT|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'a') as stream:
        need(os.fstat(stream.fileno()).st_uid==0, 'UNSAFE_AUDIT_OWNER')
        stream.write(raw+'\n')
        stream.flush()
        os.fsync(stream.fileno())


def last_blocker(wp):
    if not AUDIT.exists(): return None
    need(AUDIT.stat().st_size<10_000_000, 'AUDIT_ROTATION_REQUIRED')
    rows=[json.loads(line) for line in AUDIT.read_text().splitlines()]
    matches=[r for r in rows if r.get('wp_id')==wp and r.get('result')=='VERIFIED' and
             r.get('operation') in {'BLOCKED','UNBLOCKED'}]
    return matches[-1] if matches else None


def execute(profile,wp,target,envelope,policy,plane,gh,audit,key,previous=None):
    need(profile in q.PEOPLE and q.WP.fullmatch(wp) and target in TARGETS, 'INVALID_ARGUMENTS')
    need(wp in policy['contexts'], 'NON_CANONICAL_WP')
    item=find(plane,profile,wp,policy)
    source=plane.names[item['state']]
    record={'timestamp':now(),'profile':profile,'wp_id':wp,'from_state':source,
            'to_state':source if target in {'BLOCKED','UNBLOCKED'} else target,
            'operation':target,'reason':envelope['reason'],'evidence_refs':envelope['evidence_refs'],
            'policy_digest':policy['policy_digest']}
    record['audit_id']=hashlib.sha256(json.dumps(record,sort_keys=True).encode()).hexdigest()
    is_same=target==source or target=='BLOCKED' and plane.blocked in item['labels'] or target=='UNBLOCKED' and plane.blocked not in item['labels']
    if is_same:
        need(plane.issue(item['id'])==item, 'CONCURRENT_PLANE_CHANGE')
        record['result']='UNCHANGED'
        if previous and previous.get('operation')=='BLOCKED' and previous.get('result')=='VERIFIED':
            record['active_blocker_audit_id']=previous['audit_id']
        audit(record,key)
        return record
    operation_data=evaluate(profile,wp,source,target,item,plane,policy,gh,envelope,previous)
    if operation_data: record.update(operation_data)
    fresh=plane.issue(item['id'])
    own(fresh,profile,wp,policy)
    need(fresh==item, 'CONCURRENT_PLANE_CHANGE')
    record['result']='INTENT'
    audit(record,key)  # A writable durable audit sink is a precondition for mutation.
    try:
        try:
            plane.patch(fresh,target)  # Exactly one PATCH, never automatically retried.
        except Exception:
            pass  # A timed-out response may already have applied; only fresh readback decides.
        after=plane.issue(item['id'])
        own(after,profile,wp,policy)
        verify_readback(fresh,after,target,plane)
        record['result']='VERIFIED'
    except Exception:
        record['result']='UNCONFIRMED_REQUIRES_READBACK'
        audit(record,key)
        raise Denied('MUTATION_UNCONFIRMED_DO_NOT_RETRY_BLINDLY') from None
    audit(record,key)
    return record


def verify_policy_sources(policy):
    for name,expected in policy['source_manifest'].items():
        need(isinstance(name,str) and not name.startswith('/') and '..' not in name.split('/'), 'INVALID_POLICY_SOURCE')
        try:
            actual=hashlib.sha256((Path('/srv/ailab/project')/name).read_bytes()).hexdigest()
        except OSError:
            raise Denied('CANONICAL_POLICY_SOURCE_UNAVAILABLE') from None
        need(actual==expected, 'CANONICAL_POLICY_REFRESH_REQUIRED')
    need(hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==policy['implementation_sha256']['transition'], 'HELPER_POLICY_REFRESH_REQUIRED')
    need(hashlib.sha256(Path('/usr/local/libexec/cap-plane-queue').read_bytes()).hexdigest()==policy['implementation_sha256']['queue'], 'QUEUE_POLICY_REFRESH_REQUIRED')


def main():
    global q
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    try:
        need(os.geteuid()==0 and len(sys.argv)==4, 'INVALID_INVOCATION')
        if q is None: q=load_support()
        need(q.STATES == TARGETS-{'BLOCKED','UNBLOCKED'}, 'CANONICAL_WORKFLOW_SCHEMA_CHANGED')
        profile,wp,target=sys.argv[1:]
        need(profile in q.PEOPLE and q.WP.fullmatch(wp) and target in TARGETS, 'INVALID_ARGUMENTS')
        os.environ.clear()
        need(not getattr(sys.stdin,'isatty',lambda:False)(), 'REASON_AND_EVIDENCE_JSON_REQUIRED_ON_STDIN')
        envelope=parse_input(sys.stdin.buffer.read(8193))
        policy=json.loads((ROOT/'transition-policy.json').read_text(), object_pairs_hook=q.unique)
        key=json.loads((ROOT/'credential.json').read_text())['api_key']
        need(isinstance(key,str) and key and not any(c in key for c in '\r\n'), 'INVALID_CREDENTIAL_CONFIG')
        # Reject raw secret input before logging or external lookups.
        need(key not in json.dumps(envelope) and key not in envelope['reason'], 'SECRET_IN_INPUT')
        verify_policy_sources(policy)
        need(wp in policy['contexts'] and policy['contexts'][wp]['work_package']['primary_owner']['canonical_name']==q.PEOPLE[profile][0], 'WRONG_OR_NON_CANONICAL_OWNER')
        lockfd=os.open('/run/cap-plane-queue.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        with os.fdopen(lockfd,'r+') as lock:
            need(os.fstat(lock.fileno()).st_uid==0, 'UNSAFE_LOCK_OWNER')
            fcntl.flock(lock,fcntl.LOCK_EX)
            time.sleep(1.25)
            plane=Plane(key)
            gh=GitHub(profile)
            result=execute(profile,wp,target,envelope,policy,plane,gh,append_audit,key,last_blocker(wp))
        q.emit(result,key)
        return 0
    except Denied as exc:
        print(json.dumps({'result':'DENIED','reason_code':exc.code},sort_keys=True))
    except Exception:
        print('{"result":"UNAVAILABLE","reason_code":"EVIDENCE_OR_SERVICE_UNAVAILABLE"}')
    return 2


if __name__=='__main__':
    sys.exit(main())
