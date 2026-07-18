from .models import AgentSpec, Dependency


NODE = Dependency("Node.js/npm", ["node", "npm"], "Node.js runtime and npm package manager")
PYTHON = Dependency("Python/pip", ["python3", "pip3"], "Python 3 runtime and pip")
GIT = Dependency("Git", ["git"], "Git version control")

NODE_USER_PATHS = ["$NPM_GLOBAL_BIN", "$HOME/.local/bin"]
PYTHON_USER_PATHS = ["$HOME/.local/bin"]


AGENTS = [
    AgentSpec(
        key="claude-code",
        name="Claude Code",
        description="Anthropic's official terminal coding agent",
        command="claude",
        dependencies=[],
        install_commands={
            "windows": ["irm https://claude.ai/install.ps1 | iex"],
            "macos": ["curl -fsSL https://claude.ai/install.sh | bash"],
            "linux": ["curl -fsSL https://claude.ai/install.sh | bash"],
        },
        docs_url="https://code.claude.com/docs/en/setup",
        notes="Native installer is preferred; npm fallback is available in the official docs.",
        user_bin_paths=["$HOME/.local/bin"],
    ),
    AgentSpec(
        key="codex",
        name="OpenAI Codex CLI",
        description="OpenAI's terminal coding agent",
        command="codex",
        dependencies=[NODE],
        install_commands={
            "windows": ["npm install --global @openai/codex"],
            "macos": ["npm install --global @openai/codex"],
            "linux": ["npm install --global @openai/codex"],
        },
        docs_url="https://github.com/openai/codex",
        package="@openai/codex",
        user_bin_paths=NODE_USER_PATHS,
    ),
    AgentSpec(
        key="opencode",
        name="OpenCode",
        description="Open-source terminal AI coding agent",
        command="opencode",
        dependencies=[NODE],
        install_commands={
            "windows": ["npm install --global opencode-ai"],
            "macos": ["npm install --global opencode-ai"],
            "linux": ["npm install --global opencode-ai"],
        },
        docs_url="https://opencode.ai/docs/",
        package="opencode-ai",
        user_bin_paths=NODE_USER_PATHS,
    ),
    AgentSpec(
        key="openclaw",
        name="OpenClaw",
        description="Self-hosted personal AI assistant CLI",
        command="openclaw",
        dependencies=[NODE],
        install_commands={
            "windows": ["npm install --global openclaw@latest"],
            "macos": ["npm install --global openclaw@latest"],
            "linux": ["npm install --global openclaw@latest"],
        },
        docs_url="https://github.com/openclaw/openclaw",
        notes="The project may require Node.js 22+; the adapter checks the installed runtime before running npm.",
        package="openclaw",
        user_bin_paths=NODE_USER_PATHS,
    ),
    AgentSpec(
        key="hermes",
        name="Hermes Agent",
        description="Nous Research's terminal agent",
        command="hermes",
        dependencies=[PYTHON, GIT],
        install_commands={
            "windows": ["python -m pip install --upgrade hermes-agent"],
            "macos": ["python3 -m pip install --upgrade hermes-agent"],
            "linux": ["python3 -m pip install --upgrade hermes-agent"],
        },
        docs_url="https://github.com/NousResearch/hermes-agent",
        notes="Python 3.11+ is recommended; installing from the repository with its setup script is an alternative.",
        user_bin_paths=PYTHON_USER_PATHS,
    ),
    AgentSpec(
        key="pi",
        name="Pi Coding Agent",
        description="Minimal extensible coding agent from pi-mono",
        command="pi",
        dependencies=[NODE],
        install_commands={
            "windows": ["npm uninstall --global @mariozechner/pi-coding-agent; npm install --global @earendil-works/pi-coding-agent"],
            "macos": ["npm uninstall --global @mariozechner/pi-coding-agent; npm install --global @earendil-works/pi-coding-agent"],
            "linux": ["npm uninstall --global @mariozechner/pi-coding-agent; npm install --global @earendil-works/pi-coding-agent"],
        },
        docs_url="https://github.com/earendil-works/pi",
        notes="The current package requires Node.js 22.19 or newer.",
        package="@earendil-works/pi-coding-agent",
        user_bin_paths=NODE_USER_PATHS,
    ),
]


def get_agents():
    return list(AGENTS)
