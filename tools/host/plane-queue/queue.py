#!/usr/bin/python3 -I
"""CTRL-HOST-002: fixed-project GET-only queue. No repository imports or writes."""
import datetime
import concurrent.futures
import contextlib
import fcntl
import hashlib
import html.parser
import json
import os
import pwd
import resource
import signal
import sys
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
import re

ROOT = Path('/etc/cap-plane-queue')
ORIGIN = 'http://127.0.0.1:8080'
PREFIX = '/api/v1/workspaces/critical-aerospace-manufacturing/projects/beb6dbea-4931-4ce9-b761-a4957c4b33be/'
PEOPLE = {
    'asrin': ('Asrın Dündar', '0b4a5417-2ed5-4ac2-95ff-e74104c5d601', 'asrindundar14@hotmail.com'),
    'selman': ('Selman Özdemir', 'a3d25336-e7d0-43f8-bfef-c0b5c2137a60', 'selmanozdemir430@gmail.com'),
    'batuhan': ('Batuhan Kaya', '51137169-2989-42bd-9260-997b26e7e6dd', 'batuhankaya0204@gmail.com'),
    'yavuz': ('Yavuz Gümüş', '3ccd9ad8-99e9-4b75-ae65-2325503d347f', 'yavuzzgumus@gmail.com'),
}
CYCLES = dict(enumerate([
    '24c63960-2f75-4d61-957c-98e60f27cd9b', 'f3bd6141-b612-4d81-a5d9-6670135dfcc4',
    'a3a6a89a-0a43-4d4b-bb3c-bb3225203dc7', '8cbdd9f6-21d1-48c2-a1be-b0ebfaad3398',
    '401de4d7-795c-498c-b6a6-164f0d6d3c11', '6e5f90fd-4d6f-440e-8323-a9614404205b',
    '21e2aa2d-b09e-4769-8b5f-81fb76a26107', 'c15d617a-5b1d-4d55-af8a-fd7064538a98',
    '8e2843c3-fa98-40bc-a204-1c5e9a30b9c6', 'f705d8ac-b176-48e9-af3c-1930b369c4b2',
    '8b3dc7f5-66cb-499a-ba6d-f375347a69d2', 'd341fe5d-861a-4db5-b744-41b08c788185',
    '2f784b7a-26d4-4dc4-a149-65306380e729'], 1))
ROUTES = frozenset(['', 'members/', 'states/', 'labels/', 'issues/', 'cycles/'] +
                   [f'cycles/{identity}/cycle-issues/' for identity in CYCLES.values()])
STATES = {'BACKLOG', 'READY', 'IN_PROGRESS', 'IN_REVIEW', 'MERGE_READY', 'MERGED', 'VALIDATING', 'DONE', 'CANCELED'}
WP = re.compile(r'WP-[A-Z0-9]+-[0-9]{3}')
# The fixed project snapshot uses 18 bounded GETs in the normal case.  The old
# 1.25s interval made the pacing sleep alone exceed the 20s operator timeout,
# before health evaluation even started.
REQUEST_INTERVAL = 0.9
HEALTH_BUDGET_SECONDS = 4
MAX_READ_WORKERS = 4
PARALLEL_REQUEST_INTERVAL = REQUEST_INTERVAL / MAX_READ_WORKERS
SNAPSHOT_CACHE_PATH = Path('/run/cap-plane-snapshot.json')
SNAPSHOT_CACHE_SCHEMA = 'cap-plane-snapshot-v1'
SNAPSHOT_CACHE_TTL_SECONDS = 3.0
SNAPSHOT_CACHE_MAX_BYTES = 8_000_000
MAX_429_RETRIES = 2
MAX_429_DELAY_SECONDS = 2.0
CACHE_PATH = Path('/run/cap-plane-slot-release-v2.json')
CACHE_SCHEMA = 'cap-slot-release-cache-v1'
CACHE_MAX_BYTES = 2_000_000


class Unsafe(Exception):
    pass


def require(value):
    if not value:
        raise Unsafe()


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result)
        result[key] = value
    return result


