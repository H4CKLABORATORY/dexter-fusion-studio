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


## Validación GitHub Actions · 2026-10-18

- SHA de **código integrado probado**: `2094616a2dc63cf879ea4c603412faaf0c042452`.
- `Studio Qt — probar interfaz` run [39092395492](https://github.com/H4CKLABORATORY/dexter-fusion-studio/actions/runs/39092395492): **success**, 44 tests OK, incluidos diálogo Qt, checkpoint y paridad oficial `tiktoken 0.14.0` para gpt-4o/gpt-4.1.
- `Verificar Dexter Fusion Studio v0.2` run [39092395481](https://github.com/H4CKLABORATORY/dexter-fusion-studio/actions/runs/39092395481): **success**, 44 tests, los 2 específicos Qt omitidos justificadamente porque ese runner no instala PySide6; sí ejecutados con éxito en CI Qt.
- `Studio Qt — Windows EXE portable` run [39092395486](https://github.com/H4CKLABORATORY/dexter-fusion-studio/actions/runs/39092395486): **success**, 14 tests OK incluyendo tokenizador y UI, EXE empaquetado y captura.
- Error del primer run general: `ModuleNotFoundError: No module named 'tiktoken'` porque `verify.yml` no instalaba esa dependencia; se corrigió antes de estos runs verdes.
- No se hicieron pruebas con una API OpenAI real ni un modelo Ollama activo; no se disponía de credenciales/proveedor. No presentar esa validación como realizada.

### Próximo checkpoint
El siguiente trabajo es conectar el resto de las capacidades de `GestorContexto`, skills y resúmenes con pruebas de comportamiento, evaluar costes de inferencia y añadir diagnósticos de cancelación con proveedor real; conservar cambios incrementales basados en el SHA anterior.

## 2026-10-18 — TokenLab full UI and real Ollama proof

- Start checkpoint/head: `97bc8a966baa18c2b7d8c1bf7f64b0a78510f121`.
- Work includes: `tests/tokenlab_live_probes.py`, `.github/workflows/tokenlab-ollama.yml`, `fusion/tokenlab_context.py`, `fusion/tokenlab_skills.py`, `fusion/tokenlab_advanced.py`, `fusion/tokenlab_ollama.py`, `tests/test_tokenlab_workspace.py`; modified `fusion/tokenlab_dialog.py` and Windows test workflow.
- UI: three-layer memory, checkpoint restore, exact/real semantic dedup, prioritization JSON 60/30/10, four strict JSON skills; memory compaction and semantic embeddings use a real localhost Ollama adapter, never fake outputs.
- Successful real Ollama run [39093243927](https://github.com/H4CKLABORATORY/dexter-fusion-studio/actions/runs/39093243927): install Ollama, pull `llama3.2:1b` and `nomic-embed-text`, summary and embeddings real SUCCESS, A/B prompt input 35/36 tokens, output 3/24, latencies 1248.99/999.81 ms.
- Successful Ubuntu verify run [39093243883](https://github.com/H4CKLABORATORY/dexter-fusion-studio/actions/runs/39093243883): 50 tests SUCCESS, four Qt tests skipped in runner without Qt. Qt dedicated run [39093243896](https://github.com/H4CKLABORATORY/dexter-fusion-studio/actions/runs/39093243896): 50 tests SUCCESS including tabbed workspace.
- Additional context enhancements: preserve permanent facts and reject compaction when protected facts disappear; no GUI claims of real cancellation or streaming yet.
- Current source code head for the provider addition: `054d86a5bb3a034dcd80c3e837063c1a3b771470`. Later commits may be needed before merge.
- Remaining: real authenticated cloud-provider smoke test via private repository secret, independent MIRA repo creation, optional responsive/cancellable GUI request handling, then PR readiness and merge SHA. The connected GitHub integration has no new-repository action. Do not merge until evidence exists.

## 2026-10-18 · Streaming Qt, PR #12 y pruebas de contrato (continuación verificada)

- Punto de partida remoto inspeccionado: PR #12 `open/draft`, SHA `b0ff8db1e8078bf9eacf9bf524827c847c904982`, todos sus cuatro workflows (Qt, Windows, Ollama, general) en estado SUCCESS. Sin merge.
- SHA último cambio de código de esta sesión (antes de actualizar continuidad): `77a098d7284b78ff2480186358cc62a13c3c3b7c`.
- Añadidos `fusion/tokenlab_stream.py`, `fusion/tokenlab_context_async.py`, `tests/test_tokenlab_stream.py`, `tests/test_tokenlab_compactor.py`, `tests/test_tokenlab_live_probe_contract.py`, `.github/workflows/tokenlab-openai.yml`. Actualizados `fusion/tokenlab_advanced.py`, `docs/TOKENLAB.md` y `.github/workflows/studio-windows.yml`; sólo se leyeron rutas específicas relevantes.
- Streaming de resumen e inferencia Ollama ahora usa red Qt asíncrona, `QNetworkReply.abort()` para cancelación, timeout, errores de HTTP/NDJSON y progreso incremental. La compactación de contexto es transaccional: al cancelar o fallar, el contexto anterior sigue intacto.
- Pruebas Qt desde servidor HTTP **de prueba**, no inferencia real: éxito, timeout, cancelación, HTTP 503, errores NDJSON, conectividad, botones y rollback. Primera ejecución halló un error de `int(NetworkError)` (corregido), después Windows produjo TIMEOUT para puerto inaccesible (test acepta ambos códigos de fallo explícitos). No ocultar estas incidencias.
- CI general [39139460278](https://github.com/H4CKLABORATORY/dexter-fusion-studio/actions/runs/39139460278) y Qt [39139460267](https://github.com/H4CKLABORATORY/dexter-fusion-studio/actions/runs/39139460267) SUCCESS al consultar. Windows [39139460329](https://github.com/H4CKLABORATORY/dexter-fusion-studio/actions/runs/39139460329) y Ollama [39139460263](https://github.com/H4CKLABORATORY/dexter-fusion-studio/actions/runs/39139460263) aún estaban en progreso en esa consulta; actualizar el estado al revisar.
- Workflow OpenAI con secreto `OPENAI_API_KEY` publicado; ejecución manual o al poner etiqueta `tokenlab-openai-smoke` al PR (mismo repo, no forks); una sola llamada, timeout y skip explícito sin secreto. **Sin prueba real OpenAI verificada**. La activación `workflow_dispatch` puede requerir que el archivo esté en la rama por defecto, por eso existe el evento de etiquetado pre-merge.
- MIRA: listado GitHub accesible contiene cuatro repositorios y ninguno `mira-neural-prompt-studio`; sin herramienta `create_repository`. ZIP validado localmente SHA-256 `1e9e890c9b70478e9d1cbe55479891a29fb798748c84c05cd2e2eb5b69b0003e`; guía `MIRA_PUBLICACION_SEGURA.md` preparada. No subir a repositorio ajeno ni afirmar publicación.
- MIRA verificada aquí por grupos: 10 tests Python de backend/seguridad/tokenlab, 2 tests de UI/tokenlab-integración y 3 archivos JS: OK; suite completa se interrumpió por timeout durante tests visuales, no afirmar aprobación global.
- PR #12 continúa DRAFT, no fusionado. Descripción actualizada con funciones reales y límites. Se requiere secreto en GitHub y repositorio propio MIRA para finalizar las prioridades.

### Próxima tarea exacta

1. Consultar resultados finales de Windows/Ollama en el último SHA y corregir errores si los hay.
2. Verificar una ejecución de OpenAI con `OPENAI_API_KEY` (usuario lo configura directamente en Settings, nunca pegar al chat) y disparador etiquetado.
3. Cuando el usuario cree `H4CKLABORATORY/mira-neural-prompt-studio`, publicar el ZIP validado con commit verificable en ese repositorio y CI, sin usar 1UP-ANIME.
4. Revisar el PR para retirar DRAFT, efectuar merge autorizado tras pruebas y registrar SHA real de `main`. No generar valores ficticios.
