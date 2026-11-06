"""Multitrack compositor — FFmpeg filtergraph builder + renderer.

The compositor turns a validated v3 project (``fusion/multitrack``)
into a single FFmpeg ``filter_complex`` invocation. Design notes:

- One ``-i`` per clip (even when clips share an asset): trivially
  correct, matches the existing ``engine.py`` pattern, and keeps the
  graph generator simple. The practical limit is the OS argument list;
  projects are capped at 200 clips by the model.
- Every video clip is normalized to the canvas (scale + pad, ``fps``)
  before effects, so mixed resolutions/FPS compose correctly.
- Video tracks keep timeline gaps: clips are joined with ``xfade``
  (crossfade) or ``concat`` (hard cut), and gaps are filled with black
  segments from a ``color`` source — a track stream always spans its
  full timeline range.
- Audio is never concatenated: every audio clip is delayed to its
  timeline position (``adelay``) and all streams meet in one ``amix``
  (``normalize=0``), so gaps and overlaps stay time-correct.
  Crossfades in audio are triangular fades at the overlap
  (``afade`` out on the outgoing clip, ``afade`` in on the incoming
  one) summed by the mixer — the same curve ``acrossfade`` uses.
- Transform keyframes: zoom via ``scale`` with ``eval=frame`` and a
  piecewise-linear expression in ``t``; pan via ``crop`` x/y expressions
  (both verified in dexter). Opacity keyframes use constant segments
  (``colorchannelmixer=aa`` cannot evaluate ``t`` — see
  ``docs/ENGINE_COMPARISON.md``).
- Video fades are fades to black (``fade`` filter), which is identical
  to an alpha fade over the black base canvas. Image overlays use real
  alpha.
- The legacy v2 path (``engine.export_plan``) is untouched; this module
  is the v3 render path.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .audio import volume_expression
from .engine import EFFECTS
from .keyframes import constant_segments, evaluate, ffmpeg_number
from .media import probe, required, run
from .multitrack import _clip_duration, missing_assets, project_duration, validate_project

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def detect_encoders():
    """Return the set of encoder names this ffmpeg exposes."""
    try:
        out = subprocess.run(
            [required("ffmpeg"), "-hide_banner", "-encoders"],
            capture_output=True, text=True, timeout=30).stdout
    except Exception:
        return set()
    names = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0].startswith(("V", "A", "S")):
            names.add(parts[1])
    return names


def _escape_filter_text(text):
    return (str(text).replace("\\", "\\\\").replace(":", "\\:")
            .replace("'", "\\'").replace("[", "\\[").replace("]", "\\]")
            .replace(";", "\\;").replace(",", "\\,").replace("\n", " "))


def _piecewise_expr(keyframes, duration, *, default, time_var="t"):
    """FFmpeg expression for a piecewise-linear keyframe track.

    ``t`` in the expression is the time variable; pass ``time_var`` to
    shift it (e.g. "(t-2.5)" when the filter's clock is timeline time
    but the keyframes are relative to a clip starting at 2.5 s).
    """
    points = [(0.0, float(default))]
    for kf in keyframes or []:
        points.append((float(kf["t"]), float(kf["v"])))
    points.append((float(duration), float(keyframes[-1]["v"]) if keyframes else float(default)))
    dedup = [points[0]]
    for p in points[1:]:
        if abs(p[1] - dedup[-1][1]) > 1e-9 or p[0] in (0.0, float(duration)):
            dedup.append(p)
    points = dedup
    if len(points) <= 2 and all(abs(p[1] - points[0][1]) < 1e-9 for p in points):
        expr = ffmpeg_number(points[0][1])
    else:
        expr = ffmpeg_number(points[-1][1])
        for (t0, v0), (t1, v1) in reversed(list(zip(points, points[1:]))):
            if t1 - t0 < 1e-6:
                continue
            slope = (v1 - v0) / (t1 - t0)
            seg = f"({ffmpeg_number(v0)}+{ffmpeg_number(slope)}*(t-{ffmpeg_number(t0)}))"
            expr = f"if(lt(t,{ffmpeg_number(t1)}),{seg},{expr})"
    if time_var != "t":
        expr = re.sub(r"\bt\b", f"({time_var})", expr)
    return expr


class _Graph:
    def __init__(self):
        self.inputs = []          # list of argv chunks per input
        self.filters = []         # filter_complex nodes
        self.counter = 0

    def label(self, prefix="n"):
        self.counter += 1
        return f"[{prefix}{self.counter}]"

    def add(self, text):
        self.filters.append(text)


def _normalize_video(graph, in_label, clip, canvas, duration):
    """trim/scale/pad/fps/effect/zoom-pan/fades for one video clip."""
    width, height, fps = canvas["width"], canvas["height"], canvas["fps"]
    out = graph.label("v")
    parts = [f"{in_label}trim=start={clip['source_in']:.3f}:end={clip['source_out']:.3f}",
             "setpts=PTS-STARTPTS",
             f"scale={width}:{height}:force_original_aspect_ratio=decrease:flags=lanczos",
             f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,setsar=1",
             f"fps={fps}",
             "format=yuv420p"]
    effect = EFFECTS.get(clip.get("effect", "clean"), EFFECTS["clean"])["filter"]
    if effect != "null":
        parts.append(effect)
    keyframes = clip.get("keyframes") or {}
    zoom_kf = keyframes.get("zoom") or []
    x_kf = keyframes.get("x") or []
    y_kf = keyframes.get("y") or []
    zoom = float(clip.get("zoom", 1.0))
    if zoom_kf or zoom > 1.001:
        zoom_expr = (_piecewise_expr(zoom_kf, duration, default=zoom)
                     if zoom_kf else ffmpeg_number(zoom))
        parts.append(f"scale=w='iw*({zoom_expr})':h='ih*({zoom_expr})':eval=frame")
        x_expr = (_piecewise_expr(x_kf, duration, default=0.5)
                  if x_kf else "0.5")
        y_expr = (_piecewise_expr(y_kf, duration, default=0.5)
                  if y_kf else "0.5")
        parts.append(
            f"crop={width}:{height}:x='(in_w-{width})*({x_expr})'"
            f":y='(in_h-{height})*({y_expr})'")
        parts.append(f"scale={width}:{height}:flags=lanczos,format=yuv420p")
    fade_in = float(clip.get("fade_in", 0.0))
    fade_out = float(clip.get("fade_out", 0.0))
    if fade_in > 0:
        parts.append(f"fade=t=in:st=0:d={fade_in:.3f}")
    if fade_out > 0:
        parts.append(f"fade=t=out:st={max(0.0, duration - fade_out):.3f}:d={fade_out:.3f}")
    graph.add(",".join(parts) + out)
    return out


def _clip_audio(graph, in_label, clip, duration, *, fade_in_extra=0.0, fade_out_extra=0.0):
    """Audio branch for one clip: trim, gain envelope, fades, delay.

    ``fade_in_extra``/``fade_out_extra`` add the transition fades of a
    crossfade/fade transition (triangular, summed later by ``amix``).
    """
    out = graph.label("a")
    expr = volume_expression(clip.get("keyframes", {}).get("volume") or [],
                             duration, default_gain=float(clip.get("gain", 1.0)),
                             fade_in=float(clip.get("fade_in", 0.0)),
                             fade_out=float(clip.get("fade_out", 0.0)))
    parts = [f"{in_label}atrim=start={clip['source_in']:.3f}:end={clip['source_out']:.3f}",
             "asetpts=PTS-STARTPTS",
             f"volume='{expr}':eval=frame"]
    if fade_in_extra > 0:
        parts.append(f"afade=t=in:st=0:d={fade_in_extra:.3f}")
    if fade_out_extra > 0:
        parts.append(f"afade=t=out:st={max(0.0, duration - fade_out_extra):.3f}"
                     f":d={fade_out_extra:.3f}")
    delay_ms = int(round(float(clip["timeline_start"]) * 1000))
    parts.append(f"adelay={delay_ms}:all=1")
    graph.add(",".join(parts) + out)
    return out


def _black_segment(graph, canvas, duration):
    out = graph.label("v")
    graph.add(f"color=c=black:s={canvas['width']}x{canvas['height']}"
              f":r={canvas['fps']}:d={duration:.3f}{out}")
    return out


def _build_video_track(graph, clips, canvas, total):
    """Assemble one video track into a full-timeline stream.

    Returns the label of a stream of exactly `total` seconds. Gaps are
    black; consecutive clips join with xfade (crossfade) or concat.
    """
    width, height, fps = canvas["width"], canvas["height"], canvas["fps"]
    label = None
    cursor = 0.0  # timeline position covered so far by `label`
    for i, clip in enumerate(clips):
        dur = _clip_duration(clip)
        idx = clip["_input"]
        seg = _normalize_video(graph, f"[{idx}:v]", clip, canvas, dur)
        start = clip["timeline_start"]
        transition = clip.get("transition_in")
        if label is None:
            if start > 0.001:
                label = _black_segment(graph, canvas, start)
                cursor = start
                out = graph.label("v")
                graph.add(f"{label}{seg}concat=n=2:v=1:a=0{out}")
                label, cursor = out, start + dur
            else:
                label, cursor = seg, dur
            continue
        gap = start - cursor
        if gap > 0.001:
            # Gap: black segment, then concat the new clip.
            blk = _black_segment(graph, canvas, gap)
            out = graph.label("v")
            graph.add(f"{label}{blk}concat=n=2:v=1:a=0{out}")
            label, cursor = out, cursor + gap
            out2 = graph.label("v")
            graph.add(f"{label}{seg}concat=n=2:v=1:a=0{out2}")
            label, cursor = out2, cursor + dur
        elif transition and transition.get("type") == "crossfade":
            d = float(transition["duration"])
            offset = max(0.0, cursor - d)
            out = graph.label("v")
            graph.add(f"{label}{seg}xfade=transition=fade:duration={d:.3f}"
                      f":offset={offset:.3f}{out}")
            label, cursor = out, cursor + dur - d
        elif transition and transition.get("type") == "fade":
            d = float(transition["duration"])
            prev = graph.label("v")
            graph.add(f"{label}fade=t=out:st={max(0.0, cursor - d):.3f}:d={d:.3f}{prev}")
            nxt = graph.label("v")
            graph.add(f"{seg}fade=t=in:st=0:d={d:.3f}{nxt}")
            out = graph.label("v")
            graph.add(f"{prev}{nxt}concat=n=2:v=1:a=0{out}")
            label, cursor = out, cursor + dur
        else:
            out = graph.label("v")
            graph.add(f"{label}{seg}concat=n=2:v=1:a=0{out}")
            label, cursor = out, cursor + dur
    if cursor < total - 0.001:
        blk = _black_segment(graph, canvas, total - cursor)
        out = graph.label("v")
        graph.add(f"{label}{blk}concat=n=2:v=1:a=0{out}")
        label = out
    # Exact length + fresh timestamps.
    out = graph.label("v")
    graph.add(f"{label}trim=0:{total:.3f},setpts=PTS-STARTPTS{out}")
    return out


def build_filtergraph(project):
    """Build (inputs, filter_complex, video_label, audio_label, duration).

    ``inputs`` is a list of argv lists, one per ``-i`` (loop inputs for
    images carry their own ``-loop``/``-t`` flags).
    """
    project = validate_project(project)
    missing = missing_assets(project)
    if missing:
        names = ", ".join(a["path"] for a in missing)
        raise FileNotFoundError(f"Assets no encontrados, repara el proyecto: {names}")
    canvas = project["canvas"]
    width, height, fps = canvas["width"], canvas["height"], canvas["fps"]
    total = project_duration(project)
    if total <= 0:
        raise ValueError("El proyecto no tiene clips que renderizar.")
    assets = {a["asset_id"]: a for a in project["assets"]}
    tracks = {t["track_id"]: t for t in project["tracks"]}
    graph = _Graph()
    # One input per clip (video clips need the input once: [i:v] + [i:a]).
    for clip in project["clips"]:
        if tracks[clip["track_id"]]["kind"] == "text":
            continue
        asset = assets[clip["asset_id"]]
        index = len(graph.inputs)
        if asset["kind"] == "image":
            dur = _clip_duration(clip)
            graph.inputs.append(["-loop", "1", "-t", f"{dur:.3f}", "-i", asset["path"]])
        else:
            graph.inputs.append(["-i", asset["path"]])
        clip["_input"] = index

    video_track_streams = []  # (track_index, label) in stacking order
    audio_streams = []
    for track in sorted(project["tracks"], key=lambda t: t["index"]):
        if track.get("muted"):
            continue
        clips = sorted((c for c in project["clips"] if c["track_id"] == track["track_id"]),
                       key=lambda c: c["timeline_start"])
        if not clips:
            continue
        if track["kind"] == "video":
            stream = _build_video_track(graph, clips, canvas, total)
            video_track_streams.append((track["index"], stream))
            # Video-clip audio follows the video (V1/A1 behaviour): one
            # delayed stream per clip; crossfades become triangular fades.
            for j, clip in enumerate(clips):
                asset = assets[clip["asset_id"]]
                if not asset.get("has_audio"):
                    continue
                dur = _clip_duration(clip)
                fade_in = fade_out = 0.0
                if clip.get("transition_in") is not None:
                    fade_in = float(clip["transition_in"]["duration"])
                if j + 1 < len(clips) and clips[j + 1].get("transition_in") is not None:
                    fade_out = float(clips[j + 1]["transition_in"]["duration"])
                audio_streams.append(_clip_audio(
                    graph, f"[{clip['_input']}:a]", clip, dur,
                    fade_in_extra=fade_in, fade_out_extra=fade_out))
        elif track["kind"] == "audio":
            for j, clip in enumerate(clips):
                dur = _clip_duration(clip)
                fade_in = fade_out = 0.0
                if clip.get("transition_in") is not None:
                    fade_in = float(clip["transition_in"]["duration"])
                if j + 1 < len(clips) and clips[j + 1].get("transition_in") is not None:
                    fade_out = float(clips[j + 1]["transition_in"]["duration"])
                audio_streams.append(_clip_audio(
                    graph, f"[{clip['_input']}:a]", clip, dur,
                    fade_in_extra=fade_in, fade_out_extra=fade_out))
        # image/text tracks are composited later, directly on the base.

    # --- base canvas + video track stacking
    base = graph.label("v")
    graph.add(f"color=c=black:s={width}x{height}:r={fps}:d={total:.3f}{base}")
    current = base
    for _index, stream in sorted(video_track_streams):
        out = graph.label("v")
        graph.add(f"{current}{stream}overlay=0:0:format=yuv420{out}")
        current = out

    # --- image tracks: overlay per clip, opacity keyframes as segments
    for track in sorted(project["tracks"], key=lambda t: t["index"]):
        if track["kind"] != "image" or track.get("muted"):
            continue
        clips = sorted((c for c in project["clips"] if c["track_id"] == track["track_id"]),
                       key=lambda c: c["timeline_start"])
        for clip in clips:
            idx = clip["_input"]
            dur = _clip_duration(clip)
            start = clip["timeline_start"]
            rel_w = float(clip.get("width", 0.24))
            keyframes = clip.get("keyframes") or {}
            x_kf = keyframes.get("x") or []
            y_kf = keyframes.get("y") or []
            opacity_kf = keyframes.get("opacity") or []
            opacity = float(clip.get("opacity", 1.0))
            x_expr = (_piecewise_expr(x_kf, dur, default=0.5,
                                      time_var=f"t-{start:.3f}")
                      if x_kf else "0.5")
            y_expr = (_piecewise_expr(y_kf, dur, default=0.5,
                                      time_var=f"t-{start:.3f}")
                      if y_kf else "0.5")
            segments = constant_segments(opacity_kf, 0.0, dur, 0.25, default=opacity)
            for s0, s1, op in segments:
                img = graph.label("v")
                graph.add(f"[{idx}:v]scale={int(width * rel_w)}:-2:flags=lanczos,"
                          f"format=rgba,colorchannelmixer=aa={ffmpeg_number(op)}{img}")
                out = graph.label("v")
                graph.add(f"{current}{img}overlay="
                          f"x='(W-w)*({x_expr})':y='(H-h)*({y_expr})'"
                          f":enable='between(t,{start + s0:.3f},{start + s1:.3f})'{out}")
                current = out

    # --- text tracks: drawtext (static position; fade via enable window)
    for track in sorted(project["tracks"], key=lambda t: t["index"]):
        if track["kind"] != "text" or track.get("muted"):
            continue
        clips = sorted((c for c in project["clips"] if c["track_id"] == track["track_id"]),
                       key=lambda c: c["timeline_start"])
        for clip in clips:
            dur = _clip_duration(clip)
            start = clip["timeline_start"]
            text = _escape_filter_text(clip.get("text") or clip.get("label") or "")
            if not text:
                continue
            keyframes = clip.get("keyframes") or {}
            x = evaluate(keyframes.get("x") or [], 0, default=0.5)
            y = evaluate(keyframes.get("y") or [], 0, default=0.5)
            fontsize = max(12, int(height * 0.06))
            out = graph.label("v")
            graph.add(f"{current}drawtext=fontfile={FONT}:text='{text}'"
                      f":fontsize={fontsize}:fontcolor=white:borderw=2:bordercolor=black"
                      f":x=(w-text_w)*{ffmpeg_number(x)}:y=(h-text_h)*{ffmpeg_number(y)}"
                      f":enable='between(t,{start:.3f},{start + dur:.3f})'{out}")
            current = out

    # --- audio mix
    if audio_streams:
        if len(audio_streams) == 1:
            audio_label = audio_streams[0]
        else:
            audio_label = graph.label("a")
            graph.add(f"{''.join(audio_streams)}amix=inputs={len(audio_streams)}"
                      f":duration=longest:dropout_transition=0:normalize=0{audio_label}")
        trimmed = graph.label("a")
        graph.add(f"{audio_label}atrim=0:{total:.3f},asetpts=PTS-STARTPTS{trimmed}")
        audio_label = trimmed
    else:
        audio_label = graph.label("a")
        graph.add(f"anullsrc=r=48000:cl=stereo,atrim=0:{total:.3f},asetpts=PTS-STARTPTS{audio_label}")

    for clip in project["clips"]:
        clip.pop("_input", None)
    return {"inputs": graph.inputs,
            "filter_complex": ";".join(graph.filters),
            "video": current, "audio": audio_label,
            "duration": total, "width": width, "height": height}


def render(project, output, *, overwrite=False, preset="veryfast", crf=21,
           use_nvenc=False, width=None, height=None, fps=None):
    """Render a v3 project to MP4; returns (output_path, probe_dict).

    Raises FileNotFoundError (missing assets), ValueError (bad project)
    or RuntimeError (ffmpeg failed / output invalid). The output is
    verified with ffprobe before returning.
    """
    project = validate_project(project)
    if width is not None or height is not None or fps is not None:
        project = dict(project)
        project["canvas"] = {"width": width or project["canvas"]["width"],
                             "height": height or project["canvas"]["height"],
                             "fps": fps or project["canvas"]["fps"]}
        project = validate_project(project)
    output = Path(output)
    if output.exists() and not overwrite:
        raise FileExistsError(f"Ya existe la exportación: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    graph = build_filtergraph(project)
    encoders = detect_encoders() if use_nvenc else set()
    if use_nvenc and "h264_nvenc" in encoders:
        vcodec = ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", str(crf)]
    else:
        if use_nvenc:
            raise RuntimeError("NVENC no disponible en este ffmpeg; usa CPU (libx264).")
        vcodec = ["-c:v", "libx264", "-preset", preset, "-crf", str(crf)]
    exe = required("ffmpeg")
    cmd = [exe, "-hide_banner", "-loglevel", "error", "-nostdin", "-y"]
    for argv in graph["inputs"]:
        cmd += argv
    cmd += ["-filter_complex", graph["filter_complex"],
            "-map", graph["video"], "-map", graph["audio"],
            "-t", f"{graph['duration']:.3f}"] + vcodec + [
            "-pix_fmt", "yuv420p", "-r", str(project["canvas"]["fps"]),
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(output)]
    run(cmd)
    info = probe(output)
    if output.stat().st_size <= 1024 or info["duration"] <= 0:
        raise RuntimeError("Exportación inválida: salida vacía o sin duración.")
    if abs(info["duration"] - graph["duration"]) > 0.6:
        raise RuntimeError(
            f"Duración inesperada: ffprobe {info['duration']:.2f}s frente a "
            f"esperados {graph['duration']:.2f}s.")
    return output, info
