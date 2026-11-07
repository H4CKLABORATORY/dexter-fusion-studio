# KNOWN ISSUES — Dexter Fusion Studio

Estado verificado en dexter (Linux, CPU, sin GPU) el 2026-11-06. Nada de esta lista está confirmado como resuelto sin una medición nueva.

## Sin verificar en hardware real (no afirmar lo contrario)
- **NVENC/NVDEC en RTX 3090**: el compositor detecta NVENC solo si FFmpeg lo expone; en dexter no existe GPU, así que el camino NVENC nunca se ejecutó. En dexter se usa libx264.
- **EXE portable de Windows**: solo existe vía GitHub Actions (`studio-windows.yml`); no se ha ejecutado un build con la rama multipista ni probado el arranque en Windows.
- **Reproducción en tiempo real**: el proxy es un MP4 de baja resolución reproducido por QMediaPlayer; no es reproducción en vivo frame a frame del timeline. El scrub por frame-server (`iter_frames`) existe en el motor, pero la UI usa el proxy renderizado.
- **Rendimiento/memoria en Windows**: sin medir. En dexter, un compuesto 720p de 5.5 s renderizó en 0.88 s (~6.3x tiempo real, CPU); un render de 60 s a 640×360 está cubierto por tests.

## Limitaciones del motor v3 (por diseño, v1)
- **Posición de texto con keyframes**: estática en v1 (drawtext sin expresión de posición animada).
- **Opacidad con keyframes**: `colorchannelmixer=aa` no acepta expresiones `t`; la opacidad se muestrea en segmentos constantes de 0.25 s.
- **Mezcla de audio**: un solo `amix` con ganancias por clip; no es mezcla DAW (sin compresión, EQ por pista ni automatización por muestra).
- **GStreamer**: evaluado solo por documentación/licencia, no instalado ni ejecutado en dexter; su descarte para v1 es revisable si cambian los requisitos de playback.
- **MLT**: instalado y medido (melt 7.22.0), pero no es el motor elegido; el XML de ejemplo no forma parte del producto.

## UI / Qt
- **Diálogo modal en error de apertura**: si `open_project` falla, muestra un `QMessageBox.critical` modal; sin usuario presente (offscreen/CI) eso bloquea. Encontrado al depurar los tests Qt (la causa era un atributo faltante, ya corregido); el riesgo del modal sigue.
- **QMediaPlayer sin audio en dexter**: avisos `pipewire-0.3` y `PulseAudioService: pa_context_connect() failed` en headless; no impiden abrir proyectos ni el proxy, pero el audio de previsualización no suena en dexter.
- **Captura de pantalla**: generada offscreen (1510×920); no es una captura en Windows real.

## Repositorio / distribución
- **Push/PR bloqueado**: `gh` no tiene credenciales en dexter (verificado). La rama `feature/multitrack-engine-v1` existe solo localmente en dexter hasta que Douglas haga `gh auth login` y el push.
- **PR #12 (TokenLab)**: abierto, sin fusionar, sin revisar en este trabajo.
- **Disco en dexter**: `/data` con 2.5 GB libres (20 GB totales); el venv de Fusion Studio ocupa 776 MB. No descargar modelos grandes en dexter.

## Seguridad / contenido
- Solo medios sintéticos en tests (testsrc, smptebars, color, aevalsrc). El repo es público: nunca subir grabaciones, voces, contraseñas ni tokens.

## CI (resuelto 2026-11-07)
- **Segfault Qt en ubuntu-latest**: el 2026-11-07 `ubuntu-latest` migró a Ubuntu 26 (FFmpeg 9.0.1, PipeWire sin config) y `QMediaPlayer`/`QAudioOutput` hacía SIGSEGV (exit 139) en offscreen durante `test_drop_audio_into_a3_and_waveform`. Fijado `runs-on: ubuntu-24.04` en `studio-qt.yml` (donde los mismos tests pasan) + `LIBGL_ALWAYS_SOFTWARE=1`.
- **Tests multitrack sin pytest en CI**: `verify.yml` y `studio-qt.yml` no instalaban las dependencias de pruebas; los módulos `test_audio_proxy`, `test_compositor`, `test_multitrack` y `test_otio_bridge` fallaban al importar (`ModuleNotFoundError: No module named pytest`). Nuevo `tests/requirements.txt` (pytest, opentimelineio, numpy) instalado por ambos workflows antes de correr los tests. Ojo: los 4 modulos multitrack son estilo pytest (funciones + tmp_path); `unittest discover` los importa pero recoge 0 tests de ellos, asi que ambos workflows corren ademas `pytest` sobre esos 4 modulos (31 tests). Sin ese paso el run quedaba verde sin ejecutarlos. Nota: la línea `python -m unittest: error: --execute también requiere HERMES_RUN_ENABLED=1` en los logs es salida esperada de un test negativo de Hermes (`test_execution_requires_both_opt_ins`), no un fallo.
