#!/usr/bin/python3 -I
"""Deploy merged AUTO_NEXT sources with root-only backups and bounded rollback."""

import datetime
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

SOURCE = Path("/srv/ailab/project")
CONFIG = Path("/etc/cap-plane-queue")


def restore_targets(mapping):
    """Back up wider operational context, restore only files this feature changes."""
    return set(mapping) | {
        str(CONFIG / "transition-policy.json"),
        str(CONFIG / "catalog.json"),
        "/usr/local/share/cap-plane-transition/policy-manifest.json",
        "/etc/sudoers.d/cap-plane-advance",
    }


def main():
    if os.geteuid() != 0:
        raise PermissionError("Root required")
    os.umask(0o077)
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
    mapping = {
        "/usr/local/libexec/cap-plane-transition": "tools/host/plane-transition/transition.py",
        "/usr/local/bin/cap-plane-transition": "tools/host/plane-transition/cap-plane-transition",
        "/usr/local/libexec/cap-plane-queue": "tools/host/plane-queue/queue.py",
        "/usr/local/bin/cap-plane-queue": "tools/host/plane-queue/cap-plane-queue",
        "/usr/local/libexec/cap-auto-next.py": "tools/host/plane-transition/auto_next.py",
        "/usr/local/libexec/execution_queue.py": "tools/projectctl/src/projectctl/execution_queue.py",
        "/usr/local/bin/cap-plane-advance": "tools/host/plane-transition/cap-plane-advance",
    }
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
    # Restores deployment only, never database/state or audit history.
    rollback = """#!/usr/bin/python3 -I
import json,os,shutil,subprocess
from pathlib import Path
assert os.geteuid()==0
base=Path(__file__).resolve().parent
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
    draft = backup / "sudoers-check"
    draft.write_text("\n".join(grants) + "\n")
    draft.chmod(0o440)
    subprocess.run(["/usr/sbin/visudo", "-cf", str(draft)], check=True)
    try:
        for dest, src in mapping.items():
            write(dest, (SOURCE / src).read_bytes(), 0o755)
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
        for kind, dest in {
            "transition": "/usr/local/libexec/cap-plane-transition",
            "queue": "/usr/local/libexec/cap-plane-queue",
            "auto_next": "/usr/local/libexec/cap-auto-next.py",
            "execution_queue": "/usr/local/libexec/execution_queue.py",
        }.items():
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
        subprocess.run(["/usr/sbin/visudo", "-cf", "/etc/sudoers"], check=True)
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
