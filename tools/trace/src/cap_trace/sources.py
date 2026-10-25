"""Identity registries the trace edges point into (TL-02), read from the canonical
documents of the repository.

| Namespace | Source |
|---|---|
| FR-*/NFR-* | `requirements/catalog.json` (WP-GOV-001), active and retired IDs |
| ITEM-nn | 01 item headings (`# NN — Title`) |
| <FAMILY>-INV-nn, risks <AREA>-Rnn, scenarios | identity tokens of 01 |
| ARCH-<PREFIX>-<COMPONENT> | 02 Architecture Component ID Registry and its append-only allocations |
| IC-<NS>-nnn | identity tokens of 01 and 02 (conceptual contract catalogs) |
| verification families / assets | 03 §9.X registry, 03 §19 concrete assets, `ci/test-strategy.json` TestIDs |
| ADR-NNNN | `docs/adr/NNNN-*.md` |

TL-10: identities are extracted as whole tokens with prefix boundaries, so
`REAL-INV-01` is not found inside `SIM-REAL-INV-01`, `RES-001` not inside
`NFR-RES-001`, and `ARCH-INV-04` is not `ARCH-INV-004` (03 GAP-RTM-016).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

MASTER = "docs/01_Master_Project_Specification.md"
ARCHITECTURE = "docs/02_System_Architecture_Specification.md"
RTM = "docs/03_Requirements_Traceability_Matrix.md"
CATALOG = "requirements/catalog.json"
STRATEGY = "ci/test-strategy.json"
ADR_DIR = "docs/adr"
CHANGE_DIR = "09_change"

# A whole identity token: not preceded by an identifier or hyphen character and
# not continued by one. Hyphenated suffixes stay part of the token.
TOKEN = re.compile(
    r"(?<![A-Za-z0-9_-])([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+)(?![A-Za-z0-9_-])"
)
ITEM_HEADING = re.compile(r"^# (\d{1,3}) — ", re.M)
HEADING = re.compile(r"^(#{1,6}) ", re.M)
TABLE_ID = re.compile(r"^\| *([A-Z][A-Z0-9-]+)\b", re.M)
ARCH_SECTIONS = re.compile(r"Component ID Registry|component allocations", re.I)
INACTIVE = frozenset({"RETIRED", "SUPERSEDED"})
RUN_ID = re.compile(r"^RUN-([A-Z]+)-(\d{3})-[A-Z0-9-]+$")
EVIDENCE_ID = re.compile(r"^EVID-[A-Z0-9-]+$")
TEXT_SUFFIXES = frozenset({".md", ".json", ".txt", ".yaml", ".yml"})
VIEW_D_ROW = re.compile(r"^\| ((?:FR|NFR)-[A-Z]+-\d{3}) \| \w+ \| ([^|]+) \|", re.M)
KIND_HEADING = re.compile(r"^#### ([A-Z]+) \(\d+\)", re.M)


def tokens(text: str) -> set[str]:
    """TL-10: identity tokens with prefix boundaries."""
    return set(TOKEN.findall(text))


def sections(text: str, title: re.Pattern[str]) -> list[str]:
    """Bodies of the headings whose title matches, up to the next heading of the
    same or a higher level."""
    found: list[str] = []
    marks = list(HEADING.finditer(text))
    for index, mark in enumerate(marks):
        line_end = text.find("\n", mark.end())
        if not title.search(text[mark.end() : line_end]):
            continue
        level = len(mark.group(1))
        end = len(text)
        for later in marks[index + 1 :]:
            if len(later.group(1)) <= level:
                end = later.start()
                break
        found.append(text[mark.start() : end])
    return found


def table_ids(text: str, prefix: str = "") -> set[str]:
    return {i for i in TABLE_ID.findall(text) if i.startswith(prefix)}


@dataclass
class Index:
    requirements: set[str] = field(default_factory=set[str])
    inactive: set[str] = field(default_factory=set[str])
    items: set[int] = field(default_factory=set[int])
    master: set[str] = field(default_factory=set[str])
    architecture: set[str] = field(default_factory=set[str])
    contracts: set[str] = field(default_factory=set[str])
    verification: set[str] = field(default_factory=set[str])
    decisions: set[str] = field(default_factory=set[str])
    asset_kinds: dict[str, str] = field(default_factory=dict[str, str])
    asset_envs: dict[str, str] = field(default_factory=dict[str, str])
    verify_codes: dict[str, set[str]] = field(default_factory=dict[str, set[str]])
    changes: set[str] = field(default_factory=set[str])
    root: Path | None = None

    def path_exists(self, path: str) -> bool:
        if self.root is None or path.startswith("/") or ".." in path.split("/"):
            return False
        return (self.root / path).exists()

    def run_exists(self, run: str) -> bool:
        """A run record of the producing work package: a path under evidence/
        (`evidence/...` targets), or `RUN-<AREA>-<NNN>-...` named by a file or
        directory in, or written as a whole token inside, `evidence/WP-<AREA>-<NNN>/`."""
        if run.startswith("evidence/"):
            return self.path_exists(run)
        match = RUN_ID.match(run)
        if match is None or self.root is None:
            return False
        folder = self.root / "evidence" / f"WP-{match.group(1)}-{match.group(2)}"
        if not folder.is_dir():
            return False
        for path in sorted(folder.rglob("*")):
            if path.name == run or path.name.startswith(run + "."):
                return True
            if (
                path.is_file()
                and path.suffix in TEXT_SUFFIXES
                and run in tokens(path.read_text("utf-8", errors="replace"))
            ):
                return True
        return False

    def bundle_exists(self, evidence: str) -> bool:
        """A sealed EvidenceBundle directory named by its EvidenceID."""
        if self.root is None or not EVIDENCE_ID.match(evidence):
            return False
        return any(p.is_dir() for p in (self.root / "evidence").rglob(evidence))


def catalog_ids(data: dict[str, Any]) -> tuple[set[str], set[str]]:
    active: set[str] = set()
    inactive: set[str] = set(cast(list[str], data.get("retired_ids", [])))
    for entry in cast(list[dict[str, Any]], data.get("requirements", [])):
        status = entry.get("status")
        (inactive if status in INACTIVE else active).add(str(entry["id"]))
    return active, inactive


def verification_ids(rtm: str, strategy: dict[str, Any]) -> set[str]:
    found: set[str] = set()
    for body in sections(rtm, re.compile(r"Verification Asset Registry")):
        found |= table_ids(body)
    start = rtm.find("## 19. ")
    end = rtm.find("\n## 20. ", start)
    for table in rtm[start:end].split("| Concrete asset |")[1:]:
        rows = table.split("\n\n", 1)[0]
        found |= table_ids(rows)
    for suite in cast(list[dict[str, Any]], strategy.get("suites", [])):
        found |= set(cast(list[str], suite.get("test_ids", [])))
    legacy = cast(dict[str, Any], strategy.get("test_id", {})).get("legacy", [])
    found |= set(cast(list[str], legacy))
    found.discard("Concrete")
    return found


def asset_table(rtm: str) -> tuple[dict[str, str], dict[str, str]]:
    """Kind (the #### heading) and minimum environment of each 03 §9.X family."""
    kinds: dict[str, str] = {}
    envs: dict[str, str] = {}
    for body in sections(rtm, re.compile(r"Verification Asset Registry")):
        current = ""
        for line in body.splitlines():
            heading = KIND_HEADING.match(line)
            if heading:
                current = heading.group(1)
                continue
            cells = [c.strip() for c in line.split("|")]
            if current and len(cells) > 6 and TABLE_ID.match(line):
                kinds[cells[1]] = current
                envs[cells[1]] = cells[5]
    return kinds, envs


def verify_codes(rtm: str) -> dict[str, set[str]]:
    """Declared verification codes per requirement from 03 View D (§9)."""
    start, end = rtm.find("## 9. View D"), rtm.find("### 9.X")
    codes: dict[str, set[str]] = {}
    for requirement, cell in VIEW_D_ROW.findall(rtm[start:end] if start >= 0 else ""):
        letters = cell.replace("(derived)", "").replace(" ", "").split("/")
        codes[requirement] = {c for c in letters if c}
    return codes


def load(root: Path) -> Index:
    def read(name: str) -> str:
        return (root / name).read_text("utf-8")

    master, architecture, rtm = read(MASTER), read(ARCHITECTURE), read(RTM)
    active, inactive = catalog_ids(cast(dict[str, Any], json.loads(read(CATALOG))))
    arch: set[str] = set()
    for body in sections(architecture, ARCH_SECTIONS):
        arch |= table_ids(body, "ARCH-")
    master_tokens = tokens(master)
    kinds, envs = asset_table(rtm)
    return Index(
        requirements=active,
        inactive=inactive,
        items={int(n) for n in ITEM_HEADING.findall(master)},
        master=master_tokens,
        architecture={a for a in arch if not a.startswith("ARCH-INV-")},
        contracts={
            t for t in master_tokens | tokens(architecture) if t.startswith("IC-")
        },
        verification=verification_ids(
            rtm, cast(dict[str, Any], json.loads(read(STRATEGY)))
        ),
        decisions={
            "ADR-" + p.name[:4]
            for p in (root / ADR_DIR).glob("[0-9][0-9][0-9][0-9]-*.md")
        },
        asset_kinds=kinds,
        asset_envs=envs,
        verify_codes=verify_codes(rtm),
        changes={p.stem for p in (root / CHANGE_DIR).glob("CHG-[0-9][0-9][0-9].yaml")},
        root=root,
    )
