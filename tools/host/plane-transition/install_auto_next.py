#!/usr/bin/python3 -I
"""Deploy merged AUTO_NEXT sources with root-only backups and bounded rollback."""

import datetime
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

SOURCE = Path("/srv/ailab/project")
CONFIG = Path("/etc/cap-plane-queue")
RECONCILE_LIBEXEC = "/usr/local/libexec/cap-plane-reconcile.py"
RECONCILE_SUDOERS = "/etc/sudoers.d/cap-plane-reconcile"
PROFILES = ("asrin", "selman", "batuhan", "yavuz")
RECONCILE_TARGETS = ("MERGED", "VALIDATING")


def deployment_mapping():
    """Installed path -> reviewed repository source, for every deployed file."""
    mapping = {
        "/usr/local/libexec/cap-plane-transition": "tools/host/plane-transition/transition.py",
        "/usr/local/bin/cap-plane-transition": "tools/host/plane-transition/cap-plane-transition",
        "/usr/local/libexec/cap-plane-queue": "tools/host/plane-queue/queue.py",
        "/usr/local/bin/cap-plane-queue": "tools/host/plane-queue/cap-plane-queue",
        "/usr/local/libexec/cap-auto-next.py": "tools/host/plane-transition/auto_next.py",
        "/usr/local/libexec/execution_queue.py": "tools/projectctl/src/projectctl/execution_queue.py",
        "/usr/local/bin/cap-plane-advance": "tools/host/plane-transition/cap-plane-advance",
        "/usr/local/bin/cap-plane-health": "tools/host/plane-transition/cap-plane-health",
        "/usr/local/libexec/cap-plane-health.py": "tools/host/plane-transition/health.py",
        "/usr/local/libexec/cap-plane-health-snapshot.py": "tools/host/plane-transition/health_snapshot.py",
        "/etc/systemd/system/cap-plane-health.service": "tools/host/plane-transition/cap-plane-health.service",
        "/etc/systemd/system/cap-plane-health.timer": "tools/host/plane-transition/cap-plane-health.timer",
    }
    mapping.update(
        {
            "/usr/local/libexec/cap-preparation.py": "tools/host/plane-transition/preparation.py",
            "/usr/local/libexec/cap-plane-prepare.py": "tools/host/plane-transition/prepare.py",
            "/usr/local/bin/cap-plane-prepare": "tools/host/plane-transition/cap-plane-prepare",
            "/etc/systemd/system/cap-plane-prepare.service": "tools/host/plane-transition/cap-plane-prepare.service",
            "/etc/systemd/system/cap-plane-prepare.timer": "tools/host/plane-transition/cap-plane-prepare.timer",
        }
    )
    mapping.update(
        {
            RECONCILE_LIBEXEC: "tools/host/plane-transition/reconcile.py",
            "/usr/local/bin/cap-plane-reconcile": "tools/host/plane-transition/cap-plane-reconcile",
        }
    )
    return mapping


# Installed implementation files whose hashes the generated policy pins.
IMPLEMENTATION_TARGETS = {
    "transition": "/usr/local/libexec/cap-plane-transition",
    "queue": "/usr/local/libexec/cap-plane-queue",
    "auto_next": "/usr/local/libexec/cap-auto-next.py",
    "execution_queue": "/usr/local/libexec/execution_queue.py",
    "health": "/usr/local/libexec/cap-plane-health.py",
    "health_snapshot": "/usr/local/libexec/cap-plane-health-snapshot.py",
    "preparation": "/usr/local/libexec/cap-preparation.py",
    "prepare": "/usr/local/libexec/cap-plane-prepare.py",
    "reconcile": RECONCILE_LIBEXEC,
}


def reconcile_grants(policy):
    """Exact-argv sudo lines derived from the policy allow-list; no globs or regexes.

    One line per allow-listed profile, WP and target. Every value is validated
    before it becomes privileged command text.
    """
    lines = ["# Lifecycle reconciliation: exact allow-listed own-profile invocations"]
    for case in policy["lifecycle_reconciliation"]["cases"]:
        profile, wp = case["profile"], case["wp_id"]
        if profile not in PROFILES or not re.fullmatch(r"WP-[A-Z0-9]+-[0-9]{3}", wp):
            raise ValueError("Invalid reconciliation grant identity")
        for target in case["targets"]:
            if target not in RECONCILE_TARGETS:
                raise ValueError("Invalid reconciliation grant target")
            lines.append(
                f"{profile} ALL=(root) NOPASSWD: NOSETENV: /usr/bin/python3 -I "
                f"{RECONCILE_LIBEXEC} {profile} {wp} {target}"
            )
    return lines


def restore_targets(mapping):
    """Back up wider operational context, restore only files this feature changes."""
    return set(mapping) | {
        str(CONFIG / "transition-policy.json"),
        str(CONFIG / "catalog.json"),
        "/usr/local/share/cap-plane-transition/policy-manifest.json",
        "/etc/sudoers.d/cap-plane-advance",
        "/etc/sudoers.d/cap-plane-health",
        RECONCILE_SUDOERS,
    }


