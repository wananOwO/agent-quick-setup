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

    def run(self, command: str, check: bool = True) -> int:
        shown = self.display(command)
        print(f"$ {shown}")
        if self.dry_run:
            return 0
        if self.runtime.wsl:
            args = ["wsl.exe"] + (["-d", self.runtime.distro] if self.runtime.distro else []) + ["--", "bash", "-lc", command]
            return subprocess.run(args, check=check).returncode
        shell = True
        executable = None
        if self.runtime.shell.lower().endswith("powershell"):
            executable = "powershell.exe"
        return subprocess.run(command, shell=shell, executable=executable, check=check).returncode

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
