# DEXTER FUSION STUDIO — Director creativo local

Inspiración funcional: Higgsfield Katana (referencias, instrucciones y montaje).
**Implementación original, gratuita y local**: no incorpora Katana, Claude Opus, modelos propietarios ni generación fotorealista.

## Funciones añadidas

1. Escribe una instrucción como: **Haz una intro cinematográfica verde con texto «DEXTER FF» de 4 segundos**. El programa interpreta título, duración (1–15 s), orientación vertical/horizontal, color (verde, rojo, azul, morado, dorado) y estilo (neón, cinematic, retro).
2. Genera una **intro MP4 real** en Windows usando FFmpeg con movimiento tipográfico, borde de color, entrada/salida suave y codificación H.264.
3. Importa un video de referencia y **detecta cortes visuales aproximados** con FFmpeg. Aplica sus duraciones, en orden, al comienzo del video de tu proyecto. Puedes revisar y corregir el timeline antes de exportarlo.
4. Guarda especificación JSON de la intro y metadatos de referencia para repetirlos.

**Límites actuales:** no replica efectos internos, movimiento 3D, objetos, personajes, colorimetría o banda sonora; no separa automáticamente las mejores jugadas y no comprende cualquier descripción compleja. Un video de referencia no se copia a la exportación: se toman solo los tiempos aproximados de cortes para aplicarlos a **tu video original**. Algunas referencias con transiciones lentas no tienen cortes detectables.

## Interfaz gráfica

En el proyecto abre **Timeline v2** y escribe la instrucción en **Director creativo (local)**. Pulsa **Crear intro MP4** o **Aplicar cortes de video de referencia al proyecto**. El segundo botón deja una línea de tiempo editable, que debes revisar. En esta etapa el video de intro se genera por separado y **no se inserta automáticamente** en el montaje principal.

## Línea de comandos

Desde la carpeta del programa en Windows:

```powershell
py -3 -m fusion.cli motion --prompt "Crea una intro neón verde con texto «DEXTER FF» de 4 segundos" --output "intro.mp4"
py -3 -m fusion.cli motion --prompt "Crea un logo rojo horizontal de 3 segundos" --title "DEXTER FF" --output "intro-youtube.mp4" --platform youtube
```

Para analizar una referencia antes de editar:

```powershell
py -3 -m fusion.cli reference --project "C:\\Ruta\\MiProyecto" --reference "C:\\Ruta\\referencia.mp4" --analyze-only
```

Para aplicar ritmo al timeline (requiere confirmación explícita si ya existe uno):

```powershell
py -3 -m fusion.cli reference --project "C:\\Ruta\\MiProyecto" --reference "C:\\Ruta\\referencia.mp4" --prompt "estilo cinemático" --overwrite
py -3 -m fusion.cli prepare --project "C:\\Ruta\\MiProyecto" --overwrite
py -3 -m fusion.cli render --project "C:\\Ruta\\MiProyecto"
```

Necesitas FFmpeg y FFprobe accesibles en PATH, compilación con drawtext y soporte de codificación libx264. El motor no descarga modelos ni usa créditos. No introduzcas referencias con música, marcas o imágenes que no tengas derecho a reutilizar cuando pretendas copiar contenido protegido.

## Siguientes etapas

- Director de estilo que analiza tipografía, color y movimiento de la referencia; requiere visión computacional y evaluación manual.
- Composición automática de títulos como capas editables con transiciones de vídeo más elaboradas y sincronización con golpes musicales.
- Detección multimodal de Free Fire y selección de momentos reales, verificable por el usuario.
- Integración opcional de generación de escenas con modelos externos sujeta a costos, consentimiento y licencia.
