"""Multitrack project model — schema v3.

A multitrack project is plain, reviewable JSON (``multitrack.json``):

    {
      "schema": 3, "name": "...",
      "canvas": {"width": 1280, "height": 720, "fps": 30},
      "assets": [{"asset_id": "a1", "path": "/abs/video.mp4", "kind": "video",
                  "duration": 12.0, "width": 1280, "height": 720, "fps": 30.0,
                  "has_audio": true}],
      "tracks": [{"track_id": "v1", "kind": "video", "name": "V1",
                  "index": 0, "muted": false, "locked": false}],
      "clips": [{"clip_id": "c1", "asset_id": "a1", "track_id": "v1",
                 "source_in": 1.0, "source_out": 5.0, "timeline_start": 0.0,
                 "effect": "clean", "zoom": 1.0, "opacity": 1.0, "gain": 1.0,
                 "fade_in": 0.0, "fade_out": 0.0, "label": "Toma 1",
                 "transition_in": null,
                 "keyframes": {"zoom": [], "x": [], "y": [],
                              "opacity": [], "volume": []}}],
      "markers": [{"time": 2.5, "label": "Golpe", "color": "#FFCE72"}]
    }

Rules (enforced by ``validate``):
- clip times are non-destructive: source_in/source_out select a range of
  the asset; timeline_start places it. Originals are never modified.
- video/audio tracks: clips on the same track must not overlap.
  image/text tracks: overlap is allowed (they are overlays).
- keyframe times are relative to the clip start (0..clip duration).
- transitions (``transition_in``: {"type": "crossfade"|"fade",
  "duration": 0.5}) may only link consecutive clips on the same video
  track and must be shorter than half of each neighbour.
- assets that are missing on disk are reported in ``missing_assets``
  instead of raising at load, so a project can be opened, repaired and
  saved; rendering is blocked until they resolve (recovery, not a crash).

Migration: ``migrate_v2_timeline`` converts a v2 ``timeline-v2.json``
(single-source V1 clips + V2 image / A3 audio layers) into v3 without
touching the original file. The v2 export path (``engine.export_plan``)
keeps working untouched.
"""
from __future__ import annotations

import json
import math
import uuid
from copy import deepcopy
from pathlib import Path

from .keyframes import validate_keyframes
from .media import probe
from .project import read_json, safe_write

SCHEMA_VERSION = 3
TRACK_KINDS = ("video", "audio", "image", "text")
ASSET_KINDS = ("video", "audio", "image")
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
AUDIO_SUFFIXES = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".aac"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm", ".avi"}
MAX_CLIPS = 200
MAX_TRACKS = 16
EPS = 0.001


def _new_id(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _real(value, label, minimum, maximum):
    if isinstance(value, bool):
        raise ValueError(f"{label}: valor booleano inválido.")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label}: se requiere un número.") from exc
    if not math.isfinite(number) or not minimum <= number <= maximum:
        raise ValueError(f"{label}: fuera de rango {minimum}–{maximum}.")
    return round(number, 4)


def _text(value, label, maximum=120):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{label}: texto inválido.")
    return value.strip()


def probe_asset(path):
    """Probe a media file and return its asset metadata (no file is modified)."""
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Medio no encontrado: {source}")
    suffix = source.suffix.lower()
    if suffix in VIDEO_SUFFIXES:
        info = probe(source)
        fps = 0.0
        try:
            num, den = info.get("fps", "0/1").split("/")
            fps = float(num) / float(den) if float(den) else 0.0
        except Exception:
            fps = 0.0
        return {"asset_id": _new_id("a"), "path": str(source), "kind": "video",
                "duration": round(info["duration"], 3), "width": info["width"],
                "height": info["height"], "fps": round(fps, 3),
                "has_audio": bool(info["audio"])}
    if suffix in AUDIO_SUFFIXES:
        from .composition_layers import audio_length
        return {"asset_id": _new_id("a"), "path": str(source), "kind": "audio",
                "duration": round(audio_length(str(source)), 3), "width": 0,
                "height": 0, "fps": 0.0, "has_audio": True}
    if suffix in IMAGE_SUFFIXES:
        return {"asset_id": _new_id("a"), "path": str(source), "kind": "image",
                "duration": 0.0, "width": 0, "height": 0, "fps": 0.0,
                "has_audio": False}
    raise ValueError(f"Formato no soportado: {suffix}")


