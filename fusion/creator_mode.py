"""Modo Creador: propuestas conservadoras de tomas repetidas desde subtítulos.

No usa IA remota ni supone que una repetición es necesariamente un error.
La fuente se mantiene intacta; solamente modifica el timeline editable
cuando el usuario aprueba explícitamente la acción.
"""
from __future__ import annotations

from difflib import SequenceMatcher
from pathlib import Path
import re
import unicodedata

from .engine import read_srt
from .project import read_json, safe_write


def _tokens(value):
    plain = unicodedata.normalize('NFKD', str(value).casefold())
    plain = ''.join(x for x in plain if not unicodedata.combining(x))
    return re.findall(r'[a-z0-9]+', plain)


def suggest_repeated_takes(captions, *, max_gap=3.0, min_words=5, similarity=.90):
    """Detecta pares de frases adyacentes casi idénticas y propone quitar la primera.

    Es conservador: no detecta errores semánticos ni tartamudeos dentro
    de una misma frase. El usuario siempre debe revisar las sugerencias.
    """
    if not 0 <= max_gap <= 30 or not 3 <= min_words <= 30 or not .5 <= similarity <= 1:
        raise ValueError('Parámetros de detección inválidos')
    rows = sorted((dict(row) for row in captions), key=lambda r: float(r['start']))
    results = []
    for earlier, later in zip(rows, rows[1:]):
        a, b = float(earlier['start']), float(earlier['end'])
        c, d = float(later['start']), float(later['end'])
        if not (0 <= a < b <= c < d) or c-b > max_gap:
            continue
        first, second = _tokens(earlier['text']), _tokens(later['text'])
        if (min(len(first), len(second)) < min_words
                or min(len(set(first)), len(set(second))) < 3):
            continue
        ratio = SequenceMatcher(None, first, second, autojunk=False).ratio()
        if ratio < similarity:
            continue
        results.append({
            'start': round(a, 3), 'end': round(b, 3),
            'original_text': earlier['text'].strip(),
            'replacement_text': later['text'].strip(),
            'similarity': round(ratio, 3),
            'reason': 'Frases consecutivas similares; posible toma repetida',
            'review_required': True,
        })
    return results


def analyze_retakes(project_folder, *, overwrite=False):
    """Genera propuestas sin efectuar cortes ni cambiar el video."""
    root = Path(project_folder).expanduser().resolve()
    project = read_json(root/'project.json')
    transcript = project.get('subtitle_file')
    if not transcript or not Path(transcript).is_file():
        raise FileNotFoundError('Importa un SRT o transcribe con Whisper local antes de analizar repeticiones.')
    target = root/'retakes-report.json'
    if target.exists() and not overwrite:
        raise FileExistsError('El informe ya existe. Pasa --overwrite para regenerarlo.')
    suggestions = suggest_repeated_takes(read_srt(transcript))
    report = {
        'schema': 1, 'method': 'conservative_transcript_similarity',
        'subtitle_file': str(Path(transcript).resolve()),
        'source': project.get('source'),
        'suggestions': suggestions,
        'review_required': True,
        'warning': 'Las repeticiones pueden ser intencionales. Revisa el audio y cada corte antes de publicar.',
    }
    safe_write(target, report)
    return report


def apply_reviewed_retakes(project_folder, *, suggestion_indices, overwrite=False):
    """Aplica solo propuestas seleccionadas a timeline-v2.json; nunca toca el original."""
    root = Path(project_folder).expanduser().resolve()
    timeline_path = root/'timeline-v2.json'
    report = read_json(root/'retakes-report.json')
    timeline = read_json(timeline_path)
    if not report or not timeline:
        raise FileNotFoundError('Primero crea el timeline y ejecuta el análisis de repeticiones.')
    if not suggestion_indices:
        raise ValueError('Selecciona los índices de las sugerencias que revisaste.')
    if not overwrite:
        raise ValueError('La aplicación requiere --overwrite para confirmar la actualización del timeline.')
    if report.get('source') != timeline.get('source'):
        raise ValueError('El informe no corresponde al video del timeline.')
    suggestions = report.get('suggestions', [])
    indices = sorted(set(suggestion_indices))
    if any(not isinstance(i, int) or i < 0 or i >= len(suggestions) for i in indices):
        raise ValueError('Índice de sugerencia inválido')
    cuts = sorted((float(suggestions[i]['start']), float(suggestions[i]['end'])) for i in indices)
    if any(cuts[i][0] < cuts[i-1][1] for i in range(1, len(cuts))):
        raise ValueError('Las sugerencias se solapan.')
    new_clips = []
    for old in timeline['clips']:
        intervals = [(float(old['start']), float(old['end']))]
        for left, right in cuts:
            next_intervals = []
            for a, b in intervals:
                if right <= a or left >= b:
                    next_intervals.append((a, b))
                else:
                    if left-a >= .35:
                        next_intervals.append((a, left))
                    if b-right >= .35:
                        next_intervals.append((right, b))
            intervals = next_intervals
        for a, b in intervals:
            clip = dict(old)
            clip.update(start=round(a, 3), end=round(b, 3))
            new_clips.append(clip)
    if not new_clips or len(new_clips) > 100:
        raise ValueError('Los recortes dejarían un timeline vacío o demasiado fragmentado.')
    for i, clip in enumerate(new_clips, 1):
        clip['id'] = i
    tl = dict(timeline)
    tl['clips'] = new_clips
    if tl.get('cut_style') == 'crossfade':
        if any(x['end']-x['start'] < 2*float(tl.get('transition_seconds', .25)) for x in new_clips):
            tl['cut_style'] = 'hard'
    tl.setdefault('notes', []).append(
        'Cortes revisados de Modo Creador; confirma que no sean repeticiones intencionales.'
    )
    from .phase2 import validate_timeline
    validate_timeline(tl)
    safe_write(timeline_path, tl)
    return {'clips': len(new_clips), 'applied_indices': indices,
            'review_required': True, 'timeline': str(timeline_path)}
