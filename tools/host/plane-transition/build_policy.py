"""Generate a static canonical context projection, never execution state. Run unprivileged."""
from hashlib import sha256
import json
from pathlib import Path
import re
from projectctl.project import load_project
from projectctl.queries import context
from projectctl.models import resolve_owner

ROOT=Path('/srv/ailab/project')
p=load_project(ROOT)
assert p.summary()['validation']=='PASS', 'Canonical validation failed'
text=(ROOT/'docs/08_Definition_of_Ready_and_Done.md').read_text()
criteria={}
for line in text.splitlines():
    if re.match(r'\| (?:DOR|DOD)-[A-Z]+-[0-9]{2} \|',line):
        cells=[c.strip() for c in line.strip('|').split('|')]
        criteria.setdefault(cells[0],cells[1:])
classes={r.id:r.scope_class for r in p.catalog.requirements.requirements}
contexts={}
for w in p.catalog.work_packages:
    c=context(p,w.id)
    c.pop('diagnostics',None)
    c['scope_criteria']=sorted({'docs/08#9:'+str(classes[r]) for r in w.requirement_refs})
    contexts[w.id]=c
nodes={n.id:n for n in p.catalog.dependencies.nodes}
people={'Asrın Dündar':'asrin','Selman Özdemir':'selman','Batuhan Kaya':'batuhan','Yavuz Gümüş':'yavuz'}
node_owners={n.id:people.get(resolve_owner(n.raw_owner).canonical_name) for n in nodes.values()}
manifest=dict(p.source_manifest)
for name in ['AGENTS.md','docs/02_System_Architecture_Specification.md','docs/08_Definition_of_Ready_and_Done.md',
             'docs/09_Change_Control_Process.md','.github/workflows/projectctl.yml']:
    manifest[name]=sha256((ROOT/name).read_bytes()).hexdigest()
policy={'schema_version':'cap-transition-policy-v1','evaluation_revision':'native-execution-facts-v2','source_manifest':manifest,'contexts':contexts,
        'criteria_definitions':criteria, 'node_owners':node_owners,
        'node_levels':{n.id:[str(v) for v in n.readiness_levels] for n in nodes.values()},
        'required_ci':['projectctl'], 'bounded_historical_overrides':{'product_wp_authorizations':[],
        'reason':'Owner PR#4/#5 control-only overrides do not authorize product WPs or new heads.'}}
for key,prefix,count in [('dor_task','DOR-TASK-',12),('dor_pr','DOR-PR-',8),('dod_pr','DOD-PR-',12),
                         ('dod_wp','DOD-WP-',12),('dod_research','DOD-RES-',11)]:
    ids=sorted(k for k in criteria if k.startswith(prefix))
    assert len(ids)==count, f'Unexpected canonical criterion set: {prefix}'
    policy[key]=ids
policy['implementation_sha256']={
    'transition':sha256((ROOT/'tools/host/plane-transition/transition.py').read_bytes()).hexdigest(),
    'queue':sha256((ROOT/'tools/host/plane-queue/queue.py').read_bytes()).hexdigest()}
policy['policy_digest']=sha256(json.dumps(policy,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
output=Path('/srv/ailab/remote-ssh/staging/plane-transition-policy.json')
output.write_text(json.dumps(policy,ensure_ascii=False,sort_keys=True))
print('Canonical transition policy generated (no execution data, no secrets).')
