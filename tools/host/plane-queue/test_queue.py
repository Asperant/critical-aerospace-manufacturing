"""Host helper security/queue regression checks; no network or credentials."""
import ast
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
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


if __name__ == '__main__':
    unittest.main()
