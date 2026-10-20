# Instrucciones de agentes — Dexter Fusion Studio

Estas instrucciones son acumulativas y no sustituyen las políticas del proyecto.

## Retomar una tarea sin empezar de cero

1. Leer primero el checkpoint de la tarea en `.hermes/checkpoints/`. Usar `python tools/hermes/checkpoint.py resume --task-id <id> --current-commit <SHA-real>`.
2. Consultar el último estado y el siguiente paso del checkpoint. Revisar `PROJECT_STATUS.md` y `NEXT_TASK.md`; para TokenLab leer además `CONTINUIDAD.md` y `TOKENLAB_CHECKPOINT.json` **en la rama de PR #12**, no asumir que están en `main`.
3. Comparar el último SHA observado con HEAD real. Si no coincide, revisar diferencias, PRs y CI desde ese SHA: no repetir auditorías que ya tengan evidencia vigente.
4. Trabajar en rama independiente, ejecutar pruebas pertinentes y guardar resultados reales con `advance`. La marca `last_verified_commit` solo se permite tras prueba `passed` con evidencia verificable.
5. Si hay un bloqueo, guardar `blocked` y `next_action` específica. Preservar las bitácoras existentes. No subir secretos, medios privados o conversaciones al repositorio público.
6. No fusiones `main` ni declares despliegues/funciones completas sin autorización y verificación.

Comandos y contrato en [tools/hermes/README.md](tools/hermes/README.md). El motor de checkpoints NO es un proceso de IA autónomo ni implica trabajo continuo fuera de una ejecución real.
