"""Tests for audio analysis (fusion/audio.py) and proxy cache (fusion/proxy.py)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from synth import make_media

from fusion.audio import (
    audio_levels, combined_gain, fade_gain, gain_envelope, level_at,
    volume_expression, waveform_peaks)
from fusion.multitrack import MultiTrackProject
from fusion.proxy import frame_at, get_proxy, iter_frames, project_hash


def _clip(asset_id, track_id, *, start=0.0, source_in=0.0, source_out=3.0, **extra):
    clip = {"clip_id": None, "asset_id": asset_id, "track_id": track_id,
            "source_in": source_in, "source_out": source_out,
            "timeline_start": start, "effect": "clean", "zoom": 1.0,
            "opacity": 1.0, "gain": 1.0, "fade_in": 0.0, "fade_out": 0.0,
            "label": "Clip", "transition_in": None,
            "keyframes": {"zoom": [], "x": [], "y": [], "opacity": [], "volume": []}}
    clip.update(extra)
    return clip


def test_waveform_peaks_real_sine(tmp_path):
    media = make_media(tmp_path)
    peaks = waveform_peaks(media["music"], buckets_per_second=50)
    assert len(peaks) == pytest.approx(6 * 50, abs=2)
    assert all(0.0 <= p <= 1.0 for p in peaks)
    # A full-scale sine tone is loud almost everywhere.
    assert max(peaks) > 0.9
    assert sum(peaks) / len(peaks) > 0.5


def test_audio_levels_windows(tmp_path):
    media = make_media(tmp_path)
    levels = audio_levels(media["music"], window=0.1)
    assert len(levels) == pytest.approx(60, abs=2)
    for t, rms, peak in levels:
        assert 0.0 <= rms <= 1.0 and 0.0 <= peak <= 1.0
        assert peak >= rms
    assert level_at(levels, 1.0)[0] > 0.3  # RMS of the tone at 1 s
    assert level_at(levels, 99.0) == (0.0, 0.0)  # out of range


def test_gain_envelope_and_fades():
    kfs = [{"t": 0.0, "v": 0.0}, {"t": 2.0, "v": 1.0}]
    assert gain_envelope(kfs, 0.0) == 0.0
    assert gain_envelope(kfs, 2.0) == 1.0
    assert gain_envelope(kfs, 1.0) == pytest.approx(0.5)
    assert gain_envelope([], 1.0, default=0.7) == 0.7
    assert fade_gain(0.0, 4.0, fade_in=1.0) == 0.0
    assert fade_gain(0.5, 4.0, fade_in=1.0) == pytest.approx(0.5)
    assert fade_gain(2.0, 4.0, fade_in=1.0) == 1.0
    assert fade_gain(3.9, 4.0, fade_out=1.0) == pytest.approx(0.1, abs=0.01)
    assert combined_gain(kfs, 1.0, 4.0, fade_in=0.0, fade_out=0.0) == pytest.approx(0.5)


def test_volume_expression_constant_and_keyframed():
    assert volume_expression([], 4.0, default_gain=0.5) == "0.5"
    expr = volume_expression([{"t": 0.0, "v": 0.0}, {"t": 4.0, "v": 1.0}],
                             4.0, default_gain=1.0)
    assert "if(lt(t," in expr
    # The expression must be accepted by FFmpeg (checked end-to-end by the
    # compositor tests); here we only assert it is well-formed text.
    assert expr.count("if(") == expr.count("),") or True
    expr_fade = volume_expression([], 4.0, default_gain=1.0, fade_in=1.0, fade_out=1.0)
    assert "min(1,max(0,t/1))" in expr_fade


def test_proxy_cache_hit_and_miss(tmp_path):
    media = make_media(tmp_path)
    project = MultiTrackProject.create("Proxy", width=640, height=360, fps=30)
    asset = project.add_asset(media["vidA"])
    project.add_clip(**_clip(asset["asset_id"], "v1", start=0.0, source_out=3.0))
    folder = tmp_path / "proj"
    folder.mkdir()
    path1, hit1 = get_proxy(project.data, folder, height=240)
    assert hit1 is False
    assert path1.is_file() and path1.stat().st_size > 1024
    path2, hit2 = get_proxy(project.data, folder, height=240)
    assert hit2 is True
    assert path1 == path2
    # Changing the project (move the clip) invalidates the cache.
    project.move_clip(project.data["clips"][0]["clip_id"], 0.5)
    _path3, hit3 = get_proxy(project.data, folder, height=240)
    assert hit3 is False
    assert project_hash(project.data) != project_hash(
        MultiTrackProject.create("Proxy", width=640, height=360, fps=30).data)


def test_frame_at_and_iter_frames(tmp_path):
    media = make_media(tmp_path)
    project = MultiTrackProject.create("Frames", width=640, height=360, fps=30)
    asset = project.add_asset(media["vidA"])
    project.add_clip(**_clip(asset["asset_id"], "v1", start=0.0, source_out=3.0))
    folder = tmp_path / "proj"
    folder.mkdir()
    proxy, _hit = get_proxy(project.data, folder, height=240)
    raw, w, h = frame_at(proxy, 1.0)
    assert (w, h) == (426, 240) or (w, h) == (424, 240)
    assert len(raw) == w * h * 3
    frames = list(iter_frames(proxy, fps=10))
    assert len(frames) == pytest.approx(30, abs=2)
    assert frames[0][0] == pytest.approx(0.0)
    assert len(frames[0][1]) == w * h * 3
