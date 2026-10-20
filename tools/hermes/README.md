# DEXTER HERMES — Checkpoints portátiles (v1)

Herramienta independiente de proveedores, sin dependencias externas ni secretos. No ejecuta tareas autónomas ni modifica `main`. Se instala en la raíz de cada repositorio, junto a `.hermes/checkpoints/*.json`. Respeta las bitácoras existentes, **no las reemplaza**.

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

## Límites
- Automatización externa necesaria para ejecutar agentes mientras ChatGPT está cerrado.
- Un checkpoint no conserva el estado interno completo de una IA; contiene datos explícitos verificados.
- La verificación del SHA requiere comprobación real del repositorio; el CLI no consulta GitHub automáticamente.
- Es una primera versión local, no un producto de gestión multiagente terminado.
