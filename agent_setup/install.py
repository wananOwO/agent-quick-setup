import subprocess

from .commands import CommandRunner
from .dependencies import dependency_install_command, missing_dependencies
from .metadata import npm_engines
from .models import AgentSpec


def confirm(prompt: str, input_fn=input) -> bool:
    answer = input_fn(prompt + " [y/N]: ").strip().lower()
    return answer in {"y", "yes"}


def run_command(runner: CommandRunner, command: str) -> bool:
    try:
        return runner.run(command) == 0
    except (OSError, subprocess.SubprocessError) as error:
        print(f"Command could not be started: {error}")
        return False


def install_agent(agent: AgentSpec, runner: CommandRunner, input_fn=input) -> bool:
    engines = npm_engines(agent.package, runner)
    if engines:
        print(f"Upstream package runtime constraints: {engines}")
    missing = missing_dependencies(agent, runner)
    if missing:
        print(f"Missing dependencies for {agent.name}:")
        commands = []
        for dep in missing:
            command = dependency_install_command(dep, runner.runtime, runner)
            commands.append(command)
            print(f"  - {dep.name}: {dep.description}")
            print(f"    install: {command or 'Install manually and retry'}")
            if not command:
                return False
        if not confirm("Install these dependencies?", input_fn):
            print("Dependency installation cancelled.")
            return False
        for command in commands:
            if not run_command(runner, command):
                return False
        runner.refresh_environment()
        if not runner.dry_run:
            still_missing = missing_dependencies(agent, runner)
            if still_missing:
                names = ", ".join(dep.name for dep in still_missing)
                print(f"Dependencies were installed but are still unavailable in this process: {names}.")
                print("Open a new terminal and run Agent Quick Setup again.")
                return False
    command = agent.install_commands[runner.runtime.platform_key][0]
    print(f"Install {agent.name} with:")
    print(f"  {runner.display(command)}")
    if agent.user_bin_paths:
        print("PATH entries to configure after installation:")
        for path in agent.user_bin_paths:
            print(f"  - {runner.path_config_description(path)}")
    if not confirm("Continue?", input_fn):
        print("Cancelled.")
        return False
    if not run_command(runner, command):
        return False
    if runner.dry_run:
        print(f"Dry run complete; `{agent.command}` was not installed or verified.")
        return True
    path_persistence_failed = False
    for path in agent.user_bin_paths:
        if not runner.persist_user_path(path):
            path_persistence_failed = True
            print(f"Warning: could not persist PATH entry {path}. Add it manually before using {agent.command}.")
    runner.refresh_environment()
    if not runner.exists(agent.command):
        if path_persistence_failed:
            print(f"{agent.name} install command completed, but could not verify `{agent.command}` until PATH is fixed.")
            return True
        print(f"{agent.name} could not be verified because `{agent.command}` is not on PATH.")
        return False
    print(f"{agent.name} installed. Verify with `{agent.command}`.")
    return True
