# Instalar Dexter Fusion Studio en Windows (v0.3)

Este instalador se crea **en Windows real** mediante GitHub Actions. No exige que instales Python, Git o FFmpeg por separado.

## Descarga desde tu GitHub

1. Entra en https://github.com/H4CKLABORATORY/dexter-fusion-studio/actions/workflows/windows-installer.yml
2. Abre la compilación más reciente con estado verde (success).
3. En Artifacts, pulsa Dexter-Fusion-Studio-Windows-v0.3.0. GitHub puede pedir iniciar sesión para descargar artifacts.
4. Descomprime ese paquete y abre **Dexter-Fusion-Studio-Setup-v0.3.0.exe**.
5. Completa el asistente; al terminar abre Dexter Fusion Studio desde el menú Inicio. No hay que abrir consola ni instalar Python.

También se entrega un ZIP portable para ejecutar la app sin instalar: descomprime toda la carpeta y ejecuta DexterFusionStudio.exe. Deben permanecer juntos el archivo EXE, bin/ y _internal/.

## Qué queda funcionando al terminar

- Editor original de video para Free Fire, Shorts, TikTok y YouTube.
- Cortes y efectos FFmpeg, subtítulos con archivos SRT, memes aprobados y exportación MP4.
- Timeline v2 revisable para aceptar/corregir ediciones y sugerencias.
- ChatGPT: exportar resumen y guion, importación de JSON de edición, sin contratar una API.
- Código del motor IA Whisper (faster-whisper) empaquetado dentro del EXE.
- Incluye FFmpeg y FFprobe distribuidos como software de terceros con sus licencias.
- No instala Concat, FilmCraft, EffectCraft, Ollama o plugins automáticamente.

## IA gratuita después de instalar

La primera vez aparece el asistente de configuración. Pulsa **Preparar subtítulos IA gratis (Whisper tiny)** para descargar un modelo gratuito de voz (requiere Internet y espacio en disco; puede tardar). Después podrás transcribir tu voz en la pestaña de IA eligiendo tiny y CPU. La GPU RTX 3090 es opcional y CUDA no viene preconfigurado: no se promete aceleración GPU hasta verificar drivers y bibliotecas.

Para que la IA analice **fotogramas visuales**, necesitas Ollama y un modelo compatible instalados por separado; tienes un botón que abre la página oficial de descarga. La app no lo instala ni descarga modelos visuales a escondidas.

ChatGPT Plus y la API de OpenAI no son lo mismo. El puente gratuito con ChatGPT es mediante archivos. La API automática permanece deshabilitada si no hay clave local y autorización explícita, y puede generar cargos.

## Qué todavía no hace al 100 %

- No interpreta de forma garantizada cada baja, chiste, emoción o meme de Free Fire.
- No controla desde este chat tu Windows ni tu sesión de ChatGPT.
- No convierte toda la capacidad de Concat, FilmCraft o EffectCraft en funciones propias.
- No publica automáticamente en ninguna red social.
- No viene con todos tus guiones personales; importa tu biblioteca local cuando lo desees.

## Seguridad

El instalador es una compilación sin firma digital de pago. Windows podría mostrar una advertencia. Verifica que lo hayas obtenido de tu propio GitHub y examina los artefactos; no ejecutes copias desconocidas ni desactives tus protecciones. Las grabaciones y bibliotecas se guardan en Documentos/DexterFusionStudio, no dentro de la carpeta del programa, para conservarlas al actualizar o desinstalar.

Los binarios de FFmpeg incorporados conservan su licencia GPL y sus obligaciones de redistribución; más información en THIRD_PARTY_NOTICES.md.
