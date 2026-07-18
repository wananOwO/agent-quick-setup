import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Iterable, List, Optional

from .models import Runtime


@dataclass
class CommandRunner:
    runtime: Runtime
    dry_run: bool = False

    def display(self, command: str) -> str:
        if self.runtime.wsl:
            distro = ["-d", self.runtime.distro] if self.runtime.distro else []
            return "wsl.exe " + " ".join(distro + ["--", "bash", "-lc", repr(command)])
        return command

    def exists(self, command: str) -> bool:
        if not self.runtime.wsl and self.runtime.os_name == "windows":
            aliases = {"python3": "python", "pip3": "pip"}
            command = aliases.get(command, command)
        probe = command
        if self.runtime.wsl:
            args = ["wsl.exe"] + (["-d", self.runtime.distro] if self.runtime.distro else []) + ["--", "bash", "-lc", f"command -v {command}"]
            return subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
        return shutil.which(probe) is not None

    def run(self, command: str, check: bool = False) -> int:
        shown = self.display(command)
        print(f"$ {shown}")
        if self.dry_run:
            return 0
        if self.runtime.wsl:
            args = ["wsl.exe"] + (["-d", self.runtime.distro] if self.runtime.distro else []) + ["--", "bash", "-lc", command]
            return subprocess.run(args, check=check).returncode
        if self.runtime.os_name == "windows" and self.runtime.shell.lower().endswith("powershell"):
            powershell = shutil.which("powershell.exe")
            if not powershell:
                raise FileNotFoundError("Windows PowerShell could not be located on PATH.")
            args = [powershell, "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command]
            return subprocess.run(args, shell=False, check=check).returncode
        return subprocess.run(command, shell=True, check=check).returncode

    def refresh_environment(self) -> None:
        if self.runtime.wsl or self.runtime.os_name != "windows":
            return
        persisted = []
        try:
            import winreg

            locations = [
                (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
                (winreg.HKEY_CURRENT_USER, r"Environment"),
            ]
            for hive, key_path in locations:
                try:
                    with winreg.OpenKey(hive, key_path) as key:
                        value, _ = winreg.QueryValueEx(key, "Path")
                        persisted.extend(value.split(os.pathsep))
                except OSError:
                    continue
        except ImportError:
            return

        current = os.environ.get("PATH", "").split(os.pathsep)
        unique = []
        seen = set()
        for entry in persisted + current:
            entry = entry.strip()
            normalized = os.path.normcase(entry)
            if entry and normalized not in seen:
                seen.add(normalized)
                unique.append(entry)
        os.environ["PATH"] = os.pathsep.join(unique)

    def version(self, command: str) -> Optional[str]:
        try:
            if self.runtime.wsl:
                args = ["wsl.exe"] + (["-d", self.runtime.distro] if self.runtime.distro else []) + ["--", "bash", "-lc", f"{command} --version 2>/dev/null || {command} -V"]
                result = subprocess.run(args, capture_output=True, text=True, timeout=10)
            else:
                result = subprocess.run([command, "--version"], capture_output=True, text=True, timeout=10)
            output = (result.stdout or result.stderr).strip().splitlines()
            return output[0] if output else None
        except (OSError, subprocess.SubprocessError):
            return None
