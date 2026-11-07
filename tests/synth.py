"""Synthetic test media for the multitrack engine tests.

All media is generated locally with FFmpeg lavfi sources (testsrc,
smptebars, color, sine tones). Nothing here is a real recording, a voice
sample, or any private material. Files are created inside pytest's
tmp_path and deleted with it.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


def make_media(folder):
    """Create vidA/vidB/img/music and return their paths as a dict."""
    folder = Path(folder)
    vid_a = folder / "vidA.mp4"
    vid_b = folder / "vidB.mp4"
    img = folder / "img.png"
    music = folder / "music.wav"
    voice = folder / "voice.wav"
    cmds = [
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
         "-i", "testsrc=size=1280x720:rate=30:duration=5",
         "-f", "lavfi", "-i", "aevalsrc=0.9*sin(2*PI*440*t):duration=5",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
         "-shortest", str(vid_a)],
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
         "-i", "smptebars=size=640x480:rate=24:duration=5",
         "-f", "lavfi", "-i", "aevalsrc=0.9*sin(2*PI*880*t):duration=5",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
         "-shortest", str(vid_b)],
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
         "-i", "color=c=red:size=320x240:duration=1",
         "-frames:v", "1", str(img)],
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
         "-i", "aevalsrc=0.9*sin(2*PI*660*t):duration=6",
         "-c:a", "pcm_s16le", str(music)],
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
         "-i", "aevalsrc=0.9*sin(2*PI*220*t):duration=4",
         "-c:a", "pcm_s16le", str(voice)],
    ]
    for cmd in cmds:
        subprocess.run(cmd, check=True, capture_output=True)
    return {"vidA": vid_a, "vidB": vid_b, "img": img,
            "music": music, "voice": voice}


def frame_rgb(path, t, width=1280, height=720):
    """Decode one frame to an (H, W, 3) uint8 numpy array."""
    import numpy as np
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(path),
         "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.uint8).reshape(height, width, 3)


def dominant_freqs(path, t, *, duration=0.5, sample_rate=48000):
    """Top FFT frequencies of the audio at time t (for tone checks)."""
    import numpy as np
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(path),
         "-t", str(duration), "-f", "f32le", "-ac", "1",
         "-ar", str(sample_rate), "-"],
        capture_output=True, check=True).stdout
    a = np.frombuffer(raw, dtype=np.float32)
    if len(a) < 1024:
        return []
    spec = np.abs(np.fft.rfft(a * np.hanning(len(a))))
    freqs = np.fft.rfftfreq(len(a), 1 / sample_rate)
    top = freqs[np.argsort(spec)[-4:][::-1]]
    return sorted(int(round(f)) for f in top)


def probe_json(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=codec_type,width,height,r_frame_rate:format=duration",
         "-of", "json", str(path)],
        capture_output=True, check=True, text=True).stdout
    return json.loads(out)
