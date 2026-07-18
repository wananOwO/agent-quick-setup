#!/usr/bin/env sh
set -eu

repository="${AGENT_SETUP_REPOSITORY:-wananOwO/agent-quick-setup}"
branch="${AGENT_SETUP_BRANCH:-main}"
archive_url="${AGENT_SETUP_ARCHIVE_URL:-https://github.com/${repository}/archive/refs/heads/${branch}.tar.gz}"
temp_root="$(mktemp -d 2>/dev/null || mktemp -d -t agent-quick-setup)"

cleanup() {
  rm -rf "$temp_root"
}
trap cleanup EXIT INT TERM

archive_path="$temp_root/source.tar.gz"
echo "Downloading Agent Quick Setup from $repository..."
if command -v curl >/dev/null 2>&1; then
  curl -fL --proto '=https' --tlsv1.2 "$archive_url" -o "$archive_path"
elif command -v wget >/dev/null 2>&1; then
  wget -qO "$archive_path" "$archive_url"
else
  echo "curl or wget is required to download the project." >&2
  exit 1
fi

tar -xzf "$archive_path" -C "$temp_root"
project_file="$(find "$temp_root" -mindepth 2 -name pyproject.toml -type f | head -n 1)"
if [ -z "$project_file" ]; then
  echo "Downloaded archive does not contain pyproject.toml." >&2
  exit 1
fi
project_root="$(dirname "$project_file")"

if [ "${AGENT_SETUP_DOWNLOAD_ONLY:-0}" = "1" ]; then
  echo "Download and extraction verified: $project_root"
  exit 0
fi

sh "$project_root/install.sh" "$@"
