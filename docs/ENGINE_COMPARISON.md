# Comparación de motores — Dexter Fusion Studio

Fecha: 2026-11-06. Entorno de medición: Instabox `dexter`, Ubuntu 24.04,
4 vCPU, 7,8 GB RAM, **sin GPU**, FFmpeg 6.1.1 (build Ubuntu, `--enable-gpl`
+ libx264), melt 7.22.0 (libmlt7), Python 3.12, OpenTimelineIO 0.18.1,
PySide6 6.12.0. Medios de prueba: sintéticos generados con `testsrc` /
`smptebars` / tonos sinusoidales — nunca material privado.

Medios usados en las mediciones:

| Medio | Contenido | Propiedades |
|---|---|---|
| `vidA.mp4` | `testsrc` 1280x720 30 fps + seno 440 Hz | 5,0 s |
| `vidB.mp4` | `smptebars` 640x480 24 fps + seno 880 Hz | 5,0 s |
| `img.png` | color rojo 320x240 | 1 fotograma |
| `music.wav` | seno 660 Hz PCM 16 bits | 6,0 s |

## Decisión

**Arquitectura híbrida, con FFmpeg como motor de composición y render,**
**OpenTimelineIO como modelo de timeline e intercambio, y vista previa por**
**servidor de fotogramas (proxy renderizado + decodificación por FFmpeg).**

- El render final y la composición se hacen con un único `filtergraph` de
  FFmpeg generado desde el modelo multipista (normalización a lienzo,
  `xfade`/`acrossfade`, `overlay`, `amix`, `drawtext`, `fade`/`afade`).
- El modelo de timeline vive en `fusion/multitrack.py` (esquema v3
  versionado, con migración desde v2) y se exporta/importa con OTIO
  (Apache-2.0) como formato de intercambio.
- La vista previa NO usa QtMultimedia (no está en PySide6-Essentials y es
  frágil sin backend en Linux headless): renderiza un proxy de baja
  resolución con caché incremental y lo reproduce fotograma a fotograma
  decodificando con FFmpeg hacia `QImage`. Esto da scrubbing exacto y no
  depende del backend multimedia del sistema.
- MLT y GStreamer quedan **evaluados y descartados para esta versión**,
  con los motivos y las condiciones de revisión documentados abajo.
  Ninguno se instala como dependencia del proyecto.

## Evidencia medida (reproducible en dexter)

### 1. Composición FFmpeg multifuente (filtergraph)

Comando: dos vídeos con FPS/resolución distintos normalizados a
1280x720@30, `xfade` 0,5 s, overlay de imagen con `enable=between(t,1,4)`,
`drawtext`, mezcla de audio con `acrossfade` + `amix` y `afade`.

- Render de 5,5 s en **0,88 s reales** (~6,3x tiempo real en CPU, 720p).
- Salida verificada con ffprobe: 1280x720, 30 fps, 5,5 s, audio AAC.
- Análisis de píxeles (numpy, fotogramas crudos): a t=1,0 el píxel
  (1100,600) es `[252,0,0]` (overlay rojo presente); la media RGB cambia
  de (123,6; 116,3; 117,8) a t=1,0 a (88,5; 67,1; 75,6) a t=4,0
  (transición testsrc → smptebars confirmada).
- Análisis de audio por FFT: frecuencias dominantes a t=1,0 = **440 + 660 Hz**,
  a t=4,0 = **880 + 660 Hz** (mezcla de las dos fuentes + música confirmada).

### 2. Keyframes con expresiones FFmpeg (verificado, no supuesto)

- `scale` con `eval=frame` y expresión en `t` + `crop` → **OK** (zoom animado).
  Sin `eval=frame`, `scale` rechaza `t`.
- `volume` con expresión en `t` y `eval=frame` → **OK** (envolvente de ganancia).
- `overlay` con `x` en función de `t` → **OK**; píxel (300,200) rojo a t=0,5
  y cian a t=1,5, píxel (500,200) rojo a t=1,5 (movimiento real medido).
