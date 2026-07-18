import unittest
from contextlib import redirect_stdout
from dataclasses import replace
from io import StringIO
from unittest.mock import patch

from agent_setup.commands import CommandRunner
from agent_setup.cli import main
from agent_setup.dependencies import dependency_install_command
from agent_setup.install import install_agent
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

    def test_pi_uses_current_upstream_package(self):
        agent = next(item for item in get_agents() if item.key == "pi")
        self.assertEqual(agent.package, "@earendil-works/pi-coding-agent")
        self.assertIn("@earendil-works/pi-coding-agent", agent.install_commands["windows"][0])
        self.assertIn("npm uninstall --global @mariozechner/pi-coding-agent", agent.install_commands["windows"][0])

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

    @patch("agent_setup.commands.subprocess.run")
    @patch("agent_setup.commands.shutil.which", return_value=r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
    def test_windows_commands_use_resolved_powershell_without_shell_mode(self, _which, run):
        run.return_value.returncode = 7
        runner = CommandRunner(Runtime("windows", "powershell"))

        result = runner.run("npm --version")

        args, kwargs = run.call_args
        self.assertEqual(args[0][0], r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
        self.assertEqual(args[0][-2:], ["-Command", "npm --version"])
        self.assertIn("-ExecutionPolicy", args[0])
        self.assertIn("Bypass", args[0])
        self.assertFalse(kwargs.get("shell", False))
        self.assertFalse(kwargs.get("check", True))
        self.assertEqual(result, 7)

    def test_install_fails_when_agent_command_is_still_missing(self):
        class MissingAgentRunner(CommandRunner):
            def __init__(self):
                super().__init__(Runtime("windows", "powershell"))

            def exists(self, command):
                return command in {"node", "npm", "winget"}

            def run(self, command, check=False):
                return 0

        agent = replace(next(item for item in get_agents() if item.key == "pi"), package=None)
        output = StringIO()
        with redirect_stdout(output):
            result = install_agent(agent, MissingAgentRunner(), input_fn=lambda _prompt: "y")

        self.assertFalse(result)
        self.assertIn("could not be verified", output.getvalue())

    def test_dry_run_does_not_require_agent_to_already_exist(self):
        class PreviewRunner(CommandRunner):
            def __init__(self):
                super().__init__(Runtime("windows", "powershell"), dry_run=True)

            def exists(self, command):
                return command in {"node", "npm", "winget"}

        agent = next(item for item in get_agents() if item.key == "pi")
        output = StringIO()
        with redirect_stdout(output):
            result = install_agent(agent, PreviewRunner(), input_fn=lambda _prompt: "y")

        self.assertTrue(result)
        self.assertIn("Dry run", output.getvalue())

    def test_dependency_install_refreshes_environment_before_agent_install(self):
        class RefreshingRunner(CommandRunner):
            def __init__(self):
                super().__init__(Runtime("windows", "powershell"))
                self.refreshed = False
                self.agent_installed = False

            def exists(self, command):
                if command == "winget":
                    return True
                if command in {"node", "npm"}:
                    return self.refreshed
                if command == "pi":
                    return self.agent_installed
                return False

            def refresh_environment(self):
                self.refreshed = True

            def run(self, command, check=False):
                if command.startswith("winget install"):
                    return 0
                if "@earendil-works/pi-coding-agent" in command:
                    if not self.refreshed:
                        return 127
                    self.agent_installed = True
                    return 0
                return 1

        agent = next(item for item in get_agents() if item.key == "pi")
        result = install_agent(agent, RefreshingRunner(), input_fn=lambda _prompt: "y")

        self.assertTrue(result)

    def test_command_start_failure_is_reported_without_exception(self):
        class BrokenRunner(CommandRunner):
            def __init__(self):
                super().__init__(Runtime("windows", "powershell"), dry_run=True)

            def exists(self, command):
                return command in {"node", "npm", "winget"}

            def run(self, command, check=False):
                raise OSError("command process could not be started")

        agent = next(item for item in get_agents() if item.key == "pi")
        output = StringIO()
        with redirect_stdout(output):
            result = install_agent(agent, BrokenRunner(), input_fn=lambda _prompt: "y")

        self.assertFalse(result)
        self.assertIn("could not be started", output.getvalue())

    def test_agent_install_refreshes_path_before_verification(self):
        class AgentPathRunner(CommandRunner):
            def __init__(self):
                super().__init__(Runtime("windows", "powershell"))
                self.installed = False
                self.refreshed = False

            def exists(self, command):
                if command in {"node", "npm", "winget"}:
                    return True
                if command == "pi":
                    return self.installed and self.refreshed
                return False

            def run(self, command, check=False):
                self.installed = True
                return 0

            def refresh_environment(self):
                self.refreshed = True

        agent = next(item for item in get_agents() if item.key == "pi")
        result = install_agent(agent, AgentPathRunner(), input_fn=lambda _prompt: "y")

        self.assertTrue(result)

    @patch("agent_setup.cli.install_agent", side_effect=RuntimeError("unexpected installer failure"))
    @patch("agent_setup.cli.choose_windows_target", return_value=Runtime("linux", "bash"))
    def test_cli_converts_unexpected_errors_to_concise_failure(self, _runtime, _install):
        stderr = StringIO()
        with patch("sys.stderr", stderr):
            result = main(["pi", "--yes"])

        self.assertEqual(result, 1)
        self.assertIn("unexpected installer failure", stderr.getvalue())

    @patch("agent_setup.platforms.platform.system", return_value="Linux")
    def test_platform_detection(self, _):
        self.assertEqual(detect_runtime().os_name, "linux")


if __name__ == "__main__":
    unittest.main()