def empty_project(name, *, width=1280, height=720, fps=30):
    return {
        "schema": SCHEMA_VERSION, "name": _text(name, "Nombre del proyecto"),
        "canvas": {"width": int(width), "height": int(height),
                   "fps": _real(fps, "FPS del lienzo", 1, 120)},
        "assets": [], "tracks": [], "clips": [], "markers": [],
    }


def default_tracks(project):
    """Create the standard track stack: V1, V2, A1, A2 (+ image/text rows)."""
    specs = [("video", "V1 · Montaje"), ("video", "V2 · Vídeo superior"),
             ("image", "V3 · Imágenes"), ("text", "T1 · Textos"),
             ("audio", "A1 · Audio original"), ("audio", "A2 · Voz"),
             ("audio", "A3 · Música")]
    for i, (kind, label) in enumerate(specs):
        project["tracks"].append({
            "track_id": f"{kind[0]}{i + 1}" if kind != "image" else "v3",
            "kind": kind, "name": label, "index": i,
            "muted": False, "locked": False})
    # Fix ids to be stable and readable.
    ids = ["v1", "v2", "v3", "t1", "a1", "a2", "a3"]
    for track, tid in zip(project["tracks"], ids):
        track["track_id"] = tid
    return project


def _clip_duration(clip):
    return round(clip["source_out"] - clip["source_in"], 4)


def validate_clip(clip, assets, tracks, *, check_overlap=True):
    if not isinstance(clip, dict):
        raise ValueError("Clip inválido.")
    track = next((t for t in tracks if t["track_id"] == clip.get("track_id")), None)
    if track is None:
        raise ValueError(f"Clip sin pista válida: {clip.get('clip_id')}.")
    kind_ok = {"video": "video", "audio": "audio", "image": "image"}
    if track["kind"] == "text":
        if clip.get("asset_id") is not None:
            raise ValueError("Un clip de texto no usa asset.")
        asset = None
    else:
        asset = next((a for a in assets if a["asset_id"] == clip.get("asset_id")), None)
        if asset is None:
            raise ValueError(f"Clip sin asset válido: {clip.get('clip_id')}.")
    if track["kind"] != "text" and kind_ok.get(track["kind"]) != asset["kind"]:
        raise ValueError(
            f"El asset {asset['kind']} no pertenece a la pista {track['kind']}.")
    source_in = _real(clip.get("source_in", 0), "Inicio de fuente", 0, 172800)
    source_out = _real(clip.get("source_out", 0), "Fin de fuente", 0, 172800)
    if track["kind"] != "text" and asset["kind"] != "image" and not source_in < source_out:
        raise ValueError("El clip debe tener duración positiva.")
    if track["kind"] != "text" and asset["kind"] != "image" and asset.get("duration", 0) > 0:
        if source_out > asset["duration"] + 0.05:
            raise ValueError("El clip sale de los límites del asset.")
    timeline_start = _real(clip.get("timeline_start", 0), "Inicio en timeline", 0, 172800)
    effect = clip.get("effect", "clean")
    from .engine import EFFECTS
    if track["kind"] == "video" and effect not in EFFECTS:
        raise ValueError(f"Efecto desconocido: {effect}.")
    duration = _clip_duration({"source_in": source_in, "source_out": source_out})
    keyframes = clip.get("keyframes") or {}
    if not isinstance(keyframes, dict):
        raise ValueError("Los keyframes deben ser un objeto.")
    bounds = {"zoom": (1.0, 1.6), "x": (0.0, 1.0), "y": (0.0, 1.0),
              "opacity": (0.0, 1.0), "volume": (0.0, 2.0)}
    for name, (lo, hi) in bounds.items():
        validate_keyframes(keyframes.get(name), minimum=lo, maximum=hi,
                           duration=duration, label=f"Keyframes {name}")
    if clip.get("transition_in") is not None:
        tr = clip["transition_in"]
        if not isinstance(tr, dict) or tr.get("type") not in ("crossfade", "fade"):
            raise ValueError("Transición inválida.")
        _real(tr.get("duration", 0), "Duración de transición", 0.05, 1.5)
    _real(clip.get("zoom", 1.0), "Zoom", 1.0, 1.6)
    _real(clip.get("opacity", 1.0), "Opacidad", 0.0, 1.0)
    _real(clip.get("gain", 1.0), "Ganancia", 0.0, 2.0)
    _real(clip.get("fade_in", 0.0), "Fade de entrada", 0.0, 30.0)
    _real(clip.get("fade_out", 0.0), "Fade de salida", 0.0, 30.0)
    return {"clip_id": str(clip.get("clip_id") or _new_id("c")),
            "asset_id": clip.get("asset_id"), "track_id": track["track_id"],
            "source_in": source_in, "source_out": source_out,
            "timeline_start": timeline_start,
            "effect": effect, "zoom": _real(clip.get("zoom", 1.0), "Zoom", 1.0, 1.6),
            "opacity": _real(clip.get("opacity", 1.0), "Opacidad", 0.0, 1.0),
            "gain": _real(clip.get("gain", 1.0), "Ganancia", 0.0, 2.0),
            "fade_in": _real(clip.get("fade_in", 0.0), "Fade de entrada", 0.0, 30.0),
            "fade_out": _real(clip.get("fade_out", 0.0), "Fade de salida", 0.0, 30.0),
            "width": _real(clip.get("width", 0.24), "Ancho relativo", 0.04, 0.85),
            "label": str(clip.get("label") or "Clip")[:120],
            "text": str(clip.get("text", ""))[:500] if track["kind"] == "text" else "",
            "transition_in": clip.get("transition_in"),
            "keyframes": {name: validate_keyframes(keyframes.get(name), minimum=lo,
                                                    maximum=hi, duration=duration,
                                                    label=f"Keyframes {name}")
                         for name, (lo, hi) in bounds.items()}}


