#!/usr/bin/env python3
"""Bounded local Plane backup and isolated restore verification; no live restore."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import uuid

BACKUP_ROOT = Path('/srv/ailab/backups')
DEPLOYMENT = Path('/srv/ailab/plane/plane-app')
DB = 'plane-app-plane-db-1'
STORE = 'plane-app-plane-minio-1'
COUNTS = "SELECT json_build_object('issues',(SELECT count(*) FROM issues),'modules',(SELECT count(*) FROM modules),'cycles',(SELECT count(*) FROM cycles),'labels',(SELECT count(*) FROM labels),'states',(SELECT count(*) FROM states));"


def run(args, **kwargs):
    result = subprocess.run(args, stderr=subprocess.PIPE, **kwargs)
    if result.returncode:
        raise RuntimeError('Backup operation failed (command output redacted)')
    return result.stdout


def inspect(name):
    return json.loads(run(['docker', 'inspect', name], stdout=subprocess.PIPE))[0]


def db_command(command, extra=()):
    # Values expand only inside the verified container, never in host argv/logs.
    return ['docker', 'exec', DB, 'sh', '-c',
            'PGPASSWORD="$POSTGRES_PASSWORD" ' + command +
            ' -w -h /var/run/postgresql -U "$POSTGRES_USER" -d "${POSTGRES_DB:-$POSTGRES_USER}" "$@"',
            'plane-backup', *extra]


def live_counts():
    return json.loads(run(db_command('psql', ('-Atc', COUNTS)), stdout=subprocess.PIPE))


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def safe_backup(path):
    path = Path(path)
    if BACKUP_ROOT.is_symlink() or path.is_symlink() or path.resolve().parent != BACKUP_ROOT.resolve() or not path.is_dir():
        raise ValueError('Backup must be an existing direct child of the approved backup root')
    return path.resolve()


def verify_files(path):
    path = safe_backup(path)
    manifest = json.loads((path / 'manifest.json').read_text())
    expected = manifest['sha256']
    actual = {}
    for file in path.rglob('*'):
        if file.is_symlink():
            raise ValueError('Backup symlinks are not accepted')
        if file.is_file() and file not in {path / 'manifest.json', path / 'restore-verification.json'}:
            actual[str(file.relative_to(path))] = digest(file)
    if not expected or actual != expected:
        raise ValueError('Backup checksum inventory mismatch')
    return manifest


def backup():
    topology = []
    for name, destination in [(DB, '/var/lib/postgresql/data'), (STORE, '/export')]:
        data = inspect(name)
        labels = data['Config']['Labels']
        if labels.get('com.docker.compose.project') != 'plane-app' or not data['State']['Running']:
            raise ValueError('Unexpected Plane deployment identity or stopped persistence service')
        if not any(m['Type'] == 'volume' and m['Destination'] == destination for m in data['Mounts']):
            raise ValueError('Expected Plane persistence volume missing')
        topology.append({'name': name, 'image_id': data['Image'], 'mounts': data['Mounts'],
                         'restart_policy': data['HostConfig']['RestartPolicy']})
    if BACKUP_ROOT.is_symlink() or not BACKUP_ROOT.is_dir():
        raise ValueError('Approved backup root must already exist and not be a symlink')
    if os.statvfs(BACKUP_ROOT).f_bavail * os.statvfs(BACKUP_ROOT).f_frsize < 1024 ** 3:
        raise ValueError('Less than 1 GiB free at backup target')
    path = BACKUP_ROOT / ('plane-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8])
    path.mkdir(mode=0o700)
    before = live_counts()
    with (path / 'postgres.dump').open('xb') as stream:
        run(db_command('pg_dump', ('-Fc',)), stdout=stream)
    # Docker archive-copy reads both actual object-store mounts; no live volume is attached elsewhere.
    for source, target in [('/export', 'object-export'), ('/data', 'object-data')]:
        run(['docker', 'cp', STORE + ':' + source, str(path / target)], stdout=subprocess.PIPE)
    for name in ['docker-compose.yaml', 'plane.env']:
        source = DEPLOYMENT / name
        if source.is_symlink() or not source.is_file():
            raise ValueError('Deployment configuration unavailable or symlinked')
        (path / name).write_bytes(source.read_bytes())
    after = live_counts()
    if before != after:
        raise ValueError('Live counts changed during backup; retain attempt, do not certify it')
    for file in path.rglob('*'):
        if file.is_file():
            file.chmod(0o600)
        elif file.is_dir():
            file.chmod(0o700)
    manifest = {'schema': 'plane-backup-v1', 'created_utc': datetime.now(timezone.utc).isoformat(),
                'path': str(path), 'topology': topology, 'database_counts': before,
                'consistency': 'PostgreSQL MVCC dump; object store copied live, no cross-store atomic snapshot claimed',
                'limitations': 'Broker/Valkey queues and worker logs are not backed up; disaster recovery requires quiesced reconciliation before worker startup',
                'sha256': {str(f.relative_to(path)): digest(f) for f in sorted(path.rglob('*')) if f.is_file()}}
    (path / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (path / 'manifest.json').chmod(0o600)
    verify_files(path)
    return {'result': 'PASS', 'backup_path': str(path), 'integrity': 'SHA256 PASS', 'database_counts': before}


def restore_command(name, image='postgres:15.7-alpine'):
    return ['docker', 'run', '-d', '--pull', 'never', '--name', name, '--network', 'none', '--memory', '512m', '--cpus', '1',
            '--tmpfs', '/var/lib/postgresql/data:rw,noexec,nosuid,size=256m',
            '-e', 'POSTGRES_HOST_AUTH_METHOD=trust', image]


def verify_restore(path):
    path = safe_backup(path)
    manifest = verify_files(path)
    name = 'plane-restore-verify-' + uuid.uuid4().hex
    # Unique new container, no -v/--mount/--volumes-from, no published ports; never restore live.
    run(restore_command(name, manifest['topology'][0]['image_id']), stdout=subprocess.PIPE)
    try:
        data = inspect(name)
        if data['HostConfig']['NetworkMode'] != 'none' or any(m['Type'] != 'tmpfs' for m in data['Mounts']):
            raise ValueError('Isolated restore target failed safety assertions')
        ready = False
        for _ in range(30):
            result = subprocess.run(['docker', 'exec', name, 'pg_isready', '-U', 'postgres'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if result.returncode == 0:
                ready = True
                break
            time.sleep(1)
        if not ready:
            raise RuntimeError('Isolated PostgreSQL did not become ready')
        run(['docker', 'exec', name, 'createdb', '-U', 'postgres', 'plane_restore'], stdout=subprocess.PIPE)
        with (path / 'postgres.dump').open('rb') as stream:
            run(['docker', 'exec', '-i', name, 'pg_restore', '--exit-on-error', '--no-owner', '--no-privileges',
                 '-U', 'postgres', '-d', 'plane_restore'], stdin=stream, stdout=subprocess.PIPE)
        restored = json.loads(run(['docker', 'exec', name, 'psql', '-U', 'postgres', '-d', 'plane_restore', '-Atc', COUNTS], stdout=subprocess.PIPE))
        if restored != manifest['database_counts']:
            raise ValueError('Restored database counts disagree with backup observation')
        verify_files(path)
        report = {'result': 'PASS', 'backup_path': str(path), 'container': name, 'network': 'none',
                  'live_volumes_attached': False, 'restored_counts': restored,
                  'object_storage': 'All copied files rehashed; live object service restore not performed',
                  'live_restore': False, 'cleanup': 'Stopped isolated container retained; no deletion performed'}
    finally:
        run(['docker', 'stop', name], stdout=subprocess.PIPE)
    (path / 'restore-verification.json').write_text(json.dumps(report, indent=2) + '\n')
    (path / 'restore-verification.json').chmod(0o600)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['backup', 'verify', 'verify-isolated'])
    parser.add_argument('--backup', type=Path)
    args = parser.parse_args()
    try:
        if args.action == 'backup':
            result = backup()
        elif args.backup is None:
            parser.error('--backup is required for verification')
        elif args.action == 'verify':
            verify_files(args.backup)
            result = {'result': 'PASS', 'integrity': 'SHA256 PASS', 'backup_path': str(args.backup)}
        else:
            result = verify_restore(args.backup)
        print(json.dumps(result, indent=2))
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        parser.exit(1, f'Backup/verification failed: {type(exc).__name__} (details redacted; partial artifacts retained)\n')


if __name__ == '__main__':
    main()
