from pathlib import Path
from projectctl.project import load_project
import re,json
p=load_project(Path('.'));g=p.catalog.dependencies
text=Path('docs/05_Dependency_Graph.md').read_text();region=text.split('## 13. Explicit Non-Dependencies (Forbidden Edges)',1)[1].split('## 14.',1)[0]
checks=[]
for line in region.splitlines():
 if not line.startswith('| NDEP-'):continue
 row=[x.strip() for x in line.strip('|').split('|')];pair=re.search(r'(DN-[A-Z0-9-]+) ↛ (DN-[A-Z0-9-]+)',row[4])
 if pair:violations=[e.id for e in g.edges if e.blocking and (e.predecessor.node,e.successor.node)==(pair[1],pair[2])]
 elif row[0]=='NDEP-14':violations=[e.id for e in g.edges if e.blocking and e.predecessor.node=='DN-SIM-ORACLE' and e.successor.node!='CK-E2E01']
 else:
  term={'NDEP-09':'ColBERT','NDEP-10':'paid','NDEP-11':'Kubernetes'}[row[0]]
  violations=[n.id for n in g.nodes if term.lower() in (n.id+' '+n.name).lower()]
 assert not violations,(row[0],violations)
 checks.append({'id':row[0],'source_row':line,'violations':violations,'result':'PASS'})
assert len(checks)==14
rows=re.findall(r'^\| (NFR-[A-Z]+-\d{3}) \| ([A-Z]\d) \|',Path('docs/02_System_Architecture_Specification.md').read_text(),re.M)
assert len(rows)==len(set(x[0] for x in rows))==120
reqs={r.id:r for r in p.catalog.requirements.requirements}
assert all(reqs[x].quality_class.value==c for x,c in rows)
d=[x.model_dump(mode='json') for x in p.diagnostics() if x.code in {'READINESS_INCOMPATIBLE','PRECISION_MISSING','FIXTURE_SEMANTICS','NEED_BY_AMBIGUOUS'}]
Path('evidence/documentation-reconciliation/CTRL-DOC-005-planning-audit.json').write_text(json.dumps({'forbidden_hard_rules':checks,'oracle_checkpoint_exception':'DEP-187 gates CK-E2E01 isolation proof; not operational Oracle input','architecture_nfr_rows':120,'architecture_class_agreement':'PASS','diagnostics_preserved':d,'owner_decisions':['MC2_OWNER','E2E_COORDINATOR'],'hardware_pinning':'PENDING accepted CPU/Vision/developer values; Release/Environment/Hardware/Resource/Workload identity required','timing':'Keycloak/SeaweedFS endS4; Temporal formal endS5; Oracle isolation/credentials subset endS5 ahead of full M4 baseline','no_graph_changes':True},ensure_ascii=False,indent=2)+'\n')
print('14 forbidden rules PASS; actual120 unique architecture NFR rows/classes match')
