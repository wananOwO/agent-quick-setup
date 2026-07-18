import os
import platform
import shutil
import subprocess
from typing import Optional

from .models import Runtime


def detect_runtime() -> Runtime:
    system = platform.system().lower()
    if system == "windows":
        return Runtime("windows", "powershell")
    if system == "darwin":
        return Runtime("macos", os.environ.get("SHELL", "zsh"))
    return Runtime("linux", os.environ.get("SHELL", "bash"))


def wsl_available() -> bool:
    return platform.system().lower() == "windows" and shutil.which("wsl.exe") is not None


def first_wsl_distro() -> Optional[str]:
    if not wsl_available():
        return None
    try:
        result = subprocess.run(["wsl.exe", "-l", "-q"], capture_output=True, text=True, timeout=10)
        names = [line.strip().replace("\x00", "") for line in result.stdout.splitlines() if line.strip()]
        return names[0] if names else None
    except (OSError, subprocess.SubprocessError):
        return None


def wsl_user_shell(distro: Optional[str]) -> str:
    """Return the selected WSL user's shell basename, with a bash fallback."""
    args = ["wsl.exe"] + (["-d", distro] if distro else []) + ["--", "bash", "-lc", "getent passwd \"$USER\" | cut -d: -f7"]
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=10)
        shell = (result.stdout or "").strip().rsplit("/", 1)[-1]
        return shell if shell in {"bash", "zsh"} else "bash"
    except (OSError, subprocess.SubprocessError):
        return "bash"


def choose_windows_target(input_fn=input, output_fn=print) -> Runtime:
    runtime = detect_runtime()
    if runtime.os_name != "windows" or not wsl_available():
        return runtime
    distro = first_wsl_distro()
    output_fn("Windows detected. Choose install target:")
    output_fn("  1) Native PowerShell")
    output_fn(f"  2) WSL{f' ({distro})' if distro else ''}")
    choice = input_fn("Choice [1]: ").strip() or "1"
    if choice == "2" and distro:
        return Runtime("windows", wsl_user_shell(distro), wsl=True, distro=distro)
    if choice == "2":
        output_fn("No WSL distribution found; using native PowerShell.")
    return runtime
