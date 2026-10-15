"""Offline fixtures only. Tests never load a Plane/GitHub credential or call either service."""
from copy import deepcopy
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('transition',HERE/'transition.py')
t=importlib.util.module_from_spec(spec)
spec.loader.exec_module(t)
qs=importlib.util.spec_from_file_location('queue_fixture_source',HERE.parent/'plane-queue'/'queue.py')
t.q=importlib.util.module_from_spec(qs)
qs.loader.exec_module(t.q)
SECRET='sentinel-plane-secret-do-not-print'
HEAD='a'*40
MERGE='b'*40


class FakePlane:
    def __init__(self,item):
        self.items=[deepcopy(item)]
        self.item=deepcopy(item)
        self.states={s:s for s in t.q.STATES}
        self.names={s:s for s in t.q.STATES}
        self.members=[{'id':v[1],'email':v[2]} for v in t.q.PEOPLE.values()]
        self.blocked='BLOCKED-LABEL'
        self.patches=[]
        self.gets=0
        self.corrupt=False
        self.fail_readback=False
        self.response_lost=False
        self.apply=True
    def issue(self,identity):
        self.gets+=1
        if self.patches and self.fail_readback: raise TimeoutError(SECRET)
        return deepcopy(self.item)
    def patch(self,before,target):
        body=t.patch_body(before,target,self.states,self.blocked)
        self.patches.append(deepcopy(body))
        if self.apply: self.item.update(body)
        if self.corrupt: self.item['assignees']=['someone-else']
        if self.response_lost: raise TimeoutError(SECRET)


class FakeGH:
    def __init__(self,profile,wp,source,target,policy):
        owner=t.GITHUB[profile]
        peer=next(v for k,v in t.GITHUB.items() if k!=profile)
        post=source in {'MERGED','VALIDATING','DONE'} or target=='MERGED'
        sha=MERGE if post else HEAD
        self.pr_data={'number':1,'base':{'repo':{'full_name':'Asperant/critical-aerospace-manufacturing'},'ref':'main'},
                      'user':{'login':owner},'head':{'ref':f'wp/{wp}-test','sha':HEAD},'title':f'[{wp}] Implement slice',
                      'body':wp,'changed_files':2,'draft':source=='IN_REVIEW' and target=='IN_PROGRESS',
                      'state':'closed' if post else 'open', 'merged':post,'merge_commit_sha':MERGE if post else None,
                      'requested_reviewers':[{'login':peer}],'mergeable':True,'mergeable_state':'clean'}
        ids=sum((policy[k] for k in ['dor_task','dor_pr','dod_pr','dod_wp','dod_research']),[])
        ids+=['BLOCKER-OBSERVED','BLOCKER-RESOLVED','IMPLEMENTATION-STARTED','POST-MERGE-VALIDATION-STARTED',
              'docs/08#11:EVIDENCE-STALE','docs/08#9:F1']
        record={'wp_id':wp,'from_state':source,'to_state':target,'head_sha':sha,'source_manifest':policy['source_manifest'],
                'reason':'Observed execution event', 'policy_digest':policy['policy_digest'], 'checks':{k:{'result':'PASS','reason':'Observed fact with linked immutable evidence',
                                                            'evidence_refs':['repo:evidence/test.json']} for k in ids},
                'review_risk':'normal','high_risk_triggers':[], 'qualified_reviewers':[peer], 'pairing_participants':[],
                'owner_decision':'CANCEL','blocker':{'owner':profile,'external_dependency':'Named upstream outage'},
                'resolves_audit_id':'previous-blocker'}
        self.comments={2:{'user':{'login':owner},'body':json.dumps({'cap_plane_transition':record})},
                       3:{'user':{'login':peer},'body':json.dumps({'cap_plane_transition':record})}}
        self.review_data=[{'user':{'login':peer},'state':'APPROVED','commit_id':('c'*40 if source=='MERGE_READY' and target=='IN_REVIEW' else HEAD)}]
        self.run_data={'head_sha':sha,'head_branch':'main','event':'push',
                       'status':'in_progress' if target=='VALIDATING' else 'completed','conclusion':'success','updated_at':'2026-01-02T00:00:00+00:00'}
        self.check_data=([{'name':'projectctl','status':'completed','conclusion':'success'}],[])
        self.artifacts=[]
        self.missing_artifact=False
    def main_sha(self): return HEAD
    def pr(self,number): return deepcopy(self.pr_data)
    def comment(self,number): return deepcopy(self.comments[number])
    def run(self,number): return deepcopy(self.run_data)
    def checks(self,sha): return deepcopy(self.check_data)
    def reviews(self,number): return deepcopy(self.review_data)
    def contributors(self,number): return {self.pr_data['user']['login'].casefold()}
    def merged_shape(self,pr):
        if getattr(self,'undeleted_branch',False): raise t.Denied('MERGED_BRANCH_NOT_DELETED')
    def artifact(self,ref,sha):
        if self.missing_artifact: raise t.Denied('ARTIFACT_MISSING')
        self.artifacts.append((ref,sha))


