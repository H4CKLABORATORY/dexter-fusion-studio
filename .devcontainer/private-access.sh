#!/usr/bin/env bash
set -euo pipefail
umask 077
if ! command -v tailscale >/dev/null; then
  printf '%s\n' 'Reconstruye el contenedor para instalar Tailscale.' >&2
  exit 2
fi
if [[ ! -t 0 ]]; then
  printf '%s\n' 'Ejecuta en tu terminal: requiere autorizar Tailscale Personal gratuito.' >&2
  exit 2
fi
sudo tailscale up --accept-routes=false --accept-dns=false --ssh=false
sudo tailscale serve --bg --https=443 http://127.0.0.1:4096
tailscale status --json | python3 -c 'import json,sys; s=json.load(sys.stdin); print("Servidor privado: https://" + s["Self"]["DNSName"].rstrip("."))'
printf '%s\n' 'En iPhone conecta Tailscale con la misma cuenta; usa esta URL y Basic Auth en OpenCode iOS Client.'
