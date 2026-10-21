import importlib.util
import json
import tempfile
import unittest
import threading
import http.client
from http.server import HTTPServer
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('bridge', Path(__file__).parents[1] / 'tools/hermes/local_bridge.py')
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = bridge.Store(Path(self.temp.name) / 'state')
        self.addCleanup(self.store.db.close)

    def data(self, **changes):
        return dict(engine='lmstudio', model='local-test', prompt='Analiza el reproductor', **changes)

    def test_rejects_commands_remote_engines_and_extra_fields(self):
        for changes in ({'kind': 'shell'}, {'engine': 'http://example.com'}, {'command': 'whoami'},
                        {'prompt': ''}, {'model': 3}):
            data = self.data()
            data.update(changes)
            with self.assertRaises(ValueError):
                self.store.enqueue(data)

    def test_queue_survives_restart_without_duplicate_execution(self):
        task = self.store.enqueue(self.data())
        another = bridge.Store(self.store.root)
        self.addCleanup(another.db.close)
        self.assertEqual(another.task(task)['status'], 'pending')
        with patch.object(bridge.urllib.request, 'build_opener', side_effect=TimeoutError):
            self.assertEqual(another.run_one(), task)
        self.assertIsNone(self.store.run_one())
        self.assertEqual(self.store.task(task)['status'], 'failed')
        self.assertEqual(self.store.task(task)['result'], 'TimeoutError')

    def test_memory_is_retrievable_idempotent_and_skips_unapproved_files(self):
        memory = Path(self.temp.name) / 'memory'
        memory.mkdir()
        (memory / 'project.md').write_text('Reproductor autorizado: solo fuentes verificadas.', encoding='utf-8')
        (memory / 'secret.env').write_text('do not index')
        self.assertEqual(self.store.index(memory), 1)
        self.assertEqual(self.store.index(memory), 1)
        hits = self.store.search('reproductor')
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]['source'], 'project.md')
        self.assertEqual(len(hits[0]['digest']), 64)
        self.assertEqual(self.store.search('nonexistent'), [])

    def test_real_worker_contract_uses_fixed_loopback_and_spanish(self):
        task = self.store.enqueue(self.data())
        from io import BytesIO
        response = BytesIO(json.dumps({'choices': [{'message': {'content': 'Propuesta sin ejecutar'}}]}).encode())
        with patch.object(bridge.urllib.request, 'build_opener') as factory:
            factory.return_value.open.return_value = response
            self.store.run_one()
        request = factory.return_value.open.call_args.args[0]
        self.assertEqual(request.full_url, bridge.ENGINES['lmstudio'])
        body = json.loads(request.data)
        self.assertIn('español latinoamericano', body['messages'][0]['content'])
        self.assertNotIn('tools', body)
        self.assertEqual(self.store.task(task)['result'], 'Propuesta sin ejecutar')

    def test_http_auth_origin_host_and_task_allowlist(self):
        ready = threading.Event()
        token = 'test-token-' + 'x' * 40
        holder = {}
        def serve():
            store = bridge.Store(Path(self.temp.name) / 'http-state')
            server = HTTPServer(('127.0.0.1', 0), bridge.handler(store, token))
            holder['server'] = server
            ready.set()
            try:
                server.serve_forever(poll_interval=0.01)
            finally:
                store.db.close()
                server.server_close()
        thread = threading.Thread(target=serve)
        thread.start()
        self.assertTrue(ready.wait(5))
        server = holder['server']
        def cleanup():
            server.shutdown()
            thread.join(5)
        self.addCleanup(cleanup)
        def request(method='GET', path='/health', headers=None, body=None):
            conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
            try:
                conn.request(method, path, body=body, headers=headers or {})
                response = conn.getresponse()
                return response.status, json.loads(response.read())
            finally:
                conn.close()
        auth = {'Authorization': 'Bearer ' + token}
        self.assertEqual(request()[0], 401)
        self.assertEqual(request(headers={**auth, 'Origin': 'https://evil.example'})[0], 403)
        self.assertEqual(request(headers={**auth, 'Host': 'evil.example'})[0], 403)
        self.assertEqual(request(headers=auth)[0], 200)
        headers = {**auth, 'Content-Type': 'application/json'}
        self.assertEqual(request('POST', '/shell', headers, '{}')[0], 404)
        self.assertEqual(request('POST', '/tasks', headers, '[]')[0], 400)
        self.assertEqual(request('POST', '/tasks', headers, json.dumps({**self.data(), 'kind':'shell'}))[0], 400)
        status, task = request('POST', '/tasks', headers, json.dumps(self.data()))
        self.assertEqual(status, 201)
        self.assertEqual(request(path='/tasks/' + task['id'], headers=auth)[1]['status'], 'pending')

    def test_truncated_reasoning_is_classified_and_never_completed(self):
        from io import BytesIO
        task = self.store.enqueue({**self.data(), 'max_tokens': 8192})
        response = BytesIO(json.dumps({'choices': [{'finish_reason': 'length',
            'message': {'content': '', 'reasoning_content': 'PRIVATE SECRET'}}]}).encode())
        with patch.object(bridge.urllib.request, 'build_opener') as factory:
            factory.return_value.open.return_value = response
            self.store.run_one()
        row = self.store.task(task)
        self.assertEqual(row['status'], 'failed')
        self.assertEqual(row['diagnostic'], 'output_token_limit')
        self.assertNotIn('PRIVATE', json.dumps(row))
        self.assertEqual(json.loads(factory.return_value.open.call_args.args[0].data)['max_tokens'], 8192)
        self.assertIsNone(self.store.run_one())

    def test_parser_rejects_partial_and_malformed_answers(self):
        cases = [(b'not-json SECRET', 'invalid_json'),
                 (b'{}', 'invalid_schema'), (b'{"choices": []}', 'invalid_schema'),
                 (json.dumps({'choices': [{'message': {'content': 'partial'}, 'finish_reason': 'length'}]}).encode(), 'output_token_limit'),
                 (json.dumps({'choices': [{'message': {'content': None, 'reasoning_content': 'secret'}}]}).encode(), 'reasoning_without_answer'),
                 (b'x' * 1_000_001, 'response_too_large')]
        for raw, code in cases:
            with self.subTest(code=code), self.assertRaisesRegex(bridge.ProviderFailure, '^' + code + '$'):
                bridge.parse_completion(raw)

    def test_budget_validation(self):
        for budget in (True, 0, 8193, '8192', 1.5):
            with self.assertRaises(ValueError):
                self.store.enqueue({**self.data(), 'max_tokens': budget})

    def test_migrates_legacy_queue_without_losing_tasks(self):
        import sqlite3
        root = Path(self.temp.name) / 'legacy'
        root.mkdir()
        db = sqlite3.connect(root / 'queue.sqlite3')
        db.execute('CREATE TABLE tasks(id TEXT PRIMARY KEY, engine TEXT, model TEXT, prompt TEXT, status TEXT, result TEXT, created REAL)')
        db.execute("INSERT INTO tasks VALUES('old','lmstudio','model','prompt','pending',NULL,0)")
        db.commit()
        db.close()
        migrated = bridge.Store(root)
        self.addCleanup(migrated.db.close)
        self.assertEqual(migrated.task('old')['max_tokens'], 2400)
        self.assertEqual(migrated.task('old')['status'], 'pending')

    def test_search_failure_does_not_strand_claimed_task(self):
        task = self.store.enqueue(self.data())
        with patch.object(self.store, 'search', side_effect=RuntimeError('SECRET')):
            self.store.run_one()
        self.assertEqual(self.store.task(task)['diagnostic'], 'worker_error')
        self.assertEqual(self.store.task(task)['status'], 'failed')


if __name__ == '__main__':
    unittest.main()
