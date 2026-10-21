"""Explicitly authorized repository edits with compare-and-swap rollback.

This is a policy boundary for a trusted local coordinator, not an OS sandbox.
No model response is ever interpreted as a shell command.
"""
import hashlib
import json
from pathlib import Path
import re
import secrets
import subprocess
import sys

TESTS = frozenset(('test_hermes_local_bridge.py', 'test_hermes_agent_dispatch.py',
                   'test_hermes_durable_plan.py', 'test_hermes_repo_workspace.py'))


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def git(root, *args):
    p = subprocess.run(['git', '-C', str(root), *args], capture_output=True,
                       text=True, timeout=30, check=True)
    return p.stdout.strip()


def create_worktree(authorized_root, destination, task_id):
    root = Path(authorized_root).resolve(strict=True)
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,48}', task_id):
        raise ValueError('Invalid task ID')
    if Path(git(root, 'rev-parse', '--show-toplevel')).resolve() != root:
        raise ValueError('Repository root required')
    target = Path(destination).absolute()
    if target.exists() or root == target or root in target.parents:
        raise ValueError('New destination outside checkout required')
    # Pin to observed HEAD, never silently select main or a newer remote ref.
    commit = git(root, 'rev-parse', 'HEAD')
    git(root, 'worktree', 'add', '-b', 'hermes/' + task_id, str(target), commit)
    return {'root': str(target.resolve()), 'base_commit': commit, 'branch': 'hermes/' + task_id}


class Workspace:
    def __init__(self, authorized_root, allowed_files, private_state):
        self.root = Path(authorized_root).resolve(strict=True)
        if Path(git(self.root, 'rev-parse', '--show-toplevel')).resolve() != self.root:
            raise ValueError('Repository root required')
        branch = git(self.root, 'symbolic-ref', '--short', 'HEAD')
        if branch in ('main', 'master'):
            raise ValueError('Isolated branch required')
        self.branch = branch
        self.allowed = frozenset(allowed_files)
        self.state = Path(private_state).resolve()
        if any((p / '.git').exists() for p in (self.state, *self.state.parents)):
            raise ValueError('Private backups must stay outside Git')
        self.state.mkdir(parents=True, exist_ok=True)

    def path(self, relative):
        if git(self.root, 'symbolic-ref', '--short', 'HEAD') != self.branch:
            raise ValueError('Branch changed')
        p = Path(relative)
        if relative not in self.allowed or p.is_absolute() or any(x in ('.git', '..') for x in p.parts):
            raise ValueError('File not authorized')
        current = self.root
        for part in p.parts:
            current = current / part
            # Windows junctions/reparse points and POSIX links are rejected.
            stat = current.lstat()
            if current.is_symlink() or getattr(stat, 'st_file_attributes', 0) & 0x400:
                raise ValueError('Linked paths forbidden')
        resolved = current.resolve(strict=True)
        if self.root not in resolved.parents or not resolved.is_file() or resolved.stat().st_size > 128_000:
            raise ValueError('Invalid file')
        return resolved

    def read(self, relative):
        raw = self.path(relative).read_bytes()
        return {'path': relative, 'sha256': digest(raw), 'text': raw.decode('utf-8')}

    def replace(self, relative, expected_sha, old, new):
        if not isinstance(old, str) or not old or not isinstance(new, str):
            raise ValueError('Exact nonempty replacement required')
        p = self.path(relative)
        raw = p.read_bytes()
        if digest(raw) != expected_sha:
            raise ValueError('File changed; review again')
        text = raw.decode('utf-8')
        if text.count(old) != 1:
            raise ValueError('Replacement must match exactly once')
        result = text.replace(old, new, 1).encode('utf-8')
        if len(result) > 128_000:
            raise ValueError('Result too large')
        ident = secrets.token_hex(16)
        backup = {'root': str(self.root), 'branch': self.branch, 'path': relative,
                  'before': text, 'after_sha256': digest(result)}
        (self.state / (ident + '.json')).write_text(json.dumps(backup), encoding='utf-8')
        p.write_bytes(result)
        return {'rollback_id': ident, 'sha256': digest(result)}

    def rollback(self, ident):
        if not re.fullmatch(r'[a-f0-9]{32}', ident):
            raise ValueError('Invalid rollback ID')
        data = json.loads((self.state / (ident + '.json')).read_text(encoding='utf-8'))
        if data['root'] != str(self.root) or data['branch'] != self.branch:
            raise ValueError('Wrong workspace')
        p = self.path(data['path'])
        if digest(p.read_bytes()) != data['after_sha256']:
            raise ValueError('File changed; cannot overwrite newer work')
        p.write_bytes(data['before'].encode('utf-8'))

    def test(self, name):
        if name not in TESTS:
            raise ValueError('Test command not allowed')
        # Only run trusted, reviewed repository tests; this is not process isolation.
        p = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests',
                            '-p', name, '-v'], cwd=self.root, timeout=60,
                           capture_output=True, text=True)
        return {'returncode': p.returncode, 'output': (p.stdout + p.stderr)[-16000:]}