- `colorchannelmixer=aa` con expresión en `t` → **NO funciona**: `aa` se
  evalúa solo en init (`t` indefinido). Consecuencia de diseño: los
  keyframes de opacidad se implementan como segmentos constantes por
  tramos, no con expresiones. Limitación documentada, no escondida.

### 3. MLT (`melt` 7.22.0, libmlt7)

- XML multitractor con dos playlists + transición `mix` (`always_active`):
  75 fotogramas renderizados en **0,57 s**; salida 1280x720, 2,5 s,
  verificada con ffprobe. `melt -query` expone 492 filtros y 13
  transiciones en esta instalación.
- Avisos de timestamps de audio en el muxer MP4 (corregibles, pero ruido
  real en la salida).
- Instalación en dexter: `apt install melt` (libmlt7 ~5 MB instalado).
  Funciona, pero no se adopta (ver análisis).

### 4. OpenTimelineIO 0.18.1

- Round-trip verificado en Python: Timeline con pistas V1/A1/V2 y 3 clips
  → escritura `.otio` → relectura: pistas, nombres, `source_range`
  (inicio/duración) idénticos; duración total 5,0 s.

### 5. GStreamer

- No instalado en dexter. Candidatos apt: `gstreamer1.0-tools` (255 KB),
  `libges-1.0-0` (1,1 MB, GStreamer Editing Services), `python3-gst-1.0`
  (84 KB). Evaluación basada en documentación y arquitectura, no en
  ejecución (declarado como tal).

## Análisis por opción

### (a) FFmpeg como motor principal — ELEGIDO

| Criterio | Evaluación |
|---|---|
| Reproducción en tiempo real | Sin motor de reproducción propio; se suple con proxy + servidor de fotogramas. El render 720p corre a ~6x tiempo real en CPU en dexter; la previsualización es el proxy, no el máster. |
| Decodificación | Excelente: todos los formatos del proyecto (MP4/MOV/MKV/AVI/WAV/MP3/M4A/PNG/JPG/WEBP). |
| Composición | `filtergraph` declarativo y completo: normalización, xfade, overlay, amix, drawtext, fades, keyframes por expresiones (con la limitación de opacidad documentada). |
| Sincronización | `setpts`/`asetpts` + `fps` explícitos; verificado por FFT (tonos correctos por segmento). |
| Audio | `amix`, `acrossfade`, `afade`, `volume` con expresiones; análisis con `astats`/decodificación a PCM. |
| Keyframes | Zoom/posición/volumen por expresiones `t`; opacidad por tramos. Suficiente para v1; curvas Bézier se muestrean a lineal por tramos. |
| Efectos | Los 17 efectos actuales ya son filtros FFmpeg; reutilización total. |
| GPU | NVENC/NVDEC existen (`h264_nvenc`/`hevc_nvenc`, `cuda`); **sin verificar en dexter (no hay GPU)**. El motor elige `libx264` en CPU por defecto y NVENC solo si `ffmpeg -encoders` lo expone y el usuario lo activa. |
| Windows | Un solo binario externo (`ffmpeg.exe`/`ffprobe.exe`) junto al portable; el flujo de GitHub Actions ya lo empaqueta. Sin runtime adicional. |
| Mantenimiento | Proyecto maduro, API estable por CLI (sin bindings nativos que romper). El riesgo es la sintaxis de filtros; se mitiga con un generador de grafos con pruebas. |
| Licencias | FFmpeg LGPL-2.1/GPL según componentes. El build de Ubuntu es `--enable-gpl` (libx264 es GPL). El código propio NO se enlaza con FFmpeg: se invoca como proceso externo. Al distribuir el binario GPL hay que cumplir la GPL **para el componente FFmpeg** (ofrecer el código fuente de FFmpeg / usar un build LGPL si se quiere evitarlo). Documentado en `KNOWN_ISSUES.md`. No se copia código de FFmpeg. |
| PySide6 | Sin dependencia: comunicación por `subprocess` + archivos. |

### (b) MLT Framework como motor principal — DESCARTADO para v1

