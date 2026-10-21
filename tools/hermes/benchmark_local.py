"""Finite sequential benchmark, synthetic prompts only, existing LM Studio model."""
import argparse
import json
from pathlib import Path
import statistics
import time
try:
    from .local_bridge import ENGINES, SYSTEM, local_opener, parse_completion, probe_providers
except ImportError:
    from local_bridge import ENGINES, SYSTEM, local_opener, parse_completion, probe_providers
import urllib.request

CASES = (
    ('short', 'Responde solamente: listo.', 512),
    ('engineering', 'Propón en menos de 200 palabras tres pruebas para una cola SQLite durable con dependencias, '
     'una GPU y recuperación tras caída. Distingue resultado final de inferencia y aprobación de cambios.', 8192),
)


def run(model, repeats=3):
    if type(repeats) is not int or not 1 <= repeats <= 3:
        raise ValueError('repeats must be 1..3')
    observed = probe_providers()
    if model not in observed['providers']['lmstudio'].get('models', []):
        raise ValueError('Requested model not advertised; no automatic download')
    rows = []
    for name, prompt, budget in CASES:
        for sample in range(repeats):
            request = urllib.request.Request(ENGINES['lmstudio'], data=json.dumps({
                'model': model, 'messages': [{'role': 'system', 'content': SYSTEM},
                    {'role': 'user', 'content': prompt}], 'temperature': 0.2,
                'max_tokens': budget, 'stream': False}).encode(), headers={'Content-Type': 'application/json'})
            started = time.monotonic()
            row = {'case': name, 'sample': sample + 1, 'max_tokens': budget}
            try:
                with local_opener().open(request, timeout=180) as response:
                    raw = response.read(1_000_001)
                answer = parse_completion(raw)
                payload = json.loads(raw)
                usage = payload.get('usage', {})
                row.update(status='completed', answer_chars=len(answer))
                for key in ('prompt_tokens', 'completion_tokens', 'total_tokens'):
                    value = usage.get(key)
                    if type(value) is int and value >= 0:
                        row[key] = value
            except Exception as exc:
                row.update(status='failed', error_type=type(exc).__name__)
            row['seconds'] = round(time.monotonic() - started, 3)
            if row.get('completion_tokens'):
                row['completion_tokens_per_wall_second'] = round(row['completion_tokens'] / row['seconds'], 2)
            rows.append(row)
    summary = {}
    for name, _, _ in CASES:
        samples = [r for r in rows if r['case'] == name]
        summary[name] = {'samples': len(samples), 'completed': sum(r['status'] == 'completed' for r in samples),
                         'median_seconds': statistics.median(r['seconds'] for r in samples),
                         'max_seconds': max(r['seconds'] for r in samples)}
    return {'model': model, 'concurrency': 1, 'observed_providers': observed,
            'samples': rows, 'summary': summary,
            'limitations': 'Small sequential warm-model sample. No p95, speedup, decode-only throughput or reliability estimate.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', required=True)
    parser.add_argument('--repeats', type=int, choices=range(1, 4), default=3)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = run(args.model, args.repeats)
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report['summary']))
