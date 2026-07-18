"""Best-effort runtime metadata lookup.

The lookup is informational and never replaces the pinned manifest. It lets the
installer surface an upstream Node.js engine requirement before npm runs.
"""
import json
from typing import Optional

from .commands import CommandRunner


def npm_engines(package: Optional[str], runner: CommandRunner) -> Optional[dict]:
    if not package or not runner.exists("npm") or runner.dry_run:
        return None
    try:
        if runner.runtime.wsl:
            args = ["wsl.exe"] + (["-d", runner.runtime.distro] if runner.runtime.distro else []) + ["--", "bash", "-lc", f"npm view {package}@latest engines --json"]
        else:
            args = ["npm", "view", f"{package}@latest", "engines", "--json"]
        import subprocess
        result = subprocess.run(args, capture_output=True, text=True, timeout=20)
        if result.returncode != 0 or not result.stdout.strip():
            return None
        value = json.loads(result.stdout)
        return value if isinstance(value, dict) else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
