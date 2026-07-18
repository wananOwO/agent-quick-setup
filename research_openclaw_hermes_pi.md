# OpenClaw、Hermes Agent、Pi Coding Agent 安装调研

> Live metadata update (2026-07-18): npm now marks `@mariozechner/pi-coding-agent` deprecated and points to `@earendil-works/pi-coding-agent` (latest observed 0.80.10, Node >=22.19.0). The installer registry follows the new package and migrates the old global package.

> 调研日期：2026-07-17
>
> 本次执行环境无法解析 `github.com` / `raw.githubusercontent.com`，因此不能在本次会话中实时抓取官方 README。下文优先采用已知的官方仓库、官网和官方包名；对容易随版本变化的 Node/Python 版本、脚本路径及 Windows 支持状态明确标注为“运行时查询”或“发布前复核”，不应把未核验值静态写死到安装器中。

## 结论摘要

| Agent | 官方/主要分发方式 | 主要运行时 | macOS | Linux | Windows 原生 | Windows WSL2 | 置信度 |
|---|---|---|---|---|---|---|---|
| OpenClaw | 官网安装脚本；npm 包 `openclaw` | Node.js（当前代际通常要求 Node 22） | 支持 | 支持 | npm 路径可能可运行，但后台服务集成应谨慎 | 推荐 | 中高，版本要求需动态核验 |
| Hermes Agent | 官方 GitHub 安装脚本/源码安装 | Python（具体范围读取 `pyproject.toml`） | 支持 | 支持 | 未确认官方原生支持 | 推荐 | 中，必须在开发时在线复核脚本 |
| Pi Coding Agent | npm 包 `@mariozechner/pi-coding-agent` | Node.js（已知近期版本要求 Node 20+） | 支持 | 支持 | 支持 | 支持 | 高，精确 `engines.node` 仍应动态查询 |

安装器实现上应把三者做成独立 manifest/provider，而不是把命令写进一个大脚本。每个 manifest 至少包含：官方来源、包管理器、平台策略、运行时约束查询方法、安装命令、验证命令、卸载命令、配置目录、凭据提示和回滚信息。

---

## 1. OpenClaw

### 项目标识与官方来源

本调研所称 OpenClaw 是本地运行的个人 AI Agent / gateway 项目，不是名称相近的游戏引擎或其他旧项目。实现前应再次确认仓库 owner 和 npm 包的 provenance，避免同名包风险。

- 官网：<https://openclaw.ai/>
- 官方文档：<https://docs.openclaw.ai/>
- 官方仓库（待在线确认当前 canonical URL）：<https://github.com/openclaw/openclaw>
- npm：<https://www.npmjs.com/package/openclaw>
- npm registry 元数据：<https://registry.npmjs.org/openclaw/latest>

### 官方安装路径

macOS、Linux、WSL2 的已知推荐入口：

```sh
curl -fsSL https://openclaw.ai/install.sh | bash
```

更适合本项目做可审计安装的 npm 路径：

```sh
npm install --global openclaw@latest
openclaw onboard --install-daemon
```

不建议安装器直接执行 `curl | bash`。应先下载到临时目录，校验最终 URL、HTTPS、可选 checksum/签名，并在用户确认后执行；或者优先使用 npm 安装，因为 npm 路径更容易检测版本、卸载和记录变更。

Windows 的默认策略应为：

1. 检测 Windows build、是否启用 WSL，以及是否已有 Linux 发行版。
2. 交互提供“安装到 WSL2（推荐）”和“尝试 Windows 原生 npm 安装”两个选项。
3. WSL2 路径中在发行版内部检测/安装 Node 和 npm，不能错误复用 Windows 的 `node.exe`、npm prefix 或 PATH。
4. 原生 Windows 路径应提示：CLI 本身可能可运行，但 daemon/service、Unix shell 工具及插件兼容性可能弱于 WSL2；发布前须以官方 Windows 文档为准。

### 前置依赖

必需或核心：

- Node.js。近期版本已知通常使用 Node 22；**精确版本必须在安装时读取 npm 的 `engines.node`**。
- npm，通常随 Node 安装。
- 可写的全局 npm prefix，或使用用户级版本管理器/用户级 prefix，避免默认请求管理员权限。

按安装方式需要：

