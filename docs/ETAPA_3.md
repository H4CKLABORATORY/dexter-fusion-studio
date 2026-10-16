# Etapa 3 — IA local para Free Fire (v0.3 preliminar)

Objetivo: preparar una IA de edición que respete la voz, los guiones y el humor de Dexter FF, sin pagar APIs ni subir las grabaciones a terceros.

## ¿Qué se agregó realmente?

1. Nuevo módulo fusion/ai_local.py con transcripción real por faster-whisper (optativo; se instala aparte).
2. Análisis local de audio/silencios/cambios de escena usando FFmpeg y señales verificables del SRT.
3. Análisis opcional de fotogramas mediante Ollama instalado localmente, nunca activado por defecto. Muestrea hasta 12 imágenes por análisis. Una imagen aislada NO entiende toda la acción, el audio ni los chistes.
4. Puntuación explicable de ventanas para Shorts, borrador de timeline separado (ai-proposed-timeline.json) y aceptación explícita con copia de seguridad.
5. Nueva pestaña IA local · Etapa 3 en la aplicación Windows y comandos de automatización.
6. Sin clonación de voces ajenas, extracción de TikToks sin autorización, publicación automática ni proveedores de pago.
7. Los memes siguen saliendo de la biblioteca aprobada de etapa 2; visión nueva no autoriza insertar memes arbitrarios.

## Preparación Windows, sin suscripción

Abre el proyecto; instala Python 3.10+, FFmpeg y FFprobe y ejecuta:

    py -3 -m fusion.cli ai-check

Transcripción con IA real sin API:

    py -3 -m pip install faster-whisper
    py -3 -m fusion.cli ai-transcribe --project "C:\Ruta\Proyecto" --model small --device cpu

La primera vez el modelo Whisper puede descargarse de Internet. Para usar GPU NVIDIA se necesita CUDA/CTranslate2 compatible con tu instalación. No asumas que --device cuda funciona hasta verificar drivers y bibliotecas. Tu voz original no se modifica.

Análisis sin visión de IA (funciona sólo con FFmpeg):

    py -3 -m fusion.cli ai-analyze --project "C:\Ruta\Proyecto" --scan-seconds 180

Si hiciste una transcripción, el programa encuentra automáticamente previews/ai-transcript.srt y utiliza sus frases; si seleccionaste un SRT en el proyecto, lo respeta.

Visión con IA en tu computadora (optativo): instala Ollama desde su sitio oficial y descarga un modelo visual compatible; comprueba la memoria RAM/VRAM primero. El nombre llava es solo un ejemplo, puede no estar instalado. NO se hace ollama pull ni instalaciones automáticas.

    py -3 -m fusion.cli ai-analyze --project "C:\Ruta\Proyecto" --ollama-local --model llava --frames 4 --scan-seconds 120

El adaptador solo hace solicitudes HTTP a 127.0.0.1:11434, sin posibilidad de configurar otro servidor. No se envían medios a proveedores remotos deliberadamente. Revisa siempre la configuración de red de tu instancia Ollama.

Borrador, revisión y exportación:

    py -3 -m fusion.cli ai-draft --project "C:\Ruta\Proyecto" --limit 4

Revisa ai-analysis.json y ai-proposed-timeline.json; ajusta clips, zoom y efectos. El programa NO modifica timeline-v2.json hasta que confirmes:

    py -3 -m fusion.cli ai-approve --project "C:\Ruta\Proyecto"
    py -3 -m fusion.cli prepare --project "C:\Ruta\Proyecto"
    py -3 -m fusion.cli render --project "C:\Ruta\Proyecto"

Si el timeline principal ya existe, aprobación falla sin --overwrite; al usarlo explícitamente se guarda respaldo timeline-v2.before-ai.json. El editor conserva la grabación original.

## Limitaciones actuales

- El análisis visual mira fotogramas aislados; no interpreta el video completo ni detecta bajas/jugadas con fiabilidad.
- Las candidatas de clips se puntúan principalmente por ritmo de escenas, subtítulos y silencios. Son sugerencias, no predicciones de viralidad.
- No se ha probado en Windows real del usuario ni se han instalado Whisper/Ollama en esa PC.
- No se han importado textos completos de todos los guiones antiguos; la biblioteca sigue siendo local.
- El procesamiento de video largo puede consumir bastante CPU; acota --scan-seconds para pruebas.
- Seguimiento de personajes, memes finamente sincronizados, diarización y edición autónoma quedan para etapas posteriores.

## Pruebas

    py -3 -m unittest discover -s tests -v

GitHub Actions ejecuta lógica y pruebas sintéticas con video de muestra en CI. No prueba modelos reales instalados en la PC.
