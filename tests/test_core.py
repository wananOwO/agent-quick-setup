import io
import unittest
from unittest.mock import patch

from agent_setup.commands import CommandRunner
from agent_setup.dependencies import dependency_install_command
from agent_setup.models import Runtime
from agent_setup.platforms import detect_runtime
from agent_setup.registry import get_agents


class FakeRunner(CommandRunner):
    def __init__(self, runtime, commands):
        super().__init__(runtime, dry_run=True)
        self.commands = set(commands)

    def exists(self, command):
        return command in self.commands


class CoreTests(unittest.TestCase):
    def test_registry_contains_requested_agents(self):
        keys = {agent.key for agent in get_agents()}
        self.assertTrue({"claude-code", "codex", "opencode", "openclaw", "hermes", "pi"} <= keys)

    def test_wsl_uses_linux_install_channel(self):
        agent = next(agent for agent in get_agents() if agent.key == "codex")
        self.assertEqual(agent.install_commands["linux"], agent.install_commands["windows"])
        runtime = Runtime("windows", "bash", wsl=True, distro="Ubuntu")
        runner = FakeRunner(runtime, ["apt-get"])
        self.assertIn("apt-get", dependency_install_command(agent.dependencies[0], runtime, runner))

    def test_missing_dependency_detection(self):
        agent = next(agent for agent in get_agents() if agent.key == "codex")
        runner = FakeRunner(Runtime("linux", "bash"), ["node"])
        self.assertEqual(runner.exists("npm"), False)

    def test_dry_run_does_not_execute(self):
        runner = CommandRunner(Runtime("linux", "bash"), dry_run=True)
        self.assertEqual(runner.run("echo safe"), 0)

    @patch("agent_setup.platforms.platform.system", return_value="Linux")
    def test_platform_detection(self, _):
        self.assertEqual(detect_runtime().os_name, "linux")


if __name__ == "__main__":
    unittest.main()
