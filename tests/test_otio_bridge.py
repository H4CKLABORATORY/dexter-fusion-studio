"""Tests for the OpenTimelineIO bridge (fusion/otio_bridge.py)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

otio = pytest.importorskip("opentimelineio", reason="OTIO no instalado")

from synth import make_media

from fusion.multitrack import MultiTrackProject
from fusion.otio_bridge import from_otio, to_otio, write_otio


def _clip(asset_id, track_id, *, start=0.0, source_in=0.0, source_out=3.0, **extra):
    clip = {"clip_id": None, "asset_id": asset_id, "track_id": track_id,
            "source_in": source_in, "source_out": source_out,
            "timeline_start": start, "effect": "clean", "zoom": 1.0,
            "opacity": 1.0, "gain": 1.0, "fade_in": 0.0, "fade_out": 0.0,
            "label": "Clip", "transition_in": None,
            "keyframes": {"zoom": [], "x": [], "y": [], "opacity": [], "volume": []}}
    clip.update(extra)
    return clip


def _project(tmp_path):
    media = make_media(tmp_path)
    project = MultiTrackProject.create("OTIO", width=1280, height=720, fps=30)
    assets = {name: project.add_asset(path) for name, path in media.items()}
    project.add_clip(**_clip(assets["vidA"]["asset_id"], "v1", start=0.0,
                             source_out=3.0, effect="hype", zoom=1.2))
    project.add_clip(**_clip(assets["vidB"]["asset_id"], "v1", start=3.0,
                             source_in=1.0, source_out=4.0,
                             transition_in={"type": "crossfade", "duration": 0.5}))
    project.add_clip(**_clip(assets["music"]["asset_id"], "a3", start=0.0,
                             source_in=0.0, source_out=5.0, gain=0.4))
    project.add_clip(**_clip(assets["img"]["asset_id"], "v3", start=1.0,
                             source_out=3.0, opacity=0.8, width=0.3))
    project.add_clip(**_clip(None, "t1", start=0.5, source_in=0.0, source_out=2.5,
                             text="HOLA"))
    return project, media, assets


def test_otio_roundtrip(tmp_path):
    project, media, _assets = _project(tmp_path)
    timeline = to_otio(project.data)
    names = [t.name for t in timeline.tracks]
    assert any("V1" in n for n in names)
    assert any("A3" in n for n in names)
    out = tmp_path / "test.otio"
    write_otio(project.data, out)
    assert out.is_file()
    back = from_otio(out)
    assert back["schema"] == 3
    assert len(back["clips"]) == 5
    assert sum(1 for c in back["clips"]) == 5
    v1 = sorted((c for c in back["clips"] if c["track_id"] == "v1"),
                key=lambda c: c["timeline_start"])
    assert v1[0]["effect"] == "hype"
    assert abs(v1[0]["zoom"] - 1.2) < 0.01
    assert v1[1]["transition_in"] == {"type": "crossfade", "duration": 0.5}
    music = [c for c in back["clips"] if c["track_id"] == "a3"][0]
    assert abs(music["gain"] - 0.4) < 0.01
    text = [c for c in back["clips"] if c["track_id"] == "t1"][0]
    assert text["text"] == "HOLA"


def test_otio_gap_preserved(tmp_path):
    media = make_media(tmp_path)
    project = MultiTrackProject.create("Gap", width=640, height=360, fps=30)
    asset = project.add_asset(media["vidA"])
    project.add_clip(**_clip(asset["asset_id"], "v1", start=2.0, source_out=3.0))
    back = from_otio(write_otio(project.data, tmp_path / "gap.otio"))
    clip = [c for c in back["clips"] if c["track_id"] == "v1"][0]
    assert clip["timeline_start"] == pytest.approx(2.0, abs=0.05)
