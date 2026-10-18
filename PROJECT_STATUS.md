# DEXTER FUSION STUDIO — ESTADO VERIFICABLE

## Meta
Editor audiovisual Windows de nivel profesional. El sistema aún NO es equivalente a Premiere, CapCut, After Effects o Higgsfield Katana. Prohibido presentar prototipos como producto final.

## Base de producción actual (`main`)
- Interfaz Qt/PySide6, proyecto editable, reproducción del archivo fuente y timeline visual con V1/A1.
- Herramientas de cortar, reordenar, recortar, undo/redo, 17 efectos FFmpeg, subtítulos, exportación MP4 y Director Creativo de intros independientes.
- Compilación portátil Windows mediante GitHub Actions. Las pruebas automáticas validan arranque de GUI y render; instalación en hardware del usuario pendiente.

## Cambio incorporado a main: pull request #11 (commit 0ff9445)
- Capas V2 de imágenes con tamaño, posición, transparencia y duración.
- Pistas A3 de música con duración, comienzo, recorte, volumen y mezcla real con el audio de V1/A1.
- Línea de tiempo Qt muestra imágenes y audio exportables, con edición de parámetros desde inspector.
- Selección de las capas por clic sobre sus bloques.
- Modo para ver y escuchar el MP4 final después de exportar; no es reproducción de composición en vivo.
- Capas persistidas en JSON, validación estricta y operaciones undo/redo.
- Pruebas sintéticas que confirman cambios en píxeles y presencia de tonos audio separados.

## Límites confirmados
- Todavía no admite varios videos independientes en V1/V2, transiciones complejas entre archivos diferentes ni keyframes de efecto.
- No hay formas de onda por pista A3 individual ni mezcla de audio de nivel DAW.
- Vista compuesta disponible después de renderizar, NO en vivo.
- Detección multimodal IA de escenas de Free Fire, motion tracking, máscara y composición 3D pendientes.
- Solo archivos locales; el repositorio de GitHub es público. No subir grabaciones, datos personales ni claves al código.

## Aprobación de funcionalidades
1. Código y pruebas automatizadas pertinentes.
2. MP4 real con mediciones de imagen y sonido para cambios de composición.
3. Captura auténtica de ventana Qt en ejecución (no ilustración IA).
4. ZIP Windows con EXE y prueba de arranque completada en CI.
5. Documentación actualizada y degradación segura ante medios faltantes.

## Continuidad
Consultar `NEXT_TASK.md`, `docs/WORKSPACE_QT.md`, el PR #11 (integrado) y el issue #10 antes de empezar nuevas funcionalidades. Todo avance debe citar commit, resultado de prueba y limitaciones.