- 官网 shell installer 需要 `curl`、POSIX shell；脚本内部是否还要求 `git` 应在下载后静态检查。
- WSL2 路径需要 `wsl.exe`、WSL2 功能和一个 Linux distribution。
- `git` 很可能被插件、工作区或更新流程使用，建议作为“推荐依赖”，但不要在没有官方声明时标为启动 CLI 的绝对必需项。

凭据/配置：

- 首次 `onboard` 会配置模型供应商和 gateway；具体 API key 取决于选择的 provider。
- 配置/状态目录已知为用户目录下的 `.openclaw`；删除时必须二次确认，默认卸载不删除用户数据。

### 检测逻辑

```sh
# 已安装检查
command -v openclaw
openclaw --version

# 查询最新版和精确 Node 约束
npm view openclaw@latest version --json
npm view openclaw@latest engines --json
npm view openclaw@latest dist.tarball dist.integrity repository --json

# 环境
node --version
npm --version
git --version
```

PowerShell 对应：

```powershell
Get-Command openclaw -ErrorAction SilentlyContinue
openclaw --version
npm view openclaw@latest version engines dist.integrity repository --json
node --version
npm --version
wsl.exe --status
wsl.exe --list --verbose
```

安全门禁：安装前校验 npm 元数据中的 repository 与预期官方仓库一致，并记录 `dist.integrity`。如果 owner、包名、仓库或站点发生变化，应停止自动安装并提示用户复核。

### 验证

最低验证：

```sh
openclaw --version
openclaw --help
```

完成 onboarding/daemon 安装后的功能验证（命令是否仍存在需按当前文档复核）：

```sh
openclaw doctor
openclaw gateway status
```

验证阶段不应自动发起付费模型请求。健康检查与真实推理请求应拆成两个步骤，后者必须得到用户确认。

### 卸载

npm 安装路径的确定性卸载：

```sh
# 先停止/移除后台 gateway；子命令需按安装版本的 --help 复核
openclaw gateway stop
openclaw gateway uninstall

npm uninstall --global openclaw
```

如果通过官网脚本安装，安装器应保存脚本输出和安装清单，并优先调用官方 uninstall 子命令（如果当前版本提供）。不要靠猜测删除目录。

最后检查：

```sh
command -v openclaw || true
npm list --global --depth=0 openclaw
```

用户配置目录只在用户明确选择“同时删除数据”时删除。Windows 与 WSL 的 home 目录相互独立，必须在实际安装目标内执行卸载。

### 发布前必须复核

- 官网脚本的当前 URL、checksum/签名机制以及脚本支持的平台。
- npm 最新版本的 `engines.node`，不要长期硬编码 Node 22。
- Windows 原生是否已成为官方完整支持路径。
- daemon 的安装、停止和卸载子命令名称。
- npm 包 repository/provenance 是否仍指向 canonical 官方仓库。

---

## 2. Hermes Agent（Nous Research）

### 项目标识与官方来源

- 官方仓库：<https://github.com/NousResearch/hermes-agent>
- README：<https://github.com/NousResearch/hermes-agent/blob/main/README.md>
- raw README：<https://raw.githubusercontent.com/NousResearch/hermes-agent/main/README.md>
- Nous Research：<https://nousresearch.com/>

注意不要与同名的 Hermes LLM 模型、旧版 `hermes` Python 包或其他 CLI 混淆。安装器应该通过仓库 URL 与 package metadata 联合确认身份。

### 官方安装路径

已知官方仓库提供/曾提供安装脚本，常见入口为：

```sh
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

由于本次无法联网核验，**`scripts/install.sh` 的当前路径与 Windows 脚本是否存在必须在实现时以 README 为准**。本项目不应在验证前把该 URL 作为无条件执行命令。

可靠的审计流程应是：

```sh
git clone https://github.com/NousResearch/hermes-agent.git
cd hermes-agent

