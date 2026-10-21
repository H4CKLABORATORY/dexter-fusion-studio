# Puente local privado y cola persistente

`local_bridge.py` usa Python estándar, sin instalaciones ni descarga de modelos.
Solo permite análisis y propuestas de texto. No ofrece shell, escritura en repositorios,
instalación, commits, merge ni ejecución de código generado.

El servidor escucha exclusivamente en `127.0.0.1:18765`, requiere Bearer token en
todas las rutas, rechaza Origin y Host ajenos y no habilita CORS. No usar túneles
ni port forwarding. No conecta por sí solo la aplicación ChatGPT de otro dispositivo.
Un cliente local autorizado, como Codex ejecutándose en el equipo, puede consumirlo.

Guardar el estado fuera de cualquier checkout Git y restringir el directorio al usuario
y SYSTEM mediante permisos del sistema operativo **antes** de iniciar. El archivo
`bridge.token`, SQLite, resultados y memoria son privados; nunca adjuntarlos a PR.

```text
python tools/hermes/local_bridge.py --state <directorio-privado> index --memory <carpeta-md-txt>
python tools/hermes/local_bridge.py --state <directorio-privado> serve
python tools/hermes/local_bridge.py --state <directorio-privado> work-once
```

- `GET /health`: capacidades, sin prueba de disponibilidad de motores.
- `POST /memory/search`, JSON `{"query":"reproductor"}`: hasta tres fragmentos con
  archivo, número de fragmento y SHA-256 de procedencia. Búsqueda léxica, no embeddings.
- `POST /tasks`, JSON `{"kind":"analyze","engine":"lmstudio","model":"modelo-cargado","prompt":"consulta"}`:
  crea tarea pendiente. `kind` también admite `propose`; no cambia los permisos.
- `GET /tasks/<id>`: estado y resultado. Todas las rutas requieren el token local.
- `work-once` reclama atómicamente **una** tarea pendiente, consulta fragmentos relevantes,
  pide respuesta en español y persiste resultado. Nunca hay descarga automática.

Los motores tienen URL fija: LM Studio `127.0.0.1:1234`, Ollama `127.0.0.1:11434`.
El selector no importa modelos en Ollama: elegir un modelo inexistente registra fallo.
La memoria contiene documentos aportados, posiblemente desactualizados; no es toda la
memoria interna de ChatGPT. El índice lee solo MD/TXT del directorio elegido.

Una caída durante inferencia deja `running` para revisión humana, sin reintento automático:
así no repite una inferencia cuyo resultado sea incierto. Fallos se registran por tipo,
sin volcar respuestas del proveedor. El servidor es serial y para uso de un cliente local,
no un servicio multiusuario endurecido. Los procesos con acceso a la cuenta pueden leer
el token. Hay límites de cuerpo y tiempo; no hay defensa contra un proceso local malicioso.

Para reanudación acotada se puede programar `work-once` con el programador del equipo,
un solo proceso por vez, duración máxima y fecha de expiración. No lo confundir con un
agente que implemente tareas de GitHub: la respuesta sigue siendo una propuesta revisable.

Pruebas: `python -m unittest discover -s tests -p test_hermes_local_bridge.py -v`.

## Incremento verificable: diagnóstico y coordinación durable

`POST /tasks` admite `max_tokens` entero entre 64 y 8192 (por defecto 2400 para
compatibilidad). En tareas de razonamiento largas solicitar 8192 explícitamente.
El contexto cargado y la velocidad del proveedor siguen imponiendo límites: no es
garantía de finalización. No se reintenta automáticamente. `finish_reason=length`
produce `diagnostic=output_token_limit`, incluso con texto parcial; razonamiento
sin respuesta final produce `reasoning_without_answer`. No se conserva razonamiento
ni cuerpos de error. `elapsed_seconds` mide el worker, no throughput de decodificación.

Migración SQLite aditiva: presupuestos de tareas antiguas permanecen en 2400;
no altera su estado ni vuelve a ejecutar tareas fallidas. Probar primero con estado
nuevo. No arrancar código antiguo contra una cola migrada: usa INSERT posicional.
Detener servidor y workers antiguos antes de migrar una cola de uso diario.

`GET /providers` prueba `/v1/models` en URLs fijas, sin proxies ni redirecciones,
con timeout de 3 segundos y límite de respuesta. `reachable` significa catálogo
accesible en ese instante; no promete inferencia exitosa. ChatGPT y Locally Uncensored
se informan no verificados, sin adaptadores ni exploración de puertos arbitrarios.

`plan` reutiliza `agent_dispatch.plan` del PR #23, guarda roles y aristas en SQLite,
y rechaza reutilizar un ID con otro contenido. Los resultados previos se adjuntan
como datos no confiables y acotados. Una dependencia fallida deja descendientes
pendientes, sin ejecutarlos. Los roles son funciones de análisis; no son permisos.
Eventos `queued`, `claimed`, `completed`, `failed` y `operator_abandoned` se guardan
en transacciones junto al cambio de estado. Son auditoría, no replay de efectos.

Solo hay un slot `running` por base SQLite. Distintas bases o clientes externos
pueden competir por la misma GPU: el operador debe usar una cola por proveedor.
Una caída conserva `running` y detiene nuevas inferencias hasta revisión. Tras
comprobar que el worker anterior terminó, `abandon --task ID --confirm-worker-stopped`
registra fallo definitivo. No reencola, no recupera a ciegas ni cancela un proveedor.

La herramienta `repo_workspace.py` recibe raíz y lista de archivos autorizados del
coordinador de confianza. Ofrece worktree fijado a SHA, lectura con hash, reemplazo
exacto con revisión previa, backup privado y rollback que rechaza pisar cambios
posteriores. Pruebas por nombre en lista fija y timeout; sin shell. No es sandbox
del sistema operativo: las pruebas ejecutan código del repositorio y solo deben
correr tras revisión humana/Codex. El modelo no llama directamente al editor.

Arquitectura, comandos Windows, mediciones y límites en [HERMES_LOCAL_PHASES.md](HERMES_LOCAL_PHASES.md).
