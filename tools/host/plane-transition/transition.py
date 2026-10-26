#!/usr/bin/python3 -I
"""CTRL-HOST-003: trusted-team, evidence-gated Plane workflow projection.

CAP_PROFILE is an operational guard, not a same-UID security boundary.
Only this module's constructed state/BLOCKED PATCH is possible. No generic API CLI.
"""
import base64
import contextlib
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
REF = re.compile(r'(?:(pr|comment|run):([1-9][0-9]{0,17})|commit:[0-9a-f]{40})')
TARGETS = {'BACKLOG','READY','IN_PROGRESS','IN_REVIEW','MERGE_READY','MERGED','VALIDATING','DONE','CANCELED','BLOCKED','UNBLOCKED'}
FORWARD = dict(zip(['BACKLOG','READY','IN_PROGRESS','IN_REVIEW','MERGE_READY','MERGED','VALIDATING'],
                   ['READY','IN_PROGRESS','IN_REVIEW','MERGE_READY','MERGED','VALIDATING','DONE']))
# Edges alone never authorize anything: actual facts and semantic evidence below do.
REWORK = {('IN_REVIEW','IN_PROGRESS'), ('MERGE_READY','IN_REVIEW'), ('DONE','VALIDATING')}
FILE_PAGE = 100          # GitHub's per-page maximum for the pull-request files route
FILE_PAGE_CEILING = 10   # bounded inventory: at most 1000 files (10 pages); larger PRs are rejected
PR_FILE_STATUSES = {'added','removed','modified','renamed','copied','changed','unchanged'}
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
    need(len(refs) == len(set(refs)) and sum(r.startswith(('pr:','commit:')) for r in refs) <= 1, 'AMBIGUOUS_EVIDENCE_REFS')
    return {'reason':reason, 'evidence_refs':refs}