# 阅读当前 README、Python 约束和官方安装脚本
sed -n '1,240p' README.md
grep -nE 'requires-python|python_requires' pyproject.toml setup.cfg setup.py 2>/dev/null
find . -maxdepth 2 -type f \( -name 'install.sh' -o -name 'setup.sh' \) -print
```

然后仅执行 README 当前明确推荐的命令。若项目的 `pyproject.toml` 可直接作为 Python application 安装，可考虑隔离安装：

```sh
# 只有在当前官方项目元数据确认支持时使用
uv tool install 'git+https://github.com/NousResearch/hermes-agent.git'
# 或
pipx install 'git+https://github.com/NousResearch/hermes-agent.git'
```

`uv tool` / `pipx` 路径利于隔离和卸载，但不能声称是官方首选，除非当前 README 明确如此。若官方脚本还会安装额外资源、技能、浏览器组件或本地服务，单纯 pip/uv 安装可能不完整。

### 平台策略

- Linux：目标平台，优先支持。
- macOS：目标平台，优先支持；需区分 Apple Silicon 与 Intel，尤其是带原生依赖的 Python wheels。
- Windows 原生：本次无法确认官方完整支持，不应默认自动安装。
- Windows WSL2：当前最稳妥的 Windows 路径，建议默认；在 WSL 内完成 Python、git、uv/pipx 和 Hermes 的全部检测与安装。

### 前置依赖

核心：

- Python 3。精确范围必须读取仓库 `pyproject.toml` 的 `requires-python`，不能仅凭经验写死。
- Python 虚拟环境/隔离工具。优先 `uv tool` 或 `pipx`；如果官方脚本自带 venv 管理，则遵从官方脚本。
- `git`，用于可靠地获取官方仓库以及可能的更新操作。
- `curl`，仅在使用官方 one-line installer 时需要。

可能由功能触发的可选依赖：

- 编译工具链和 Python headers：当平台没有预编译 wheel 时需要。
- Docker：只有 sandbox/container 工具启用时才需要，不应为基础 CLI 无条件安装。
- 浏览器自动化、音频、搜索等工具的系统包：必须根据当前官方 extras/README 和用户启用的功能安装。

凭据：

- Hermes 可接入的推理服务和环境变量会随版本变化，应从 README 或 `hermes --help` 获取。
- API key 不应由安装器打印、写入日志或保存到项目目录；优先调用 Hermes 自身 onboarding/config 命令，或者写入用户选择的系统 secret store。

### 检测逻辑

```sh
command -v hermes
hermes --help

python3 --version
git --version
curl --version
uv --version
pipx --version
```

源码元数据查询建议：

```sh
git ls-remote https://github.com/NousResearch/hermes-agent.git HEAD

# clone 到临时目录后解析，不执行仓库代码
python3 -c "import tomllib,pathlib; p=tomllib.loads(pathlib.Path('pyproject.toml').read_text()); print(p.get('project',{}).get('requires-python')); print(p.get('project',{}).get('scripts',{}))"
```

安装器应解析 `[project.scripts]` 后再确认实际命令是否为 `hermes`；不要仅依赖显示名称。

### 验证

不会消耗模型额度的最低验证：

```sh
hermes --help
```

如果当前版本明确支持版本参数，再执行：

```sh
hermes --version
```

此外应检查：

- 可执行文件是否来自刚创建的 venv/tool 环境。
- `python` ABI 与安装目标一致。
- CLI 启动时无缺失动态库。
- 真实模型调用作为可选 smoke test，明确提示可能产生费用。

### 卸载

卸载必须与实际安装方式对称：

```sh
# uv tool 安装
uv tool uninstall hermes-agent

