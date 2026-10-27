# DEXTER Local Accelerator — cola de Qwen y scraping de 1UP Anime

**Estado:** código preparado en la rama del PR #30; probado con Python/Node en un entorno de pruebas Linux, **no** probado todavía en el Windows del propietario ni conectado a LM Studio real. Los cambios de GitHub no instalan programas automáticamente en el PC.

## Software existente que reutilizamos

| Herramienta | Original | Función |
| --- | --- | --- |
| LM Studio | https://lmstudio.ai/ | Servir Qwen local por API compatible con OpenAI |
| Aider | https://github.com/Aider-AI/aider | Modificar archivos mediante IA |
| Git | https://git-scm.com/ | Ramas y worktrees aislados |
| Node.js | https://nodejs.org/ | Ejecutar el scraper existente de AniList de 1UP Anime |
| GitHub CLI | https://cli.github.com/ | Autenticación para revisión manual futura (no hace falta en el primer ensayo) |

No copiamos los proyectos de terceros dentro del repositorio ni modificamos sus licencias; los instaladores apuntan a sus distribuidores originales.

## Cuando enciendas el PC (PowerShell)

Primero, asegúrate de tener Git y Python, o ejecuta el instalador anterior tras descargar el PR. Para obtener esta rama **sin esperar un merge a main**:

```powershell
cd $env:USERPROFILE
git clone --branch feature/local-accelerator-bootstrap-20261021 https://github.com/H4CKLABORATORY/dexter-fusion-studio.git
cd .\dexter-fusion-studio\tools\local-accelerator
.\RUN-DEXTER-AUTO.ps1 -Plan
```

Si falta Git, Python o Node, ejecuta `.\START-DEXTER.ps1 -Install` y abre una nueva ventana de PowerShell. Este instalador solo corre si tú lo ejecutas.

**Primer ensayo sin Qwen (scraping real de AniList):**

```powershell
.\RUN-DEXTER-AUTO.ps1 -ScraperOnly
```

Después carga Qwen en LM Studio y habilita `http://127.0.0.1:1234`. Para continuar **el mismo checkpoint**, sin repetir el scraping ya aprobado:

```powershell
.\RUN-DEXTER-AUTO.ps1 -Resume
```

Si prefieres intentar **ambas tareas de una vez** en una rama nueva:

```powershell
.\RUN-DEXTER-AUTO.ps1
```

Aider se instala en `%USERPROFILE%\DEXTER-LOCAL\.venv` solo si no está instalado. El script no instala otro modelo de IA. El modo `-Plan` no ejecuta tareas ni crea ramas.

## Flujo real y protecciones

1. `mission_queue.json` define **dos tareas** aprobadas, con límite de 240 y 900 segundos. No admite comandos arbitrarios.
2. `mission_supervisor.py` crea una rama `agent/dexter-...` y un **Git worktree distinto** para no tocar el árbol del proyecto original.
3. Ejecuta `node --check` y `scripts/refresh-catalog.mjs` del repositorio 1UP Anime; valida el JSON y el recuento de fichas.
4. Consulta LM Studio **solo en localhost** y ejecuta Aider con Qwen para revisar el scraper y corregir **un problema real**, si lo identifica.
5. Guarda checkpoint atómico en `%USERPROFILE%\DEXTER-LOCAL\supervisor\active.json`, además de logs por tarea. `-Resume` omite las tareas completadas.
6. Si se interrumpe una edición, **no** la repite silenciosamente: conserva el estado para inspección. Ni Aider ni este flujo son un sandbox del sistema operativo; ejecuta solo proyectos confiables.

**No implementado aún:** ejecución continua 24/7, recuperación automática de ediciones fallidas, notificaciones WhatsApp, aprobaciones remotas, publicación automática ni reproducción de anime. El scraping recupera **metadatos**, no derechos de retransmisión.

## Evidencia de pruebas

- **Local Linux, 2026-10-21:** `python -m unittest discover -s tests -v` — 7 pruebas satisfactorias, incluida ejecución **real de Node** con un fixture sin conexión externa.
- `python -m py_compile mission_supervisor.py` — satisfactorio.
- `.github/workflows/local-accelerator-tests.yml` prepara CI de PR con Python 3.12 y Node 22. **No afirmar éxito del CI antes de comprobar el run de GitHub**.
- Windows PowerShell, Qwen real, AniList en vivo y prueba iPhone: **pendientes**.

**Próxima tarea:** comprobar el primer informe de Windows, corregir incompatibilidades concretas y posteriormente añadir un supervisor de varias misiones con recuperación controlada y avisos.
