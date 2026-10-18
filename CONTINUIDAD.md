# CONTINUIDAD — DEXTER FUSION STUDIO / TOKENLAB

## 2026-10-18 · Integración incremental del contador A/B

- Base inspeccionada: `main` SHA `97b088f7776a4433d82001308bd6e08c5453f53b`.
- Rama: `feature/tokenlab-qt-count-ab`.
- Último commit funcional verificado por el conector antes de escribir esta bitácora: `a8c5fdda1fc160c0b7e1d31bc37233036a5a7609`.
- Inspección perezosa: `studio.py`, `fusion/studio_qt.py`, `studio-requirements.txt`, `tests/test_smoke.py`, `.github/workflows/studio-qt.yml`, `.github/workflows/studio-windows.yml`, `README.md`, `PROJECT_STATUS.md`, `NEXT_TASK.md`. No se reescribió el motor de render.
- Archivos añadidos: `fusion/tokenlab_tools.py`, `fusion/tokenlab_dialog.py`, `tests/test_tokenlab_tools.py`, `docs/TOKENLAB.md`. Modificados: `fusion/studio_qt.py`, `studio-requirements.txt`, `.github/workflows/studio-windows.yml`.
- Funciones identificadas: `StudioWindow._make_ui`, `StudioWindow._build_menus`, `TokenLabDialog.compare`, `TokenLabDialog.save`, `compare_texts`, `counter_for_model`, `AtomicTaskCheckpoint.save/load`.
- Validación local del núcleo sin dependencia: recuperación de checkpoint/validación de rutas/SHA-256/tipos. Paridad tiktoken requiere CI porque PyPI no fue accesible localmente. Qt real requiere CI con PySide6. No hubo inferencia real (sin Ollama ni claves OpenAI).
- MIRA v2.4 se integró en un ZIP local separado desde su paquete fuente original; no hay repositorio MIRA autorizado con nombre inequívoco para abrirle PR, por lo que no se escribió al proyecto web `dexter-ai-web` no relacionado.

## Pendiente siguiente

1. Ejecutar CI de GitHub Actions sobre PR y corregir errores de pruebas o empaquetado.
2. Confirmar compatibilidad de `tiktoken` con gpt-4o/gpt-4.1 y validar conteo.
3. Ejecutar pruebas de inferencia reales solo cuando haya modelo Ollama funcionando y claves privadas autorizadas, con pruebas de latencia y cancelación.
4. Conectar tres capas de contexto y más skills en Qt, solo tras demostrar su integración y pruebas completas; nunca presentarlas como finalizadas.

## Regla de memoria

Revisadas las instrucciones activas del proyecto; reglas más recientes priman sobre anteriores. Este archivo es un registro de continuidad del proyecto y **no** una modificación automática de la memoria interna de ChatGPT.
