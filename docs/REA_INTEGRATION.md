# REA — Reverse Engineer Anything (integración opcional)

**Fuente oficial:** https://github.com/morluto/rea — paquete npm `rea-agents`, licencia MIT para código propio de REA; terceros mantienen sus licencias.

REA ofrece un servidor MCP y comandos de análisis local con evidencias. Este proyecto **no distribuye ni instala REA**: añade un adaptador pequeño, configuraciones MCP opcionales y pruebas independientes para conectar una instalación existente.

## Instalación en un equipo o servidor que vaya a analizar los archivos

1. Instala Node.js compatible: **22.19+**, **24.11+** o **26+**, además de npm.
2. Revisa el origen del paquete y ejecuta `npx rea-agents setup` en ese equipo. Confirma manualmente los cambios propuestos por su instalador. Para solo usar la CLI, REA documenta `npm install --global rea-agents`.
3. Comprueba `rea doctor --json`. Para motores nativos y firmware pueden hacer falta Ghidra, Hopper, IDA u otros proveedores compatibles, instalados y configurados aparte. Para análisis JS estático no se necesita decompilador nativo.
4. Reinicia el agente seleccionado si usaste el setup MCP. No publiques archivos binarios privados ni capturas con credenciales en GitHub.

## Uso Python desde Dexter Fusion Studio

```python
from fusion.rea_bridge import doctor, analyze_javascript_application

health = doctor()  # Diagnóstico real de la instalación local.
report = analyze_javascript_application("C:/ruta/app-extraida")
# report es el JSON original con hallazgos/evidencias de REA.
```

El adaptador acepta una **carpeta local de aplicación JavaScript/Electron** o un archivo **`.asar`** existente. No descarga, modifica, ejecuta ni sube a internet el archivo analizado por sí mismo. Se ejecuta el comando local `rea analyze-javascript-application ... --json`, con tiempo límite y sin shell. El análisis interno que realice REA depende de sus proveedores y configuración.

Para otras clases (binarios nativos, firmware, APK, iOS y páginas web), usa **las herramientas MCP de REA** después de configurar las capacidades y autorizaciones necesarias, en lugar de suponer que el adaptador JS soporta esos formatos.

## MCP para agentes

El generador `fusion.integrations.export_mcp_client_config` agrega la entrada `rea` **solo si detecta un ejecutable REA existente**, usando `{"command":"RUTA_ABSOLUTA_A_REA", "args":["mcp"]}`. Puede especificarse `config={"rea_cli":"RUTA_AL_REA"}`. La función `scan()` expone el estado de REA. El archivo generado sirve para clientes compatibles con el formato `mcpServers`; instalarlo en un cliente concreto y reiniciar el cliente sigue siendo un paso separado.

REA documenta `rea mcp` como servidor stdio. No abrir puertos de red ni integrar comandos MCP globalmente de manera implícita. No se almacenan claves API.

## Flujo de investigación para otros proyectos

**Inventariar** los artefactos y autorización → **diagnosticar** proveedores → **analizar** características relevantes → **conservar evidencias, incertidumbres y limitaciones** → **implementar código original** → **probar** → **guardar checkpoint**. Se reutiliza en 1UP Anime (inspección de JS/web), DEXTER Fusion Studio (interfaces de edición), y firmware/otros dispositivos cuando se tenga el hardware/proveedor compatible.

REA no ofrece acceso ilimitado a ChatGPT ni sustituye instalación local, un servidor persistente, credenciales legítimas o el cumplimiento de licencias y autorizaciones.

## Pruebas

```bash
python -m unittest tests.test_rea_bridge -v
```

Estas pruebas simulan la CLI y **no demuestran** que REA real, Ghidra o un agente MCP estén instalados o ejecutándose.
