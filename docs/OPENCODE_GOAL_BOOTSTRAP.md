# DEXTER — usar OpenCode Goal, sin construir otro agente

**Origen oficial:** https://github.com/ByBrawe/opencode-goal

Objetivo: usar OpenCode como ejecutor y Qwen como modelo local; Goal se encarga de mantener una tarea hasta verificar los resultados. Este documento no instala software en la computadora por si solo.

## Una sola instalacion en el PC (PowerShell, con Node.js/npm y OpenCode ya instalados)

```powershell
npx -y @bybrawe/opencode-goal@latest
```

El instalador oficial registra el plugin en la configuracion GLOBAL de OpenCode, respetando otros plugins. Reinicia completamente OpenCode, abre el proyecto y escribe:

```text
/goal status
```

Si el comando no aparece en Desktop pero si en la terminal de OpenCode, sigue el diagnostico del desarrollador: https://github.com/ByBrawe/opencode-loop/blob/main/docs/OPENCODE2-DESKTOP-WINDOWS.md . No inventes un puente de comandos ni reinstales sin diagnostico.

## Configuracion de Qwen

Abre la configuracion de modelos en OpenCode; selecciona el Qwen local ya descargado. Comprueba realmente que el servidor local de LU, LM Studio u Ollama responda y que OpenCode pueda consumirlo. **No asumas un puerto fijo**; las instalaciones pueden usar endpoints distintos. Nunca pegues en GitHub claves personales o Stripe.

## Primer trabajo verificado

**En la carpeta raiz de DEXTER AI STUDIO**, despues de crearla o abrirla (no usar la carpeta del editor para crear otra aplicacion dentro sin confirmacion), lee [DEXTER_AI_STUDIO_GOAL.md](DEXTER_AI_STUDIO_GOAL.md) desde este repositorio y lanza el objetivo:

```text
/goal Implementa la primera fase comprobable de DEXTER AI STUDIO: inspecciona archivos, reutiliza la base existente si la hay, crea interfaz y backend Cloudflare minimo con autenticacion segura preparada. Ejecuta la prueba real de build y deja CHECKPOINT.md con errores, pruebas y siguiente paso. No inventes conexiones a Stripe/Higgsfield. No subas secretos ni despliegues produccion. --max-minutes 60
```

No activar **OpenCode Goal** y otro plugin loop/controlador autonomo simultaneamente sobre la misma sesion. No usar `--continuous` hasta que los trabajos y los limites esten validados. La CLI Goal conserva objetivos locales, pero no sustituye los mensajes del historial completo de LU/ChatGPT.

## Comprobacion

- `/goal status` — objetivo, estado y consumo
- `/goal audit` — pruebas y evidencia actuales
- `/goal pause` — suspender
- `/goal resume` — reanudar tras interrupcion
- `/goal queue` — cola futura

Los datos del plugin se guardan bajo `.opencode/goals/`, `.opencode/goal-sequences/` y `.opencode/goal-locks/`; su estado es LOCAL. Revisa diferencias y pruebas antes de cualquier merge.

## Limites reales

El plugin debe instalarse y probarse **en el PC**. Un commit de GitHub no instala OpenCode, no inicia el servidor Qwen y no concede control remoto del equipo. Los cambios de este PR solo preparan instrucciones y contexto para que el agente local pueda usarlos.
