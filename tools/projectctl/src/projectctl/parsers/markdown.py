"""Small scanner for the canonical heading, fenced-block and pipe-table grammar."""
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Heading:
    level: int
    title: str
    line: int
    end: int


def headings(text: str) -> list[Heading]:
    lines = text.splitlines()
    found: list[tuple[int, str, int]] = []
    fence: tuple[str, int] | None = None
    for number, line in enumerate(lines, 1):
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})(.*)$", line)
        if marker:
            run, suffix = marker.groups()
            if fence is None:
                fence = (run[0], len(run))
            elif run[0] == fence[0] and len(run) >= fence[1] and not suffix.strip():
                fence = None
            continue
        if fence:
            continue
        match = re.match(r"^(#{1,6}) (.+)$", line)
        if match:
            found.append((len(match[1]), match[2], number))
    return [Heading(level, title, line, next(
        (n - 1 for other, _, n in found[i + 1:] if other <= level), len(lines)
    )) for i, (level, title, line) in enumerate(found)]


def table_cells(line: str) -> list[str] | None:
    if not line.startswith("|") or not line.rstrip().endswith("|"):
        return None
    cells: list[str] = []
    cell = ""
    code_run = 0
    i = 1
    body = line.rstrip()[:-1]
    while i < len(body):
        char = body[i]
        if char == "\\" and i + 1 < len(body) and body[i + 1] == "|":
            cell += "|"
            i += 2
            continue
        if char == "`":
            end = i
            while end < len(body) and body[end] == "`":
                end += 1
            run = end - i
            code_run = run if code_run == 0 else (0 if code_run == run else code_run)
            cell += body[i:end]
            i = end
            continue
        if char == "|" and code_run == 0:
            cells.append(cell.strip())
            cell = ""
        else:
            cell += char
        i += 1
    cells.append(cell.strip())
    return cells
