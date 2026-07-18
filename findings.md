# 调研与设计发现

## Agent 安装资料

调研原始记录见 [research_platform.md](research_platform.md) 和 [research_openclaw_hermes_pi.md](research_openclaw_hermes_pi.md)。核心安装渠道如下（发布前仍需在线复核易变包名/版本）：

| Agent | 官方安装方式/包名 | 运行时依赖与注意事项 |
|---|---|---|
| Claude Code | `curl -fsSL https://claude.ai/install.sh \| bash`；Windows `irm https://claude.ai/install.ps1 \| iex`；npm 备用 `@anthropic-ai/claude-code` | 原生脚本通常不要求 Node；npm 方式需要 Node 18+；Windows 可切换 WSL |
| Codex | `npm install --global @openai/codex` | Node.js/npm；首次运行自行完成认证 |
| OpenCode | `npm install --global opencode-ai`；官方脚本/ Homebrew 亦可能可用 | Node.js/npm；Windows 支持需按 release 矩阵复核 |
| OpenClaw | 官网脚本或 `npm install --global openclaw@latest` | Node/npm，近期版本常要求 Node 22+；包名和 onboarding 命令需动态核验 |
| Hermes | 官方仓库 installer 或 Python 安装；当前适配器使用 `python -m pip install --upgrade hermes-agent` 作为可审阅候选 | Python 版本、脚本路径和 Windows 原生支持需发布前读取 README/pyproject |
| Pi | 先卸载旧包，再安装 `@earendil-works/pi-coding-agent` | Node/npm，当前包要求 Node 22.19+；旧包 `@mariozechner/pi-coding-agent` 已弃用 |

## 依赖与平台矩阵

- Windows 原生：优先 winget 安装 Git、Node.js LTS、Python；PowerShell 中显示完整命令并确认。
- Windows + WSL：通过 `wsl.exe -d <distro> -- bash -lc ...` 在 WSL 内重新检测和安装，使用 Linux 包管理器；不混用 Windows PATH。
- macOS：已有 Homebrew 时使用 brew；否则优先 Agent 官方脚本并提示用户自行安装 Xcode Command Line Tools。
- Linux：按 apt-get、dnf、pacman 探测并生成依赖命令；不假设发行版。
- 所有安装遵循 `detect → plan → confirm → apply → verify`，不自动安装 WSL、系统升级或删除用户配置。

## 架构决策

- 选择 Python 3.9+ 标准库实现核心 CLI，避免为了安装 Node Agent 而先要求 Node。
- `AgentSpec` 数据对象集中描述 Agent，`CommandRunner` 隔离 Windows PowerShell/WSL/Unix 执行，新增 Agent 只需注册适配器。
- 依赖检查支持命令别名（Windows 的 `python`/`python3`、`pip`/`pip3`），包管理器映射集中维护。
- 安装命令在执行前始终打印并确认；`--dry-run` 可离线审阅，`--yes` 是显式自动确认开关。

## PATH persistence findings

- Claude Code's native installer places its executable in `$HOME/.local/bin` on POSIX systems; this directory must be persisted before verification.
- Persistence is shell-specific and idempotent: bash `.bashrc`, zsh `.zshrc`, fallback `.profile`.
- WSL persistence must execute within `wsl.exe`; writing the Windows host's `$HOME` would leave the selected Linux target broken.
- A child installer process cannot update its parent's environment, so the installer updates its own PATH and documents reopening the terminal.
- WSL verification must use an interactive shell (`bash -ic`/`zsh -ic`); non-interactive `bash -lc` may return before loading `.bashrc`.
- macOS Bash login shells conventionally use `.bash_profile`; WSL shell detection now supports Bash and Zsh with a Bash fallback.
- Native Ubuntu flow uses the same POSIX persistence path as macOS/Linux; an integration test now verifies `.bashrc` loading in a real interactive Bash subprocess rather than only mocking `CommandRunner`.
- PATH configuration is now an Agent-wide post-install concern: npm-based tools resolve the active global prefix instead of assuming Claude's `$HOME/.local/bin`, while Python/native tools retain user-local fallbacks.
