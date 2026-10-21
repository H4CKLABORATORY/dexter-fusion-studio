# DEXTER HERMES: fases y evidencia local

Fecha de sesión: 20 de octubre de 2026, America/Mexico_City. Los timestamps de
GitHub, SQLite y checkpoints pueden corresponder al 21 en UTC.

## Base preservada

- PR #22: `616f0af0c54c5d7c29dd09157aeff5d7b5d571eb`, draft, no fusionado.
  Checks consultados: Checkpoints y Verificar Studio, success.
- PR #23: `306be5aa2ae554b136bb06ff6d7f74104d6340ce`, draft sobre la rama del #22.
  Checks consultados: Cloud Monitor, Checkpoints y Verificar Studio, success.
- Esta rama parte del SHA del #23. No copia ni sustituye esos PR.
- Esos checks no ejecutaban la suite de `agent_dispatch`; este incremento la añade,
  junto con cola DAG y workspaces, en Linux y Windows.

## Implementado y probado

1. Diagnóstico seguro del puente, presupuesto configurable, rechazo de respuestas
   truncadas, migración de cola antigua y fallo de búsqueda capturado después de claim.
2. DAG persistente reutilizando el planificador: seis roles, hasta 64 nodos,
   dependencias, IDs idempotentes, eventos transaccionales y un slot de inferencia
   por cola. Descendientes no avanzan tras fallo. Recuperación manual sin replay.
3. Adaptador de repositorio explícitamente autorizado: worktree por tarea,
   raíz/archivos permitidos, hash previo, reemplazo exacto, rollback con hash posterior,
   pruebas predefinidas y timeout. No hace push, merge, instalación ni shell generado.
4. Detección de catálogo real de proveedores con hora. No se presume acceso cloud.
5. Handoff local real: Codex envió un fragmento público a Qwen; Qwen propuso JSON
   para validar tipo de rol antes del lookup en frozenset. Codex revisó el cambio,
   aplicó con hash, probó rollback exacto, reaplicó y ejecutó siete pruebas PASS.
   Antes del cambio, roles lista/dict reproducían dos TypeError en la nueva regresión.

Flujo operativo: especificación autorizada → DAG durable → propuesta Qwen →
revisión Codex/humana → edición acotada en worktree → pruebas → commit/draft PR.
`completed` en la cola significa respuesta de texto final; no equivale a cambio
aprobado, pruebas aprobadas ni tarea de producto terminada.

## Medición y causa raíz

Hardware observado: RTX 3090, 24576 MiB VRAM; RAM física 137438953472 bytes (128 GiB).
VRAM usada en observación inicial: 19216 MiB. No representa pico durante benchmark.
API LM Studio `/api/v0/models`: Qwen `qwen3.8-27b-defiance-uncensored-mtp`, IQ4_XS,
cargado; contexto cargado 8192, máximo anunciado del modelo 262144.

Reproducción usando el prompt privado fallido, sin publicar su texto ni memoria:

| Intento | Presupuesto | Resultado | Tiempo |
|---|---:|---|---:|
| Original reproducido | 2400 | length, final vacío; 2400 tokens de razonamiento | 38.891 s |
| Worker corregido, nuevo intento explícito | 8192 | completed, 3740 caracteres finales | 51.188 s |
| Propuesta pequeña de código | 8192 | completed, revisión y pruebas PASS | 8.641 s |

Son mediciones de tareas diferentes o con presupuesto distinto, no una aceleración
ni una estimación de fiabilidad. El intento corregido no reejecutó ni alteró el
registro privado fallido: se creó una tarea nueva en estado de ensayo separado.
Benchmark sintético reproducible en `benchmark_local.py`; resultados adjuntos a
esta fase en `experiments/local-core-benchmark.json`. Modelo caliente, concurrencia
uno, tres muestras por caso; tokens/s son tokens de salida por tiempo de pared,
incluyen espera y razonamiento. No son velocidad pura de decodificación ni p95.

Resultado sintético: short 3/3 completed, mediana 1.031 s, máximo 1.328 s;
engineering 3/3 completed, mediana 42.969 s, máximo 44.390 s.
Validación focalizada del incremento: 27 pruebas PASS (puente 10, planificador 7,
DAG durable 6, workspace 4). Suite HERMES ampliada: 108 casos, 94 PASS,
12 omitidos por harness POSIX y dos fallos del contrato de propuestas. Los mismos
dos fallos se reprodujeron por separado sobre la rama base del #23; no se cambió
ni debilitó ese contrato para aprobar Windows. Checkpoints y scheduler también PASS.

Locally Uncensored está abierto, pero no se verificó contrato API. Su proceso
principal no mostró listener propio en la consulta; eso no demuestra inexistencia
de API en procesos auxiliares. No se integra por una suposición. Ollama no devolvió
catálogo válido en la prueba. ChatGPT carece de adaptador verificado en este motor.

## Decisiones de ingeniería y fuentes

