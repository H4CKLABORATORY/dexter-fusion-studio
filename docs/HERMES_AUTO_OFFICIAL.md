# DEXTER HERMES — Configuracion rapida del agente OFICIAL (Windows)

**Prioridad:** activar ejecucion local recurrente SIN construir otro harness. Fuentes: https://github.com/NousResearch/hermes-agent y https://hermes-agent.nousresearch.com/docs/user-guide/windows-native.

## Instalacion manual minima (segun los desarrolladores de Hermes)

Abre PowerShell normal en Windows:

```powershell
iex (irm https://hermes-agent.nousresearch.com/install.ps1)
```

Cierra y vuelve a abrir PowerShell. Confirma `hermes` y ejecuta:

```powershell
hermes model
hermes config set compression.enabled true
hermes config set compression.threshold 0.80
hermes config set compression.tail_mode lean
hermes gateway install
hermes gateway start
hermes gateway status
hermes cron status
```

En `hermes model` selecciona LM Studio (http://127.0.0.1:1234/v1) con **Qwen cargado**, Ollama (11434) o Custom endpoint si LU usa otro puerto. No descargues otro modelo si uno compatible ya esta instalado. La instalacion puede requerir mas de 5 minutos por dependencias y red.

El servicio oficial de Windows se activa al iniciar sesion, mediante tarea programada. **No** mantiene el PC encendido, no reconecta por si mismo un Qwen descargado pero no servido por API, y no reanuda automaticamente cualquier ejecucion fallida. Primero hay que verificar un chat simple.

## Arranque guiado desde el mismo repositorio (opcional)

`tools/hermes-official/START-HERMES-AUTO.ps1` usa los mismos comandos oficiales y deja el horario de codificacion **desactivado por defecto**.

```powershell
.\tools\hermes-official\START-HERMES-AUTO.ps1 -Install
```

Tras verificar que Qwen responde, para programar **una tarea acotada cada hora** en un repo autorizado:

```powershell
.\tools\hermes-official\START-HERMES-AUTO.ps1 -EnableHourlyWork -ProjectPath "C:\TU_CARPETA\dexter-fusion-studio"
```

El script evita duplicar una tarea con el mismo nombre de proyecto. No instala OpenCode: Hermes posee herramientas de archivos/terminal propias. OpenCode Goal sigue siendo opcional, no ejecutar dos orquestadores sobre la misma carpeta a la vez.

## Sobre la compactacion al 80%

Hermes admite `compression.threshold: 0.80` para el compresor principal, aunque el mecanismo de higiene del gateway tiene su propio umbral, y el contexto que informa el proveedor puede variar. Comprimir no equivale a recordar todo: guardar progreso en checkpoints Git y `.dexter-local/LAST_SESSION.md` sigue siendo necesario.

## Limitaciones y seguridad

- El modelo debe estar **sirviendo una API local**, no basta con tener un archivo descargado.
- Los trabajos de cron ejecutan herramientas como el usuario de Windows que ejecuta Hermes; las restricciones del prompt **no son una sandbox**. Usa una cuenta con permisos limitados y repositorios confiables.
- Nunca incluir claves Stripe/Higgsfield en scripts, GitHub o archivos de estado.
- Para continuidad horaria, cron crea **sesiones nuevas** y depende de que el gateway y el servidor del modelo esten encendidos. La reanudacion de un trabajo interrumpido puede quedar pendiente de revision; no afirmar autonomia continua garantizada durante dias.
- La verificacion inicial debe incluir `hermes model`, una respuesta simple en `hermes chat`, `hermes gateway status`, `hermes cron status` y una primera tarea acotada validada antes de habilitar la programacion por hora.
- La integracion directa con OpenCode no esta implementada por este script: Hermes ejecuta por sus propias herramientas, sin inventar un puente ni depender de LU.

## Continuidad con DEXTER AI STUDIO

El primer proyecto a automatizar **despues de validar el motor** sera DEXTER AI STUDIO (Cloudflare). Su especificacion sigue en `docs/DEXTER_AI_STUDIO_GOAL.md` en esta misma rama de PR. No iniciar cobros ni desplegar servicios comerciales sin permisos.
