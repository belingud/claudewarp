# ClaudeWarp

<p align="center">
  <img src="claudewarp/gui/resources/icons/claudewarp.ico" alt="ClaudeWarp Logo" width="128" height="128">
</p>

<p align="center">
  <strong>Claude 中转站管理工具</strong>
</p>

<p align="center">
  一个优雅的 Claude API 代理服务器管理工具，支持 CLI 和 GUI 双模式操作
</p>

<p align="center">
  <a href="https://github.com/belingud/claudewarp/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License">
  </a>
  <a href="https://github.com/belingud/claudewarp/releases">
    <img src="https://img.shields.io/github/v/release/belingud/claudewarp?include_prereleases" alt="Release">
  </a>
  <a href="https://python.org">
    <img src="https://img.shields.io/badge/Python-3.8%2B-brightgreen" alt="Python Version">
  </a>
  <a href="https://github.com/belingud/claudewarp/actions">
    <img src="https://img.shields.io/github/workflow/status/belingud/claudewarp/Build%20and%20Release" alt="Build Status">
  </a>
</p>

---

## ✨ 功能特色

🚀 **双模式支持** - 既可命令行操作，也可图形界面管理  
🔧 **智能配置** - 基于 TOML 的配置文件，支持自动验证和备份  
🌐 **多代理管理** - 轻松添加、切换和管理多个 Claude 中转站  
📝 **环境变量导出** - 支持多种 Shell 格式的环境变量导出  
🏷️ **标签系统** - 为代理服务器添加标签，方便分类和筛选  
✅ **数据验证** - 使用 Pydantic 确保配置数据的完整性和正确性  
🎨 **美观界面** - 基于 PySide6 的现代化 GUI 界面  

![screenshot](artwork/screenshot.png)

## 📦 安装方式

### 从发布版本安装（推荐）

