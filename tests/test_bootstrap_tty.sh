#!/usr/bin/env bash
set -euo pipefail

project_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
test_root=$(mktemp -d)
trap 'rm -rf "$test_root"' EXIT

payload="$test_root/agent-quick-setup-main"
fake_bin="$test_root/bin"
archive="$test_root/source.tar.gz"
result="$test_root/result.txt"
log="$test_root/session.log"
mkdir -p "$payload" "$fake_bin"
touch "$payload/pyproject.toml"

cat > "$payload/install.sh" <<'INSTALL_SCRIPT'
#!/bin/sh
printf 'Select numbers (comma separated): '
if ! IFS= read -r choice; then
  echo 'EOF while reading interactive input' >&2
  exit 70
fi
if [ "$choice" != "6" ]; then
  echo "unexpected choice: $choice" >&2
  exit 71
fi
printf '%s' "$choice" > "$AGENT_SETUP_TEST_RESULT"
INSTALL_SCRIPT
chmod +x "$payload/install.sh"
tar -czf "$archive" -C "$test_root" "$(basename "$payload")"

cat > "$fake_bin/curl" <<'FAKE_CURL'
#!/bin/sh
output=''
while [ "$#" -gt 0 ]; do
  case "$1" in
    -o)
      output=$2
      shift 2
      ;;
    *) shift ;;
  esac
done
cp "$AGENT_SETUP_TEST_ARCHIVE" "$output"
FAKE_CURL
chmod +x "$fake_bin/curl"

printf -v command "cat %q | env PATH=%q AGENT_SETUP_ARCHIVE_URL=%q AGENT_SETUP_TEST_ARCHIVE=%q AGENT_SETUP_TEST_RESULT=%q sh" \
  "$project_root/bootstrap.sh" "$fake_bin:$PATH" "https://example.invalid/source.tar.gz" "$archive" "$result"

printf '6\n' | script -qec "$command" /dev/null > "$log"

if [ ! -f "$result" ] || [ "$(cat "$result")" != "6" ]; then
  cat "$log" >&2
  echo "Piped bootstrap did not forward the controlling terminal to the installer." >&2
  exit 1
fi

echo "Piped bootstrap TTY test passed."
