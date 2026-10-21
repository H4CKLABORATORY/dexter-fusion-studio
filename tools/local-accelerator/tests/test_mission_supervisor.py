import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'mission_supervisor.py'
spec = importlib.util.spec_from_file_location('mission_supervisor', SCRIPT)
ms = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ms)


class SupervisorTests(unittest.TestCase):
    def test_queue_accepts_known_types(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'queue.json'
            path.write_text(json.dumps({'schemaVersion': 1, 'tasks': [{'id': 'fetch-data', 'kind': 'catalog_refresh', 'timeoutSeconds': 45}]}))
            self.assertEqual(ms.read_queue(path)[0]['id'], 'fetch-data')

    def test_queue_rejects_arbitrary_command(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'queue.json'
            path.write_text(json.dumps({'schemaVersion': 1, 'tasks': [{'id': 'bad-task', 'kind': 'shell', 'command': 'rm -rf /', 'timeoutSeconds': 45}]}))
            with self.assertRaises(ValueError):
                ms.read_queue(path)

    def test_catalog_validation(self):
        with tempfile.TemporaryDirectory() as td:
            file = Path(td) / 'catalog.json'
            records = [{'id': 'mal-'+str(i), 'title': 'Title', 'streaming': [{'url': 'https://example.org/video'}]} for i in range(5)]
            doc = {'updated': '2026-10-21T13:00:00Z', 'groups': {'trending': records}}
            file.write_text(json.dumps(doc))
            self.assertEqual(ms.validate_catalog(file), 5)
            records.append(dict(records[0]))
            file.write_text(json.dumps(doc))
            with self.assertRaisesRegex(ValueError, 'Duplicate'):
                ms.validate_catalog(file)
            records.pop()
            records[0]['streaming'][0]['url'] = 'http://insecure.example'
            file.write_text(json.dumps(doc))
            with self.assertRaisesRegex(ValueError, 'Non-HTTPS'):
                ms.validate_catalog(file)

    def test_model_endpoint_is_loopback_only(self):
        with self.assertRaises(ValueError):
            ms.model_id('http://evil.example/v1/models')

    def test_worktree_execution_checkpoint_and_resume(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project = root / 'site'
            project.mkdir()
            subprocess.run(['git', 'init', str(project)], check=True, capture_output=True)
            subprocess.run(['git', 'config', 'user.email', 'unit@test.example'], cwd=project, check=True)
            subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=project, check=True)
            (project / 'README.md').write_text('base\n')
            subprocess.run(['git', 'add', '.'], cwd=project, check=True)
            subprocess.run(['git', 'commit', '-m', 'base'], cwd=project, check=True, capture_output=True)
            queue = root / 'queue.json'
            queue.write_text(json.dumps({'schemaVersion': 1, 'tasks': [
                {'id':'step-one', 'kind':'catalog_refresh', 'timeoutSeconds':45},
                {'id':'step-two', 'kind':'qwen_catalog_review', 'timeoutSeconds':45}
            ]}))
            state_root = root / 'state'
            args = ['--project', str(project), '--state-root', str(state_root), '--queue', str(queue)]
            def action(task, worktree, log_path, venv_python, endpoint):
                (worktree / ('created-' + task['id'])).write_text('yes')
                return {'ok': True}
            with patch.object(ms, 'execute_task', side_effect=action) as fake:
                self.assertEqual(ms.main(args + ['--max-tasks', '1']), 0)
                self.assertEqual(fake.call_count, 1)
                state = json.loads((state_root / 'active.json').read_text())
                self.assertEqual(state['status'], 'paused')
                self.assertEqual(state['tasks']['step-one']['status'], 'passed')
                # An interrupted in-progress AI task must not be rerun blindly.
                state['tasks']['step-two'] = {'status': 'running'}
                ms.write_json(state_root / 'active.json', state)
                self.assertEqual(ms.main(args + ['--resume']), 1)
                self.assertEqual(fake.call_count, 1)
                state['tasks'].pop('step-two')
                ms.write_json(state_root / 'active.json', state)
                self.assertEqual(ms.main(args + ['--resume']), 0)
                self.assertEqual(fake.call_count, 2)
                state = json.loads((state_root / 'active.json').read_text())
                self.assertEqual(state['status'], 'completed')
                self.assertTrue((Path(state['worktree']) / 'created-step-one').exists())
                self.assertTrue((Path(state['worktree']) / 'created-step-two').exists())
            self.assertFalse((project / 'created-step-one').exists())

    def test_real_node_scraper_in_isolated_worktree(self):
        # Real Node invocation, but with an offline fixture rather than live AniList.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project = root / 'site'
            (project / 'scripts').mkdir(parents=True)
            (project / 'scripts' / 'refresh-catalog.mjs').write_text(
                "import fs from 'node:fs'; "
                "fs.mkdirSync('data',{recursive:true}); "
                "fs.writeFileSync('data/catalog.json',JSON.stringify({updated:new Date().toISOString(),groups:{trending:Array.from({length:5},(_,i)=>({id:'al-'+i,title:'Sample '+i,streaming:[]}))}}));"
            )
            subprocess.run(['git', 'init', str(project)], check=True, capture_output=True)
            subprocess.run(['git', 'config', 'user.email', 'unit@test.example'], cwd=project, check=True)
            subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=project, check=True)
            subprocess.run(['git', 'add', '.'], cwd=project, check=True)
            subprocess.run(['git', 'commit', '-m', 'base'], cwd=project, check=True, capture_output=True)
            queue = root / 'queue.json'
            queue.write_text(json.dumps({'schemaVersion':1,'tasks':[{'id':'metadata-test','kind':'catalog_refresh','timeoutSeconds':30}]}))
            state_root = root / 'state'
            self.assertEqual(ms.main(['--project',str(project),'--state-root',str(state_root),'--queue',str(queue)]),0)
            state = json.loads((state_root / 'active.json').read_text())
            self.assertEqual(state['status'],'completed')
            self.assertEqual(state['tasks']['metadata-test']['result']['afterCards'],5)
            self.assertFalse((project / 'data' / 'catalog.json').exists())
            self.assertTrue((Path(state['worktree']) / 'data' / 'catalog.json').is_file())

    def test_failed_agent_preserved_without_silent_retry(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project = root / 'site'
            project.mkdir()
            subprocess.run(['git', 'init', str(project)], check=True, capture_output=True)
            subprocess.run(['git', 'config', 'user.email', 'unit@test.example'], cwd=project, check=True)
            subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=project, check=True)
            (project / 'README.md').write_text('base\n')
            subprocess.run(['git', 'add', '.'], cwd=project, check=True)
            subprocess.run(['git', 'commit', '-m', 'base'], cwd=project, check=True, capture_output=True)
            queue = root / 'queue.json'
            queue.write_text(json.dumps({'schemaVersion':1,'tasks':[{'id':'broken-job','kind':'catalog_refresh','timeoutSeconds':30}]}))
            args = ['--project', str(project), '--state-root', str(root/'state'), '--queue', str(queue)]
            with patch.object(ms, 'execute_task', side_effect=RuntimeError('intentional failure')) as fake:
                self.assertEqual(ms.main(args), 1)
                self.assertEqual(ms.main(args + ['--resume']), 1)
                self.assertEqual(fake.call_count, 1)
            state = json.loads((root/'state'/'active.json').read_text())
            self.assertEqual(state['tasks']['broken-job']['status'], 'failed')

if __name__ == '__main__':
    unittest.main()
