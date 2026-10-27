#!/usr/bin/env bash
set -u
echo "== HERMES Mobile: entorno listo =="
python --version
node --version
git --version
echo
echo "Para instalar OpenCode (opcional), ejecuta:"
echo "  curl -fsSL https://opencode.ai/install | bash"
echo "Verifica el instalador oficial antes de ejecutarlo."
echo "Para iniciar un agente, abre la terminal y ejecuta: opencode"
echo "Nunca pegues claves API en archivos versionados."
