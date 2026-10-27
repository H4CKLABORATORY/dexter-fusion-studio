# Empezar a programar desde iPhone — HERMES Mobile

## Paso 1: abrir Codespaces

En Safari abre: https://github.com/codespaces/new?repo=H4CKLABORATORY/dexter-fusion-studio

Selecciona la rama `feature/hermes-mobile-agent-zero-cost` **antes de crear el Codespace**, si el selector lo permite. Si no, crea el Codespace y cambia a la rama desde la terminal con:

```bash
git fetch origin
git switch feature/hermes-mobile-agent-zero-cost
```

GitHub puede exigir habilitar Codespaces o disponer de cuota. **No confirmes ninguna compra**.

## Paso 2: instalar OpenCode

En la terminal del Codespace, tras revisar el instalador oficial:

```bash
curl -fsSL https://opencode.ai/install | bash
```

Abre una terminal nueva y comprueba:

```bash
opencode --version
```

Luego inicia:

```bash
opencode
```

Configura un proveedor con cuota gratuita compatible si está disponible. **Claude requiere acceso autorizado y puede generar cargos**; no se incluye ninguna clave ni se activa facturación.

## Paso 3: primera orden

> Inspecciona el repositorio y lee README.md, PROJECT_STATUS.md y NEXT_TASK.md. No modifiques main. Selecciona una tarea pequeña verificable, crea una rama, implementa el cambio, ejecuta las pruebas existentes y prepara un pull request. Informa archivos, pruebas, errores y limitaciones.

## Seguridad y costos

- El Codespace se detiene o elimina según sus controles; no es un servidor 24/7.
- Comprueba tu cuota en GitHub → Settings → Billing and licensing → Codespaces.
- Detén el Codespace al terminar para no consumir horas.
- No publiques puertos del agente ni secretos.
- Los modelos gratuitos tienen límites; no se promete acceso gratuito a Claude.
