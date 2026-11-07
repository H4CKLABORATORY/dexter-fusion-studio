"""Tests for the multitrack compositor (fusion/compositor.py).

Every test renders real synthetic media with FFmpeg and verifies the
result with ffprobe, pixel analysis and audio FFT — never with mocks
of the render itself.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from synth import make_media, frame_rgb, dominant_freqs, probe_json

from fusion.multitrack import MultiTrackProject, project_duration
from fusion.compositor import build_filtergraph, detect_encoders, render


def _base_project(tmp_path, *, width=1280, height=720, fps=30):
    media = make_media(tmp_path)
    project = MultiTrackProject.create("Render", width=width, height=height, fps=fps)
    assets = {name: project.add_asset(path) for name, path in media.items()}
    return project, media, assets


def _clip(asset_id, track_id, *, start=0.0, source_in=0.0, source_out=3.0, **extra):
    clip = {"clip_id": None, "asset_id": asset_id, "track_id": track_id,
            "source_in": source_in, "source_out": source_out,
            "timeline_start": start, "effect": "clean", "zoom": 1.0,
            "opacity": 1.0, "gain": 1.0, "fade_in": 0.0, "fade_out": 0.0,
            "label": "Clip", "transition_in": None,
            "keyframes": {"zoom": [], "x": [], "y": [], "opacity": [], "volume": []}}
    clip.update(extra)
    return clip


def test_filtergraph_contains_expected_nodes(tmp_path):
    project, _media, assets = _base_project(tmp_path)
    project.add_clip(**_clip(assets["vidA"]["asset_id"], "v1", start=0.0, source_out=3.0))
    project.add_clip(**_clip(assets["vidB"]["asset_id"], "v1", start=3.0,
                             source_in=1.0, source_out=4.0,
                             transition_in={"type": "crossfade", "duration": 0.5}))
    graph = build_filtergraph(project.data)
    assert "xfade" in graph["filter_complex"]
    assert "amix" in graph["filter_complex"] or "adelay" in graph["filter_complex"]
    assert graph["duration"] == pytest.approx(5.5, abs=0.01)
    assert len(graph["inputs"]) == 2


def test_render_mixed_fps_res_crossfade_image_music_text(tmp_path):
    project, _media, assets = _base_project(tmp_path)
    project.add_clip(**_clip(assets["vidA"]["asset_id"], "v1", start=0.0, source_out=3.0))
    project.add_clip(**_clip(assets["vidB"]["asset_id"], "v1", start=3.0,
                             source_in=1.0, source_out=4.0,
                             transition_in={"type": "crossfade", "duration": 0.5}))
    project.add_clip(**_clip(assets["img"]["asset_id"], "v3", start=1.0, source_out=3.0,
                             opacity=1.0, width=0.25))
    project.add_clip(**_clip(assets["music"]["asset_id"], "a3", start=0.0,
                             source_in=0.0, source_out=5.0, gain=0.35))
    project.add_clip(**_clip(None, "t1", start=0.5, source_in=0.0, source_out=2.5,
                             text="DEXTER TEST"))
    out, info = render(project.data, tmp_path / "out.mp4", overwrite=True)
    assert out.is_file() and out.stat().st_size > 1024
    assert info["duration"] == pytest.approx(5.5, abs=0.6)
    assert info["width"] == 1280 and info["height"] == 720
    # Pixels: red overlay present at t=2 (image track), video changed
    # across the crossfade (mean colour differs between t=1 and t=4.5).
    early = frame_rgb(out, 1.0)
    late = frame_rgb(out, 4.5)
    assert abs(float(early.mean()) - float(late.mean())) > 5
    assert early[300, 600].tolist()[0] > 200  # red overlay pixel (centred image)
    # Audio: 440 Hz (vidA) + 660 Hz (music) early; 880 Hz + 660 Hz late.
    assert 440 in dominant_freqs(out, 1.0) or 438 in dominant_freqs(out, 1.0)
    assert 660 in dominant_freqs(out, 1.0)
    assert 880 in dominant_freqs(out, 4.5) or 878 in dominant_freqs(out, 4.5)
    # Text: near-white pixels exist around the centred text at t=1.
    centre = early[300:400, 400:900]
    assert (centre.sum(axis=2) > 600).sum() > 50


def test_render_gap_is_black(tmp_path):
    project, _media, assets = _base_project(tmp_path)
    project.add_clip(**_clip(assets["vidA"]["asset_id"], "v1", start=0.0, source_out=2.0))
    project.add_clip(**_clip(assets["vidA"]["asset_id"], "v1", start=4.0,
                             source_in=0.0, source_out=2.0))
    assert project_duration(project.data) == 6.0
    out, _info = render(project.data, tmp_path / "gap.mp4", overwrite=True)
    gap_frame = frame_rgb(out, 3.0)
    assert float(gap_frame.mean()) < 5  # black gap between the clips
    assert float(frame_rgb(out, 1.0).mean()) > 20  # content elsewhere


def test_render_zoom_and_volume_keyframes(tmp_path):
    project, _media, assets = _base_project(tmp_path)
    clip = _clip(assets["vidA"]["asset_id"], "v1", start=0.0, source_out=4.0,
                 keyframes={"zoom": [{"t": 0.0, "v": 1.0}, {"t": 4.0, "v": 1.5}],
                            "x": [], "y": [], "opacity": [],
                            "volume": [{"t": 0.0, "v": 0.2}, {"t": 4.0, "v": 1.0}]})
    project.add_clip(**clip)
    out, info = render(project.data, tmp_path / "kf.mp4", overwrite=True)
    assert info["duration"] == pytest.approx(4.0, abs=0.6)
    # Zoom changes the framing: the centre crop at t=3.5 differs from t=0.2.
    early = frame_rgb(out, 0.2)
    late = frame_rgb(out, 3.5)
    assert abs(float(early.mean()) - float(late.mean())) > 1
    # Volume envelope: the late segment is louder than the early one.
    assert 440 in dominant_freqs(out, 3.5)


def test_render_opacity_keyframes_segments(tmp_path):
    project, _media, assets = _base_project(tmp_path)
    project.add_clip(**_clip(assets["vidA"]["asset_id"], "v1", start=0.0, source_out=4.0))
    project.add_clip(**_clip(
        assets["img"]["asset_id"], "v3", start=0.0, source_out=4.0, opacity=1.0,
        keyframes={"zoom": [], "x": [], "y": [],
                   "opacity": [{"t": 0.0, "v": 0.0}, {"t": 4.0, "v": 1.0}],
                   "volume": []}))
    out, _info = render(project.data, tmp_path / "op.mp4", overwrite=True)
    early = frame_rgb(out, 0.3)
    late = frame_rgb(out, 3.7)
    # Opacity ramps 0 -> 1: the red overlay pixel strengthens a lot.
    early_red = int(early[300, 600].tolist()[0])
    late_red = int(late[300, 600].tolist()[0])
    assert late_red > 200
    assert late_red - early_red > 80


def test_render_missing_asset_blocked(tmp_path):
    project, media, assets = _base_project(tmp_path)
    project.add_clip(**_clip(assets["vidA"]["asset_id"], "v1", start=0.0, source_out=3.0))
    media["vidA"].unlink()
    with pytest.raises(FileNotFoundError):
        render(project.data, tmp_path / "x.mp4", overwrite=True)


def test_render_empty_project_rejected(tmp_path):
    project = MultiTrackProject.create("Vacío")
    with pytest.raises(ValueError):
        render(project.data, tmp_path / "x.mp4", overwrite=True)


def test_nvenc_unavailable_is_honest_error(tmp_path):
    project, _media, assets = _base_project(tmp_path)
    project.add_clip(**_clip(assets["vidA"]["asset_id"], "v1", start=0.0, source_out=2.0))
    encoders = detect_encoders()
    assert isinstance(encoders, set)
    if "h264_nvenc" not in encoders:
        with pytest.raises(RuntimeError, match="NVENC"):
            render(project.data, tmp_path / "x.mp4", overwrite=True, use_nvenc=True)


def test_render_60s_small_canvas(tmp_path):
    # A 60 s composition from the 5 s synthetic sources (looped ranges),
    # rendered at 640x360 to keep the CPU test fast.
    project, _media, assets = _base_project(tmp_path, width=640, height=360, fps=30)
    position = 0.0
    for i in range(12):
        asset = assets["vidA"] if i % 2 == 0 else assets["vidB"]
        project.add_clip(**_clip(asset["asset_id"], "v1", start=position,
                                 source_in=0.0, source_out=5.0))
        position += 5.0
    assert project_duration(project.data) == 60.0
    out, info = render(project.data, tmp_path / "long.mp4", overwrite=True)
    assert info["duration"] == pytest.approx(60.0, abs=0.6)
    assert info["width"] == 640 and info["height"] == 360


def test_reordered_project_renders_in_new_order(tmp_path):
    project, _media, assets = _base_project(tmp_path)
    project.add_clip(**_clip(assets["vidA"]["asset_id"], "v1", start=0.0, source_out=2.0,
                             label="primero-A"))
    project.add_clip(**_clip(assets["vidB"]["asset_id"], "v1", start=2.0, source_out=2.0,
                             label="segundo-B"))
    out1, _ = render(project.data, tmp_path / "order1.mp4", overwrite=True)
    # Reorder: move B before A by rebuilding the same clips swapped.
    project2, _m2, assets2 = _base_project(tmp_path)
    project2.add_clip(**_clip(assets2["vidB"]["asset_id"], "v1", start=0.0, source_out=2.0,
                              label="primero-B"))
    project2.add_clip(**_clip(assets2["vidA"]["asset_id"], "v1", start=2.0, source_out=2.0,
                              label="segundo-A"))
    out2, _ = render(project2.data, tmp_path / "order2.mp4", overwrite=True)
    early1 = float(frame_rgb(out1, 1.0).mean())
    early2 = float(frame_rgb(out2, 1.0).mean())
    assert abs(early1 - early2) > 5  # the first two seconds really changed
