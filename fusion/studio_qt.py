"""DEXTER FUSION STUDIO — Qt native professional editing workspace.

V1 export uses the real FFmpeg rendering engine. The source preview is not
yet a composited multi-track output preview; unsupported tracks are labelled.
"""
from __future__ import annotations

import array
import math
import os
from pathlib import Path
import subprocess
import sys

from PySide6.QtCore import Qt, QThread, Signal, QUrl, QSize
from PySide6.QtGui import (
    QAction, QColor, QBrush, QPen, QFont, QIcon, QPainter, QPixmap,
    QKeySequence, QShortcut, QLinearGradient,
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QSplitter, QListWidget,
    QListWidgetItem, QComboBox, QDoubleSpinBox, QSlider,
    QMessageBox, QToolBar, QFrame, QProgressBar, QGraphicsScene,
    QGraphicsView, QGraphicsRectItem, QGraphicsSimpleTextItem,
    QSizePolicy, QScrollArea, QGroupBox, QInputDialog, QDockWidget, QStackedWidget,
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget

from .engine import EFFECTS, export_plan
from .media import required
from .phase2 import apply_timeline
from .project import create_project
from .studio_model import StudioDocument

ACCENT = '#28E7B6'
BG = '#0B1019'
PANEL = '#151D2A'
BORDER = '#293448'
TEXT = '#E8EEF9'
DIM = '#8190AA'

STYLE = """
QWidget { background: #0B1019; color: #E8EEF9; font-family: 'Segoe UI'; font-size: 12px; }
QMainWindow, QSplitter { background: #0B1019; }
QFrame#Surface, QGroupBox { background: #151D2A; border: 1px solid #293448; border-radius: 10px; }
QGroupBox { margin-top: 15px; padding: 12px 9px 8px; font-weight: 700; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 5px; color: #E8EEF9; }
QLabel#Section { color: #F6FAFF; font-size: 13px; font-weight: 700; }
QLabel#Muted { color: #8190AA; font-size: 11px; }
QLabel#ProjectTitle { font-size: 15px; color: #F6FAFF; font-weight: 750; }
QLabel#Brand { font-size: 16px; color: #EAF8F8; font-weight: 800; letter-spacing: 1px; }
QPushButton { background: #233148; border: 1px solid #34445F; border-radius: 7px; padding: 8px 12px; font-weight: 650; }
QPushButton:hover { background: #344560; border-color: #28E7B6; }
QPushButton:pressed { background: #1C8170; }
QPushButton#Primary { background: #21D8AC; color: #061A18; border: 0; font-weight: 800; }
QPushButton#Primary:hover { background: #77FFDB; }
QPushButton:disabled { color: #66758B; background: #182130; border-color: #283244; }
QComboBox, QDoubleSpinBox, QLineEdit { background: #101725; border: 1px solid #34445F; border-radius: 6px; padding: 6px; min-height: 24px; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView { background: #192338; selection-background-color: #276558; }
QListWidget { background: #111A29; border: 1px solid #293448; border-radius: 7px; padding: 5px; }
QListWidget::item { padding: 6px; border-radius: 5px; }
QListWidget::item:selected { background: #1D5049; color: white; }
QSlider::groove:horizontal { background: #303E55; height: 5px; border-radius: 2px; }
QSlider::handle:horizontal { background: #28E7B6; width: 14px; margin: -5px 0; border-radius: 7px; }
QProgressBar { background: #1F2D41; color: #E8EEF9; border: 0; border-radius: 5px; min-height: 8px; }
QProgressBar::chunk { background: #28E7B6; border-radius: 5px; }
QScrollBar:horizontal, QScrollBar:vertical { background: #151D2A; width: 12px; height: 12px; }
QScrollBar::handle:horizontal, QScrollBar::handle:vertical { background: #3A4A62; border-radius: 5px; min-height: 25px; }
QToolBar { background: #111A29; border-bottom: 1px solid #293448; padding: 7px; spacing: 6px; }
QMenuBar { background: #111A29; padding: 4px; }
QMenuBar::item:selected, QMenu::item:selected { background: #21483F; }
QMenu { background: #192338; border: 1px solid #34445F; }
QStatusBar { background: #101725; color: #96A8C2; border-top: 1px solid #293448; }
QSplitter::handle { background: #293448; }
"""


def label(text, kind='Muted'):
    result = QLabel(text)
    result.setObjectName(kind)
    return result


def format_time(seconds):
    total = max(0, float(seconds))
    hrs = int(total // 3600)
    minutes = int((total % 3600) // 60)
    secs = int(total % 60)
    frames = round((total - math.floor(total)) * 30)
    return f'{hrs:02}:{minutes:02}:{secs:02}:{frames:02}'


def _envelope(source, limit_seconds=240, buckets=1100):
    """Actual audio peaks decoded through FFmpeg (bounded memory and CPU)."""
    exe = required('ffmpeg')
    result = subprocess.run(
        [exe, '-hide_banner', '-loglevel', 'error', '-nostdin', '-i', str(source),
         '-vn', '-ac', '1', '-ar', '2000', '-t', str(limit_seconds),
         '-f', 's16le', 'pipe:1'], capture_output=True, timeout=35,
    )
    if result.returncode:
        return []
    values = array.array('h')
    values.frombytes(result.stdout[:len(result.stdout) // 2 * 2])
    if not values:
        return []
    count = min(buckets, len(values))
    step = max(1, math.ceil(len(values) / count))
    return [
        min(1.0, max(abs(sample) for sample in values[i:i+step]) / 32768.0)
        for i in range(0, len(values), step)
    ]


class WaveformWorker(QThread):
    finished_wave = Signal(object)

    def __init__(self, source):
        super().__init__()
        self.source = source

    def run(self):
        try:
            data = _envelope(self.source)
        except Exception:
            data = []
        self.finished_wave.emit(data)


class ExportWorker(QThread):
    completed = Signal(str)
    failed = Signal(str)

    def __init__(self, folder, overwrite=False):
        super().__init__()
        self.folder = folder
        self.overwrite = overwrite

    def run(self):
        try:
            apply_timeline(self.folder, overwrite=True)
            output = export_plan(self.folder, overwrite=self.overwrite)
            self.completed.emit(str(output))
        except Exception as exc:
            self.failed.emit(str(exc))


class TimelineCanvas(QGraphicsView):
    clip_picked = Signal(int)
    seek_requested = Signal(float)

    HEAD = 138
    RULER = 35
    ROW = 57

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setStyleSheet('QGraphicsView { background: #101725; border: 1px solid #293448; }')
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.pixels_per_second = 48.0
        self.document = None
        self.waveform = []
        self.selected_index = -1
        self.playhead = 0.0
        self.track_names = ['V3  Efectos (próximamente)', 'V2  Overlays (próximamente)',
                            'V1  Montaje', 'A1  Audio original', 'A2  Voz (próximamente)',
                            'A3  Música (próximamente)']
        self.redraw()

    def set_document(self, document):
        self.document = document
        self.selected_index = 0
        self.playhead = 0
        self.waveform = []
        self.redraw()

    def set_waveform(self, data):
        self.waveform = data
        self.redraw()

    def set_scale(self, value):
        self.pixels_per_second = max(10, min(180, float(value)))
        self.redraw()

    def set_playhead(self, seconds):
        self.playhead = max(0.0, float(seconds))
        if self._playline:
            self._playline.setLine(self.HEAD + self.playhead * self.pixels_per_second,
                                   0, self.HEAD + self.playhead * self.pixels_per_second,
                                   self.RULER + self.ROW * len(self.track_names))

    def _t(self, text, x, y, color='#CBD7EA', size=10, bold=False):
        item = QGraphicsSimpleTextItem(text)
        font = QFont('Segoe UI', size)
        font.setBold(bold)
        item.setFont(font)
        item.setBrush(QBrush(QColor(color)))
        item.setPos(x, y)
        self._scene.addItem(item)
        return item

    def redraw(self):
        scene = self._scene
        scene.clear()
        self._playline = None
        length = self.document.output_duration if self.document else 50
        width = max(1250.0, self.HEAD + (length + 4) * self.pixels_per_second)
        height = self.RULER + self.ROW * len(self.track_names)
        scene.setSceneRect(0, 0, width, height)
        scene.addRect(0, 0, width, self.RULER, QPen(Qt.PenStyle.NoPen), QBrush(QColor('#151F30')))
        step = 1 if self.pixels_per_second >= 100 else (5 if self.pixels_per_second > 25 else 10)
        for t in range(0, int(length)+int(5*step), step):
            x = self.HEAD + t*self.pixels_per_second
            scene.addLine(x, 18, x, height, QPen(QColor('#263449'), 1, Qt.PenStyle.DotLine))
            self._t(f'{t//60:02}:{t%60:02}', x+3, 3, '#96A8C2', 9)
        for i, name in enumerate(self.track_names):
            y = self.RULER + i*self.ROW
            tint = '#141E2C' if i%2 == 0 else '#101825'
            scene.addRect(0, y, width, self.ROW, QPen(QColor('#283449'), 1), QBrush(QColor(tint)))
            scene.addRect(0, y, self.HEAD, self.ROW, QPen(QColor('#283449')), QBrush(QColor('#1A2636')))
            active = i in (2,3)
            self._t(name, 12, y+16, '#E7EFFC' if active else '#64758E', 9, active)
        if self.document:
            current = 0.0
            for index, clip in enumerate(self.document.clips):
                duration = clip.duration
                x = self.HEAD + current * self.pixels_per_second
                w = max(2.0, duration * self.pixels_per_second - 2)
                y = self.RULER + 2 * self.ROW + 6
                selected = index == self.selected_index
                fill = QColor('#236C8C' if not selected else '#2BB7BB')
                box = QGraphicsRectItem(x, y, w, self.ROW-13)
                box.setBrush(QBrush(fill))
                box.setPen(QPen(QColor('#8EEFE2' if selected else '#4FA6D3'), 2 if selected else 1))
                box.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable, True)
                box.setData(0, index)
                box.setToolTip(f'{clip.label}\nFuente {format_time(clip.start)} a {format_time(clip.end)}\nEfecto: {clip.effect}')
                scene.addItem(box)
                title = QGraphicsSimpleTextItem('▣  ' + clip.label[:25], box)
                title.setBrush(QBrush(QColor('#FFFFFF')))
                title.setFont(QFont('Segoe UI', 10, QFont.Weight.DemiBold))
                title.setPos(9, 5)
                stamp = QGraphicsSimpleTextItem(f'{duration:.1f}s  ·  {clip.effect}', box)
                stamp.setBrush(QBrush(QColor('#D2F9FF')))
                stamp.setFont(QFont('Segoe UI', 9))
                stamp.setPos(9, 24)
                # Source audio follows the visual edit in V1.
                ay = self.RULER + 3*self.ROW + 6
                sound = scene.addRect(x, ay, w, self.ROW-12,
                                      QPen(QColor('#1F9884')), QBrush(QColor('#135D59')))
                sound.setToolTip('Audio de la grabación original, sincronizado con V1')
                if self.waveform:
                    duration_src = min(240.0, self.document.media_info['duration'])
                    n = len(self.waveform)
                    span = max(0, round(w/3))
                    if span:
                        for k in range(span):
                            source_t = clip.start + (k+.5)/span * duration
                            pos = int(source_t / duration_src * n)
                            if 0 <= pos < n:
                                amp = self.waveform[pos]
                                wx = x+(k+.5)/span*w
                                center = ay+((self.ROW-12)/2)
                                amplitude = max(1.0, amp * 19)
                                scene.addLine(wx, center-amplitude, wx, center+amplitude,
                                              QPen(QColor('#3DF5CC'), 1.6))
                current += duration
        self._playline = scene.addLine(self.HEAD + self.playhead*self.pixels_per_second, 0,
                                       self.HEAD + self.playhead*self.pixels_per_second, height,
                                       QPen(QColor('#FFCE72'), 2))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.pos())
            cursor = item
            while cursor is not None:
                index = cursor.data(0)
                if index is not None:
                    self.selected_index = int(index)
                    self.clip_picked.emit(int(index))
                    self.redraw()
                    return
                cursor = cursor.parentItem()
            else:
                pos = self.mapToScene(event.pos())
                if pos.y() < self.RULER:
                    self.seek_requested.emit(max(0.0, (pos.x()-self.HEAD)/self.pixels_per_second))
                    self.set_playhead((pos.x()-self.HEAD)/self.pixels_per_second)
        super().mousePressEvent(event)


class StudioWindow(QMainWindow):
    def __init__(self, project_folder=None):
        super().__init__()
        self.setWindowTitle('DEXTER FUSION STUDIO  —  Workspace Pro')
        self.resize(1510, 920)
        self.setMinimumSize(1080, 700)
        self.setStyleSheet(STYLE)
        self.document = None
        self._render = None
        self._wave_worker = None
        self._loading = False
        self.audio = QAudioOutput(self)
        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio)
        self.audio.setVolume(.55)
        self._make_ui()
        if project_folder:
            self.open_project(project_folder)

    def _make_ui(self):
        self._build_menus()
        tool = QToolBar('Acciones')
        tool.setMovable(False)
        self.addToolBar(tool)
        brand = label('◈  DEXTER FUSION STUDIO','Brand')
        tool.addWidget(brand)
        spacer = QWidget()
        spacer.setFixedWidth(24)
        tool.addWidget(spacer)
        for text, callback in [('＋  Importar video', self.import_video),
                                ('⌁  Abrir proyecto', self.browse_project),
                                ('↶  Deshacer', self.undo), ('↷  Rehacer', self.redo),
                                ('✂  Dividir', self.split_at_player), ('▣  Guardar', self.save_project)]:
            action = QAction(text, self)
            action.triggered.connect(callback)
            tool.addAction(action)
        tool.addSeparator()
        self.export_action = QAction('EXPORTAR MP4  ↗', self)
        self.export_action.triggered.connect(self.export)
        tool.addAction(self.export_action)

        main = QWidget()
        self.setCentralWidget(main)
        root = QVBoxLayout(main)
        root.setContentsMargins(9, 8, 9, 8)
        root.setSpacing(7)
        split_v = QSplitter(Qt.Orientation.Vertical)
        split_h = QSplitter(Qt.Orientation.Horizontal)
        split_v.addWidget(split_h)
        split_v.setChildrenCollapsible(False)
        split_h.setChildrenCollapsible(False)
        split_h.addWidget(self._make_bin())
        split_h.addWidget(self._make_preview())
        split_h.addWidget(self._make_inspector())
        split_h.setStretchFactor(0, 2)
        split_h.setStretchFactor(1, 5)
        split_h.setStretchFactor(2, 2)
        split_h.setSizes([275, 760, 300])
        split_v.addWidget(self._make_timeline())
        split_v.setStretchFactor(0, 5)
        split_v.setStretchFactor(1, 4)
        split_v.setSizes([420, 465])
        root.addWidget(split_v)
        self.statusBar().showMessage('Listo · Motor FFmpeg local · Crea o abre un proyecto para comenzar')
        self._refresh()

    def _build_menus(self):
        bar = self.menuBar()
        file_menu = bar.addMenu('Archivo')
        for title, callback, shortcut in [
            ('Importar video', self.import_video, 'Ctrl+O'),
            ('Abrir proyecto', self.browse_project, 'Ctrl+Shift+O'),
            ('Guardar', self.save_project, 'Ctrl+S'),
            ('Exportar MP4', self.export, 'Ctrl+E')
        ]:
            a = file_menu.addAction(title)
            a.triggered.connect(callback)
            a.setShortcut(QKeySequence(shortcut))
        edit_menu = bar.addMenu('Edición')
        for title, callback, shortcut in [
            ('Deshacer', self.undo, 'Ctrl+Z'),
            ('Rehacer', self.redo, 'Ctrl+Shift+Z'),
            ('Dividir clip', self.split_at_player, 'Ctrl+B'),
            ('Eliminar clip', self.remove_clip, 'Delete')
        ]:
            a = edit_menu.addAction(title)
            a.triggered.connect(callback)
            a.setShortcut(QKeySequence(shortcut))
        help_menu = bar.addMenu('Ayuda')
        help_menu.addAction('Acerca del Studio', self.about)

    def _make_bin(self):
        panel = QFrame()
        panel.setObjectName('Surface')
        box = QVBoxLayout(panel)
        box.addWidget(label('BIBLIOTECA DE MEDIOS', 'Section'))
        box.addWidget(label('Fuentes importadas y accesos rápidos'))
        self.media_list = QListWidget()
        self.media_list.setMinimumHeight(90)
        self.media_list.setMaximumHeight(170)
        box.addWidget(self.media_list, 2)
        btn = QPushButton('＋  Añadir grabación')
        btn.clicked.connect(self.import_video)
        box.addWidget(btn)
        box.addWidget(label('EFECTOS DISPONIBLES', 'Section'))
        self.effects_list = QListWidget()
        self.effects_list.setMinimumHeight(100)
        self.effects_list.setMaximumHeight(225)
        for key, config in EFFECTS.items():
            item = QListWidgetItem('✧  '+config['label'])
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.effects_list.addItem(item)
        self.effects_list.itemDoubleClicked.connect(self.effect_picked)
        box.addWidget(self.effects_list, 1)
        box.addWidget(label('Los efectos son filtros FFmpeg reales.'))
        return panel

    def _make_preview(self):
        panel = QFrame()
        panel.setObjectName('Surface')
        box = QVBoxLayout(panel)
        top = QHBoxLayout()
        top.addWidget(label('VISOR DE FUENTE', 'Section'))
        top.addStretch(1)
        top.addWidget(label('Vista previa del archivo original'))
        box.addLayout(top)
        black = QFrame()
        black.setStyleSheet('background:#050910;border:1px solid #283449;border-radius:7px;')
        playerbox = QVBoxLayout(black)
        playerbox.setContentsMargins(4,4,4,4)
        self.video = QVideoWidget()
        self.video.setMinimumHeight(120)
        self.player.setVideoOutput(self.video)
        self.preview_stack=QStackedWidget()
        self.poster=QLabel('IMPORTA UNA GRABACIÓN PARA PREVISUALIZAR')
        self.poster.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.poster.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.poster.setMinimumHeight(0)
        self.poster.setStyleSheet('background:#060B14;color:#7788A2;font-weight:700;font-size:14px;')
        self.preview_stack.addWidget(self.poster)
        self.preview_stack.addWidget(self.video)
        self.preview_stack.setCurrentWidget(self.poster)
        playerbox.addWidget(self.preview_stack)
        box.addWidget(black, 1)
        self.scrub = QSlider(Qt.Orientation.Horizontal)
        self.scrub.setRange(0,0)
        self.scrub.sliderMoved.connect(self.player.setPosition)
        box.addWidget(self.scrub)
        transport = QHBoxLayout()
        self.time_display = label('00:00:00:00   /   00:00:00:00','ProjectTitle')
        transport.addWidget(self.time_display)
        transport.addStretch()
        for text, callback in [('⏮', self.back_5), ('▶  /  ❚❚', self.toggle_play),
                               ('⏭', self.forward_5)]:
            btn = QPushButton(text)
            btn.clicked.connect(callback)
            transport.addWidget(btn)
        box.addLayout(transport)
        self.player.positionChanged.connect(self._player_position)
        self.player.durationChanged.connect(self._player_duration)
        self.player.errorOccurred.connect(lambda *args: self.statusBar().showMessage('Reproductor: revisa compatibilidad del archivo',6000))
        box.addWidget(label('Montaje exportado con FFmpeg; la previsualización compuesta multipista es una fase posterior.'))
        return panel

    def _make_inspector(self):
        panel = QFrame()
        panel.setObjectName('Surface')
        box = QVBoxLayout(panel)
        box.addWidget(label('INSPECTOR DE PROPIEDADES', 'Section'))
        self.clip_info = label('Selecciona un clip de la línea de tiempo.')
        self.clip_info.setWordWrap(True)
        box.addWidget(self.clip_info)
        group = QGroupBox('Transformación y estilo')
        gv = QVBoxLayout(group)
        gv.addWidget(label('Efecto de color'))
        self.effect_combo = QComboBox()
        for key, val in EFFECTS.items():
            self.effect_combo.addItem(val['label'], key)
        gv.addWidget(self.effect_combo)
        gv.addWidget(label('Escala / zoom'))
        self.zoom_spin = QDoubleSpinBox()
        self.zoom_spin.setRange(1.0,1.6)
        self.zoom_spin.setDecimals(2)
        self.zoom_spin.setSingleStep(.05)
        gv.addWidget(self.zoom_spin)
        apply = QPushButton('Aplicar al clip seleccionado')
        apply.clicked.connect(self.apply_properties)
        gv.addWidget(apply)
        box.addWidget(group)
        edit_group = QGroupBox('Montaje de segmentos')
        ev = QVBoxLayout(edit_group)
        for text, fn in [
            ('✂  Dividir en el cabezal', self.split_at_player),
            ('⌫  Eliminar segmento', self.remove_clip),
            ('←  Mover antes', lambda: self.move_clip(-1)),
            ('Mover después  →', lambda: self.move_clip(1)),
            ('Editar entrada y salida', self.trim_clip),
        ]:
            btn=QPushButton(text);btn.clicked.connect(fn);ev.addWidget(btn)
        box.addWidget(edit_group)
        export_box = QGroupBox('Renderización')
        ex = QVBoxLayout(export_box)
        self.output_label = label('H.264 · MP4 · FFmpeg')
        ex.addWidget(self.output_label)
        self.export_progress = QProgressBar()
        self.export_progress.setRange(0, 100)
        self.export_progress.setValue(0)
        ex.addWidget(self.export_progress)
        self.export_button = QPushButton('Exportar montaje MP4')
        self.export_button.setObjectName('Primary')
        self.export_button.clicked.connect(self.export)
        ex.addWidget(self.export_button)
        box.addWidget(export_box)
        box.addStretch(1)
        scroll=QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(panel)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setMinimumHeight(225)
        scroll.setMinimumWidth(250)
        return scroll

    def _make_timeline(self):
        panel=QFrame()
        panel.setObjectName('Surface')
        box=QVBoxLayout(panel)
        row=QHBoxLayout()
        row.addWidget(label('LÍNEA DE TIEMPO  ·  EDICIÓN NO DESTRUCTIVA','Section'))
        row.addStretch(1)
        row.addWidget(label('Zoom de tiempo'))
        self.timeline_zoom=QSlider(Qt.Orientation.Horizontal)
        self.timeline_zoom.setMinimumWidth(110)
        self.timeline_zoom.setMaximumWidth(175)
        self.timeline_zoom.setRange(10, 160)
        self.timeline_zoom.setValue(48)
        row.addWidget(self.timeline_zoom)
        self.total_label=label('00:00:00:00')
        row.addWidget(self.total_label)
        box.addLayout(row)
        self.timeline=TimelineCanvas()
        self.timeline.setMinimumHeight(355)
        self.timeline_zoom.valueChanged.connect(self.timeline.set_scale)
        self.timeline.clip_picked.connect(self.select_clip)
        self.timeline.seek_requested.connect(self.seek_timeline)
        box.addWidget(self.timeline)
        footer=QHBoxLayout()
        footer.addWidget(label('V1: cortes y efectos exportables · A1: audio sincronizado · otras pistas: previstas, no exportables'))
        footer.addStretch(1)
        footer.addWidget(label('30 fps · Proyecto local'))
        box.addLayout(footer)
        return panel

    def import_video(self):
        path, _ = QFileDialog.getOpenFileName(self,'Importar video original',str(Path.home()),
            'Videos (*.mp4 *.mov *.mkv *.webm *.avi)')
        if not path:
            return
        try:
            base = Path.home()/'Documents'/'DexterFusionStudio'
            folder, _ = create_project(base, Path(path).stem, path, profile='freefire_short')
            self.open_project(folder)
        except Exception as exc:
            QMessageBox.critical(self,'Error al importar',str(exc))

    def browse_project(self):
        folder = QFileDialog.getExistingDirectory(self,'Abrir proyecto Dexter Fusion Studio',str(Path.home()/'Documents'))
        if folder:
            self.open_project(folder)

    def open_project(self, folder):
        try:
            if self._wave_worker and self._wave_worker.isRunning():
                self._wave_worker.wait(1500)
            self.document = StudioDocument(folder)
            self.player.setSource(QUrl.fromLocalFile(str(self.document.source)))
            self._source_poster()
            self.media_list.clear()
            info=self.document.media_info
            item=QListWidgetItem('▣  '+self.document.source.name)
            item.setToolTip(str(self.document.source))
            self.media_list.addItem(item)
            self.media_list.addItem(f"◷  {info['width']}×{info['height']} · {info['duration']:.1f}s")
            self.timeline.set_document(self.document)
            self.setWindowTitle(f'DEXTER FUSION STUDIO  —  {self.document.project.get("name","Proyecto")}')
            self._refresh()
            if info['audio']:
                worker=WaveformWorker(str(self.document.source))
                worker.finished_wave.connect(self.timeline.set_waveform)
                self._wave_worker=worker
                worker.start()
            self.statusBar().showMessage('Proyecto cargado · Archivo original protegido',5000)
        except Exception as exc:
            QMessageBox.critical(self,'No se pudo abrir',str(exc))

    def _source_poster(self):
        """Show an actual frame extracted from this recording, never a fabricated demo."""
        try:
            path=self.document.folder/'previews'/'studio-poster.jpg'
            path.parent.mkdir(parents=True,exist_ok=True)
            if not path.is_file():
                subprocess.run([
                    required('ffmpeg'),'-hide_banner','-loglevel','error',
                    '-nostdin','-y','-ss','0.7','-i',str(self.document.source),
                    '-frames:v','1','-vf','scale=960:-2',str(path)
                ],capture_output=True,check=True,timeout=15)
            pic=QPixmap(str(path))
            if not pic.isNull():
                self.poster.setPixmap(pic.scaled(
                    QSize(730,410),Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation))
                self.preview_stack.setCurrentWidget(self.poster)
        except Exception:
            self.poster.setText('Vista previa disponible al reproducir')

    def _refresh(self):
        doc=self.document
        self.total_label.setText(format_time(doc.output_duration) if doc else '00:00:00:00')
        selected=self.timeline.selected_index
        if doc and 0 <= selected < len(doc.clips):
            clip=doc.clips[selected]
            self.clip_info.setText(f'{clip.label}\n{format_time(clip.start)} → {format_time(clip.end)}\nDuración {clip.duration:.2f}s')
            self.effect_combo.setCurrentIndex(max(0,self.effect_combo.findData(clip.effect)))
            self.zoom_spin.setValue(clip.zoom)
            self.output_label.setText(f"MP4 · {doc.project.get('platform','youtube').upper()} · H.264")
        else:
            self.clip_info.setText('Importa un archivo y selecciona un clip.')
        self.export_button.setEnabled(bool(doc) and not self._render)
        self.export_action.setEnabled(bool(doc) and not self._render)

    def select_clip(self, index):
        if self.document and 0 <= index < len(self.document.clips):
            self.timeline.selected_index=index
            self._refresh()

    def effect_picked(self, item):
        key = item.data(Qt.ItemDataRole.UserRole)
        index = self.effect_combo.findData(key)
        if index >= 0:
            self.effect_combo.setCurrentIndex(index)
            self.apply_properties()

    def apply_properties(self):
        if not self.document:
            return
        try:
            idx=self.timeline.selected_index
            self.document.set_effect(idx,effect=self.effect_combo.currentData(),zoom=self.zoom_spin.value())
            self.timeline.redraw()
            self._refresh()
        except Exception as exc:
            QMessageBox.warning(self,'Inspector',str(exc))

    def split_at_player(self):
        if not self.document:
            return
        try:
            idx=self.timeline.selected_index
            self.document.split(idx,self.player.position()/1000)
            self.timeline.redraw()
            self._refresh()
        except Exception as exc:
            QMessageBox.warning(self,'Dividir clip',str(exc))

    def remove_clip(self):
        if not self.document:
            return
        try:
            idx=self.timeline.selected_index
            self.document.remove(idx)
            self.timeline.selected_index=min(idx,len(self.document.clips)-1)
            self.timeline.redraw()
            self._refresh()
        except Exception as exc:
            QMessageBox.warning(self,'Eliminar clip',str(exc))

    def move_clip(self, delta):
        if not self.document:
            return
        try:
            idx=self.timeline.selected_index
            next_idx=idx+delta
            self.document.move(idx,next_idx)
            self.timeline.selected_index=next_idx
            self.timeline.redraw()
            self._refresh()
        except (IndexError,ValueError) as exc:
            self.statusBar().showMessage(str(exc),4000)

    def trim_clip(self):
        if not self.document:
            return
        index=self.timeline.selected_index
        clip=self.document.clips[index]
        a,ok=QInputDialog.getDouble(self,'Entrada','Inicio del medio (segundos)',
                                    clip.start,0.0,self.document.media_info['duration'],3)
        if not ok:
            return
        b,ok=QInputDialog.getDouble(self,'Salida','Final del medio (segundos)',
                                    clip.end,0.0,self.document.media_info['duration'],3)
        if not ok:
            return
        try:
            self.document.trim(index,start=a,end=b)
            self.timeline.redraw()
            self._refresh()
        except ValueError as exc:
            QMessageBox.warning(self,'Recorte',str(exc))

    def undo(self):
        if self.document and self.document.undo():
            self.timeline.selected_index=min(self.timeline.selected_index,len(self.document.clips)-1)
            self.timeline.redraw()
            self._refresh()

    def redo(self):
        if self.document and self.document.redo():
            self.timeline.selected_index=min(self.timeline.selected_index,len(self.document.clips)-1)
            self.timeline.redraw()
            self._refresh()

    def save_project(self):
        if not self.document:
            return
        try:
            path=self.document.save()
            self.statusBar().showMessage('Línea de tiempo guardada: '+str(path),5000)
        except Exception as exc:
            QMessageBox.critical(self,'Guardar',str(exc))

    def export(self):
        if not self.document or self._render:
            return
        try:
            self.document.save()
            target=self.document.folder/'output'/f"{self.document.project.get('platform','youtube')}-{self.document.project.get('effects','clean')}.mp4"
            overwrite=False
            if target.exists():
                response=QMessageBox.question(self,'Exportación existente',
                    'Ya existe un render con este nombre. ¿Sobrescribir solamente ese MP4?',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if response!=QMessageBox.StandardButton.Yes:
                    return
                overwrite=True
            self._render=ExportWorker(str(self.document.folder),overwrite=overwrite)
            self._render.completed.connect(self._export_complete)
            self._render.failed.connect(self._export_failed)
            self.export_progress.setRange(0,0)
            self.export_button.setEnabled(False)
            self.export_action.setEnabled(False)
            self._render.start()
            self.statusBar().showMessage('Codificando MP4 con FFmpeg…',10000)
        except Exception as exc:
            QMessageBox.critical(self,'Renderización',str(exc))

    def _export_complete(self, path):
        self.export_progress.setRange(0,100)
        self.export_progress.setValue(100)
        self._render.wait(2500)
        self._render=None
        self._refresh()
        self.statusBar().showMessage('Exportación terminada: '+path,10000)
        QMessageBox.information(self,'Render completado','Archivo MP4 generado:\n'+path)

    def _export_failed(self, message):
        self.export_progress.setRange(0,100)
        self.export_progress.setValue(0)
        self._render.wait(2500)
        self._render=None
        self._refresh()
        QMessageBox.critical(self,'Falló la exportación',message)

    def seek_timeline(self, seconds):
        """Translate composition time into source time, respecting clip reorder."""
        if not self.document:
            return
        offset=0.0
        for clip in self.document.clips:
            if offset <= seconds < offset + clip.duration:
                self.player.setPosition(round((clip.start + seconds - offset) * 1000))
                return
            offset += clip.duration
        if self.document.clips:
            self.player.setPosition(round(self.document.clips[-1].end*1000))

    def _player_position(self, position):
        if not self.scrub.isSliderDown():
            self.scrub.setValue(position)
        self.time_display.setText(f'{format_time(position/1000)}  /  {format_time(self.player.duration()/1000)}')
        # Playback time points into the original source, not the edited composition.
        self.timeline.set_playhead(position/1000)

    def _player_duration(self, duration):
        self.scrub.setRange(0,max(0,int(duration)))

    def toggle_play(self):
        if self.player.playbackState()==QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.preview_stack.setCurrentWidget(self.video)
            self.player.play()

    def back_5(self):
        self.player.setPosition(max(0,self.player.position()-5000))

    def forward_5(self):
        self.player.setPosition(min(self.player.duration(),self.player.position()+5000))

    def about(self):
        QMessageBox.information(self,'Dexter Fusion Studio',
            'Espacio de edición Qt profesional en desarrollo.\n'
            'Motor de exportación FFmpeg integrado.\n'
            'Actualmente V1 y A1 tienen montaje/exportación real.\n'
            'La previsualización usa el video original; no representa aún las capas compuestas.\n'
            'Las pistas adicionales no son exportables.')

    def closeEvent(self, event):
        if self._render and self._render.isRunning():
            QMessageBox.warning(self,'Exportación en curso',
                'Espera a que termine la exportación antes de cerrar.')
            event.ignore()
            return
        event.accept()


def main(argv=None):
    import argparse
    from PySide6.QtCore import QTimer
    parser=argparse.ArgumentParser(description='DEXTER FUSION STUDIO Qt workspace')
    parser.add_argument('--project',help='Carpeta de proyecto compatible con timeline-v2.json')
    parser.add_argument('--screenshot',help='Captura verdadera de la interfaz Qt, sin renderizar medios externos')
    args=parser.parse_args(argv)
    app=QApplication.instance() or QApplication(sys.argv[:1])
    win=StudioWindow(args.project)
    win.show()
    if args.screenshot:
        def screenshot():
            path=Path(args.screenshot).expanduser().resolve()
            path.parent.mkdir(parents=True,exist_ok=True)
            win.grab().save(str(path))
            app.quit()
        QTimer.singleShot(1300,screenshot)
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
