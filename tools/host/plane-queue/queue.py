#!/usr/bin/python3 -I
"""CTRL-HOST-002: fixed-project GET-only queue. No repository imports or writes."""
import datetime
import fcntl
import hashlib
import html.parser
import json
import os
import pwd
from pathlib import Path
import re
import resource
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

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


class Reader:
    def __init__(self, key):
        self.key = key
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        self.last = 0
        self.calls = []

    def get(self, route, cursor=None):
        require(route in ROUTES)
        require(cursor is None or isinstance(cursor, str) and re.fullmatch(r'[A-Za-z0-9:_=.-]{1,128}', cursor))
        query = '' if cursor is None else '?' + urllib.parse.urlencode({'cursor': cursor})
        time.sleep(max(0, 1.25 - (time.monotonic() - self.last)))
        self.last = time.monotonic()
        request = urllib.request.Request(ORIGIN + PREFIX + route + query,
                                        headers={'X-API-Key': self.key}, method='GET')
        self.calls.append(('GET', route))
        with self.opener.open(request, timeout=10) as response:
            require(response.status == 200)
            raw = response.read(8_000_001)
            require(len(raw) <= 8_000_000)
            return json.loads(raw, object_pairs_hook=unique)

    def rows(self, route):
        result, seen = [], set()
        cursor = None
        for _ in range(20):
            data = self.get(route, cursor)
            if isinstance(data, list):
                page, more = data, False
            else:
                require(isinstance(data, dict) and isinstance(data.get('results'), list))
                page, more = data['results'], data.get('next_page_results', False)
                require(type(more) is bool)
            require(all(isinstance(row, dict) and isinstance(row.get('id'), str) for row in page))
            result.extend(page)
            if not more:
                require(len({r['id'] for r in result}) == len(result))
                if isinstance(data, dict) and 'total_count' in data:
                    require(data['total_count'] == len(result))
                return result
            cursor = data.get('next_cursor')
            require(isinstance(cursor, str) and cursor and cursor not in seen)
            seen.add(cursor)
        raise Unsafe()


def snapshot(reader, catalog):
    project = reader.get('')
    require(project.get('id') == PREFIX.split('/')[-2] and project.get('name') == 'Graduation Project'
            and project.get('identifier') == 'CAP')
    members = reader.rows('members/')
    for owner, identity, email in PEOPLE.values():
        require(len([m for m in members if m['id'] == identity and m.get('email', '').casefold() == email]) == 1)
        require(len([m for m in members if m.get('email', '').casefold() == email]) == 1)
    states = reader.rows('states/')
    require(len({s['name'] for s in states}) == len(states) and {s['name'] for s in states} == STATES)
    state_map = {s['id']: s['name'] for s in states}
    labels = reader.rows('labels/')
    require(len([x for x in labels if x['name'] == 'BLOCKED']) == 1)
    blocked_id = next(x['id'] for x in labels if x['name'] == 'BLOCKED')
    issues = reader.rows('issues/')
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
    cycles = reader.rows('cycles/')
    require({c['id']: c['name'] for c in cycles} == {identity: 'S' + str(n) for n, identity in CYCLES.items()})
    by_id = {r['_id']: r for r in rows.values()}
    for n, identity in CYCLES.items():
        for item in reader.rows(f'cycles/{identity}/cycle-issues/'):
            require(item['id'] in by_id)
            row = by_id[item['id']]
            require(row['cycle'] is None)
            row['cycle'] = 'S' + str(n)
    return rows


def clean(text):
    return ''.join(c for c in text if not unicodedata.category(c).startswith('C'))[:240]


def select(profile, rows):
    own = [r for r in rows.values() if r['_profile'] == profile]
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
        result['current_task' if active else 'next_task'] = task
        result['status'] = 'BLOCKED' if row['blocked'] else 'OK'
    pending = [r for r in own if r['plane_state'] in {'IN_REVIEW','MERGE_READY','MERGED','VALIDATING'}]
    if not active and not ready and pending:
        if len(pending)>1:
            result.update(status='AMBIGUOUS',ambiguity='MULTIPLE_PENDING_WORK')
        else:
            row=pending[0]
            result['current_task']={k:clean(v) if isinstance(v,str) else v for k,v in row.items() if not k.startswith('_')}
            result['status']='BLOCKED' if row['blocked'] else 'OK'
    result['display_status']=('CURRENT' if result['current_task'] else 'READY') if result['status']=='OK' else result['status']
    if result['status']=='NO_TASK':
        result['reason']='NO_RELEASED_WORK; use read-only automatic eligibility details; never choose BACKLOG'
    return result


def emit(result, key=''):
    encoded = json.dumps(result, ensure_ascii=True, sort_keys=True)
    require(not key or key not in encoded and json.dumps(key)[1:-1] not in encoded)
    print(encoded)


def exit_status(result):
    if result['status'] in {'OK','NO_TASK'}:
        return 0
    return 2 if result['status']=='UNAVAILABLE' else 1


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
            time.sleep(1.25)
            result = select(profile, snapshot(Reader(key), catalog))
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
            try:
                auto_loader=__import__('importlib.machinery',fromlist=['SourceFileLoader']).SourceFileLoader('cap_auto_health','/usr/local/libexec/cap-auto-next.py')
                auto_spec=__import__('importlib.util',fromlist=['spec_from_loader']).spec_from_loader(auto_loader.name,auto_loader)
                auto=__import__('importlib.util',fromlist=['module_from_spec']).module_from_spec(auto_spec)
                auto_loader.exec_module(auto)
                t=auto.load_transition()
                policy=json.loads((ROOT/'transition-policy.json').read_text())
                t.verify_policy_sources(policy)
                health=auto.owner_health(t,profile,policy,t.Plane(key),t.GitHub)
                result.update(prepared_next=health['prepared_next'],health=health['health'],first_blocker=health['first_blocker'])
            except Exception:
                result.update(prepared_next=None,health='UNAVAILABLE',first_blocker={'reason':'PREFLIGHT_SOURCE_UNAVAILABLE'})
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
