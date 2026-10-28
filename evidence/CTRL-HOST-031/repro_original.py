"""Run the CTRL-HOST-031 regression module against the ORIGINAL transition.py.

Copies tools/host/plane-transition, the queue module and the review policy into a
temporary tree, swaps in ``origin/main:tools/host/plane-transition/transition.py`` and
runs ``test_chg054_start_transitions.py`` there. Failures are the expected result: they
show which behaviors the correction changes (exit 1 when some tests fail, 0 if none do).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PKG = "tools/host/plane-transition"


def main() -> int:
    original = subprocess.run(
        ["git", "show", f"origin/main:{PKG}/transition.py"],
        cwd=REPO,
        capture_output=True,
        check=True,
    ).stdout
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for rel in (PKG, "tools/host/plane-queue", "09_change"):
            shutil.copytree(
                REPO / rel,
                root / rel,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
        (root / PKG / "transition.py").write_bytes(original)
        done = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                str(root / PKG / "test_chg054_start_transitions.py"),
            ],
            cwd=root,
            capture_output=True,
            text=True,
        )
    sys.stdout.write(done.stdout.replace(tmp, "<tmp>"))
    sys.stderr.write(done.stderr.replace(tmp, "<tmp>"))
    return 1 if done.returncode else 0


if __name__ == "__main__":
    sys.exit(main())
