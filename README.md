# DEXTER FUSION STUDIO · Editor personal de videos

Editor de escritorio gratuito para producir videos propios de Free Fire, YouTube, Shorts y TikTok. **El repositorio GitHub actual es público: nunca subas grabaciones, voces privadas, contraseñas ni tokens.** Proyecto original; **no incluye código copiado de Concat, FilmCraft, EffectCraft ni OpenCreator**.

## Compositor V2 + A3 real (desarrollo en PR #11)

El editor Qt incorpora **imágenes superpuestas V2** (tiempos, tamaño, posición y transparencia) y **música A3 independiente** (ganancia, recorte, inicio). Se guarda en el proyecto y se compone realmente en el MP4 con FFmpeg, preservando los medios originales. Permite seleccionar las capas desde el timeline y editar sus propiedades, así como reproducir el resultado ya exportado. **No ofrece aún composición en vivo ni múltiples videos superpuestos.**

- Código y pruebas integrales de audio/video: [PR #11](https://github.com/H4CKLABORATORY/dexter-fusion-studio/pull/11).
- Estado verificable: [PROJECT_STATUS.md](PROJECT_STATUS.md).
- Próxima tarea concreta: [NEXT_TASK.md](NEXT_TASK.md).

## Nuevo espacio de edición Qt para Windows (beta)

La nueva ventana de escritorio **Dexter Fusion Studio Workspace Qt** no es una maqueta: utiliza PySide6, FFmpeg y el timeline editable existente. Incluye visor del medio original, inspector, biblioteca de efectos, pistas V1/A1 con forma de onda, cortes, recortes, reordenar, undo/redo, subtítulos animados, exportación MP4 y Director Creativo de intros. **No reemplaza aún el motor de composición profesional completo**: V2/V3/A2/A3 están pendientes y el visor no reproduce todavía las capas compuestas.

- Ejecutable portable Windows (con FFmpeg y Qt): desde la pestaña [Actions — Studio Qt Windows EXE](https://github.com/H4CKLABORATORY/dexter-fusion-studio/actions/workflows/studio-windows.yml) descarga el artefacto `DexterFusionStudio-Windows-Portable` de una ejecución aprobada.
- Versión Python: `py -3 -m pip install -r studio-requirements.txt` y abre `INICIAR_ESTUDIO_WINDOWS.bat` o `py -3 studio.py`.
- Captura real generada automáticamente: [Actions — interfaz Qt y screenshot](https://github.com/H4CKLABORATORY/dexter-fusion-studio/actions/workflows/studio-qt.yml).
- Detalles, funciones faltantes y licencias: [docs/WORKSPACE_QT.md](docs/WORKSPACE_QT.md).

La interfaz Tk clásica permanece disponible durante la migración. No confundas los diseños conceptuales con una captura del ejecutable.

## Etapa 2 — Actualización principal

La versión 0.2 añade pestaña **Timeline v2**, 17 estilos reales FFmpeg, edición por escena con inicio/fin y zoom, selección heurística de clips, transición crossfade y narración original/subtítulos desde archivo SRT. Hay un motor de transcripción local opcional `faster-whisper` (no viene instalado ni configurado). Más detalles en `docs/ETAPA_2.md`.

## Modo Creador · propuestas de tomas repetidas (rama de mejora)

Con subtítulos SRT existentes o generados localmente con Whisper, el editor puede señalar tomas consecutivas muy similares y crear un informe revisable. Desde Timeline v2 aparece el botón **Analizar tomas repetidas**. Los cortes solo se aplican al timeline mediante CLI si se indican explícitamente las sugerencias revisadas; los originales permanecen intactos. No es el plugin comercial AutoEdit ni una función de Claude incorporada. Guía: [docs/MODO_CREADOR.md](docs/MODO_CREADOR.md).

## Subtítulos animados

En Timeline v2, **Estilo de subtítulos** permite `classic` (SRT tradicional), `karaoke` (palabras resaltadas) y `punch` (resaltado y aparición animada). Se renderizan localmente usando ASS/FFmpeg sin APIs de pago. La sincronía por palabra es aproximada porque el SRT contiene tiempos por frase. Ver [docs/SUBTITULOS_ANIMADOS.md](docs/SUBTITULOS_ANIMADOS.md).

## Director creativo · intros desde texto y cortes por referencia

Nuevo prototipo local en **Timeline v2**. Describe una intro en español y genera un MP4 original con títulos animados usando FFmpeg; o importa un video de referencia y reutiliza **solo la duración aproximada de sus cortes** en el timeline editable. No genera personajes ni reproduce efectos propietarios de Higgsfield Katana, y el original permanece intacto. [Uso y limitaciones](docs/DIRECTOR_CREATIVO.md).

## Funcionamiento actual

- Interfaz Windows de 6 pestañas: proyecto, edición automática, efectos y memes, **Timeline v2**, nuevos contenidos e integraciones.
- Exporta MP4 H.264 16:9 (1920×1080) y 9:16 (1080×1920).
- Elimina **silencios** si se habilita y prepara un plan JSON que puedes revisar; no identifica todas las jugadas o chistes por sí solo.
- Aplica 17 presets de efectos reales (incluye clean, hype, cinematic, neon, comic, glitch, VHS y otros); cortes y fundidos a negro, marca de agua, imágenes meme, subtítulos SRT y mezcla de narración.
- Importación de guiones locales con deduplicación; vocabulario y títulos conocidos listos como **semilla**, no falsos guiones completos.
- Detector conservador de contenido. Cuando no reconoce un tipo, solicita que elijas uno.
- Adaptador de **Concat JSON-RPC con token en localhost**, además de configuración MCP de FilmCraft/EffectCraft cuando se han instalado aparte.
- Originales intactos. Sin cuotas API ni nube obligatoria.

## Arranque en Windows

1. Descarga/instala Python 3.10+ desde https://www.python.org/downloads/.
2. Instala FFmpeg y FFprobe desde https://ffmpeg.org/download.html; agrega la carpeta bin a PATH.
3. Extrae este ZIP y en su carpeta ejecuta `py -3 main.py`. También puedes hacer doble clic en `INICIAR_WINDOWS.bat` si está correctamente asociado Python.
4. Elige un video grabado por ti. El editor guarda proyectos en `Documentos/DexterFusionStudio`.
5. Escoge perfil (Free Fire novela, Free Fire short, tutorial, reacción o vlog), o detecta automáticamente cuando existan pistas claras.
6. En **Edición automática**, selecciona formato y efecto, genera el plan y exporta. Comprueba el video antes de publicarlo.
7. Para guiones, entra a **Nuevos contenidos** e importa su carpeta. Los guiones se guardan en tu PC, no en el repositorio.

Requisitos prácticos: Windows 10/11, FFmpeg con libass para subtítulos. Para 1080p una GPU NVIDIA puede acelerar futuras versiones; la actual usa libx264 por CPU para asegurar compatibilidad.

## Editor externo Concat (opcional)

Instala Concat desde https://github.com/jub0t/Concat/releases y habilita Settings > Remote. Deja el servidor en **127.0.0.1:7420**. Introduce su token en el botón de la pestaña Integraciones. El adaptador crea un proyecto **real y editable en Concat** a partir de tu MP4, sin clonar internamente sus efectos.

Para FilmCraft y EffectCraft instala sus releases si quieres trabajar con un agente compatible MCP; la aplicación genera una configuración `mcp-integrations.json` con rutas de ejecutables encontrados. No ejecuta su GUI ni usa efectos externos si no los instalaste.

Documentación exacta de Concat: https://concat.standalones.org/docs/transports/json-rpc/.

## Sincronizar con tu GitHub

Antes de subir este ZIP verifica que el repositorio objetivo sea el correcto y que su visibilidad sea **Private de verdad**; llamarlo `Private` no lo vuelve privado. La subida desde ChatGPT queda pendiente hasta confirmar ese dato.

Si prefieres subirlo tú desde Windows, asegúrate primero de que el repositorio de destino esté vacío y de haber configurado Git. Dentro de esta carpeta ejecuta:

```powershell
git init -b main
git add .
git commit -m "Initial Dexter Fusion Studio"
git remote add origin https://github.com/TU_USUARIO/dexter-fusion-studio.git
git push -u origin main
```

GitHub puede pedir autenticación del usuario. Jamás pegues tu token en el código. Si no tienes Git instalado, puedes cargar los archivos desde la interfaz web (sin incluir tus grabaciones ni biblioteca privada).

## Comprobación

`python -m unittest discover -s tests -v`

Para pruebas de exportación con FFmpeg: `python -m unittest tests.test_smoke -v` (requiere FFmpeg y algo de CPU).

**No está instalado en tu PC aún.** Se entrega como código fuente ejecutable y listo para tu repositorio independiente, no como `.exe` firmado. Puede mejorarse paso a paso sin pagar proveedores de IA.

## Archivos extra

- `docs/ESTILO_DEXTER_FF.md`: instrucciones y preferencias reunidas para Free Fire y proyectos futuros.
- `SUBIR_A_GITHUB.ps1`: para subir a un **repositorio nuevo y privado que tú crees primero**, sin incluir secretos o medios.
- `fusion/phase2.py` y `fusion/timeline_ui.py`: línea de tiempo y selección de momentos explicable.
- `fusion/cli.py`: comandos automatizables para agentes.
- `fusion/concat_bridge.py`: catálogo real `catalogue.list` de Concat, inserción opcional de un efecto validado en su proyecto local.
- `fusion/integrations.py`: exporta proyectos FilmCraft/EffectCraft preexistentes con sus CLIs oficiales, si los instalas.

GitHub: **se necesita confirmar la identidad y visibilidad privada del repositorio** antes de subir este código. El conector no cambia la visibilidad de los repositorios. No confundas este proyecto local listo para publicar con una instalación remota completada.


## LOTTO LAB DEXTER (aplicación web independiente)

El proyecto de lotería matemática está separado del editor de video, en [`lotto-lab/`](lotto-lab/). Incluye programa adaptable a iPhone, calculadora de probabilidades, pruebas contra datos históricos y descargas diarias verificadas desde NY Open Data. **No predice sorteos futuros.**

- [Código y guía de Lotto Lab](lotto-lab/README.md)
- [Actualizaciones y descargas con histórico completo](https://github.com/H4CKLABORATORY/dexter-fusion-studio/actions/workflows/lotto-lab-pages.yml)
- Para obtener enlace público es preciso activar GitHub Pages una vez en Settings → Pages → GitHub Actions.
