#!/usr/bin/env bash
set -euo pipefail

project_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
test_home=$(mktemp -d)
trap 'rm -rf "$test_home"' EXIT

python_cmd=${AGENT_SETUP_PYTHON:-python3}
if ! command -v "$python_cmd" >/dev/null 2>&1; then
  python_cmd=python
fi
if ! command -v "$python_cmd" >/dev/null 2>&1; then
  echo "Python 3 is required for the Linux PATH test." >&2
  exit 1
fi

mkdir -p "$test_home/.local/bin"
printf '#!/bin/sh\n' > "$test_home/.local/bin/claude"
chmod +x "$test_home/.local/bin/claude"

HOME="$test_home" PATH="/usr/bin:/bin" PYTHONPATH="$project_root" \
  "$python_cmd" - <<'PY'
from agent_setup.commands import CommandRunner
from agent_setup.models import Runtime

runner = CommandRunner(Runtime("linux", "bash"))
if not runner.persist_user_path("$HOME/.local/bin"):
    raise SystemExit("could not persist Linux PATH")
PY

found=$(HOME="$test_home" PATH="/usr/bin:/bin" bash -ic 'command -v claude' 2>/dev/null)
if [[ "$found" != "$test_home/.local/bin/claude" ]]; then
  echo "Linux interactive shell did not load persisted PATH: $found" >&2
  exit 1
fi

echo "Linux PATH persistence test passed."
