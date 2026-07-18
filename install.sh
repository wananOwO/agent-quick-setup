#!/usr/bin/env sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

find_python() {
  if [ -n "${AGENT_SETUP_PYTHON:-}" ]; then
    candidates="$AGENT_SETUP_PYTHON"
  else
    candidates="python3 python"
  fi
  for candidate in $candidates; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

python_cmd=$(find_python || true)
if [ -z "$python_cmd" ]; then
  if [ "${AGENT_SETUP_NO_BOOTSTRAP:-0}" = "1" ]; then
    echo "No working Python 3.9+ interpreter was found." >&2
    exit 1
  fi

  manager=""
  command_text=""
  if command -v brew >/dev/null 2>&1; then
    manager="brew"
    command_text="brew install python"
  elif command -v apt-get >/dev/null 2>&1; then
    manager="apt-get"
    command_text="sudo apt-get update && sudo apt-get install -y python3 python3-pip"
  elif command -v dnf >/dev/null 2>&1; then
    manager="dnf"
    command_text="sudo dnf install -y python3 python3-pip"
  elif command -v pacman >/dev/null 2>&1; then
    manager="pacman"
    command_text="sudo pacman -Sy --noconfirm python python-pip"
  else
    echo "Python 3.9+ is required, and no supported package manager was found." >&2
    exit 1
  fi

  echo "Python 3.9+ is required and was not found."
  echo "The following command will be used:"
  echo "  $command_text"
  if [ "${AGENT_SETUP_ASSUME_YES:-0}" = "1" ]; then
    answer="y"
  else
    printf 'Install Python now? [Y/n] '
    read -r answer || answer=""
  fi
  case "$answer" in
    ""|y|Y|yes|YES) ;;
    *) echo "Python installation was cancelled." >&2; exit 1 ;;
  esac

  case "$manager" in
    brew) brew install python ;;
    apt-get) sudo apt-get update && sudo apt-get install -y python3 python3-pip ;;
    dnf) sudo dnf install -y python3 python3-pip ;;
    pacman) sudo pacman -Sy --noconfirm python python-pip ;;
  esac

  python_cmd=$(find_python || true)
  if [ -z "$python_cmd" ]; then
    echo "Python was installed but is not available on PATH yet. Open a new terminal and retry." >&2
    exit 1
  fi
fi

cd "$script_dir"
exec "$python_cmd" -m agent_setup "$@"
