"""WP-GOV-001: source-linked requirement catalog; no execution-state authority."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import subprocess
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .parsers.requirements import MASTER, RTM, parse_requirements

CATALOG = "requirements/catalog.json"
SCHEMA = "requirements/catalog.schema.json"
COUNTS = "requirements/coverage_counts.json"
COUNT_START = "<!-- WP-GOV-001:GENERATED-COUNTS:START -->"
COUNT_END = "<!-- WP-GOV-001:GENERATED-COUNTS:END -->"
TERMINAL = {"RETIRED", "SUPERSEDED"}
Identity = Annotated[str, Field(pattern=r"^(?:FR|NFR)-[A-Z]+-[0-9]{3}$")]
OwnerName = Literal["Asrın Dündar", "Selman Özdemir", "Batuhan Kaya", "Yavuz Gümüş"]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class CatalogSource(Record):
    path: Literal[MASTER]
    item: Literal[81, 82]
    heading: str = Field(min_length=1)
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class Entry(Record):
    id: Identity
    primary_owner: OwnerName
    # Null is a canonical source gap, never a lifecycle default.
    revision: str | None
    status: Literal["DEFINED", "MEASURABLE", "IMPLEMENTED", "TESTED", "MEASURED", "VERIFIED", "RETIRED", "SUPERSEDED"] | None
    source: CatalogSource


class FunctionalEntry(Entry):
    id: Annotated[str, Field(pattern=r"^FR-[A-Z]+-[0-9]{3}$")]
    kind: Literal["FR"]
    scope_class: Literal["F0", "F1", "R1"]
    quality_class: None


class NonfunctionalEntry(Entry):
    id: Annotated[str, Field(pattern=r"^NFR-[A-Z]+-[0-9]{3}$")]
    kind: Literal["NFR"]
    scope_class: None
    quality_class: Literal["H0", "A1", "S2", "C3"]


class RetiredIdentity(Record):
    id: Identity
    status: Literal["RETIRED", "SUPERSEDED"]
    decision_ref: str = Field(pattern=r"^09_change/CHG-[0-9]{3}\.yaml$")


class CatalogFile(Record):
    schema_version: Literal["requirement-catalog-v1"]
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    requirements: list[Annotated[FunctionalEntry | NonfunctionalEntry, Field(discriminator="kind")]]
    retired_ids: list[RetiredIdentity]

    @model_validator(mode="after")
    def identities(self):
        for name, rows in [("requirements", self.requirements), ("retired_ids", self.retired_ids)]:
            ids = [r.id for r in rows]
            if len(ids) != len(set(ids)):
                raise ValueError(f"Duplicate ID in {name}")
            if ids != sorted(ids):
                raise ValueError(f"{name} must be sorted by stable ID")
        retired = {r.id: r.status for r in self.retired_ids}
        for entry in self.requirements:
            expected_item = 81 if entry.kind == "FR" else 82
            if not entry.id.startswith(entry.kind + "-") or entry.source.item != expected_item:
                raise ValueError(f"ID/kind/source item mismatch: {entry.id}")
            if entry.source.heading != f"Item {expected_item} / {entry.id}" or entry.source.line_end < entry.source.line_start:
                raise ValueError(f"Invalid source anchor: {entry.id}")
            if entry.id in retired and entry.status != retired[entry.id]:
                raise ValueError(f"Retired-ID reuse: {entry.id}")
            if entry.status in TERMINAL and retired.get(entry.id) != entry.status:
                raise ValueError(f"Terminal identity lacks retirement record: {entry.id}")
        return self


def encode(payload):
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def decode(text):
    def unique_keys(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"Duplicate JSON key: {key}")
            value[key] = item
        return value
    return json.loads(text, object_pairs_hook=unique_keys)


def read_catalog(path):
    return CatalogFile.model_validate(decode(path.read_text(encoding="utf-8")))


def catalog_schema():
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", **CatalogFile.model_json_schema()}


def from_sources(root: Path, retired_ids=()):
    master = (root / MASTER).read_text(encoding="utf-8")
    parsed = parse_requirements(master, (root / RTM).read_text(encoding="utf-8"))
    if Counter(r.kind.value for r in parsed.requirements) != {"FR": 186, "NFR": 120}:
        raise ValueError("Canonical baseline must contain 186 FR and 120 NFR definitions")
    entries = []
    for requirement in parsed.requirements:
        ref = requirement.provenance
        entries.append(dict(
            id=requirement.id, kind=requirement.kind.value,
            scope_class=requirement.scope_class.value if requirement.scope_class else None,
            quality_class=requirement.quality_class.value if requirement.quality_class else None,
            primary_owner=requirement.primary_owner.canonical_name,
            revision=requirement.revision, status=requirement.catalog_status,
            source=dict(path=MASTER, item=81 if requirement.kind == "FR" else 82,
                        heading=ref.heading, line_start=ref.line_start, line_end=ref.line_end,
                        sha256=sha256(ref.raw_context.encode()).hexdigest()),
        ))
    return CatalogFile.model_validate(dict(schema_version="requirement-catalog-v1",
        source_sha256=sha256((root / MASTER).read_bytes()).hexdigest(), requirements=entries,
        retired_ids=[r.model_dump() for r in retired_ids]))


def coverage_counts(catalog):
    """Inventory only: these counts imply no implementation/evidence coverage."""
    rows = catalog.requirements
    def counts(values):
        return dict(sorted(Counter(values).items()))
    return dict(schema_version="requirement-counts-v1", source_sha256=catalog.source_sha256,
        total=len(rows), unique_ids=len({r.id for r in rows}),
        by_kind=counts(r.kind for r in rows),
        fr_scope=counts(r.scope_class for r in rows if r.kind == "FR"),
        nfr_quality=counts(r.quality_class for r in rows if r.kind == "NFR"),
        by_owner=counts(r.primary_owner for r in rows),
        by_domain=counts(r.id.rsplit("-", 1)[0] for r in rows),
        missing_revision=sum(r.revision is None for r in rows),
        missing_status=sum(r.status is None for r in rows),
        retired_id_count=len(catalog.retired_ids))


def rtm_counts(catalog):
    counts = coverage_counts(catalog)
    rows = [("Total / unique IDs", f"{counts['total']} / {counts['unique_ids']}"),
            ("FR / NFR", f"{counts['by_kind'].get('FR', 0)} / {counts['by_kind'].get('NFR', 0)}"),
            ("FR F0 / F1 / R1", " / ".join(str(counts['fr_scope'].get(c, 0)) for c in ["F0", "F1", "R1"])),
            ("NFR H0 / A1 / S2 / C3", " / ".join(str(counts['nfr_quality'].get(c, 0)) for c in ["H0", "A1", "S2", "C3"])),
            ("Missing canonical Revision / Status", f"{counts['missing_revision']} / {counts['missing_status']}"),
            ("Recorded retired/superseded IDs", str(counts['retired_id_count']))]
    return "\n".join([COUNT_START, "| Inventory (not verification coverage) | Count |", "|---|---|",
                      *[f"| {label} | {value} |" for label, value in rows], COUNT_END])


def check_history(current, previous):
    """Every PR retains tombstones and records removed historical identities."""
    issues = []
    now = {r.id: r for r in current.requirements}
    retired = {r.id: r for r in current.retired_ids}
    for old in previous.retired_ids:
        if retired.get(old.id) != old:
            issues.append(f"RETIREMENT_HISTORY: missing/changed tombstone {old.id}")
        if old.id in now and now[old.id].status != old.status:
            issues.append(f"RETIRED_ID_REUSE: {old.id}")
    for old in previous.requirements:
        if old.id not in now and old.id not in retired:
            issues.append(f"ID_REMOVED_WITHOUT_RETIREMENT: {old.id}")
        if old.status in TERMINAL and old.id in now and now[old.id].status != old.status:
            issues.append(f"RETIRED_ID_REUSE: {old.id}")
    return sorted(set(issues))


def git_baseline(root, revision):
    resolved = subprocess.run(["git", "rev-parse", "--verify", "--end-of-options", f"{revision}^{{commit}}"],
                              cwd=root, text=True, capture_output=True)
    if resolved.returncode:
        raise ValueError("History baseline must resolve to a Git commit")
    commit = resolved.stdout.strip()
    listing = subprocess.run(["git", "ls-tree", "--name-only", commit, "--", CATALOG],
                             cwd=root, text=True, capture_output=True, check=True)
    if not listing.stdout.strip():
        return None  # First introduction; no pre-catalog retirement history is asserted.
    content = subprocess.run(["git", "show", f"{commit}:{CATALOG}"], cwd=root,
                             text=True, capture_output=True, check=True).stdout
    return CatalogFile.model_validate(decode(content))


def lint_catalog(root, baseline=None):
    catalog = read_catalog(root / CATALOG)
    expected = from_sources(root, catalog.retired_ids)
    issues = []
    if catalog != expected:
        issues.append("SOURCE_MISMATCH: catalog differs from canonical Items 81/82; regenerate and review")
    for path, value in [(CATALOG, catalog.model_dump()), (SCHEMA, catalog_schema()), (COUNTS, coverage_counts(catalog))]:
        if (root / path).read_text(encoding="utf-8") != encode(value):
            issues.append(f"GENERATED_DRIFT: {path}")
    rtm = (root / RTM).read_text(encoding="utf-8")
    if rtm.count(COUNT_START) != 1 or rtm.count(COUNT_END) != 1 or rtm_counts(catalog) not in rtm:
        issues.append("RTM_COUNTS_DRIFT: regenerate the marked inventory block in 03")
    for record in catalog.retired_ids:
        if not (root / record.decision_ref).is_file():
            issues.append(f"RETIREMENT_DECISION_MISSING: {record.id}")
    history = "NOT_CHECKED (local inventory only)"
    if baseline is not None:
        previous = git_baseline(root, baseline)
        history = "CHECKED" if previous is not None else "INITIAL_CATALOG (no prior catalog at baseline)"
        if previous is not None:
            issues.extend(check_history(catalog, previous))
    return dict(result="FAIL" if issues else "PASS", history=history,
                counts=coverage_counts(catalog), issues=sorted(issues),
                source_gaps=["Unspecified canonical Revision/Status remain null (GAP-RTM-004/005)",
                             "NFR measurement metadata remains owner-confirmation work (GAP-RTM-004)"],
                readiness="NOT_CERTIFIED", evidence="NOT_CERTIFIED")
