#!/usr/bin/env bash
set -euo pipefail
umask 077
hermes_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$hermes_root"
python3 --version
node --version
npm ci --prefix tools/hermes/mobile --no-audit --no-fund
python3 tools/hermes/mobile.py doctor
python3 -m unittest discover -s tests -p 'test_hermes_mobile*.py' -v
printf '%s\n' 'Instalado. Sin servidor activo y sin APIs de pago.'
printf '%s\n' 'Respaldo CPU: python3 tools/hermes/mobile.py install-cpu'
printf '%s\n' 'Iniciar: python3 tools/hermes/mobile.py start'
