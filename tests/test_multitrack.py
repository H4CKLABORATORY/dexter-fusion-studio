"""Tests for the multitrack model (fusion/multitrack.py + keyframes)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from synth import make_media

from fusion.keyframes import evaluate, validate_keyframes
from fusion.multitrack import (
    MultiTrackProject, migrate_v2_timeline, project_duration,
    snap_points, snap_time, validate_project, missing_assets,
)


def _project(tmp_path):
    media = make_media(tmp_path)
    project = MultiTrackProject.create("Prueba multipista", width=1280, height=720, fps=30)
    asset_a = project.add_asset(media["vidA"])
    asset_b = project.add_asset(media["vidB"])
    asset_m = project.add_asset(media["music"])
    asset_i = project.add_asset(media["img"])
    return project, media, asset_a, asset_b, asset_m, asset_i


def _clip(asset_id, track_id, *, start=0.0, source_in=0.0, source_out=3.0, **extra):
    clip = {"clip_id": None, "asset_id": asset_id, "track_id": track_id,
            "source_in": source_in, "source_out": source_out,
            "timeline_start": start, "effect": "clean", "zoom": 1.0,
            "opacity": 1.0, "gain": 1.0, "fade_in": 0.0, "fade_out": 0.0,
            "label": "Clip", "transition_in": None,
            "keyframes": {"zoom": [], "x": [], "y": [], "opacity": [], "volume": []}}
    clip.update(extra)
    return clip


def test_create_default_tracks():
    project = MultiTrackProject.create("Vacío")
    kinds = [t["kind"] for t in project.data["tracks"]]
    assert kinds == ["video", "video", "image", "text", "audio", "audio", "audio"]
    assert project.data["schema"] == 3
    assert project_duration(project.data) == 0.0


def test_add_clips_and_duration(tmp_path):
    project, _media, a, b, _m, _i = _project(tmp_path)
    project.add_clip(**_clip(a["asset_id"], "v1", start=0.0, source_out=3.0))
    project.add_clip(**_clip(b["asset_id"], "v1", start=3.0, source_in=1.0, source_out=4.0))
    assert project_duration(project.data) == 6.0
    assert len(project.data["clips"]) == 2


def test_overlap_rejected_on_video_track(tmp_path):
    project, _media, a, _b, _m, _i = _project(tmp_path)
    project.add_clip(**_clip(a["asset_id"], "v1", start=0.0, source_out=3.0))
    with pytest.raises(ValueError):
        project.add_clip(**_clip(a["asset_id"], "v1", start=2.0, source_out=4.0))


def test_overlap_allowed_on_image_track(tmp_path):
    project, _media, _a, _b, _m, img = _project(tmp_path)
    project.add_clip(**_clip(img["asset_id"], "v3", start=0.0, source_out=3.0))
    project.add_clip(**_clip(img["asset_id"], "v3", start=1.0, source_out=4.0))
    assert len(project.data["clips"]) == 2


def test_clip_outside_asset_rejected(tmp_path):
    project, _media, a, _b, _m, _i = _project(tmp_path)
    with pytest.raises(ValueError):
        project.add_clip(**_clip(a["asset_id"], "v1", start=0.0, source_out=99.0))


def test_wrong_kind_track_rejected(tmp_path):
    project, _media, a, _b, m, _i = _project(tmp_path)
    with pytest.raises(ValueError):
        project.add_clip(**_clip(m["asset_id"], "v1", start=0.0, source_out=3.0))


def test_transition_rules(tmp_path):
    project, _media, a, b, _m, _i = _project(tmp_path)
    project.add_clip(**_clip(a["asset_id"], "v1", start=0.0, source_out=3.0))
    # Transition longer than half of the shortest neighbour: rejected.
    with pytest.raises(ValueError):
        project.add_clip(**_clip(b["asset_id"], "v1", start=3.0, source_in=0.0,
                                 source_out=1.0,
                                 transition_in={"type": "crossfade", "duration": 1.0}))
    project.add_clip(**_clip(b["asset_id"], "v1", start=3.0, source_in=0.0,
                             source_out=2.0,
                             transition_in={"type": "crossfade", "duration": 0.5}))
    assert project.data["clips"][1]["transition_in"]["type"] == "crossfade"


def test_snap_time(tmp_path):
    project, _media, a, _b, _m, _i = _project(tmp_path)
    project.add_clip(**_clip(a["asset_id"], "v1", start=0.0, source_out=3.0))
    project.add_marker(1.5, "Golpe")
    assert snap_time(project.data, 2.9) == 3.0
    assert snap_time(project.data, 1.4) == 1.5
    assert snap_time(project.data, 0.1) == 0.0
    assert snap_time(project.data, 2.0) == 2.0  # no snap point nearby
    assert 0.0 in snap_points(project.data) and 3.0 in snap_points(project.data)


def test_split_move_undo_redo(tmp_path):
    project, _media, a, _b, _m, _i = _project(tmp_path)
    clip = project.add_clip(**_clip(a["asset_id"], "v1", start=0.0, source_out=4.0))
    project.split_clip(clip["clip_id"], 2.0)
    assert len(project.data["clips"]) == 2
    assert project.data["clips"][0]["source_out"] == 2.0
    assert project.data["clips"][1]["source_in"] == 2.0
    assert project.undo() is True
    assert len(project.data["clips"]) == 1
    assert project.redo() is True
    assert len(project.data["clips"]) == 2
    # Invalid split rolls back without corrupting the project.
    with pytest.raises(ValueError):
        project.split_clip(project.data["clips"][0]["clip_id"], 0.05)
    assert len(project.data["clips"]) == 2


def test_keyframes_evaluate_and_validate():
    kfs = validate_keyframes(
        [{"t": 0, "v": 1.0}, {"t": 2, "v": 1.5, "easing": "ease_in"}],
        minimum=1.0, maximum=1.6, duration=2.0, label="zoom")
    assert evaluate(kfs, 0, default=1.0) == 1.0
    assert evaluate(kfs, 2, default=1.0) == 1.5
    assert 1.0 < evaluate(kfs, 1.0, default=1.0) < 1.5
    with pytest.raises(ValueError):
        validate_keyframes([{"t": 0, "v": 9.0}], minimum=1.0, maximum=1.6,
                           duration=2.0, label="zoom")
    with pytest.raises(ValueError):
        validate_keyframes([{"t": 5, "v": 1.2}], minimum=1.0, maximum=1.6,
                           duration=2.0, label="zoom")


def test_missing_assets_reported_not_crash(tmp_path):
    project, media, a, _b, _m, _i = _project(tmp_path)
    project.add_clip(**_clip(a["asset_id"], "v1", start=0.0, source_out=3.0))
    media["vidA"].unlink()
    assert len(missing_assets(project.data)) == 1
    # The project still validates and saves; only rendering is blocked.
    validate_project(project.data)
    project.save(tmp_path / "multitrack.json")
    assert (tmp_path / "multitrack.json").is_file()


def test_migrate_v2_to_v3(tmp_path):
    media = make_media(tmp_path)
    timeline_v2 = {
        "source": str(media["vidA"]), "platform": "youtube",
        "cut_style": "crossfade", "transition_seconds": 0.25,
        "caption_style": "classic",
        "clips": [{"start": 0.0, "end": 2.0, "effect": "hype", "zoom": 1.1,
                   "label": "A"},
                  {"start": 2.0, "end": 5.0, "effect": "clean", "zoom": 1.0,
                   "label": "B"}],
        "layers": {"images": [{"path": str(media["img"]), "start": 0.5,
                               "end": 2.5, "width": 0.3, "x": 0.7, "y": 0.2,
                               "opacity": 0.8}],
                   "audio": [{"path": str(media["music"]), "start": 0.0,
                              "source_start": 1.0, "duration": 4.0, "gain": 0.4}]},
    }
    project_json = {"name": "Migrado", "platform": "youtube"}
    data = migrate_v2_timeline(timeline_v2, project_json)
    assert data["schema"] == 3
    v1 = [c for c in data["clips"] if c["track_id"] == "v1"]
    assert len(v1) == 2
    assert v1[1]["transition_in"] == {"type": "crossfade", "duration": 0.25}
    assert abs(project_duration(data) - 4.75) < 0.01
    images = [c for c in data["clips"] if c["track_id"] == "v3"]
    assert len(images) == 1 and images[0]["opacity"] == 0.8
    assert images[0]["width"] == 0.3
    music = [c for c in data["clips"] if c["track_id"] == "a3"]
    assert len(music) == 1 and music[0]["gain"] == 0.4
    # The original v2 dict is untouched (migration is non-destructive).
    assert timeline_v2["clips"][0]["start"] == 0.0


def test_save_load_roundtrip(tmp_path):
    project, _media, a, _b, _m, _i = _project(tmp_path)
    project.add_clip(**_clip(a["asset_id"], "v1", start=0.0, source_out=3.0))
    path = tmp_path / "multitrack.json"
    project.save(path)
    loaded = MultiTrackProject.load(path)
    assert loaded.data["name"] == "Prueba multipista"
    assert len(loaded.data["clips"]) == 1
    assert loaded.data["clips"][0]["source_out"] == 3.0
    # Corrupt schema is rejected, not silently accepted.
    bad = json.loads(path.read_text())
    bad["schema"] = 2
    (tmp_path / "bad.json").write_text(json.dumps(bad))
    with pytest.raises(ValueError):
        MultiTrackProject.load(tmp_path / "bad.json")
