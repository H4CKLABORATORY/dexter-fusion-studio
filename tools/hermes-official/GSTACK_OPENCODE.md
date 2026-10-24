# Integración gstack → OpenCode → Hermes

gstack oficial: https://github.com/garrytan/gstack (MIT). Soporte OpenCode **experimental**. Reutilizamos su instalador oficial `setup.ps1 --host opencode`; no copiamos herramientas ni construimos un agente nuevo.

## Windows: instalación sencilla

Requisitos: Git for Windows, Bun, Node.js y OpenCode. En tu checkout de la rama del [PR #33](https://github.com/H4CKLABORATORY/dexter-fusion-studio/pull/33):

```powershell
.\tools\hermes-official\INSTALL-GSTACK-OPENCODE.ps1
```

El script reutiliza o descarga el repositorio oficial en `%LOCALAPPDATA%\DEXTER-TOOLS\gstack`, llama a `setup.ps1 --host opencode --no-browser` y verifica `--status`. No instala nuevos modelos ni cambia Qwen, Hermes, Claude o Codex. La descarga de Chromium se omite para reducir espera (se puede activar con `-WithBrowser` si se necesita QA visual). Deben existir Git, Bun y Node; no se instalan a escondidas.

Reinicia OpenCode. Comprueba que aparece `/gstack-review`. Las funciones de revisión externa que llaman Claude Code o Codex requieren CLI y autenticación independiente.

## Añadir gstack a la cola existente

Tras instalar el puente Hermes/OpenCode, prepara `C:\Tareas\mejora.txt` con una tarea concreta y ejecuta:

```powershell
$worker = Join-Path $env:LOCALAPPDATA 'hermes\scripts\dexter_opencode_tick.py'
python $worker add --project 'C:\Repos\mi-proyecto' --prompt-file 'C:\Tareas\mejora.txt' --name mejora-001 --gstack review --timeout 1800
python $worker status
```

Opciones de `--gstack`: `none` (predeterminado), `review`, `investigate`, `qa`, `plan-eng-review`, `design-review`. OpenCode recibe una instrucción de **leer y aplicar el skill instalado**, no un segundo proceso de auditoría independiente. No se confunde la recomendación del modelo con la verificación del host. Sin pruebas externas al modelo, el estado final es `needs_review`.

Si el skill falta, la tarea se marca `blocked` sin intentos recurrentes. Para verificar con comandos del proyecto, usa `--checks-json C:\Tareas\checks.json`, donde el archivo contiene por ejemplo:

```json
[["python", "-m", "unittest", "discover", "-s", "tests", "-v"]]
```

Las pruebas deben corresponder al proyecto. No se deben habilitar acciones automáticas de gstack para publicar, fusionar ramas o desplegar.

## Límites verificados

- La instalación en Windows del usuario, Qwen real y las habilidades gstack en OpenCode **no se han probado** desde este chat.
- gstack no proporciona un proceso autónomo durante días; esa responsabilidad sigue siendo de Hermes, con cola, gateway y cron.
- OpenCode Goal no se activa automáticamente mediante `opencode run`, y no debe competir sobre el mismo árbol de trabajo.
- El soporte oficial OpenCode de gstack es experimental; los hooks de seguridad son recomendaciones, no restricciones de permisos del sistema.
- Usar un skill grande puede gastar mucho contexto en Qwen local. Preferir `review` o `investigate` según necesidad, sin invocar todos los roles en cada tarea.
- Los tests de GitHub Actions usan Git real y OpenCode simulado, no inferencia Qwen ni ejecución de gstack.
