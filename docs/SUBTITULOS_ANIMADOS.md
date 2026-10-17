# Subtítulos animados locales · Etapa experimental

Dexter Fusion Studio incluye dos estilos originales de subtítulos animados implementados con formato ASS y FFmpeg/libass. No requiere APIs externas ni descargar efectos comerciales.

## Estilos

- **classic** (por defecto): subtítulos SRT estándar como antes.
- **karaoke**: frases divididas en grupos cortos, palabras resaltadas progresivamente y entrada suave.
- **punch**: resaltado karaoke más entrada animada de escala para videos rápidos.

La letra y el margen vertical se adaptan a YouTube 16:9, Shorts y TikTok 9:16. Aun así, hay que verificar la zona segura de cada plataforma y las palabras largas.

## Uso (Windows)

1. Carga tu grabación y crea un proyecto.
2. Importa un SRT o usa la transcripción local opcional **Whisper** para generar uno.
3. Genera o carga la línea de tiempo en **Timeline v2**.
4. En **Estilo de subtítulos** escoge `classic`, `karaoke` o `punch`.
5. Pulsa **Guardar y preparar edición**, revisa la línea de tiempo y **Exportar MP4**.

El exportador construye un ASS temporal en el directorio de trabajo, lo aplica con el filtro `subtitles` de FFmpeg y conserva el archivo fuente. El MP4 exportado **sí lleva el texto incrustado**; no exige que el receptor tenga el archivo SRT aparte.

## Limitaciones explícitas

Los SRT habituales contienen la hora de cada frase, **no la de cada palabra**. Por eso el resaltado utiliza una estimación según la longitud de las palabras. No garantiza correspondencia exacta con el ritmo de la voz. Un alineador local de voz por palabras será necesario para lograr sincronía muy precisa.

No se detectan automáticamente jugadas, memes, emociones ni cortes virales. Los efectos visuales pertenecen a este proyecto y no son una implementación del plugin propietario AutoEdit.

## Comprobación

```powershell
py -3 -m unittest tests.test_caption_styles -v
```

También están las pruebas existentes de la línea de tiempo:

```powershell
py -3 -m unittest discover -s tests -v
```

Exportar subtítulos ASS requiere FFmpeg compilado con soporte libass (filtro `subtitles`), además de FFprobe. Si el video no tiene SRT, no se crean textos ficticios.

## Mejoras pendientes

- Transcripción/alineación por palabra usando modelos locales opt-in.
- Biblioteca de plantillas reutilizables a partir de estilos autorizados y referencias analizadas.
- Personalización de colores, tipografía, posición y moderación de subtítulos.
- Edición musical al ritmo y análisis visual de gameplay.
