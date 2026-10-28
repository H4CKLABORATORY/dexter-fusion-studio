"""Failure and security contracts; real server/model evidence is recorded separately."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools' / 'hermes'))
import mobile as m
import mobile_cpu as cpu

class MobileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name); self.root = self.base / 'repo'; self.root.mkdir()
        for args in [('init', '-q', '-b', 'feature/mobile'), ('config', 'user.name', 'Test'),
                     ('config', 'user.email', 'test@example.invalid')]:
            subprocess.run(['git', *args], cwd=self.root, check=True)
        (self.root / 'README.md').write_text('baseline\n')
        subprocess.run(['git', 'add', '.'], cwd=self.root, check=True)
        subprocess.run(['git', 'commit', '-qm', 'baseline'], cwd=self.root, check=True)
        self.store = m.state_dir(self.root)

    def host(self):
        m.save(self.store / 'host.json', {'status': 'running', 'heartbeat': time.time(),
            'instance': 'test', 'model': m.CPU, 'port': 4096})

    def fake_run(self, command, root, env, logfile, seconds):
        logfile.parent.mkdir(exist_ok=True, parents=True)
        if 'run' in command:
            self.assertEqual(m.read(m.taskfile(self.store, 'one'))['status'], 'running')
            self.assertNotIn('GH_TOKEN', env)
            (root / 'result.py').write_text('answer = 42\n')
            logfile.write_text('{"type":"text"}\n')
        else:
            self.assertNotIn('OPENCODE_SERVER_PASSWORD', env); logfile.write_text('passed\n')
        return {'exit_code': 0, 'reason': 'exit', 'sha256': 'a' * 64}

    def run_task(self, runner=None, resume=False):
        self.host()
        with patch.object(m, 'probe', return_value={'models': [m.CPU]}), \
             patch.object(m, 'request', return_value=(200, {'id': 'ses_test'})), \
             patch.object(m, 'binary', return_value='opencode'), \
             patch.object(m, 'bounded', side_effect=runner or self.fake_run):
            return m.task(self.root, self.store, 'one', 'Implement small change', ['python3', '-m', 'unittest'], resume=resume)

    def test_private_state_cannot_be_inside_repo(self):
        with self.assertRaises(m.MobileError): m.state_dir(self.root, self.root / 'private')
    def test_private_state_symlink_rejected(self):
        path = self.base / 'link'; path.symlink_to(self.store)
        with self.assertRaises(m.MobileError): m.state_dir(self.root, path)
    def test_credentials_are_stable_random_and_private(self):
        auth = m.credentials(self.store)
        self.assertEqual(auth, m.credentials(self.store)); self.assertGreaterEqual(len(auth['password']), 32)
        self.assertEqual((self.store / 'auth.json').stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.store.stat().st_mode & 0o777, 0o700)
    def test_unsafe_credentials_permissions_rejected(self):
        m.credentials(self.store); (self.store / 'auth.json').chmod(0o644)
        with self.assertRaises(m.MobileError): m.credentials(self.store)
    def test_paid_models_rejected(self):
        for model in ['anthropic/claude', 'opencode/claude', 'openai/gpt', 'hermes-cpu/unapproved']:
            with self.assertRaises(m.MobileError): m.config(self.store, model)
    def test_remote_provider_is_free_only(self):
        cfg = m.config(self.store, 'opencode/big-pickle')
        self.assertEqual(cfg['enabled_providers'], ['opencode'])
        self.assertEqual(cfg['provider']['opencode']['whitelist'], list(m.FREE))
        self.assertIn('anthropic', cfg['disabled_providers']); self.assertEqual(cfg['share'], 'disabled')
    def test_agent_has_no_inherited_tokens_or_shell_hooks(self):
        keys = ['GH_TOKEN', 'GITHUB_TOKEN', 'ANTHROPIC_API_KEY', 'OPENAI_API_KEY', 'SSH_AUTH_SOCK', 'BASH_ENV']
        with patch.dict(os.environ, dict.fromkeys(keys, 'private')):
            env = m.agent_env(self.store, m.config(self.store))
        self.assertTrue(all(k not in env for k in keys)); self.assertEqual(env['HOME'], os.environ['HOME'])
    def test_external_files_and_shell_require_restrictions(self):
        rules = m.config(self.store)['permission']
        self.assertEqual(rules['external_directory'], 'deny'); self.assertEqual(rules['bash'], 'ask')
        self.assertEqual(rules['read']['**/.env*'], 'deny'); self.assertEqual(rules['read']['.git/**'], 'deny')
    def test_main_execution_is_rejected(self):
        subprocess.run(['git', 'switch', '-qc', 'main'], cwd=self.root, check=True)
        with self.assertRaises(m.MobileError): m.workspace(self.root, True)
    def test_second_writer_is_rejected_and_lock_is_released(self):
        with m.lock(self.store, 'task'):
            with self.assertRaises(m.MobileError):
                with m.lock(self.store, 'task'): pass
        with m.lock(self.store, 'task'): pass
    def test_crashed_host_is_reported_interrupted(self):
        m.save(self.store / 'host.json', {'status': 'running', 'heartbeat': time.time() - 20})
        self.assertEqual(m.status(self.store)['status'], 'interrupted')
    def test_task_ids_cannot_traverse(self):
        for ident in ['../secret', '.', '..', '', 'a/b']:
            with self.assertRaises(m.MobileError): m.taskfile(self.store, ident)
    def test_probe_requires_anonymous_401(self):
        with patch.object(m, 'request', return_value=(200, {'healthy': True, 'version': m.VERSION})):
            with self.assertRaises(m.MobileError): m.probe(self.store, 4096)
    def test_probe_rejects_priced_model(self):
        replies = [(401, None), (401, None), (200, {'healthy': True, 'version': m.VERSION}),
            (200, {'providers': [{'id': 'opencode', 'models': {'big-pickle': {'cost': {'input': 1, 'output': 0}}}}]})]
        with patch.object(m, 'request', side_effect=replies):
            with self.assertRaises(m.MobileError): m.probe(self.store, 4096)
    def test_probe_accepts_only_zero_price_and_does_not_return_credentials(self):
        replies = [(401, None), (401, None), (200, {'healthy': True, 'version': m.VERSION}),
            (200, {'providers': [{'id': 'opencode', 'models': {'big-pickle': {'cost': {'input': 0, 'output': 0}}}}]})]
        with patch.object(m, 'request', side_effect=replies): result = m.probe(self.store, 4096)
        self.assertEqual(result['models'], ['opencode/big-pickle'])
        self.assertNotIn(m.credentials(self.store)['password'], json.dumps(result))
    def test_changed_code_with_external_passing_tests_is_verified(self):
        result = self.run_task(); self.assertEqual(result['status'], 'verified')
        self.assertTrue(result['changed']); self.assertNotIn('session', result)
    def test_failed_tests_never_complete_a_task(self):
        def runner(*args):
            result = self.fake_run(*args)
            if 'run' not in args[0]: result['exit_code'] = 1
            return result
        self.assertEqual(self.run_task(runner)['status'], 'blocked')
    def test_model_error_with_exit_zero_does_not_pass(self):
        def runner(*args):
            result = self.fake_run(*args); args[3].write_text('{"type":"error"}\n'); return result
        result = self.run_task(runner)
        self.assertEqual(result['status'], 'blocked'); self.assertEqual(result['tests']['result'], 'not_run')
    def test_zero_changes_never_complete_a_task(self):
        def runner(*args):
            result = self.fake_run(*args)
            if 'run' in args[0]: (self.root / 'result.py').unlink()
            return result
        self.assertEqual(self.run_task(runner)['status'], 'blocked')
    def test_resume_rejects_changed_source(self):
        def runner(*args):
            result = self.fake_run(*args); result['exit_code'] = 1; return result
        self.run_task(runner)
        subprocess.run(['git', 'switch', '-qc', 'feature/other'], cwd=self.root, check=True)
        with self.assertRaises(m.MobileError): self.run_task(resume=True)
    def test_timeout_terminates_process(self):
        now = time.monotonic()
        result = m.bounded([sys.executable, '-c', 'import time;time.sleep(30)'], self.root,
            dict(os.environ), self.store / 'timeout.log', 1)
        self.assertEqual(result['reason'], 'timeout'); self.assertNotEqual(result['exit_code'], 0)
        self.assertLess(time.monotonic() - now, 6)
    def test_archive_traversal_is_rejected(self):
        archive = self.base / 'bad.tgz'
        with tarfile.open(archive, 'w:gz') as f:
            entry = tarfile.TarInfo('../../escape'); entry.size = 3; f.addfile(entry, io.BytesIO(b'bad'))
        with self.assertRaises(ValueError): cpu.extract(archive, self.base / 'unpack')
    def test_archive_external_symlink_is_rejected(self):
        archive = self.base / 'bad.tgz'
        with tarfile.open(archive, 'w:gz') as f:
            entry = tarfile.TarInfo('link'); entry.type = tarfile.SYMTYPE; entry.linkname = '/etc/passwd'; f.addfile(entry)
        with self.assertRaises(ValueError): cpu.extract(archive, self.base / 'unpack')

if __name__ == '__main__': unittest.main()
