# ChatGPT + Dexter Fusion Studio (Etapa 3)

Hay dos conexiones distintas. **Ninguna usa tu sesión ni la suscripción de ChatGPT para facturar a la API.**

## Modo 1: Gratis, con ChatGPT del navegador o iPhone

No requiere clave API y no instala modelos de terceros.

1. Abre el programa Windows y selecciona un proyecto de Free Fire.
2. En **IA local · Etapa 3** puedes transcribir con faster-whisper si lo instalaste; también puedes añadir tu propio archivo SRT.
3. En **ChatGPT · Editor asistido**, pulsa **Preparar paquete para ChatGPT**.
4. En la carpeta del proyecto, revisa los archivos chatgpt-request.json y chatgpt-instructions.txt. El JSON contiene el título, una muestra del texto hablado y las escenas candidatas; NO contiene video, audio, imágenes, rutas completas ni claves. **Los diálogos sí pueden ser privados**.
5. Comparte voluntariamente ambos archivos en ChatGPT. Pide un JSON con los clips recomendados: el prompt ya está listo.
6. Copia la respuesta completa a un archivo con extensión .json en tu PC.
7. Pulsa **Importar respuesta JSON de ChatGPT**. El programa valida huella de proyecto, tiempos, zoom, efectos, transición, cantidad de clips y límites.
8. **Revisa** chatgpt-proposed-timeline.json y pulsa **Aceptar la propuesta revisada**. Si ya existe un montaje, pregunta antes y guarda respaldo.
9. Abre Timeline v2, corrige cortes y efectos, prepara y exporta tu video como siempre.

Comandos alternativos sin ventana:

    py -3 -m fusion.cli chatgpt-export --project "C:\RUTA\PROYECTO"
    py -3 -m fusion.cli chatgpt-import --project "C:\RUTA\PROYECTO" --response-file "C:\RUTA\respuesta-chatgpt.json"
    py -3 -m fusion.cli chatgpt-approve --project "C:\RUTA\PROYECTO"
    py -3 -m fusion.cli prepare --project "C:\RUTA\PROYECTO"
    py -3 -m fusion.cli render --project "C:\RUTA\PROYECTO"

Si necesitas sustituir archivos que ya existen añade --overwrite al comando correspondiente, solo tras comprobar qué se reemplazará.

### Lo que puede y no puede hacer ChatGPT

ChatGPT puede sugerir secuencias, ganchos, cortes, títulos, transiciones, guiones y memes por sus categorías. **Si solo recibe transcripciones y escenas sugeridas, no ha visto el video original** y no sabe con certeza si un momento tiene una jugada sorprendente o un chiste visual. Para análisis visual detallado, se necesitan fotogramas/video compartidos explícitamente; la versión automática actual NO los comparte.

## Modo 2: API de OpenAI (opcional, puede costar dinero)

**No confundir con la suscripción ChatGPT Plus.** La facturación de API es independiente. Este modo está completamente desactivado salvo orden explícita. El puente no inicia sesión en ChatGPT ni intercambia cookies, contraseñas o sesiones.

Solo si tienes cuenta de API con presupuesto propio:

1. Configura OPENAI_API_KEY como variable de entorno **en tu PC**, jamás en GitHub.
2. Exporta primero chatgpt-request.json y revísalo.
3. Autoriza una llamada individual a Responses API:

    py -3 -m fusion.cli chatgpt-api --project "C:\RUTA\PROYECTO" --model gpt-4.1-mini --allow-paid-api

4. Se guardará un borrador para revisar, sin aplicarlo automáticamente al timeline.

Cada ejecución de ese comando puede generar cargos; nunca se reintenta automáticamente ni se ejecuta en segundo plano. El nombre del modelo es configurable según tu acceso; ningún modelo se instala con este comando. El módulo solo transmite un JSON de texto limitado al endpoint oficial, con store=false. La API y las políticas de retención de OpenAI son independientes de tu almacenamiento local; comprueba sus condiciones antes de compartir material.

Documentación: https://platform.openai.com/docs/api-reference/responses y https://help.openai.com/en/articles/9039756-managing-billing-settings-on-chatgpt-web-and-platform

## Seguridad y permisos

- Tus guiones privados, voces, videos y clips originales permanecen locales.
- Compartir chatgpt-request.json en el chat es una acción deliberada.
- El JSON devuelto se trata como **datos no fiables**, nunca como código; no puede establecer rutas ni ejecutar herramientas, y debe pertenecer a la misma grabación.
- Se conservan copias del timeline antes de un reemplazo aprobado.
- No hay publicación automática en YouTube ni TikTok.
- Todos los memes y recursos de terceros necesitan permiso y revisión.
- Este puente no sirve para controlar remotamente tu PC desde esta conversación; eso requeriría un servidor/connector adicional autorizado.
