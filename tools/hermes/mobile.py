"""HERMES Mobile: finite OpenCode host and recoverable tasks; Linux only.

No cloud resources, billing changes or paid API credentials are created here.
All private state is outside the git repository. Permissions are not an OS sandbox.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import signal
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, ProxyHandler, build_opener

HERE = Path(__file__).resolve().parent
ASSETS = HERE / 'mobile'
VERSION = '1.19.4'
CPU = 'hermes-cpu/qwen2.5-coder-1.5b'
FREE = ('glm-5.3-flash-free', 'big-pickle', 'mimo-v2.6-flash-free')
HTTP = build_opener(ProxyHandler({}))
ID = re.compile(r'[a-zA-Z0-9][a-zA-Z0-9._-]{0,79}\Z')
MAX_LOG = 8 * 1024 * 1024

class MobileError(RuntimeError):
    pass

def save(path: Path, value: dict):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink():
        raise MobileError('Estado privado no puede ser un enlace')
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.hermes-')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(value, f, indent=2, ensure_ascii=False, allow_nan=False)
            f.write('\n'); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def read(path: Path) -> dict:
    value = json.loads(path.read_text())
    if not isinstance(value, dict): raise MobileError('Estado JSON inválido')
    return value

def git(root: Path, *args) -> str:
    p = subprocess.run(['git', *args], cwd=root, capture_output=True, text=True, timeout=20)
    if p.returncode: raise MobileError('Git falló: ' + ' '.join(args[:2]))
    return p.stdout.strip()

def workspace(root: Path, execute=False) -> dict:
    if Path(git(root, 'rev-parse', '--show-toplevel')).resolve() != root.resolve():
        raise MobileError('Usa la raíz del repositorio')
    branch = git(root, 'symbolic-ref', '--short', 'HEAD')
    if execute and branch in {'main', 'master'}:
        raise MobileError('No se ejecutan agentes en main/master')
    return {'branch': branch, 'head': git(root, 'rev-parse', 'HEAD')}

def state_dir(root: Path, override=None) -> Path:
    digest = hashlib.sha256(str(root.resolve()).encode()).hexdigest()[:16]
    dest = Path(override or root.parent / '.hermes-mobile' / digest).expanduser()
    if dest.is_symlink(): raise MobileError('Estado privado no puede ser un enlace')
    dest = dest.resolve()
    if dest == root.resolve() or root.resolve() in dest.parents:
        raise MobileError('Guarda el estado privado fuera del repositorio')
    dest.mkdir(parents=True, exist_ok=True, mode=0o700); dest.chmod(0o700)
    return dest

@contextmanager
def lock(store: Path, name: str):
    path = store / (name + '.lock')
    if path.is_symlink(): raise MobileError('Bloqueo inválido')
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try: fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc: raise MobileError('Otra ejecución mantiene el bloqueo') from exc
        yield
    finally: os.close(fd)

def credentials(store: Path) -> dict:
    with lock(store, 'auth'):
        path = store / 'auth.json'
        if not path.exists():
            save(path, {'username': 'opencode', 'password': secrets.token_urlsafe(32),
                        'cpu_key': secrets.token_urlsafe(32)})
        if path.is_symlink() or path.stat().st_mode & 0o077:
            raise MobileError('auth.json requiere permisos 600')
        value = read(path)
        if len(value.get('password', '')) < 32 or len(value.get('cpu_key', '')) < 32:
            raise MobileError('Credencial inválida')
        return value

def binary():
    path = ASSETS / 'node_modules' / '.bin' / 'opencode'
    if not path.exists(): raise MobileError('Ejecuta bash .devcontainer/setup-hermes.sh')
    p = subprocess.run([str(path), '--version'], capture_output=True, text=True, timeout=15)
    if p.returncode or p.stdout.strip() != VERSION: raise MobileError('Versión OpenCode sin verificar')
    return str(path)

def config(store: Path, model=CPU, goal=False):
    if model == CPU:
        providers = {'hermes-cpu': {'npm': '@ai-sdk/openai-compatible', 'name': 'HERMES CPU',
            'options': {'baseURL': 'http://127.0.0.1:8081/v1', 'apiKey': credentials(store)['cpu_key']},
            'models': {'qwen2.5-coder-1.5b': {'name': 'Qwen2.5 Coder 1.5B CPU',
                'limit': {'context': 16384, 'output': 2048}, 'cost': {'input': 0, 'output': 0}, 'tool_call': True}}}}
    elif model in ['opencode/' + m for m in FREE]:
        providers = {'opencode': {'whitelist': list(FREE)}}
    else: raise MobileError('Solo se permiten modelos CPU o gratuitos; Claude permanece desactivado')
    value = {'$schema': 'https://opencode.ai/config.json', 'model': model, 'small_model': model,
        'enabled_providers': list(providers), 'disabled_providers': ['anthropic', 'openai', 'opencode-go'],
        'provider': providers, 'share': 'disabled', 'autoupdate': False, 'default_agent': 'hermes',
        'permission': {'*': 'ask', 'read': {'*': 'allow', '*.env*': 'deny', '**/.env*': 'deny',
            '.git/**': 'deny', '**/*.pem': 'deny', '**/*credentials*': 'deny', str(store) + '/**': 'deny'},
            'edit': {'*': 'allow', '.git/**': 'deny', '*.env*': 'deny', '**/.env*': 'deny',
                     '.github/**': 'ask', '.devcontainer/**': 'ask'},
            'external_directory': 'deny', 'task': 'deny', 'bash': 'ask', 'webfetch': 'deny', 'websearch': 'deny'},
        'agent': {'hermes': {'description': 'Programador acotado de HERMES', 'mode': 'primary',
            'model': model, 'steps': 8, 'prompt': 'Responde en español. Lee AGENTS.md cuando corresponda. '
                'Trabaja en la rama actual. No leas secretos ni hagas push/merge. Verifica los cambios.'}}}
    if goal: value['plugin'] = [str(ASSETS / 'goal.ts')]
    return value

def agent_env(store, settings):
    allowed = {'PATH', 'HOME', 'LANG', 'LC_ALL', 'TERM', 'TZ', 'USER', 'LOGNAME', 'HTTP_PROXY',
        'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY', 'http_proxy', 'https_proxy', 'all_proxy', 'no_proxy',
        'SSL_CERT_FILE', 'SSL_CERT_DIR', 'NODE_EXTRA_CA_CERTS'}
    env = {k: v for k, v in os.environ.items() if k in allowed}
    for key, folder in [('XDG_CONFIG_HOME', 'config'), ('XDG_DATA_HOME', 'data'),
                        ('XDG_CACHE_HOME', 'cache'), ('XDG_STATE_HOME', 'state')]:
        (store / folder).mkdir(mode=0o700, exist_ok=True); env[key] = str(store / folder)
    env.update(OPENCODE_CONFIG_CONTENT=json.dumps(settings), OPENCODE_DISABLE_PROJECT_CONFIG='1',
               OPENCODE_DISABLE_AUTOUPDATE='1')
    return env

def request(port, path, auth=None, *, method='GET', body=None, timeout=10):
    headers = {'Content-Type': 'application/json'}
    if auth:
        headers['Authorization'] = 'Basic ' + base64.b64encode((auth['username'] + ':' + auth['password']).encode()).decode()
    req = Request(f'http://127.0.0.1:{port}{path}', headers=headers, method=method,
                  data=json.dumps(body).encode() if body is not None else None)
    try:
        with HTTP.open(req, timeout=timeout) as reply:
            raw = reply.read(4 * 1024 * 1024)
            return reply.status, json.loads(raw) if raw else None
    except HTTPError as exc: return exc.code, None

def probe(store, port):
    auth = credentials(store)
    anonymous, _ = request(port, '/path')
    incorrect, _ = request(port, '/path', {'username': 'opencode', 'password': 'incorrect'})
    code, health = request(port, '/global/health', auth)
    if anonymous != 401 or incorrect != 401 or code != 200 or not isinstance(health, dict) or health.get('healthy') is not True:
        raise MobileError('Falló autenticación o salud')
    if health.get('version') != VERSION: raise MobileError('Versión del servidor incorrecta')
    code, catalog = request(port, '/config/providers', auth, timeout=30)
    if code != 200: raise MobileError('Catálogo no disponible')
    models = []
    for provider in catalog.get('providers', []):
        for name, model in provider.get('models', {}).items():
            ident = provider['id'] + '/' + name
            if ident not in [CPU, *['opencode/' + m for m in FREE]]:
                raise MobileError('Proveedor o modelo fuera de la lista gratuita')
            if model.get('cost', {}).get('input') != 0 or model.get('cost', {}).get('output') != 0:
                raise MobileError('Modelo facturable detectado')
            models.append(ident)
    if not models: raise MobileError('No hay modelos gratuitos disponibles')
    return {'healthy': True, 'version': VERSION, 'anonymous_http': anonymous,
            'incorrect_auth_http': incorrect, 'models': models, 'paid_api_enabled': False}

def terminate(proc):
    if proc.poll() is not None: return
    os.killpg(proc.pid, signal.SIGTERM)
    try: proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL); proc.wait(timeout=3)

def status(store):
    value = read(store / 'host.json') if (store / 'host.json').exists() else {'status': 'not_started'}
    if value['status'] == 'running' and time.time() - value.get('heartbeat', 0) > 4:
        value['status'] = 'interrupted'
    return value

def supervise(root, store, model, seconds, goal=False, port=4096):
    if not 5 <= seconds <= 3600: raise MobileError('Límite de host: 5–3600 segundos')
    workspace(root, True)
    with lock(store, 'host'):
        auth = credentials(store); settings = config(store, model, goal)
        env = agent_env(store, settings); env['OPENCODE_SERVER_PASSWORD'] = auth['password']
        children = []; reason = 'process_exit'; stop_requested = False
        def interrupt(*_):
            nonlocal stop_requested
            stop_requested = True
        signal.signal(signal.SIGTERM, interrupt); signal.signal(signal.SIGINT, interrupt)
        try:
            if model == CPU:
                from mobile_cpu import server_command
                with (store / 'cpu.log').open('ab', buffering=0) as log:
                    cpu = subprocess.Popen(server_command(store, auth['cpu_key']), env=agent_env(store, settings),
                        stdout=log, stderr=log, start_new_session=True)
                children.append(cpu)
                for _ in range(120):
                    if cpu.poll() is not None or stop_requested: raise MobileError('Modelo CPU no arrancó')
                    try:
                        if request(8081, '/health')[0] == 200: break
                    except (OSError, URLError): pass
                    time.sleep(.5)
                else: raise MobileError('Arranque CPU agotado')
            command = [binary(), 'serve', '--hostname', '127.0.0.1', '--port', str(port)]
            if not goal: command.append('--pure')
            with (store / 'server.log').open('ab', buffering=0) as log:
                server = subprocess.Popen(command, cwd=root, env=env, stdout=log, stderr=log, start_new_session=True)
            children.append(server); checked = None
            for _ in range(100):
                if server.poll() is not None or stop_requested: raise MobileError('OpenCode no arrancó')
                try: checked = probe(store, port); break
                except (OSError, URLError): time.sleep(.25)
            if checked is None: raise MobileError('Arranque OpenCode agotado')
            start = time.monotonic()
            value = {'status': 'running', 'instance': secrets.token_hex(16), 'model': model, 'goal': goal,
                'port': port, 'max_seconds': seconds, 'started_at': time.time(), 'probe': checked}
            while not stop_requested and time.monotonic() - start < seconds:
                if (store / 'stop.json').exists() and read(store / 'stop.json').get('instance') == value['instance']:
                    reason = 'user_stop'; break
                if any(p.poll() is not None for p in children): break
                if any(p.exists() and p.stat().st_size > MAX_LOG for p in [store / 'server.log', store / 'cpu.log']):
                    reason = 'log_limit'; break
                value['heartbeat'] = time.time(); save(store / 'host.json', value); time.sleep(.5)
            else: reason = 'user_stop' if stop_requested else 'wall_time_limit'
        finally:
            for child in reversed(children): terminate(child)
            save(store / 'host.json', {'status': 'stopped', 'reason': reason, 'stopped_at': time.time()})
            # Best effort only; stopping this server does not stop Codespace storage usage.
            if os.environ.get('CODESPACE_NAME'):
                try:
                    p = subprocess.run(['gh', 'codespace', 'stop', '-c', os.environ['CODESPACE_NAME']], capture_output=True, timeout=20)
                    save(store / 'codespace-stop.json', {'attempted': True, 'exit_code': p.returncode})
                except (OSError, subprocess.SubprocessError):
                    save(store / 'codespace-stop.json', {'attempted': True, 'failed': True})

def start(root, store, model=CPU, seconds=2700, goal=False):
    workspace(root, True); config(store, model, goal); binary()
    if not 5 <= seconds <= 3600: raise MobileError('Límite de host inválido')
    if status(store)['status'] == 'running': raise MobileError('Host ya iniciado')
    command = [sys.executable, str(Path(__file__).resolve()), '--root', str(root), '--state-dir', str(store),
               '_serve', '--model', model, '--max-seconds', str(seconds)]
    if goal: command.append('--goal')
    with (store / 'supervisor.log').open('ab', buffering=0) as log:
        proc = subprocess.Popen(command, cwd=root, stdout=log, stderr=log, start_new_session=True)
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        value = status(store)
        if value['status'] == 'running': return value
        if proc.poll() is not None: raise MobileError('Host falló; revisa supervisor.log privado')
        time.sleep(.25)
    terminate(proc); raise MobileError('Arranque agotado')

def stop(store):
    value = status(store)
    if value['status'] != 'running': return {'stopped': True, 'previous': value['status']}
    save(store / 'stop.json', {'instance': value['instance']})
    for _ in range(100):
        if status(store)['status'] != 'running': return {'stopped': True}
        time.sleep(.1)
    raise MobileError('Host no respondió; revisar antes de reiniciar')

def bounded(command, root, env, logfile, seconds):
    logfile.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    with logfile.open('wb', buffering=0) as log:
        proc = subprocess.Popen(command, cwd=root, env=env, stdout=log, stderr=log, start_new_session=True)
        deadline = time.monotonic() + seconds; reason = 'exit'
        try:
            while proc.poll() is None:
                if time.monotonic() >= deadline: reason = 'timeout'; break
                if logfile.stat().st_size > MAX_LOG: reason = 'log_limit'; break
                time.sleep(.1)
        finally: terminate(proc)
    return {'exit_code': proc.returncode, 'reason': reason, 'sha256': hashlib.sha256(logfile.read_bytes()).hexdigest()}

def taskfile(store, ident):
    if not ID.fullmatch(ident) or ident in {'.', '..'}: raise MobileError('ID inválido')
    return store / 'tasks' / (ident + '.json')

def digest(root):
    value = hashlib.sha256(git(root, 'diff', 'HEAD', '--binary').encode())
    for name in git(root, 'ls-files', '--others', '--exclude-standard').splitlines():
        path = root / name; value.update(name.encode())
        if path.is_file() and not path.is_symlink(): value.update(path.read_bytes())
    return value.hexdigest()

def task(root, store, ident, prompt, tests, seconds=240, resume=False):
    snap = workspace(root, True); dest = taskfile(store, ident)
    if not 5 <= seconds <= 300 or not prompt.strip() or len(prompt) > 14000: raise MobileError('Límite de tarea o prompt inválido')
    if not tests or tests[0] not in {'python3', 'python', 'node', 'npm'}: raise MobileError('Indica pruebas Python/Node/npm explícitas')
    host = status(store)
    if host['status'] != 'running': raise MobileError('Inicia el host')
    with lock(store, 'task'):
        checked = probe(store, host['port']); auth = credentials(store)
        if host['model'] not in checked['models']: raise MobileError('Modelo no disponible')
        if resume:
            value = read(dest)
            if value['source'] != snap or value['attempts'] >= 2 or value['status'] == 'verified':
                raise MobileError('Revisar rama/HEAD o límite de dos intentos antes de recuperar')
        else:
            if dest.exists() or git(root, 'status', '--porcelain'): raise MobileError('Tarea existente o árbol git sucio')
            code, session = request(host['port'], '/session', auth, method='POST', body={'title': 'HERMES ' + ident})
            if code != 200: raise MobileError('No se pudo crear sesión')
            value = {'id': ident, 'source': snap, 'session': session['id'], 'attempts': 0, 'initial_diff': digest(root)}
        value.update(status='running', attempts=value['attempts'] + 1, next_action='Revisar registro y recuperar explícitamente')
        save(dest, value)
        env = agent_env(store, config(store, host['model'], host.get('goal', False)))
        env['OPENCODE_SERVER_PASSWORD'] = auth['password']
        logfile = dest.with_suffix('.jsonl')
        try:
            run = bounded([binary(), 'run', '--pure', '--attach', f"http://127.0.0.1:{host['port']}",
                '--session', value['session'], '--format', 'json', '--agent', 'hermes', '--model', host['model'], prompt],
                root, env, logfile, seconds)
        except BaseException:
            value['status'] = 'interrupted'; save(dest, value); raise
        finally:
            try: request(host['port'], '/session/' + value['session'] + '/abort', auth, method='POST')
            except (OSError, URLError): pass
        errors = False
        for line in logfile.read_text(errors='replace').splitlines():
            try: errors |= json.loads(line).get('type') == 'error'
            except (ValueError, AttributeError): pass
        test = {'result': 'not_run'}
        if run['exit_code'] == 0 and run['reason'] == 'exit' and not errors and workspace(root) == snap:
            test = bounded(tests, root, agent_env(store, config(store, host['model'])), dest.with_suffix('.tests.log'), 120)
            test['result'] = 'passed' if test['exit_code'] == 0 and test['reason'] == 'exit' else 'failed'
        changed = digest(root) != value['initial_diff']
        verified = changed and test['result'] == 'passed' and workspace(root) == snap
        value.update(status='verified' if verified else 'blocked', run=run, tests=test, changed=changed,
            candidate_diff=digest(root), next_action='Revisar diff y crear PR' if verified else 'Corregir bloqueo antes de --resume')
        save(dest, value)
        return {k: value[k] for k in ['id', 'status', 'attempts', 'run', 'tests', 'changed', 'next_action']}

def main(argv=None):
    os.umask(0o077)
    parser = argparse.ArgumentParser(description='HERMES Mobile: OpenCode sin APIs de pago')
    parser.add_argument('--root', type=Path, default=Path.cwd()); parser.add_argument('--state-dir', type=Path)
    sub = parser.add_subparsers(dest='action', required=True)
    for name in ['doctor', 'status', 'stop', 'probe', 'credentials', 'install-cpu', 'tui']: sub.add_parser(name)
    for name in ['start', '_serve']:
        p = sub.add_parser(name); p.add_argument('--model', default=CPU); p.add_argument('--max-seconds', type=int, default=2700)
        p.add_argument('--goal', action='store_true')
    p = sub.add_parser('task'); p.add_argument('--id', required=True); p.add_argument('--prompt-file', required=True, type=Path)
    p.add_argument('--max-seconds', type=int, default=240); p.add_argument('--resume', action='store_true')
    p.add_argument('--test', nargs=argparse.REMAINDER, required=True)
    p = sub.add_parser('recover'); p.add_argument('--id', required=True)
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve(strict=True); store = state_dir(root, args.state_dir)
        if args.action == 'doctor': result = {'workspace': workspace(root), 'opencode': binary(), 'version': VERSION,
            'codespace': bool(os.environ.get('CODESPACE_NAME')), 'quota_verified': False, 'paid_api_enabled': False}
        elif args.action == 'start': result = start(root, store, args.model, args.max_seconds, args.goal)
        elif args.action == '_serve': supervise(root, store, args.model, args.max_seconds, args.goal); return 0
        elif args.action == 'stop': result = stop(store)
        elif args.action == 'status': result = status(store)
        elif args.action == 'probe': result = probe(store, status(store).get('port', 4096))
        elif args.action == 'credentials':
            if not sys.stdout.isatty(): raise MobileError('Credenciales solo en tu terminal interactiva; nunca en logs')
            result = {k: v for k, v in credentials(store).items() if k != 'cpu_key'}
        elif args.action == 'install-cpu':
            from mobile_cpu import install
            result = install(store)
        elif args.action == 'tui':
            host = status(store)
            if host['status'] != 'running': raise MobileError('Inicia el host')
            env = agent_env(store, config(store, host['model'], host.get('goal', False)))
            env['OPENCODE_SERVER_PASSWORD'] = credentials(store)['password']
            return subprocess.call([binary(), 'attach', f"http://127.0.0.1:{host['port']}"], cwd=root, env=env)
        elif args.action == 'recover':
            value = read(taskfile(store, args.id)); result = {k: value[k] for k in ['id', 'status', 'attempts', 'next_action']}
            result['source_changed'] = value['source'] != workspace(root)
        else: result = task(root, store, args.id, args.prompt_file.read_text(), args.test, args.max_seconds, args.resume)
        print(json.dumps(result, indent=2, ensure_ascii=False)); return 2 if result.get('status') == 'blocked' else 0
    except (MobileError, OSError, ValueError, URLError, subprocess.SubprocessError) as exc:
        print('HERMES Mobile: ' + str(exc), file=sys.stderr); return 2

if __name__ == '__main__': raise SystemExit(main())
