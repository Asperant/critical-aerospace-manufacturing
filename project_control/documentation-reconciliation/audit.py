"""Read-only, offline documentation audit. No project state or network access."""
from collections import Counter
from hashlib import sha256
from pathlib import Path
import json
import re
import subprocess
import sys

from projectctl.project import load_project

ROOT = Path(__file__).resolve().parents[2]
TERMS = re.compile(r'\bfab\b|fab[-_](?:core|simulator|bff)|fabctl|wafer|lithograph|\betch\w*|deposition|semiconductor|SECOM|WM-?811K|MixedWM38|Autonomous Critical-Component Manufacturing Facility Operating System', re.I)


def audit():
    project = load_project(ROOT)
    snap = project.snapshot()
    # Strip location-only provenance when comparing the canonical semantic model.
    def semantic(value):
        if isinstance(value, dict):
            return {k: semantic(v) for k, v in value.items() if k != 'provenance'}
        if isinstance(value, list):
            return [semantic(v) for v in value]
        return value
    model = {k: semantic(snap[k]) for k in ('capability_areas', 'work_packages', 'schedule', 'dependency_nodes', 'dependency_edges', 'requirements')}
    sources = {}
    headings = {}
    occurrences = []
    links = []
    files = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    # Include canonical additions before their first commit, exclude local credentials.
    files = sorted(set(files) | {str(p.relative_to(ROOT)) for p in (ROOT / 'docs').glob('*.md')})
    for name in files:
        path = ROOT / name
        if not path.is_file():
            continue
        try:
            data = path.read_text(encoding='utf-8')
        except (UnicodeError, OSError):
            continue
        if name.startswith('docs/'):
            sources[name] = sha256(path.read_bytes()).hexdigest()
            headings[name] = [{'line': n, 'heading': line} for n, line in enumerate(data.splitlines(), 1) if line.startswith('#')]
        heading = ''
        for number, line in enumerate(data.splitlines(), 1):
            if line.startswith('#'):
                heading = line
            for match in TERMS.finditer(line):
                if name.startswith('evidence/') or name.startswith('09_change/') or '10_Pre_' in name:
                    category = 'HISTORICAL_FINDING_OR_EVIDENCE_PRESERVE'
                elif re.search(r'WL-INV|FAB-\d|TEST-PLAT-FABCTL', line):
                    category = 'STABLE_LEGACY_ID_PRESERVE'
                elif re.search(r'SECOM|WM-?811K|MixedWM38', line, re.I):
                    category = 'EXTERNAL_DATASET_IDENTITY_RETAIN_ONLY_WITH_CROSS_DOMAIN_SCOPE'
                elif re.search(r'migrat|legacy|changelog|comparison|mapping|semiconductor', line, re.I):
                    category = 'MIGRATION_HISTORY_OR_COMPARISON_PRESERVE'
                else:
                    category = 'UNRESOLVED_CONTEXT_PRESERVE_FOR_REVIEW'
                occurrences.append(dict(file=name, line=number, column=match.start()+1, term=match.group(), heading=heading, text=line, classification=category, auto_replace=False))
            if name.startswith('docs/'):
                for target in re.findall(r'`([^`\n]+\.md)`', line):
                    if '/' not in target and not (ROOT / 'docs' / target).exists() and not (ROOT / target).exists():
                        links.append(dict(file=name, line=number, target=target, status='MISSING_OR_PLANNED_ARTIFACT_REQUIRES_CONTEXT'))
    master = (ROOT / 'docs/01_Master_Project_Specification.md').read_text().splitlines()
    reqs = project.catalog.requirements.requirements
    exact = {r.id: r.provenance.line_start for r in reqs}
    rtm = (ROOT / 'docs/03_Requirements_Traceability_Matrix.md').read_text()
    citations = []
    for trace in project.catalog.requirements.traces:
        anchor = trace.assertions.get('meta', {}).get('anchor', '')
        match = re.search(r'\bL(\d+)\b', anchor)
        citations.append(dict(id=trace.requirement_id, anchor=anchor, expected_line=exact[trace.requirement_id], valid=bool(match and int(match[1]) == exact[trace.requirement_id])))
    numeric_refs = []
    for name in sources:
        for n, line in enumerate((ROOT / name).read_text().splitlines(), 1):
            if re.search(r'\bL\d+', line):
                numeric_refs.append(dict(file=name, line=n, text=line, status='IDENTITY_REQUIRED' if name != 'docs/03_Requirements_Traceability_Matrix.md' else 'RTM_REVIEW'))
    summary = project.summary()
    summary['class_counts'] = dict(Counter((r.scope_class or r.quality_class).value for r in reqs))
    summary['diagnostic_counts'] = dict(Counter(d.code for d in project.diagnostics()))
    checks = {
        'requirement_count': 306, 'fr_count': 186, 'nfr_count': 120, 'wp_count': 179,
        'capability_count': 29, 'dependency_node_count': 100, 'dependency_edge_count': 217,
        'hard_edge_count': 208, 'soft_edge_count': 9, 'hard_cycle_count': 0,
        'scheduled_wp_count': 174, 'cycle_count': 13, 'milestone_count': 9,
    }
    for key, expected in checks.items():
        assert summary[key] == expected, (key, summary[key], expected)
    assert summary['class_counts'] == {'F0':17, 'F1':159, 'R1':10, 'H0':52, 'A1':41, 'S2':23, 'C3':4}
    assert summary['unscheduled_wp_ids'] == ['WP-R2-001','WP-R2-002','WP-R2-003','WP-S-001','WP-X-001']
    assert Counter(w.primary_owner.canonical_name for w in project.catalog.work_packages) == {'Asrın Dündar':73,'Selman Özdemir':17,'Batuhan Kaya':32,'Yavuz Gümüş':57}
    assert {c.id for c in project.catalog.schedule.cycles} == {f'S{i}' for i in range(1,14)}
    assert {m.id for m in project.catalog.schedule.milestones} == {f'M{i}' for i in range(9)}
    assert not [d for d in project.diagnostics() if d.severity.value == 'ERROR']
    # Every dataset/naming occurrence is classified; uncertain contexts are not rewritten.
    return dict(summary=summary, semantic_model_sha256=sha256(json.dumps(model, sort_keys=True, ensure_ascii=False).encode()).hexdigest(), canonical_sources=sources, headings=headings, occurrences=occurrences, exact_requirement_citations=citations, numeric_reference_review=numeric_refs, missing_or_planned_links=links, diagnostics=snap['diagnostics'])

if __name__ == '__main__':
    json.dump(audit(), sys.stdout, ensure_ascii=False, indent=2)
    print()
