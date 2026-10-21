import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from tools.hermes import local_bridge as b


class DurablePlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = b.Store(Path(self.temp.name))
        self.addCleanup(self.store.db.close)
        self.spec = {'tasks': [
            {'id': 'review', 'role': 'reviewer', 'prompt': 'Review', 'depends_on': ['draft']},
            {'id': 'draft', 'role': 'backend', 'prompt': 'Propose', 'depends_on': []}]}

    def enqueue(self, spec=None):
        return self.store.enqueue_plan('demo', spec or self.spec, 'lmstudio', 'test')

    def test_idempotent_durable_dag_and_dependency_context(self):
        rows = self.enqueue()
        self.assertEqual(self.enqueue(), rows)
        other = b.Store(Path(self.temp.name))
        self.addCleanup(other.db.close)
        by_key = {r['task_key']: r['id'] for r in rows}
        for expected in ('draft', 'review'):
            response = BytesIO(json.dumps({'choices': [{'message': {'content': 'reviewable proposal'}, 'finish_reason': 'stop'}]}).encode())
            with patch.object(b, 'local_opener') as opener:
                opener.return_value.open.return_value = response
                self.assertEqual(other.run_one(), by_key[expected])
                if expected == 'review':
                    self.assertIn('reviewable proposal', opener.return_value.open.call_args.args[0].data.decode())
        self.assertIsNone(other.run_one())

    def test_failure_blocks_dependents_without_retry(self):
        self.enqueue()
        with patch.object(b, 'local_opener', side_effect=TimeoutError):
            self.store.run_one()
        self.assertIsNone(self.store.run_one())
        self.assertEqual([r['status'] for r in self.store.plan_status('demo')], ['failed', 'pending'])

    def test_running_task_holds_single_gpu_slot_after_restart(self):
        self.enqueue()
        with self.store.db:
            self.store.db.execute("UPDATE tasks SET status='running' WHERE prompt='Propose'")
        other = b.Store(Path(self.temp.name))
        self.addCleanup(other.db.close)
        self.assertIsNone(other.run_one())

    def test_conflicting_plan_and_cycle_do_not_mutate_queue(self):
        self.enqueue()
        changed = json.loads(json.dumps(self.spec))
        changed['tasks'][0]['prompt'] = 'different'
        with self.assertRaises(ValueError):
            self.enqueue(changed)
        cyclic = json.loads(json.dumps(self.spec))
        cyclic['tasks'][1]['depends_on'] = ['review']
        with self.assertRaises(ValueError):
            self.store.enqueue_plan('cycle', cyclic, 'lmstudio', 'test')
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM tasks').fetchone()[0], 2)

    def test_probe_never_claims_cloud_access(self):
        with patch.object(b, 'local_opener', side_effect=OSError('private secret')):
            report = b.probe_providers()
        self.assertEqual(report['chatgpt'], 'unverified_no_adapter')
        self.assertNotIn('secret', json.dumps(report))
        self.assertEqual(report['providers']['lmstudio']['status'], 'unavailable_or_invalid')

    def test_abandon_requires_operator_and_preserves_event_checkpoint(self):
        rows = self.enqueue()
        ident = rows[0]['id']
        with self.store.db:
            self.store.db.execute("UPDATE tasks SET status='running' WHERE id=?", (ident,))
        with self.assertRaises(ValueError):
            self.store.abandon(ident)
        self.store.abandon(ident, worker_stopped=True)
        self.assertEqual(self.store.task(ident)['diagnostic'], 'operator_abandoned')
        self.assertEqual([r[0] for r in self.store.db.execute('SELECT event FROM events WHERE task_id=? ORDER BY sequence', (ident,))], ['queued', 'operator_abandoned'])
        with self.assertRaises(ValueError):
            self.store.abandon(ident, worker_stopped=True)