def validate_project(data):
    """Canonicalize + validate a v3 project dict; returns the clean copy."""
    if not isinstance(data, dict) or data.get("schema") != SCHEMA_VERSION:
        raise ValueError(f"El proyecto debe ser esquema v{SCHEMA_VERSION}.")
    canvas = data.get("canvas") or {}
    width = int(canvas.get("width", 1280))
    height = int(canvas.get("height", 720))
    fps = _real(canvas.get("fps", 30), "FPS del lienzo", 1, 120)
    if not (16 <= width <= 7680 and 16 <= height <= 4320):
        raise ValueError("Dimensiones de lienzo no válidas.")
    assets = data.get("assets") or []
    tracks = data.get("tracks") or []
    clips = data.get("clips") or []
    markers = data.get("markers") or []
    if len(assets) > 500 or len(tracks) > MAX_TRACKS or len(clips) > MAX_CLIPS:
        raise ValueError("Proyecto demasiado grande (límites: 500 assets, "
                         f"{MAX_TRACKS} pistas, {MAX_CLIPS} clips).")
    seen_assets = set()
    clean_assets = []
    for asset in assets:
        if not isinstance(asset, dict) or asset.get("asset_id") in seen_assets:
            raise ValueError("Asset duplicado o inválido.")
        seen_assets.add(asset["asset_id"])
        if asset.get("kind") not in ASSET_KINDS:
            raise ValueError("Tipo de asset desconocido.")
        clean_assets.append({
            "asset_id": str(asset["asset_id"]), "path": str(asset.get("path", "")),
            "kind": asset["kind"],
            "duration": _real(asset.get("duration", 0), "Duración del asset", 0, 172800),
            "width": int(asset.get("width", 0)), "height": int(asset.get("height", 0)),
            "fps": _real(asset.get("fps", 0), "FPS del asset", 0, 240),
            "has_audio": bool(asset.get("has_audio", False))})
    seen_tracks = set()
    clean_tracks = []
    for track in tracks:
        if not isinstance(track, dict) or track.get("track_id") in seen_tracks:
            raise ValueError("Pista duplicada o inválida.")
        seen_tracks.add(track["track_id"])
        if track.get("kind") not in TRACK_KINDS:
            raise ValueError("Tipo de pista desconocido.")
        clean_tracks.append({
            "track_id": str(track["track_id"]), "kind": track["kind"],
            "name": str(track.get("name", track["kind"]))[:80],
            "index": int(track.get("index", len(clean_tracks))),
            "muted": bool(track.get("muted", False)),
            "locked": bool(track.get("locked", False))})
    clean_tracks.sort(key=lambda t: t["index"])
    clean_clips = [validate_clip(c, clean_assets, clean_tracks) for c in clips]
    # Overlap rule: video/audio tracks are sequential; image/text may overlap.
    for track in clean_tracks:
        if track["kind"] in ("image", "text"):
            continue
        ordered = sorted((c for c in clean_clips if c["track_id"] == track["track_id"]),
                         key=lambda c: c["timeline_start"])
        for a, b in zip(ordered, ordered[1:]):
            a_end = a["timeline_start"] + _clip_duration(a)
            if b["timeline_start"] < a_end - EPS:
                raise ValueError(
                    f"Solape en la pista {track['track_id']}: "
                    f"{a['clip_id']} y {b['clip_id']} se cruzan.")
            # A transition_in only makes sense on a clip that directly
            # follows another clip on the same track.
            if b.get("transition_in") is not None:
                gap = b["timeline_start"] - a_end
                dur = b["transition_in"]["duration"]
                if gap > EPS:
                    raise ValueError("La transición requiere clips contiguos.")
                if dur > min(_clip_duration(a), _clip_duration(b)) / 2:
                    raise ValueError("Transición más larga que la mitad del clip.")
    clean_markers = []
    for marker in markers:
        if not isinstance(marker, dict):
            raise ValueError("Marcador inválido.")
        clean_markers.append({
            "time": _real(marker.get("time", 0), "Tiempo del marcador", 0, 172800),
            "label": str(marker.get("label", ""))[:80],
            "color": str(marker.get("color", "#FFCE72"))[:16]})
    return {"schema": SCHEMA_VERSION,
            "name": _text(data.get("name", "Proyecto multipista"), "Nombre"),
            "canvas": {"width": width, "height": height, "fps": fps},
            "assets": clean_assets, "tracks": clean_tracks,
            "clips": clean_clips, "markers": clean_markers}