class Metadata(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks, self.current = [], None

    def handle_starttag(self, tag, attrs):
        if tag == 'pre':
            require(self.current is None)
            self.current = []
        elif self.current is not None:
            require(tag == 'code')

    def handle_endtag(self, tag):
        if tag == 'pre':
            require(self.current is not None)
            self.blocks.append(''.join(self.current))
            self.current = None
        elif self.current is not None:
            require(tag == 'code')

    def handle_data(self, value):
        if self.current is not None:
            self.current.append(value)


def metadata(value):
    require(isinstance(value, str))
    if value.lstrip().startswith('{'):
        data = value
    else:
        parser = Metadata()
        parser.feed(value)
        parser.close()
        require(len(parser.blocks) == 1 and parser.current is None)
        data = parser.blocks[0]
    result = json.loads(data, object_pairs_hook=unique)
    require(isinstance(result, dict))
    return result


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise Unsafe()


class RateLimiter:
    """Bound aggregate read rate while allowing independent GETs to overlap."""
    def __init__(self):
        self.lock = threading.Lock()
        self.next_at = 0.0

    def wait(self):
        with self.lock:
            now = time.monotonic()
            delay = max(0.0, self.next_at - now)
            self.next_at = max(now, self.next_at) + PARALLEL_REQUEST_INTERVAL
        if delay:
            time.sleep(delay)

    def defer(self, delay):
        """Pause aggregate reads after a server-side rate-limit response."""
        require(delay >= 0)
        with self.lock:
            self.next_at = max(self.next_at, time.monotonic() + delay)


class Reader:
    def __init__(self, key, limiter=None):
        self.key = key
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        self.last = 0
        self.calls = []
        self.limiter = limiter
        self.metrics = {'get_count': 0}

    def get(self, route, cursor=None):
        require(route in ROUTES)
        require(cursor is None or isinstance(cursor, str) and re.fullmatch(r'[A-Za-z0-9:_=.-]{1,128}', cursor))
        query = '' if cursor is None else '?' + urllib.parse.urlencode({'cursor': cursor})
        request = urllib.request.Request(ORIGIN + PREFIX + route + query,
                                        headers={'X-API-Key': self.key}, method='GET')
        for attempt in range(MAX_429_RETRIES + 1):
            if self.limiter is None:
                time.sleep(max(0, REQUEST_INTERVAL - (time.monotonic() - self.last)))
                self.last = time.monotonic()
            else:
                self.limiter.wait()
            self.calls.append(('GET', route))
            self.metrics['get_count'] += 1
            try:
                with self.opener.open(request, timeout=10) as response:
                    require(response.status == 200)
                    raw = response.read(8_000_001)
                    require(len(raw) <= 8_000_000)
                    return json.loads(raw, object_pairs_hook=unique)
            except urllib.error.HTTPError as exc:
                if exc.code != 429 or attempt >= MAX_429_RETRIES:
                    raise
                retry_after = 0.0
                if exc.headers is not None:
                    with contextlib.suppress(ValueError, TypeError):
                        retry_after = float(exc.headers.get('Retry-After', 0))
                delay = min(MAX_429_DELAY_SECONDS,
                            max(0.25 * (2 ** attempt), retry_after))
                if self.limiter is not None:
                    self.limiter.defer(delay)
                else:
                    self.last = time.monotonic() + delay

    def rows(self, route):
        result, seen = [], set()
        cursor = None
        for _ in range(20):
            data = self.get(route, cursor)
            if isinstance(data, list):
                page, more = data, False
            else:
                if not isinstance(data, dict) or not isinstance(data.get('results'), list):
                    raise Unsafe()
                page, more = data['results'], data.get('next_page_results', False)
                require(type(more) is bool)
            require(all(isinstance(row, dict) and isinstance(row.get('id'), str) for row in page))
            result.extend(page)
            if not more:
                require(len({r['id'] for r in result}) == len(result))
                if isinstance(data, dict) and 'total_count' in data:
                    require(data['total_count'] == len(result))
                return result
            require(isinstance(data, dict))
            cursor = data.get('next_cursor')
            require(isinstance(cursor, str) and cursor and cursor not in seen)
            seen.add(cursor)
        raise Unsafe()


def _read_routes(reader, routes, limiter=None):
    """Read independent routes with bounded concurrency; preserve fake readers."""
    routes = list(routes)
    if not isinstance(reader, Reader):
        return {route: reader.rows(route) for route in routes}
    result, errors = {}, []
    next_route = 0
    state_lock = threading.Lock()

    def worker():
        nonlocal next_route
        while True:
            with state_lock:
                if next_route >= len(routes):
                    return
                route = routes[next_route]
                next_route += 1
            try:
                child = Reader(reader.key, limiter)
                child.metrics = reader.metrics
                result[route] = child.rows(route)
            except BaseException as exc:
                with state_lock:
                    errors.append(exc)
                return

    workers = [threading.Thread(target=worker)
               for _ in range(min(MAX_READ_WORKERS, len(routes)))]
    for thread in workers:
        thread.start()
    for thread in workers:
        thread.join()
    if errors:
        raise errors[0]
    return result


def snapshot(reader, catalog):
    project = reader.get('')
    require(project.get('id') == PREFIX.split('/')[-2] and project.get('name') == 'Graduation Project'
            and project.get('identifier') == 'CAP')
    limiter = reader.limiter if isinstance(reader, Reader) else None
    route_rows = _read_routes(reader, ('members/', 'states/', 'labels/', 'issues/', 'cycles/'), limiter)
    members = route_rows['members/']
    for owner, identity, email in PEOPLE.values():
        require(len([m for m in members if m['id'] == identity and m.get('email', '').casefold() == email]) == 1)
        require(len([m for m in members if m.get('email', '').casefold() == email]) == 1)
    states = route_rows['states/']
    require(len({s['name'] for s in states}) == len(states) and {s['name'] for s in states} == STATES)
    state_map = {s['id']: s['name'] for s in states}
    labels = route_rows['labels/']
    require(len([x for x in labels if x['name'] == 'BLOCKED']) == 1)
    blocked_id = next(x['id'] for x in labels if x['name'] == 'BLOCKED')
    issues = route_rows['issues/']
    rows = {}
    for item in issues:
        wp = item.get('external_id', '')
        if not isinstance(wp, str) or not wp.startswith('WP-'):
            require(not item.get('name', '').startswith('[WP-'))
            continue  # Control items are not product work packages.
        require(WP.fullmatch(wp) and wp in catalog['owners'] and wp not in rows)
        require(item.get('external_source') == 'projectctl' and item['name'].startswith('[' + wp + '] '))
        meta = metadata(item.get('description_html'))
        require(meta.get('canonical_wp_id') == wp and meta.get('canonical_owner') == catalog['owners'][wp])
        owner = next(p for p, details in PEOPLE.items() if details[0] == meta['canonical_owner'])
        require(item.get('assignees') == [PEOPLE[owner][1]] and item['state'] in state_map)
        require(isinstance(item.get('labels'), list))
        rows[wp] = {'wp_id': wp, 'title': item['name'].split('] ', 1)[1], 'plane_state': state_map[item['state']],
                    'blocked': blocked_id in item['labels'], 'cycle': None, '_id': item['id'], '_profile': owner}
    require(set(rows) == set(catalog['owners']))
    cycles = route_rows['cycles/']
    require({c['id']: c['name'] for c in cycles} == {identity: 'S' + str(n) for n, identity in CYCLES.items()})
    by_id = {r['_id']: r for r in rows.values()}
    membership_routes = [f'cycles/{identity}/cycle-issues/' for identity in CYCLES.values()]
    memberships = _read_routes(reader, membership_routes, limiter)
    for n, identity in CYCLES.items():
        for item in memberships[f'cycles/{identity}/cycle-issues/']:
            require(item['id'] in by_id)
            row = by_id[item['id']]
            require(row['cycle'] is None)
            row['cycle'] = 'S' + str(n)
    return rows


def _read_snapshot_cache():
    """Return only a fresh complete snapshot; expiry is fail-closed."""
    try:
        if not SNAPSHOT_CACHE_PATH.is_file() or SNAPSHOT_CACHE_PATH.stat().st_size > SNAPSHOT_CACHE_MAX_BYTES:
            return None
        value = json.loads(SNAPSHOT_CACHE_PATH.read_text())
        if not isinstance(value, dict):
            return None
        captured = value.get('captured_at')
        rows = value.get('rows')
        if (value.get('schema') != SNAPSHOT_CACHE_SCHEMA or
                not isinstance(captured, int | float) or
                time.time() - captured < 0 or
                time.time() - captured > SNAPSHOT_CACHE_TTL_SECONDS or
                not isinstance(rows, dict)):
            return None
        return rows
    except (OSError, ValueError, TypeError, AttributeError):
        return None


def _write_snapshot_cache(rows):
    payload = json.dumps({'schema': SNAPSHOT_CACHE_SCHEMA,
                          'captured_at': time.time(), 'rows': rows}, sort_keys=True)
    if len(payload.encode()) > SNAPSHOT_CACHE_MAX_BYTES:
        return
    temporary = SNAPSHOT_CACHE_PATH.with_name(SNAPSHOT_CACHE_PATH.name + '.tmp')
    try:
        temporary.write_text(payload)
        os.chmod(temporary, 0o600)
        os.replace(temporary, SNAPSHOT_CACHE_PATH)
    except OSError:
        with contextlib.suppress(OSError):
            temporary.unlink()


def load_snapshot(reader, catalog):
    """Share one fresh Plane state snapshot across the complete queue run."""
    if isinstance(reader, Reader):
        cached = _read_snapshot_cache()
        if cached is not None:
            return cached, True
    rows = snapshot(reader, catalog)
    if isinstance(reader, Reader):
        _write_snapshot_cache(rows)
    return rows, False


def clean(text):
    return ''.join(c for c in text if not unicodedata.category(c).startswith('C'))[:240]


def select(profile, rows, deferred=None):
    """`deferred` holds WP IDs the shared resolver classifies as verified waits.

    They stay visible through `deferred_waits` but never become, or hide, the owner's
    current actionable work. Unknown or unavailable classification passes none (fail-closed).
    """
    own = [r for r in rows.values() if r['_profile'] == profile and r['wp_id'] not in (deferred or ())]
    active = [r for r in own if r['plane_state'] == 'IN_PROGRESS']
    ready = [r for r in own if r['plane_state'] == 'READY']
    result = {'profile': profile, 'canonical_owner': PEOPLE[profile][0], 'status': 'NO_TASK',
              'current_task': None, 'next_task': None, 'ambiguity': None,
              'read_timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    if len(active) > 1 or len(ready) > 1:
        result.update(status='AMBIGUOUS', ambiguity='MULTIPLE_IN_PROGRESS_OR_READY',
                      candidate_wp_ids=sorted(r['wp_id'] for r in active + ready))
    elif active or ready:
        row = (active or ready)[0]
        task = {k: clean(v) if isinstance(v, str) else v for k, v in row.items() if not k.startswith('_')}
        result['current_task'] = task
        if not active:
            result['next_task'] = task  # READY stays in next_task for existing readers
        result['status'] = 'BLOCKED' if row['blocked'] else 'OK'
    pending = [r for r in own if r['plane_state'] in {'IN_REVIEW','MERGE_READY','MERGED','VALIDATING'}]
    if not active and not ready and pending:
        if len(pending)>1:
            result.update(status='AMBIGUOUS',ambiguity='MULTIPLE_PENDING_WORK')
        else:
            row=pending[0]
            result['current_task']={k:clean(v) if isinstance(v,str) else v for k,v in row.items() if not k.startswith('_')}
            result['status']='BLOCKED' if row['blocked'] else 'OK'
    current = result['current_task']
    result['display_status']=('READY' if current and current['plane_state']=='READY' else 'CURRENT' if current else 'READY') if result['status']=='OK' else result['status']
    if result['status']=='NO_TASK':
        result['reason']='NO_RELEASED_WORK; use read-only automatic eligibility details; never choose BACKLOG'
    return result


def _slot_waits(profile, key, rows, auto=None, transition=None, policy=None):
    """Read only verified slot releases; no preparation/evidence health work."""
    if auto is None:
        loader = __import__('importlib.machinery', fromlist=['SourceFileLoader']).SourceFileLoader(
            'cap_auto_slots', '/usr/local/libexec/cap-auto-next.py')
        spec = __import__('importlib.util', fromlist=['spec_from_loader']).spec_from_loader(loader.name, loader)
        auto = __import__('importlib.util', fromlist=['module_from_spec']).module_from_spec(spec)
        loader.exec_module(auto)
    t = transition or auto.load_transition()
    if policy is None:
        policy = json.loads((ROOT / 'transition-policy.json').read_text())
        t.verify_policy_sources(policy)
    candidates = []
    for row in rows.values():
        if row.get('_profile') != profile or not row.get('blocked'):
            continue
        if row.get('plane_state') not in {'IN_PROGRESS', 'VALIDATING'}:
            continue
        wp = row['wp_id']
        candidates.append((wp, row['plane_state']))
    if not candidates:
        return []
    cache = _read_slot_cache()
    cache_lock = threading.Lock()

    gh = t.GitHub(profile)

    def evaluate(candidate):
        wp, state = candidate
        try:
            source = auto.semantic_slot_release_source(t, wp, profile, policy, gh)
            if source is None:
                return None
            entry_key = f'{profile}:{wp}'
            cached = cache.get(entry_key)
            cached_proof = cached.get('proof') if isinstance(cached, dict) else None
            if _cache_entry_matches(cached, source) and isinstance(cached_proof, dict):
                proof = cached_proof
            else:
                proof = auto.semantic_slot_release_proof(
                    t, wp, profile, policy, gh, source=source
                )
                if proof and proof.get('proof_fingerprint') == source['proof_fingerprint']:
                    with cache_lock:
                        cache[entry_key] = {
                            'fingerprint': source['proof_fingerprint'],
                            'proof': proof,
                        }
                        _write_slot_cache(cache)
        except Exception:
            return None  # This WP remains visible; UNKNOWN never releases it.
        if proof:
            return {'wp_id': wp, 'state': state, 'blocked': True,
                    'reason': proof['semantic_blocker_class']}
        return None

    waits = []
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=min(MAX_READ_WORKERS, len(candidates))
    ) as pool:
        futures = [pool.submit(evaluate, candidate) for candidate in candidates]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                waits.append(result)
    return waits


def _read_slot_cache():
    try:
        if not CACHE_PATH.is_file() or CACHE_PATH.stat().st_size > CACHE_MAX_BYTES:
            return {}
        value = json.loads(CACHE_PATH.read_text())
        if value.get('schema') != CACHE_SCHEMA or not isinstance(value.get('entries'), dict):
            return {}
        return value['entries']
    except (OSError, ValueError, TypeError, AttributeError):
        return {}


def _write_slot_cache(entries):
    payload = json.dumps({'schema': CACHE_SCHEMA, 'entries': entries}, sort_keys=True)
    if len(payload.encode()) > CACHE_MAX_BYTES:
        return
    temporary = CACHE_PATH.with_name(CACHE_PATH.name + '.tmp')
    try:
        temporary.write_text(payload)
        os.chmod(temporary, 0o600)
        os.replace(temporary, CACHE_PATH)
    except OSError:
        with contextlib.suppress(OSError):
            temporary.unlink()


def _cache_entry_matches(entry, source):
    if not isinstance(entry, dict) or not isinstance(entry.get('proof'), dict):
        return False
    proof = entry['proof']
    return (
        entry.get('fingerprint') == source.get('proof_fingerprint')
        and proof.get('proof_fingerprint') == source.get('proof_fingerprint')
        and proof.get('schema') == 'cap-slot-release-v2'
        and proof.get('wp_id') == source.get('wp_id', proof.get('wp_id'))
        and proof.get('local_actionable_work') == 'NONE'
        and proof.get('implementation_persisted') is True
        and proof.get('semantic_blocker_id') == source.get('semantic_blocker_id')
        and proof.get('semantic_blocker_class') == source.get('semantic_blocker_class')
        and proof.get('relevant_scope_digest') == source.get('scope')
    )


def preflight(profile, key, rows=None):
    """Return verified slot releases even when derived health is unavailable."""
    try:
        loader=__import__('importlib.machinery',fromlist=['SourceFileLoader']).SourceFileLoader('cap_auto_health','/usr/local/libexec/cap-auto-next.py')
        spec=__import__('importlib.util',fromlist=['spec_from_loader']).spec_from_loader(loader.name,loader)
        auto=__import__('importlib.util',fromlist=['module_from_spec']).module_from_spec(spec)
        loader.exec_module(auto)
        t=auto.load_transition()
        policy=json.loads((ROOT/'transition-policy.json').read_text())
        t.verify_policy_sources(policy)
        waits = _slot_waits(profile, key, rows if rows is not None else {}, auto, t, policy)
        # Selection consumes only these verified proofs. Full preparation health
        # is advisory and may be too slow for the queue's bounded read budget.
        return {'health': 'UNAVAILABLE', 'prepared_next': None,
                'first_blocker': {'reason': 'PREFLIGHT_SOURCE_UNAVAILABLE'},
                'deferred_waits': waits}
    except Exception:
        return None


def combine(profile, rows, health):
    """Selection excluding verified waits, plus derived health; health None fails closed."""
    waits = (health or {}).get('deferred_waits', [])
    deferred = {w['wp_id'] for w in waits if isinstance(w, dict) and isinstance(w.get('wp_id'), str)}
    result = select(profile, rows, deferred)
    if health is not None:
        result.update(prepared_next=health['prepared_next'], health=health['health'],
                      first_blocker=health['first_blocker'], deferred_waits=waits)
    else:
        result.update(prepared_next=None, health='UNAVAILABLE', first_blocker={'reason': 'PREFLIGHT_SOURCE_UNAVAILABLE'})
    return result


def emit(result, key=''):
    encoded = json.dumps(result, ensure_ascii=True, sort_keys=True)
    require(not key or key not in encoded and json.dumps(key)[1:-1] not in encoded)
    print(encoded)


def exit_status(result):
    if result['status'] in {'OK','NO_TASK'}:
        return 0
    return 2 if result['status']=='UNAVAILABLE' else 1


class HealthTimeout(Exception):
    pass


def bounded_preflight(profile, key, rows=None):
    """Health is advisory; it must not turn a live queue read into a hang."""
    def alarm_handler(signum, frame):
        raise HealthTimeout()

    previous = signal.signal(signal.SIGALRM, alarm_handler)
    signal.setitimer(signal.ITIMER_REAL, HEALTH_BUDGET_SECONDS)
    try:
        return preflight(profile, key) if rows is None else preflight(profile, key, rows)
    except (HealthTimeout, TimeoutError, OSError):
        return None
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def main():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    profile = sys.argv[1] if len(sys.argv) == 2 and sys.argv[1] in PEOPLE else None
    if profile is None:
        print('{"status":"UNAVAILABLE","reason":"INVALID_PROFILE_OR_ARGUMENTS"}')
        return 2
    try:
        require(os.geteuid() == 0)
        caller=int(os.environ.get('SUDO_UID','0'))
        require(caller in {0,pwd.getpwnam(profile).pw_uid})
        os.environ.clear()
        key = json.loads((ROOT / 'credential.json').read_text())['api_key']
        require(isinstance(key, str) and key and '\n' not in key and '\r' not in key)
        catalog = json.loads((ROOT / 'catalog.json').read_text())
        # Serialize whole reads across the four endpoints; no cached execution data.
        fd = os.open('/run/cap-plane-queue.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'r+') as lock:
            require(os.fstat(lock.fileno()).st_uid == 0)
            fcntl.flock(lock, fcntl.LOCK_EX)
            reader = Reader(key, RateLimiter())
            rows, snapshot_cached = load_snapshot(reader, catalog)
            result = combine(profile, rows, bounded_preflight(profile, key, rows))
            result['plane_gets'] = 0 if snapshot_cached else reader.metrics['get_count']
            result['plane_snapshot_cached'] = snapshot_cached
            if result['status']=='BLOCKED':
                result['reason']='ACTIVE_BLOCKER; accountable reason unavailable from live label alone'
                task=result['current_task'] or result['next_task']
                audit=Path('/var/log/cap-plane-transition/audit.jsonl')
                if audit.exists() and audit.stat().st_size<=10000000:
                    matches=[json.loads(line) for line in audit.read_text().splitlines()]
                    matches=[r for r in matches if r.get('wp_id')==task['wp_id'] and r.get('result')=='VERIFIED' and r.get('operation') in {'BLOCKED','UNBLOCKED'}]
                    if matches and matches[-1]['operation']=='BLOCKED':
                        result['reason']=clean(matches[-1].get('reason','ACTIVE_BLOCKER'))
            if result['status']=='NO_TASK':
                loader=__import__('importlib.machinery',fromlist=['SourceFileLoader']).SourceFileLoader('cap_auto_next','/usr/local/libexec/cap-auto-next.py')
                spec=__import__('importlib.util',fromlist=['spec_from_loader']).spec_from_loader(loader.name,loader)
                auto=__import__('importlib.util',fromlist=['module_from_spec']).module_from_spec(spec)
                loader.exec_module(auto)
                t=auto.load_transition()
                policy=json.loads((ROOT/'transition-policy.json').read_text())
                t.verify_policy_sources(policy)
                decision=auto.advance_owner(t,profile,policy,lambda:t.Plane(key),t.GitHub,lambda *_:None,key,preview=True)
                result['eligibility']=decision
                result['reason']='; '.join(decision.get('reasons',[])) or 'ELIGIBLE_WORK_AWAITS_GUARDED_RECOVERY'
                if decision['status'] in {'UNAVAILABLE','INVALID_BASELINE'}:
                    result['status']='UNAVAILABLE'
                    result['display_status']='UNAVAILABLE'
        emit(result, key)
        return exit_status(result)
    except Exception:
        # Never format exceptions, response bodies, URLs, config or credential data.
        emit({'profile': profile, 'canonical_owner': PEOPLE[profile][0], 'status': 'UNAVAILABLE',
              'reason': 'LIVE_READ_OR_IDENTITY_VALIDATION_FAILED',
              'read_timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat()})
        return 2


if __name__ == '__main__':
    sys.exit(main())
