#!/usr/bin/env bash
set -euo pipefail

BOOTSTRAP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
  printf '[err] python3 is required\n' >&2
  exit 1
fi

if [[ $# -gt 0 ]]; then
  case "$1" in
    --status) set -- status "${@:2}" ;;
    --global) set -- global "${@:2}" ;;
    --workspace) set -- workspace "${@:2}" ;;
    --all) set -- all "${@:2}" ;;
  esac
fi

exec python3 -m src.agent_bootstrap.cli --root "$BOOTSTRAP_DIR" "$@"