def project_duration(project):
    """Composed duration of the project.

    Video tracks are simulated the same way the compositor builds them:
    crossfade transitions overlap the neighbours, so they shorten the
    track (a 2 s + 3 s pair with a 0.25 s crossfade lasts 4.75 s, not
    5 s). Other tracks use the plain max end time.
    """
    total = 0.0
    tracks = {t["track_id"]: t for t in project["tracks"]}
    for track in project["tracks"]:
        clips = sorted((c for c in project["clips"]
                        if c["track_id"] == track["track_id"]),
                       key=lambda c: c["timeline_start"])
        if not clips:
            continue
        if track["kind"] == "video":
            cursor = 0.0
            for clip in clips:
                dur = _clip_duration(clip)
                start = clip["timeline_start"]
                if cursor == 0.0 and start > 0:
                    cursor = start + dur
                    continue
                gap = start - cursor
                if gap > 0.001:
                    cursor += gap + dur
                elif clip.get("transition_in") is not None and \
                        clip["transition_in"].get("type") == "crossfade":
                    cursor += dur - float(clip["transition_in"]["duration"])
                else:
                    cursor += dur
            total = max(total, cursor)
        else:
            for clip in clips:
                total = max(total, clip["timeline_start"] + _clip_duration(clip))
    return round(total, 3)


def missing_assets(project):
    return [a for a in project["assets"] if not Path(a["path"]).is_file()]


def snap_points(project):
    """Times the playhead/clip edges snap to: 0, clip edges, markers, end."""
    points = {0.0}
    for clip in project["clips"]:
        points.add(round(clip["timeline_start"], 3))
        points.add(round(clip["timeline_start"] + _clip_duration(clip), 3))
    for marker in project["markers"]:
        points.add(round(marker["time"], 3))
    points.add(project_duration(project))
    return sorted(points)


