# Etapa 2 · Montaje inteligente asistido y efectos gratuitos

**Estado:** integrado en el código fuente, validado con pruebas unitarias y MP4 real generado en Linux. No instalado todavía en Windows del usuario ni enlazado a las GUIs externas.

## Novedades

- Nueva pestaña **Timeline v2**: generar propuestas, previsualizar fotograma, dividir clips, modificar in/out, reordenar, eliminar y asignar efecto/zoom individual. El programa conserva el MP4 fuente.
- Detección **técnica**: FFmpeg observa cambios de escena y silencios; subtítulos SRT existentes añaden coincidencias por palabras. Puntuación explicable en `timeline-v2.json`. No identifica kills, memes, emociones ni calidad viral.
- Selección de mejores intervalos sin solapamiento, configurable (2–90 segundos por ventana, hasta 20 clips). Modo estándar conserva todo: especialmente importante en novelas largas.
- **17** presets locales FFmpeg en total: clean, hype, cinematic, retro, monochrome, none, neon, comic, cold, warm, dream, glitch, vhs, night, flash, soft, sharp. Son presets originales, no una copia de efectos del motor Concat o EffectCraft.
- **Transición cruzada real** entre clips (`xfade` de video y `acrossfade` de audio), además de corte y fundido a negro. Su uso modifica la duración neta de la película al superponer escenas.
- Zoom manual independiente en cada clip entre 1.0 y 1.6. Escoge `fit` para conservar todo el gameplay original; el zoom recorta deliberadamente dentro de ese encuadre.
- Sugerencia de un efecto por escena cuando el SRT contiene ciertas palabras comprobables. Los efectos siempre son editables.
- Transcripción en español opcional con `faster-whisper` local; necesita instalar el paquete y descargar el modelo una vez, y no es un servicio API de pago.
- CLI para que Codex/OpenCreator puedan invocar generación y exportación sin GUI. Controlando el plan JSON, nunca decisiones privadas automáticas de publicación.

## Instalación

Windows: extrae el ZIP, instala Python 3.10+ y FFmpeg, y ejecuta `INICIAR_WINDOWS.bat`. Abre primero **Proyecto**, luego **Timeline v2**. Un proyecto necesita una grabación real. Pulsar `Generar línea de tiempo` analiza el contenido técnico, `Guardar y preparar edición` lo pasa al motor y `Exportar MP4` codifica el resultado. Los efectos visuales externos Concat/EffectCraft requieren aplicaciones y conexiones por separado.

Desde PowerShell, ejemplo usando un proyecto previamente creado:

```powershell
py -3 -m fusion.cli timeline --project "C:\Users\TU_NOMBRE\Documents\DexterFusionStudio\Mi-Proyecto" --highlights --window 10 --limit 4
py -3 -m fusion.cli prepare --project "C:\Users\TU_NOMBRE\Documents\DexterFusionStudio\Mi-Proyecto" --overwrite
py -3 -m fusion.cli render --project "C:\Users\TU_NOMBRE\Documents\DexterFusionStudio\Mi-Proyecto"
```

Siempre revisa los recortes, los memes y los subtítulos antes de usar el video. Los clips sugeridos por el modelo heurístico pueden ser aburridos o cortar el contexto.

## Seguridad y licencias

- Los medios privados, contraseñas y guiones no deben añadirse a GitHub. Solo se sube el código fuente limpio.
- Concat es AGPLv3: el adaptador lo consume vía API local autorizada, no incorpora su motor o su código. FilmCraft/EffectCraft son proyectos externos con licencias propias.
- No se crean imitaciones de voces ajenas sin autorización.
- Ningún video se publica o se sube automáticamente.
- No se prometen todos los efectos de Concat/ArtCraft integrados en esta versión. Necesitaríamos una implementación y pruebas adicionales para controlar desde el timeline todas las funciones de cada editor externo.

## Siguientes etapas

1. Previsualización de video continua con waveform, no solo fotogramas.
2. Localización de zonas seguras de texto y eventos de gameplay con modelos audiovisuales locales opt-in.
3. Integración avanzada de timeline nativo en Concat verificada en la versión instalada.
4. Empaquetado firmado `.exe`, instalador y validación de CPU/GPU en Windows.