访问 [Releases 页面](https://github.com/belingud/claudewarp/releases) 下载适合您系统的版本：

- **macOS Intel**: 下载 `.dmg` 或 `.zip` 文件
- **macOS Apple Silicon**: 下载对应 ARM64 版本
- **Windows**: 下载 `.zip` 压缩包

### 从源码安装

```bash
# 克隆项目
git clone https://github.com/belingud/claudewarp.git
cd claudewarp

# 使用 pip 安装
pip install -e .
```

## 🚀 快速开始

### GUI 模式

直接双击应用程序图标，或在终端运行：

```bash
# 从源码运行
python main.py

# 或使用构建的应用
./ClaudeWarp.app  # macOS
claudewarp.exe    # Windows
```

### CLI 模式

```bash
# 查看所有命令
cw --help

# 添加代理服务器
cw add --name proxy-cn --url https://api.claude-proxy.com/ --key sk-your-api-key
# 或使用交互式
cw add

# 查看所有代理
cw list

# 切换到指定代理
cw use proxy-cn

# 查看当前代理
cw current

# 导出环境变量
cw export
```

## 📖 详细使用说明

### CLI 命令参考

| 命令               | 说明               | 示例                                                            |
| ------------------ | ------------------ | --------------------------------------------------------------- |
| `cw add`           | 添加新的代理服务器 | `cw add --name proxy-hk --url https://hk.api.com/ --key sk-xxx` |
| `cw list`          | 列出所有代理服务器 | `cw list`                                                       |
| `cw use <name>`    | 切换到指定代理     | `cw use proxy-cn`                                               |
| `cw current`       | 显示当前活跃代理   | `cw current`                                                    |
| `cw remove <name>` | 删除指定代理       | `cw remove proxy-old`                                           |
| `cw export`        | 导出环境变量       | `cw export --shell bash`                                        |
| `cw test <name>`   | 测试代理连通性     | `cw test proxy-cn`                                              |

### 配置文件

配置文件位于：`~/.config/claudewarp/config.toml`

```toml
version = "1.0"
current_proxy = "proxy-cn"

[proxies.proxy-cn]
name = "proxy-cn"
base_url = "https://api.claude-proxy.com/"
api_key = "sk-1234567890abcdef"
description = "国内主力节点"
tags = ["china", "primary"]
is_active = true
created_at = "2024-01-15T10:30:00"
updated_at = "2024-01-15T10:30:00"

[proxies.proxy-hk]
name = "proxy-hk"
base_url = "https://hk.claude-proxy.com/"
api_key = "sk-abcdef1234567890"
description = "香港备用节点"
tags = ["hongkong", "backup"]
is_active = true
created_at = "2024-01-15T11:00:00"
updated_at = "2024-01-15T11:00:00"

[settings]
auto_backup = true
backup_count = 5
log_level = "INFO"
```

### 环境变量导出

支持多种 Shell 格式：

```bash
# Bash/Zsh
cw export --shell bash
# 输出：
# export ANTHROPIC_API_KEY="sk-your-api-key"
# export ANTHROPIC_BASE_URL="https://api.claude-proxy.com/"

# PowerShell
cw export --shell powershell
# 输出：
# $env:ANTHROPIC_API_KEY="sk-your-api-key"
# $env:ANTHROPIC_BASE_URL="https://api.claude-proxy.com/"

# Fish Shell
cw export --shell fish
# 输出：
# set -x ANTHROPIC_API_KEY "sk-your-api-key"
# set -x ANTHROPIC_BASE_URL "https://api.claude-proxy.com/"
```

## 🏗️ 开发指南

### 项目结构

```
claudewarp/
├── claudewarp/              # 主应用包
│   ├── core/               # 核心业务逻辑
│   │   ├── config.py       # 配置管理
│   │   ├── manager.py      # 代理管理器
│   │   ├── models.py       # 数据模型
│   │   ├── exceptions.py   # 异常定义
│   │   └── utils.py        # 工具函数
│   ├── cli/                # 命令行界面
│   │   ├── commands.py     # CLI 命令
│   │   ├── formatters.py   # 输出格式化
│   │   └── main.py         # CLI 入口
│   └── gui/                # 图形界面
│       ├── app.py          # GUI 应用
│       ├── main_window.py  # 主窗口
│       ├── dialogs.py      # 对话框
│       └── resources/      # 资源文件
├── tests/                  # 测试文件
├── scripts/                # 构建脚本
├── main.py                 # 应用入口
├── pyproject.toml          # 项目配置
├── Justfile               # 构建命令
└── BUILD.md               # 构建说明
```

### 开发环境设置

```bash
# 克隆代码
git clone https://github.com/belingud/claudewarp.git
cd claudewarp

# 安装 uv（Python 包管理器）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 同步所有依赖
uv sync --all-groups --all-extras

# 运行测试
uv run pytest

# 代码格式化
just format

# 本地构建
just pyinstaller
```

### 构建发布版本

```bash
# 本地构建
just pyinstaller

# 查看构建帮助
cat BUILD.md
```

详细构建说明请参考 [BUILD.md](BUILD.md)。

## 🧪 测试

```bash
# 运行所有测试
uv run pytest

# 运行特定测试
uv run pytest tests/test_manager.py

# 生成覆盖率报告
uv run pytest --cov=claudewarp --cov-report=html
```

## 🤝 贡献指南

我们欢迎所有形式的贡献！请查看以下步骤：

1. **Fork** 本仓库
2. 创建您的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启一个 **Pull Request**

### 开发规范

- 使用 [Ruff](https://ruff.rs/) 进行代码格式化
- 为新功能添加测试
- 更新相关文档

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [Typer](https://typer.tiangolo.com/) - 出色的 CLI 框架
- [PySide6](https://wiki.qt.io/Qt_for_Python) - 强大的 GUI 框架
- [Pydantic](https://pydantic-docs.helpmanual.io/) - 数据验证库
- [Rich](https://rich.readthedocs.io/) - 美观的终端输出

## 🔗 相关链接

- [问题反馈](https://github.com/belingud/claudewarp/issues)
- [变更日志](https://github.com/belingud/claudewarp/releases)
- [讨论区](https://github.com/belingud/claudewarp/discussions)

---

<p align="center">
  Made with ❤️ by ClaudeWarp Team
</p>