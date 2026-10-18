"""Editable video timeline document for the Qt studio.

The export path is still the existing FFmpeg engine. No synthetic media is
created, and project files are explicit, reviewable JSON.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from .engine import EFFECTS
from .project import read_json, safe_write
from .composition_layers import validate_layers, audio_length


@dataclass
class StudioClip:
    start: float
    end: float
    effect: str = 'clean'
    zoom: float = 1.0
    label: str = 'Clip'

    @property
    def duration(self):
        return round(self.end - self.start, 3)

    def as_dict(self, index):
        return {
            'id': index, 'start': round(self.start, 3),
            'end': round(self.end, 3), 'effect': self.effect,
            'zoom': self.zoom, 'label': self.label,
        }


class StudioDocument:
    """Non-destructive V1 editor model; source audio follows each video cut."""

    def __init__(self, folder):
        self.folder = Path(folder).expanduser().resolve()
        self.project = read_json(self.folder / 'project.json')
        if not self.project:
            raise FileNotFoundError('No existe project.json; crea o abre un proyecto.')
        self.source = Path(self.project['source']).expanduser().resolve()
        if not self.source.is_file():
            raise FileNotFoundError('No se encontró la grabación original.')
        from .media import probe
        self.media_info = probe(self.source)
        if self.media_info['duration'] <= 0:
            raise ValueError('La grabación original no tiene duración válida.')
        saved = read_json(self.folder / 'timeline-v2.json')
        if saved and Path(saved.get('source', '')).resolve() != self.source:
            raise ValueError('El timeline guardado pertenece a otra grabación.')
        items = saved.get('clips', []) if saved else []
        self.clips = [
            StudioClip(float(item['start']), float(item['end']),
                       str(item.get('effect', 'clean')),
                       float(item.get('zoom', 1.0)),
                       str(item.get('label', 'Clip')))
            for item in items
        ] if items else [
            StudioClip(0.0, self.media_info['duration'],
                       self.project.get('effects', 'clean'), 1.0, 'Grabación original')
        ]
        self.caption_style = saved.get('caption_style', 'classic') if saved else 'classic'
        self.layers = deepcopy(saved.get('layers', {'images': [], 'audio': []})) if saved else {'images': [], 'audio': []}
        self._undo = []
        self._redo = []
        self.validate()

    @property
    def output_duration(self):
        return sum(c.duration for c in self.clips)

    def validate(self):
        if not 1 <= len(self.clips) <= 100:
            raise ValueError('El proyecto admite entre 1 y 100 segmentos.')
        total = self.media_info['duration'] + 0.05
        for clip in self.clips:
            if not 0 <= clip.start < clip.end <= total:
                raise ValueError('Segmento fuera de los límites del video.')
            if clip.effect not in EFFECTS or not 1 <= clip.zoom <= 1.6:
                raise ValueError('Efecto o zoom no compatible.')
        self.layers = validate_layers(self.layers, self.output_duration)
        return True

    def snapshot(self):
        return (deepcopy(self.clips), deepcopy(self.layers))

    def restore(self, state):
        self.clips, self.layers = deepcopy(state)

    def change(self, action):
        before = self.snapshot()
        action()
        try:
            self.validate()
        except Exception:
            self.restore(before)
            raise
        self._undo.append(before)
        self._undo = self._undo[-40:]
        self._redo.clear()

    def add_image(self, source, *, start=0, end=None, width=.24, x=.5, y=.8, opacity=1):
        if end is None:
            end = self.output_duration
        entry = {'path': str(source), 'start': start, 'end': end,
                 'width': width, 'x': x, 'y': y, 'opacity': opacity}
        self.change(lambda: self.layers['images'].append(entry))

    def add_audio(self, source, *, start=0, source_start=0, duration=None, gain=.35):
        if duration is None:
            duration = min(self.output_duration-float(start),
                           audio_length(str(source))-float(source_start))
        entry = {'path': str(source), 'start': start, 'source_start': source_start,
                 'duration': duration, 'gain': gain}
        self.change(lambda: self.layers['audio'].append(entry))

    def remove_layer(self, kind, index):
        if kind not in ('audio','images'):
            raise ValueError('Tipo de pista inválido')
        self.change(lambda: self.layers[kind].pop(index))

    def update_layer(self, kind, index, **changes):
        if kind not in ('audio','images'):
            raise ValueError('Tipo de pista inválido')
        def change():
            for key,value in changes.items():
                if key not in self.layers[kind][index] or key == 'path':
                    raise ValueError('Propiedad de pista no editable.')
                self.layers[kind][index][key] = value
        self.change(change)

    def split(self, index, at):
        if not 0 <= index < len(self.clips):
            raise IndexError(index)
        clip = self.clips[index]
        if not clip.start + 0.20 < at < clip.end - 0.20:
            raise ValueError('Coloca el cursor al menos 0,2 s de cada extremo.')
        def act():
            a = deepcopy(clip)
            b = deepcopy(clip)
            a.end = round(float(at), 3)
            b.start = round(float(at), 3)
            self.clips[index:index+1] = [a, b]
        self.change(act)

    def remove(self, index):
        if len(self.clips) < 2:
            raise ValueError('No es posible eliminar el último clip.')
        self.change(lambda: self.clips.pop(index))

    def move(self, index, new_index):
        if not 0 <= index < len(self.clips) or not 0 <= new_index < len(self.clips):
            raise IndexError('Clip fuera del timeline.')
        def act():
            clip = self.clips.pop(index)
            self.clips.insert(new_index, clip)
        self.change(act)

    def set_effect(self, index, *, effect=None, zoom=None):
        def act():
            clip = self.clips[index]
            if effect is not None:
                clip.effect = effect
            if zoom is not None:
                clip.zoom = float(zoom)
        self.change(act)

    def trim(self, index, *, start=None, end=None):
        def act():
            clip = self.clips[index]
            if start is not None:
                clip.start = round(float(start), 3)
            if end is not None:
                clip.end = round(float(end), 3)
        self.change(act)

    def undo(self):
        if not self._undo:
            return False
        self._redo.append(self.snapshot())
        self.restore(self._undo.pop())
        return True

    def redo(self):
        if not self._redo:
            return False
        self._undo.append(self.snapshot())
        self.restore(self._redo.pop())
        return True

    def save(self):
        self.validate()
        from .caption_styles import CAPTION_STYLES
        if self.caption_style not in CAPTION_STYLES:
            raise ValueError('Estilo de subtítulos inválido.')
        path = self.folder / 'timeline-v2.json'
        prior = read_json(path, {})
        timeline = {
            'version': 2, 'kind': 'timeline',
            'source': str(self.source), 'duration': self.media_info['duration'],
            'platform': self.project.get('platform', 'youtube'),
            'profile': self.project.get('profile', 'freefire_short'),
            'effects': self.project.get('effects', 'clean'),
            'composition': self.project.get('composition', 'fit'),
            'cut_style': 'hard', 'transition_seconds': 0.25,
            'caption_style': self.caption_style,
            'clips': [c.as_dict(i) for i, c in enumerate(self.clips, 1)],
            'layers': deepcopy(self.layers),
            'candidates': prior.get('candidates', []),
            'scene_times': prior.get('scene_times', []),
            'subtitle_file': self.project.get('subtitle_file'),
            'watermark_file': self.project.get('watermark_file'),
            'narration_file': self.project.get('narration_file'),
            'review_required': True,
            'notes': ['UI Qt: montaje de video V1 con audio original sincronizado.',
                      'V2 admite imágenes y A3 música real; V3/A2 y pistas multivideo aún no se exportan.'],
        }
        from .phase2 import validate_timeline
        validate_timeline(timeline)
        safe_write(path, timeline)
        return path
