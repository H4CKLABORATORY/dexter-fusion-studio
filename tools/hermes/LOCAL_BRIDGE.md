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
- `GET /hardware`: lectura actual NVIDIA de temperatura del núcleo y VRAM, fecha
  de muestreo y estado; requiere autenticación. CLI: `hardware`.
- `POST /memory/search`, JSON `{"query":"reproductor"}`: hasta tres fragmentos con
  archivo, número de fragmento y SHA-256 de procedencia. Búsqueda léxica, no embeddings.
- `POST /tasks`, JSON `{"kind":"analyze","engine":"lmstudio","model":"modelo-cargado","prompt":"consulta"}`:
  crea tarea pendiente. `kind` también admite `propose`; no cambia los permisos.
- `GET /tasks/<id>`: estado y resultado. Todas las rutas requieren el token local.
- `GET /tasks`: conteos por estado y últimas 50 tareas, sin preguntas, respuestas
  ni fragmentos privados. También funciona `status` desde la CLI con acceso al estado local.
- `POST /tasks/<id>/cancel`, JSON `{}`: cancela solo tareas pendientes, conservando
  el registro. Una tarea iniciada, finalizada o ya cancelada devuelve 409; no se
  interrumpe una inferencia en curso. CLI equivalente: `cancel --task-id <id>`.
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

## Temperatura antes de iniciar tareas
Cada `work-once` con trabajo pendiente consulta `nvidia-smi` con argumentos fijos,
sin shell y con timeout de tres segundos. A partir de **80 °C** en cualquier GPU
NVIDIA detectada, conserva la tarea pendiente y no inicia inferencia. Si falta el
sensor, devuelve valores inválidos o falla la lectura, también espera. El límite
es una política operativa conservadora del programador, no una especificación
térmica del fabricante. Una ejecución posterior vuelve a leer la temperatura.

La salida del worker incluye `hardware` para distinguir la espera de una cola vacía.
La comprobación se hace al inicio: no es vigilancia continua, no interrumpe inferencias
en curso, no controla otras aplicaciones y no modifica ventiladores, potencia ni clocks.
Solo informa temperatura de núcleo NVIDIA; no certifica temperatura del CPU,
hotspot o memoria gráfica. `cpu_temperature_c: null` significa que no se ha medido.

Pruebas: `python -m unittest discover -s tests -p test_hermes_local_bridge.py -v`.