def main():
    if os.geteuid() != 0:
        raise PermissionError("Root required")
    os.umask(0o077)
    fd = os.open(
        "/run/cap-plane-queue.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600
    )
    deployment_lock = os.fdopen(fd, "r+")
    if os.fstat(fd).st_uid != 0:
        raise PermissionError("Unsafe lock owner")
    fcntl.flock(deployment_lock, fcntl.LOCK_EX)
    status = subprocess.check_output(
        ["git", "-C", str(SOURCE), "status", "--porcelain"], text=True
    )
    head = subprocess.check_output(
        ["git", "-C", str(SOURCE), "rev-parse", "HEAD"], text=True
    ).strip()
    remote = subprocess.check_output(
        ["git", "-C", str(SOURCE), "rev-parse", "origin/main"], text=True
    ).strip()
    if status or head != remote:
        raise ValueError("Clean merged reference source required")
    mapping = deployment_mapping()
    policy = json.loads(
        Path("/srv/ailab/remote-ssh/staging/plane-transition-policy.json").read_text()
    )
    for name, expected in policy["source_manifest"].items():
        if hashlib.sha256((SOURCE / name).read_bytes()).hexdigest() != expected:
            raise ValueError("Stale generated source policy")
    backup = Path("/root") / (
        "cap-auto-next-"
        + datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%S%fZ")
    )
    backup.mkdir(mode=0o700)
    touched = list(mapping) + [
        str(CONFIG / "transition-policy.json"),
        str(CONFIG / "catalog.json"),
        str(CONFIG / "credential.json"),
        "/usr/local/share/cap-plane-transition/policy-manifest.json",
        "/etc/sudoers.d/cap-plane-advance",
        "/etc/sudoers.d/cap-plane-queue",
        "/etc/sudoers.d/cap-plane-transition",
        "/etc/sudoers.d/cap-plane-health",
        RECONCILE_SUDOERS,
    ]
    originals = []
    for name in touched:
        path = Path(name)
        if path.is_symlink():
            raise ValueError("Symlink deployment target")
        exists = path.exists()
        originals.append(
            {
                "path": name,
                "existed": exists,
                "restore": name in restore_targets(mapping),
            }
        )
        if exists:
            target = backup / name.lstrip("/")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
    (backup / "inventory.json").write_text(json.dumps(originals, indent=2))
    timer_state = {
        name: subprocess.run(
            ["systemctl", action, name], capture_output=True
        ).returncode
        == 0
        for name, action in [
            ("cap-plane-health.timer", "is-enabled"),
            ("cap-plane-health.service", "is-active"),
        ]
    }
    (backup / "timer-state.json").write_text(json.dumps(timer_state))
    prep_timer_state = (
        subprocess.run(
            ["systemctl", "is-enabled", "cap-plane-prepare.timer"], capture_output=True
        ).returncode
        == 0
    )
    (backup / "prepare-timer-state.json").write_text(json.dumps(prep_timer_state))
    # Restores deployment only, never database/state or audit history.
    rollback = """#!/usr/bin/python3 -I
import json,os,shutil,subprocess
from pathlib import Path
assert os.geteuid()==0
base=Path(__file__).resolve().parent
subprocess.run(['systemctl','disable','--now','cap-plane-prepare.timer'],capture_output=True)
subprocess.run(['systemctl','stop','cap-plane-prepare.service'],capture_output=True)
subprocess.run(['systemctl','disable','--now','cap-plane-health.timer'],capture_output=True)
for item in json.loads((base/'inventory.json').read_text()):
    if not item['restore']:
        continue
    target=Path(item['path'])
    assert not target.is_symlink()
    if item['existed']:
        shutil.copy2(base/item['path'].lstrip('/'),target)
        os.chown(target,0,0)
    elif target.exists():
        target.unlink()
subprocess.run(['/usr/sbin/visudo','-cf','/etc/sudoers'],check=True)
subprocess.run(['systemctl','daemon-reload'],check=True)
if json.loads((base/'timer-state.json').read_text())['cap-plane-health.timer']:
    subprocess.run(['systemctl','enable','--now','cap-plane-health.timer'],check=True)
if json.loads((base/'prepare-timer-state.json').read_text()):
    subprocess.run(['systemctl','enable','--now','cap-plane-prepare.timer'],check=True)
print('AUTO_NEXT deployment restored; Plane states and audit untouched. Source policy drift remains fail-closed.')
"""
    (backup / "rollback.py").write_text(rollback)
    (backup / "rollback.py").chmod(0o700)

    def write(path, raw, mode):
        path = Path(path)
        if path.is_symlink():
            raise ValueError("Unsafe deployment target")
        temp = path.with_name(path.name + ".auto-next-new")
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.chown(temp, 0, 0)
        os.chmod(temp, mode)
        os.replace(temp, path)

    # Validate sudo grants before modifying existing helpers.
    grants = [
        "# CTRL-HOST-004; exact own-profile command, admin all mode requires root"
    ]
    for profile in ("asrin", "selman", "batuhan", "yavuz"):
        grants.append(
            profile
            + " ALL=(root) NOPASSWD: NOSETENV: /usr/bin/python3 -I /usr/local/libexec/cap-auto-next.py "
            + profile
        )
    health_grants = ["# CTRL-HOST-005 exact read-only own-profile invocations"]
    for profile in ("asrin", "selman", "batuhan", "yavuz"):
        for suffix in ("", " --json"):
            health_grants.append(
                profile
                + " ALL=(root) NOPASSWD: NOSETENV: /usr/bin/python3 -I /usr/local/libexec/cap-plane-health.py "
                + profile
                + suffix
            )
    health_draft = backup / "health-sudoers-check"
    health_draft.write_text("\n".join(health_grants) + "\n")
    health_draft.chmod(0o440)
    subprocess.run(["/usr/sbin/visudo", "-cf", str(health_draft)], check=True)
    reconcile_draft = backup / "reconcile-sudoers-check"
    reconcile_draft.write_text("\n".join(reconcile_grants(policy)) + "\n")
    reconcile_draft.chmod(0o440)
    subprocess.run(["/usr/sbin/visudo", "-cf", str(reconcile_draft)], check=True)
    draft = backup / "sudoers-check"
    draft.write_text("\n".join(grants) + "\n")
    draft.chmod(0o440)
    subprocess.run(["/usr/sbin/visudo", "-cf", str(draft)], check=True)
    try:
        for dest, src in mapping.items():
            write(
                dest,
                (SOURCE / src).read_bytes(),
                0o644 if dest.endswith((".service", ".timer")) else 0o755,
            )
        write(
            CONFIG / "transition-policy.json",
            json.dumps(policy, ensure_ascii=False, sort_keys=True).encode(),
            0o600,
        )
        catalog = {
            "owners": {
                wp: context["work_package"]["primary_owner"]["canonical_name"]
                for wp, context in policy["contexts"].items()
            },
            "source_manifest": policy["source_manifest"],
        }
        write(
            CONFIG / "catalog.json",
            json.dumps(catalog, ensure_ascii=False, sort_keys=True).encode(),
            0o600,
        )
        for kind, dest in IMPLEMENTATION_TARGETS.items():
            if (
                hashlib.sha256(Path(dest).read_bytes()).hexdigest()
                != policy["implementation_sha256"][kind]
            ):
                raise ValueError("Installed policy implementation mismatch")
        public = {
            k: v
            for k, v in policy.items()
            if k not in {"contexts", "execution_project", "execution_preferences"}
        }
        write(
            "/usr/local/share/cap-plane-transition/policy-manifest.json",
            json.dumps(public, sort_keys=True).encode(),
            0o644,
        )
        write("/etc/sudoers.d/cap-plane-advance", draft.read_bytes(), 0o440)
        write("/etc/sudoers.d/cap-plane-health", health_draft.read_bytes(), 0o440)
        write(RECONCILE_SUDOERS, reconcile_draft.read_bytes(), 0o440)
        subprocess.run(["/usr/sbin/visudo", "-cf", "/etc/sudoers"], check=True)
        subprocess.run(
            [
                "systemd-analyze",
                "verify",
                "/etc/systemd/system/cap-plane-health.service",
                "/etc/systemd/system/cap-plane-health.timer",
            ],
            check=True,
        )
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        subprocess.run(
            ["systemctl", "enable", "--now", "cap-plane-health.timer"], check=True
        )
        subprocess.run(
            [
                "systemd-analyze",
                "verify",
                "/etc/systemd/system/cap-plane-prepare.service",
                "/etc/systemd/system/cap-plane-prepare.timer",
            ],
            check=True,
        )
        subprocess.run(
            ["systemctl", "enable", "--now", "cap-plane-prepare.timer"], check=True
        )
        hashes = {
            dest: hashlib.sha256(Path(dest).read_bytes()).hexdigest()
            for dest in mapping
        }
        for dest, src in mapping.items():
            if hashes[dest] != hashlib.sha256((SOURCE / src).read_bytes()).hexdigest():
                raise ValueError("Installed source hash mismatch")
        log = Path("/var/log/cap-plane-transition")
        log.mkdir(mode=0o700, exist_ok=True)
        (log / "audit.jsonl").touch(mode=0o600, exist_ok=True)
        record = {
            "source_sha": head,
            "backup": str(backup),
            "hashes": hashes,
            "policy_digest": policy["policy_digest"],
            "rollback": str(backup / "rollback.py"),
        }
        (backup / "deployment.json").write_text(json.dumps(record, indent=2))
        print(json.dumps(record, sort_keys=True))
    except Exception:
        subprocess.run(
            ["/usr/bin/python3", "-I", str(backup / "rollback.py")], check=True
        )
        raise


if __name__ == "__main__":
    main()
