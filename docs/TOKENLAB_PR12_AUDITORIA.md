# Revisión externa del PR #12 — Dexter Fusion Studio / TokenLab

## Alcance y estado

Se inspeccionó el **diff completo del PR** contra `main`: 26 archivos cambiados al comienzo de esta revisión, código real y tests asociados, `CONTINUIDAD.md` y `TOKENLAB_CHECKPOINT.json`. PR inicial `OPEN/DRAFT`, base `97b088f7776a4433d82001308bd6e08c5453f53b`, head antes de la auditoría **`c32e6737f611082c090481c5f427a8d34103f6ff`**. No se solicitaron permisos ni se hicieron commits en `main`.

## Problemas detectados y corregidos en la rama

1. **Caché contaminada al cambiar modelo** (`fusion/tokenlab_skills.py`): `contar_tokens` y `comparar_prompts` tenían la clave de caché compuesta únicamente por nombre de skill y argumentos. Tras cambiar el selector de modelo OpenAI podía devolverse el resultado del modelo previo. Ahora la clave incluye el **modelo exacto**. Prueba de regresión con dos modelos y conteos diferenciados.
2. **Búsqueda incompleta** (`fusion/tokenlab_skills.py`): `buscar_repositorio` inspeccionaba únicamente `*.py`, ignorando documentación, JavaScript, HTML y configuraciones. Se amplió a extensiones de texto comunes, usando `os.walk` con exclusión de directorios temporales/symlinks, límite máximo de 5000 archivos y señal explícita `truncated`. Prueba que encuentra MD/JS y excluye `node_modules`.
3. **Cambio de sesión durante resumen activo** (`fusion/tokenlab_advanced.py`): `new_context` podía cambiar `self.compactor.manager` mientras llegaban resultados asíncronos de una compresión anterior; `restore_context` cambiaba campos antes de validar. Se impide cambiar o restaurar sesión con operación activa y se valida la restauración por completo **antes** de sustituir el estado visible. Pruebas de cambio concurrente y checkpoint inválido.
4. **Bypass del loopback** (`fusion/tokenlab_ollama.py`): una comprobación de prefijo de URL aceptaba valores ambiguos como `http://127.0.0.1:11434@evil.example`. Ahora `urlsplit` exige HTTP, hostname loopback, puerto, ausencia de usuario/contraseña/path/query/fragment. Pruebas de URL maliciosa y válida.
5. **Ejemplos JSON inconsistentes en el panel de skills** (`fusion/tokenlab_advanced.py`): `buscar_repositorio` se seleccionaba inicialmente, pero mostraba argumentos `texto` pertenecientes a otra skill. Se muestran ejemplos correctos cuando se cambia cada skill. Pruebas para los cuatro esquemas.
6. **Errores de validación escasamente explicados** (`fusion/tokenlab_skills.py`): se devolvía sólo `code`. Se agregó `message` legible para `ValueError/TypeError`, truncado; errores inesperados muestran mensaje genérico, sin revelar claves ni parámetros secretos. Regresión de límites inválidos.
7. **Imports sin uso**: eliminación de `embed_ollama` importado por la GUI tras cambiar a embeddings asíncronos, y de `json` en el compactador asíncrono.
8. **Cobertura de pruebas negativas**: escenarios de cambio de modelo, docs/JS ignorados, URL ambigua, cambio/recuperación de contexto durante compactación, checkpoint inválido, errores de límites y argumentos predeterminados de cada skill. Se mantiene la distinción **contract tests** frente a inferencia real Ollama.

No se detectaron marcadores TODO/FIXME añadidos por los 26 archivos iniciales en el diff del PR. La búsqueda no sustituye análisis estático externo ni auditoría de seguridad completa.

## CI y evidencia

- Baseline del usuario comprobado antes de esta auditoría: SHA `c32e6737f611082c090481c5f427a8d34103f6ff` y 4 CI SUCCESS: Qt run **39139681210**, Ollama run **39139681256**, Windows run **39139681212**, general run **39139681213**.
- SHA **final de código corregido y verificado**: `a3a5c0240d88802c3cc22205e0ed0597f400eb84` (no es el SHA de merge). Los cuatro workflows asociados a ese SHA finalizaron **SUCCESS** en GitHub:
  - General [39142870136](https://github.com/H4CKLABORATORY/dexter-fusion-studio/actions/runs/39142870136): **79 pruebas**, con skips Qt justificados por el runner sin PySide6.
  - Qt [39142870017](https://github.com/H4CKLABORATORY/dexter-fusion-studio/actions/runs/39142870017): **79 pruebas**, incluido cambio de modelo, restauración de sesión, búsqueda MD/JS y protección de URL.
  - Windows EXE [39142870112](https://github.com/H4CKLABORATORY/dexter-fusion-studio/actions/runs/39142870112): **46 pruebas**, EXE construido/ejecutado y artefacto portable publicado.
  - Ollama real [39142870093](https://github.com/H4CKLABORATORY/dexter-fusion-studio/actions/runs/39142870093): generación `llama3.2:1b`, resumen y embeddings `nomic-embed-text` reales, SUCCESS; generación A/B **1225.36 / 1006.95 ms** en ese runner.
- Los commits posteriores a ese SHA se limitan a revisión documental/checkpoint; no inferir que la rama `main` fue actualizada.
- El workflow OpenAI opt-in no equivale a llamada autenticada. `SKIPPED_NO_OPENAI_API_KEY` es ausencia de prueba, no éxito de proveedor.

## Pendientes de bloqueo real

- Dexter debe configurar el secreto GitHub Actions `OPENAI_API_KEY`, aplicar el label `tokenlab-openai-smoke` y verificar resultado de **una llamada real**.
- Dexter debe crear `H4CKLABORATORY/mira-neural-prompt-studio` como **Private**; después subir el ZIP SHA-256 `1e9e890c9b70478e9d1cbe55479891a29fb798748c84c05cd2e2eb5b69b0003e` y verificar commit + pruebas.
- Mantener PR #12 **DRAFT** hasta evidencias anteriores, CI final requerida en verde y autorización de merge. No se dispone de SHA final de `main` sin un merge real.

## Procedimiento exclusivo del propietario

Ver `docs/DEXTER_ACCIONES_OPENAI_Y_MIRA.md`. Este documento separa el flujo de secreto, el disparador de la prueba, la creación privada de repositorio y los comandos PowerShell. **Ninguna acción se ejecutó en la cuenta del propietario en virtud de la guía.**