# pipx 安装；实际 distribution name 要从 metadata 获取
pipx uninstall hermes-agent
```

若官方 installer 采用 clone + venv + symlink/wrapper，不能假设上述命令有效。安装器必须在安装时记录：

- distribution name/version；
- venv/clone 路径；
- 创建的 wrapper/symlink；
- PATH 修改；
- 是否创建 daemon、container 或额外资源。

卸载时依照记录逐项回滚；用户历史、配置、skills、会话和凭据默认保留，只有明确确认后才删除。

### 发布前必须复核

- README 当前推荐的 one-line 安装命令和脚本实际路径。
- `pyproject.toml` 的 `requires-python`、distribution name 和 `[project.scripts]`。
- macOS Apple Silicon、Linux 发行版及 Windows/WSL 的官方支持表。
- 是否需要 `uv`、Docker、Node、系统编译器或额外系统库。
- 官方卸载方式以及配置/数据目录。

---

## 3. Pi Coding Agent

### 项目标识与官方来源

此处的 Pi 是 Mario Zechner 的 terminal coding agent，位于 `pi-mono` monorepo；不要与 Raspberry Pi、Inflection Pi 或 npm 上其他同名包混淆。

- 官方仓库：<https://github.com/badlogic/pi-mono>
- Coding Agent README：<https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent>
- raw README：<https://raw.githubusercontent.com/badlogic/pi-mono/main/packages/coding-agent/README.md>
- 官方 npm 包：<https://www.npmjs.com/package/@mariozechner/pi-coding-agent>
- npm registry 元数据：<https://registry.npmjs.org/@mariozechner%2fpi-coding-agent/latest>

### 官方安装

```sh
npm install --global @mariozechner/pi-coding-agent
pi
```

为了结果可复现，安装器先解析 latest 得到精确版本，再向用户展示并安装：

```sh
PI_VERSION="$(npm view @mariozechner/pi-coding-agent@latest version)"
npm install --global "@mariozechner/pi-coding-agent@${PI_VERSION}"
```

不要使用无关的 `npm install -g pi`。

### 平台支持

- macOS：支持。
- Linux：支持。
- Windows 原生：npm/Node 路径支持；需要正确处理 PowerShell PATH、npm global prefix 和 `.cmd` shim。
- Windows WSL2：支持，并且更适合 Unix-first 的开发环境。与 OpenClaw/Hermes 一样，Windows 和 WSL 的 Node/npm/PATH/配置必须完全分开检测。

安装器可以在 Windows 提供两个目标，不应重复安装：

- `windows-native`：使用 PowerShell 下的 `node.exe` 和 `npm.cmd`。
- `wsl:<distro>`：通过 `wsl.exe -d <distro> -- ...` 在 Linux 内安装。

### 前置依赖

核心：

- Node.js。近期已知要求 Node 20+；**精确 SemVer 约束从 npm `engines.node` 获取并用 SemVer 库判断**。
- npm，随 Node 安装。

推荐但不一定是 CLI 启动的硬依赖：

- `git`，用于 coding workflow 和版本库上下文。
- 常见 shell 工具，具体取决于用户让 Pi 执行的任务；不能作为基础安装的全量强制依赖。

凭据：

- Pi 支持多个模型供应商，使用哪一种决定所需 API key 或登录流程。
- 安装完成不等于 provider 已配置。应把“CLI 安装验证”与“模型 provider 配置”分成两个状态。
- 优先引导使用 Pi 自身的登录/配置交互；支持的 provider、环境变量和 OAuth 登录方式应从当前 README/CLI 帮助动态读取。

### 检测逻辑

```sh
# 身份与版本
command -v pi
pi --version

# 运行时
node --version
npm --version
git --version

# 包的可信元数据与精确约束
npm view @mariozechner/pi-coding-agent@latest version --json
npm view @mariozechner/pi-coding-agent@latest engines --json
npm view @mariozechner/pi-coding-agent@latest bin repository dist.integrity --json
```

安装前至少校验：

- `bin` 中存在预期的 `pi`；
- repository 指向 `badlogic/pi-mono`；
- 当前 Node 满足 `engines.node`；
- 解析得到的是 scope 包 `@mariozechner/pi-coding-agent`，不是同名/仿冒包；
- 记录 exact version 和 `dist.integrity`。

Windows PowerShell：

```powershell
Get-Command pi -ErrorAction SilentlyContinue
Get-Command node -ErrorAction SilentlyContinue
Get-Command npm -ErrorAction SilentlyContinue
npm view '@mariozechner/pi-coding-agent@latest' version engines bin repository dist.integrity --json
```

### 验证

```sh
pi --version
pi --help
npm list --global --depth=0 @mariozechner/pi-coding-agent
```

最低验证不应发送模型请求。可选的 provider smoke test 应单独询问，并说明可能产生费用。

还应检查实际命令解析位置，防止旧版本遮蔽：

```sh
command -v pi
npm prefix --global
```

PowerShell：

```powershell
(Get-Command pi).Source
npm prefix --global
```

### 卸载

```sh
npm uninstall --global @mariozechner/pi-coding-agent
```

验证卸载：

```sh
npm list --global --depth=0 @mariozechner/pi-coding-agent
command -v pi || true
```

用户配置和会话默认保留。已知 Pi 的用户级数据位于 `~/.pi` 体系下（coding agent 常见目录为 `~/.pi/agent`）；**确切目录应按当前 README 复核**，并且只能在用户明确选择“清除数据”后删除。

### 发布前必须复核

- npm 最新包的 `engines.node`，不要长期硬编码 Node 20。
- README 当前列出的 Windows 支持和 provider 登录方式。
- 配置、会话、extensions/skills 的当前目录。
- `pi --version` 在当前发布版是否稳定可用；始终保留 `pi --help` 作为无副作用验证。

---

## 4. 对统一安装器的具体实现建议

### 4.1 manifest 草案

```yaml
id: pi
displayName: Pi Coding Agent
officialSources:
  repository: https://github.com/badlogic/pi-mono
  package: npm:@mariozechner/pi-coding-agent
