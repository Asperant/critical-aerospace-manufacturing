"""Host helper security/queue regression checks; no network or credentials."""
import ast
import contextlib
from email.message import Message
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import time
import urllib.error
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('queue_helper', HERE / 'queue.py')
q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)


def task(wp='WP-GOV-001', state='READY', blocked=False):
    return {'wp_id': wp, 'title': 'Title\x1b\n', 'plane_state': state, 'blocked': blocked,
            'cycle': 'S1', '_id': 'private-id', '_profile': 'asrin'}


class QueueTests(unittest.TestCase):
    def test_current_precedes_ready(self):
        result = q.select('asrin', {'a': task(state='IN_PROGRESS'), 'b': task('WP-GOV-002')})
        self.assertEqual(result['current_task']['wp_id'], 'WP-GOV-001')
        self.assertIsNone(result['next_task'])

    def test_ready_and_no_backlog_selection(self):
        self.assertEqual(q.select('asrin', {'a': task()})['next_task']['wp_id'], 'WP-GOV-001')
        self.assertEqual(q.select('asrin', {'a': task(state='BACKLOG')})['status'], 'NO_TASK')
        self.assertEqual(q.select('selman', {'a': task()})['status'], 'NO_TASK')

    def test_multiple_candidates_never_choose(self):
        for states in [('READY', 'READY'), ('IN_PROGRESS', 'IN_PROGRESS')]:
            result = q.select('asrin', {str(n): task(str(n), state) for n, state in enumerate(states)})
            self.assertEqual(result['status'], 'AMBIGUOUS')
            self.assertIsNone(result['current_task'])
            self.assertIsNone(result['next_task'])

    def test_blocked_current_not_replaced(self):
        result = q.select('asrin', {'a': task(state='IN_PROGRESS', blocked=True), 'b': task('WP-GOV-002')})
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertEqual(result['current_task']['wp_id'], 'WP-GOV-001')

    def test_sanitize_and_secret_guard(self):
        result = q.select('asrin', {'a': task()})
        self.assertEqual(result['next_task']['title'], 'Title')
        self.assertNotIn('_id', result['next_task'])
        with self.assertRaises(q.Unsafe), contextlib.redirect_stdout(io.StringIO()):
            q.emit({'title': 'sentinel-secret'}, 'sentinel-secret')

    def test_no_arbitrary_routes_or_cursor(self):
        reader = q.Reader('sentinel-secret')
        for route, cursor in [('https://evil/', None), ('issues/1/', None), ('issues/', 'x&method=POST')]:
            with self.assertRaises(q.Unsafe):
                reader.get(route, cursor)
        self.assertEqual(reader.calls, [])
        with self.assertRaises(q.Unsafe):
            q.NoRedirect().redirect_request(None, None, None, None, None, None)

    def test_actual_transport_is_get_and_ignores_proxy(self):
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, limit): return b'[]'
        reader = q.Reader('sentinel-secret')
        with patch.object(reader.opener, 'open', return_value=Response()) as opened:
            reader.get('issues/', '100:1:0')
        request = opened.call_args.args[0]
        self.assertEqual(request.get_method(), 'GET')
        self.assertIsNone(request.data)
        self.assertTrue(request.full_url.startswith(q.ORIGIN + q.PREFIX + 'issues/?cursor='))
        self.assertFalse(hasattr(reader, 'post'))

    def test_429_retries_are_bounded_and_backed_off(self):
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, limit): return b'[]'
        headers = Message()
        headers['Retry-After'] = '0'
        errors = [urllib.error.HTTPError('http://plane', 429, 'busy', headers, None),
                  urllib.error.HTTPError('http://plane', 429, 'busy', headers, None)]
        reader = q.Reader('sentinel-secret', q.RateLimiter())
        with patch.object(reader.opener, 'open', side_effect=errors + [Response()]) as opened, \
             patch.object(q.time, 'sleep') as sleep:
            self.assertEqual(reader.get('issues/'), [])
        self.assertEqual(opened.call_count, 3)
        self.assertEqual(sleep.call_count, 2)
        self.assertEqual(reader.metrics['get_count'], 3)

    def test_expired_snapshot_is_never_reused(self):
        rows = {'a': task()}
        with patch.object(q, 'SNAPSHOT_CACHE_PATH', Path('/tmp/cap-plane-test-snapshot.json')):
            q.SNAPSHOT_CACHE_PATH.unlink(missing_ok=True)
            q._write_snapshot_cache(rows)
            value = json.loads(q.SNAPSHOT_CACHE_PATH.read_text())
            value['captured_at'] = time.time() - q.SNAPSHOT_CACHE_TTL_SECONDS - 1
            q.SNAPSHOT_CACHE_PATH.write_text(json.dumps(value))
            self.assertIsNone(q._read_snapshot_cache())
            q.SNAPSHOT_CACHE_PATH.unlink(missing_ok=True)

    def test_fresh_snapshot_is_shared_without_a_second_plane_read(self):
        rows = {'a': task()}
        reader = q.Reader('sentinel-secret')
        with patch.object(q, '_read_snapshot_cache', return_value=rows), \
             patch.object(q, 'snapshot') as read:
            actual, cached = q.load_snapshot(reader, {'owners': {}})
        self.assertTrue(cached)
        self.assertEqual(actual, rows)
        read.assert_not_called()

    def test_snapshot_pacing_fits_operator_budget(self):
        # The normal snapshot has 18 bounded GETs; the pacing budget must not
        # exceed the documented 20-second operator timeout by itself.
        self.assertLessEqual(18 * q.REQUEST_INTERVAL, 16.2)

    def test_health_timeout_is_advisory(self):
        with patch.object(q, 'preflight', side_effect=TimeoutError('sentinel')):
            self.assertIsNone(q.bounded_preflight('asrin', 'sentinel-secret'))

    def test_health_probe_uses_short_github_budget(self):
        transition = type('Transition', (), {})()
        observed = {}

        class GitHub:
            def __init__(self, profile, request_timeout=30):
                observed.update(profile=profile, request_timeout=request_timeout)

        transition.GitHub = GitHub  # pyright: ignore[reportAttributeAccessIssue]
        auto = type('Auto', (), {
            'semantic_slot_release_source': staticmethod(lambda *args: None),
            'semantic_slot_release_proof': staticmethod(lambda *args, **kwargs: None),
        })
        rows = {'candidate': task('WP-CORE-004', 'IN_PROGRESS', blocked=True)}
        executor = type('Executor', (), {
            '__init__': lambda self, **kwargs: None,
            '__enter__': lambda self: self,
            '__exit__': lambda self, *args: None,
            'submit': lambda self, *args: object(),
        })
        with patch.object(q, '_read_slot_cache', return_value={}), \
             patch.object(q.concurrent.futures, 'ThreadPoolExecutor', executor), \
             patch.object(q.concurrent.futures, 'as_completed', return_value=[]):
            q._slot_waits('asrin', 'sentinel-secret', rows, auto, transition,
                          {'policy_digest': 'p'})
        self.assertEqual(observed, {'profile': 'asrin', 'request_timeout': 1})

    def test_slot_release_cache_reuses_only_matching_fingerprint(self):
        source = {
            'wp_id': 'WP-CORE-004',
            'proof_fingerprint': 'f' * 64,
            'semantic_blocker_id': 'CORE-004-EXT',
            'semantic_blocker_class': 'WAITING_EXTERNAL_INTEGRATION_BINDINGS',
            'scope': 's' * 64,
        }
        proof = {
            'schema': 'cap-slot-release-v2',
            'wp_id': 'WP-CORE-004',
            'local_actionable_work': 'NONE',
            'implementation_persisted': True,
            'semantic_blocker_id': source['semantic_blocker_id'],
            'semantic_blocker_class': source['semantic_blocker_class'],
            'relevant_scope_digest': source['scope'],
            'proof_fingerprint': source['proof_fingerprint'],
        }
        entry = {'fingerprint': source['proof_fingerprint'], 'proof': proof}
        self.assertTrue(q._cache_entry_matches(entry, source))
        changed = dict(source, proof_fingerprint='0' * 64)
        self.assertFalse(q._cache_entry_matches(entry, changed))
        changed_scope = dict(source, scope='0' * 64)
        self.assertFalse(q._cache_entry_matches(entry, changed_scope))

    def test_slot_source_cache_is_ttl_and_policy_bound(self):
        source = {'proof_fingerprint': 'f' * 64, 'policy_digest': 'p'}
        entry = {'source': source, 'fingerprint': source['proof_fingerprint'],
                 'source_captured_at': time.time()}
        self.assertEqual(q._cached_slot_source(entry, {'policy_digest': 'p'}), source)
        self.assertIsNone(q._cached_slot_source(entry, {'policy_digest': 'changed'}))
        self.assertIsNone(q._cached_slot_source(
            dict(entry, fingerprint='changed'), {'policy_digest': 'p'}
        ))
        self.assertEqual(q.SNAPSHOT_CACHE_TTL_SECONDS, 60.0)
        self.assertEqual(q.SOURCE_CACHE_TTL_SECONDS, 60.0)
        expired = dict(entry, source_captured_at=time.time() - q.SOURCE_CACHE_TTL_SECONDS - 1)
        self.assertIsNone(q._cached_slot_source(expired, {'policy_digest': 'p'}))

    def test_unavailable_health_keeps_verified_slot_releases(self):
        rows = {
            'a': task('WP-CORE-004', 'VALIDATING', blocked=True),
            'b': task('WP-CORE-005', 'IN_PROGRESS', blocked=True),
            'c': task('WP-UI-001', 'READY'),
        }
        health = {
            'health': 'UNAVAILABLE',
            'prepared_next': None,
            'first_blocker': {'reason': 'PREFLIGHT_SOURCE_UNAVAILABLE'},
            'deferred_waits': [
                {'wp_id': 'WP-CORE-004', 'reason': 'WAITING_DOWNSTREAM_INTEGRATED_ACCEPTANCE_EVIDENCE'},
                {'wp_id': 'WP-CORE-005', 'reason': 'WAITING_EXTERNAL_INTEGRATION_BINDINGS'},
            ],
        }
        result = q.combine('asrin', rows, health)
        self.assertEqual(result['status'], 'OK')
        self.assertEqual(result['next_task']['wp_id'], 'WP-UI-001')
        self.assertEqual(result['health'], 'UNAVAILABLE')

    def test_unknown_slot_proof_does_not_hide_wp(self):
        rows = {
            'a': task('WP-CORE-004', 'IN_PROGRESS', blocked=True),
            'b': task('WP-CORE-005', 'IN_PROGRESS', blocked=True),
        }
        health = {'health': 'UNAVAILABLE', 'prepared_next': None,
                  'first_blocker': {'reason': 'PREFLIGHT_SOURCE_UNAVAILABLE'},
                  'deferred_waits': []}
        result = q.combine('asrin', rows, health)
        self.assertEqual(result['status'], 'AMBIGUOUS')
        self.assertEqual(result['candidate_wp_ids'], ['WP-CORE-004', 'WP-CORE-005'])

    def test_cached_deferred_waits_survive_preflight_timeout(self):
        rows = {
            'a': task('WP-CORE-004', 'IN_PROGRESS', blocked=True),
            'b': task('WP-CORE-005', 'IN_PROGRESS', blocked=True),
            'c': task('WP-CORE-003', 'BACKLOG'),
        }
        health = None  # bounded preflight timed out
        waits = [
            {'wp_id': 'WP-CORE-004', 'state': 'IN_PROGRESS', 'blocked': True,
             'reason': 'WAITING_EXTERNAL_INTEGRATION_BINDINGS'},
            {'wp_id': 'WP-CORE-005', 'state': 'IN_PROGRESS', 'blocked': True,
             'reason': 'WAITING_EXTERNAL_INTEGRATION_BINDINGS'},
        ]
        result = q.combine('asrin', rows, health, waits)
        self.assertEqual(result['status'], 'NO_TASK')
        self.assertIsNone(result['current_task'])
        self.assertEqual(result['deferred_waits'], waits)

    def test_response_bounds_and_redirects_fail_closed(self):
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, limit): return b'x' * limit
        reader = q.Reader('sentinel-secret')
        with patch.object(reader.opener, 'open', return_value=Response()):
            with self.assertRaises(q.Unsafe): reader.get('issues/')
        with patch.object(reader.opener, 'open', side_effect=TimeoutError('sentinel-secret')):
            with self.assertRaises(TimeoutError): reader.get('issues/')

    def test_get_only_source_contract(self):
        tree = ast.parse((HERE / 'queue.py').read_text())
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and
                 isinstance(node.func, ast.Attribute) and node.func.attr == 'Request']
        self.assertEqual(len(calls), 1)
        self.assertEqual(next(k.value.value for k in calls[0].keywords if k.arg == 'method'), 'GET')
        self.assertFalse(any(k.arg == 'data' for k in calls[0].keywords))

    def test_pagination_rejects_duplicates_and_partial_results(self):
        reader = q.Reader('sentinel-secret')
        with patch.object(reader, 'get', return_value={'results': [{'id':'a'}, {'id':'a'}]}):
            with self.assertRaises(q.Unsafe): reader.rows('issues/')
        with patch.object(reader, 'get', return_value={'results': [], 'total_count': 1}):
            with self.assertRaises(q.Unsafe): reader.rows('issues/')
        pages = [{'results':[{'id':'a'}], 'next_page_results':True, 'next_cursor':'10:1:0'},
                 {'results':[{'id':'b'}], 'next_page_results':False, 'total_count':2}]
        with patch.object(reader, 'get', side_effect=pages):
            self.assertEqual(len(reader.rows('issues/')), 2)

    def test_metadata_wrappers_and_duplicate_keys(self):
        for value in ['{"canonical_wp_id":"WP-GOV-001"}', '<div><pre><code>{"canonical_wp_id":"WP-GOV-001"}</code></pre></div>']:
            self.assertEqual(q.metadata(value)['canonical_wp_id'], 'WP-GOV-001')
        for value in ['{"x":1,"x":2}', '<pre>{}</pre><pre>{}</pre>']:
            with self.assertRaises(q.Unsafe): q.metadata(value)

    def test_invalid_profile_arguments_and_unavailable_do_not_leak(self):
        for args in [[], ['asrin','--url','bad'], ['evil']]:
            output = io.StringIO()
            with patch.object(q.sys, 'argv', ['helper'] + args), contextlib.redirect_stdout(output):
                self.assertEqual(q.main(), 2)
            self.assertEqual(json.loads(output.getvalue())['status'], 'UNAVAILABLE')
        output = io.StringIO()
        with patch.object(q.sys, 'argv', ['helper', 'asrin']), patch.object(q.os, 'geteuid', return_value=0), \
             patch.object(q.Path, 'read_text', side_effect=Exception('sentinel-secret')), \
             patch.object(q.os.environ, 'clear'), contextlib.redirect_stdout(output):
            self.assertEqual(q.main(), 2)
        self.assertNotIn('sentinel-secret', output.getvalue())

    def test_snapshot_validates_complete_identity_and_cycles(self):
        people = list(q.PEOPLE.values())
        cycle_id = q.CYCLES[1]
        catalog = {'owners': {'WP-GOV-001': 'Asrın Dündar'}}
        issue = {'id':'issue', 'external_id':'WP-GOV-001', 'external_source':'projectctl',
                 'name':'[WP-GOV-001] Title', 'description_html':json.dumps({'canonical_wp_id':'WP-GOV-001', 'canonical_owner':'Asrın Dündar'}),
                 'assignees':[people[0][1]], 'state':'READY', 'labels':[]}
        data = {'members/':[{'id':p[1], 'email':p[2]} for p in people],
                'states/':[{'id':s,'name':s} for s in q.STATES], 'labels/':[{'id':'blocked','name':'BLOCKED'}],
                'issues/':[issue], 'cycles/':[{'id':identity,'name':'S'+str(n)} for n,identity in q.CYCLES.items()]}
        for identity in q.CYCLES.values():
            data[f'cycles/{identity}/cycle-issues/'] = [issue] if identity == cycle_id else []
        class Fake:
            def get(self, route): return {'id':q.PREFIX.split('/')[-2], 'name':'Graduation Project','identifier':'CAP'}
            def rows(self, route): return data[route]
        self.assertEqual(q.snapshot(Fake(), catalog)['WP-GOV-001']['cycle'], 'S1')
        issue['assignees'] = [people[1][1]]
        with self.assertRaises(q.Unsafe): q.snapshot(Fake(), catalog)
        issue['assignees'] = [people[0][1]]
        data['issues/'].append(issue)
        with self.assertRaises(q.Unsafe): q.snapshot(Fake(), catalog)

    def test_snapshot_can_defer_cycle_reads_until_selection(self):
        people = list(q.PEOPLE.values())
        catalog = {'owners': {'WP-GOV-001': 'Asrın Dündar'}}
        issue = {'id': 'issue', 'external_id': 'WP-GOV-001', 'external_source': 'projectctl',
                 'name': '[WP-GOV-001] Title',
                 'description_html': json.dumps({'canonical_wp_id': 'WP-GOV-001',
                                                 'canonical_owner': 'Asrın Dündar'}),
                 'assignees': [people[0][1]], 'state': 'READY', 'labels': []}
        data = {'members/': [{'id': p[1], 'email': p[2]} for p in people],
                'states/': [{'id': s, 'name': s} for s in q.STATES],
                'labels/': [{'id': 'blocked', 'name': 'BLOCKED'}], 'issues/': [issue]}

        class Fake:
            def __init__(self):
                self.calls = []
            def get(self, route):
                self.calls.append(route)
                return {'id': q.PREFIX.split('/')[-2], 'name': 'Graduation Project',
                        'identifier': 'CAP'}
            def rows(self, route):
                self.calls.append(route)
                return data[route]

        reader = Fake()
        rows = q.snapshot(reader, catalog, set())
        self.assertIsNone(rows['WP-GOV-001']['cycle'])
        self.assertNotIn('cycles/', reader.calls)


