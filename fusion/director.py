"""Local original motion-title and reference-cut director; no remote AI required."""
from __future__ import annotations
from pathlib import Path
import re
import tempfile
from .media import probe, required, run, scene_changes
from .project import read_json, safe_write

PALETTES = {
    'green': ('0x061710', '0x37FF9B'),
    'red': ('0x1B070B', '0xFF355B'),
    'blue': ('0x071326', '0x41BAFF'),
    'purple': ('0x17091F', '0xCA72FF'),
    'gold': ('0x201504', '0xF7C35E'),
}


def parse_prompt(prompt: str, *, title: str | None = None,
                 seconds: float | None = None, platform: str | None = None) -> dict:
    """Parse safe supported motion parameters, not arbitrary render instructions."""
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 2000:
        raise ValueError('Escribe una instrucción de 1 a 2000 caracteres.')
    low = prompt.casefold()
    if not title:
        match = re.search(r'[«“"\x27]([^»”"\x27]{1,90})[»”"\x27]', prompt)
        title = match.group(1).strip() if match else 'DEXTER FF'
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 90 or any(c in title for c in '\r\n\x00'):
        raise ValueError('El título debe tener entre 1 y 90 caracteres, en una sola línea.')
    if seconds is None:
        match = re.search(r'\b(\d+(?:[.,]\d+)?)\s*(?:segundos?|secs?|seconds?)\b', low)
        seconds = float(match.group(1).replace(',', '.')) if match else 4.0
    seconds = float(seconds)
    if not 1.0 <= seconds <= 15.0:
        raise ValueError('La duración debe estar entre 1 y 15 segundos.')
    if platform is None:
        platform = 'youtube' if ('horizontal' in low or '16:9' in low or 'youtube largo' in low) else 'shorts'
    if platform not in ('youtube', 'shorts', 'tiktok'):
        raise ValueError('Formato inválido. Usa youtube, shorts o tiktok.')
    color = 'green'
    for name, words in (
        ('red', ('rojo', 'roja', 'red')),
        ('blue', ('azul', 'blue')),
        ('purple', ('morado', 'violeta', 'purple')),
        ('gold', ('dorado', 'oro', 'gold')),
        ('green', ('verde', 'green')),
    ):
        if any(re.search(r'(?<!\w)' + re.escape(w) + r'(?!\w)', low) for w in words):
            color = name
            break
    style = 'cinematic' if 'cinem' in low or 'película' in low else 'neon'
    if 'retro' in low or 'vhs' in low:
        style = 'retro'
    return {
        'version': 1, 'prompt': prompt.strip(), 'title': title.strip(),
        'duration': round(seconds, 2), 'platform': platform,
        'style': style, 'palette': color, 'review_required': True,
        'capabilities': ['kinetic title', 'fade', 'neon outline', 'native h264 render'],
        'limitations': 'Plantilla procedural; no genera imágenes nuevas ni recrea escenas 3D con IA.',
    }


def render_motion(spec: dict, output, *, size: tuple[int, int] | None = None,
                  overwrite: bool = False) -> Path:
    """Render a local title sequence using FFmpeg, never executing prompt text."""
    output = Path(output).expanduser().resolve()
    if output.suffix.lower() != '.mp4':
        raise ValueError('El archivo de salida debe terminar en .mp4.')
    if output.exists() and not overwrite:
        raise FileExistsError('La intro ya existe; elige otro archivo o confirma sobrescribir.')
    if size is None:
        size = (1920, 1080) if spec['platform'] == 'youtube' else (1080, 1920)
    w, h = map(int, size)
    if not (160 <= w <= 3840 and 160 <= h <= 3840 and w % 2 == 0 and h % 2 == 0):
        raise ValueError('La resolución debe ser par y estar entre 160 y 3840.')
    bg, accent = PALETTES[spec['palette']]
    duration = float(spec['duration'])
    if not (1 <= duration <= 15):
        raise ValueError('Duración inválida')
    title = spec['title']
    if not title or len(title) > 90 or any(c in title for c in '\r\n\x00'):
        raise ValueError('Título inválido')
    output.parent.mkdir(parents=True, exist_ok=True)
    font_size = max(28, min(round(w * .085), round((w * .88) / max(2, len(title) * .61))))
    with tempfile.TemporaryDirectory(prefix='director-') as temp:
        work = Path(temp)
        (work/'title.txt').write_text(title, encoding='utf-8')
        fade = f'min(1\\,t*2.2)*min(1\\,({duration:.2f}-t)*2.2)'
        float_x = '(w-text_w)/2+8*sin(t*2.2)'
        base_y = '(h-text_h)/2'
        filters = [
            f'drawbox=x=0:y=0:w=iw:h={max(5,h//85)}:color={accent}@0.9:t=fill',
            f'drawbox=x=0:y=ih-{max(5,h//85)}:w=iw:h={max(5,h//85)}:color={accent}@0.65:t=fill',
            f'drawtext=textfile=title.txt:font=Sans:fontsize={font_size}:'
            f'fontcolor={accent}:borderw=3:bordercolor={accent}@0.3:'
            f'box=1:boxcolor=black@0.2:boxborderw=12:'
            f'x={float_x}:y={base_y}:alpha={fade}',
        ]
        if spec['style'] == 'retro':
            filters += ['noise=alls=5:allf=t+u']
        elif spec['style'] == 'cinematic':
            filters += ['vignette=PI/5']
        filters.append('format=yuv420p')
        cmd = [required('ffmpeg'), '-hide_banner', '-loglevel', 'error', '-nostdin',
               '-y' if overwrite else '-n', '-f', 'lavfi', '-i',
               f'color=c={bg}:s={w}x{h}:r=30:d={duration:.2f}',
               '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo',
               '-t', str(duration), '-vf', ','.join(filters),
               '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '21',
               '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '96k',
               '-shortest', '-movflags', '+faststart', str(output)]
        run(cmd, cwd=work)
    if not output.is_file() or probe(output)['duration'] <= 0:
        raise RuntimeError('No se pudo verificar el video exportado.')
    safe_write(output.with_suffix('.json'), spec)
    return output


