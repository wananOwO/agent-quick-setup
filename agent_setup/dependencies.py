from typing import Dict, List

from .commands import CommandRunner
from .models import AgentSpec, Dependency, Runtime


def check_dependency(dep: Dependency, runner: CommandRunner) -> bool:
    return all(runner.exists(command) for command in dep.commands)


def missing_dependencies(agent: AgentSpec, runner: CommandRunner) -> List[Dependency]:
    return [dep for dep in agent.dependencies if not check_dependency(dep, runner)]


def package_manager(runtime: Runtime, runner: CommandRunner) -> str:
    candidates = ["winget", "choco"] if runtime.os_name == "windows" and not runtime.wsl else ["brew", "apt-get", "dnf", "pacman"]
    for candidate in candidates:
        if runner.exists(candidate):
            return candidate
    return ""


def dependency_install_command(dep: Dependency, runtime: Runtime, runner: CommandRunner) -> str:
    manager = package_manager(runtime, runner)
    names = {
        "Node.js/npm": {"winget": "OpenJS.NodeJS.LTS", "brew": "node", "apt-get": "nodejs npm", "dnf": "nodejs npm", "pacman": "nodejs npm"},
        "Python/pip": {"winget": "Python.Python.3.12", "brew": "python", "apt-get": "python3 python3-pip", "dnf": "python3 python3-pip", "pacman": "python python-pip"},
        "Git": {"winget": "Git.Git", "brew": "git", "apt-get": "git", "dnf": "git", "pacman": "git"},
    }
    package = names.get(dep.name, {}).get(manager)
    if not package:
        return ""
    if manager == "winget":
        return f"winget install --id {package} --exact --source winget"
    if manager == "brew":
        return f"brew install {package}"
    if manager == "apt-get":
        return f"sudo apt-get update && sudo apt-get install -y {package}"
    if manager == "dnf":
        return f"sudo dnf install -y {package}"
    return f"sudo pacman -Sy --noconfirm {package}"
