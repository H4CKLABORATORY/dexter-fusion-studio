# DEXTER FUSION STUDIO — Workspace Qt profesional (primera etapa)

**Estado:** interfaz PySide6 real en rama `feature/studio-qt-workspace`; los renders siguen usando FFmpeg. La interfaz Tkinter antigua está disponible como alternativa durante la migración.

## Diferencia entre imágenes

- La propuesta visual (concept art) es una REFERENCIA, no una captura ni una característica implementada.
- La captura en GitHub Actions `Dexter-Studio-Qt-Real-Screenshot` sí proviene de `QWidget.grab()` sobre el programa ejecutándose en Qt sin videos privados.
- La interfaz V1 no está completa ni es equivalente a Adobe After Effects, Premiere, CapCut ni Katana.

## Funciones reales en esta entrega

| Módulo | Estado |
| --- | --- |
| Ventana de escritorio Qt oscura, paneles redimensionables, herramientas y menús | Implementado |
| Biblioteca de grabación y lista de efectos | Implementado (una fuente por proyecto) |
| Reproducción del archivo fuente mediante Qt Multimedia | Implementado (compatibilidad según códecs de Qt) |
| Poster de un fotograma extraído del MP4 real | Implementado |
| Timeline visual de V1 con clips de FFmpeg, selección y zoom de tiempo | Implementado |
| A1 con audio fuente sincronizado y forma de onda FFmpeg | Implementado (máximo 240 s de muestras) |
| Deshacer, rehacer, dividir, recortar, mover, eliminar clips | Implementado |
| Inspector con zoom 1–1,6 y presets de efectos FFmpeg | Implementado |
| Guardar timeline JSON, validar, aplicar y exportar MP4 | Implementado, render previo no compuesto |
| Pistas V2/V3/A2/A3 visibles | Reservadas; NO EDITABLES NI EXPORTABLES |
| Previsualización compuesta en tiempo real | Pendiente |
| Edición multifuente y mezcla multipista | Pendiente |
| Fotogramas clave, curvas de animación, máscara, motion tracking, keying, 3D | Pendiente |
| Motor de IA capaz de interpretar instrucciones arbitrarias como Katana | Pendiente |
| Instalador Windows firmado y actualización automática | Pendiente |

Las pistas pendientes están **rotuladas expresamente** para no simular capacidades. El visor reproduce el medio original; la composición definitiva se conoce después de exportar el MP4.

## Windows

1. Desde GitHub Actions, descarga el artefacto `DexterFusionStudio-Windows-Portable` del último run completado correctamente.
2. Extrae TODO el ZIP y ejecuta `DexterFusionStudio.exe` (no muevas solamente el .exe).
3. O, con código fuente, ejecuta `py -3 -m pip install -r studio-requirements.txt` y abre `INICIAR_ESTUDIO_WINDOWS.bat`.
4. Importa una grabación desde el disco, selecciona fragmentos, ajusta efectos y exporta.

El ZIP portable empaqueta PySide6 y los ejecutables FFmpeg/FFprobe para evitar instalación manual. Windows puede mostrar avisos SmartScreen porque todavía no tiene firma digital de un editor verificado.

## Calidad y siguientes entregas

- La compilación Windows incluye prueba del modelo, render MP4 real y prueba de arranque GUI Qt en modo sin pantalla.
- Se conserva la aplicación Tk original mientras la nueva no tenga paridad funcional.
- Siguiente módulo prioritario: **montaje multipista real (varios videos y audios) con previsualización compuesta y controles de volumen**; después, keyframes, motion graphics y análisis de referencias.
- Los componentes de terceros deben distribuirse respetando sus licencias. PySide6 usa términos LGPL/GPL/comercial; las distribuciones de FFmpeg pueden ser LGPL o GPL dependiendo de los componentes compilados. El producto no puede borrar los créditos o avisos legales de su código.
- Las imágenes de captura generadas por CI deben producirse desde la aplicación, no desde un mockup estático.

## Pruebas

```powershell
py -3 -m pip install -r studio-requirements.txt
py -3 -m unittest discover -s tests -v
py -3 studio.py
```

Ruta del workflow Linux: `.github/workflows/studio-qt.yml`. Para el ejecutable Windows: `.github/workflows/studio-windows.yml`.
