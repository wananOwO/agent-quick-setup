# Agent 快速部署器实施计划

## 目标

构建一个支持 Windows、macOS、Linux 的 CLI 工具：交互式选择主流 Agent（Claude Code、Codex、OpenCode、OpenClaw、Hermes、Pi 等），检测操作系统与依赖，必要时引导安装依赖（Windows 可选择原生 PowerShell 或 WSL），最后安装所选 Agent。

## 阶段

- [completed] 阶段 1：调研各 Agent 官方安装方式、平台支持与依赖
- [completed] 阶段 2：确定架构、命令行交互与安全策略，形成开发设计
- [completed] 阶段 3：实现跨平台 CLI、检测器、依赖安装器和 Agent 适配器
- [completed] 阶段 4：编写测试、文档与示例，执行验证（静态检查完成；运行时测试因当前环境没有 Python 解释器而无法执行）
- [completed] Phase 5: Fix the silent Windows bootstrap failure, add remote one-line installers, publish the repository, and verify both download paths.

## 全局约束

- 优先使用官方安装渠道与文档；对网络安装命令展示并请求用户确认。
- 不执行静默的高风险系统修改；依赖安装前明确列出将执行的命令。
- Windows 支持原生 PowerShell，并提供 WSL 选项；macOS/Linux 使用 shell 包管理器或官方脚本。
- 适配器配置应可扩展，新增 Agent 无需修改核心流程。

## 错误记录

| 错误 | 尝试 | 解决 |
|---|---|---|
| `python` 指向 Microsoft Store alias，无法启动解释器 | `python -m unittest discover -s tests -v` | 已记录为环境限制；提供 `install.ps1`/`install.sh` 的 Python 检测提示，用户安装 Python 3.9+ 后可运行测试 |
