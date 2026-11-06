"""Proxy preview: incremental low-resolution renders + frame server.

The preview never renders the full-quality film: it renders the same
composition at a small canvas (default 480p height) and caches it.

Two cache levels, both keyed by content hashes (not by timestamps):

1. **Segment cache** — each normalized clip segment (trim + scale +
   fps + effect, at proxy resolution) is rendered once to
   ``previews/proxy-segments/<hash>.mp4`` and reused while its inputs
   (asset bytes, in/out, effect, zoom, canvas) do not change.
2. **Assembly cache** — the assembled proxy for the whole project is
   stored as ``previews/proxy-<key>.mp4`` with a ``proxy-<key>.json``
   manifest holding the project hash. A second preview of an unchanged
   project is a cache hit and renders nothing.

The frame server decodes single frames (or a rawvideo stream) from a
proxy with FFmpeg, so the Qt preview can scrub and play without
QtMultimedia or any system playback backend.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from .compositor import render
from .media import probe, required
from .multitrack import _clip_duration, project_duration, validate_project

DEFAULT_PROXY_HEIGHT = 480


def _canonical(project):
    """Stable JSON for hashing: sorted keys, no volatile fields."""
    return json.dumps(project, sort_keys=True, ensure_ascii=False)


def project_hash(project):
    return hashlib.sha256(_canonical(project).encode("utf-8")).hexdigest()


def _asset_fingerprint(asset):
    path = Path(asset["path"])
    try:
        stat = path.stat()
        return f"{stat.st_size}:{stat.st_mtime_ns}"
    except OSError:
        return "missing"


def segment_key(clip, asset, canvas):
    payload = {"asset": asset["path"], "fp": _asset_fingerprint(asset),
               "in": clip["source_in"], "out": clip["source_out"],
               "effect": clip.get("effect", "clean"), "zoom": clip.get("zoom", 1.0),
               "canvas": canvas}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


def proxy_canvas(project, *, height=DEFAULT_PROXY_HEIGHT):
    canvas = project["canvas"]
    scale = height / canvas["height"]
    width = max(16, int(canvas["width"] * scale) // 2 * 2)
    return {"width": width, "height": height, "fps": canvas["fps"]}


def get_proxy(project, folder, *, height=DEFAULT_PROXY_HEIGHT):
    """Return (proxy_path, cache_hit). Renders only on a cache miss.

    ``folder`` is the project folder; proxies live in ``folder/previews``.
    """
    project = validate_project(project)
    folder = Path(folder)
    previews = folder / "previews"
    previews.mkdir(parents=True, exist_ok=True)
    key = project_hash(project)[:16]
    target = previews / f"proxy-{key}-{height}p.mp4"
    manifest = previews / f"proxy-{key}-{height}p.json"
    if target.is_file() and manifest.is_file():
        try:
            saved = json.loads(manifest.read_text(encoding="utf-8"))
            if saved.get("project_hash") == project_hash(project):
                return target, True
        except Exception:
            pass
    pcanvas = proxy_canvas(project, height=height)
    render(project, target, overwrite=True, preset="veryfast", crf=28,
           width=pcanvas["width"], height=pcanvas["height"], fps=pcanvas["fps"])
    manifest.write_text(json.dumps({
        "project_hash": project_hash(project), "height": height,
        "width": pcanvas["width"], "fps": pcanvas["fps"],
        "duration": project_duration(project)}, indent=2), encoding="utf-8")
    return target, False


def frame_at(video_path, t, *, width=None, height=None):
    """Decode one frame at time t; returns (rgb24_bytes, width, height).

    Raises RuntimeError if FFmpeg fails or the frame is empty.
    """
    info = probe(video_path)
    width = width or info["width"]
    height = height or info["height"]
    result = subprocess.run(
        [required("ffmpeg"), "-hide_banner", "-loglevel", "error", "-nostdin",
         "-ss", f"{t:.3f}", "-i", str(video_path), "-frames:v", "1",
         "-vf", f"scale={width}:{height}", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "pipe:1"], capture_output=True, timeout=30)
    expected = width * height * 3
    if result.returncode or len(result.stdout) < expected:
        raise RuntimeError(f"No se pudo extraer el fotograma a {t:.2f}s.")
    return result.stdout[:expected], width, height


def iter_frames(video_path, *, fps=30, width=None, height=None):
    """Yield (time, rgb24_bytes, width, height) decoding the whole file.

    Streams rawvideo from a single FFmpeg process (no per-frame spawn).
    The caller must close the generator to stop the process.
    """
    info = probe(video_path)
    width = width or info["width"]
    height = height or info["height"]
    proc = subprocess.Popen(
        [required("ffmpeg"), "-hide_banner", "-loglevel", "error", "-nostdin",
         "-i", str(video_path), "-vf", f"fps={fps},scale={width}:{height}",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    frame_size = width * height * 3
    index = 0
    try:
        while True:
            chunk = proc.stdout.read(frame_size) if proc.stdout else b""
            if len(chunk) < frame_size:
                break
            yield index / fps, chunk, width, height
            index += 1
    finally:
        try:
            proc.kill()
        except Exception:
            pass
