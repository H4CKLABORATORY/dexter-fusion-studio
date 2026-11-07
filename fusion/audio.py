"""Real audio analysis for the multitrack engine.

Everything here is computed from decoded PCM — no decorative waveforms.
Only the standard library is used (``array``, ``math``, ``struct``);
numpy is deliberately NOT a runtime dependency of the app.

- ``waveform_peaks``: peak amplitude per time bucket (what the timeline
  draws). Decodes with FFmpeg to 8 kHz mono s16le, bounded memory.
- ``audio_levels``: RMS + peak per window (what the meter widget shows).
- ``gain_envelope`` / ``fade_gain``: pure math for gain envelopes and
  fades, shared by the UI preview and the tests.
- ``volume_expression``: translates gain keyframes into an FFmpeg
  ``volume`` filter expression (``eval=frame``), verified in dexter.
"""
from __future__ import annotations

import array
import math
import subprocess

from .keyframes import evaluate, ffmpeg_number
from .media import required


def _decode_mono(path, *, sample_rate=8000, limit_seconds=1800):
    """Decode audio to mono s16le samples; returns (samples, rate)."""
    exe = required("ffmpeg")
    result = subprocess.run(
        [exe, "-hide_banner", "-loglevel", "error", "-nostdin", "-i", str(path),
         "-vn", "-ac", "1", "-ar", str(sample_rate),
         "-t", str(limit_seconds), "-f", "s16le", "pipe:1"],
        capture_output=True, timeout=120)
    if result.returncode:
        raise RuntimeError(f"No se pudo decodificar el audio: {path}")
    values = array.array("h")
    values.frombytes(result.stdout[:len(result.stdout) // 2 * 2])
    return values, sample_rate


def waveform_peaks(path, *, buckets_per_second=50, limit_seconds=1800):
    """Peak amplitude (0..1) per bucket across the whole file.

    ``buckets_per_second`` controls the timeline resolution: 50 buckets/s
    is enough to draw a faithful waveform without storing the raw audio.
    """
    values, rate = _decode_mono(path, sample_rate=8000, limit_seconds=limit_seconds)
    if not values:
        return []
    per_bucket = max(1, rate // buckets_per_second)
    peaks = []
    for i in range(0, len(values), per_bucket):
        chunk = values[i:i + per_bucket]
        peaks.append(min(1.0, max(abs(s) for s in chunk) / 32768.0))
    return peaks


def audio_levels(path, *, window=0.1, limit_seconds=1800):
    """[(time, rms, peak), ...] one entry per `window` seconds.

    RMS is computed on normalized float samples; peak is the max absolute
    sample in the window. Silent windows report (t, 0.0, 0.0).
    """
    values, rate = _decode_mono(path, sample_rate=8000, limit_seconds=limit_seconds)
    if not values:
        return []
    per_window = max(1, int(rate * window))
    levels = []
    for i in range(0, len(values), per_window):
        chunk = values[i:i + per_window]
        if not chunk:
            continue
        squares = sum((s / 32768.0) ** 2 for s in chunk) / len(chunk)
        rms = math.sqrt(squares)
        peak = max(abs(s) for s in chunk) / 32768.0
        levels.append((round(i / rate, 3), round(rms, 4), round(peak, 4)))
    return levels


def level_at(levels, t):
    """(rms, peak) of the window containing time t; (0, 0) if out of range."""
    if not levels:
        return (0.0, 0.0)
    window = levels[1][0] - levels[0][0] if len(levels) > 1 else 0.1
    index = int(t // window) if window > 0 else 0
    if 0 <= index < len(levels):
        return (levels[index][1], levels[index][2])
    return (0.0, 0.0)


def gain_envelope(keyframes, t, *, default=1.0):
    """Gain multiplier at relative time t from gain keyframes."""
    return evaluate(keyframes, t, default=default)


def fade_gain(t, duration, *, fade_in=0.0, fade_out=0.0):
    """Linear fade multiplier: 0→1 over fade_in, 1→0 over fade_out."""
    gain = 1.0
    if fade_in > 0 and t < fade_in:
        gain = min(gain, t / fade_in)
    if fade_out > 0 and t > duration - fade_out:
        gain = min(gain, max(0.0, (duration - t) / fade_out))
    return max(0.0, min(1.0, gain))


def combined_gain(keyframes, t, duration, *, default_gain=1.0, fade_in=0.0, fade_out=0.0):
    """Gain keyframes × clip gain × fades, at relative time t."""
    return (gain_envelope(keyframes, t, default=default_gain)
            * fade_gain(t, duration, fade_in=fade_in, fade_out=fade_out))


def volume_expression(keyframes, duration, *, default_gain=1.0, fade_in=0.0, fade_out=0.0):
    """Build an FFmpeg ``volume`` expression for a clip.

    The expression is evaluated per frame (``eval=frame``) and uses only
    FFmpeg expression functions (``if``/``lt``/``min``/``max``). Keyframes
    are piecewise-linear; fades multiply the envelope. A constant gain
    collapses to a plain number (no expression overhead).
    """
    points = [(0.0, default_gain)]
    for kf in keyframes or []:
        points.append((float(kf["t"]), float(kf["v"])))
    points.append((float(duration), float(keyframes[-1]["v"]) if keyframes else default_gain))
    # Deduplicate identical consecutive values.
    dedup = [points[0]]
    for p in points[1:]:
        if abs(p[1] - dedup[-1][1]) > 1e-9 or p[0] in (0.0, float(duration)):
            dedup.append(p)
    points = dedup
    if len(points) <= 2 and all(abs(p[1] - points[0][1]) < 1e-9 for p in points):
        base = points[0][1]
        if fade_in <= 0 and fade_out <= 0:
            return ffmpeg_number(base)
        expr = ffmpeg_number(base)
    else:
        # Piecewise linear: nested if(lt(t, t1), v0 + slope*(t - t0), ...).
        expr = ffmpeg_number(points[-1][1])
        for (t0, v0), (t1, v1) in reversed(list(zip(points, points[1:]))):
            if t1 - t0 < 1e-6:
                continue
            slope = (v1 - v0) / (t1 - t0)
            seg = f"({ffmpeg_number(v0)}+{ffmpeg_number(slope)}*(t-{ffmpeg_number(t0)}))"
            expr = f"if(lt(t,{ffmpeg_number(t1)}),{seg},{expr})"
    if fade_in > 0:
        expr = f"({expr})*min(1,max(0,t/{ffmpeg_number(fade_in)}))"
    if fade_out > 0:
        expr = (f"({expr})*min(1,max(0,({ffmpeg_number(duration)}-t)"
                f"/{ffmpeg_number(fade_out)}))")
    return expr
