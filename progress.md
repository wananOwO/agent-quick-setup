# 工作进度日志

## 2026-07-17

- 初始化规划文件。
- 并行调研完成：新增 `research_platform.md`、`research_openclaw_hermes_pi.md`；网络受限部分已标注发布前复核项。
- 完成 Python CLI、Agent 注册表、Windows/WSL 运行目标、依赖包管理器映射、确认/试运行流程。
- 新增 `README.md`、`install.ps1`、`install.sh` 和单元测试。
- 修复中文编码导致的 CLI 字符串语法风险，统一核心运行时输出为 ASCII。
- 尝试运行 `python -m unittest discover -s tests -v`；当前执行环境只有 Microsoft Store Python alias，没有可用解释器，因此未能执行运行时测试。已完成文件级语法风险扫描和 dry-run 逻辑审阅。
- 2026-07-18: Reproduced `install.cmd` returning exit code 9009 with no output. Root cause: the WindowsApps Python app-execution alias is discoverable but not usable.
- GitHub CLI is authenticated as `wananOwO`; `wananOwO/agent-quick-setup` is currently available for creation.
- Fixed Windows Store Python alias detection; missing Python now triggers a visible error or an optional winget bootstrap.
- Added secure one-line bootstraps for PowerShell and POSIX shells, with temporary archive extraction and cleanup.
- Published the public repository at https://github.com/wananOwO/agent-quick-setup and verified the Windows raw-script/archive path.
- GitHub Actions run 29640074251 passed bootstrap, shell syntax, and Python 3.9/3.12 tests on Windows, Ubuntu, and macOS.
- 2026-07-18: User report reproduced three design defects: `subprocess` uses a non-resolved `powershell.exe` shell, Python PATH is only refreshed immediately after installation, and errors are re-thrown at three layers.
- Fixed Windows PowerShell command execution policy, PATH refresh before/after dependency and Agent installation, concise error handling, and Pi package migration to `@earendil-works/pi-coding-agent`.
- Full native Windows Pi install completed successfully; `pi --version` reports 0.80.10 and npm confirms `@earendil-works/pi-coding-agent@0.80.10`.
- 2026-07-18: Ubuntu 24 VPS report shows `curl | bash` consumes stdin, causing Python `input()` to raise EOF at the Agent selection prompt.
- POSIX bootstrap now opens `/dev/tty` on fd 3 and forwards it to `install.sh`; README recommends `bash <(curl ...)`, and CI includes a util-linux `script` pseudo-terminal regression test.
- 2026-07-18: Added `AgentSpec.user_bin_paths` and automatic PATH persistence. Claude Code declares `$HOME/.local/bin`; POSIX writes the shell rc file idempotently and refreshes the current process, WSL writes only inside the selected distro, and native Windows updates the HKCU user PATH. Installation output previews PATH changes and warns (without failing Agent installation) if persistence is unavailable.
- 2026-07-18: Review follow-up: WSL command discovery now uses the detected user's interactive Bash/Zsh shell so `.bashrc`/`.zshrc` PATH entries are visible during verification; macOS Bash uses `.bash_profile`; non-UTF-8 shell files fail with a warning instead of an exception. Added registry, shell-detection, and WSL verification tests.
- 2026-07-18: Commit `43fa568` is complete locally. Three HTTPS push retries failed because the GitHub connection was reset/unreachable; the previous `dba164d` commit remains published.
- 2026-07-18: Added `tests/linux_path_test.sh`, which uses a temporary HOME and a real interactive `bash -ic` subprocess to verify that a persisted `$HOME/.local/bin` entry exposes a Claude executable on native Linux. The test passes locally under Git Bash and runs in the Ubuntu CI shell job.
