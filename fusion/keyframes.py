"""Keyframe evaluation for the multitrack engine.

Keyframes are stored as plain JSON lists of {"t": seconds, "v": value,
"easing": "linear"|"ease_in"|"ease_out"|"ease_in_out"|"hold"} where "t" is
relative to the clip start (0..clip duration). Evaluation is piecewise
linear with easing applied inside each segment. Nothing here touches
FFmpeg: the compositor translates evaluated keyframes into filter
expressions or constant segments (see fusion/compositor.py).
"""
from __future__ import annotations

import math

EASINGS = ("linear", "ease_in", "ease_out", "ease_in_out", "hold")


def _ease(kind, x):
    if kind == "ease_in":
        return x * x
    if kind == "ease_out":
        return 1 - (1 - x) * (1 - x)
    if kind == "ease_in_out":
        return 2 * x * x if x < 0.5 else 1 - (-2 * x + 2) ** 2 / 2
    if kind == "hold":
        return 0.0
    return x


def validate_keyframes(raw, *, minimum, maximum, duration, label):
    """Canonicalize a keyframe list; raises ValueError on bad data."""
    if raw is None:
        return []
    if not isinstance(raw, list) or len(raw) > 64:
        raise ValueError(f"{label}: se requieren entre 0 y 64 keyframes.")
    out = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError(f"{label}: keyframe inválido.")
        t = item.get("t")
        v = item.get("v")
        easing = item.get("easing", "linear")
        if isinstance(t, bool) or isinstance(v, bool):
            raise ValueError(f"{label}: valores booleanos inválidos.")
        try:
            t = float(t)
            v = float(v)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{label}: tiempo y valor deben ser números.") from exc
        if not (math.isfinite(t) and math.isfinite(v)):
            raise ValueError(f"{label}: valores no finitos.")
        if not 0 <= t <= duration + 0.001:
            raise ValueError(f"{label}: keyframe fuera del clip (t={t}).")
        if not minimum <= v <= maximum:
            raise ValueError(f"{label}: valor {v} fuera de rango {minimum}–{maximum}.")
        if easing not in EASINGS:
            raise ValueError(f"{label}: easing desconocido: {easing}.")
        out.append({"t": round(t, 4), "v": round(v, 4), "easing": easing})
    out.sort(key=lambda k: k["t"])
    # Two keyframes at the same time: keep the last one (a step).
    dedup = []
    for kf in out:
        if dedup and dedup[-1]["t"] == kf["t"]:
            dedup[-1] = kf
        else:
            dedup.append(kf)
    return dedup


def evaluate(keyframes, t, *, default):
    """Value of a keyframe track at relative time t (seconds)."""
    if not keyframes:
        return default
    if t <= keyframes[0]["t"]:
        return keyframes[0]["v"]
    if t >= keyframes[-1]["t"]:
        return keyframes[-1]["v"]
    for a, b in zip(keyframes, keyframes[1:]):
        if a["t"] <= t <= b["t"]:
            span = b["t"] - a["t"]
            if span <= 0:
                return b["v"]
            x = (t - a["t"]) / span
            return a["v"] + (b["v"] - a["v"]) * _ease(a.get("easing", "linear"), x)
    return keyframes[-1]["v"]


def sample(keyframes, start, end, step, *, default):
    """Sample the track every `step` seconds; returns [(t, value), ...]."""
    if step <= 0:
        raise ValueError("El paso de muestreo debe ser positivo.")
    points = []
    t = start
    while t < end:
        points.append((round(t, 4), round(evaluate(keyframes, t - start, default=default), 4)))
        t += step
    points.append((round(end, 4), round(evaluate(keyframes, end - start, default=default), 4)))
    return points


def constant_segments(keyframes, start, end, step, *, default):
    """Split [start, end] into constant-value segments for filters that
    cannot evaluate expressions over time (e.g. colorchannelmixer `aa`).

    Returns a list of (seg_start, seg_end, value) with no gaps. Adjacent
    segments with the same value are merged.
    """
    points = sample(keyframes, start, end, step, default=default)
    segments = []
    for (t0, v0), (t1, _v1) in zip(points, points[1:]):
        if t1 - t0 < 0.001:
            continue
        if segments and segments[-1][2] == v0 and abs(segments[-1][1] - t0) < 0.001:
            segments[-1] = (segments[-1][0], t1, v0)
        else:
            segments.append((t0, t1, v0))
    if not segments and end > start:
        segments.append((start, end, evaluate(keyframes, 0, default=default)))
    return segments


def ffmpeg_number(value):
    """Format a float for an FFmpeg expression (no exponent, dot decimal)."""
    text = f"{float(value):.6f}".rstrip("0").rstrip(".")
    return text if text not in ("", "-0") else "0"
