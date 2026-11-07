"""OpenTimelineIO bridge for the multitrack model (optional dependency).

OTIO (Apache-2.0) is used as a timeline *interchange* format only: it
does not render or play anything. If ``opentimelineio`` is not installed
the functions raise a clear error and the rest of the editor keeps
working.

Mapping (documented, lossy where OTIO cannot express a v3 concept):
- v3 track -> OTIO Track (kind Video/Audio; image/text tracks become
  Video tracks named after the v3 track, with metadata
  ``dexter_kind`` = "image"|"text").
- v3 clip -> OTIO Clip with ExternalReference (file URL) and source_range.
  OTIO tracks are sequential, so a clip that starts after the previous
  one gets a preceding ``Gap``; overlapping image/text clips are placed
  on separate OTIO tracks (one per clip) to preserve the overlap.
- v3 keyframes/effects/transitions are stored in Clip.metadata
  ("dexter": {...}) and restored on import when present.
- Time conversion uses the canvas fps (RationalTime); sub-frame precision
  is rounded to the nearest frame and documented in the metadata.
"""
from __future__ import annotations

from pathlib import Path

from .multitrack import validate_project, _clip_duration, _new_id


def _require_otio():
    try:
        import opentimelineio as otio
    except ImportError as exc:
        raise RuntimeError(
            "OpenTimelineIO no está instalado. Instala opentimelineio "
            "para exportar/importar timelines OTIO.") from exc
    return otio


def _plain(value):
    """Convert OTIO AnyDictionary/AnyVector metadata to plain Python."""
    if isinstance(value, dict) or hasattr(value, "items"):
        try:
            items = value.items()
        except Exception:
            return value
        return {str(k): _plain(v) for k, v in items}
    if isinstance(value, (list, tuple)) or (
            hasattr(value, "__iter__") and not isinstance(value, (str, bytes))):
        try:
            return [_plain(v) for v in value]
        except Exception:
            return value
    return value


def _rt(otio, seconds, fps):
    return otio.opentime.RationalTime(round(seconds * fps), fps)


def to_otio(project, *, fps=None):
    """Convert a validated v3 project dict to an OTIO Timeline object."""
    otio = _require_otio()
    project = validate_project(project)
    fps = fps or project["canvas"]["fps"]
    timeline = otio.schema.Timeline(name=project["name"])
    for track in sorted(project["tracks"], key=lambda t: t["index"]):
        kind = track["kind"]
        otio_kind = (otio.schema.TrackKind.Video if kind in ("video", "image", "text")
                     else otio.schema.TrackKind.Audio)
        clips = sorted((c for c in project["clips"] if c["track_id"] == track["track_id"]),
                       key=lambda c: c["timeline_start"])
        if kind in ("image", "text") and len(clips) > 1:
            # OTIO tracks are sequential; overlapping overlay clips each get
            # their own track so the overlap survives the round-trip.
            for clip in clips:
                sub = otio.schema.Track(
                    name=f"{track['name']} · {clip['label']}", kind=otio_kind)
                sub.metadata["dexter_kind"] = kind
                sub.metadata["dexter_track_id"] = track["track_id"]
                _append_clip(otio, sub, clip, project, fps)
                timeline.tracks.append(sub)
            continue
        otio_track = otio.schema.Track(name=track["name"], kind=otio_kind)
        otio_track.metadata["dexter_kind"] = kind
        otio_track.metadata["dexter_track_id"] = track["track_id"]
        cursor = 0.0
        for clip in clips:
            if clip["timeline_start"] > cursor + 0.001:
                gap = otio.schema.Gap(source_range=otio.opentime.TimeRange(
                    _rt(otio, 0, fps), _rt(otio, clip["timeline_start"] - cursor, fps)))
                otio_track.append(gap)
            _append_clip(otio, otio_track, clip, project, fps)
            cursor = clip["timeline_start"] + _clip_duration(clip)
        timeline.tracks.append(otio_track)
    return timeline


def _append_clip(otio, otio_track, clip, project, fps):
    duration = _clip_duration(clip)
    if clip.get("asset_id") is None:
        # Text clips have no media file: use a Text generator reference.
        ref = otio.schema.GeneratorReference(
            name="Text", generator_kind="Text",
            parameters={"text": clip.get("text") or clip.get("label") or ""},
            available_range=otio.opentime.TimeRange(
                _rt(otio, 0, fps), _rt(otio, duration, fps)))
        otio_clip = otio.schema.Clip(
            name=clip["label"], media_reference=ref,
            source_range=otio.opentime.TimeRange(
                _rt(otio, 0, fps), _rt(otio, duration, fps)))
        otio_clip.metadata["dexter"] = {
            "clip_id": clip["clip_id"], "track_id": clip["track_id"],
            "text": clip.get("text", ""), "timeline_start": clip["timeline_start"],
            "keyframes": clip.get("keyframes", {})}
        otio_track.append(otio_clip)
        return
    asset = next(a for a in project["assets"] if a["asset_id"] == clip["asset_id"])
    ref = otio.schema.ExternalReference(
        target_url=Path(asset["path"]).as_uri(),
        available_range=otio.opentime.TimeRange(
            _rt(otio, 0, fps),
            _rt(otio, asset["duration"] or duration, fps)))
    otio_clip = otio.schema.Clip(
        name=clip["label"], media_reference=ref,
        source_range=otio.opentime.TimeRange(
            _rt(otio, clip["source_in"], fps), _rt(otio, duration, fps)))
    otio_clip.metadata["dexter"] = {
        "clip_id": clip["clip_id"], "track_id": clip["track_id"],
        "effect": clip.get("effect", "clean"), "zoom": clip.get("zoom", 1.0),
        "opacity": clip.get("opacity", 1.0), "gain": clip.get("gain", 1.0),
        "fade_in": clip.get("fade_in", 0.0), "fade_out": clip.get("fade_out", 0.0),
        "width": clip.get("width", 0.24), "text": clip.get("text", ""),
        "transition_in": clip.get("transition_in"),
        "keyframes": clip.get("keyframes", {}),
        "timeline_start": clip["timeline_start"]}
    otio_track.append(otio_clip)


