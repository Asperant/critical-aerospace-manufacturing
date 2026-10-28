"""Produce RUN-CICD-002-DEV-001: the WP-CICD-002 development run on the shared host.

Run from the repository root on a clean checkout of main, after the `release` workflow
has published the image of a main commit:

    uv run --project ci --locked python evidence/WP-CICD-002/collect_run.py <release-run-id> [NNN]

The optional NNN numbers the run (RUN-CICD-002-DEV-NNN); every run is kept, failed ones too.

It downloads that run's ReleaseManifest, checks out the release commit in a throw-away
worktree and, with `python -m cap_release deploy`:

1. refuses a deployment while the host source tree carries a manual change;
2. refuses a manifest whose image digest is not in the registry;
3. deploys the real manifest: the image is pulled by digest and nothing is built on the
   host, then health and the REAL smoke tests pass and a DeploymentRecord is written.

Every command is a real invocation; exit codes and output are recorded as observed.
Host paths and the host name are replaced with placeholders. Run records are kept in a
temporary state directory so the host's own release state is untouched.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

RUN_ID = "RUN-CICD-002-DEV-" + (sys.argv[2] if len(sys.argv) > 2 else "001")
ANSI = re.compile(r"\x1b\[[0-9;]*m")
REPO = "Asperant/critical-aerospace-manufacturing"


def sh(
    *argv: str, cwd: Path | None = None, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(argv), capture_output=True, text=True, check=False, cwd=cwd, env=env
    )


def main() -> int:
    if len(sys.argv) not in {2, 3} or not sys.argv[1].isdigit():
        print("usage: collect_run.py <release-run-id> [NNN]", file=sys.stderr)
        return 2
    release_run = sys.argv[1]
    root = Path(sh("git", "rev-parse", "--show-toplevel").stdout.strip())
    os.chdir(root)
    if sh("git", "status", "--porcelain").stdout.strip():
        print("Refusing to run: commit or stash local changes first.", file=sys.stderr)
        return 2
    out = root / "evidence" / "WP-CICD-002" / RUN_ID
    out.mkdir(parents=True, exist_ok=True)
    home = str(Path.home())
    work = Path(tempfile.mkdtemp(prefix="cicd002-"))
    replacements = [
        (home, "<home>"),
        (str(root), "<repo>"),
        (str(work), "<tmp>"),
        (socket.gethostname(), "<host>"),
    ]

    def clean(text: str) -> str:
        text = ANSI.sub("", text)
        for old, new in replacements:
            text = text.replace(old, new)
        return (
            "\n".join(line.rstrip() for line in text.splitlines()).rstrip("\n") + "\n"
        )

    def save(name: str, text: str) -> None:
        (out / name).write_text(clean(text), encoding="utf-8")

    steps: list[dict[str, Any]] = []

    def record(step: str, code: int, note: str, output: str) -> None:
        steps.append({"step": step, "exit_code": code, "note": note, "output": output})
        print(f"{step:<22} exit={code} -> {output}")

    # 1. the release manifest of the published run
    mdir = work / "manifest"
    done = sh(
        "gh",
        "run",
        "download",
        release_run,
        "-R",
        REPO,
        "-D",
        str(mdir),
        "--pattern",
        "release-manifest-*",
    )
    manifest_path = next(mdir.rglob("release-manifest.json"), None)
    if done.returncode != 0 or manifest_path is None:
        print(done.stderr, file=sys.stderr)
        return 2
    manifest = json.loads(manifest_path.read_text("utf-8"))
    commit = manifest["source"]["commit"]
    save("release-manifest.json", json.dumps(manifest, indent=2, sort_keys=True))
    record(
        "manifest",
        0,
        f"{manifest['release_id']} at {commit[:12]}",
        "release-manifest.json",
    )

    # 2. a clean worktree of the release commit stands for the host checkout
    tree = work / "host-checkout"
    sh("git", "fetch", "--quiet", "origin", "main")
    done = sh("git", "worktree", "add", "--detach", str(tree), commit)
    if done.returncode != 0:
        print(done.stderr, file=sys.stderr)
        return 2
    state = work / "state"
    env = {
        **os.environ,
        "PYTHONPATH": "tools/release/src",
        "CAP_RELEASE_STATE_DIR": str(state),
    }
    deploy = [
        "uv",
        "run",
        "--project",
        "ci",
        "--locked",
        "python",
        "-m",
        "cap_release",
        "deploy",
    ]

    def run_deploy(label: str, manifest_file: Path) -> dict[str, Any]:
        done = sh(*deploy, "--manifest", str(manifest_file), cwd=tree, env=env)
        save(f"{label}.stderr.txt", done.stderr)
        try:
            data = json.loads(done.stdout)
        except ValueError:
            data = {}
        save(f"{label}.record.json", json.dumps(data, indent=2, sort_keys=True))
        record(
            label,
            done.returncode,
            f"result {data.get('result')}",
            f"{label}.record.json",
        )
        return data

    try:
        # (a) a manual patch on the host source tree
        patched = tree / "infra" / "compose" / "README.md"
        patched.write_text(patched.read_text("utf-8") + "\nmanual host edit\n", "utf-8")
        refusal_dirty = run_deploy("refusal-dirty-tree", manifest_path)
        sh("git", "checkout", "--", "infra/compose/README.md", cwd=tree)

        # (b) a digest that the registry does not hold
        forged = json.loads(manifest_path.read_text("utf-8"))
        forged["service_images"][0]["digest"] = "sha256:" + "0" * 64
        forged["service_images"][0]["reference"] = (
            forged["service_images"][0]["repository"]
            + "@"
            + forged["service_images"][0]["digest"]
        )
        forged_path = work / "forged-manifest.json"
        forged_path.write_text(json.dumps(forged), "utf-8")
        refusal_digest = run_deploy("refusal-unknown-digest", forged_path)

        # (c) the real deployment
        success = run_deploy("deploy", manifest_path)
        inspect = sh(
            "docker",
            "inspect",
            "cap-platform-mlflow-1",
            "--format",
            "{{.Config.Image}} | {{.Image}}",
        )
        save("mlflow-container-image.txt", inspect.stdout)
        record(
            "container-image",
            inspect.returncode,
            "the running container's image reference",
            "mlflow-container-image.txt",
        )
        build_probe = sh(
            "docker",
            "compose",
            "-f",
            "infra/compose/compose.yaml",
            "images",
            "mlflow",
            cwd=tree,
        )
        save("compose-images.txt", build_probe.stdout + build_probe.stderr)
        sh("infra/compose/stack.sh", "down", cwd=tree, env=env)
    finally:
        sh("git", "worktree", "remove", "--force", str(tree))
        shutil.rmtree(work, ignore_errors=True)

    summary = {
        "run_id": RUN_ID,
        "work_package": "WP-CICD-002",
        "kind": "DEV run on the shared host: the first published image, deployed from a clean checkout of its commit",
        "boundary_mode": "REAL",
        "code_revision": sh("git", "rev-parse", "HEAD").stdout.strip(),
        "release_run": release_run,
        "release_id": manifest["release_id"],
        "release_commit": commit,
        "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "outcomes": {
            "refusal_dirty_tree": {
                "result": refusal_dirty.get("result"),
                "preflight": (refusal_dirty.get("stages") or [{}])[0].get("detail"),
            },
            "refusal_unknown_digest": {
                "result": refusal_digest.get("result"),
                "preflight": (refusal_digest.get("stages") or [{}])[0].get("detail"),
            },
            "deploy": {
                "result": success.get("result"),
                "stages": {s["stage"]: s["result"] for s in success.get("stages", [])},
                "record_id": success.get("record_id"),
            },
        },
        "steps": steps,
        "non_zero_explained": {
            "refusal-dirty-tree": "expected: the host source tree carried a manual change",
            "refusal-unknown-digest": "expected: the forged digest is not in the registry",
        },
    }
    (out / "record.json").write_text(
        clean(json.dumps(summary, indent=2, ensure_ascii=False)), encoding="utf-8"
    )
    print(f"Recorded {RUN_ID}: deploy={success.get('result')}")
    return 0 if success.get("result") == "SUCCEEDED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
