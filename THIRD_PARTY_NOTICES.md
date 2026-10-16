# Componentes de terceros / Third-party components

DEXTER FUSION STUDIO utiliza código Python original de este proyecto e integra
herramientas externas, con sus propias licencias.

## FFmpeg y FFprobe (en compilaciones Windows que los incluyan)

El flujo GitHub Actions descarga los binarios de FFmpeg y FFprobe desde el
proyecto independiente BtbN/FFmpeg-Builds, variante Windows GPL shared.

- Construcciones originales: https://github.com/BtbN/FFmpeg-Builds/releases
- Scripts de construcción: https://github.com/BtbN/FFmpeg-Builds
- Código fuente FFmpeg: https://git.ffmpeg.org/ffmpeg.git
- Licencias y fuentes: https://ffmpeg.org/legal.html
- Licencia principal GPL de la distribución seleccionada. Los binarios de FFmpeg
  NO pasan a ser propiedad de DEXTER FF y deben redistribuirse respetando
  su GPL y los requisitos sobre código fuente correspondiente.
- La versión exacta de FFmpeg se recoge al construir, en
  ffmpeg-version.txt junto al instalador. Usa ffmpeg -version para
  identificar la versión integrada.

Los ejecutables y DLL del paquete van en bin/ y se usan como procesos
separados. Pueden sustituirse por una versión compatible.

## faster-whisper / CTranslate2 y dependencias

- https://github.com/SYSTRAN/faster-whisper
- https://github.com/OpenNMT/CTranslate2
- Los componentes Python distribuidos conservan sus licencias originales.
- El modelo de transcripción tiny se descarga solo tras consentimiento
  expreso en el asistente y se rige por su propia licencia.

## Ollama

- https://github.com/ollama/ollama
- No se redistribuye Ollama dentro del instalador.
- Los modelos visuales se descargan e instalan aparte, con sus propios
  términos y necesidades de VRAM.

## PyInstaller / Inno Setup

PyInstaller construye el ejecutable para Windows. Inno Setup construye
el instalador. Se aplican sus respectivas licencias.

Este documento no sustituye los textos originales de licencia. Antes de
redistribuir FFmpeg en otra versión o fuera de este proyecto, revisa la
licencia y la disponibilidad del código fuente correspondiente.
