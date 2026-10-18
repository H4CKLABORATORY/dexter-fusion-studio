# DEXTER FUSION STUDIO — Workspace Qt profesional (primera etapa)

**Estado:** interfaz PySide6 incorporada a `main`; desarrollo iterativo en ramas. Los renders usan FFmpeg. La interfaz Tkinter antigua está disponible como alternativa durante la migración.

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
| V2 imagen fija (posición, escala, opacidad y aparición) | Implementado, se guarda y exporta en MP4 |
| A3 música con inicio, recorte y ganancia, mezclada con audio original | Implementado, se guarda y exporta en MP4 |
| V3 y A2 | Pendientes, no editables ni exportables |
| Formas de onda A3 individuales | Pendiente; la forma de onda verificada es la del audio original A1 |
| Previsualización compuesta en tiempo real | Pendiente |
| Edición multifuente y mezcla multipista | Pendiente |
| Fotogramas clave, curvas de animación, máscara, motion tracking, keying, 3D | Pendiente |
| Motor de IA capaz de interpretar instrucciones arbitrarias como Katana | Pendiente |
| Instalador Windows firmado y actualización automática | Pendiente |

**Importante:** ahora V2 y A3 sí afectan el MP4. Las imágenes y pistas musicales se editan desde la lista «Pistas reales V2 · A3» del inspector (doble clic para modificar duración, posición, opacidad y ganancia). Se muestra la duración de A3, pero todavía no dibuja su forma de onda individual. Los clips principales continúan usando una sola fuente de video.

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
- Siguiente módulo prioritario: **previsualización de composición** a partir del render completo, más pistas multimedia (varios videos, mixer de audio y keyframes); después, motion graphics y análisis de referencias.
- Los componentes de terceros deben distribuirse respetando sus licencias. PySide6 usa términos LGPL/GPL/comercial; las distribuciones de FFmpeg pueden ser LGPL o GPL dependiendo de los componentes compilados. El producto no puede borrar los créditos o avisos legales de su código.
- Las imágenes de captura generadas por CI deben producirse desde la aplicación, no desde un mockup estático.

## Pruebas

```powershell
py -3 -m pip install -r studio-requirements.txt
py -3 -m unittest discover -s tests -v
py -3 studio.py
```

Ruta del workflow Linux: `.github/workflows/studio-qt.yml`. Para el ejecutable Windows: `.github/workflows/studio-windows.yml`.

## Controles V2 y A3 (nueva etapa)

1. Abre un proyecto y pulsa **＋ Imagen V2** o **＋ Música A3** en la barra superior o inspector.
2. La imagen se sitúa inicialmente durante los primeros 3 segundos, centrada horizontalmente; la música utiliza el fragmento más largo que quepa en el montaje, con ganancia inicial 0,35.
3. Selecciona la pista desde **Pistas reales V2 · A3** y pulsa **Editar** o haz doble clic. Ajusta entrada/salida, transparencia, tamaño, posición, inicio dentro del archivo y volumen según tipo.
4. Guarda. La configuración queda en `timeline-v2.json`, propiedad `layers`, sin copiar los originales al repositorio.
5. Exporta MP4; el motor incorpora **verdaderas imágenes y pistas de sonido**. Se verifican los archivos y límites antes de exportar.

Los archivos importados permanecen en el disco local. Si se eliminan o mueven, el programa solicitará corregir la ruta. Las pistas V2 son solo imágenes fijas; no admiten actualmente clips de video superpuestos.