platforms:
  darwin: supported
  linux: supported
  windows-native: supported
  windows-wsl: supported
runtime:
  kind: node
  constraintSource:
    command: npm view @mariozechner/pi-coding-agent@latest engines --json
install:
  kind: npm-global
  package: '@mariozechner/pi-coding-agent'
verify:
  - pi --version
  - pi --help
uninstall:
  kind: npm-global
  package: '@mariozechner/pi-coding-agent'
```

OpenClaw 可复用 npm provider，但增加 onboarding/daemon 生命周期。Hermes 需要 `python-tool` 或 `official-script` provider，并且在官方元数据复核前将 Windows native 标为 `unsupported/experimental`。

### 4.2 不要只检查命令是否存在

`node`、`npm`、`git`、`pi` 等命令存在仍可能版本不满足、来自错误平台或被旧 PATH 遮蔽。检测结果至少包含：

- 命令绝对路径；
- 版本；
- 架构（x64/arm64）；
- OS/执行环境（Windows native 或具体 WSL distro）；
- 是否满足包声明的 SemVer/Python specifier；
- 安装来源和可否安全升级。

### 4.3 动态依赖约束

- npm Agent：用 registry 元数据中的 `engines`、`os`、`cpu`、`bin`、repository 和 integrity。
- Python Agent：只解析仓库/包中的 `pyproject.toml` 和 wheel metadata；解析阶段不执行 setup 脚本。
- 官方 shell script：下载后显示来源、hash 和将要运行的命令；脚本版本/commit 要写入安装记录。
- 网络不可用时只能使用经过签名/校验的缓存 manifest，不能静默猜版本。

### 4.4 Windows/WSL 边界

用户在 PowerShell 启动安装器时选择 WSL，不代表后续命令仍在 Windows 执行。安装器要生成明确的 target context：

```text
host: windows
target: wsl
distro: Ubuntu-24.04
arch: x86_64
home: /home/<user>
```

依赖检测、下载、安装、PATH 修改和验证全部在这个 context 内完成。不要把 Windows npm global 包误判为 WSL 已安装，反之亦然。

### 4.5 卸载与回滚

每次安装写入 receipt，例如：

```json
{
  "agent": "pi",
  "target": "windows-native",
  "method": "npm-global",
  "package": "@mariozechner/pi-coding-agent",
  "version": "<resolved-version>",
  "integrity": "<registry-integrity>",
  "runtimeInstalledByUs": false,
  "pathsCreated": [],
  "userDataRemoved": false
}
```

只有 `runtimeInstalledByUs: true` 且没有其他已安装 Agent 依赖该 runtime 时，才询问是否卸载 Node/Python/git。默认永远不删除用户工作区、API key、聊天历史、配置和 skills。

## 5. 在线复核清单

在真正实现这三个 manifest 前，按以下顺序执行一次联网复核并把结果固定到测试 fixture：

1. 下载三个官方 README，记录 URL、commit SHA 和获取日期。
2. 查询两个 npm 包的 latest、`engines`、`bin`、repository、integrity、os/cpu。
3. clone Hermes 仓库，只解析 `pyproject.toml`、README 和 installer，不执行代码。
4. 在 macOS arm64、Linux x64、Windows x64 原生、Windows + WSL2 四个环境运行 dry-run。
5. 分别测试 clean install、已满足依赖、依赖版本过旧、PATH 冲突、无管理员权限、断网恢复、卸载保留数据。
6. 对真实付费模型调用保持 opt-in；基础验证必须完全离线且无费用。
