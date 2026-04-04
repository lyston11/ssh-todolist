#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_BIN="${ROOT_DIR}/.venv/bin"
DEFAULT_DB="${ROOT_DIR}/data/todos.db"

mkdir -p "${ROOT_DIR}/data"

if [[ -x "${VENV_BIN}/ssh-todolist-service" ]]; then
  exec "${VENV_BIN}/ssh-todolist-service" \
    --host 0.0.0.0 \
    --port 8000 \
    --ws-port 8001 \
    --db "${DEFAULT_DB}" \
    "$@"
fi

if command -v ssh-todolist-service >/dev/null 2>&1; then
  exec ssh-todolist-service \
    --host 0.0.0.0 \
    --port 8000 \
    --ws-port 8001 \
    --db "${DEFAULT_DB}" \
    "$@"
fi

echo "ssh-todolist-service is not installed yet." >&2
echo "Run ./install.sh first." >&2
exit 1