def fixture(profile='asrin',source='READY',target='IN_PROGRESS'):
    names=dict(t.q.PEOPLE)
    ids={p:'WP-TEST-'+str(n).zfill(3) for n,p in enumerate(names,1)}
    wp=ids[profile]
    contexts={}
    for p,identity in ids.items():
        contexts[identity]={'work_package':{'id':identity,'primary_owner':{'canonical_name':names[p][0]},
                             'supporting_reviewers':[{'canonical_name':v[0]} for key,v in names.items() if key!=p],
                             'dor_refs':['DOR-WP-01'],'dod_refs':['DOD-WP-01'],'size_band':'M','scope_class':'F1'},
                            'dependency_edges':[], 'scope_criteria':['docs/08#9:F1'],'cycle_ids':['S1']}
    policy={'contexts':contexts,'source_manifest':{'docs/08':'canonical-sha'},'required_ci':['projectctl'],
            'policy_digest':'fixture-policy-digest','dor_task':['DOR-TASK-01','DOR-WP-01'],'dor_pr':['DOR-PR-01'],'dod_pr':['DOD-PR-01'],
            'dod_wp':['DOD-WP-01'],'dod_research':['DOD-RES-01'],'node_owners':{},'node_levels':{}}
    item={'id':'12345678-1234-1234-1234-123456789abc','external_id':wp,'external_source':'projectctl',
          'name':f'[{wp}] Test work','description_html':json.dumps({'canonical_wp_id':wp,'canonical_owner':names[profile][0]}),
          'state':source,'assignees':[names[profile][1]],'labels':['MILESTONE-LABEL'], 'priority':'low', 'cycle':'S1'}
    if target=='UNBLOCKED': item['labels'].append('BLOCKED-LABEL')
    plane=FakePlane(item)
    gh=FakeGH(profile,wp,source,target,policy)
    envelope={'reason':'Observed execution event','evidence_refs':['pr:1','comment:2','comment:3','run:4']}
    return wp,policy,plane,gh,envelope


def run_case(profile='asrin',source='READY',target='IN_PROGRESS',mutate=None):
    wp,policy,plane,gh,envelope=fixture(profile,source,target)
    if mutate: mutate(policy,plane,gh,envelope)
    logs=[]
    def audit(record,key):
        encoded=json.dumps(record)
        if key in encoded: raise t.Denied('SECRET_IN_AUDIT_INPUT')
        logs.append(deepcopy(record))
    result=t.execute(profile,wp,target,envelope,policy,plane,gh,audit,SECRET,
                     {'result':'VERIFIED','operation':'BLOCKED','audit_id':'previous-blocker','timestamp':'2026-01-01T00:00:00+00:00'})
    return result,plane,logs,gh


