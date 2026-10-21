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
        self.assertEqual(request(path='/tasks')[0], 401)
        overview = request(path='/tasks', headers=auth)[1]
        self.assertEqual(overview['counts']['pending'], 1)
        self.assertNotIn('prompt', overview['recent'][0])
        cancel_path = '/tasks/' + task['id'] + '/cancel'
        self.assertEqual(request('POST', cancel_path, headers, '{"force":true}')[0], 400)
        self.assertEqual(request('POST', cancel_path, {}, '{}')[0], 401)
        self.assertEqual(request('POST', cancel_path, headers, '{}')[1]['status'], 'cancelled')
        self.assertEqual(request('POST', cancel_path, headers, '{}')[0], 409)
        self.assertEqual(request('POST', '/tasks/' + '0'*32 + '/cancel', headers, '{}')[0], 404)

    def test_cancel_preserves_record_skips_worker_and_never_interrupts_running(self):
        task = self.store.enqueue(self.data())
        self.assertTrue(self.store.cancel_pending(task))
        self.assertEqual(self.store.task(task)['prompt'], self.data()['prompt'])
        with patch.object(bridge.urllib.request, 'build_opener') as factory:
            self.assertIsNone(self.store.run_one())
        factory.assert_not_called()
        running = self.store.enqueue(self.data())
        with self.store.db:
            self.store.db.execute("UPDATE tasks SET status='running' WHERE id=?", (running,))
        self.assertFalse(self.store.cancel_pending(running))
        self.assertEqual(self.store.task(running)['status'], 'running')
        self.assertFalse(self.store.cancel_pending("'; DROP TABLE tasks; --"))

    def test_overview_is_bounded_and_excludes_private_contents(self):
        for _ in range(55):
            self.store.enqueue(self.data())
        overview = self.store.status()
        self.assertEqual(overview['counts']['pending'], 55)
        self.assertEqual(len(overview['recent']), 50)
        self.assertNotIn('Analiza el reproductor', json.dumps(overview))
        self.assertEqual(set(overview['recent'][0]), {'id','engine','model','status','created'})


if __name__ == '__main__':
    unittest.main()