class GitHub:
    """Fixed GET API via existing per-profile gh login, always as the matching unprivileged Linux account.

    No GitHub credential is copied/exported by the root helper. No repo code runs.
    User-controlled GH configuration is consumed only after dropping root.
    """
    def __init__(self, profile):
        self.profile = profile
        self.cache = {}
        account = pwd.getpwnam(profile)
        self.uid, self.gid = account.pw_uid, account.pw_gid
        self.env = {'PATH':'/usr/bin:/bin', 'HOME':account.pw_dir, 'USER':profile,
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
            need(result.returncode == 0 or b'HTTP 401' not in result.stderr, 'GITHUB_AUTH_HTTP_401')
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

    def invalidate(self):
        """Forget every cached read except immutable SHA-addressed commits.

        Mutable evidence (main, refs, PR bodies and files, comparisons, runs) must be read
        again from GitHub when a caller needs a genuinely fresh snapshot.
        """
        immutable=re.compile(re.escape(REPO)+r'/commits/[0-9a-f]{40}')
        keep={route:value for route,value in self.cache.items() if immutable.fullmatch(route)}
        self.cache.clear()
        self.cache.update(keep)

    def fresh_pr(self,number):
        need(type(number) is int and 0<number<10**10, 'INVALID_PR')
        self.cache.pop(f'{REPO}/pulls/{number}',None)
        return self.pr(number)

    def started_commit(self,wp,sha,profile):
        need(q.WP.fullmatch(wp) and SHA.fullmatch(sha), 'INVALID_WORK_REVISION')
        branches=self._get(f'{REPO}/git/matching-refs/heads/wp/{wp}-')
        need(isinstance(branches,list) and len(branches)<100, 'WORK_BRANCH_LIST_INCOMPLETE')
        matches=[b for b in branches if b.get('ref','').startswith('refs/heads/wp/'+wp+'-')
                 and b.get('object',{}).get('sha')==sha]
        need(len(matches)==1, 'WORK_BRANCH_MISSING_OR_AMBIGUOUS')
        commit=self._get(f'{REPO}/commits/{sha}')
        need(commit.get('author',{}).get('login','').casefold()==GITHUB[profile].casefold(), 'WORK_COMMIT_AUTHOR_MISMATCH')
        comparison=self._get(f'{REPO}/compare/main...{sha}')
        need(comparison.get('ahead_by',0)>0 and comparison.get('files'), 'NO_IMPLEMENTATION_CHANGE_FROM_MAIN')

    def comment(self, number):
        need(type(number) is int and 0 < number < 10**10, 'INVALID_COMMENT')
        return self._get(f'{REPO}/issues/comments/{number}')

    def run(self, number):
        need(type(number) is int and 0 < number < 10**18, 'INVALID_RUN')
        return self._get(f'{REPO}/actions/runs/{number}')

    def checks(self, sha):
        need(isinstance(sha,str) and SHA.fullmatch(sha), 'INVALID_REVISION')
        value = self._get(f'{REPO}/commits/{sha}/check-runs?per_page=100')
        need(value.get('total_count') == len(value.get('check_runs',[])), 'INCOMPLETE_CI_CHECKS')
        statuses = self._get(f'{REPO}/commits/{sha}/status?per_page=100')
        need(statuses.get('total_count') == len(statuses.get('statuses',[])), 'INCOMPLETE_COMMIT_STATUSES')
        return value['check_runs'], statuses['statuses']

    def files(self,pr):
        """Complete, bounded PR file inventory: every page, exact count, no truncation.

        The inventory must equal the PR's own changed_files count, contain no duplicate or
        malformed row, and stay unchanged while it is read. More than FILE_PAGE_CEILING pages
        is refused rather than silently truncated.
        """
        number=pr.get('number')
        need(type(number) is int and 0<number<10**10, 'INVALID_PR')
        expected=pr.get('changed_files')
        need(type(expected) is int and expected>=0, 'INCOMPLETE_PR_FILE_SCOPE')
        need(expected<=FILE_PAGE*FILE_PAGE_CEILING, 'PR_FILE_SCOPE_EXCEEDS_CEILING')
        pages=-(-expected//FILE_PAGE)
        rows=[]
        for page in range(1,pages+1):
            chunk=self._get(f'{REPO}/pulls/{number}/files?per_page={FILE_PAGE}&page={page}')
            need(isinstance(chunk,list) and len(chunk)==min(FILE_PAGE,expected-FILE_PAGE*(page-1)),
                 'INCOMPLETE_PR_FILE_SCOPE')
            rows.extend(chunk)
        if pages<FILE_PAGE_CEILING:
            # An empty terminal page proves nothing was left unread (exact 100/200/... files).
            need(self._get(f'{REPO}/pulls/{number}/files?per_page={FILE_PAGE}&page={pages+1}')==[],
                 'INCOMPLETE_PR_FILE_SCOPE')
        names=[]
        for row in rows:
            need(isinstance(row,dict) and isinstance(row.get('filename'),str) and row['filename']
                 and row.get('status') in PR_FILE_STATUSES, 'MALFORMED_PR_FILE_ROW')
            names.append(row['filename'])
        need(len(names)==len(set(names)), 'DUPLICATE_PR_FILE_PATH')
        need(self.fresh_pr(number).get('changed_files')==expected, 'PR_FILE_SCOPE_CHANGED')
        return rows

    def commit(self,sha):
        need(isinstance(sha,str) and SHA.fullmatch(sha), 'INVALID_REVISION')
        value=self._get(f'{REPO}/commits/{sha}')
        need(isinstance(value,dict) and value.get('sha')==sha, 'COMMIT_IDENTITY_MISMATCH')
        return value

    def branch_deleted(self,branch):
        need(isinstance(branch,str) and re.fullmatch(r'wp/[A-Za-z0-9_./-]+',branch) and '..' not in branch, 'INVALID_PR_BRANCH')
        refs=self._get(f'{REPO}/git/matching-refs/heads/{branch}')
        need(isinstance(refs,list) and not any(r.get('ref')=='refs/heads/'+branch for r in refs), 'MERGED_BRANCH_NOT_DELETED')

    def fresh_run(self,number):
        need(type(number) is int and 0<number<10**18, 'INVALID_RUN')
        self.cache.pop(f'{REPO}/actions/runs/{number}',None)
        return self.run(number)

    def technical_ci(self,sha,policy,extra=()):
        checks,_=self.checks(sha)
        required=policy.get('required_technical_steps',[])
        need(isinstance(required,list) and required and all(isinstance(x,str) for x in required), 'TECHNICAL_CI_POLICY_MISSING')
        selected=[c for c in checks if c.get('name') in policy['required_ci']]
        need(selected, 'TECHNICAL_CI_RUN_EVIDENCE_MISSING')
        runs=set()
        for check in selected:
            match=re.fullmatch(r'https://github\.com/Asperant/critical-aerospace-manufacturing/actions/runs/([1-9][0-9]*)/job/[1-9][0-9]*',check.get('details_url',''),re.I)
            need(match, 'TECHNICAL_CI_RUN_BINDING_UNKNOWN')
            runs.add(int(match[1]))
        for number in sorted(runs):
            run=self.run(number)
            need(run.get('head_sha')==sha and run.get('status')=='completed' and run.get('conclusion')=='success', 'TECHNICAL_CI_RUN_NOT_GREEN')
            jobs=self._get(f'{REPO}/actions/runs/{number}/jobs?filter=latest&per_page=100')
            rows=jobs.get('jobs',[])
            need(jobs.get('total_count')==len(rows), 'INCOMPLETE_CI_JOB_EVIDENCE')
            selected_jobs=[j for j in rows if j.get('name') in policy['required_ci']]
            need(selected_jobs, 'TECHNICAL_CI_JOB_MISSING')
            for job in selected_jobs:
                need(job.get('head_sha')==sha and job.get('status')=='completed' and job.get('conclusion')=='success', 'TECHNICAL_CI_JOB_BINDING_UNKNOWN')
                steps={step['name']:step for step in job.get('steps',[])}
                for name in set(required)|set(extra):
                    step=steps.get(name,{})
                    need(step.get('status')=='completed' and step.get('conclusion')=='success', 'REQUIRED_TECHNICAL_STEP_NOT_PASSED')

    def current_main(self,pr):
        sha=pr['head']['sha']
        need(SHA.fullmatch(sha), 'INVALID_REVISION')
        comparison=self._get(f'{REPO}/compare/main...{sha}')
        need(comparison.get('behind_by')==0, 'PR_BEHIND_CURRENT_MAIN')

    def merged_shape(self,pr):
        branch=pr['head']['ref']
        need(isinstance(branch,str) and re.fullmatch(r'wp/[A-Za-z0-9_./-]+',branch) and '..' not in branch, 'INVALID_PR_BRANCH')
        refs=self._get(f'{REPO}/git/matching-refs/heads/{branch}')
        need(isinstance(refs,list) and not any(r.get('ref')=='refs/heads/'+branch for r in refs), 'MERGED_BRANCH_NOT_DELETED')
        sha=pr['merge_commit_sha']
        need(isinstance(sha,str) and SHA.fullmatch(sha), 'INVALID_MERGE_COMMIT')
        commit=self._get(f'{REPO}/commits/{sha}')
        need(len(commit.get('parents',[]))==1, 'NON_SQUASH_MERGE_SHAPE')

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

    def repository_file(self, path, sha, limit=65536):
        need(isinstance(path,str) and re.fullmatch(r'[A-Za-z0-9_./-]+',path)
             and not path.startswith('/') and all(p not in {'','.','..'} for p in path.split('/'))
             and SHA.fullmatch(sha), 'INVALID_ARTIFACT_PATH')
        value=self._get(f'{REPO}/contents/{path}?ref={sha}')
        need(isinstance(value,dict) and value.get('type')=='file' and value.get('encoding')=='base64'
             and 0 < value.get('size',0) <= limit and SHA.fullmatch(value.get('sha','')), 'ARTIFACT_NOT_A_FILE')
        raw=base64.b64decode(value.get('content',''))
        need(0 < len(raw) <= limit, 'ARTIFACT_CONTENT_UNAVAILABLE')
        return raw,value['sha']

    def ancestor(self, base, head):
        need(SHA.fullmatch(base or '') and SHA.fullmatch(head or ''), 'INVALID_REVISION')
        value=self._get(f'{REPO}/compare/{base}...{head}')
        need(value.get('status') in {'ahead','identical'} and value.get('behind_by')==0,
             'PRODUCER_MERGE_NOT_IN_MAIN_ANCESTRY')

    def evidence_text(self,path,sha):
        # Only immutable repository evidence, never user URLs or executable code.
        need(isinstance(path,str) and path.startswith(('evidence/','09_change/','project_control/'))
             and path.endswith('.md'), 'INVALID_ASSESSMENT_PATH')
        self.artifact('repo:'+path,sha)
        value=self._get(f'{REPO}/contents/{path}?ref={sha}')
        need(value.get('encoding')=='base64' and value.get('size',0)<=65536, 'ASSESSMENT_CONTENT_UNAVAILABLE')
        raw=base64.b64decode(value.get('content',''))
        need(len(raw)<=65536, 'EVIDENCE_TOO_LARGE')
        return raw.decode('utf-8')


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

    def refresh_items(self):
        """Re-read the project's issue list (a fresh queue snapshot); never writes."""
        self.items = self.reader.rows('issues/')
        return self.items

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


def artifact_refs(text):
    # A sentence-ending full stop is prose, not part of a bare repo:path token.
    # Explicit code spans and Markdown destinations keep their literal paths.
    literals=[m.span() for m in re.finditer(r'(?P<ticks>`+).*?(?P=ticks)',text,re.S)]
    refs=[]
    for match in re.finditer(r'(?:repo:[A-Za-z0-9_./-]+|artifact:[1-9][0-9]{0,9})',text):
        ref=match.group()
        prose_end=match.end()==len(text) or text[match.end()].isspace()
        literal=any(start<=match.start()<end for start,end in literals)
        if ref.startswith('repo:') and prose_end and not literal:
            ref=ref.rstrip('.')
        refs.append(ref)
    for path in re.findall(r'\]\(([A-Za-z0-9_./-]+)(?:#[A-Za-z0-9_.-]+)?\)',text):
        if '/' in path and not path.startswith('/') and not any(p in {'','.','..'} for p in path.split('/')):
            refs.append('repo:'+path)
    return sorted(set(refs))


def evidence_digest(value):
    raw = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(raw).hexdigest()


def _automatic_runtime_readiness_attestation(gh, context, edge, sha, policy):
    """Package only immutable, allow-listed runtime SKELETON_READY evidence."""
    assert q is not None
    reasons = []

    def reject(code):
        if code not in reasons:
            reasons.append(code)

    semantics = edge.get("semantics", {})
    node = edge.get("predecessor", {}).get("node")
    successor = edge.get("successor", {}).get("node")
    wp = context.get("work_package", {}).get("id")
    producer = policy.get("node_owners", {}).get(node)
    consumer = policy.get("node_owners", {}).get(successor)
    profiles = {value[0]: profile for profile, value in q.PEOPLE.items()}
    expected_consumer = profiles.get(
        context.get("work_package", {}).get("primary_owner", {}).get("canonical_name")
    )
    if policy.get("auto_readiness_attestation_schema") != "auto-readiness-attestation-v1":
        reject("AUTO_READINESS_FEATURE_UNAVAILABLE")
    if semantics.get("kind") != "RUNTIME" or semantics.get("required_readiness") != "SKELETON_READY":
        reject("AUTO_READINESS_NOT_APPLICABLE")
    if not re.fullmatch(r"DN-[A-Z0-9-]+", node or "") or not re.fullmatch(
        r"DEP-[0-9]+", edge.get("id", "")
    ):
        reject("CANONICAL_READINESS_IDENTITY_INVALID")
    if producer not in q.PEOPLE or consumer not in q.PEOPLE or consumer != expected_consumer:
        reject("CANONICAL_READINESS_OWNERSHIP_INVALID")
    if not isinstance(edge.get("precise_requirement"), str) or not edge["precise_requirement"].strip():
        reject("PRECISE_CONSUMER_REQUIREMENT_MISSING")
    levels = policy.get("node_levels", {}).get(node, [])
    if "SKELETON_READY" not in levels:
        reject("REQUIRED_READINESS_LEVEL_INVALID")
    try:
        if gh.main_sha() != sha:
            reject("SOURCE_SHA_NOT_CURRENT_MAIN")
    except Denied as exc:
        reject(exc.code)

    basis_path = f"evidence/readiness/{node}.json"
    basis = None
    basis_blob = None
    raw = b""
    try:
        raw, basis_blob = gh.repository_file(basis_path, sha)
        basis = json.loads(raw.decode("utf-8"), object_pairs_hook=q.unique)
    except Denied as exc:
        reject("RUNTIME_READINESS_BASIS_MISSING" if exc.code in {
            "ARTIFACT_NOT_A_FILE", "ARTIFACT_CONTENT_UNAVAILABLE"
        } else exc.code)
    except (ValueError, UnicodeDecodeError, TypeError):
        reject("RUNTIME_READINESS_BASIS_INVALID")

    expected_keys = {
        "schema", "node", "level", "producer_wp", "producer_pr", "producer_merge_sha",
        "consumer_edges", "consumer_wps", "checks"
    }
    if not isinstance(basis, dict) or set(basis) != expected_keys or basis.get("schema") != "auto-runtime-readiness-basis-v1":
        reject("RUNTIME_READINESS_BASIS_INVALID")
    if isinstance(basis, dict):
        if basis.get("node") != node or basis.get("level") != "SKELETON_READY":
            reject("RUNTIME_READINESS_LEVEL_MISMATCH")
        if basis.get("producer_wp") not in policy.get("node_producers", {}).get(node, []):
            reject("PRODUCER_SCOPE_UNKNOWN")
        if basis.get("consumer_edges") != [edge.get("id")]:
            reject("CONSUMER_EDGE_BINDING_MISSING")
        if basis.get("consumer_wps", {}).get(edge.get("id")) != wp:
            reject("CONSUMER_WP_BINDING_MISSING")
        merge = basis.get("producer_merge_sha")
        producer_pr = basis.get("producer_pr")
        login = GITHUB.get(producer)
        owner = q.PEOPLE.get(producer, (None,))[0] if producer in q.PEOPLE else None
        producer_files = set()
        if not isinstance(merge, str) or not SHA.fullmatch(merge) or type(producer_pr) is not int:
            reject("PRODUCER_MERGE_BINDING_INVALID")
        else:
            try:
                pr = gh.pr(producer_pr)
                if not pr.get("merged") or pr.get("merge_commit_sha") != merge or \
                        pr.get("user", {}).get("login", "").casefold() != (login or "").casefold():
                    reject("PRODUCER_MERGE_ATTRIBUTION_INVALID")
                gh.ancestor(merge, sha)
                producer_files = {item.get("filename") for item in gh.files(pr)
                                  if item.get("status") != "removed"}
            except Denied as exc:
                reject(exc.code)
                producer_files = set()
        checks = basis.get("checks")
        if not isinstance(checks, list) or not checks:
            reject("RUNTIME_EVIDENCE_UNDECLARED")
            checks = []
        seen = {}
        observed_pass = False
        observed_health = False
        normalized = []
        for check in checks:
            if not isinstance(check, dict) or not {"path", "blob", "kind", "value"}.issubset(check):
                reject("RUNTIME_EVIDENCE_INVALID")
                continue
            path, blob, kind, value = (check.get("path"), check.get("blob"), check.get("kind"), check.get("value"))
            if kind == "json_equals" and set(check) != {"path", "blob", "kind", "field", "value"}:
                reject("RUNTIME_EVIDENCE_INVALID")
                continue
            if kind == "text_contains" and set(check) != {"path", "blob", "kind", "value"}:
                reject("RUNTIME_EVIDENCE_INVALID")
                continue
            if not isinstance(path, str) or (path in seen and seen[path] != blob) or not re.fullmatch(r"[a-f0-9]{40}", str(blob)):
                reject("RUNTIME_EVIDENCE_INVALID")
                continue
            if kind not in {"text_contains", "json_equals"}:
                reject("RUNTIME_EVIDENCE_KIND_UNSUPPORTED")
                continue
            if path not in producer_files:
                reject("RUNTIME_EVIDENCE_NOT_PRODUCER_AUTHORED")
            try:
                content, actual_blob = gh.repository_file(path, sha)
                if actual_blob != blob:
                    reject("STALE_RUNTIME_EVIDENCE_BLOB")
                if kind == "text_contains":
                    text = content.decode("utf-8")
                    if not isinstance(value, str) or not value or value not in text:
                        reject("RUNTIME_HEALTH_OR_SMOKE_NOT_PASS")
                    observed_pass |= isinstance(value, str) and "pass" in value.casefold()
                    observed_health |= isinstance(value, str) and "healthy" in value.casefold()
                else:
                    data = json.loads(content.decode("utf-8"), object_pairs_hook=q.unique)
                    field = check.get("field")
                    # The basis schema intentionally supports only bounded dotted object paths.
                    if not isinstance(field, str) or not re.fullmatch(r"[A-Za-z0-9_]+(?:\[[0-9]+\])?(?:\.[A-Za-z0-9_]+(?:\[[0-9]+\])?)*", field):
                        reject("RUNTIME_EVIDENCE_FIELD_INVALID")
                    else:
                        actual = data
                        for part in field.split("."):
                            match = re.fullmatch(r"([A-Za-z0-9_]+)(?:\[([0-9]+)\])?", part)
                            if not match or not isinstance(actual, dict) or match[1] not in actual:
                                raise KeyError(part)
                            actual = actual[match[1]]
                            if match[2] is not None:
                                if not isinstance(actual, list):
                                    raise KeyError(part)
                                actual = actual[int(match[2])]
                        if actual != value:
                            reject("RUNTIME_HEALTH_OR_SMOKE_NOT_PASS")
            except (Denied, UnicodeDecodeError, ValueError, TypeError, KeyError):
                reject("RUNTIME_EVIDENCE_UNREADABLE")
            seen[path] = blob
            normalized.append(dict(check))
        if not observed_pass or not observed_health:
            reject("RUNTIME_HEALTH_OR_SMOKE_NOT_PASS")
    else:
        merge = None
        owner = None
        login = None
        normalized = []

    if reasons:
        return {"schema": "auto-readiness-attestation-v1", "status": "UNKNOWN",
                "node": node, "level": "SKELETON_READY", "producer": producer,
                "consumer": {"edge_id": edge.get("id"), "wp_id": wp, "node": successor},
                "source_sha": sha, "reasons": reasons}
    proof = {"schema": "auto-readiness-attestation-v1", "status": "PASS", "node": node,
             "level": "SKELETON_READY", "producer": {"profile": producer, "owner": owner, "login": login},
             "consumer": {"edge_id": edge["id"], "wp_id": wp, "required_level": "SKELETON_READY"},
             "source_sha": sha, "producer_merge_sha": merge, "artifacts": normalized,
             "tests": [], "trace": [], "semantic_basis": {"path": basis_path, "blob": basis_blob}}
    proof["proof_digest"] = evidence_digest(proof)
    return proof


def automatic_readiness_attestation(gh, context, edge, sha, policy):
    """Package immutable CONTRACT or mechanical runtime readiness evidence only."""
    assert q is not None
    semantics = edge.get("semantics", {})
    if semantics.get("kind") == "RUNTIME" and semantics.get("required_readiness") == "SKELETON_READY":
        return _automatic_runtime_readiness_attestation(gh, context, edge, sha, policy)
    reasons = []

    def reject(code):
        if code not in reasons:
            reasons.append(code)

    semantics = edge.get("semantics", {})
    node = edge.get("predecessor", {}).get("node")
    successor = edge.get("successor", {}).get("node")
    wp = context.get("work_package", {}).get("id")
    producer = policy.get("node_owners", {}).get(node)
    consumer = policy.get("node_owners", {}).get(successor)
    profiles = {value[0]: profile for profile, value in q.PEOPLE.items()}
    expected_consumer = profiles.get(
        context.get("work_package", {}).get("primary_owner", {}).get("canonical_name")
    )
    if policy.get("auto_readiness_attestation_schema") != "auto-readiness-attestation-v1":
        reject("AUTO_READINESS_FEATURE_UNAVAILABLE")
    if (
        semantics.get("kind") != "CONTRACT"
        or semantics.get("required_readiness") != "CONTRACT_READY"
    ):
        reject("AUTO_READINESS_NOT_APPLICABLE")
    if not re.fullmatch(r"DN-[A-Z0-9-]+", node or "") or not re.fullmatch(
        r"DEP-[0-9]+", edge.get("id", "")
    ):
        reject("CANONICAL_READINESS_IDENTITY_INVALID")
    if (
        producer not in q.PEOPLE
        or consumer not in q.PEOPLE
        or consumer != expected_consumer
    ):
        reject("CANONICAL_READINESS_OWNERSHIP_INVALID")
    if not isinstance(edge.get("precise_requirement"), str) or not edge[
        "precise_requirement"
    ].strip():
        reject("PRECISE_CONSUMER_REQUIREMENT_MISSING")
    levels = policy.get("node_levels", {}).get(node, [])
    if "CONTRACT_READY" not in levels:
        reject("REQUIRED_READINESS_LEVEL_INVALID")
    try:
        if gh.main_sha() != sha:
            reject("SOURCE_SHA_NOT_CURRENT_MAIN")
    except Denied as exc:
        reject(exc.code)
    basis_path = f"evidence/readiness/{node}.json" if isinstance(node, str) else ""
    basis = None
    basis_blob = None
    raw = b""
    try:
        raw, basis_blob = gh.repository_file(basis_path, sha)
        basis = json.loads(raw.decode("utf-8"), object_pairs_hook=q.unique)
    except Denied as exc:
        reject(
            "SEMANTIC_BASIS_MISSING"
            if exc.code in {"ARTIFACT_NOT_A_FILE", "ARTIFACT_CONTENT_UNAVAILABLE"}
            else exc.code
        )
    except (ValueError, UnicodeDecodeError, TypeError):
        reject("SEMANTIC_BASIS_INVALID")
    if not isinstance(basis, dict):
        reject("SEMANTIC_BASIS_MISSING")
        reject("CONTRACT_ARTIFACTS_UNDECLARED")
        reject("TEST_EVIDENCE_UNDECLARED")
        reject("TRACE_EVIDENCE_UNDECLARED")
        return {
            "schema": "auto-readiness-attestation-v1",
            "status": "UNKNOWN",
            "node": node,
            "level": "CONTRACT_READY",
            "consumer": {"edge_id": edge.get("id"), "wp_id": wp, "node": successor},
            "source_sha": sha,
            "reasons": reasons,
        }
    expected_keys = {
        "schema", "node", "level", "producer", "producer_wp", "producer_pr",
        "producer_merge_sha", "scope_projections", "certification", "semantic_basis",
        "consumer_edges", "artifacts", "tests", "trace",
    }
    if set(basis) != expected_keys or basis.get("schema") != "auto-readiness-semantic-basis-v1":
        reject("SEMANTIC_BASIS_SCHEMA_INVALID")
    if basis.get("node") != node or basis.get("level") != "CONTRACT_READY":
        reject("SEMANTIC_BASIS_NODE_OR_LEVEL_MISMATCH")
    negative = r"(?is)(?:does\s+not|not|no)\s+(?:declare|certif\w*)?\s*CONTRACT_READY"
    if basis.get("certification") != "CONTRACT_READY" or re.search(
        negative, raw.decode("utf-8", "replace")
    ):
        reject("EXPLICIT_NON_CERTIFICATION")
    owner = q.PEOPLE.get(producer, (None,))[0] if producer in q.PEOPLE else None
    login = GITHUB.get(producer)
    if basis.get("producer") != {"owner": owner, "login": login}:
        reject("PRODUCER_ATTRIBUTION_MISMATCH")
    producer_wps = policy.get("node_producers", {}).get(node, [])
    if (
        not isinstance(producer_wps, list)
        or not producer_wps
        or basis.get("producer_wp") not in producer_wps
    ):
        reject("PRODUCER_SCOPE_UNKNOWN")
    scope = basis.get("scope_projections")
    if not isinstance(scope, dict) or set(scope) != set(producer_wps):
        reject("PRODUCER_SCOPE_PROJECTION_MISMATCH")
    else:
        for producer_wp in producer_wps:
            projection = policy.get("scope_projections", {}).get(producer_wp)
            if projection is None or scope.get(producer_wp) != evidence_digest(projection):
                reject("PRODUCER_SCOPE_PROJECTION_MISMATCH")
    judgment = basis.get("semantic_basis")
    semantic_fields = {
        "stability", "consumer_usability", "compatibility_intent", "scope_meaning"
    }
    if (
        not isinstance(judgment, dict)
        or set(judgment) != semantic_fields
        or any(
            not isinstance(judgment.get(key), str)
            or not judgment[key].strip()
            or re.match(r"^(?:UNKNOWN|TBD|TODO|PENDING)\b", judgment[key], re.I)
            for key in semantic_fields
        )
    ):
        reject("ATTRIBUTABLE_SEMANTIC_BASIS_MISSING")
    normalized_judgment = judgment if isinstance(judgment, dict) else {}
    edges = basis.get("consumer_edges")
    if (
        not isinstance(edges, list)
        or edge.get("id") not in edges
        or len(edges) != len(set(edges))
    ):
        reject("CONSUMER_EDGE_BINDING_MISSING")
    merge = basis.get("producer_merge_sha")
    pr_number = basis.get("producer_pr")
    if not isinstance(merge, str) or not SHA.fullmatch(merge) or type(pr_number) is not int:
        reject("PRODUCER_MERGE_BINDING_INVALID")
    else:
        try:
            pr = gh.pr(pr_number)
            author = pr.get("user", {}).get("login", "")
            if (
                not pr.get("merged")
                or pr.get("merge_commit_sha") != merge
                or author.casefold() != (login or "").casefold()
            ):
                reject("PRODUCER_MERGE_ATTRIBUTION_INVALID")
            files = gh.files(pr)
            authored = {
                item.get("filename") for item in files if item.get("status") != "removed"
            }
            if basis_path not in authored:
                reject("SEMANTIC_BASIS_NOT_PRODUCER_AUTHORED")
            gh.ancestor(merge, sha)
        except Denied as exc:
            reject(exc.code)
    normalized = {}
    for field, roles in [
        ("artifacts", {"contract", "schema", "fixture"}),
        ("tests", None),
        ("trace", None),
    ]:
        rows = basis.get(field)
        if not isinstance(rows, list) or not rows:
            reject(field.upper() + "_EVIDENCE_UNDECLARED")
            continue
        seen = set()
        normalized[field] = []
        for row in rows:
            if field == "artifacts":
                required = {"path", "blob", "role"}
            elif field == "tests":
                required = {"test_id", "check", "path", "blob"}
            else:
                required = {"requirement", "path", "blob"}
            if not isinstance(row, dict) or set(row) != required or row.get("path") in seen:
                reject(field.upper() + "_EVIDENCE_INVALID")
                continue
            if (
                field == "tests"
                and (
                    not re.fullmatch(r"TEST-[A-Z0-9-]+", row.get("test_id", ""))
                    or not isinstance(row.get("check"), str)
                    or not row["check"].strip()
                )
            ):
                reject("TEST_EVIDENCE_INVALID")
                continue
            if field == "trace" and not re.fullmatch(
                r"(?:FR|NFR)-[A-Z0-9]+-[0-9]{3}", row.get("requirement", "")
            ):
                reject("TRACE_EVIDENCE_INVALID")
                continue
            seen.add(row["path"])
            try:
                _, blob = gh.repository_file(row["path"], sha)
                if blob != row.get("blob"):
                    reject("STALE_" + field.upper() + "_BLOB")
            except Denied as exc:
                reject(exc.code)
                continue
            normalized[field].append(row)
        if roles is not None and {row.get("role") for row in rows} != roles:
            reject("CONTRACT_ARTIFACT_ROLES_INCOMPLETE")
    required_trace = set(policy.get("node_requirements", {}).get(node, []))
    if isinstance(basis.get("trace"), list) and {
        row.get("requirement") for row in basis["trace"] if isinstance(row, dict)
    } != required_trace:
        reject("TRACE_REQUIREMENT_COVERAGE_MISMATCH")
    checks = []
    try:
        checks, _ = gh.checks(sha)
    except Denied as exc:
        reject(exc.code)
    required_checks = set(policy.get("required_ci", [])) | set(
        policy.get("required_aggregate_ci", [])
    )
    if isinstance(basis.get("tests"), list):
        required_checks |= {
            row.get("check") for row in basis["tests"] if isinstance(row, dict)
        }
    for name in sorted(required_checks):
        matches = [check for check in checks if check.get("name") == name]
        if (
            len(matches) != 1
            or matches[0].get("head_sha", sha) != sha
            or matches[0].get("status") != "completed"
            or matches[0].get("conclusion") != "success"
        ):
            reject("SHA_BOUND_REQUIRED_TEST_NOT_GREEN")
    if reasons:
        return {
            "schema": "auto-readiness-attestation-v1",
            "status": "UNKNOWN",
            "node": node,
            "level": "CONTRACT_READY",
            "producer": producer,
            "consumer": {"edge_id": edge.get("id"), "wp_id": wp, "node": successor},
            "source_sha": sha,
            "reasons": reasons,
        }
    proof = {
        "schema": "auto-readiness-attestation-v1",
        "status": "PASS",
        "node": node,
        "level": "CONTRACT_READY",
        "producer": {"profile": producer, "owner": owner, "login": login},
        "consumer": {
            "edge_id": edge["id"], "wp_id": wp, "node": successor,
            "required_level": "CONTRACT_READY",
        },
        "source_sha": sha,
        "producer_merge_sha": merge,
        "policy_digest": policy["policy_digest"],
        "artifacts": normalized["artifacts"],
        "tests": normalized["tests"],
        "trace": normalized["trace"],
        "semantic_basis": dict(
            normalized_judgment, path=basis_path, blob=basis_blob, author=login
        ),
    }
    proof["proof_digest"] = evidence_digest(proof)
    return proof


def existing_assessment(gh,text,wp,sha):
    # The accountable author can refer to an already committed evidence assessment instead
    # of copying it into a new comment. One bounded hop; attribution stays GitHub's.
    link_text='\n'.join(line for line in text.splitlines() if not re.search(r'(?:DOR|DOD)-[A-Z]+-[0-9]{2}|docs/08#|BLOCKER-(?:OBSERVED|RESOLVED)|DEP-[0-9]+|(?:IMPLEMENTATION|POST-MERGE-VALIDATION)-STARTED',line))
    paths=[r[5:] for r in artifact_refs(link_text) if r.startswith('repo:') and r.endswith('.md')
           and r[5:].startswith(('evidence/','09_change/','project_control/'))]
    need(len(paths)<=8, 'TOO_MANY_ASSESSMENTS')
    record=native_record(text,wp,sha)
    for path in paths:
        linked=native_record(gh.evidence_text(path,sha),wp,sha)
        for key in ('checks','dependency_readiness','dependency_stage_dispositions'):
            need(not set(record[key]) & set(linked[key]), 'AMBIGUOUS_SEMANTIC_EVIDENCE')
            record[key].update(linked[key])
        record['_artifact_refs']=sorted(set(record['_artifact_refs']+linked['_artifact_refs']))
        for key in ('owner_decision','blocker','resolves_audit_id'):
            if linked.get(key):
                need(not record.get(key), 'AMBIGUOUS_SEMANTIC_EVIDENCE')
                record[key]=linked[key]
    return record


def native_record(text, wp, sha):
    """Read existing Markdown evidence, without a transition-specific JSON schema.

    Canonical criterion tables/checklists retain their own IDs and linked evidence.
    Unstructured prose is never guessed into PASS. The caller supplies attribution
    and immutable revision from GitHub, not from stdin.
    """
    need(isinstance(text,str) and len(text)<=65536, 'EVIDENCE_TOO_LARGE')
    data={'wp_id':wp, 'head_sha':sha, 'reason':'Existing GitHub assessment',
          '_native':True, '_artifact_refs':artifact_refs(text), 'checks':{}, 'dependency_readiness':{}, 'dependency_stage_dispositions':{}}
    def field(label):
        values=re.findall(r'(?im)^\s*(?:[-*]\s+)?(?:\*\*)?'+re.escape(label)+r'(?:\*\*)?\s*:\s*(.+?)\s*$',text)
        need(len(values)<=1, 'AMBIGUOUS_SEMANTIC_EVIDENCE')
        return values[0].strip(' *`') if values else None
    for line in text.splitlines():
        cells=[c.strip(' `') for c in line.strip().strip('|').split('|')]
        checked=re.match(r'^\s*[-*] \[x\]\s+(\S+)\s+(.*)',line,re.I)
        if checked: cells=[checked[1].rstrip(':'),'PASS',checked[2]]
        if len(cells)<3: continue
        identity,result=cells[:2]
        if result not in {'PASS','N/A'}: continue
        refs=artifact_refs(' '.join(cells[2:]))
        if re.fullmatch(r'(?:DOR|DOD)-[A-Z]+-[0-9]{2}|docs/08#[0-9]+:[A-Z0-9-]+|BLOCKER-(?:OBSERVED|RESOLVED)',identity):
            need(identity not in data['checks'], 'AMBIGUOUS_SEMANTIC_EVIDENCE')
            data['checks'][identity]={'result':result,'reason':' '.join(cells[2:]),'evidence_refs':refs}
    # Ordinary project-owner decisions and blocker notes; no policy/from/to copy.
    data['reason']=field('Reason') or text[:1000]
    data['owner_decision']=field('Owner decision')
    blocker_owner=field('Blocker owner')
    if blocker_owner:
        data['blocker']={'owner':blocker_owner,'wp_id':field('Blocking WP'),
                         'external_dependency':field('External dependency')}
    data['resolves_audit_id']=field('Resolves blocker')
    # Existing dependency assessment tables: DEP-ID | readiness | consumer/evidence.
    for line in text.splitlines():
        cells=[c.strip(' `') for c in line.strip().strip('|').split('|')]
        if len(cells)>=3 and re.fullmatch(r'DEP-[0-9]+',cells[0]):
            need(cells[0] not in data['dependency_readiness'] and cells[0] not in data['dependency_stage_dispositions'], 'AMBIGUOUS_SEMANTIC_EVIDENCE')
            if cells[1]=='NOT_APPLICABLE':
                data['dependency_stage_dispositions'][cells[0]]={'applies_to_wp_completion':False,
                    'reason':' '.join(cells[2:]),'evidence_refs':artifact_refs(' '.join(cells[2:]))}
                continue
            data['dependency_readiness'][cells[0]]={'readiness':cells[1],
                'precise_consumer_requirement':' '.join(cells[2:]),
                'evidence_refs':artifact_refs(' '.join(cells[2:]))}
    return data


def records(gh, refs, wp=None, sha=None, pr=None):
    """Existing PR description or explicitly referenced technical evidence comments.

    Legacy JSON remains readable, but is never required. Native comments must
    explicitly name the canonical WP and immutable revision; PR bodies inherit
    GitHub's actual revision. Review APIs are not consulted. Ambiguous/missing judgments still fail closed.
    """
    result=[]
    for ref in refs:
        kind, number=ref.split(':')
        if kind!='comment': continue
        comment=gh.comment(int(number))
        text=comment.get('body','')
        need(isinstance(text,str) and len(text)<=65536, 'EVIDENCE_TOO_LARGE')
        try: body=json.loads(text, object_pairs_hook=q.unique)
        except (ValueError,TypeError): body=None
        if isinstance(body,dict) and set(body)=={'cap_plane_transition'}:
            need(isinstance(body['cap_plane_transition'],dict), 'INVALID_CONFIRMATION_RECORD')
            data=body['cap_plane_transition']
        elif wp and sha and wp in text and sha in text:
            if pr: need(comment.get('issue_url','').endswith('/issues/'+str(pr['number'])), 'EVIDENCE_WRONG_PR')
            data=existing_assessment(gh,text,wp,sha)
        else: continue
        result.append((comment.get('user',{}).get('login',''),dict(data,_recorded_at=comment.get('updated_at') or comment.get('created_at'))))
    if pr:
        result.append((pr['user']['login'],dict(existing_assessment(gh,pr.get('body') or '',wp,sha),_recorded_at=pr.get('updated_at'))))
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
    required=set(policy['required_ci'])|set(policy.get('required_aggregate_ci',[]))
    selected=[c for c in checks if c.get('name') in required]
    statuses=[v for v in statuses if v.get('context') in required]
    need(selected or statuses, 'CI_EVIDENCE_MISSING')
    need(required<=({c['name'] for c in selected}|{v['context'] for v in statuses}), 'REQUIRED_CI_MISSING')
    need(all(c.get('status')=='completed' and c.get('conclusion')=='success' for c in selected), 'CI_NOT_GREEN')
    need(all(v.get('state')=='success' for v in statuses), 'COMMIT_STATUS_NOT_GREEN')
    gh.technical_ci(sha,policy)


def confirmation(rows, authors, wp, source, target, sha, policy):
    # Native evidence is bound by GitHub attribution/revision and canonical IDs.
    # No digest/source_manifest/from/to duplication into an extra comment.
    candidates=[(author,data) for author,data in rows if author.casefold() in {a.casefold() for a in authors}
                and data.get('wp_id')==wp and data.get('head_sha')==sha]
    native=[dict(data,_confirming_login=author) for author,data in candidates if data.get('_native') and
            (data.get('checks') or data.get('owner_decision') or data.get('dependency_readiness') or data.get('blocker') or data.get('resolves_audit_id'))]
    legacy=[dict(data,_confirming_login=author) for author,data in candidates if not data.get('_native')
            and data.get('from_state')==source and data.get('to_state')==target
            and data.get('source_manifest')==policy['source_manifest'] and data.get('policy_digest')==policy['policy_digest']]
    matches=native or legacy
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


def blocker_evidence(gh,record,criterion,sha):
    if record.get('_native'):
        safe_text(record.get('reason'))
        refs=record.get('_artifact_refs',[])
        need(refs, 'BLOCKER_EVIDENCE_MISSING')
        for ref in refs: gh.artifact(ref,sha)
    else:
        criteria(gh,record,[criterion],sha)  # Optional legacy assessment.


def dependencies(gh, rows, context, record, sha, policy, final=False):
    for edge in context['dependency_edges']:
        semantics=edge['semantics']
        if semantics['strength']!='HARD' or not final and semantics['blocking_stage']!='START': continue
        if final and semantics['blocking_stage'] in {'MILESTONE_EXIT','FREEZE'}:
            # A milestone/freeze gate is not automatically a WP closure gate.
            # Its applicability requires actual accountable-owner assessment/evidence, not a reviewer.
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
                 if author.casefold()==GITHUB[producer].casefold() and data.get('wp_id')==context['work_package']['id']
                 and data.get('head_sha')==sha and (data.get('_native') or
                 data.get('source_manifest')==policy['source_manifest'] and data.get('policy_digest')==policy['policy_digest'])]
        matches=[m for m in matches if isinstance(m,dict)]
        need(len(matches)<=1,'DEPENDENCY_READINESS_AMBIGUOUS')
        if not matches:
            automatic=automatic_readiness_attestation(
                gh,context,edge,gh.main_sha(),policy
            )
            need(automatic.get('status')=='PASS', automatic.get('reasons',['DEPENDENCY_READINESS_UNKNOWN'])[0])
            continue
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


def pr_scope_paths(files):
    """Reject unsafe, secret or runtime paths in a complete PR file inventory."""
    for file in files:
        path=file.get('filename','')
        need(isinstance(path,str) and path and not path.startswith('/') and '..' not in path.split('/'), 'INVALID_PR_SCOPE_PATH')
        if file.get('status')!='removed':
            need(not path.startswith('project_control/local/') and
                 not any(part in {'.venv','__pycache__','.pytest_cache'} or part.endswith('.egg-info') for part in path.split('/'))
                 and path.rsplit('/',1)[-1] not in {'.env','plane.env','id_rsa','id_ed25519'}, 'PR_SECRET_OR_RUNTIME_PATH')


def pr_governance(gh,pr,wp,context,policy):
    """Check native PR scope/DoR-PR/pre-merge DoD declarations and real artifacts.

    Semantic assertions remain attributable to the real author, not manufactured
    by CI. This is neither WP acceptance nor a replacement for post-merge DoD.
    """
    body=pr.get('body') or ''
    need(set(re.findall(r'(?<![A-Z0-9-])'+q.WP.pattern+r'(?![A-Z0-9-])',pr.get('title','')))=={wp}, 'PR_SCOPE_IDENTITY_AMBIGUOUS')
    groups=[('wp/control id',),('plane reference',),('requirements',),
            ('architecture surfaces and authority boundaries',),('change class',),
            ('contract/compatibility and migration impact','contract/compatibility','contract impact'),
            ('security/authority and dataset/model impact','security/authority'),('observability impact',),
            ('commands, environment and actual results',),('negative/failure paths exercised',),
            ('evidence paths and identity bindings',),('post-merge validation plan',),
            ('rollout/rollback notes',),('known limitations',),('docs impact',),('trace updates',)]
    fields={}
    current=None
    for line in body.splitlines():
        match=re.match(r'^\s*(?:\*\*)?([^:]+):(?:\*\*)?\s*(.*)$',line)
        label=match[1].strip(' *').casefold() if match else ''
        if match and any(label.startswith(alias) for group in groups for alias in group):
            need(label not in fields, 'PR_DECLARATION_AMBIGUOUS')
            fields[label]=match[2].strip(' *')
            current=label
        elif line.startswith('#'):
            current=None
        elif current and line.strip():
            fields[current]+=' '+line.strip()
    found={}
    for group in groups:
        values=[value for label,value in fields.items() if any(label.startswith(alias) for alias in group)]
        need(len(values)==1 and values[0] and not re.match(r'^(?:TODO|TBD|UNKNOWN|PENDING)\b',values[0],re.I),
             'PR_DOR_DOD_DECLARATION_MISSING')
        found[group[0]]=values[0]
    need(set(re.findall(r'(?<![A-Z0-9-])'+q.WP.pattern+r'(?![A-Z0-9-])',found['wp/control id']))=={wp}, 'PR_SCOPE_IDENTITY_AMBIGUOUS')
    need(re.search(r'^## Summary\s*$',body,re.M) and re.search(r'\bC[0-3]\b',found['change class']), 'PR_SCOPE_OR_CHANGE_CLASS_MISSING')
    for identity in context['work_package'].get('requirement_refs') or []:
        need(re.search(r'(?<![A-Z0-9-])'+re.escape(identity)+r'(?![A-Z0-9-])',found['requirements']), 'PR_REQUIREMENT_SCOPE_MISSING')
    need(re.search(r'no secrets|secret.*(?:clean|no findings|checked)|checked for secrets',body,re.I), 'PR_SELF_REVIEW_MISSING')
    refs=artifact_refs(found['evidence paths and identity bindings'])
    need(refs, 'PR_EVIDENCE_ARTIFACTS_MISSING')
    for ref in refs: gh.artifact(ref,pr['head']['sha'])
    files=gh.files(pr)
    pr_scope_paths(files)
    if any(f['filename'].startswith('tools/host/plane-') for f in files):
        gh.technical_ci(pr['head']['sha'],policy,('Host Plane queue security tests (offline)',
                         'Plane transition policy tests (offline fixtures only)'))


def policy_checks(policy):
    data=policy.get('review_policy',{})
    need(data.get('policy_id')=='DEV-REVIEW-2026-10-15-FINAL'
         and data.get('scope')=='development_github_repository_only'
         and type(data.get('required_human_approvals')) is int and data['required_human_approvals']==0
         and data.get('review_mode')=='ADVISORY'
         and data.get('review_state_is_workflow_input') is False
         and data.get('reviewer_presence_required') is False
         and data.get('product_hitl_unchanged') is True, 'REVIEW_POLICY_CONFLICT')


def evaluate(profile,wp,source,target,item,plane,policy,gh,envelope,previous=None,projection=None):
    policy_checks(policy)
    context=policy['contexts'][wp]
    card=own(item,profile,wp,policy)
    need(source!='CANCELED' or target=='UNBLOCKED', 'CANCELED_IS_TERMINAL')
    need(source!='DONE' or target in {'VALIDATING','UNBLOCKED'}, 'DONE_REQUIRES_STALENESS_REOPEN')
    need(target in {'BLOCKED','UNBLOCKED','CANCELED'} or FORWARD.get(source)==target or (source,target) in REWORK,
         'INVALID_CANONICAL_TRANSITION')
    blocked=plane.blocked in item['labels']
    need(not blocked or target in {'BLOCKED','UNBLOCKED','CANCELED'}, 'ACTIVE_BLOCKER_UNRESOLVED')
    refs=envelope['evidence_refs']
    # Planning/blocker/cancellation evidence may precede an implementation PR.
    # Requiring code before READY would invert the canonical DoR gate.
    prework=target in {'READY','BLOCKED','UNBLOCKED','CANCELED'}
    commits=[r.split(':')[1] for r in refs if r.startswith('commit:')]
    starting_commit=target=='IN_PROGRESS' and source=='READY' and len(commits)==1
    pr=pr_fact(gh,refs,wp,profile) if not prework and not starting_commit or any(r.startswith('pr:') for r in refs) else None
    post=source in {'MERGED','VALIDATING','DONE'} or target=='MERGED'
    sha=(pr.get('merge_commit_sha') if post else pr['head']['sha']) if pr else (commits[0] if starting_commit else gh.main_sha())
    need(isinstance(sha,str) and SHA.fullmatch(sha), 'REVISION_UNAVAILABLE')
    if post and pr: need(pr.get('merged') is True, 'PR_NOT_ACTUALLY_MERGED')
    owner=GITHUB[profile]
    # Only semantic operations/readiness actually consume assessment records.
    start_dependencies=target=='IN_PROGRESS' and any(
        e['semantics']['strength']=='HARD' and e['semantics']['blocking_stage']=='START'
        for e in context['dependency_edges'])
    rows=records(gh,refs,wp,sha,pr) if target in {'READY','BLOCKED','UNBLOCKED','CANCELED','DONE'} or source=='DONE' or start_dependencies else []
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
        blocker_evidence(gh,record,'BLOCKER-OBSERVED',sha)
        return {'blocker':{'owner':blocker['owner'],'wp_id':linked,
                'external_dependency':q.clean(blocker.get('external_dependency',''))}}
    if target=='UNBLOCKED':
        need(previous and previous.get('result')=='VERIFIED' and previous.get('operation')=='BLOCKED', 'BLOCKER_HISTORY_MISSING')
        # A resolution can be corroborated by an actual successful validation run,
        # or by actual post-block owner resolution evidence; no reviewer quota.
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
        record=confirmation(rows,[owner],wp,source,target,sha,policy)
        # Server-attributed resolution after the blocker, or an actual fresh run;
        # another person's review/presence is never required.
        need(automated or resolved_after_block({'updated_at':record.get('_recorded_at')}), 'BLOCKER_RESOLUTION_NOT_FRESH')
        need(record.get('resolves_audit_id')==previous['audit_id'], 'WRONG_BLOCKER_RESOLUTION')
        blocker_evidence(gh,record,'BLOCKER-RESOLVED',sha)
        return {'resolves_audit_id':previous['audit_id']}
    if target=='READY':
        need(context['cycle_ids'], 'UNSCHEDULED_WORK_NEEDS_PLANNING_DECISION')
        need(not any(r['id']!=item['id'] and r.get('assignees')==[q.PEOPLE[profile][1]] and
                     r.get('state')==plane.states['READY'] for r in plane.items), 'ANOTHER_READY_WP_EXISTS')
        if not rows and policy.get('preparation_schema') == 'cap-preparation-v1':
            spec=importlib.util.spec_from_file_location('cap_preparation_ready','/usr/local/libexec/cap-preparation.py')
            assert spec is not None and spec.loader is not None
            prep=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(prep)
            record=prep.verified_record(sys.modules[__name__],gh,wp,sha,policy)
        else:
            record=confirmation(rows,[owner],wp,source,target,sha,policy)
        criteria(gh,record,policy['dor_task']+card['dor_refs'],sha)
        dependencies(gh,rows,context,record,sha,policy)
    elif target=='IN_PROGRESS':
        if starting_commit: gh.started_commit(wp,sha,profile)
        else: need(not pr.get('merged') and pr.get('state')=='open', 'NO_LIVE_IMPLEMENTATION_PR')
        if source=='IN_REVIEW': need(pr.get('draft') is True, 'REWORK_REQUIRES_DRAFT_PR')
        active=[r for r in plane.items if r.get('assignees')==[q.PEOPLE[profile][1]] and
                r.get('state')==plane.states['IN_PROGRESS'] and r['id']!=item['id']]
        if active:
            try:
                auto=auto_next_support()
                resolver=auto.load_resolver()
                live=auto.live_view(sys.modules[__name__],plane,policy,profile,gh)
                need(live.get('complete') is True, 'WIP_LIVE_VIEW_INCOMPLETE')
                # Only a fresh, positively verified released wait frees a slot.
                # Missing/invalid/UNKNOWN evidence keeps the original active set.
                active=[r for r in active if resolver.released_wait(
                    r['external_id'],live['items'][r['external_id']]) is None]
            except Exception:
                pass
        need(len(active)<2, 'IMPLEMENTATION_WIP_LIMIT')
        def heavy(identity):
            c=policy['contexts'][identity]['work_package']
            band=re.fullmatch(r'([SML])(?: \(.*\))?',c.get('size_band') or '')
            need(band is not None, 'WORKLOAD_CLASS_UNKNOWN')
            return band.group(1)=='L' or identity.startswith('WP-CORE-')
        if heavy(wp): need(not any(heavy(r.get('external_id','')) for r in active), 'HEAVY_CORE_WIP_LIMIT')
        # An actual changed WP branch/PR proves work started; no extra event comment.
        dependencies(gh,rows,context,{},sha,policy)
    elif target=='IN_REVIEW':
        need(pr.get('state')=='open' and not pr.get('draft') and not pr.get('merged'), 'REAL_REVIEWABLE_PR_REQUIRED')
        ci(gh,sha,policy)
        if source=='MERGE_READY':
            need(projection and projection.get('result')=='VERIFIED' and projection.get('operation')=='MERGE_READY'
                 and isinstance(projection.get('observed_pr_head'),str)
                 and SHA.fullmatch(projection['observed_pr_head']) and projection['observed_pr_head']!=sha,
                 'TECHNICAL_REWORK_REVISION_UNKNOWN')
    elif target=='MERGE_READY':
        need(not pr.get('draft') and not pr.get('merged'), 'REAL_REVIEWABLE_PR_REQUIRED')
        ci(gh,sha,policy)
        need(pr.get('state')=='open', 'REAL_REVIEWABLE_PR_REQUIRED')
        pr_governance(gh,pr,wp,context,policy)
        need(pr.get('mergeable') is True, 'PR_NOT_MERGE_READY')
        gh.current_main(pr)
    elif target=='MERGED':
        need(pr.get('merged') is True and pr.get('base',{}).get('ref')=='main', 'PR_NOT_ACTUALLY_MERGED')
        ci(gh,pr['head']['sha'],policy)
        gh.merged_shape(pr)
        pr_governance(gh,pr,wp,context,policy)
    elif target=='VALIDATING':
        if source=='DONE':
            record=confirmation(rows,[owner],wp,source,target,sha,policy)
            criteria(gh,record,['docs/08#11:EVIDENCE-STALE'],sha)
        runs=[gh.run(int(r.split(':')[1])) for r in refs if r.startswith('run:')]
        need(any(r.get('head_sha')==sha and r.get('head_branch')=='main' and r.get('status')=='in_progress'
                 and r.get('event')!='pull_request' for r in runs), 'POST_MERGE_VALIDATION_NOT_RUNNING')
    elif target=='DONE':
        ci(gh,sha,policy)
        gh.merged_shape(pr)
        owner_record=confirmation(rows,[owner],wp,source,target,sha,policy)
        ids=sorted(set(policy['dod_wp']+card['dod_refs']+context['scope_criteria']))
        if card.get('scope_class')=='R1': ids+=policy['dod_research']
        criteria(gh,owner_record,ids,sha)
        pr_governance(gh,pr,wp,context,policy)
        dependencies(gh,rows,context,owner_record,sha,policy,final=True)
        runs=[gh.run(int(r.split(':')[1])) for r in refs if r.startswith('run:')]
        need(any(r.get('head_sha')==sha and r.get('head_branch')=='main' and r.get('status')=='completed'
                 and r.get('conclusion')=='success' and r.get('event')!='pull_request' for r in runs), 'POST_MERGE_VALIDATION_NOT_PASSED')

    if pr: return {'observed_pr_head':pr['head']['sha'],'observed_pr_number':pr['number'],
                   'pr_facts':pr_facts(pr)}


def pr_facts(pr):
    return {'head':pr['head']['sha'],'branch':pr['head']['ref'],'base':pr['base']['ref'],
            'draft':pr.get('draft'),'state':pr.get('state'),'merged':pr.get('merged'),
            'merge_commit':pr.get('merge_commit_sha') if pr.get('merged') else None,
            'mergeable':pr.get('mergeable') if not pr.get('merged') else None}


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


AUDIT_IDENTITY_FIELDS=('timestamp','profile','wp_id','from_state','to_state','operation','reason','evidence_refs','policy_digest')


def audit_identity(row):
    """Recompute the audit_id execute() derives, to detect edited audit rows."""
    return hashlib.sha256(json.dumps({k:row.get(k) for k in AUDIT_IDENTITY_FIELDS},sort_keys=True).encode()).hexdigest()


def blocker_rows(wp):
    """Chronological BLOCKED/UNBLOCKED audit rows of any result for one WP; read-only."""
    try:
        if not AUDIT.exists():
            return []
        need(AUDIT.stat().st_size<10_000_000, 'AUDIT_ROTATION_REQUIRED')
        rows=[json.loads(line) for line in AUDIT.read_text().splitlines()]
    except OSError:
        return []
    return [r for r in rows if r.get('wp_id')==wp and r.get('operation') in {'BLOCKED','UNBLOCKED'}]


def last_projection(wp):
    if not AUDIT.exists(): return None
    need(AUDIT.stat().st_size<10_000_000, 'AUDIT_ROTATION_REQUIRED')
    rows=[json.loads(line) for line in AUDIT.read_text().splitlines()]
    matches=[r for r in rows if r.get('wp_id')==wp and r.get('result')=='VERIFIED'
             and r.get('operation')=='MERGE_READY']
    return matches[-1] if matches else None


def execute(profile,wp,target,envelope,policy,plane,gh,audit,key,previous=None,projection=None,prewrite=None):
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
    operation_data=evaluate(profile,wp,source,target,item,plane,policy,gh,envelope,previous,projection)
    if operation_data:
        record.update(operation_data)
        if operation_data.get('observed_pr_number'):
            need(pr_facts(gh.fresh_pr(operation_data['observed_pr_number']))==operation_data['pr_facts'], 'CONCURRENT_GITHUB_CHANGE')
    fresh=plane.issue(item['id'])
    own(fresh,profile,wp,policy)
    need(fresh==item, 'CONCURRENT_PLANE_CHANGE')
    if prewrite is not None:
        prewrite()
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
    if 'execution_project' in policy:
        data=dict(policy)
        expected=data.pop('policy_digest')
        need(hashlib.sha256(json.dumps(data,ensure_ascii=False,sort_keys=True).encode()).hexdigest()==expected,'POLICY_DIGEST_MISMATCH')
    for kind,path in [('auto_next','/usr/local/libexec/cap-auto-next.py'),('execution_queue','/usr/local/libexec/execution_queue.py'),('health','/usr/local/libexec/cap-plane-health.py'),('health_snapshot','/usr/local/libexec/cap-plane-health-snapshot.py'),('preparation','/usr/local/libexec/cap-preparation.py'),('prepare','/usr/local/libexec/cap-plane-prepare.py')]:
        if kind in policy.get('implementation_sha256',{}):
            need(hashlib.sha256(Path(path).read_bytes()).hexdigest()==policy['implementation_sha256'][kind], 'AUTO_NEXT_POLICY_REFRESH_REQUIRED')
    for name,expected in policy['source_manifest'].items():
        need(isinstance(name,str) and not name.startswith('/') and '..' not in name.split('/'), 'INVALID_POLICY_SOURCE')
        try:
            actual=hashlib.sha256((Path('/srv/ailab/project')/name).read_bytes()).hexdigest()
        except OSError:
            raise Denied('CANONICAL_POLICY_SOURCE_UNAVAILABLE') from None
        need(actual==expected, 'CANONICAL_POLICY_REFRESH_REQUIRED')
    need(hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==policy['implementation_sha256']['transition'], 'HELPER_POLICY_REFRESH_REQUIRED')
    need(hashlib.sha256(Path('/usr/local/libexec/cap-plane-queue').read_bytes()).hexdigest()==policy['implementation_sha256']['queue'], 'QUEUE_POLICY_REFRESH_REQUIRED')


def auto_next_support():
    loader = importlib.machinery.SourceFileLoader('cap_auto_next', '/usr/local/libexec/cap-auto-next.py')
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def main():
    global q
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    try:
        need(os.geteuid()==0 and len(sys.argv)==4, 'INVALID_INVOCATION')
        if q is None: q=load_support()
        need(q.STATES == TARGETS-{'BLOCKED','UNBLOCKED'}, 'CANONICAL_WORKFLOW_SCHEMA_CHANGED')
        profile,wp,target=sys.argv[1:]
        need(profile in q.PEOPLE and q.WP.fullmatch(wp) and target in TARGETS, 'INVALID_ARGUMENTS')
        caller_uid=int(os.environ.get('SUDO_UID',str(os.getuid())))
        os.environ.clear()
        need(not getattr(sys.stdin,'isatty',lambda:False)(), 'REASON_AND_EVIDENCE_JSON_REQUIRED_ON_STDIN')
        envelope=parse_input(sys.stdin.buffer.read(8193))
        policy=json.loads((ROOT/'transition-policy.json').read_text(), object_pairs_hook=q.unique)
        key=json.loads((ROOT/'credential.json').read_text())['api_key']
        need(isinstance(key,str) and key and not any(c in key for c in '\r\n'), 'INVALID_CREDENTIAL_CONFIG')
        # Reject raw secret input before logging or external lookups.
        need(key not in json.dumps(envelope) and key not in envelope['reason'], 'SECRET_IN_INPUT')
        verify_policy_sources(policy)
        auto = auto_next_support()
        auto.require_caller(profile,caller_uid)
        need(wp in policy['contexts'] and policy['contexts'][wp]['work_package']['primary_owner']['canonical_name']==q.PEOPLE[profile][0], 'WRONG_OR_NON_CANONICAL_OWNER')
        lockfd=os.open('/run/cap-plane-queue.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        with os.fdopen(lockfd,'r+') as lock:
            need(os.fstat(lock.fileno()).st_uid==0, 'UNSAFE_LOCK_OWNER')
            fcntl.flock(lock,fcntl.LOCK_EX)
            time.sleep(1.25)
            plane=Plane(key)
            gh=GitHub(profile)
            result=execute(profile,wp,target,envelope,policy,plane,gh,append_audit,key,last_blocker(wp),last_projection(wp))
            if target=='DONE' and result.get('result')=='VERIFIED':
                try:
                    result['auto_next']=auto.after_done(sys.modules[__name__],wp,policy,lambda:Plane(key),GitHub,append_audit,key)
                except Exception:
                    result['auto_next']={'status':'UNAVAILABLE','reasons':['ADVANCE_REQUIRES_RECOVERY']}
            elif target in {'MERGED','UNBLOCKED'} and result.get('result')=='VERIFIED':
                # Contract readiness and verified blocker resolution may precede DONE.
                try:
                    result['auto_next']=auto.after_done(sys.modules[__name__],wp,policy,lambda:Plane(key),GitHub,append_audit,key)
                except Exception:
                    result['auto_next']={'status':'UNAVAILABLE','reasons':['ADVANCE_REQUIRES_RECOVERY']}
            if result.get('result')=='VERIFIED':
                try:
                    result['health']=auto.after_transition(sys.modules[__name__],wp,policy,lambda:Plane(key),GitHub)
                except Exception:
                    result['health']={'health':'UNAVAILABLE','reasons':['PREFLIGHT_SOURCE_UNAVAILABLE']}
        if result.get('result')=='VERIFIED':
            # Nonblocking replenishment after lock release; failure cannot undo work.
            with contextlib.suppress(OSError,subprocess.TimeoutExpired):
                subprocess.run(['/usr/bin/systemctl','--no-block','start','cap-plane-prepare.service'],capture_output=True,timeout=5,check=False)
        q.emit(result,key)
        return 0
    except Denied as exc:
        print(json.dumps({'result':'DENIED','reason_code':exc.code},sort_keys=True))
    except Exception:
        print('{"result":"UNAVAILABLE","reason_code":"EVIDENCE_OR_SERVICE_UNAVAILABLE"}')
    return 2


if __name__=='__main__':
    sys.exit(main())
