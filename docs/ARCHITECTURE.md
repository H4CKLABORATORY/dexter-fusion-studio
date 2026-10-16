# Arquitectura y límites

La aplicación es una **orquestación original** y no un fork ni copia de los 170/306 efectos de Concat/EffectCraft.

## Módulos

- `fusion.project` — proyectos, estilos, reconocimiento textual conservador.
- `fusion.media` — metadatos reales y silencios de audio.
- `fusion.engine` — montaje automático con FFmpeg, 17 presets de color, dos tipos de transición, subtítulos por SRT, marca de agua y memes autorizados.
- `fusion.library` — biblioteca privada de guiones y memes, con SHA-256 para deduplicar.
- `fusion.concat_bridge` — conexión API JSON-RPC real al servidor Concat local 127.0.0.1:7420 con token. Puede crear un proyecto editable en Concat a partir del MP4 exportado y aplicar un efecto de su catálogo validado por ID.
- `fusion.integrations` — detección Windows, configuración MCP para FilmCraft y EffectCraft, sin afirmar que estén instalados.
- `fusion.interface` — cinco pestañas Tkinter en Windows.

## Matriz de funcionalidad real

| Función | En esta versión | Limitación |
|---|---|---|
| Cortes por silencios | Sí | No distingue pausas dramáticas ni chistes |
| Formatos horizontal/vertical | Sí | `fit` añade bandas, `crop` pierde zona lateral |
| Corrección de color | Sí | 6 estilos FFmpeg, no LUTs GPU avanzadas |
| Transiciones | Sí | corte y fundido a negro (no crossfade real) |
| Subtítulos | Sí | Requiere SRT generado externamente; no OCR/transcripción incorporada |
| Memes | Sí | Sugiere por etiquetas, aprobación manual, imágenes |
| Narración | Sí | Mezcla un archivo de audio de tu propiedad o autorizado; no clona voces |
| Concat API | Sí, adaptador implementado | Requiere editor/API instalado y token; no es una interfaz de efectos integrada |
| FilmCraft y EffectCraft | MCP config real | Se usan mediante un cliente MCP externo; no se ejecutan dentro de la ventana |
| OpenCreator | Flujo compatible por archivo | Sin vinculación automatizada del motor todavía |
| Análisis integral TikTok | No | Requiere ingestión de referencias y modelo multimodal |
| Exportación local | Sí, FFmpeg | Requiere FFmpeg en PATH |

## Licencias y ética de componentes

- Concat: AGPL-3.0-or-later, repositorio de terceros. Se usa **vía su API pública**, no se redistribuye su código.
- FilmCraft/EffectCraft: `MIT OR Apache-2.0`, herramientas externas por CLI/MCP.
- OpenCreator: licencia Apache-2.0, herramienta externa.
- FFmpeg: consultar licencia y configuración de la distribución escogida.
- Esta base propia puede mantenerse en repositorio privado. Si en el futuro se copia/cambia código de terceros, revisar avisos, licencias y obligaciones antes de distribuir.

**La existencia de una API no garantiza todas las operaciones de render en cada versión externa.**

## Privacidad

- Originales, guiones, perfiles privados y renders se almacenan en carpeta del usuario. No se incluyen en ZIP ni GitHub.
- Tokens de Concat se introducen solo en la sesión; no se guardan ni registran.
- API Concat debe escuchar solo en localhost. No exponer el puerto 7420 a Internet.
- No hay telemetría ni publicación automática.

## Mejoras previstas

1. Análisis de escenas multimodal (voz, memes visuales, texto en pantalla) mediante modelo **local** con recursos disponibles.
2. Línea de tiempo gráfica editable y vista previa a múltiples FPS.
3. Captions propios con faster-whisper local y alineación por palabra.
4. Más efectos, auto-reencuadre con seguimiento de objetivos, keyframes y transiciones reales.
5. Orquestación coordinada entre Concat y ArtCraft tras integrar sus APIs y pruebas de escritorio.

Adaptadores CLI adicionales: FilmCraft y EffectCraft permiten exportar `.fcproj`/`.ecproj` preexistentes desde la pestaña Integraciones, usando sus comandos oficiales. No fusionan motores de GPU en un proceso único.

## Etapa 2: alcance verificado

- `fusion.phase2`: candidatas visuales con score explicable, propuesta de efectos por texto, edición cronológica JSON, preview de imagen y Whisper local opcional.
- `fusion.timeline_ui`: pestaña de timeline con selección, ajuste, zoom y efectos por clip.
- `fusion.cli`: integración local por subcomandos `create`, `timeline`, `prepare`, `render`, `effects`, `status`.
- `fusion.engine.crossfade_parts`: crossfade de video/audio mediante FFmpeg (prueba de salida MP4 real).
- **No se han fusionado los motores propietarios/externos ni hay interpretaciones audiovisuales semánticas.**
