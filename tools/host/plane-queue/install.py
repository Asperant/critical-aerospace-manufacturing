#!/usr/bin/python3 -I
"""Owner-authorized host install. Run as root; never imports developer code as root."""
import json
import os
from pathlib import Path
import shlex
import stat
import subprocess
import sys

SOURCE = Path('/srv/ailab/project/tools/host/plane-queue')
ROOT = Path('/etc/cap-plane-queue')
LEGACY = Path('/srv/ailab/project/project_control/local/plane.env')
CATALOG = Path('/srv/ailab/remote-ssh/staging/plane-queue-catalog.json')
HELPER = Path('/usr/local/libexec/cap-plane-queue')
SUDOERS = Path('/etc/sudoers.d/cap-plane-queue')


def secure_dir(path, mode):
    if path.is_symlink():
        raise RuntimeError('Unsafe destination')
    path.mkdir(mode=mode, exist_ok=True)
    if path.stat().st_uid != 0:
        raise RuntimeError('Destination must be root-owned')
    path.chmod(mode)


def write(path, data, mode):
    if path.is_symlink():
        raise RuntimeError('Unsafe destination')
    temporary = path.with_name(path.name + '.new')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.chown(temporary, 0, 0)
    os.chmod(temporary, mode)
    os.replace(temporary, path)


def main():
    if os.geteuid() != 0 or len(sys.argv) != 1:
        raise RuntimeError('Root install only; no arguments')
    os.umask(0o077)
    secure_dir(ROOT, 0o700)
    secure_dir(Path('/usr/local/libexec'), 0o755)
    keyfile = ROOT / 'credential.json'
    if not keyfile.exists():
        values = {}
        if LEGACY.is_symlink():
            raise RuntimeError('Unsafe credential source')
        for line in LEGACY.read_text().splitlines():
            key, sep, raw = line.strip().removeprefix('export ').partition('=')
            if sep and key.startswith('PLANE_'):
                parts = shlex.split(raw, comments=True)
                if len(parts) != 1 or key in values:
                    raise RuntimeError('Invalid credential source')
                values[key] = parts[0]
        key = values['PLANE_API_KEY']
        if not key or any(c in key for c in '\r\n'):
            raise RuntimeError('Invalid credential')
        write(keyfile, json.dumps({'api_key':key}).encode(), 0o600)
    if keyfile.stat().st_uid != 0 or stat.S_IMODE(keyfile.stat().st_mode) != 0o600:
        raise RuntimeError('Unsafe credential ownership/mode')
    catalog = json.loads(CATALOG.read_text())
    if len(catalog['owners']) != 180 or set(catalog['owners'].values()) != {'Asrın Dündar','Selman Özdemir','Batuhan Kaya','Yavuz Gümüş'}:
        raise RuntimeError('Invalid canonical identity catalog')
    write(ROOT / 'catalog.json', json.dumps(catalog).encode(), 0o644)
    write(HELPER, (SOURCE / 'queue.py').read_bytes(), 0o755)
    write(Path('/usr/local/bin/cap-plane-queue'), (SOURCE / 'cap-plane-queue').read_bytes(), 0o755)
    text = '# CTRL-HOST-002: display scope only; no user-controlled URL/method/environment.\n'
    text += 'Defaults!/usr/local/libexec/cap-plane-queue env_reset, !setenv\n'
    text += 'ailab ALL=(root) NOPASSWD: NOSETENV: ' + ', '.join(str(HELPER) + ' ' + p for p in ('asrin','selman','batuhan','yavuz')) + '\n'
    draft = ROOT / 'sudoers-check'
    write(draft, text.encode(), 0o440)
    subprocess.run(['/usr/sbin/visudo','-cf',str(draft)], check=True)
    write(SUDOERS, text.encode(), 0o440)
    subprocess.run(['/usr/sbin/visudo','-cf','/etc/sudoers'], check=True)
    if LEGACY.exists():
        # Remove only the reference clone's ignored legacy credential; never visit workspaces.
        values = {}
        for line in LEGACY.read_text().splitlines():
            key, sep, raw = line.strip().removeprefix('export ').partition('=')
            if sep and key == 'PLANE_API_KEY':
                values[key] = shlex.split(raw, comments=True)[0]
        if values.get('PLANE_API_KEY') != json.loads(keyfile.read_text())['api_key']:
            raise RuntimeError('Legacy credential differs; not removed')
        LEGACY.unlink()
    print('Installed root-owned GET-only helper, fixed-profile sudo rules; legacy credential migrated.')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('INSTALL_FAILED (details redacted)', file=sys.stderr)
        sys.exit(1)
