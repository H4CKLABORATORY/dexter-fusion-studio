"""Qt helpers for the multitrack engine (proxy preview, meter, export).

Kept in a separate module so ``studio_qt.py`` stays readable. All heavy
work runs in QThreads; the UI thread never blocks on FFmpeg.
"""
from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from .audio import audio_levels, waveform_peaks
from .compositor import render
from .proxy import get_proxy


class MeterWidget(QWidget):
    """Real audio meter: RMS (green) + peak (amber) bars from measured
    levels of the proxy audio. No animation is faked: without levels the
    bars stay at zero."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(26)
        self.setMinimumWidth(120)
        self._levels = []
        self._time = 0.0

    def set_levels(self, levels):
        self._levels = list(levels or [])
        self._time = 0.0
        self.update()

    def set_time(self, seconds):
        self._time = max(0.0, float(seconds))
        self.update()

    def _level_at(self):
        if not self._levels:
            return 0.0, 0.0
        window = (self._levels[1][0] - self._levels[0][0]
                  if len(self._levels) > 1 else 0.1)
        index = int(self._time // window) if window > 0 else 0
        if 0 <= index < len(self._levels):
            return self._levels[index][1], self._levels[index][2]
        return 0.0, 0.0

    def paintEvent(self, _event):
        rms, peak = self._level_at()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        width, height = self.width(), self.height()
        painter.fillRect(0, 0, width, height, QColor("#101725"))
        bar_h = (height - 8) // 2
        painter.setPen(QPen(QColor("#283449"), 1))
        painter.drawRect(0, 2, width - 1, bar_h)
        painter.drawRect(0, 4 + bar_h, width - 1, bar_h)
        painter.fillRect(1, 3, max(0, int((width - 2) * min(1.0, rms))),
                         bar_h - 1, QColor("#28E7B6"))
        painter.fillRect(1, 5 + bar_h, max(0, int((width - 2) * min(1.0, peak))),
                         bar_h - 1, QColor("#FFCE72"))
        painter.setPen(QColor("#8190AA"))
        painter.drawText(4, height - 4,
                         f"RMS {rms:.2f} · pico {peak:.2f}  (medido del proxy)")


class ProxyWorker(QThread):
    """Render (or reuse from cache) the proxy of a v3 project."""

    completed = Signal(str, bool)   # path, cache_hit
    failed = Signal(str)

    def __init__(self, project_data, folder, height=480):
        super().__init__()
        self.project_data = project_data
        self.folder = Path(folder)
        self.height = height

    def run(self):
        try:
            path, hit = get_proxy(self.project_data, self.folder, height=self.height)
            self.completed.emit(str(path), bool(hit))
        except Exception as exc:
            self.failed.emit(str(exc))


class MultitrackExportWorker(QThread):
    """Render a v3 project to full-quality MP4 in the background."""

    completed = Signal(str)
    failed = Signal(str)

    def __init__(self, project_data, output, overwrite=False):
        super().__init__()
        self.project_data = project_data
        self.output = Path(output)
        self.overwrite = overwrite

    def run(self):
        try:
            path, _info = render(self.project_data, self.output,
                                 overwrite=self.overwrite)
            self.completed.emit(str(path))
        except Exception as exc:
            self.failed.emit(str(exc))


class ClipWaveformWorker(QThread):
    """Real waveform peaks for one audio file, tagged with a clip id."""

    finished = Signal(str, object)  # clip_id, peaks list

    def __init__(self, clip_id, source):
        super().__init__()
        self.clip_id = clip_id
        self.source = source

    def run(self):
        try:
            data = waveform_peaks(self.source)
        except Exception:
            data = []
        self.finished.emit(self.clip_id, data)


def proxy_audio_levels(proxy_path):
    """Measured RMS/peak levels of a proxy file (for the meter widget)."""
    try:
        return audio_levels(proxy_path, window=0.1)
    except Exception:
        return []


def dbfs(value):
    """Amplitude 0..1 to dBFS (for tooltips, not for fake precision)."""
    if value <= 0:
        return float("-inf")
    return round(20 * math.log10(value), 1)