- **DAG:** solo nodos cuyas dependencias terminaron son elegibles. Se conserva el
  planificador existente; no se añade framework. [Python graphlib](https://docs.python.org/3/library/graphlib.html).
- **Colas y Little:** `L = λW` relaciona ocupación media, llegada y tiempo total
  en régimen estable. Medir espera y servicio por separado antes de estimar capacidad;
  seis muestras no prueban estabilidad. [Sigman, Columbia](https://www.columbia.edu/~ks20/stochastic-I/stochastic-I-LL.pdf).
- **Amdahl:** `S(N) ≤ 1 / (s + (1-s)/N)`; muchos roles compartiendo una GPU no
  multiplican su capacidad. Empezar con N=1 para inferencia; comparar N=2 solo en
  experimento futuro con latencia, memoria y calidad. [MIT 6.172](https://ocw.mit.edu/courses/6-172-performance-engineering-of-software-systems-fall-2018/543e419bff1ed05b1a649115c24c44b3_MIT6_172F18_lec7.pdf).
- **Fiabilidad:** timeouts, errores clasificables y reintentos limitados solo para
  efectos idempotentes. Esta fase usa cero retries automáticos. Una inferencia incierta
  bloquea el slot hasta revisión. [AWS](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/).
- **Eventos:** cambios de estado y auditoría juntos; no confundir event log con replay
  determinista de efectos externos. Temporal es referencia de diseño, no dependencia
  instalada. [Temporal](https://docs.temporal.io/workflow-execution).
- **Durabilidad:** claim y plan usan `BEGIN IMMEDIATE`; SQLite aún puede reportar
  contención. No se promete entrega exactamente una vez del proveedor. No se habilita
  WAL sin necesidad medida. [SQLite](https://www.sqlite.org/lang_transaction.html).
- **API:** catálogo accesible e inferencia exitosa son observaciones diferentes.
  [LM Studio](https://lmstudio.ai/docs/developer/openai-compat/chat-completions).

No hay fundamento para prometer aceleración cuántica en este hardware y software.

## Pendiente, con criterios de aceptación

- Aplicar esta versión al servicio de uso diario tras parar workers antiguos y
  respaldar la cola: no se reemplazó el proceso que ya escuchaba en 18765.
- Sandbox Windows por proceso/Job Object y aislamiento de red/credenciales para
  ejecutar cambios no confiables. La lista de comandos no sustituye aislamiento.
- Autorizaciones persistentes firmadas por propuesta, auditoría de identidad y
  vínculo obligatorio entre propuesta, revisión, resultados y commit; hoy el
  coordinador de confianza/Codex realiza esa revisión y conexión explícitamente.
- Inbox/outbox de handoff cloud con correlación, caducidad e idempotencia. Sin API
  autorizada, generar tarea para revisión humana; nunca presumir que ChatGPT recibió algo.
- Preflight de contexto mediante tokenizador del proveedor, partición de tareas
  mayores, política de backpressure y límite de pendientes por cola.
- Registro de modelo/configuración/versiones y pruebas de calidad antes de cambiar
  proveedor. No descargar modelos para solventar fallos.
- Memoria: permisos Windows verificados, procedencia con ruta autorizada y fecha,
  borrado explícito de fuentes retiradas; hoy índice léxico con nombre, SHA y fragmento.
- Pruebas de caída real, disco lleno, carrera de dos procesos y campañas largas
  de carga; medir p50/p95 con muestra suficiente y comparar concurrencia 1/2.
- Nueva CI debe aprobar antes de considerar integración. Sin auto-merge.

## Comandos exactos de esta fase en PowerShell

```powershell
$repo = 'C:\Users\Dexterff\Documents\Codex\2026-10-20\referenced-chatgpt-conversation-this-is-an-5\work\hermes'
$py = 'C:\Users\Dexterff\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$state = 'C:\Users\Dexterff\Documents\IA_LOCAL\hermes-phase-test'
Set-Location -LiteralPath $repo
& $py tools/hermes/local_bridge.py --state $state providers
& $py -m unittest discover -s tests -p test_hermes_local_bridge.py -v
& $py -m unittest discover -s tests -p test_hermes_agent_dispatch.py -v
& $py -m unittest discover -s tests -p test_hermes_durable_plan.py -v
& $py -m unittest discover -s tests -p test_hermes_repo_workspace.py -v
& $py tools/hermes/checkpoint.py validate-all
& $py tools/hermes/benchmark_local.py --model qwen3.8-27b-defiance-uncensored-mtp --repeats 3 --output "$state\benchmark.json"
```

Para un DAG privado aprobado (JSON con `tasks` del PR #23):

```powershell
& $py tools/hermes/local_bridge.py --state $state plan --id ejemplo-01 --spec "$state\plan.json" --engine lmstudio --model qwen3.8-27b-defiance-uncensored-mtp --max-tokens 8192
& $py tools/hermes/local_bridge.py --state $state work-once
```

Cada llamada procesa como máximo una tarea. Repetir deliberadamente para la
siguiente; no se inicia un daemon ni se abre un puerto con estos comandos.
No publicar SQLite, backups de edición, tokens, prompts o memorias privadas.