def snap_time(project, t, *, threshold=0.25):
    """Return the nearest snap point within `threshold`, else `t`."""
    best = None
    for point in snap_points(project):
        if abs(point - t) <= threshold and (best is None or abs(point - t) < abs(best - t)):
            best = point
    return round(best, 3) if best is not None else round(t, 3)


class History:
    """Undo/redo over serialized project snapshots (max 40)."""

    def __init__(self, initial):
        self._undo = []
        self._redo = []
        self._current = deepcopy(initial)

    def commit(self, project):
        self._undo.append(deepcopy(self._current))
        self._undo = self._undo[-40:]
        self._redo.clear()
        self._current = deepcopy(project)

    def undo(self):
        if not self._undo:
            return None
        self._redo.append(deepcopy(self._current))
        self._current = self._undo.pop()
        return deepcopy(self._current)

    def redo(self):
        if not self._redo:
            return None
        self._undo.append(deepcopy(self._current))
        self._current = self._redo.pop()
        return deepcopy(self._current)

    @property
    def current(self):
        return deepcopy(self._current)


class MultiTrackProject:
    """In-memory v3 project with validation, history and persistence."""

    def __init__(self, data):
        self.data = validate_project(data)
        self.history = History(self.data)

    @classmethod
    def create(cls, name, *, width=1280, height=720, fps=30):
        project = default_tracks(empty_project(name, width=width, height=height, fps=fps))
        return cls(project)

    @classmethod
    def load(cls, path):
        data = read_json(Path(path))
        if not data:
            raise FileNotFoundError(f"No existe el proyecto multipista: {path}")
        return cls(data)

    def save(self, path):
        safe_write(Path(path), self.data)
        return Path(path)

    def change(self, mutate):
        before = deepcopy(self.data)
        mutate(self.data)
        try:
            self.data = validate_project(self.data)
        except Exception:
            self.data = before
            raise
        self.history.commit(self.data)

    def undo(self):
        state = self.history.undo()
        if state is not None:
            self.data = state
            return True
        return False

    def redo(self):
        state = self.history.redo()
        if state is not None:
            self.data = state
            return True
        return False

    def add_asset(self, path):
        asset = probe_asset(path)
        self.change(lambda d: d["assets"].append(asset))
        return asset

    def add_clip(self, **fields):
        clip = validate_clip(fields, self.data["assets"], self.data["tracks"])
        self.change(lambda d: d["clips"].append(clip))
        return clip

    def move_clip(self, clip_id, new_start, *, snap=True):
        def mutate(d):
            clip = next(c for c in d["clips"] if c["clip_id"] == clip_id)
            clip["timeline_start"] = snap_time(d, new_start) if snap else round(new_start, 3)
        self.change(mutate)

    def split_clip(self, clip_id, at_timeline):
        def mutate(d):
            clip = next(c for c in d["clips"] if c["clip_id"] == clip_id)
            offset = at_timeline - clip["timeline_start"]
            duration = _clip_duration(clip)
            if not 0.2 < offset < duration - 0.2:
                raise ValueError("Divide al menos a 0,2 s de cada extremo.")
            second = deepcopy(clip)
            second["clip_id"] = _new_id("c")
            second["source_in"] = round(clip["source_in"] + offset, 3)
            second["timeline_start"] = round(at_timeline, 3)
            second["transition_in"] = None
            clip["source_out"] = round(clip["source_in"] + offset, 3)
            clip["transition_in"] = None
            d["clips"].append(second)
        self.change(mutate)

    def remove_clip(self, clip_id):
        self.change(lambda d: d.__setitem__(
            "clips", [c for c in d["clips"] if c["clip_id"] != clip_id]))

    def add_marker(self, time, label=""):
        self.change(lambda d: d["markers"].append(
            {"time": round(time, 3), "label": label, "color": "#FFCE72"}))


