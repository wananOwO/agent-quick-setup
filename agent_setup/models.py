from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class Dependency:
    name: str
    commands: List[str]
    description: str
    required: bool = True


@dataclass(frozen=True)
class AgentSpec:
    key: str
    name: str
    description: str
    command: str
    dependencies: List[Dependency]
    install_commands: Dict[str, List[str]]
    docs_url: str
    notes: str = ""
    package: Optional[str] = None
    user_bin_paths: List[str] = field(default_factory=lambda: ["$HOME/.local/bin"])


@dataclass
class Runtime:
    """Execution target. On Windows this can be native PowerShell or WSL."""

    os_name: str
    shell: str
    wsl: bool = False
    distro: Optional[str] = None

    @property
    def platform_key(self) -> str:
        if self.wsl:
            return "linux"
        return self.os_name
