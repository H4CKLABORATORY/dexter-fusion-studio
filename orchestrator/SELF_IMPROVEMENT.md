# DEXTER MISSION CONTROL — AUTO-MEJORA CONTROLADA

Objetivo: en la MISMA revisión horaria del Control Maestro, dedicar una fase BREVE a detectar una mejora verificable del orquestador sin bloquear el desarrollo de los proyectos. No se crea otra automatización ni un chat por proyecto.

## Rutina A/B por ejecución
1. Leer `orchestrator/MASTER_QUEUE.json` y este documento; observar la evidencia de la ejecución anterior, si existe. No recorrer todos los repositorios sin necesidad.
2. Detectar como máximo UN problema concreto: repetición de acciones, lectura excesiva, conflictos SHA, bloqueo sin registrar, error de pruebas, duplicación, trabajo no persistido o instrucciones ambiguas.
3. Registrar hipótesis con causa observable, solución reversible, métrica ANTES y criterio de éxito. No extrapolar ahorro de tokens sin medición; si no hay telemetría, usar métricas indirectas identificadas como tales (archivos leídos, pasos duplicados o tasa de fallos).
4. Solo si hay evidencia y un cambio seguro, aplicar UNA mejora pequeña a archivos de coordinación (preferiblemente mediante rama/PR si toca el comportamiento de tareas). No alterar automáticamente los criterios de aceptación, prioridades fijadas por el usuario, permisos, herramientas, cuotas, seguridad, gastos, frecuencia del trigger ni reglas de ejecución.
5. Comprobar la mejora (validación JSON, prueba determinista, inspección de diff, o ejecución controlada), comparar con la línea base y revertir o documentar el fallo si empeora. Registrar `maintenance.last_review_at`, `maintenance.last_result`, `maintenance.next_hypothesis` y evidencia con commit/PR.
6. Si no existe un cambio útil, registrar `sin mejora verificable` sin commits artificiales. PROSEGUIR igualmente con una tarea real del proyecto elegible.
7. Aplicar como máximo UNA tarea de ingeniería del proyecto por revisión. Si una etapa queda bloqueada, documentar el motivo y continuar con la siguiente en la próxima revisión.

## Asignación de esfuerzo
- La auto-mejora es secundaria y acotada: idealmente <=15% del tiempo/contexto operativo cuando se pueda estimar, no más de una modificación propuesta por revisión.
- Priorizar el proyecto actual. No marcarlo `done` salvo evidencia de todos sus criterios.
- Cuando los proyectos terminen o estén bloqueados, permitir una revisión periódica de bajo costo del gestor, sin notificaciones repetitivas, y detenerse cuando el usuario lo pida. Nunca crear bucles infinitos dentro de una ejecución.

## Formato de evidencia
Cada modificación real debe especificar: problema, cambio, comprobación, resultado medido u observado, SHA/PR, riesgo/reversión, y próxima acción. Separar `observado`, `hipótesis` y `no verificado`.

## Limitaciones
ChatGPT no puede crear un chat independiente o despertar otros chats como reacción a sus pausas, reparar desde este gestor el error de transmisión de la app, evitar límites de uso, ni ejecutar código de forma continua 24/7. La continuidad depende del disparador horario, de los permisos y de los conectores. Un plugin no se autoactualiza sin una ejecución que lo edite explícitamente y con los controles de la plataforma.