| Criterio | Evaluación |
|---|---|
| Fortalezas reales | Motor NLE de verdad (tractor/multitrack/transiciones), usado por Shotcut y Kdenlive. El test de `melt` rindió bien (0,57 s / 75 fotogramas) y el XML es legible. 492 filtros disponibles. |
| Por qué no ahora | 1) **Bindings Python inexistentes/maduros**: MLT no tiene bindings Python oficiales mantenidos; la integración sería generar XML + invocar `melt` por subprocess — el mismo patrón que FFmpeg, pero con un motor que el equipo no conoce y sin aprovechar su API C++. 2) **Reescritura del exportador**: habría que reescribir `engine.py`, `composition_layers.py` y los 17 efectos (que hoy son filtros FFmpeg) a servicios MLT, y re-verificar todas las pruebas. 3) **Empaquetado Windows**: MLT no tiene instalador oficial para Windows; habría que empaquetar las DLLs y sus dependencias (frei0r, SDL, etc.) a mano, frente a un único `ffmpeg.exe` ya resuelto. 4) **Audio**: los avisos de timestamps del test muestran fricción real en el muxer. 5) **Licencia**: el framework es **LGPL-2.1** (verificado vía GitHub API), aceptable; pero varios módulos/filtros son GPL y **Shotcut es GPL-3.0: estudiarlo sí, copiar su código no**. |
| Condición de revisión | Si en el futuro se necesita reproducción en tiempo real con scrubbing por debajo de la latencia del proxy, o transiciones MLT específicas, reevaluar con un prototipo que mida: latencia de seek, uso de memoria y empaquetado Windows real. El modelo multitrack v3 está diseñado para poder generar XML MLT además de filtergraph FFmpeg (los clips normalizados son agnósticos al motor). |

### (c) GStreamer como motor de reproducción — DESCARTADO para v1

| Criterio | Evaluación |
|---|---|
| Fortalezas reales | Pipelines excelentes, baja latencia, LGPL-2.1, `playbin`/`uridecodebin` maduros; GES (GStreamer Editing Services) aporta timeline/efectos. |
| Por qué no ahora | 1) GStreamer **no es un NLE por sí solo**: sin GES no hay timeline; GES es un proyecto aparte con bindings Python (`GstEditingServices`) frágiles en Windows y documentación escasa. 2) **Empaquetado Windows**: requiere el runtime de GStreamer (instalador MSI aparte, ~100 MB+) o empaquetado manual de DLLs; el portable actual solo necesita `ffmpeg.exe`. 3) Duplicaría el motor: seguiría haciendo falta FFmpeg para el render final y los efectos existentes. 4) Sin medición en dexter (no instalado; evaluación por documentación, declarada como tal). |
| Uso futuro posible | Solo como backend opcional de reproducción si QtMultimedia resultara insuficiente en Windows; no como motor de composición. |

### (d) Arquitectura híbrida — ELEGIDA (detalle)

```
Qt Workspace (PySide6)
  Biblioteca - Visor proxy - Inspector - Timeline (QGraphics)
  + TimelineCanvas: snapping, drag/drop, marcadores, ondas
        | modelo v3 (JSON)            | vista previa
        v                             v
  fusion/multitrack.py          fusion/proxy.py
  MultiTrackProject v3          hash -> proxy 480p en cache
  assets/tracks/clips/          segmentos por clip + ensamble
  markers/transitions/          frame-server: ffmpeg -> QImage
  keyframes/migracion v2
        |
        v
  fusion/compositor.py          fusion/audio.py
  filtergraph FFmpeg:           ondas reales (PCM->picos),
  normalizar -> efectos ->      medidores RMS/pico, fades,
  xfade -> overlay -> texto     envolventes de ganancia
  -> amix -> MP4 (ffprobe)
        |
        v
  fusion/otio_bridge.py         fusion/keyframes.py
  OTIO <-> modelo v3            lineal + easing, muestreo
  (Apache-2.0, opcional)        por tramos para opacidad

  Legado intacto: fusion/engine.py (plan v2) y
  fusion/composition_layers.py (V2/A3) siguen funcionando;
  el compositor v3 los reutiliza donde son compatibles.
```

### (e) Motor propio sobre bibliotecas existentes — DESCARTADO