def write_otio(project, path):
    """Write a v3 project dict to a .otio file."""
    otio = _require_otio()
    timeline = to_otio(project)
    otio.adapters.write_to_file(timeline, str(path))
    return Path(path)


def from_otio(path, *, canvas_width=1280, canvas_height=720, fps=30):
    """Read a .otio file into a validated v3 project dict.

    Only timelines written by this bridge (or with the same conventions)
    round-trip fully; foreign OTIO files import clips/tracks, and v3-only
    fields fall back to defaults.
    """
    otio = _require_otio()
    timeline = otio.adapters.read_from_file(str(path))
    project = {"schema": 3, "name": timeline.name or "OTIO importado",
               "canvas": {"width": canvas_width, "height": canvas_height, "fps": fps},
               "assets": [], "tracks": [], "clips": [], "markers": []}
    assets_by_url = {}
    for ti, otio_track in enumerate(timeline.tracks):
        kind = otio_track.metadata.get("dexter_kind")
        if kind not in ("video", "audio", "image", "text"):
            kind = ("audio" if otio_track.kind == otio.schema.TrackKind.Audio
                    else "video")
        track_id = otio_track.metadata.get("dexter_track_id") or f"{kind[0]}{ti + 1}"
        if not any(t["track_id"] == track_id for t in project["tracks"]):
            project["tracks"].append({
                "track_id": track_id, "kind": kind,
                "name": otio_track.name or kind.upper(), "index": len(project["tracks"]),
                "muted": False, "locked": False})
        cursor = 0.0
        for item in otio_track:
            if isinstance(item, otio.schema.Gap):
                cursor += item.source_range.duration.to_seconds()
                continue
            if not isinstance(item, otio.schema.Clip):
                continue
            ref = item.media_reference
            if isinstance(ref, otio.schema.GeneratorReference):
                meta = _plain(item.metadata.get("dexter", {}) or {})
                start = meta.get("timeline_start", cursor)
                project["clips"].append({
                    "clip_id": meta.get("clip_id") or _new_id("c"),
                    "asset_id": None, "track_id": track_id,
                    "source_in": 0.0,
                    "source_out": item.source_range.duration.to_seconds(),
                    "timeline_start": start, "effect": "clean", "zoom": 1.0,
                    "opacity": 1.0, "gain": 1.0, "fade_in": 0.0, "fade_out": 0.0,
                    "width": 0.24, "label": item.name or "Texto",
                    "text": meta.get("text", "") or
                            (ref.parameters.get("text", "") if hasattr(ref, "parameters") else ""),
                    "transition_in": None,
                    "keyframes": meta.get("keyframes", {})})
                cursor = start + _clip_duration(project["clips"][-1])
                continue
            url = getattr(ref, "target_url", "") or ""
            url_path = url[7:] if url.startswith("file://") else url
            if url_path not in assets_by_url:
                from .multitrack import probe_asset
                try:
                    asset = probe_asset(url_path)
                except Exception:
                    # Unknown/missing media: keep a placeholder asset so the
                    # project still loads; rendering will report it missing.
                    asset = {"asset_id": _new_id("a"), "path": url_path,
                             "kind": "video" if kind == "video" else
                             ("audio" if kind == "audio" else "image"),
                             "duration": item.source_range.duration.to_seconds(),
                             "width": 0, "height": 0, "fps": 0.0, "has_audio": False}
                assets_by_url[url_path] = asset
                project["assets"].append(asset)
            asset = assets_by_url[url_path]
            meta = _plain(item.metadata.get("dexter", {}) or {})
            start = meta.get("timeline_start", cursor)
            project["clips"].append({
                "clip_id": meta.get("clip_id") or _new_id("c"),
                "asset_id": asset["asset_id"], "track_id": track_id,
                "source_in": item.source_range.start_time.to_seconds(),
                "source_out": (item.source_range.start_time
                               + item.source_range.duration).to_seconds(),
                "timeline_start": start,
                "effect": meta.get("effect", "clean"),
                "zoom": meta.get("zoom", 1.0),
                "opacity": meta.get("opacity", 1.0),
                "gain": meta.get("gain", 1.0),
                "fade_in": meta.get("fade_in", 0.0),
                "fade_out": meta.get("fade_out", 0.0),
                "width": meta.get("width", 0.24),
                "label": item.name or "Clip",
                "text": meta.get("text", ""),
                "transition_in": meta.get("transition_in"),
                "keyframes": meta.get("keyframes", {})})
            cursor = start + _clip_duration(project["clips"][-1])
    return validate_project(project)
