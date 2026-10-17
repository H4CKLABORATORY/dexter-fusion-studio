# Modo Creador: toma repetida (primera mejora inspirada en AutoEdit)

Esta función es una implementación ORIGINAL para Dexter Fusion Studio. **No incorpora el plugin comercial AutoEdit de Eleven Percent, ni Claude AI, ni código propietario.** Tampoco confunde ese plugin con el proyecto libre Auto-Editor de WyattBlue.

## Disponible en esta rama

- Revisa subtítulos SRT en español u otros idiomas para detectar dos intervenciones **consecutivas y casi idénticas**.
- Exige por defecto 5 palabras, 3 palabras diferentes, parecido >= 90 % y pausas inferiores a 3 s. Evita marcar repeticiones cortas intencionales (por ejemplo «no, no, no»).
- Crea `retakes-report.json` con los momentos y el motivo de cada sugerencia.
- Ofrece un botón **Analizar tomas repetidas** en Timeline v2: muestra el informe, sin efectuar cortes.
- Ofrece un comando para **aplicar solamente índices revisados** sobre el JSON de la línea de tiempo.
- No mueve, borra, comparte ni sobrescribe archivos MP4 originales.

## Cómo utilizar

1. Crea un proyecto con tu video.
2. Importa un SRT de voz o pulsa **Subtitular mi voz** (requiere faster-whisper local).
3. Abre **Timeline v2** y genera la línea de tiempo.
4. Pulsa **Analizar tomas repetidas** para obtener propuestas.
5. Abre `retakes-report.json`; revisa con el video los índices `0, 1, 2...`.

También puedes analizarlo desde PowerShell (en Windows, dentro de la carpeta del programa):

```powershell
py -3 -m fusion.cli retakes --project "C:\\RUTA\\AL\\PROYECTO" --overwrite
```

Para aplicar ÚNICAMENTE las sugerencias 0 y 2 después de revisarlas:

```powershell
py -3 -m fusion.cli retakes --project "C:\\RUTA\\AL\\PROYECTO" --apply "0,2" --overwrite
py -3 -m fusion.cli prepare --project "C:\\RUTA\\AL\\PROYECTO" --overwrite
py -3 -m fusion.cli render --project "C:\\RUTA\\AL\\PROYECTO"
```

`--apply` **no se ejecuta automáticamente** desde el botón. No se considera que el detector entienda la comedia, la historia ni qué repetición fue deliberada. Tampoco detecta malas tomas que no repitan palabras. El SRT debe ser razonablemente fiel y tener tiempos correctos.

## Próximas funciones, todavía no implementadas

- Subtítulos palabra por palabra con animación, zonas seguras y estilos configurables.
- Detección de muletillas, inicio fallido de frase y correcciones.
- Detector multimodal de jugadas Free Fire, risas, kills y momentos destacados.
- Biblioteca de efectos extraídos en forma de «recetas técnicas» de videos de referencia autorizados, con revisión antes de exportar.
- Sincronización con golpes de audio, gráficos y transiciones.
- Opcionalmente, integración de herramientas de código abierto respetando sus licencias.

El reel promocional enviado para comparación muestra funciones del plugin comercial; no equivale a un proyecto de edición original y no permite recuperar sus filtros o modelos internos.