Escribir un compositor desde cero (decodificar con libav, mezclar en
numpy/OpenCV, codificar) duplicaría FFmpeg con peor rendimiento, más
bugs y mantenimiento propio de sincronización A/V. Solo tendría sentido
para efectos que FFmpeg no puede expresar; ninguno de los pendientes lo
requiere. Se reutiliza, no se reinventa.

### OpenTimelineIO — ADOPTADO como modelo/intercambio (no como motor)

- Apache-2.0 (verificado vía GitHub API). Round-trip verificado (0.18.1).
- Uso: exportar/importar el timeline v3 (`Timeline`/`Track`/`Clip`/
  `ExternalReference`/`TimeRange`); **no** reproduce ni renderiza.
- Dependencia opcional: si `opentimelineio` no está instalado, el
  export/import OTIO lanza un error claro y el resto del editor funciona.
- Nota de precisión: OTIO usa tiempos racionales; la conversión
  segundos a `RationalTime` se hace a la tasa del lienzo (30 fps por
  defecto) con redondeo documentado en el código.

## Plan de migración (compatible con el código existente)

1. **Sin ruptura**: `StudioDocument` (v2) y `engine.export_plan` siguen
   siendo el camino de exportación por defecto. Nada de lo que funciona
   se elimina hasta que el v3 tenga paridad (regla del proyecto).
2. **Modelo nuevo al lado**: `fusion/multitrack.py` (v3) con migración
   `migrate_v2_timeline()` (clips V1 a pista V1 con `asset_id` del vídeo
   original; capas V2/A3 a pistas de imagen/audio). La migración es
   explícita, reversible (el `timeline-v2.json` original no se toca) y
   validada por pruebas.
3. **Compositor nuevo al lado**: `fusion/compositor.py` genera el
   filtergraph desde v3 y renderiza con el mismo `ffmpeg`/`ffprobe` y los
   mismos presets de códec que `engine.py`. Las pruebas comparan ambos
   caminos sobre el mismo material sintético.
4. **Vista previa nueva**: `fusion/proxy.py` + visor por fotogramas; no
   toca el reproductor de fuente existente (`QMediaPlayer`).
5. **Activación gradual en la UI**: acción de menú "Migrar a multipista
   (v3)" y exportación v3 solo cuando el proyecto tiene
   `multitrack.json`. El resto de la UI no cambia de estructura.
6. **MLT/GStreamer**: si se reevalúan, el punto de inserción es un
   generador alternativo (`multitrack -> MLT XML` / `-> GES`) sin tocar el
   modelo; la decisión se tomaría con mediciones, no con opiniones.

## Lo que queda explícitamente sin verificar

- **GPU / NVENC / NVDEC en RTX 3090**: dexter no tiene GPU; el código
  detecta NVENC solo si `ffmpeg -encoders` lo expone y cae a `libx264`
  en caso contrario. Sin prueba en hardware real.
- **EXE portable de Windows y arranque real**: solo GitHub Actions
  (Windows) puede producirlo; en dexter solo se verifica el build de
  Python, las pruebas Qt offscreen y el render FFmpeg.
- **Reproducción en tiempo real**: la vista previa por proxy es
  fotograma a fotograma; la fluidez a 30 fps en Windows es un objetivo
  medible, no una afirmación.
- **GStreamer**: evaluación por documentación, sin ejecución en dexter.

## Hallazgo TokenLab / PR #12 (inspección, sin fusión)

- La rama `feature/tokenlab-qt-count-ab` **NO está en `main`**: tiene 28
  archivos cambiados y +2.366 líneas respecto a `main` (módulos
  `fusion/tokenlab_*.py`, pruebas `tests/test_tokenlab_*.py`,
  `tests/tokenlab_live_probes.py`, +2 líneas en
  `studio-requirements.txt`). El PR #12 sigue **abierto, sin fusionar**.
- No se fusiona en este trabajo: es un subsistema de IA independiente
  (contadores/checkpoints TokenLab, Ollama) y la prioridad de
  `NEXT_TASK.md` es el motor multipista. Si se integra después, debe
  hacerse como servicio interno del Director Creativo, sin bloquear la
  UI ni el render (hilos separados, como ya hace `MotionWorker`).