class TransitionTests(unittest.TestCase):
    def test_all_profiles_can_transition_only_their_wp(self):
        for profile in t.q.PEOPLE:
            with self.subTest(profile=profile):
                result,plane,logs,gh=run_case(profile)
                self.assertEqual(result['result'],'VERIFIED')
                self.assertEqual(plane.patches,[{'state':'IN_PROGRESS'}])
                self.assertEqual([r['result'] for r in logs],['INTENT','VERIFIED'])
                wp,policy,plane,gh,envelope=fixture(profile)
                other=next(p for p in t.q.PEOPLE if p!=profile)
                with self.assertRaises(t.Denied):
                    t.execute(other,wp,'IN_PROGRESS',envelope,policy,plane,gh,lambda *args:None,SECRET)
                self.assertEqual(plane.patches,[])

    def test_all_forward_workflow_transitions_have_real_predicates(self):
        for source,target in t.FORWARD.items():
            with self.subTest(source=source,target=target):
                result,plane,logs,gh=run_case(source=source,target=target)
                self.assertEqual(result['result'],'VERIFIED')
                self.assertTrue(gh.artifacts or target=='CANCELED')

    def test_documented_rework_conditions(self):
        for source,target in t.REWORK:
            with self.subTest(source=source):
                result,plane,logs,gh=run_case(source=source,target=target)
                self.assertEqual(result['result'],'VERIFIED')
        def no_draft(policy,plane,gh,envelope): gh.pr_data['draft']=False
        with self.assertRaises(t.Denied): run_case(source='IN_REVIEW',target='IN_PROGRESS',mutate=no_draft)

    def test_invalid_skips_backwards_and_terminal_rejected(self):
        for source,target in [('BACKLOG','DONE'),('IN_PROGRESS','READY'),('READY','MERGED'),('CANCELED','READY'),('DONE','IN_PROGRESS')]:
            with self.subTest(source=source,target=target), self.assertRaises(t.Denied):
                run_case(source=source,target=target)

    def test_noncanonical_and_duplicate_identity_rejected(self):
        wp,policy,plane,gh,envelope=fixture()
        with self.assertRaises(t.Denied):
            t.execute('asrin','WP-FAKE-999','IN_PROGRESS',envelope,policy,plane,gh,lambda *a:None,SECRET)
        plane.items.append(deepcopy(plane.items[0]))
        with self.assertRaises(t.Denied):
            t.execute('asrin',wp,'IN_PROGRESS',envelope,policy,plane,gh,lambda *a:None,SECRET)
        self.assertEqual(plane.patches,[])

    def test_ready_and_blocker_declarations_do_not_require_implementation_before_dor(self):
        for source,target in [('BACKLOG','READY'),('BACKLOG','CANCELED'),('IN_PROGRESS','BLOCKED')]:
            def without_pr(policy,plane,gh,envelope):
                envelope['evidence_refs']=[r for r in envelope['evidence_refs'] if not r.startswith('pr:')]
            result,plane,logs,gh=run_case(source=source,target=target,mutate=without_pr)
            self.assertEqual(result['result'],'VERIFIED')

    def test_assignee_and_metadata_isolation(self):
        for field,value in [('assignees',['foreign-user']),('description_html','{}')]:
            def bad(policy,plane,gh,envelope): plane.item[field]=value
            with self.assertRaises(t.Denied): run_case(mutate=bad)

    def test_arbitrary_input_body_url_and_extra_args_rejected(self):
        for payload in [{'reason':'a','evidence_refs':['https://evil']},
                        {'reason':'a','evidence_refs':['pr:1'],'body':{'assignees':['x']}},
                        {'reason':'a','evidence_refs':['pr:1/../../evil']},
                        {'reason':'a','evidence_refs':['pr:1','pr:2']}]:
            with self.assertRaises((t.Denied,ValueError)): t.parse_input(json.dumps(payload))
        for args in [[],['asrin','WP-TEST-001','DONE','extra'],['asrin','https://evil','DONE']]:
            with patch.object(t.sys,'argv',['helper']+args),patch.object(t.os,'geteuid',return_value=0),patch('sys.stdout',new_callable=io.StringIO) as out:
                self.assertEqual(t.main(),2)
                self.assertNotIn(SECRET,out.getvalue())

    def test_blocked_set_clear_preserves_other_labels_state_and_requires_resolution(self):
        for target in ['BLOCKED','UNBLOCKED']:
            result,plane,logs,gh=run_case(source='IN_PROGRESS',target=target)
            self.assertEqual(plane.item['state'],'IN_PROGRESS')
            self.assertIn('MILESTONE-LABEL',plane.item['labels'])
            self.assertEqual('BLOCKED-LABEL' in plane.item['labels'],target=='BLOCKED')
            self.assertEqual(set(plane.patches[0]),{'labels'})
        def unresolved(policy,plane,gh,envelope):
            for record in gh.comments.values():
                data=json.loads(record['body']);data['cap_plane_transition']['resolves_audit_id']='different'
                record['body']=json.dumps(data)
        with self.assertRaises(t.Denied): run_case(source='IN_PROGRESS',target='UNBLOCKED',mutate=unresolved)
        def blocked(policy,plane,gh,envelope): plane.item['labels'].append('BLOCKED-LABEL')
        with self.assertRaises(t.Denied): run_case(mutate=blocked)

    def test_terminal_workflow_is_not_resurrected_by_orthogonal_blocker_resolution(self):
        for source in ['DONE','CANCELED']:
            result,plane,logs,gh=run_case(source=source,target='UNBLOCKED')
            self.assertEqual(result['result'],'VERIFIED')
            self.assertEqual(plane.item['state'],source)
            self.assertNotIn('BLOCKED-LABEL',plane.item['labels'])
            self.assertEqual(set(plane.patches[0]),{'labels'})

    def test_old_successful_run_does_not_automatically_resolve_a_new_blocker(self):
        def old_run_no_peer(policy,plane,gh,envelope):
            gh.run_data['updated_at']='2025-12-01T00:00:00+00:00'
            envelope['evidence_refs'].remove('comment:3')
        with self.assertRaises(t.Denied): run_case(source='IN_PROGRESS',target='UNBLOCKED',mutate=old_run_no_peer)
        def fresh_run_no_peer(policy,plane,gh,envelope): envelope['evidence_refs'].remove('comment:3')
        result,*_=run_case(source='IN_PROGRESS',target='UNBLOCKED',mutate=fresh_run_no_peer)
        self.assertEqual(result['result'],'VERIFIED')

    def test_cancel_requires_explicit_real_owner_record(self):
        result,plane,logs,gh=run_case(source='BACKLOG',target='CANCELED')
        self.assertEqual(result['result'],'VERIFIED')
        def absent(policy,plane,gh,envelope):
            for record in gh.comments.values():
                data=json.loads(record['body']);data['cap_plane_transition'].pop('owner_decision')
                record['body']=json.dumps(data)
        with self.assertRaises(t.Denied): run_case(source='BACKLOG',target='CANCELED',mutate=absent)
        def not_owner(policy,plane,gh,envelope): gh.comments[2]['user']['login']='Ejlonn'
        with self.assertRaises(t.Denied): run_case(source='BACKLOG',target='CANCELED',mutate=not_owner)

    def test_no_gate_pass_from_caller_boolean_or_missing_artifact(self):
        def absent(policy,plane,gh,envelope): envelope['evidence_refs']=['pr:1']
        with self.assertRaises(t.Denied): run_case(source='BACKLOG',target='READY',mutate=absent)
        def missing(policy,plane,gh,envelope): gh.missing_artifact=True
        with self.assertRaises(t.Denied): run_case(source='VALIDATING',target='DONE',mutate=missing)
        def na(policy,plane,gh,envelope):
            for record in gh.comments.values():
                data=json.loads(record['body']);data['cap_plane_transition']['checks']['DOD-WP-01']['result']='N/A'
                record['body']=json.dumps(data)
        with self.assertRaises(t.Denied): run_case(source='VALIDATING',target='DONE',mutate=na)

    def test_real_ci_review_and_merge_predicates(self):
        for what in ['ci','draft','stale','self','mergeability']:
            def bad(policy,plane,gh,envelope):
                if what=='ci': gh.check_data[0][0]['conclusion']='failure'
                elif what=='draft': gh.pr_data['draft']=True
                elif what=='stale': gh.review_data[0]['commit_id']='c'*40
                elif what=='self': gh.review_data[0]['user']['login']='Asperant'
                else: gh.pr_data['mergeable']=None
            with self.subTest(what=what),self.assertRaises(t.Denied): run_case(source='IN_REVIEW',target='MERGE_READY',mutate=bad)
        def not_merged(policy,plane,gh,envelope): gh.pr_data['merged']=False
        with self.assertRaises(t.Denied): run_case(source='MERGE_READY',target='MERGED',mutate=not_merged)

    def test_high_risk_needs_two_current_independent_qualified_approvals(self):
        def high(policy,plane,gh,envelope):
            for record in gh.comments.values():
                data=json.loads(record['body']);assessment=data['cap_plane_transition']
                assessment.update(review_risk='high',high_risk_triggers=['authentication_authorization'],qualified_reviewers=['selorito','Yavuzgmus'])
                record['body']=json.dumps(data)
        with self.assertRaises(t.Denied): run_case(source='IN_REVIEW',target='MERGE_READY',mutate=high)
        def enough(policy,plane,gh,envelope):
            high(policy,plane,gh,envelope)
            gh.review_data.append({'user':{'login':'Yavuzgmus'},'state':'APPROVED','commit_id':HEAD})
        result,*_=run_case(source='IN_REVIEW',target='MERGE_READY',mutate=enough)
        self.assertEqual(result['result'],'VERIFIED')

    def test_pairing_author_cannot_supply_independent_approval(self):
        def paired(policy,plane,gh,envelope):
            for record in gh.comments.values():
                data=json.loads(record['body'])
                data['cap_plane_transition']['pairing_participants']=['selorito']
                record['body']=json.dumps(data)
        with self.assertRaises(t.Denied): run_case(source='IN_REVIEW',target='MERGE_READY',mutate=paired)

    def test_required_postmerge_run_is_bound_to_merge_revision(self):
        for target,source in [('VALIDATING','MERGED'),('DONE','VALIDATING')]:
            def wrong(policy,plane,gh,envelope): gh.run_data['head_sha']=HEAD
            with self.assertRaises(t.Denied): run_case(source=source,target=target,mutate=wrong)

    def test_merged_and_done_require_deleted_work_branch(self):
        for source,target in [('MERGE_READY','MERGED'),('VALIDATING','DONE')]:
            def undeleted(policy,plane,gh,envelope): gh.undeleted_branch=True
            with self.assertRaises(t.Denied): run_case(source=source,target=target,mutate=undeleted)

    def test_readback_protected_fields_and_lost_response(self):
        for field in ['corrupt','fail_readback']:
            def bad(policy,plane,gh,envelope): setattr(plane,field,True)
            with self.assertRaises(t.Denied): run_case(mutate=bad)
        def lost(policy,plane,gh,envelope): plane.response_lost=True
        result,plane,logs,gh=run_case(mutate=lost)
        self.assertEqual(result['result'],'VERIFIED')
        self.assertEqual(len(plane.patches),1)
        self.assertGreaterEqual(plane.gets,3)

    def test_idempotent_repeated_state_and_blocker_no_patch(self):
        for source,target in [('IN_PROGRESS','IN_PROGRESS'),('IN_PROGRESS','UNBLOCKED')]:
            wp,policy,plane,gh,envelope=fixture(source=source,target=target)
            plane.item['labels']=['MILESTONE-LABEL']
            result=t.execute('asrin',wp,target,envelope,policy,plane,gh,lambda *a:None,SECRET)
            self.assertEqual(result['result'],'UNCHANGED')
            self.assertEqual(plane.patches,[])

    def test_audit_failure_prevents_write_and_secret_is_not_logged(self):
        wp,policy,plane,gh,envelope=fixture()
        def broken(*args): raise OSError('disk full')
        with self.assertRaises(OSError): t.execute('asrin',wp,'IN_PROGRESS',envelope,policy,plane,gh,broken,SECRET)
        self.assertEqual(plane.patches,[])
        with self.assertRaises(t.Denied): t.append_audit({'reason':SECRET},SECRET)
        result,plane,logs,gh=run_case()
        self.assertNotIn(SECRET,json.dumps(logs))

    def test_hard_dependency_requires_producer_confirmation(self):
        def dep(policy,plane,gh,envelope):
            card=policy['contexts'][plane.item['external_id']]
            card['dependency_edges']=[{'id':'DEP-001','predecessor':{'node':'DN-ONE'},
                                      'semantics':{'strength':'HARD','blocking_stage':'START','required_readiness':'CONTRACT_READY'}}]
            policy['node_owners']['DN-ONE']='selman'
            policy['node_levels']['DN-ONE']=['DEFINED','CONTRACT_READY']
        with self.assertRaises(t.Denied): run_case(mutate=dep)
        def satisfied(policy,plane,gh,envelope):
            dep(policy,plane,gh,envelope)
            record=gh.comments[3]
            data=json.loads(record['body'])
            data['cap_plane_transition']['dependency_readiness']={'DEP-001':{'readiness':'CONTRACT_READY',
                'precise_consumer_requirement':'Actual published command fields','evidence_refs':['repo:contracts/command.json']}}
            record['body']=json.dumps(data)
        result,*_=run_case(mutate=satisfied)
        self.assertEqual(result['result'],'VERIFIED')

    def test_solo_patch_transport_has_fixed_issue_endpoint_and_minimal_body(self):
        from types import SimpleNamespace
        from unittest.mock import MagicMock
        wp,policy,plane,gh,envelope=fixture()
        class Response:
            status=200
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def read(self,limit): return json.dumps(plane.item).encode()
        client=t.Plane.__new__(t.Plane)
        client.key=SECRET;client.states=plane.states;client.blocked=plane.blocked
        client.reader=SimpleNamespace(last=0,opener=MagicMock())
        client.reader.opener.open.return_value=Response()
        for target in ['IN_PROGRESS','BLOCKED','UNBLOCKED']:
            client.reader.last=0
            client.patch(plane.item,target)
            request=client.reader.opener.open.call_args.args[0]
            self.assertEqual(request.get_method(),'PATCH')
            self.assertEqual(request.full_url,t.q.ORIGIN+t.q.PREFIX+'issues/'+plane.item['id']+'/')
            body=json.loads(request.data)
            self.assertEqual(set(body),{'labels'} if target in {'BLOCKED','UNBLOCKED'} else {'state'})
        with self.assertRaises(t.Denied): client.patch(plane.item,'https://evil')

    def test_concurrent_change_prevents_patch(self):
        wp,policy,plane,gh,envelope=fixture()
        original=plane.issue
        def changing(identity):
            if plane.gets==1: plane.item['state']='BACKLOG'
            return original(identity)
        plane.issue=changing
        with self.assertRaises(t.Denied):
            t.execute('asrin',wp,'IN_PROGRESS',envelope,policy,plane,gh,lambda *a:None,SECRET)
        self.assertEqual(plane.patches,[])

    def test_readback_failure_is_audited_without_retry(self):
        wp,policy,plane,gh,envelope=fixture()
        plane.fail_readback=True
        logs=[]
        with self.assertRaises(t.Denied):
            t.execute('asrin',wp,'IN_PROGRESS',envelope,policy,plane,gh,lambda r,k:logs.append(deepcopy(r)),SECRET)
        self.assertEqual([r['result'] for r in logs],['INTENT','UNCONFIRMED_REQUIRES_READBACK'])
        self.assertEqual(len(plane.patches),1)
        self.assertNotIn(SECRET,json.dumps(logs))

    def test_repeat_of_success_is_idempotent(self):
        wp,policy,plane,gh,envelope=fixture()
        def audit(*args): pass
        first=t.execute('asrin',wp,'IN_PROGRESS',envelope,policy,plane,gh,audit,SECRET)
        second=t.execute('asrin',wp,'IN_PROGRESS',envelope,policy,plane,gh,audit,SECRET)
        self.assertEqual(first['result'],'VERIFIED')
        self.assertEqual(second['result'],'UNCHANGED')
        self.assertEqual(len(plane.patches),1)

    def test_canonical_raw_size_bands_enforce_relative_heavy_wip_without_day_estimates(self):
        def second_heavy(policy,plane,gh,envelope):
            wp=plane.item['external_id']
            policy['contexts'][wp]['work_package']['size_band']='L (≈7–12 focused days)'
            other='WP-TEST-099'
            policy['contexts'][other]=deepcopy(policy['contexts'][wp])
            policy['contexts'][other]['work_package']['id']=other
            active=deepcopy(plane.item)
            active.update(id='other-id',external_id=other,name='['+other+'] Other active WP',state='IN_PROGRESS')
            plane.items.append(active)
        with self.assertRaises(t.Denied) as raised: run_case(mutate=second_heavy)
        self.assertEqual(raised.exception.code,'HEAVY_CORE_WIP_LIMIT')
        def actual_small_band(policy,plane,gh,envelope):
            policy['contexts'][plane.item['external_id']]['work_package']['size_band']='S (≈1–3 focused days)'
        result,*_=run_case(mutate=actual_small_band)
        self.assertEqual(result['result'],'VERIFIED')

    def test_unscheduled_missing_ci_and_missing_done_peer_fail_closed(self):
        def unscheduled(policy,plane,gh,envelope): policy['contexts'][plane.item['external_id']]['cycle_ids']=[]
        with self.assertRaises(t.Denied): run_case(source='BACKLOG',target='READY',mutate=unscheduled)
        def missing_ci(policy,plane,gh,envelope): gh.check_data=([],[])
        with self.assertRaises(t.Denied): run_case(source='IN_PROGRESS',target='IN_REVIEW',mutate=missing_ci)
        def no_peer(policy,plane,gh,envelope): envelope['evidence_refs'].remove('comment:3')
        with self.assertRaises(t.Denied): run_case(source='VALIDATING',target='DONE',mutate=no_peer)

    def test_milestone_dependency_is_not_blindly_a_wp_closure_blocker(self):
        def milestone(policy,plane,gh,envelope):
            policy['contexts'][plane.item['external_id']]['dependency_edges']=[{
                'id':'DEP-001','predecessor':{'node':'MS-ONE'},
                'semantics':{'strength':'HARD','blocking_stage':'MILESTONE_EXIT','required_readiness':None}}]
        with self.assertRaises(t.Denied): run_case(source='VALIDATING',target='DONE',mutate=milestone)
        def assessed(policy,plane,gh,envelope):
            milestone(policy,plane,gh,envelope)
            record=gh.comments[3]
            data=json.loads(record['body'])
            data['cap_plane_transition']['dependency_stage_dispositions']={'DEP-001':{
                'applies_to_wp_completion':False,'reason':'This gate belongs to the later milestone, not this WP closure',
                'evidence_refs':['repo:docs/05_Dependency_Graph.md']}}
            record['body']=json.dumps(data)
        result,*_=run_case(source='VALIDATING',target='DONE',mutate=assessed)
        self.assertEqual(result['result'],'VERIFIED')

    def test_launcher_rejects_invalid_arguments_before_sudo(self):
        for args in [[],['https://evil','DONE'],['WP-TEST-001','DELETE'],['WP-TEST-001','DONE','extra']]:
            result=subprocess.run(['/bin/sh',str(HERE/'cap-plane-transition')]+args,
                                  env={'CAP_PROFILE':'asrin','PATH':'/usr/bin:/bin'},capture_output=True,text=True)
            self.assertEqual(result.returncode,2)
            self.assertEqual(json.loads(result.stdout)['result'],'DENIED')
            self.assertEqual(result.stderr,'')

    def test_actual_secret_in_input_never_reaches_stdout_or_audit(self):
        wp,policy,plane,gh,envelope=fixture()
        envelope['reason']=SECRET
        input_stream=type('Input',(),{'buffer':io.BytesIO(json.dumps(envelope).encode())})()
        with patch.object(t.sys,'argv',['helper','asrin',wp,'IN_PROGRESS']), \
             patch.object(t.os,'geteuid',return_value=0),patch.object(t.os.environ,'clear'), \
             patch.object(t.sys,'stdin',input_stream),patch.object(t.Path,'read_text',side_effect=[json.dumps(policy),json.dumps({'api_key':SECRET})]), \
             patch('sys.stdout',new_callable=io.StringIO) as output,patch.object(t,'append_audit') as audit:
            self.assertEqual(t.main(),2)
        self.assertNotIn(SECRET,output.getvalue())
        self.assertEqual(json.loads(output.getvalue())['reason_code'],'SECRET_IN_INPUT')
        audit.assert_not_called()

    def test_missing_reason_evidence_input_is_explicitly_rejected(self):
        with self.assertRaises(t.Denied) as raised: t.parse_input(b'')
        self.assertEqual(raised.exception.code,'REASON_AND_EVIDENCE_JSON_REQUIRED_ON_STDIN')

    def test_policy_source_drift_fails_closed(self):
        policy={'source_manifest':{'docs/08_Definition_of_Ready_and_Done.md':'wrong-sha'}}
        with patch.object(t.Path,'read_bytes',return_value=b'changed canonical bytes'),self.assertRaises(t.Denied):
            t.verify_policy_sources(policy)

    def test_gitHub_transport_always_get_drops_root_and_profile_login_is_checked(self):
        from types import SimpleNamespace
        account=SimpleNamespace(pw_uid=1000,pw_gid=1000,pw_dir='/home/ailab')
        for profile,login in t.GITHUB.items():
            response=subprocess.CompletedProcess([],0,json.dumps({'login':login}).encode(),b'')
            with patch.object(t.subprocess,'run',return_value=response) as called,patch.object(t.pwd,'getpwnam',return_value=account):
                gh=t.GitHub(profile)
            args=called.call_args
            self.assertIn('GET',args.args[0])
            self.assertEqual(args.kwargs['user'],1000)
            self.assertEqual(args.kwargs['env']['GH_CONFIG_DIR'],f'/srv/ailab/user-profiles/{profile}/gh')
            self.assertNotIn('PLANE_API_KEY',args.kwargs['env'])
        response=subprocess.CompletedProcess([],0,b'{"login":"Asperant"}',b'')
        with patch.object(t.subprocess,'run',return_value=response),patch.object(t.pwd,'getpwnam',return_value=account),self.assertRaises(t.Denied):
            t.GitHub('yavuz')


if __name__=='__main__': unittest.main()
