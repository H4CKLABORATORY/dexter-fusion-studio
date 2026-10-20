# DEXTER HERMES — Servidor local y ejecución automática

**Estado:** código del ejecutor y programador integrado en la rama/PR. Instalación en un equipo real y autenticación de un motor de IA aún requieren acceso/configuración del propietario. No equivale a un servicio 24/7 ya encendido.

## Arquitectura

- [Hermes Agent original](https://github.com/NousResearch/hermes-agent) proporciona el agente y herramientas de código. **No** se ha redistribuido ni modificado su código.
- `tools/hermes/checkpoint.py` guarda avances por tarea; se conserva compatibilidad con bitácoras previas.
- `tools/hermes/runner.py` invoca la CLI oficial de Hermes una vez mediante `hermes chat --oneshot --query-file -`. No usa shell para construir comandos.
- `tools/hermes/scheduler.py` elige trabajos de una lista de repositorios, salta los bloqueados/completados, y limita ejecuciones por ciclo.
- Estados privados: `~/.dexter-hermes/workspaces/<hash>/.hermes/checkpoints/`, **fuera del árbol público**. El historial publicado en GitHub sigue siendo la plantilla/bitácora inicial; los estados privados se deben revisar antes de sincronizar un avance público.
- Bloqueo por directorio y por tarea evita dos ejecuciones simultáneas a través del programador en una misma máquina. Una caída puede dejar un lock de recuperación manual (no se borra automáticamente).

## Preparación una sola vez

1. Instalar Git, Python 3.11+, Hermes Agent mediante instrucciones oficiales y configurar la CLI `hermes setup`.
2. Seleccionar un modelo para Hermes (`hermes model`). Para infraestructura local se puede usar Ollama en la PC: `ollama pull qwen2.5-coder:14b`, arrancar Ollama y configurar `http://127.0.0.1:11434/v1` como endpoint OpenAI-compatible; verificar primero con `hermes chat --oneshot -q "responde hola"`. No se garantiza que un modelo local pequeño complete tareas complejas.
3. Clonar estos repositorios **en ramas de trabajo**, no ejecutar sobre `main`: `H4CKLABORATORY/dexter-fusion-studio` y `H4CKLABORATORY/1UP-ANIME`. Asegurarse de que `git status --porcelain` esté vacío y que exista un checkpoint cuyo `branch` coincida con la rama actual.
4. Crear un archivo **privado** fuera de GitHub, `~/.config/dexter-hermes/projects.json`:

```json
{
  "schema_version": 1,
  "projects": [
    {
      "root": "/home/USUARIO/Projects/dexter-fusion-studio",
      "tasks": ["hermes-orchestrator-v1"]
    },
    {
      "root": "/home/USUARIO/Projects/1UP-ANIME",
      "tasks": ["1up-iphone-player"]
    }
  ]
}
```

Editar las dos rutas según el equipo. Las tareas bloqueadas o completadas se omiten; no se fuerzan. Si hay un bloqueo, revisar el checkpoint en el directorio privado y resolverlo explícitamente antes de reanudar.

## Probar sin consumir modelos

```bash
python3 tools/hermes/scheduler.py --config ~/.config/dexter-hermes/projects.json
```

No llama a ninguna IA ni cambia archivos. Devuelve el estado y si hay cambios pendientes de revisión.

## Una ejecución real, controlada

```bash
HERMES_RUN_ENABLED=1 python3 tools/hermes/scheduler.py \
  --config ~/.config/dexter-hermes/projects.json \
  --execute --max-runs 1 --timeout-sec 900
```

Requiere Hermes correctamente configurado. Ejecuta **máximo una tarea** por ciclo y **máximo quince minutos** de tiempo de espera. Si el agente no genera un commit nuevo o deja cambios no confirmados, el trabajo queda bloqueado para evitar intentos repetidos. Un commit nuevo queda **pendiente de pruebas reales y revisión**; no se hace push ni merge automáticamente.

## Ejecución cada hora en Linux con systemd (mini PC o servidor)

Crear `~/.config/systemd/user/dexter-hermes.service`:

```ini
[Unit]
Description=Dexter Hermes — un ciclo autorizado

[Service]
Type=oneshot
Environment=HERMES_RUN_ENABLED=1
ExecStart=/usr/bin/python3 /home/USUARIO/Projects/dexter-fusion-studio/tools/hermes/scheduler.py --config /home/USUARIO/.config/dexter-hermes/projects.json --execute --max-runs 1
TimeoutStartSec=1200
```

Crear `~/.config/systemd/user/dexter-hermes.timer`:

```ini
[Unit]
Description=Dexter Hermes — control horario

[Timer]
OnBootSec=2min
OnUnitInactiveSec=1h
Persistent=true
Unit=dexter-hermes.service

[Install]
WantedBy=timers.target
```

Reemplazar `USUARIO` por el nombre real y revisar rutas. Habilitar únicamente **después de probar el primer ciclo**:

```bash
systemctl --user daemon-reload
systemctl --user enable --now dexter-hermes.timer
systemctl --user list-timers
journalctl --user -u dexter-hermes.service --since today
```

Para que el servicio de usuario siga funcionando sin sesión interactiva, en algunos equipos el administrador debe habilitar linger: `sudo loginctl enable-linger "$USER"`. No ejecutar el agente como root.

## Windows

Usar el programador de tareas de Windows para ejecutar PowerShell cada hora **después** de comprobar que Hermes funciona en modo no interactivo. Configurar la acción `powershell.exe -NoProfile -File RUTA\run-hermes.ps1` y guardar el script fuera de carpetas públicas:

```powershell
$env:HERMES_RUN_ENABLED = "1"
py -3 "C:\Projects\dexter-fusion-studio\tools\hermes\scheduler.py" --config "$HOME\.config\dexter-hermes\projects.json" --execute --max-runs 1
```

En Windows, usar rutas `C:\...` reales en el manifiesto, repositorios con las ramas apropiadas y permisos de cuenta limitada. Si el PC se duerme o se apaga, la automatización se detendrá.

## Seguridad, límites y costos

- **Nunca** exponer `localhost:11434`, la API del agente o el dashboard al Internet público. Para iPhone usar acceso privado por VPN/Tailscale o túnel SSH; no abrir puertos del router.
- Ejecutar Hermes en una cuenta de usuario sin privilegios, sin credenciales personales; preferir contenedor o VM aislados y un GitHub token con permisos mínimos solo para los repositorios permitidos.
- No habilitar `--yolo`, aprobación indiscriminada de comandos, ni integraciones externas con permisos amplios. El prompt no constituye una barrera de seguridad contra ejecución arbitraria: configurar herramientas y sandbox de Hermes.
- El código existente **no instala ni configura Ollama/Hermes por sí solo**. Su configuración se realiza una sola vez en el equipo elegido.
- El proyecto no ejecuta agentes de forma ilimitada: respeta el límite por ciclo, timeout, estado de tarea y permisos. Ollama puede evitar tarifas por llamada, pero consume electricidad y recursos.
- `systemd`/Task Scheduler son responsables de reactivar el proceso; el router solo permite la conectividad.
