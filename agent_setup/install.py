from .commands import CommandRunner
from .dependencies import dependency_install_command, missing_dependencies
from .metadata import npm_engines
from .models import AgentSpec


def confirm(prompt: str, input_fn=input) -> bool:
    answer = input_fn(prompt + " [y/N]: ").strip().lower()
    return answer in {"y", "yes"}


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
            if runner.run(command) != 0:
                return False
    command = agent.install_commands[runner.runtime.platform_key][0]
    print(f"Install {agent.name} with:")
    print(f"  {runner.display(command)}")
    if not confirm("Continue?", input_fn):
        print("Cancelled.")
        return False
    if runner.run(command) != 0:
        return False
    if not runner.exists(agent.command):
        print(f"Install command finished, but `{agent.command}` is not on PATH yet.")
    else:
        print(f"{agent.name} installed. Verify with `{agent.command}`.")
    return True