class DeferredWaitVisibilityTests(unittest.TestCase):
    WAITS = [{'wp_id': 'WP-CORE-005', 'state': 'IN_PROGRESS', 'blocked': True,
              'reason': 'WAITING_EXTERNAL_INTEGRATION_BINDINGS'},
             {'wp_id': 'WP-CORE-001', 'state': 'VALIDATING', 'blocked': True,
              'reason': 'WAITING_DOWNSTREAM_INTEGRATED_ACCEPTANCE_EVIDENCE'}]

    def rows(self, *extra):
        rows = {'a': task('WP-CORE-005', 'IN_PROGRESS', blocked=True),
                'b': task('WP-CORE-001', 'VALIDATING', blocked=True)}
        rows.update({str(n): row for n, row in enumerate(extra)})
        return rows

    def health(self, waits=None):
        return {'prepared_next': None, 'health': 'STALL_RISK', 'first_blocker': None,
                'deferred_waits': self.WAITS if waits is None else waits}

    def test_ready_work_is_current_and_deferred_waits_stay_visible(self):
        result = q.combine('asrin', self.rows(task('WP-UI-001')), self.health())
        self.assertEqual(result['status'], 'OK')
        self.assertEqual(result['current_task']['wp_id'], 'WP-UI-001')
        self.assertEqual(result['next_task']['wp_id'], 'WP-UI-001')  # compatibility
        self.assertEqual(result['display_status'], 'READY')
        self.assertEqual(result['deferred_waits'], self.WAITS)
        self.assertEqual(result['health'], 'STALL_RISK')

    def test_only_deferred_waits_leave_no_current_task(self):
        result = q.combine('asrin', self.rows(), self.health())
        self.assertEqual(result['status'], 'NO_TASK')
        self.assertIsNone(result['current_task'])
        self.assertIsNone(result['next_task'])
        self.assertEqual([w['wp_id'] for w in result['deferred_waits']], ['WP-CORE-005', 'WP-CORE-001'])

    def test_ordinary_in_progress_still_wins(self):
        rows = self.rows(task('WP-ORD-001', 'IN_PROGRESS'), task('WP-UI-001'))
        result = q.combine('asrin', rows, self.health())
        self.assertEqual(result['current_task']['wp_id'], 'WP-ORD-001')
        self.assertIsNone(result['next_task'])
        self.assertEqual(result['display_status'], 'CURRENT')
        self.assertEqual(len(result['deferred_waits']), 2)

    def test_ordinary_blocked_in_progress_is_never_treated_as_a_wait(self):
        rows = self.rows(task('WP-ORD-001', 'IN_PROGRESS', blocked=True), task('WP-UI-001'))
        result = q.combine('asrin', rows, self.health())
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertEqual(result['current_task']['wp_id'], 'WP-ORD-001')

    def test_multiple_actionable_work_still_fails_closed(self):
        for extra in ((task('WP-A-001'), task('WP-A-002')),
                      (task('WP-A-001', 'IN_PROGRESS'), task('WP-A-002', 'IN_PROGRESS'))):
            result = q.combine('asrin', self.rows(*extra), self.health())
            self.assertEqual(result['status'], 'AMBIGUOUS')
            self.assertIsNone(result['current_task'])
            self.assertEqual(result['candidate_wp_ids'], ['WP-A-001', 'WP-A-002'])
            self.assertEqual(len(result['deferred_waits']), 2)

    def test_unclassified_or_unavailable_waits_fail_closed(self):
        rows = self.rows(task('WP-UI-001'))
        for health in (None, self.health(waits=[])):
            result = q.combine('asrin', rows, health)
            self.assertEqual(result['current_task']['wp_id'], 'WP-CORE-005')
            self.assertEqual(result['status'], 'BLOCKED')  # old behavior: nothing is hidden
        self.assertEqual(q.combine('asrin', rows, None)['health'], 'UNAVAILABLE')

    def test_classification_is_by_resolver_output_not_by_wp_id(self):
        rows = {'a': task('WP-OTHER-009', 'IN_PROGRESS', blocked=True), 'b': task('WP-UI-001')}
        waits = [{'wp_id': 'WP-OTHER-009', 'state': 'IN_PROGRESS', 'blocked': True, 'reason': 'X'}]
        result = q.combine('asrin', rows, self.health(waits))
        self.assertEqual(result['current_task']['wp_id'], 'WP-UI-001')

    def test_other_owners_are_untouched(self):
        other = dict(task('WP-SEL-001', 'IN_PROGRESS'), _profile='selman')
        result = q.combine('asrin', self.rows(other), self.health())
        self.assertEqual(result['status'], 'NO_TASK')


if __name__ == '__main__':
    unittest.main()
