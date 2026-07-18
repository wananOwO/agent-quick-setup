import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
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

    def _shell_config_name(self) -> str:
        shell = (self.runtime.shell or "").lower()
        if "zsh" in shell:
            return ".zshrc"
        if "bash" in shell:
            return ".bashrc"
        return ".profile"

    @staticmethod
    def _home_directory() -> Path:
        home = os.environ.get("HOME") or os.environ.get("USERPROFILE")
        return Path(home).expanduser() if home else Path.home()

    def _path_expression(self, path: str) -> str:
        if path == "~":
            return "$HOME"
        if path.startswith("~/"):
            return "$HOME/" + path[2:]
        if path == "$HOME":
            return "$HOME"
        if path.startswith("$HOME/"):
            return path
        if path.startswith("${HOME}/"):
            return "$HOME/" + path[7:]
        return path

    def _path_line(self, path: str) -> str:
        expression = self._path_expression(path).replace("\\", "\\\\").replace('"', '\\"')
        return f'export PATH="{expression}:$PATH"'

    def _expanded_path(self, path: str) -> str:
        home = str(self._home_directory())
        expanded = path.replace("${HOME}", home).replace("$HOME", home)
        return os.path.abspath(os.path.expanduser(os.path.expandvars(expanded)))

    def _prepend_process_path(self, path: str) -> None:
        current = os.environ.get("PATH", "")
        entries = [entry for entry in current.split(os.pathsep) if entry]
        normalized = os.path.normcase(os.path.normpath(path))
        if not any(os.path.normcase(os.path.normpath(entry)) == normalized for entry in entries):
            os.environ["PATH"] = os.pathsep.join([path] + entries)

    def path_config_description(self, path: str) -> str:
        if self.runtime.wsl:
            return f"WSL {self._shell_config_name()} ({path})"
        if self.runtime.os_name == "windows":
            return f"Windows user PATH ({self._expanded_path(path)})"
        return f"{self._home_directory() / self._shell_config_name()} ({path})"

    def persist_user_path(self, path: str) -> bool:
        """Persist a user-level PATH entry and update this process when possible.

        WSL targets are always modified inside the selected distribution. A
        failed persistence operation returns False so callers can warn without
        marking an otherwise successful Agent installation as failed.
        """
        line = self._path_line(path)
        if self.runtime.wsl:
            config = f"$HOME/{self._shell_config_name()}"
            quoted_line = shlex.quote(line)
            command = (
                f"touch \"{config}\"; "
                f"grep -Fqx {quoted_line} \"{config}\" || "
                f"printf '%s\\n' {quoted_line} >> \"{config}\""
            )
            try:
                return self.run(command) == 0
            except (OSError, subprocess.SubprocessError):
                return False

        expanded = self._expanded_path(path)
        if self.runtime.os_name == "windows":
            try:
                import winreg

                key_path = r"Environment"
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                    try:
                        existing, _ = winreg.QueryValueEx(key, "Path")
                    except OSError:
                        existing = ""
                    entries = [entry for entry in existing.split(os.pathsep) if entry]
                    normalized = os.path.normcase(os.path.normpath(expanded))
                    if not any(os.path.normcase(os.path.normpath(entry)) == normalized for entry in entries):
                        entries.append(expanded)
                        winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, os.pathsep.join(entries))
                self._prepend_process_path(expanded)
                return True
            except (ImportError, OSError):
                return False

        config = self._home_directory() / self._shell_config_name()
        try:
            config.parent.mkdir(parents=True, exist_ok=True)
            content = config.read_text(encoding="utf-8") if config.exists() else ""
            if line not in content.splitlines():
                with config.open("a", encoding="utf-8") as handle:
                    if content and not content.endswith("\n"):
                        handle.write("\n")
                    handle.write(line + "\n")
            self._prepend_process_path(expanded)
            return True
        except OSError:
            return False

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
