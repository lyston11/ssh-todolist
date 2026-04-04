#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
METHOD="venv"
VENV_DIR="${ROOT_DIR}/.venv"
IMAGE_NAME="ssh-todolist-services:latest"

print_help() {
  cat <<'EOF'
Usage:
  ./install.sh [--method venv|pipx|docker]

Methods:
  venv    Create a local virtualenv and install the service into it
  pipx    Install the service as a standalone CLI with pipx
  docker  Build the Docker image locally
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --method)
      METHOD="${2:-}"
      shift 2
      ;;
    -h|--help)
      print_help
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      print_help >&2
      exit 1
      ;;
  esac
done

install_venv() {
  command -v python3 >/dev/null 2>&1 || {
    echo "python3 is required for --method venv" >&2
    exit 1
  }

  python3 -m venv "${VENV_DIR}"
  "${VENV_DIR}/bin/python" -m pip install --upgrade pip
  "${VENV_DIR}/bin/pip" install --no-build-isolation .

  cat <<EOF
Installed with local virtualenv:
  ${VENV_DIR}

Run with:
  ./run.sh --token your-shared-token
EOF
}

install_pipx() {
  command -v pipx >/dev/null 2>&1 || {
    echo "pipx is required for --method pipx" >&2
    exit 1
  }

  pipx install --force --pip-args=--no-build-isolation "${ROOT_DIR}"

  cat <<'EOF'
Installed with pipx.

Run with:
  ssh-todolist-service --host 0.0.0.0 --port 8000 --token your-shared-token
EOF
}

install_docker() {
  command -v docker >/dev/null 2>&1 || {
    echo "docker is required for --method docker" >&2
    exit 1
  }

  docker build -t "${IMAGE_NAME}" "${ROOT_DIR}"

  cat <<EOF
Built Docker image:
  ${IMAGE_NAME}

Run with:
  docker run --rm -p 8000:8000 -p 8001:8001 \\
    -e SSH_TODOLIST_TOKEN=your-shared-token \\
    -v "${ROOT_DIR}/data:/app/data" \\
    ${IMAGE_NAME}
EOF
}

case "${METHOD}" in
  venv)
    install_venv
    ;;
  pipx)
    install_pipx
    ;;
  docker)
    install_docker
    ;;
  *)
    echo "Unsupported method: ${METHOD}" >&2
    print_help >&2
    exit 1
    ;;
esac
