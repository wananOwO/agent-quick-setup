import argparse
import builtins
import sys
from typing import List

from .commands import CommandRunner
from .install import install_agent
from .platforms import choose_windows_target
from .registry import get_agents


def parse_args(argv=None):
    parser = argparse.ArgumentParser(prog="agent-setup", description="Detect dependencies and install agent CLIs")
    parser.add_argument("agents", nargs="*", help="Agent keys such as claude-code or codex")
    parser.add_argument("--yes", action="store_true", help="Automatically confirm install steps")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing them")
    parser.add_argument("--list", action="store_true", help="List available agents")
    return parser.parse_args(argv)


def choose_agents(agents, input_fn=input) -> List:
    print("Available agents:")
    for index, agent in enumerate(agents, 1):
        print(f"  {index}) {agent.name:<20} {agent.description}")
    raw = input_fn("Select numbers (comma separated): ").strip()
    selected = []
    for item in raw.split(","):
        try:
            index = int(item.strip()) - 1
            if 0 <= index < len(agents):
                selected.append(agents[index])
        except ValueError:
            continue
    return selected


def main(argv=None) -> int:
    args = parse_args(argv)
    agents = get_agents()
    if args.list:
        for agent in agents:
            print(f"{agent.key}\t{agent.name}\t{agent.docs_url}")
        return 0
    runtime = choose_windows_target()
    print(f"Target runtime: {runtime.os_name}{' / WSL' if runtime.wsl else ''}")
    selected = [agent for key in args.agents for agent in agents if agent.key == key]
    if args.agents and len(selected) != len(args.agents):
        unknown = sorted(set(args.agents) - {agent.key for agent in selected})
        print(f"Unknown agent(s): {', '.join(unknown)}", file=sys.stderr)
        return 2
    if not selected:
        selected = choose_agents(agents)
    if not selected:
        print("No agents selected.")
        return 1
    runner = CommandRunner(runtime, dry_run=args.dry_run)
    input_fn = (lambda _prompt: "y") if args.yes else builtins.input
    success = all(install_agent(agent, runner, input_fn=input_fn) for agent in selected)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
