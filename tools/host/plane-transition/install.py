#!/usr/bin/python3 -I
"""Install only reviewed transition code/policy; no API calls or SSH/workspace changes."""
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

SOURCE=Path('/srv/ailab/project/tools/host/plane-transition')
ROOT=Path('/etc/cap-plane-queue')
POLICY=Path('/srv/ailab/remote-ssh/staging/plane-transition-policy.json')


def write(path,data,mode):
    if path.is_symlink(): raise ValueError()
    temporary=path.with_name(path.name+'.new')
    fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
    with os.fdopen(fd,'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.chown(temporary,0,0)
    os.chmod(temporary,mode)
    os.replace(temporary,path)


def main():
    if os.geteuid()!=0 or len(sys.argv)!=1: raise ValueError()
    os.umask(0o077)
    for path in [ROOT,ROOT/'credential.json',Path('/usr/local/libexec/cap-plane-queue')]:
        if path.is_symlink() or path.stat().st_uid!=0 or path.stat().st_mode & 0o022: raise ValueError()
    policy=json.loads(POLICY.read_text())
    if policy['schema_version']!='cap-transition-policy-v1' or not policy['contexts']: raise ValueError()
    write(ROOT/'transition-policy.json',POLICY.read_bytes(),0o600)
    write(Path('/usr/local/libexec/cap-plane-transition'),(SOURCE/'transition.py').read_bytes(),0o755)
    write(Path('/usr/local/bin/cap-plane-transition'),(SOURCE/'cap-plane-transition').read_bytes(),0o755)
    log=Path('/var/log/cap-plane-transition')
    if log.is_symlink(): raise ValueError()
    log.mkdir(mode=0o700,exist_ok=True)
    if log.stat().st_uid!=0: raise ValueError()
    log.chmod(0o700)
    audit=log/'audit.jsonl'
    if audit.is_symlink(): raise ValueError()
    fd=os.open(audit,os.O_WRONLY|os.O_APPEND|os.O_CREAT|os.O_NOFOLLOW,0o600)
    os.close(fd)
    if audit.stat().st_uid!=0: raise ValueError()
    audit.chmod(0o600)
    share=Path('/usr/local/share/cap-plane-transition')
    if share.is_symlink(): raise ValueError()
    share.mkdir(mode=0o755,exist_ok=True)
    if share.stat().st_uid!=0: raise ValueError()
    share.chmod(0o755)
    public={k:v for k,v in policy.items() if k!='contexts'}
    write(share/'policy-manifest.json',json.dumps(public,sort_keys=True).encode(),0o644)
    # Exact argv grants, derived from canonical ownership; no sudo globs or regex.
    owners={'Asrın Dündar':'asrin','Selman Özdemir':'selman','Batuhan Kaya':'batuhan','Yavuz Gümüş':'yavuz'}
    targets=['BACKLOG','READY','IN_PROGRESS','IN_REVIEW','MERGE_READY','MERGED','VALIDATING','DONE','CANCELED','BLOCKED','UNBLOCKED']
    lines=['# CTRL-HOST-003: trusted-team operational guards, not UID isolation.',
           'Defaults!/usr/local/libexec/cap-plane-transition env_reset, !setenv']
    for wp,c in sorted(policy['contexts'].items()):
        # Validate before generating privileged command text.
        import re
        if not re.fullmatch(r'WP-[A-Z0-9]+-[0-9]{3}',wp): raise ValueError()
        profile=owners[c['work_package']['primary_owner']['canonical_name']]
        commands=', '.join('/usr/local/libexec/cap-plane-transition '+profile+' '+wp+' '+target for target in targets)
        lines.append('ailab ALL=(root) NOPASSWD: NOSETENV: '+commands)
    text=('\n'.join(lines)+'\n').encode()
    draft=ROOT/'transition-sudoers-check'
    write(draft,text,0o440)
    subprocess.run(['/usr/sbin/visudo','-cf',str(draft)],check=True)
    write(Path('/etc/sudoers.d/cap-plane-transition'),text,0o440)
    subprocess.run(['/usr/sbin/visudo','-cf','/etc/sudoers'],check=True)
    print('Transition helper installed; queue unchanged; no Plane request or mutation.')


if __name__=='__main__':
    try: main()
    except Exception:
        print('INSTALL_FAILED (details redacted)',file=sys.stderr)
        sys.exit(1)
