# Agent Quick Setup

一条命令检测环境并安装主流 Agent CLI，支持 Windows、Windows WSL、macOS 和 Linux。

首版支持：Claude Code、OpenAI Codex CLI、OpenCode、OpenClaw、Hermes Agent、Pi Coding Agent。

## 一键启动

Windows CMD 或 PowerShell：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Invoke-RestMethod 'https://raw.githubusercontent.com/wananOwO/agent-quick-setup/main/bootstrap.ps1' | Invoke-Expression"
```

macOS / Linux：

```bash
curl -fsSL https://raw.githubusercontent.com/wananOwO/agent-quick-setup/main/bootstrap.sh | bash
```

如果更习惯 `wget`：

```bash
bash <(wget -qO- https://raw.githubusercontent.com/wananOwO/agent-quick-setup/main/bootstrap.sh)
```

远程引导脚本会：

1. 使用 HTTPS 下载 GitHub 仓库归档；
2. 解压到随机临时目录；
3. 检测 Python 3.9+；缺失时显示包管理器命令并询问是否安装；
4. 启动 Agent 交互式选择界面；
5. 退出后清理临时文件。

脚本不会关闭 TLS 证书验证，也不会收集 API key 或自动完成模型账号登录。

## 本地运行

Windows 不需要修改永久执行策略，使用 CMD 包装入口：

```powershell
.\install.cmd
```

macOS / Linux：

```bash
sh ./install.sh
```

也可以在已有 Python 3.9+ 的环境直接运行：

```bash
python -m agent_setup --list
python -m agent_setup claude-code codex
python -m agent_setup --dry-run pi
```

## 安装流程

默认流程为：

```text
detect -> plan -> confirm -> apply -> verify
```

- Windows 原生优先使用 `winget` 补齐 Python、Node.js、npm 和 Git。
- Windows 检测到 WSL 后，可选择把依赖检测和 Agent 安装全部放在 WSL 内完成。
- macOS 优先使用 Homebrew。
- Linux 自动识别 apt、dnf 或 pacman。
- 每条系统修改和 Agent 安装命令都会在执行前显示并请求确认。

## Agent 安装渠道

| Agent | 安装渠道 | 主要依赖 |
|---|---|---|
| Claude Code | Anthropic 官方安装脚本 | 原生脚本通常不需要 Node.js |
| Codex | `npm install --global @openai/codex` | Node.js / npm |
| OpenCode | `npm install --global opencode-ai` | Node.js / npm |
| OpenClaw | `npm install --global openclaw@latest` | Node.js / npm；版本约束动态查询 |
| Hermes Agent | Python 包或官方仓库安装器 | Python / pip / Git |
| Pi | `npm install --global @mariozechner/pi-coding-agent` | Node.js / npm；版本约束动态查询 |

OpenClaw、Hermes 的上游安装方式可能变化，发布前需按 `research_*.md` 的复核清单确认。

## 测试

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\windows_bootstrap_test.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\remote_bootstrap_test.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\python_bootstrap_test.ps1
```

```bash
python -m unittest discover -s tests -v
```

远程下载只验证模式：

```powershell
$env:AGENT_SETUP_DOWNLOAD_ONLY = "1"
irm https://raw.githubusercontent.com/wananOwO/agent-quick-setup/main/bootstrap.ps1 | iex
```

```bash
curl -fsSL https://raw.githubusercontent.com/wananOwO/agent-quick-setup/main/bootstrap.sh | AGENT_SETUP_DOWNLOAD_ONLY=1 bash
```
