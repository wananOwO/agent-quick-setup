# 跨平台 CLI 与 Agent 安装渠道调研

> 本文件只记录平台实现与安装渠道研究，不替代适配器中的运行时探测。第三方项目安装命令、包名和最低版本会变更；实现时应在发布前再次读取官方页面/仓库的 manifest，并允许锁定版本。外网抓取在本环境不可用（连接被沙箱拦截），因此以下链接是官方来源入口，带有“需复核”的命令不能直接硬编码为无确认脚本。

## 1. Agent 官方渠道（截至 2026-07，需在实现时复核）

| Agent | 官方来源 | 常见安装渠道 | 平台与依赖要点 |
|---|---|---|---|
| Claude Code | [Anthropic setup](https://docs.anthropic.com/en/docs/claude-code/setup) | macOS/Linux/WSL 官方安装脚本 `curl -fsSL https://claude.ai/install.sh \\| bash`；Windows PowerShell `irm https://claude.ai/install.ps1 \\| iex`；兼容 npm `npm install -g @anthropic-ai/claude-code` | 官方脚本优先；npm 路径通常要求 Node.js 18+。Windows 原生运行需要 Git for Windows，或选择 WSL 后按 Linux 安装。脚本内容和支持版本应在运行前展示并要求确认。 |
| OpenAI Codex CLI | [OpenAI Codex CLI](https://developers.openai.com/codex/cli/)；[npm package](https://www.npmjs.com/package/@openai/codex) | npm `npm install -g @openai/codex`；macOS 也可使用 Homebrew Cask（以官方页面当前命令为准） | npm 安装需要可用 Node/npm；登录/认证在首次运行时完成。Windows 支持和沙箱能力随版本变化，默认提供 WSL 选项并在适配器中声明限制。 |
| OpenCode | [OpenCode installation](https://opencode.ai/docs/installation/)；[GitHub](https://github.com/anomalyco/opencode) | 官方脚本 `curl -fsSL https://opencode.ai/install \\| bash`；npm `npm install -g opencode-ai`；Homebrew `brew install anomalyco/tap/opencode` | 脚本、npm、brew 三条路径可能不同步；优先官方发布二进制/包管理器，Windows 原生支持需按 release 矩阵复核，WSL 是可靠回退。 |
| OpenClaw | [项目仓库](https://github.com/openclaw/openclaw)；[文档](https://docs.openclaw.ai/)（域名/包名可能随项目迁移） | 常见渠道为项目提供的安装脚本或 npm 全局包（历史上包名/命令有变更）；必须从仓库 README 与 release manifest 动态获取 | 不要把早期 `clawdbot`/`moltbot` 等旧名称当作当前包名。适配器应要求用户选择版本，记录最终解析到的包名、来源 URL 和校验值；没有可验证 manifest 时只生成计划，不自动执行。 |
| Hermes Agent (Nous Research) | [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) | 仓库 installer（README 中的 `scripts/install.sh` 路径需复核）或 PyPI/源码安装（通常为 `pip`/`uv`） | Python 版本、GPU/系统库和可选浏览器依赖因 release 改变；不能只检查 Python。建议优先 `uv`/venv 隔离，安装前读取 pyproject 的 `requires-python` 和 extras；Windows 推荐 WSL。 |
| Pi coding agent | [pi-mono](https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent)；[npm package](https://www.npmjs.com/package/@mariozechner/pi-coding-agent) | `npm install -g @mariozechner/pi-coding-agent`（包名与命令必须从 npm 当前 metadata 复核） | 通常要求 Node.js 20+；npm 全局目录在 macOS/Linux 可能不可写，使用用户级 prefix 而不是无提示 `sudo npm`。Windows 可原生试用，遇到 shell/依赖问题提供 WSL。 |

**适配器契约：** 每个 Agent 以数据描述依赖（`id`、`displayName`、`supportedOS`、`supportedArch`、`minVersions`、`installChannels`、`authNotes`、`sourceUrls`）而不是散落在代码中的命令。安装命令应带版本/校验策略；未知或已失效的渠道返回“需人工确认”，不能猜测。

## 2. 操作系统与 CPU 检测

1. 先区分“执行环境”与“宿主机”。在 WSL 内应按 Linux 处理，不要因为宿主是 Windows 就调用 winget；在 PowerShell 中才探测 WSL。
2. 统一结果枚举：`windows`、`macos`、`linux`、`unknown`；架构统一为 `x64`、`arm64`、`armv7`、`unknown`。所有 Agent 适配器只使用归一化值。
3. 原生实现可用：
   - Windows/.NET：`RuntimeInformation.IsOSPlatform` 与 `OSArchitecture`；同时记录 `ProcessArchitecture`（32 位进程可能误报）。PowerShell 可用 `$IsWindows`，Windows PowerShell 5.1 没有该变量时以 `$env:OS -eq 'Windows_NT'` 回退。
   - macOS/Linux：`uname -s`、`uname -m`；macOS 通过 `sw_vers` 取版本。Apple Silicon 在 Rosetta 下 `uname -m` 可能是 `x86_64`，可读取 `sysctl -in sysctl.proc_translated` 并记录 `translated=true`。
   - Linux 发行版：读取 `/etc/os-release` 的 `ID`/`ID_LIKE`，不要仅凭发行版名称拼命令。容器/BusyBox 可能没有完整字段，应回退到通用脚本并提示。
4. Windows WSL：检测 `wsl.exe --status` 与 `wsl.exe --list --quiet`。若未安装，展示微软官方 `wsl --install` 文档链接（[WSL install](https://learn.microsoft.com/windows/wsl/install)）；该操作需要管理员权限、可能重启，不能在 `--yes` 模式静默执行。让用户选择发行版后，通过 `wsl.exe -d <distro> -- bash -lc <quoted-command>` 执行，并重新在 WSL 内检测依赖。

## 3. 依赖与包管理器策略

| 平台 | 首选 | 回退/注意事项 |
|---|---|---|
| Windows 原生 | `winget`（Microsoft App Installer）检查 `winget --version`；按稳定 ID 安装 Git、Node.js LTS、Python 等 | 不自动安装 Chocolatey/Scoop；若用户已有可使用并显示来源。winget 可能要求 UAC/商店协议，安装前明确列出。 |
| macOS | 已有 Homebrew 时使用 `brew`; `brew --prefix` 判断架构/安装位置 | Homebrew 不应无提示自动引导安装（需要 sudo、写入 shell profile）；没有 brew 时优先 Agent 官方安装器或给出可复制命令。必要的 Xcode Command Line Tools 使用 `xcode-select --install`，需用户确认。 |
| Debian/Ubuntu | `apt-get`/`apt`; 检查 `/etc/os-release` 与命令存在 | `sudo` 只包裹单个包管理命令；不要把整个远程脚本以 root 执行。 |
| Fedora/RHEL | `dnf`（旧系统 `yum`） | 依赖名可能不同，适配器维护发行版映射；安装失败显示手动命令。 |
| Arch | `pacman`；openSUSE `zypper`；Alpine `apk` | 只在检测到对应管理器时执行；不应假定 `apt`。 |

通用探测使用命令及版本输出（`git --version`、`node --version`、`npm --version`、`python3 --version`、`uv --version`），再做 semver 比较。Node/npm 全局安装优先用户 prefix；避免 `sudo npm install -g`。环境变量和 PATH 修改只在用户确认后写入，并提供变更前后 diff。

## 4. CLI 交互、安全与可恢复性

- 两阶段流程：`detect -> plan -> confirm -> apply -> verify`。默认只生成计划并询问确认；`--yes` 是显式选择，仍不能绕过高风险（WSL 安装、系统升级、未知签名）警告。
- 在确认前打印 OS/发行版/架构、目标 Agent、每项依赖、准确命令、权限（用户/UAC/sudo）、下载 URL、预计写入位置及是否重启。支持 `--dry-run`、`--json` 供脚本调用。
- 网络脚本（`curl | sh`、PowerShell `irm | iex`）必须显示 URL、TLS 错误即终止；若官方提供 checksum/签名则校验，优先下载到临时文件后执行。禁止把页面内容拼接进 shell 命令，参数用 argv/严格 quoting。
- 记录结构化日志（时间、适配器版本、解析后的版本、命令退出码），不记录 token/环境变量密钥。每一步失败立即停止，保留日志和已完成步骤；不要自动回滚可能影响系统的包管理操作。
- 已安装 Agent 询问“跳过/升级/重装”；升级必须是独立确认。认证（API key、OAuth）只在 Agent 首次运行交给其官方流程，安装器不收集密钥。
- Linux/macOS 使用 sudo 时检测 tty、解释原因；Windows 使用 UAC。权限不足时输出官方手动命令，不循环提权。

## 5. 实现建议与已知不确定性

- 若主 CLI 使用 Node/TypeScript，会产生“先安装 Node 才能运行安装器”的引导问题。建议发布自包含二进制（Go/Rust）或提供极薄的 PowerShell/sh bootstrap，再由核心 CLI 安装 Node；核心逻辑避免依赖 shell 特性。
- 将 Agent 元数据版本化（例如 `agents/*.json`），启动时可选择安全的官方 metadata refresh；签名/哈希失败或来源域名不在 allowlist 时拒绝自动安装。
- OpenClaw 与 Hermes 的包名/脚本在历史版本中有迁移，OpenCode/Claude 的 Windows 支持也随版本变化。发布前 CI 应在 Windows 原生、Windows+WSL、macOS Intel/Apple Silicon、Ubuntu/Fedora/Arch 容器中运行“仅检测/计划”测试，并定期验证官方安装文档。
