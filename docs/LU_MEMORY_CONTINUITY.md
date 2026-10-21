# LU + Qwen: memoria real entre sesiones, chats y proyectos

## Alcance y limite tecnico

LU tiene tres mecanismos DIFERENTES:
- Chat: Settings > Agent > Memory inyecta datos globales en los mensajes de chat. Se configura desde LU, no desde GitHub.
- Historial: Settings > General > Chat Backup > Export all chats / Import chats; Settings > General > Import from other chatbots admite exportaciones de ChatGPT, Claude o Gemini. Esto copia el historial, no vuelve automaticamente accesibles todos los mensajes en cada nuevo chat.
- Code: cada ejecucion lee `.lurules` SOLO de la raiz seleccionada con "Select folder" (limite 10 KB). No hereda archivos de carpetas padre ni lee otro chat por si solo.

Por eso este repositorio y los demas proyectos incorporan `.lurules`, instrucciones para checkpoints y exclusiones de datos privados.

## Preparacion de LU (operacion hecha EN el PC por el usuario o Qwen con permisos)

1. Abrir LU > Settings > Agent > Memory y crear un resumen global breve de los proyectos y preferencias de desarrollo (sin claves ni contrasenas).
2. En LU > Settings > General > Import from other chatbots, importar el archivo de exportacion de ChatGPT si se desea recuperar los chats antiguos. NO equivale a conectar automaticamente todas las conversaciones futuras.
3. En LU > Settings > General > Chat Backup, usar Export all chats para un respaldo recuperable; Import chats para restaurar. LU tambien mantiene respaldos locales, pero conviene tener una copia independiente bajo control del propietario.
4. En LU > Code > Select folder, escoger SIEMPRE la carpeta raiz exacta del repositorio. Un modelo sin herramientas no puede escribir checkpoints.
5. Usar ramas y revisar el diff; no subir conversaciones privadas, tokens o exportaciones al repositorio publico.

## Sincronizador local privado

El script en `tools/lu-memory/sync_context.py` prepara la memoria de Code para varios repositorios locales. Necesita Python 3.10+.

Desde la carpeta de DEXTER Fusion Studio, en PowerShell (reemplaza la ruta por la carpeta donde tienes tus repos):

```powershell
py -3 tools/lu-memory/sync_context.py --parent "C:\Users\TU_USUARIO\Projects"
```

Tambien acepta varias carpetas sin explorar todo el disco:

```powershell
py -3 tools/lu-memory/sync_context.py --repo "C:\codigo\1UP-ANIME" --repo "C:\codigo\dexter-fusion-studio"
```

El script:
- Detecta repositorios solo dentro del directorio indicado, sin recorrer tu disco entero.
- Crea `.dexter-local/LAST_SESSION.md` para cada repo y lo conserva en ejecuciones posteriores.
- Escribe en `.dexter-local/SHARED_CONTEXT.md` un resumen del contexto maestro y el ultimo checkpoint local de cada proyecto.
- Crea un `.lurules` generico si la carpeta aun no tiene uno; nunca sobreescribe reglas existentes.
- Agrega `.dexter-local/` a `.git/info/exclude` en clones Git ordinarios; los repos de este cambio tambien llevan regla en `.gitignore`.
- Conserva memoria maestra privada en `%LOCALAPPDATA%\DEXTER-MEMORY\MASTER_CONTEXT.md` (o la ruta `--memory-home`).

No extrae automaticamente mensajes de LU ni ChatGPT. Para importar contenido historico utiliza las funciones oficiales de LU. Los archivos privados nunca deben ser incluidos en Git, PR o Cloudflare.

**IMPORTANTE:** corre de nuevo `sync_context.py` para propagar nuevos `LAST_SESSION.md` entre carpetas. No existe servicio permanente instalado por este cambio; si no ejecutas el script, cada repo conserva su memoria local pero la vista transversal no se actualiza.

## Contrato para cada nueva ejecucion de Code

- Leer `.lurules`, las instrucciones AGENTS/documentacion del repo y `.dexter-local/SHARED_CONTEXT.md` + `LAST_SESSION.md`.
- Revisar HEAD, rama, archivos y tests antes de declarar avances.
- Trabajar y validar cambios con herramientas de verdad.
- Antes de terminar, dejar en `LAST_SESSION.md` fecha, objetivo, resultados verificados, errores, rama/commit, siguiente accion.
- Si se alcanza limite de contexto, resumir antes de continuar y guardar checkpoint. LU tambien soporta `/compact` en chat.
- Nunca asumir que Qwen leyo automaticamente TODOS los chats antiguos: importar/exportar es un paso diferente.

## Estado de implementacion (21/oct/2026)

Los archivos de reglas y exclusiones se prepararon en ramas separadas de 1UP-ANIME, dexter-fusion-studio, dexter-ai-web y dexter-bot-panel. No hay prueba de instalacion en la PC del usuario, ni de haber importado los chats en LU. Estos cambios NO crean ni instalan por si solos la aplicacion independiente HERMES AI STUDIO.