def migrate_v2_timeline(timeline_v2, project_json):
    """Convert a v2 timeline dict (StudioDocument JSON) into a v3 project.

    The source files are never touched; the result must pass
    ``validate_project`` before it is used anywhere.
    """
    source = Path(timeline_v2["source"]).expanduser().resolve()
    info = probe(source)
    fps = 0.0
    try:
        num, den = info.get("fps", "30/1").split("/")
        fps = float(num) / float(den) if float(den) else 30.0
    except Exception:
        fps = 30.0
    platform = timeline_v2.get("platform", "youtube")
    width, height = (1080, 1920) if platform in ("shorts", "tiktok") else (1920, 1080)
    project = default_tracks(empty_project(
        project_json.get("name", "Proyecto migrado v2"),
        width=width, height=height, fps=round(fps) or 30))
    asset = {"asset_id": "a-source", "path": str(source), "kind": "video",
             "duration": round(info["duration"], 3), "width": info["width"],
             "height": info["height"], "fps": round(fps, 3),
             "has_audio": bool(info["audio"])}
    project["assets"].append(asset)
    position = 0.0
    cut_style = timeline_v2.get("cut_style", "hard")
    transition = float(timeline_v2.get("transition_seconds", 0.25))
    for i, clip in enumerate(timeline_v2.get("clips", [])):
        duration = float(clip["end"]) - float(clip["start"])
        entry = {"clip_id": f"c-v1-{i + 1}", "asset_id": "a-source",
                 "track_id": "v1", "source_in": float(clip["start"]),
                 "source_out": float(clip["end"]), "timeline_start": round(position, 3),
                 "effect": clip.get("effect", "clean"),
                 "zoom": float(clip.get("zoom", 1.0)), "opacity": 1.0, "gain": 1.0,
                 "fade_in": 0.0, "fade_out": 0.0,
                 "label": clip.get("label", f"Clip {i + 1}"),
                 "transition_in": ({"type": "crossfade", "duration": transition}
                                  if cut_style == "crossfade" and i > 0 else None),
                 "keyframes": {"zoom": [], "x": [], "y": [], "opacity": [], "volume": []}}
        project["clips"].append(entry)
        position += duration
        if cut_style == "crossfade" and i > 0:
            position -= transition
    layers = timeline_v2.get("layers") or {}
    for i, image in enumerate(layers.get("images", [])):
        img_asset = probe_asset(image["path"])
        img_asset["asset_id"] = f"a-img-{i + 1}"
        project["assets"].append(img_asset)
        project["clips"].append({
            "clip_id": f"c-v3-{i + 1}", "asset_id": img_asset["asset_id"],
            "track_id": "v3", "source_in": 0.0, "source_out": 0.0,
            "timeline_start": float(image["start"]),
            "effect": "clean", "zoom": 1.0,
            "opacity": float(image.get("opacity", 1.0)), "gain": 1.0,
            "fade_in": 0.0, "fade_out": 0.0,
            "label": Path(image["path"]).name,
            "transition_in": None,
            "width": float(image.get("width", 0.24)),
            "keyframes": {"zoom": [], "x": [{"t": 0.0, "v": float(image.get("x", 0.5)), "easing": "linear"}],
                         "y": [{"t": 0.0, "v": float(image.get("y", 0.8)), "easing": "linear"}],
                         "opacity": [], "volume": []}})
        # Duration of an image clip is carried by its end time; store it by
        # using source_out as a duration marker (0 means "still image").
        project["clips"][-1]["source_out"] = round(
            float(image.get("end", 0.0)) - float(image.get("start", 0.0)), 3)
    for i, music in enumerate(layers.get("audio", [])):
        mus_asset = probe_asset(music["path"])
        mus_asset["asset_id"] = f"a-mus-{i + 1}"
        project["assets"].append(mus_asset)
        project["clips"].append({
            "clip_id": f"c-a3-{i + 1}", "asset_id": mus_asset["asset_id"],
            "track_id": "a3", "source_in": float(music.get("source_start", 0)),
            "source_out": float(music.get("source_start", 0)) + float(music.get("duration", 0)),
            "timeline_start": float(music.get("start", 0)),
            "effect": "clean", "zoom": 1.0, "opacity": 1.0,
            "gain": float(music.get("gain", 0.35)), "fade_in": 0.0, "fade_out": 0.0,
            "label": Path(music["path"]).name,
            "transition_in": None,
            "keyframes": {"zoom": [], "x": [], "y": [], "opacity": [], "volume": []}})
    # Image clips: source_in=0 and source_out=on-screen duration (an image
    # asset has no intrinsic duration); see validate_clip.
    return validate_project(project)
