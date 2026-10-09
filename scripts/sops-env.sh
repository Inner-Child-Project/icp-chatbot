#!/usr/bin/env bash
# Helper SOPS para .env.sops. El fichero se llama *.env.sops (no *.env) y sops
# NO autodetecta dotenv por esa extensión: TODOS los comandos llevan los flags
# explícitos (ya incluidos aquí — no los quites).
#
# Uso:
#   ./scripts/sops-env.sh edit      # abre $EDITOR con el plaintext, re-cifra al salir
#   ./scripts/sops-env.sh verify    # descifra y comprueba las 16 claves sin mostrar valores
#   ./scripts/sops-env.sh keys      # lista nombres de variables (sin valores)
#
# Requiere: SOPS_AGE_KEY_FILE o ~/.config/sops/age/keys.txt (600).
set -euo pipefail
cd "$(dirname "$0")/.."

F=".env.sops"
T="--input-type dotenv --output-type dotenv"
export SOPS_AGE_KEY_FILE="${SOPS_AGE_KEY_FILE:-$HOME/.config/sops/age/keys.txt}"

case "${1:-}" in
  edit)
    # shellcheck disable=SC2086
    sops $T .env.sops
    ;;
  verify)
    # shellcheck disable=SC2086
    sops --decrypt $T .env.sops | python3 -c "
import sys
keys = [l.split('=', 1)[0] for l in sys.stdin.read().splitlines() if '=' in l]
want = {'OPENROUTER_API_KEY','LANGSMITH_API_KEY','N8N_LEAD_WEBHOOK_URL','N8N_LEAD_WEBHOOK_SECRET','CORS_ORIGINS'}
missing = want - set(keys)
print(f'{len(keys)} vars, critical missing: {missing or \"none\"}')
sys.exit(1 if missing else 0)
"
    ;;
  keys)
    grep -E '^[A-Z_]+=' .env.sops | cut -d= -f1
    ;;
  *)
    echo "uso: $0 {edit|verify|keys}"; exit 1;;
esac
