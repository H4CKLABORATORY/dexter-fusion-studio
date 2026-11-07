# DEXTER FUSION STUDIO — ESTADO VERIFICABLE

## Meta
Editor audiovisual Windows de nivel profesional. El sistema aún NO es equivalente a Premiere, CapCut, After Effects o Higgsfield Katana. Prohibido presentar prototipos como producto final.

## Base de producción actual (`main`)
- Interfaz Qt/PySide6, proyecto editable, reproducción del archivo fuente y timeline visual con V1/A1.
- Herramientas de cortar, reordenar, recortar, undo/redo, 17 efectos FFmpeg, subtítulos, exportación MP4 y Director Creativo de intros independientes.
- Compilación portátil Windows mediante GitHub Actions. Las pruebas automáticas validan arranque de GUI y render; instalación en hardware del usuario pendiente.

## Cambio incorporado a main: pull request #11 (commit 0ff9445)
- Capas V2 de imágenes con tamaño, posición, transparencia y duración.
- Pistas A3 de música con duración, comienzo, recorte, volumen y mezcla real con el audio de V1/A1.
- Línea de tiempo Qt muestra imágenes y audio exportables, con edición de parámetros desde inspector.
- Selección de las capas por clic sobre sus bloques.
- Modo para ver y escuchar el MP4 final después de exportar; no es reproducción de composición en vivo.
- Capas persistidas en JSON, validación estricta y operaciones undo/redo.
- Pruebas sintéticas que confirman cambios en píxeles y presencia de tonos audio separados.

## Motor multipista v3 — rama `feature/multitrack-engine-v1` (SIN fusionar a main, 2026-11-06)
- Arquitectura elegida y documentada en `docs/ENGINE_COMPARISON.md`: **híbrida — FFmpeg como motor de composición/render + OpenTimelineIO como modelo/intercambio de timeline + proxy con caché para la vista previa**. MLT y GStreamer evaluados y descartados para v1 con motivos documentados; motor propio descartado.
- Modelo de proyecto versionado (schema 3, `multitrack.json`): assets, 7 pistas (V1/V2/V3/T1/A1/A2/A3), clips no destructivos, transiciones, keyframes, marcadores, snapping (0.25 s), undo/redo (40 pasos), migración v2→v3 sin tocar `timeline-v2.json`, reporte de assets faltantes.
- Compositor real con FFmpeg: mezcla FPS/resoluciones, crossfade vídeo y audio, overlays de imagen con opacidad, textos drawtext, keyframes de zoom/volumen/posición (opacidad por segmentos constantes de 0.25 s), V2/A3 de PR #11 intactos. Verificado con ffprobe + análisis de píxeles + FFT de audio en medios sintéticos; render de 60 s verificado.
- Vista previa proxy con caché incremental de dos niveles (segmentos + composición), medidor de audio real (RMS/pico medidos del proxy) y formas de onda reales por clip de audio.
- Intercambio OTIO (Apache-2.0) de ida y vuelta, con campos v3 en metadatos `dexter`.
- Qt: menú Multipista (migrar, exportar MP4, vista previa proxy, OTIO), drag/drop de medios al timeline, marcadores con doble clic en la regla, snapping al buscar/arrastrar, formas de onda por clip en A3. Captura real: `docs/screenshots/qt-multitrack-v3.png`.
- Pruebas: 154 passed + 67 subtests (suite completa, 2026-11-06), incluidos 31 tests nuevos del motor y 5 tests Qt offscreen. La base de 118 tests previos sigue en verde.
- **Pendiente de verificar (no afirmado):** NVENC/NVDEC en RTX 3090, EXE Windows real, reproducción en tiempo real, rendimiento/memoria en Windows.

## Límites confirmados
- En `main`: todavía no admite varios videos independientes en V1/V2, transiciones complejas entre archivos diferentes ni keyframes de efecto (todo eso existe solo en la rama multipista v3, pendiente de revisión y merge).
- No hay formas de onda por pista A3 individual ni mezcla de audio de nivel DAW (en `main`; la rama v3 añade ondas por clip y medidor, pero no mezcla DAW).
- Vista compuesta disponible después de renderizar, NO en vivo (la rama v3 añade proxy de la composición, que tampoco es reproducción en vivo).
- Detección multimodal IA de escenas de Free Fire, motion tracking, máscara y composición 3D pendientes.
- Solo archivos locales; el repositorio de GitHub es público. No subir grabaciones, datos personales ni claves al código.

## Aprobación de funcionalidades
1. Código y pruebas automatizadas pertinentes.
2. MP4 real con mediciones de imagen y sonido para cambios de composición.
3. Captura auténtica de ventana Qt en ejecución (no ilustración IA).
4. ZIP Windows con EXE y prueba de arranque completada en CI.
5. Documentación actualizada y degradación segura ante medios faltantes.

## Continuidad
Consultar `NEXT_TASK.md`, `docs/WORKSPACE_QT.md`, el PR #11 (integrado) y el issue #10 antes de empezar nuevas funcionalidades. Todo avance debe citar commit, resultado de prueba y limitaciones.
