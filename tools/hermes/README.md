# DEXTER HERMES — Checkpoints portátiles (v1)

Herramientas con código de checkpoints sin dependencias y un ejecutor opcional de Hermes Agent. En modo seguro solo consultan estados; para ejecutar el agente se requieren **ambas** condiciones: `--execute` y `HERMES_RUN_ENABLED=1`, además de instalar/configurar Hermes Agent. No ejecutan cambios en `main`. Respetan las bitácoras existentes, **no las reemplazan**.

## Primera instrucción para cualquier agente
1. Leer instrucciones del repositorio (`AGENTS.md`, `CONTINUIDAD.md`, `PROJECT_STATUS.md`, etc.).
2. Consultar `.hermes/checkpoints/*.json` y ejecutar `resume` sobre el task_id activo.
3. Obtener el `HEAD` real de la rama y pasarlo por `--current-commit`. Si difiere, revisar **el diff incremental y los PR/CI recientes**, no volver a inspeccionar todo el código desde cero.
4. Comprobar que las referencias del checkpoint sigan vigentes; verificar y anotar pruebas realizadas de verdad. Nunca inferir que un commit fue verificado por el simple hecho de existir.
5. Al finalizar o bloquearse, usar `advance` y registrar *qué sigue*. No almacenar secretos ni datos privados en repositorios públicos.

## Comandos

```bash
python tools/hermes/checkpoint.py init --project H4CKLABORATORY/repo --task-id mi-tarea --objective 'Implementar función X' --branch feature/x --next-action 'Crear prueba fallida primero'
python tools/hermes/checkpoint.py resume --task-id mi-tarea --current-commit 1234567abc
python tools/hermes/checkpoint.py advance --task-id mi-tarea --status in_progress --next-action 'Corregir error de integración' --step 'Añadidos casos de prueba' --changed-file src/main.py --observed-commit 1234567abc
python tools/hermes/checkpoint.py advance --task-id mi-tarea --status completed --next-action 'Revisar PR' --observed-commit 1234567abc --verified-commit 1234567abc --test-name 'CI GitHub Actions' --test-result passed --evidence 'https://github.com/owner/repo/actions/runs/123'
python tools/hermes/checkpoint.py validate-all
```

`last_observed_commit` no implica pruebas; `last_verified_commit` requiere `passed` y evidencia. Si se descubre un SHA diferente, se elimina cualquier afirmación de verificación para el nuevo estado hasta ejecutar pruebas. Las entradas de `history` se conservan hasta las últimas 60; la evidencia de pruebas se mantiene completa. `init` no sobreescribe un checkpoint existente; `advance` reescribe mediante archivo temporal y reemplazo atómico. **No hay bloqueo interproceso**: una futura versión debe agregar control de concurrencia o escritura serializada antes de habilitar múltiples agentes escritores simultáneos.

## Ejecución real y servidor

- [Instalación en Linux, Windows y conexión con Ollama](SERVER_SETUP.md).
- Un turno sobre la rama de la tarea: `HERMES_RUN_ENABLED=1 python tools/hermes/runner.py --root /ruta/al/repositorio --task-id tarea --execute`.
- Varias tareas de repositorios distintos: `HERMES_RUN_ENABLED=1 python tools/hermes/scheduler.py --config ~/.config/dexter-hermes/projects.json --execute --max-runs 1`.
- Sin `--execute` el scheduler solo inspecciona, no utiliza la IA ni modifica archivos.
- Para frecuencia horaria necesitas el programador del sistema operativo con equipo encendido. No se ha instalado en la computadora del usuario.

## Límites
- Automatización de ejecución periódica necesita systemd, Windows Task Scheduler o el scheduler oficial Hermes debidamente configurados; el CLI no sigue trabajando si el proceso termina.
- Un checkpoint no conserva el estado interno completo de una IA; contiene datos explícitos verificados.
- La verificación del SHA requiere comprobación real del repositorio; el CLI no consulta GitHub automáticamente.
- El ejecutor funciona con la CLI oficial de Hermes y checkpoints, pero su entorno real debe configurarse y probarse por separado.
- No hay pruebas autenticadas de modelos ni prueba de servicio doméstico 24/7 en este PR.
