# CHANGELOG — Dexter Fusion Studio

Formato: cambios verificados en dexter (Linux, CPU, sin GPU) salvo indicación expresa.

## Unreleased — rama `feature/multitrack-engine-v1` (2026-11-06)

### Añadido
- **Motor multipista v3** (`fusion/multitrack.py`): esquema versionado (schema 3), assets, 7 pistas (V1/V2/V3/T1/A1/A2/A3), clips no destructivos, transiciones, marcadores, snapping (0.25 s), undo/redo (40 pasos), migración v2→v3 sin tocar `timeline-v2.json`, reporte de assets faltantes.
- **Compositor real** (`fusion/compositor.py`): FFmpeg combina varios vídeos, imágenes, audio y textos en un MP4; mezcla FPS/resoluciones, crossfade de vídeo y audio, overlays con opacidad, drawtext, keyframes de zoom/volumen/posición, detección de encoders (NVENC solo si existe y se pide; error honesto si no).
- **Keyframes** (`fusion/keyframes.py`): linear, ease_in, ease_out, ease_in_out, hold; validación y muestreo; opacidad por segmentos constantes (limitación documentada).
- **Audio real** (`fusion/audio.py`): formas de onda (picos PCM), niveles RMS/pico por ventana de 0.1 s, envolventes de ganancia, fades, expresiones `volume` de FFmpeg desde keyframes (mínimo 2 keyframes).
- **Vista previa proxy** (`fusion/proxy.py`): caché incremental de dos niveles (segmentos por fingerprint + composición), `frame_at`/`iter_frames` para scrub por frame-server.
- **Intercambio OTIO** (`fusion/otio_bridge.py`): OTIO ⇄ v3, con campos v3 en metadatos `dexter`.
- **Qt** (`fusion/studio_qt.py`, `fusion/qt_multitrack.py`): menú Multipista (migrar, exportar MP4, vista previa proxy, OTIO), drag/drop de medios, marcadores con doble clic en la regla, snapping, formas de onda por clip en A3, medidor RMS/pico real, workers en hilo (proxy, export, ondas).
- **Investigación** (`docs/ENGINE_COMPARISON.md`): FFmpeg vs MLT vs GStreamer vs híbrido vs motor propio + OTIO, con mediciones reales en dexter, licencias y plan de migración.
- **Captura real**: `docs/screenshots/qt-multitrack-v3.png` (1510×920, ventana Qt offscreen con proyecto multipista).
- **Tests**: 31 tests nuevos del motor + 5 tests Qt offscreen; suite completa 154 passed + 67 subtests (2026-11-06). Medios 100 % sintéticos (testsrc/smptebars/color/aevalsrc).

### Sin cambios intencionados
- V2/A3 de PR #11 siguen funcionando (capas, exportación, undo/redo). La UI Tk clásica y el flujo v2 no se retiraron.

## 0.3.0 — main (2026-10-28, último push verificado)
- PR #11 fusionado (commit `0ff9445`): overlays V2 y música A3 reales en el MP4 final.
- PR #12 abierto, sin fusionar: contador TokenLab A/B en Qt (rama `feature/tokenlab-qt-count-ab`).
