from pathlib import Path
import subprocess
import tempfile
import unittest
from tools.hermes.repo_workspace import Workspace, create_worktree


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'repo'
        self.root.mkdir()
        for args in (('init', '-b', 'task'), ('config', 'user.email', 'test@example.invalid'),
                     ('config', 'user.name', 'Test')):
            subprocess.run(['git', '-C', str(self.root), *args], check=True, capture_output=True)
        (self.root / 'code.py').write_bytes(b'value = 1\r\n')
        subprocess.run(['git', '-C', str(self.root), 'add', 'code.py'], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(self.root), 'commit', '-m', 'fixture'], check=True, capture_output=True)
        self.ws = Workspace(self.root, ['code.py'], Path(self.tmp.name) / 'private')

    def test_exact_edit_and_lossless_rollback(self):
        original = self.ws.read('code.py')
        result = self.ws.replace('code.py', original['sha256'], 'value = 1', 'value = 2')
        self.assertEqual((self.root / 'code.py').read_bytes(), b'value = 2\r\n')
        self.ws.rollback(result['rollback_id'])
        self.assertEqual((self.root / 'code.py').read_bytes(), b'value = 1\r\n')

    def test_stale_hash_and_rollback_conflict_preserve_new_work(self):
        original = self.ws.read('code.py')
        with self.assertRaises(ValueError):
            self.ws.replace('code.py', 'stale', 'value', 'other')
        result = self.ws.replace('code.py', original['sha256'], '1', '2')
        (self.root / 'code.py').write_text('new work')
        with self.assertRaises(ValueError):
            self.ws.rollback(result['rollback_id'])
        self.assertEqual((self.root / 'code.py').read_text(), 'new work')

    def test_denies_unapproved_files_commands_and_private_state_in_git(self):
        for path in ('../code.py', '.git/config', 'other.py'):
            with self.assertRaises(ValueError):
                self.ws.read(path)
        with self.assertRaises(ValueError):
            self.ws.test('whoami')
        with self.assertRaises(ValueError):
            Workspace(self.root, ['code.py'], self.root / 'private')

    def test_worktree_pins_base_and_denies_reuse(self):
        target = Path(self.tmp.name) / 'isolated'
        result = create_worktree(self.root, target, 'fixture-task')
        self.assertEqual(result['branch'], 'hermes/fixture-task')
        self.assertTrue((target / 'code.py').exists())
        with self.assertRaises(ValueError):
            create_worktree(self.root, target, 'fixture-task')