def reference_cuts(reference, *, max_seconds=30.0) -> dict:
    """Return approximate scene boundaries; not content understanding."""
    path = Path(reference).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError('No se encontró el video de referencia.')
    info = probe(path)
    duration = min(float(max_seconds), info['duration'])
    if not 0.5 <= duration <= 120:
        raise ValueError('El video de referencia debe durar al menos 0.5 segundos.')
    times = scene_changes(path, threshold=.26, max_seconds=duration)
    points = [0.0]
    for t in times:
        if points[-1]+.32 <= t <= duration-.32:
            points.append(float(t))
    points.append(duration)
    intervals = [[round(a, 3), round(b, 3)] for a, b in zip(points, points[1:])]
    return {
        'reference': str(path), 'duration': round(duration, 3),
        'reference_intervals': intervals, 'method': 'ffmpeg_scene_change_heuristic',
        'review_required': True,
        'warning': 'Cortes aproximados. No identifica sujetos, animaciones, efectos ni música.',
    }


def reference_to_timeline(project_folder, reference, *, prompt='estilo neón', overwrite=False) -> dict:
    """Apply reference cut rhythm to project footage, never replace source video."""
    folder = Path(project_folder).expanduser().resolve()
    target = folder/'timeline-v2.json'
    if target.exists() and not overwrite:
        raise FileExistsError('Ya existe una línea de tiempo. Confirma para reemplazarla.')
    project = read_json(folder/'project.json')
    if not project:
        raise FileNotFoundError('Crea un proyecto de video antes de usar referencias.')
    original = Path(project['source']).expanduser().resolve()
    src = probe(original)
    ref = reference_cuts(reference, max_seconds=min(30,src['duration']))
    if original == Path(ref['reference']):
        raise ValueError('El video fuente y la referencia deben ser distintos.')
    spec = parse_prompt(prompt, platform=project.get('platform', 'youtube'))
    style = {'neon': 'neon', 'cinematic': 'cinematic', 'retro': 'vhs'}[spec['style']]
    shots = []
    for i, (a, b) in enumerate(ref['reference_intervals'], 1):
        if b-a < .15:
            continue
        shots.append({'id': i, 'start': a, 'end': b, 'effect': style,
                      'zoom': 1.0, 'label': f'Referencia corte {i}',
                      'effect_reason': 'Estilo por instrucción; corte detectado en referencia'})
    if not shots:
        raise ValueError('No se detectaron intervalos aprovechables.')
    timeline = {
        'version': 2, 'kind': 'timeline', 'source': str(original),
        'duration': src['duration'], 'platform': project.get('platform','youtube'),
        'profile': project.get('profile', 'freefire_short'),
        'effects': style, 'composition': project.get('composition','fit'),
        'cut_style': 'hard', 'transition_seconds': .25, 'caption_style': 'classic',
        'clips': shots, 'candidates': [], 'subtitle_file': project.get('subtitle_file'),
        'watermark_file': project.get('watermark_file'),
        'narration_file': project.get('narration_file'),
        'review_required': True,
        'reference_analysis': ref,
        'notes': ['Conserva el ritmo aproximado de cortes; NO recrea tomas, efectos 3D ni sujetos.',
                  'La fuente original no se modifica. Revisa la línea de tiempo antes de exportar.'],
    }
    from .phase2 import validate_timeline
    validate_timeline(timeline)
    safe_write(target, timeline)
    return timeline
