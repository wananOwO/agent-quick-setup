import os
import sys
import unittest
from contextlib import redirect_stdout
from dataclasses import replace
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from agent_setup.commands import CommandRunner
from agent_setup.cli import main
from agent_setup.dependencies import dependency_install_command
from agent_setup.install import install_agent
from agent_setup.models import Runtime
from agent_setup.platforms import detect_runtime, wsl_user_shell
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

    def test_every_agent_declares_user_path_strategy(self):
        for agent in get_agents():
            self.assertTrue(agent.user_bin_paths, agent.key)

    @patch("agent_setup.commands.subprocess.run")
    def test_npm_global_bin_path_is_resolved_for_node_agents(self, run):
        run.return_value.returncode = 0
        run.return_value.stdout = "/home/test/.npm-global\n"
        runner = CommandRunner(Runtime("linux", "bash"))

        self.assertEqual(runner.resolve_path_entry("$NPM_GLOBAL_BIN"), "/home/test/.npm-global/bin")

    @patch("agent_setup.commands.shutil.which", return_value=r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
    @patch("agent_setup.commands.subprocess.run")
    def test_windows_npm_global_bin_uses_powershell_capture(self, run, _which):
        run.return_value.returncode = 0
        run.return_value.stdout = r"C:\Users\Test\AppData\Roaming\npm" + "\n"
        runner = CommandRunner(Runtime("windows", "powershell"))

        self.assertEqual(runner.resolve_path_entry("$NPM_GLOBAL_BIN"), r"C:\Users\Test\AppData\Roaming\npm")
        args = run.call_args.args[0]
        self.assertIn("-Command", args)
        self.assertIn("npm prefix --global", args)

    def test_pi_uses_current_upstream_package(self):
        agent = next(item for item in get_agents() if item.key == "pi")
        self.assertEqual(agent.package, "@earendil-works/pi-coding-agent")
        self.assertIn("@earendil-works/pi-coding-agent", agent.install_commands["windows"][0])
        self.assertIn("npm uninstall --global @mariozechner/pi-coding-agent", agent.install_commands["windows"][0])

    def test_claude_declares_user_bin_path(self):
        agent = next(item for item in get_agents() if item.key == "claude-code")
        self.assertIn("$HOME/.local/bin", agent.user_bin_paths)

    def test_persist_user_path_updates_bashrc_idempotently_and_process_path(self):
        with TemporaryDirectory() as home:
            with patch.dict("os.environ", {"HOME": home, "PATH": ""}, clear=False):
                runner = CommandRunner(Runtime("linux", "bash"))

                self.assertTrue(runner.persist_user_path("$HOME/.local/bin"))
                config = Path(home) / ".bashrc"
                line = 'export PATH="$HOME/.local/bin:$PATH"'
                self.assertIn(line, config.read_text())
                self.assertIn(str(Path(home) / ".local" / "bin"), os.environ["PATH"])

                self.assertTrue(runner.persist_user_path("$HOME/.local/bin"))
                self.assertEqual(config.read_text().count(line), 1)

    def test_persist_user_path_uses_zshrc_for_zsh(self):
        with TemporaryDirectory() as home:
            with patch.dict("os.environ", {"HOME": home, "PATH": ""}, clear=False):
                runner = CommandRunner(Runtime("macos", "/bin/zsh"))
                self.assertTrue(runner.persist_user_path("$HOME/.local/bin"))
                self.assertTrue((Path(home) / ".zshrc").exists())
                self.assertFalse((Path(home) / ".bashrc").exists())

    def test_persist_user_path_warns_cleanly_for_non_utf8_shell_file(self):
        with TemporaryDirectory() as home:
            config = Path(home) / ".bashrc"
            config.write_bytes(b"export PATH=\xff\n")
            with patch.dict("os.environ", {"HOME": home, "PATH": ""}, clear=False):
                runner = CommandRunner(Runtime("linux", "bash"))
                self.assertFalse(runner.persist_user_path("$HOME/.local/bin"))

    def test_wsl_path_persistence_runs_inside_wsl_without_host_file_write(self):
        with TemporaryDirectory() as home:
            with patch.dict("os.environ", {"HOME": home}, clear=False):
                runner = CommandRunner(Runtime("windows", "bash", wsl=True, distro="Ubuntu"))
                with patch.object(runner, "run", return_value=0) as run:
                    self.assertTrue(runner.persist_user_path("$HOME/.local/bin"))
                self.assertFalse((Path(home) / ".bashrc").exists())
                command = run.call_args.args[0]
                self.assertIn(".bashrc", command)
                self.assertIn("export PATH=", command)

    @patch("agent_setup.commands.subprocess.run")
    def test_wsl_exists_uses_interactive_shell_for_user_path(self, run):
        run.return_value.returncode = 0
        runner = CommandRunner(Runtime("windows", "bash", wsl=True, distro="Ubuntu"))

        self.assertTrue(runner.exists("claude"))
        args = run.call_args.args[0]
        self.assertIn("-ic", args)

    def test_macos_bash_uses_login_profile(self):
        runner = CommandRunner(Runtime("macos", "/bin/bash"))
        self.assertEqual(runner._shell_config_name(), ".bash_profile")

    @patch("agent_setup.platforms.subprocess.run")
    def test_wsl_user_shell_detects_zsh(self, run):
        run.return_value.stdout = "/bin/zsh\n"
        self.assertEqual(wsl_user_shell("Ubuntu"), "zsh")

    def test_windows_user_path_persistence_preserves_and_deduplicates_registry_path(self):
        class FakeKey:
            values = {"Path": ("/existing", 2)}

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def QueryValueEx(self, _key, name):
                return self.values[name]

            def SetValueEx(self, _key, name, _reserved, value_type, value):
                self.values[name] = (value, value_type)

        class FakeWinreg:
            HKEY_CURRENT_USER = object()
            REG_EXPAND_SZ = 2
            key = FakeKey()

            @classmethod
            def CreateKey(cls, _hive, _path):
                return cls.key

            @classmethod
            def QueryValueEx(cls, key, name):
                return key.QueryValueEx(key, name)

            @classmethod
            def SetValueEx(cls, key, name, reserved, value_type, value):
                return key.SetValueEx(key, name, reserved, value_type, value)

        with TemporaryDirectory() as home:
            with patch.dict("os.environ", {"HOME": home, "USERPROFILE": home, "PATH": ""}, clear=False):
                with patch.dict(sys.modules, {"winreg": FakeWinreg}):
                    runner = CommandRunner(Runtime("windows", "powershell"))
                    self.assertTrue(runner.persist_user_path("$HOME/.local/bin"))
                    self.assertTrue(runner.persist_user_path("$HOME/.local/bin"))

        persisted = FakeWinreg.key.values["Path"][0].split(os.pathsep)
        self.assertEqual(["/existing", os.path.join(home, ".local", "bin")], persisted)

    def test_install_persists_agent_path_before_verification(self):
        class PathRunner(CommandRunner):
            def __init__(self):
                super().__init__(Runtime("linux", "bash"))
                self.persisted = []

            def exists(self, command):
                return command == "claude"

            def run(self, command, check=False):
                return 0

            def persist_user_path(self, path):
                self.persisted.append(path)
                return True

        agent = next(item for item in get_agents() if item.key == "claude-code")
        output = StringIO()
        runner = PathRunner()
        with redirect_stdout(output):
            result = install_agent(agent, runner, input_fn=lambda _prompt: "y")

        self.assertTrue(result)
        self.assertEqual(["$HOME/.local/bin"], runner.persisted)
        self.assertIn("PATH", output.getvalue())

    def test_path_persistence_failure_does_not_mark_completed_install_as_failed(self):
        class UnpersistableRunner(CommandRunner):
            def __init__(self):
                super().__init__(Runtime("linux", "bash"))

            def exists(self, command):
                return False

            def run(self, command, check=False):
                return 0

            def persist_user_path(self, path):
                return False

        agent = next(item for item in get_agents() if item.key == "claude-code")
        output = StringIO()
        with redirect_stdout(output):
            result = install_agent(agent, UnpersistableRunner(), input_fn=lambda _prompt: "y")

        self.assertTrue(result)
        self.assertIn("could not persist PATH", output.getvalue())
        self.assertIn("could not verify", output.getvalue())

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

        agent = replace(next(item for item in get_agents() if item.key == "pi"), package=None, user_bin_paths=[])
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
