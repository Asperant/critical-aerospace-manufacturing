"""CTRL-PM-011: isolated local clones and profiles; never authenticate users."""
import argparse
import os
from pathlib import Path
import subprocess

REPO = 'https://github.com/Asperant/critical-aerospace-manufacturing.git'
IDENTITIES = {
    'asrin': ('Asrın Dündar', 'asrindundar14@hotmail.com', 'Asperant'),
    'selman': ('Selman Özdemir', 'selmanozdemir430@gmail.com', 'selorito'),
    'batuhan': ('Batuhan Kaya', 'batuhankaya0204@gmail.com', 'eilonn'),
    'yavuz': ('Yavuz Gümüş', 'yavuzgumus@gmail.com', 'Yavuzgmus'),
}


def environment(profile, inherited=None):
    env = dict(os.environ if inherited is None else inherited)
    # Do not pass the reference session's tokens, credential helpers or SSH agent.
    for key in list(env):
        if (key in {'GH_TOKEN', 'GITHUB_TOKEN', 'GH_ENTERPRISE_TOKEN', 'GITHUB_ENTERPRISE_TOKEN',
                    'OPENAI_API_KEY', 'SSH_AUTH_SOCK', 'SSH_AGENT_PID', 'GIT_ASKPASS', 'SSH_ASKPASS'}
                or key.startswith(('PLANE_', 'GIT_CONFIG_', 'GIT_SSH', 'GIT_DIR', 'GIT_WORK_TREE'))):
            env.pop(key)
    env.update(GH_CONFIG_DIR=str(profile / 'gh'), CODEX_HOME=str(profile / 'codex'),
               XDG_CONFIG_HOME=str(profile / 'config'), GIT_CONFIG_GLOBAL='/dev/null',
               GIT_CONFIG_NOSYSTEM='1', GIT_TERMINAL_PROMPT='1')
    return env


def prepare(person, base=Path('/srv/ailab'), source=Path('/srv/ailab/project')):
    name, email, login = IDENTITIES[person]
    target = base / 'workspaces' / person / 'project'
    profile = base / 'user-profiles' / person
    if target.exists():
        raise ValueError('Workspace already exists; inspect it manually; never overwrite')
    source_name = subprocess.check_output(['git', '-C', str(source), 'config', '--local', 'user.name'], text=True).strip()
    source_email = subprocess.check_output(['git', '-C', str(source), 'config', '--local', 'user.email'], text=True).strip()
    if person == 'asrin' and (source_name, source_email) != (name, email):
        raise ValueError('Reference owner identity differs; human verification required')
    for part in ['gh', 'codex', 'config', 'vscode-data', 'vscode-extensions']:
        (profile / part).mkdir(parents=True, exist_ok=True, mode=0o700)
    target.parent.mkdir(parents=True, exist_ok=True)
    env = environment(profile)
    subprocess.run(['git', 'clone', '--no-hardlinks', '--branch', 'main', str(source), str(target)], env=env, check=True)
    for key, value in [('remote.origin.url', REPO), ('user.name', name), ('user.email', email),
                       ('credential.helper', ''), ('credential.useHttpPath', 'true')]:
        subprocess.run(['git', '-C', str(target), 'config', '--local', key, value], env=env, check=True)
    subprocess.run(['git', '-C', str(target), 'config', '--local', '--add', 'credential.helper', '!gh auth git-credential'], env=env, check=True)
    return target, profile, login


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'shell', 'code'])
    parser.add_argument('person', choices=IDENTITIES)
    args = parser.parse_args()
    base = Path('/srv/ailab')
    target = base / 'workspaces' / args.person / 'project'
    profile = base / 'user-profiles' / args.person
    if args.action == 'prepare':
        print(prepare(args.person))
        return
    if not (target / '.git').is_dir():
        parser.error('Prepare the workspace first')
    env = environment(profile)
    if args.action == 'code':
        command = ['code', '--new-window', '--user-data-dir', str(profile / 'vscode-data'),
                   '--extensions-dir', str(profile / 'vscode-extensions'), str(target)]
    else:
        command = ['bash', '--noprofile', '--norc']
    subprocess.run(command, cwd=target, env=env, check=True)


if __name__ == '__main__':
    main()
