"""Real V2 still-image and A3 music tracks for FFmpeg renders.

All values are validated and represented as typed numbers; file paths are passed as
subprocess arguments and never interpolated into FFmpeg filter expressions.
This module intentionally does not claim multi-source video or realtime composition.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from .media import required, run


AUDIO_SUFFIXES = {'.wav', '.mp3', '.m4a', '.flac', '.ogg', '.aac'}
IMAGE_SUFFIXES = {'.png', '.jpg', '.jpeg', '.webp'}


def _real(value, label, minimum, maximum):
    if isinstance(value, bool):
        raise ValueError(label + ': valor booleano inválido.')
    try:
        number = float(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(label + ': se requiere un número.') from exc
    if not math.isfinite(number) or not minimum <= number <= maximum:
        raise ValueError(f'{label}: fuera de rango {minimum}–{maximum}.')
    return round(number, 4)


def _file(path, suffixes, kind):
    if not isinstance(path, str) or not path or '\x00' in path:
        raise ValueError(f'{kind}: ruta inválida.')
    source = Path(path).expanduser().resolve()
    if source.suffix.lower() not in suffixes or not source.is_file():
        raise FileNotFoundError(f'{kind}: archivo compatible no encontrado: {source}')
    return str(source)


def audio_length(path):
    """Get audio duration and require a real audio stream; no video needed."""
    output = run([
        required('ffprobe'), '-v', 'error', '-show_entries',
        'stream=codec_type:format=duration', '-of', 'json', path,
    ]).stdout
    parsed = json.loads(output)
    if not any(s.get('codec_type') == 'audio' for s in parsed.get('streams', [])):
        raise ValueError('La pista importada no contiene audio.')
    duration = float(parsed.get('format', {}).get('duration') or 0)
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('La duración del audio es inválida.')
    return duration


def validate_layers(layers, duration):
    """Canonicalize asset tracks; fail *before* touching output files."""
    duration = _real(duration, 'Duración del montaje', .1, 172800)
    if layers is None:
        layers = {}
    if not isinstance(layers, dict):
        raise ValueError('Las capas deben ser un objeto JSON.')
    images = layers.get('images', [])
    audio = layers.get('audio', [])
    if not isinstance(images, list) or len(images) > 6:
        raise ValueError('V2 admite hasta 6 imágenes.')
    if not isinstance(audio, list) or len(audio) > 4:
        raise ValueError('A3 admite hasta 4 pistas de música.')
    result = {'images': [], 'audio': []}
    for raw in images:
        if not isinstance(raw, dict):
            raise ValueError('Capa de imagen inválida.')
        start = _real(raw.get('start', 0), 'Inicio de overlay', 0, duration)
        end = _real(raw.get('end', duration), 'Fin de overlay', 0, duration)
        if end - start < .1:
            raise ValueError('El overlay debe durar al menos 0,1 segundos.')
        result['images'].append({
            'path': _file(raw.get('path'), IMAGE_SUFFIXES, 'Imagen'),
            'start': start, 'end': end,
            'width': _real(raw.get('width', .24), 'Ancho relativo', .04, .85),
            'x': _real(raw.get('x', .5), 'Posición X', 0, 1),
            'y': _real(raw.get('y', .8), 'Posición Y', 0, 1),
            'opacity': _real(raw.get('opacity', 1), 'Opacidad', 0, 1),
        })
    for raw in audio:
        if not isinstance(raw, dict):
            raise ValueError('Capa de sonido inválida.')
        path = _file(raw.get('path'), AUDIO_SUFFIXES, 'Música')
        start = _real(raw.get('start', 0), 'Inicio de música', 0, duration)
        source_start = _real(raw.get('source_start', 0), 'Inicio dentro del archivo', 0, 172800)
        length = _real(raw.get('duration', duration-start), 'Duración musical', .1, duration)
        if start + length > duration + .025:
            raise ValueError('La música no puede continuar fuera de la composición.')
        if source_start + length > audio_length(path) + .05:
            raise ValueError('El archivo de música es demasiado corto para el fragmento.')
        result['audio'].append({
            'path': path, 'start': start,
            'source_start': source_start, 'duration': length,
            'gain': _real(raw.get('gain', .35), 'Ganancia musical', 0, 2),
        })
    return result


def compose_layers(cmd, filters, current_video, current_audio, *, first_input, layers, width, height):
    """Append actual file inputs and FFmpeg filter nodes.

    Existing inputs are [joined video, optional watermark/memes, optional narration].
    Returns (video_output_label, audio_output_label, extra_input_count).
    """
    image_layers = layers['images']
    audio_layers = layers['audio']
    idx = first_input
    for item in image_layers:
        cmd.extend(['-loop', '1', '-i', item['path']])
    for item in audio_layers:
        cmd.extend(['-i', item['path']])
    for index, item in enumerate(image_layers):
        slot = idx + index
        scale_width = max(2, 2 * round(width * item['width'] / 2))
        opacity = item['opacity']
        filters.append(
            f'[{slot}:v]scale={scale_width}:-2:flags=lanczos,'
            f'format=rgba,colorchannelmixer=aa={opacity:.4f}[layerimg{index}]'
        )
        out = f'[vextra{index}]'
        filters.append(
            f'{current_video}[layerimg{index}]'
            f'overlay=x=(W-w)*{item["x"]:.4f}:y=(H-h)*{item["y"]:.4f}:'
            f'enable=\'between(t,{item["start"]:.4f},{item["end"]:.4f})\':'
            f'shortest=1{out}'
        )
        current_video = out
    audio_nodes = [current_audio]
    for index, item in enumerate(audio_layers):
        slot = idx + len(image_layers) + index
        delay_ms = round(item['start']*1000)
        filters.append(
            f'[{slot}:a]atrim=start={item["source_start"]:.4f}:'
            f'duration={item["duration"]:.4f},'
            f'asetpts=PTS-STARTPTS,aresample=48000,'
            f'aformat=channel_layouts=stereo,volume={item["gain"]:.4f},'
            f'adelay={delay_ms}:all=1[atrack{index}]'
        )
        audio_nodes.append(f'[atrack{index}]')
    if audio_layers:
        filters.append(
            ''.join(audio_nodes) +
            f'amix=inputs={len(audio_nodes)}:duration=first:dropout_transition=0[atotal]'
        )
        current_audio = '[atotal]'
    return current_video, current_audio, len(image_layers)+len(audio_layers)
