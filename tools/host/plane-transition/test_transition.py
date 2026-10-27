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


def pr_body(wp):
    return f"""## Identity and scope
WP/control ID: {wp}
Plane reference: canonical {wp}
Requirements: NONE — fixture has no source requirements
Architecture surfaces and authority boundaries: Existing approved scope only
Change class / review risk: C1 / CR-2 (normal-risk)
Contract/compatibility and migration impact: No contract or migration impact
Security/authority and dataset/model impact: No authentication/authorization, protected execution, secrets, security infrastructure, major authority or data/model changes
Observability impact: No runtime impact
Pairing participants: none
## Summary
One coherent canonical WP change; scope excludes other WPs. Author self-reviewed; no secrets or debug artifacts.
## Validation
Commands, environment and actual results: pytest passed locally; actual CI is checked live
Negative/failure paths exercised: Actual failure and malformed-input cases tested
Evidence paths and identity bindings: [Actual run](evidence/test.json)
Post-merge validation plan: Run validation at actual merge revision; Merged != Done
Rollout/rollback notes: Reviewed Git revert if required
Known limitations: Fixture demonstrates gates, not product acceptance
Docs impact: Runbook updated within WP
Trace updates and prior evidence staleness: Requirements/code/test links recorded; prior evidence remains revision-bound
"""


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
                      'body':pr_body(wp),'changed_files':2,'draft':source=='IN_REVIEW' and target=='IN_PROGRESS',
                      'state':'closed' if post else 'open', 'merged':post,'merged_at':'2026-01-02T00:00:00+00:00' if post else None,
                      'merge_commit_sha':MERGE if post else None,
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
        self.comments={2:{'updated_at':'2026-01-02T00:00:00+00:00','user':{'login':owner},'body':json.dumps({'cap_plane_transition':record})},
                       3:{'updated_at':'2026-01-02T00:00:00+00:00','user':{'login':peer},'body':json.dumps({'cap_plane_transition':record})}}
        self.review_data=[{'user':{'login':peer},'state':'APPROVED','commit_id':('c'*40 if source=='MERGE_READY' and target=='IN_REVIEW' else HEAD)}]
        self.run_data={'head_sha':sha,'head_branch':'main','event':'push',
                       'status':'in_progress' if target=='VALIDATING' else 'completed','conclusion':'success','updated_at':'2026-01-02T00:00:00+00:00'}
        self.check_data=([{'name':'projectctl','status':'completed','conclusion':'success'}],[])
        self.artifacts=[]
        self.missing_artifact=False
        self.documents={}
        self.repo_files={}
        self.file_rows=[{'filename':'src/project.py'},{'filename':'evidence/test.json'}]
    def evidence_text(self,path,sha):
        if path not in self.documents: raise t.Denied('ASSESSMENT_CONTENT_UNAVAILABLE')
        self.artifact('repo:'+path,sha)
        return self.documents[path]
    def started_commit(self,wp,sha,profile):
        if getattr(self,'bad_work_commit',False): raise t.Denied('NO_IMPLEMENTATION_CHANGE_FROM_MAIN')
        self.started=(wp,sha,profile)
    def main_sha(self): return HEAD
    def pr(self,number): return deepcopy(self.pr_data)
    def fresh_pr(self,number): return deepcopy(self.pr_data)
    def comment(self,number): return deepcopy(self.comments[number])
    def run(self,number): return deepcopy(self.run_data)
    def fresh_run(self,number): return deepcopy(self.run_data)
    def checks(self,sha): return deepcopy(self.check_data)
    def reviews(self,number): raise AssertionError('Advisory review API must not be queried')
    def files(self,pr):
        return self.file_rows
    def technical_ci(self,sha,policy,extra=()):
        if getattr(self,'failed_technical_step',False): raise t.Denied('REQUIRED_TECHNICAL_STEP_NOT_PASSED')
    def current_main(self,pr):
        if getattr(self,'behind_main',False): raise t.Denied('PR_BEHIND_CURRENT_MAIN')
    def contributors(self,number): return {self.pr_data['user']['login'].casefold()}
    def merged_shape(self,pr):
        if getattr(self,'undeleted_branch',False): raise t.Denied('MERGED_BRANCH_NOT_DELETED')
    def artifact(self,ref,sha):
        if self.missing_artifact: raise t.Denied('ARTIFACT_MISSING')
        self.artifacts.append((ref,sha))
    def repository_file(self,path,sha,limit=65536):
        if path not in self.repo_files:
            raise t.Denied('ARTIFACT_NOT_A_FILE')
        raw,blob=self.repo_files[path]
        return raw,blob
    def ancestor(self,base,head):
        if getattr(self,'stale_ancestry',False):
            raise t.Denied('PRODUCER_MERGE_NOT_IN_MAIN_ANCESTRY')


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
    policy={'contexts':contexts,'source_manifest':{'docs/08':'canonical-sha'},'required_ci':['projectctl'], 'required_technical_steps':['Canonical validation','Changed-scope focused tests and regressions','Requirement catalog lint','Whitespace and repository hygiene'],
            'review_policy':json.loads((HERE.parents[2]/'09_change/development_review_policy.json').read_text()),
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
    if target=='DONE':
        policy['required_aggregate_ci']=['ci-gate']
        gh.check_data[0].append({'name':'ci-gate','status':'completed','conclusion':'success',
                                 'details_url':'https://github.com/Asperant/critical-aerospace-manufacturing/actions/runs/12/job/22'})
    if mutate: mutate(policy,plane,gh,envelope)
    logs=[]
    def audit(record,key):
        encoded=json.dumps(record)
        if key in encoded: raise t.Denied('SECRET_IN_AUDIT_INPUT')
        logs.append(deepcopy(record))
    result=t.execute(profile,wp,target,envelope,policy,plane,gh,audit,SECRET,
                     {'result':'VERIFIED','operation':'BLOCKED','audit_id':'previous-blocker','timestamp':'2026-01-01T00:00:00+00:00'},
                     {'result':'VERIFIED','operation':'MERGE_READY','observed_pr_head':'c'*40})
    return result,plane,logs,gh


class TransitionTests(unittest.TestCase):
    def test_ready_transition_consumes_check_ready_canonical_assessment(self):
        def canonical_ready(policy, plane, gh, envelope):
            wp=plane.item['external_id']
            rows='\n'.join(f'| DOR-TASK-{number:02d} | PASS | Canonical scope evidence. |'
                           for number in range(1,12))
            rows+='\n| DOR-WP-01 | PASS | Canonical scope evidence. |'
            gh.repo_files[f'evidence/{wp}/READY.md']=(
                f'Accountable owner: Asrın Dündar (Asperant)\n\n{rows}\n'.encode(),
                'c'*40)
            envelope['evidence_refs']=['pr:1']
        result,plane,_,gh=run_case(source='BACKLOG',target='READY',mutate=canonical_ready)
        self.assertEqual(result['result'],'VERIFIED')
        self.assertEqual(plane.item['state'],'READY')
        self.assertIn(('repo:evidence/'+plane.item['external_id']+'/READY.md',HEAD),gh.artifacts)

    def automatic_fixture(self):
        wp,policy,plane,gh,envelope=fixture()
        producer_wp=next(k for k,v in policy['contexts'].items()
                         if v['work_package']['primary_owner']['canonical_name']=='Selman Özdemir')
        node='DN-TEST-CONTRACT'
        successor='DN-TEST-CONSUMER'
        edge={'id':'DEP-900','predecessor':{'node':node,'owner':'Selman'},
              'successor':{'node':successor,'owner':'Asrın'},'precise_requirement':'Exact v1 command fields',
              'semantics':{'kind':'CONTRACT','strength':'HARD','blocking_stage':'START','required_readiness':'CONTRACT_READY'}}
        context=policy['contexts'][wp]
        context['dependency_edges']=[edge]
        policy.update(auto_readiness_attestation_schema='auto-readiness-attestation-v1',
                      node_owners={node:'selman',successor:'asrin'},
                      node_levels={node:['DEFINED','CONTRACT_READY']},
                      node_requirements={node:['FR-TEST-001']},node_producers={node:[producer_wp]},
                      scope_projections={producer_wp:{'scope':'canonical'}})
        policy['required_aggregate_ci']=[]
        files={'contracts/test.json':'1'*40,'contracts/test.schema.json':'2'*40,
               'contracts/test.fixture.json':'3'*40,'tests/test_contract.py':'4'*40,
               'docs/trace.md':'5'*40}
        for path,blob in files.items():
            gh.repo_files[path]=(b'content',blob)
        basis={'schema':'auto-readiness-semantic-basis-v1','node':node,'level':'CONTRACT_READY',
               'producer':{'owner':'Selman Özdemir','login':'selorito'},'producer_wp':producer_wp,
               'producer_pr':9,'producer_merge_sha':MERGE,
               'scope_projections':{producer_wp:t.evidence_digest({'scope':'canonical'})},
               'certification':'CONTRACT_READY','semantic_basis':{
                   'stability':'v1 interface is stable','consumer_usability':'Exact fields usable by declared consumer',
                   'compatibility_intent':'Compatible v1 evolution','scope_meaning':'Contract boundary is unchanged'},
               'consumer_edges':['DEP-900'],'artifacts':[
                   {'path':'contracts/test.json','blob':files['contracts/test.json'],'role':'contract'},
                   {'path':'contracts/test.schema.json','blob':files['contracts/test.schema.json'],'role':'schema'},
                   {'path':'contracts/test.fixture.json','blob':files['contracts/test.fixture.json'],'role':'fixture'}],
               'tests':[{'test_id':'TEST-CONTRACT','check':'t1-contract','path':'tests/test_contract.py','blob':files['tests/test_contract.py']}],
               'trace':[{'requirement':'FR-TEST-001','path':'docs/trace.md','blob':files['docs/trace.md']}]}
        basis_path=f'evidence/readiness/{node}.json'
        basis_blob='6'*40
        def store():
            gh.repo_files[basis_path]=(json.dumps(basis).encode(),basis_blob)
        store()
        gh.pr_data.update(number=9,user={'login':'selorito'},merged=True,merge_commit_sha=MERGE,
                          changed_files=1,state='closed')
        gh.file_rows=[{'filename':basis_path,'status':'added'}]
        gh.check_data=([{'name':'projectctl','head_sha':HEAD,'status':'completed','conclusion':'success'},
                        {'name':'t1-contract','head_sha':HEAD,'status':'completed','conclusion':'success'}],[])
        return context,edge,policy,gh,basis,store

    def test_automatic_contract_readiness_is_accepted_by_dependency_path(self):
        context,edge,policy,gh,basis,store=self.automatic_fixture()
        proof=t.automatic_readiness_attestation(gh,context,edge,HEAD,policy)
        self.assertEqual(proof['status'],'PASS')
        self.assertRegex(proof['proof_digest'],r'^[0-9a-f]{64}$')
        t.dependencies(gh,[],context,{},HEAD,policy)

    def test_automatic_contract_readiness_fail_closed_cases(self):
        cases={
            'precise':lambda c,e,p,g,b: e.update(precise_requirement=None),
            'semantic':lambda c,e,p,g,b: b.update(semantic_basis={}),
            'noncertification':lambda c,e,p,g,b: b.update(certification='NOT_CERTIFIED'),
            'blob':lambda c,e,p,g,b: b['artifacts'][0].update(blob='f'*40),
            'sha':lambda c,e,p,g,b: setattr(g,'main_sha',lambda:'e'*40),
            'test':lambda c,e,p,g,b: g.check_data[0][1].update(conclusion='failure'),
            'owner':lambda c,e,p,g,b: b.update(producer={'owner':'Selman Özdemir','login':'foreign'}),
            'scope':lambda c,e,p,g,b: p['scope_projections'][b['producer_wp']].update(scope='changed'),
        }
        expected={'precise':'PRECISE_CONSUMER_REQUIREMENT_MISSING','semantic':'ATTRIBUTABLE_SEMANTIC_BASIS_MISSING',
                  'noncertification':'EXPLICIT_NON_CERTIFICATION','blob':'STALE_ARTIFACTS_BLOB',
                  'sha':'SOURCE_SHA_NOT_CURRENT_MAIN','test':'SHA_BOUND_REQUIRED_TEST_NOT_GREEN',
                  'owner':'PRODUCER_ATTRIBUTION_MISMATCH','scope':'PRODUCER_SCOPE_PROJECTION_MISMATCH'}
        for name,change in cases.items():
            context,edge,policy,gh,basis,store=self.automatic_fixture()
            change(context,edge,policy,gh,basis)
            store()
            result=t.automatic_readiness_attestation(gh,context,edge,HEAD,policy)
            with self.subTest(name=name):
                self.assertEqual(result['status'],'UNKNOWN')
                self.assertIn(expected[name],result['reasons'])

    def runtime_fixture(self):
        wp, policy, plane, gh, envelope = fixture()
        producer_wp = next(k for k, v in policy['contexts'].items()
                           if v['work_package']['primary_owner']['canonical_name'] == 'Yavuz Gümüş')
        node = 'DN-PLAT-COMPOSE'
        successor = 'DN-RT-PG'
        edge = {'id': 'DEP-006', 'predecessor': {'node': node, 'owner': 'Yavuz'},
                'successor': {'node': successor, 'owner': 'Yavuz'},
                'precise_requirement': 'local PostgreSQL profile up',
                'semantics': {'kind': 'RUNTIME', 'strength': 'HARD', 'blocking_stage': 'START',
                              'required_readiness': 'SKELETON_READY'}}
        context = policy['contexts'][wp]
        context['dependency_edges'] = [edge]
        policy.update(auto_readiness_attestation_schema='auto-readiness-attestation-v1',
                      node_owners={node: 'yavuz', successor: 'yavuz'},
                      node_levels={node: ['DEFINED', 'SKELETON_READY', 'INTEGRATION_READY']},
                      node_producers={node: [producer_wp]})
        files = {
            'evidence/WP-PLAT-001/README.md': ('Owner: Yavuz Gümüş\n', '1' * 40),
            'evidence/WP-PLAT-001/RUN-PLAT-001-DEV-001/record.json':
                (json.dumps({'work_package': 'WP-PLAT-001', 'boundary_mode': 'REAL',
                             'steps': [{'step': 'smoke', 'exit_code': 0}]}), '2' * 40),
            'evidence/WP-PLAT-001/RUN-PLAT-001-DEV-001/status.log.txt':
                ('cap-platform-postgres-1 postgres:18.6-alpine healthy\n', '3' * 40),
            'evidence/WP-PLAT-001/RUN-PLAT-001-DEV-001/smoke.log.txt':
                ('smoke platform-infra: PASS in 1.1 s\n', '4' * 40),
        }
        for path, (content, blob) in files.items():
            gh.repo_files[path] = (content.encode(), blob)
        basis = {'schema': 'auto-runtime-readiness-basis-v1', 'node': node,
                 'level': 'SKELETON_READY', 'producer_wp': producer_wp,
                 'producer_pr': 53, 'producer_merge_sha': MERGE,
                 'consumer_edges': ['DEP-006'], 'consumer_wps': {'DEP-006': wp},
                 'checks': [
                     {'path': 'evidence/WP-PLAT-001/README.md', 'blob': '1' * 40,
                      'kind': 'text_contains', 'value': 'Owner: Yavuz Gümüş'},
                     {'path': 'evidence/WP-PLAT-001/RUN-PLAT-001-DEV-001/record.json', 'blob': '2' * 40,
                      'kind': 'json_equals', 'field': 'work_package', 'value': 'WP-PLAT-001'},
                     {'path': 'evidence/WP-PLAT-001/RUN-PLAT-001-DEV-001/record.json', 'blob': '2' * 40,
                      'kind': 'json_equals', 'field': 'steps[0].exit_code', 'value': 0},
                     {'path': 'evidence/WP-PLAT-001/RUN-PLAT-001-DEV-001/status.log.txt', 'blob': '3' * 40,
                      'kind': 'text_contains', 'value': 'healthy'},
                     {'path': 'evidence/WP-PLAT-001/RUN-PLAT-001-DEV-001/smoke.log.txt', 'blob': '4' * 40,
                      'kind': 'text_contains', 'value': 'smoke platform-infra: PASS'},
                 ]}
        basis_path = f'evidence/readiness/{node}.json'
        gh.repo_files[basis_path] = (json.dumps(basis).encode(), '5' * 40)
        gh.pr_data.update(number=53, user={'login': 'Yavuzgmus'}, merged=True,
                          merge_commit_sha=MERGE, state='closed')
        gh.file_rows = [{'filename': path, 'status': 'added'} for path in files]
        return context, edge, policy, gh, basis

    def test_automatic_runtime_skeleton_readiness_is_accepted(self):
        context, edge, policy, gh, basis = self.runtime_fixture()
        proof = t.automatic_readiness_attestation(gh, context, edge, HEAD, policy)
        self.assertEqual(proof['status'], 'PASS')
        self.assertEqual(proof['level'], 'SKELETON_READY')
        t.dependencies(gh, [], context, {}, HEAD, policy)

    def test_automatic_runtime_readiness_fails_closed_on_stale_or_missing_health(self):
        context, edge, policy, gh, basis = self.runtime_fixture()
        basis['checks'][-1]['blob'] = 'f' * 40
        gh.repo_files['evidence/readiness/DN-PLAT-COMPOSE.json'] = (json.dumps(basis).encode(), '5' * 40)
        result = t.automatic_readiness_attestation(gh, context, edge, HEAD, policy)
        self.assertEqual(result['status'], 'UNKNOWN')
        self.assertIn('STALE_RUNTIME_EVIDENCE_BLOB', result['reasons'])
        context, edge, policy, gh, basis = self.runtime_fixture()
        gh.repo_files['evidence/WP-PLAT-001/RUN-PLAT-001-DEV-001/smoke.log.txt'] = (b'not available', '4' * 40)
        result = t.automatic_readiness_attestation(gh, context, edge, HEAD, policy)
        self.assertEqual(result['status'], 'UNKNOWN')
        self.assertIn('RUNTIME_HEALTH_OR_SMOKE_NOT_PASS', result['reasons'])

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
                if target in {'READY','DONE'}: self.assertTrue(gh.artifacts)

    def test_mechanical_forward_transitions_need_no_confirmation_comment(self):
        for source,target in [('READY','IN_PROGRESS'),('IN_PROGRESS','IN_REVIEW'),
                              ('IN_REVIEW','MERGE_READY'),('MERGE_READY','MERGED'),('MERGED','VALIDATING')]:
            def no_comments(policy,plane,gh,envelope):
                envelope['evidence_refs']=['pr:1','run:4']
                gh.comments={}
            with self.subTest(source=source):
                result,plane,logs,gh=run_case(source=source,target=target,mutate=no_comments)
                self.assertEqual(result['result'],'VERIFIED')
                self.assertEqual(len(plane.patches),1)
                if target not in {'MERGE_READY','MERGED'}: self.assertFalse(gh.artifacts)

    def test_work_can_start_on_real_owned_wp_branch_before_pr_exists(self):
        def commit(policy,plane,gh,envelope): envelope['evidence_refs']=['commit:'+HEAD]
        result,plane,logs,gh=run_case(mutate=commit)
        self.assertEqual(result['result'],'VERIFIED')
        self.assertEqual(gh.started,(plane.item['external_id'],HEAD,'asrin'))
        def missing(policy,plane,gh,envelope):
            commit(policy,plane,gh,envelope);gh.bad_work_commit=True
        with self.assertRaises(t.Denied): run_case(mutate=missing)
        with self.assertRaises(t.Denied):
            t.parse_input(json.dumps({'reason':'Two revision sources','evidence_refs':['commit:'+HEAD,'pr:1']}))

    def test_start_commit_contract_rejects_foreign_missing_ambiguous_or_unchanged(self):
        wp,policy,plane,gh,envelope=fixture()
        for what in ['foreign','missing','ambiguous','unchanged']:
            branch={'ref':'refs/heads/wp/'+wp+'-test','object':{'sha':HEAD}}
            responses=[[branch],{'author':{'login':'Asperant'}},{'ahead_by':1,'files':[{'filename':'a.py'}]}]
            if what=='foreign': responses[1]['author']['login']='Ejlonn'
            if what=='missing': responses[0]=[]
            if what=='ambiguous': responses[0]=[branch,branch]
            if what=='unchanged': responses[2]['ahead_by']=0
            client=t.GitHub.__new__(t.GitHub)
            with patch.object(client,'_get',side_effect=responses),self.subTest(what=what),self.assertRaises(t.Denied):
                client.started_commit(wp,HEAD,'asrin')

    def test_wp_gov_001_pr7_review_regression(self):
        wp,policy,plane,gh,envelope=fixture(source='IN_PROGRESS',target='IN_REVIEW')
        canonical='WP-GOV-001'
        policy['contexts'][canonical]=policy['contexts'].pop(wp)
        policy['contexts'][canonical]['work_package']['id']=canonical
        for item in (plane.item,plane.items[0]):
            item.update(external_id=canonical,name='['+canonical+'] Requirement catalog',
                        description_html=json.dumps({'canonical_wp_id':canonical,'canonical_owner':'Asrın Dündar'}))
        gh.pr_data.update(number=7,title='[WP-GOV-001] Requirement catalog',
                          body=pr_body(canonical)+'\nNo confirmation JSON.')
        gh.pr_data['head']['ref']='wp/WP-GOV-001-requirement-catalog'
        envelope['evidence_refs']=['pr:7']
        gh.comments={};gh.review_data=[]
        logs=[]
        result=t.execute('asrin',canonical,'IN_REVIEW',envelope,policy,plane,gh,lambda r,k:logs.append(deepcopy(r)),SECRET)
        self.assertEqual(result['result'],'VERIFIED')
        self.assertEqual(plane.patches,[{'state':'IN_REVIEW'}])

    def test_unrelated_plain_comment_is_not_a_confirmation_protocol_error(self):
        def ordinary(policy,plane,gh,envelope):
            for comment in gh.comments.values(): comment['body']='Thanks, reviewing the implementation.'
        result,*_=run_case(source='IN_PROGRESS',target='IN_REVIEW',mutate=ordinary)
        self.assertEqual(result['result'],'VERIFIED')

    def test_review_presence_never_required_but_real_technical_guards_remain(self):
        for what in ['draft','closed','ci','blocked']:
            def invalid(policy,plane,gh,envelope):
                envelope['evidence_refs']=['pr:1'];gh.review_data=[];gh.pr_data['requested_reviewers']=[]
                if what=='draft': gh.pr_data['draft']=True
                if what=='closed': gh.pr_data['state']='closed'
                if what=='ci': gh.check_data[0][0]['conclusion']='failure'
                if what=='blocked': plane.item['labels'].append(plane.blocked)
            with self.subTest(what=what),self.assertRaises(t.Denied):
                run_case(source='IN_PROGRESS',target='IN_REVIEW',mutate=invalid)

    def test_native_dor_dod_checklists_without_custom_json(self):
        for source,target in [('BACKLOG','READY'),('VALIDATING','DONE')]:
            def native(policy,plane,gh,envelope):
                wp=plane.item['external_id'];sha=MERGE if target=='DONE' else HEAD
                for comment in gh.comments.values():
                    old=json.loads(comment['body'])['cap_plane_transition']
                    comment['body']=wp+' '+sha+'\n'+'\n'.join(
                        '- [x] '+identity+': '+check['reason']+' '+check['evidence_refs'][0]
                        for identity,check in old['checks'].items())
                    comment['issue_url']='https://api.github.com/'+t.REPO+'/issues/1'
            with self.subTest(target=target):
                result,*_=run_case(source=source,target=target,mutate=native)
                self.assertEqual(result['result'],'VERIFIED')

    def test_native_pr_and_review_dod_evidence_no_duplicate_comment(self):
        def native(policy,plane,gh,envelope):
            checks=json.loads(gh.comments[2]['body'])['cap_plane_transition']['checks']
            text='\n'.join('| '+k+' | PASS | Existing evaluation repo:evidence/result.md |' for k in checks)
            gh.pr_data['body']+='\n'+text
            gh.review_data[0]['body']=text
            envelope['evidence_refs']=['pr:1','run:4'];gh.comments={}
        result,*_=run_case(source='VALIDATING',target='DONE',mutate=native)
        self.assertEqual(result['result'],'VERIFIED')

    def test_existing_repository_assessment_is_reused_by_owner_and_reviewer(self):
        def linked(policy,plane,gh,envelope):
            checks=json.loads(gh.comments[2]['body'])['cap_plane_transition']['checks']
            gh.documents['evidence/accepted-assessment.md']='\n'.join(
                '| '+k+' | PASS | Existing analysis [result](evidence/result.json) |' for k in checks)
            gh.pr_data['body']+='\nAssessment: [accepted evidence](evidence/accepted-assessment.md)'
            gh.review_data[0]['body']='Reviewed assessment: [evidence](evidence/accepted-assessment.md)'
            gh.comments={};envelope['evidence_refs']=['pr:1','run:4']
        result,plane,logs,gh=run_case(source='VALIDATING',target='DONE',mutate=linked)
        self.assertEqual(result['result'],'VERIFIED')
        self.assertIn(('repo:evidence/accepted-assessment.md',MERGE),gh.artifacts)

    def test_native_dependency_producer_assessment_without_policy_json(self):
        def native(policy,plane,gh,envelope):
            wp=plane.item['external_id']
            policy['contexts'][wp]['dependency_edges']=[{'id':'DEP-001','predecessor':{'node':'DN-ONE'},
                'semantics':{'strength':'HARD','blocking_stage':'START','required_readiness':'CONTRACT_READY'}}]
            policy['node_owners']['DN-ONE']='selman';policy['node_levels']['DN-ONE']=['DEFINED','CONTRACT_READY']
            gh.comments[3].update(body=wp+' '+HEAD+'\n| DEP-001 | CONTRACT_READY | Command fields [contract](contracts/command.json) |',
                                  issue_url='https://api.github.com/'+t.REPO+'/issues/1')
            envelope['evidence_refs']=['pr:1','comment:3']
        result,*_=run_case(mutate=native)
        self.assertEqual(result['result'],'VERIFIED')

    def test_native_owner_cancel_and_blocker_notes(self):
        for source,target in [('BACKLOG','CANCELED'),('IN_PROGRESS','BLOCKED'),('IN_PROGRESS','UNBLOCKED')]:
            def native(policy,plane,gh,envelope):
                for comment in gh.comments.values():
                    note=plane.item['external_id']+' '+HEAD+'\n'
                    if target=='CANCELED': note+='Owner decision: CANCEL\n'
                    elif target=='BLOCKED':
                        note+='Blocker owner: asrin\nExternal dependency: Upstream service outage\n'
                        note+='Reason: Upstream outage observed; [incident](evidence/incident.md)\n'
                    else:
                        note+='Resolves blocker: previous-blocker\n'
                        note+='Reason: Incident resolved; [result](evidence/resolution.md)\n'
                    gh.documents['evidence/incident.md']='Recorded upstream incident.'
                    gh.documents['evidence/resolution.md']='Recorded actual incident resolution.'
                    comment.update(body=note,issue_url='https://api.github.com/'+t.REPO+'/issues/1')
            with self.subTest(target=target):
                result,*_=run_case(source=source,target=target,mutate=native)
                self.assertEqual(result['result'],'VERIFIED')

    def test_semantic_native_evidence_wrong_author_revision_missing_or_ambiguous_denied(self):
        for what in ['author','revision','coverage','duplicate']:
            def bad(policy,plane,gh,envelope):
                wp=plane.item['external_id']
                text=wp+' '+(HEAD if what!='revision' else 'f'*40)+'\n| DOR-TASK-01 | PASS | Real evidence repo:evidence/result.md |'
                if what=='duplicate': text+='\n| DOR-TASK-01 | PASS | Conflicting second assessment repo:evidence/other.md |'
                gh.comments[2].update(body=text,issue_url='https://api.github.com/'+t.REPO+'/issues/1')
                if what=='author': gh.comments[2]['user']['login']='Ejlonn'
                envelope['evidence_refs']=['pr:1','comment:2']
            with self.subTest(what=what),self.assertRaises(t.Denied):
                run_case(source='BACKLOG',target='READY',mutate=bad)

    def test_review_risk_metadata_is_not_a_workflow_input(self):
        for risk in ['CR-0','CR-1','CR-2','CR-3','CR-4','UNKNOWN ADVISORY CLASSIFICATION']:
            def advisory(policy,plane,gh,envelope):
                gh.pr_data['body']=gh.pr_data['body'].replace('CR-2 (normal-risk)',risk)
                gh.review_data=[];gh.pr_data['requested_reviewers']=[]
            result,*_=run_case(source='IN_REVIEW',target='MERGE_READY',mutate=advisory)
            self.assertEqual(result['result'],'VERIFIED')

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

    def test_unblock_needs_actual_fresh_resolution_not_a_reviewer(self):
        def stale(policy,plane,gh,envelope):
            gh.run_data['updated_at']='2025-12-01T00:00:00+00:00'
            gh.comments[2]['updated_at']='2025-12-01T00:00:00+00:00'
            envelope['evidence_refs'].remove('comment:3')
        with self.assertRaises(t.Denied): run_case(source='IN_PROGRESS',target='UNBLOCKED',mutate=stale)
        def current_record(policy,plane,gh,envelope):
            envelope['evidence_refs']=['pr:1','comment:2']
            gh.review_data=[]
        result,*_=run_case(source='IN_PROGRESS',target='UNBLOCKED',mutate=current_record)
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

    def test_normal_risk_zero_approvals_and_optional_review_request(self):
        for classification in ['CR-0','CR-1','CR-2','CR-4']:
            for source,target in [('IN_PROGRESS','IN_REVIEW'),('IN_REVIEW','MERGE_READY')]:
                def no_review(policy,plane,gh,envelope):
                    gh.pr_data['body']=gh.pr_data['body'].replace('CR-2',classification)
                    gh.review_data=[];gh.comments={};gh.pr_data['requested_reviewers']=[]
                    envelope['evidence_refs']=['pr:1']
                with self.subTest(classification=classification,target=target):
                    result,*_=run_case(source=source,target=target,mutate=no_review)
                    self.assertEqual(result['result'],'VERIFIED')

    def test_native_multiline_pr_fields_are_not_missing_declarations(self):
        def multiline(policy,plane,gh,envelope):
            gh.review_data=[]
            gh.pr_data['body']=gh.pr_data['body'].replace('Known limitations: Fixture demonstrates gates, not product acceptance',
                '**Known limitations and unresolved findings:**\n\n- Fixture demonstrates gates, not product acceptance\n- Post-merge acceptance is still pending')
        result,*_=run_case(source='IN_REVIEW',target='MERGE_READY',mutate=multiline)
        self.assertEqual(result['result'],'VERIFIED')

    def test_current_template_explicit_no_high_risk_trigger(self):
        def normal(policy,plane,gh,envelope):
            gh.review_data=[]
            gh.pr_data['body']+='\nActual high-risk triggers (normal approvals 0 / high approvals 2): NONE — ordinary tooling'
        result,*_=run_case(source='IN_REVIEW',target='MERGE_READY',mutate=normal)
        self.assertEqual(result['result'],'VERIFIED')

    def test_normal_zero_approvals_still_requires_scope_dor_dod_and_artifacts(self):
        for missing in ['scope','requirements','tests','negative','trace','evidence','artifact','non_draft']:
            def bad(policy,plane,gh,envelope):
                gh.review_data=[]
                if missing=='scope': gh.pr_data['title']+=' WP-TEST-002'
                elif missing=='requirements':
                    policy['contexts'][plane.item['external_id']]['work_package']['requirement_refs']=['FR-GOV-001']
                elif missing=='artifact': gh.missing_artifact=True
                elif missing=='non_draft': gh.pr_data['draft']=True
                else:
                    labels={'tests':'Commands, environment and actual results:',
                            'negative':'Negative/failure paths exercised:', 'trace':'Trace updates',
                            'evidence':'Evidence paths and identity bindings:'}
                    gh.pr_data['body']='\n'.join(line for line in gh.pr_data['body'].splitlines() if not line.startswith(labels[missing]))
            with self.subTest(missing=missing),self.assertRaises(t.Denied):
                run_case(source='IN_REVIEW',target='MERGE_READY',mutate=bad)

    def test_aggregate_review_blocked_metadata_is_not_a_technical_gate(self):
        def advisory(policy,plane,gh,envelope):
            gh.pr_data['mergeable_state']='blocked';gh.pr_data['mergeable']=True
        result,*_=run_case(source='IN_REVIEW',target='MERGE_READY',mutate=advisory)
        self.assertEqual(result['result'],'VERIFIED')

    def test_optional_review_bot_is_not_a_required_ci_gate(self):
        def advisory(policy,plane,gh,envelope):
            gh.check_data[0].append({'name':'Optional advisory review bot','status':'completed','conclusion':'failure'})
        result,*_=run_case(source='IN_REVIEW',target='MERGE_READY',mutate=advisory)
        self.assertEqual(result['result'],'VERIFIED')

    def test_all_github_review_states_are_advisory(self):
        for state in ['CHANGES_REQUESTED','DISMISSED','COMMENTED','PENDING','APPROVED']:
            def advisory(policy,plane,gh,envelope):
                gh.review_data=[{'user':{'login':'selorito'},'state':state,'commit_id':HEAD}]
            with self.subTest(state=state):
                result,*_=run_case(source='IN_REVIEW',target='MERGE_READY',mutate=advisory)
                self.assertEqual(result['result'],'VERIFIED')

    def test_normal_risk_cannot_merge_when_behind_current_main(self):
        def behind(policy,plane,gh,envelope): gh.review_data=[];gh.behind_main=True
        with self.assertRaises(t.Denied) as denied:
            run_case(source='IN_REVIEW',target='MERGE_READY',mutate=behind)
        self.assertEqual(denied.exception.code,'PR_BEHIND_CURRENT_MAIN')

    def test_review_api_failure_does_not_block_technical_readiness(self):
        def unavailable(policy,plane,gh,envelope):
            def fail(*args): raise TimeoutError('Review API unavailable')
            gh.reviews=fail
        result,*_=run_case(source='IN_REVIEW',target='MERGE_READY',mutate=unavailable)
        self.assertEqual(result['result'],'VERIFIED')

    def test_advisory_changes_requested_cannot_override_a_real_ci_failure(self):
        def bad(policy,plane,gh,envelope):
            gh.review_data=[{'state':'CHANGES_REQUESTED','commit_id':'d'*40}]
            gh.check_data[0][0]['conclusion']='failure'
        with self.assertRaises(t.Denied) as denied:
            run_case(source='IN_REVIEW',target='MERGE_READY',mutate=bad)
        self.assertEqual(denied.exception.code,'CI_NOT_GREEN')

    def test_high_risk_needs_zero_humans_but_real_ci_tests_validation(self):
        def no_review(policy,plane,gh,envelope):
            gh.pr_data['body']=gh.pr_data['body'].replace('CR-2 (normal-risk)','CR-3 (high-risk)')
            gh.review_data=[];gh.pr_data['requested_reviewers']=[]
        result,*_=run_case(source='IN_REVIEW',target='MERGE_READY',mutate=no_review)
        self.assertEqual(result['result'],'VERIFIED')
        def failed_step(policy,plane,gh,envelope):
            no_review(policy,plane,gh,envelope);gh.failed_technical_step=True
        with self.assertRaises(t.Denied): run_case(source='IN_REVIEW',target='MERGE_READY',mutate=failed_step)

    def test_all_security_platform_protected_surfaces_use_technical_gates_only(self):
        for surface in ['auth/authorization','protected-action authority','destructive migration','secrets/security infra','authority boundary','safety/protected execution']:
            def no_review(policy,plane,gh,envelope):
                gh.pr_data['body']=gh.pr_data['body'].replace('CR-2 (normal-risk)','CR-3 (high-risk)')
                gh.pr_data['body']+='\nActual impact: '+surface
                gh.review_data=[]
            with self.subTest(surface=surface):
                result,*_=run_case(source='IN_REVIEW',target='MERGE_READY',mutate=no_review)
                self.assertEqual(result['result'],'VERIFIED')

    def test_security_impact_is_not_an_approval_special_case(self):
        def security(policy,plane,gh,envelope):
            gh.pr_data['body']=gh.pr_data['body'].replace('No authentication/authorization, protected execution, secrets, security infrastructure, major authority or data/model changes','Authentication/authorization technical changes with actual negative evidence')
            gh.review_data=[]
        result,*_=run_case(source='IN_REVIEW',target='MERGE_READY',mutate=security)
        self.assertEqual(result['result'],'VERIFIED')

    def test_compiled_policy_cannot_reintroduce_human_review_gates(self):
        for key,value in [('required_human_approvals',2),('reviewer_presence_required',True),('review_state_is_workflow_input',True),('product_hitl_unchanged',False)]:
            def tampered(policy,plane,gh,envelope): policy['review_policy'][key]=value
            with self.subTest(key=key),self.assertRaises(t.Denied):
                run_case(source='IN_REVIEW',target='MERGE_READY',mutate=tampered)

    def test_real_ci_scope_and_merge_predicates(self):
        for what in ['ci','draft','technical_step','secret_path','mergeability']:
            def bad(policy,plane,gh,envelope):
                if what=='ci': gh.check_data[0][0]['conclusion']='failure'
                elif what=='draft': gh.pr_data['draft']=True
                elif what=='technical_step': gh.failed_technical_step=True
                elif what=='secret_path': gh.file_rows=[{'filename':'project_control/local/plane.env'}]
                else: gh.pr_data['mergeable']=None
            with self.subTest(what=what),self.assertRaises(t.Denied):
                run_case(source='IN_REVIEW',target='MERGE_READY',mutate=bad)
        def not_merged(policy,plane,gh,envelope): gh.pr_data['merged']=False
        with self.assertRaises(t.Denied): run_case(source='MERGE_READY',target='MERGED',mutate=not_merged)

    def test_done_no_peer_or_approval_but_all_actual_dod_and_postmerge_evidence(self):
        for profile in t.q.PEOPLE:
            def no_peer(policy,plane,gh,envelope):
                gh.review_data=[];gh.pr_data['requested_reviewers']=[]
                envelope['evidence_refs'].remove('comment:3')
            with self.subTest(profile=profile):
                result,*_=run_case(profile,source='VALIDATING',target='DONE',mutate=no_peer)
                self.assertEqual(result['result'],'VERIFIED')

    def test_pairing_and_self_review_metadata_do_not_gate_workflow(self):
        def advisory(policy,plane,gh,envelope):
            gh.pr_data['body']=gh.pr_data['body'].replace('Pairing participants: none','Pairing participants: @selorito')
            gh.review_data=[{'user':{'login':'Asperant'},'state':'APPROVED','commit_id':HEAD}]
        result,*_=run_case(source='IN_REVIEW',target='MERGE_READY',mutate=advisory)
        self.assertEqual(result['result'],'VERIFIED')

    def test_required_postmerge_run_is_bound_to_merge_revision(self):
        for target,source in [('VALIDATING','MERGED'),('DONE','VALIDATING')]:
            def wrong(policy,plane,gh,envelope): gh.run_data['head_sha']=HEAD
            with self.assertRaises(t.Denied): run_case(source=source,target=target,mutate=wrong)

    def test_done_uses_exact_main_ci_gate_without_projectctl(self):
        def main_only(policy,plane,gh,envelope):
            gh.check_data=([{'name':'ci-gate','status':'completed','conclusion':'success',
                             'details_url':'https://github.com/Asperant/critical-aerospace-manufacturing/actions/runs/12/job/22'}],[])
        result,*_=run_case(source='VALIDATING',target='DONE',mutate=main_only)
        self.assertEqual(result['result'],'VERIFIED')

    def test_done_rejects_missing_failed_or_wrong_revision_main_ci(self):
        cases={
            'missing': lambda gh: setattr(gh,'check_data',([],[])),
            'failed': lambda gh: setattr(gh,'check_data',([{'name':'ci-gate','status':'completed','conclusion':'failure',
                'details_url':'https://github.com/Asperant/critical-aerospace-manufacturing/actions/runs/12/job/22'}],[])),
            'wrong_revision': lambda gh: gh.run_data.update(head_sha=HEAD),
        }
        for name,mutate in cases.items():
            with self.subTest(name=name):
                def deny(policy,plane,gh,envelope,mutate=mutate):
                    mutate(gh)
                with self.assertRaises(t.Denied):
                    run_case(source='VALIDATING',target='DONE',mutate=deny)

    def test_merge_ready_fast_gate_still_requires_projectctl(self):
        def no_projectctl(policy,plane,gh,envelope):
            gh.check_data=([{'name':'ci-gate','status':'completed','conclusion':'success',
                             'details_url':'https://github.com/Asperant/critical-aerospace-manufacturing/actions/runs/12/job/22'}],[])
        with self.assertRaises(t.Denied):
            run_case(source='IN_REVIEW',target='MERGE_READY',mutate=no_projectctl)

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

    def test_current_github_head_is_fresh_before_plane_mutation(self):
        wp,policy,plane,gh,envelope=fixture(source='IN_REVIEW',target='MERGE_READY')
        def changed(number):
            pr=deepcopy(gh.pr_data);pr['head']['sha']='f'*40;return pr
        gh.fresh_pr=changed
        with self.assertRaises(t.Denied) as denied:
            t.execute('asrin',wp,'MERGE_READY',envelope,policy,plane,gh,lambda *a:None,SECRET)
        self.assertEqual(denied.exception.code,'CONCURRENT_GITHUB_CHANGE')
        self.assertEqual(plane.patches,[])

    def test_technical_ci_requires_actual_run_job_and_all_required_steps(self):
        from unittest.mock import MagicMock
        wp,policy,plane,gh,envelope=fixture()
        for failure in [None,'run_sha','job_sha','skipped_step','missing_step','failed_run']:
            client=t.GitHub.__new__(t.GitHub)
            check={'name':'projectctl','details_url':'https://github.com/Asperant/critical-aerospace-manufacturing/actions/runs/11/job/22'}
            client.checks=MagicMock(return_value=([check],[]))
            run={'head_sha':HEAD,'status':'completed','conclusion':'success'}
            steps=[{'name':name,'status':'completed','conclusion':'success'} for name in policy['required_technical_steps']]
            job={'name':'projectctl','head_sha':HEAD,'status':'completed','conclusion':'success','steps':steps}
            if failure=='run_sha': run['head_sha']='d'*40
            if failure=='job_sha': job['head_sha']='d'*40
            if failure=='skipped_step': steps[0]['conclusion']='skipped'
            if failure=='missing_step': steps.pop()
            if failure=='failed_run': run['conclusion']='failure'
            client.run=MagicMock(return_value=run)
            client._get=MagicMock(return_value={'total_count':1,'jobs':[job]})
            with self.subTest(failure=failure):
                if failure:
                    with self.assertRaises(t.Denied): client.technical_ci(HEAD,policy)
                else: client.technical_ci(HEAD,policy)

    def test_host_security_test_steps_required_when_host_files_change(self):
        def host(policy,plane,gh,envelope):
            gh.file_rows=[{'filename':'tools/host/plane-transition/transition.py'}]
            def inspect(sha,policy,extra=()):
                if extra: raise t.Denied('REQUIRED_TECHNICAL_STEP_NOT_PASSED')
            gh.technical_ci=inspect
        with self.assertRaises(t.Denied): run_case(source='IN_REVIEW',target='MERGE_READY',mutate=host)

    def test_actual_file_scope_must_be_complete(self):
        from unittest.mock import MagicMock
        wp,policy,plane,gh,envelope=fixture()
        client=t.GitHub.__new__(t.GitHub)
        client._get=MagicMock(return_value=[{'filename':'one.py'}])
        with self.assertRaises(t.Denied): client.files(gh.pr_data)

    def test_rework_is_bound_to_actual_revision_not_advisory_review(self):
        wp,policy,plane,gh,envelope=fixture(source='MERGE_READY',target='IN_REVIEW')
        for projection in [None,{'result':'VERIFIED','operation':'MERGE_READY','observed_pr_head':HEAD}]:
            with self.assertRaises(t.Denied):
                t.execute('asrin',wp,'IN_REVIEW',envelope,policy,plane,gh,lambda *a:None,SECRET,projection=projection)
        result=t.execute('asrin',wp,'IN_REVIEW',envelope,policy,plane,gh,lambda *a:None,SECRET,
                         projection={'result':'VERIFIED','operation':'MERGE_READY','observed_pr_head':'c'*40})
        self.assertEqual(result['result'],'VERIFIED')

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

    def test_unscheduled_missing_ci_and_missing_actual_done_evidence_fail_closed(self):
        def unscheduled(policy,plane,gh,envelope): policy['contexts'][plane.item['external_id']]['cycle_ids']=[]
        with self.assertRaises(t.Denied): run_case(source='BACKLOG',target='READY',mutate=unscheduled)
        def missing_ci(policy,plane,gh,envelope): gh.check_data=([],[])
        with self.assertRaises(t.Denied): run_case(source='IN_PROGRESS',target='IN_REVIEW',mutate=missing_ci)
        def no_assessment(policy,plane,gh,envelope): envelope['evidence_refs']=['pr:1','run:4']
        with self.assertRaises(t.Denied): run_case(source='VALIDATING',target='DONE',mutate=no_assessment)

    def test_milestone_dependency_is_not_blindly_a_wp_closure_blocker(self):
        def milestone(policy,plane,gh,envelope):
            policy['contexts'][plane.item['external_id']]['dependency_edges']=[{
                'id':'DEP-001','predecessor':{'node':'MS-ONE'},
                'semantics':{'strength':'HARD','blocking_stage':'MILESTONE_EXIT','required_readiness':None}}]
        with self.assertRaises(t.Denied): run_case(source='VALIDATING',target='DONE',mutate=milestone)
        def assessed(policy,plane,gh,envelope):
            milestone(policy,plane,gh,envelope)
            record=gh.comments[2]
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

    def test_real_actions_run_ids_exceed_ten_digits_and_stay_bounded(self):
        number=38655953289
        client=object.__new__(t.GitHub)
        with patch.object(client,'_get',return_value={'id':number}) as request:
            self.assertEqual(client.run(number),{'id':number})
        self.assertEqual(request.call_args.args[0],f'{t.REPO}/actions/runs/{number}')
        parsed=t.parse_input(json.dumps({'reason':'Real post-merge run','evidence_refs':[f'run:{number}']}).encode())
        self.assertEqual(parsed['evidence_refs'],[f'run:{number}'])
        for invalid in [True,0,-1,10**18,'1/../../secrets']:
            with self.assertRaises(t.Denied): client.run(invalid)

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

    def test_github_probe_deadline_clips_each_subprocess_timeout(self):
        client = object.__new__(t.GitHub)
        client.cache = {}
        client.env = {}
        client.uid = 1000
        client.gid = 1000
        client.request_timeout = 1
        client.deadline = 100.0
        response = subprocess.CompletedProcess([], 0, b'{}', b'')
        with patch.object(t.time, 'monotonic', return_value=99.75), \
             patch.object(t.subprocess, 'run', return_value=response) as called:
            self.assertEqual(client._get('repos/example'), {})
        self.assertEqual(called.call_args.kwargs['timeout'], 0.25)


if __name__=='__main__': unittest.main()
