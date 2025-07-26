# Claude 中转站管理工具设计文档

## 📌 项目简介

本项目（claudewarp）是一个基于 Python 实现的工具，用于管理和切换多个 Claude 中转站（Proxy）。它支持终端命令行（CLI）操作，也提供图形用户界面（GUI）以增强用户体验。该工具通过配置文件管理多个中转站的 base URL 与 API key，便于开发者在不同网络环境或供应商之间快速切换。

---

## 🎯 核心目标

- 支持添加、删除、切换中转站配置
- 支持导出当前中转站的环境变量（用于 shell 脚本或模型调用）
- 支持 CLI + GUI 共用一套逻辑（核心逻辑独立）
- 提供跨平台的桌面 GUI（基于 pyside6）
- 使用标准配置文件格式（如 TOML）进行持久化存储

---

## 📂 项目结构

```
claudewarp/
├── claudewarp/              # 主应用包
│   ├── core/               # 核心业务逻辑
│   │   ├── config.py       # 配置文件读写
│   │   ├── manager.py      # 中转站管理逻辑
│   │   ├── models.py       # 数据模型
│   │   ├── exceptions.py   # 异常定义
│   │   └── utils.py        # 工具函数
│   ├── cli/                # 命令行界面
│   │   ├── commands.py     # CLI 命令处理
│   │   ├── formatters.py   # 输出格式化
│   │   └── main.py         # CLI 入口
│   └── gui/                # GUI 图形界面（pyside6）
│       ├── app.py          # GUI 应用
│       ├── main_window.py  # 主窗口
│       ├── dialogs.py      # 对话框
│       └── resources/      # 资源文件
│           └── icons/      # 应用图标
├── tests/                  # 单元测试
├── scripts/                # 构建脚本
├── .github/                # GitHub Actions
│   └── workflows/          # CI/CD 流程
├── main.py                 # 启动入口
├── pyproject.toml          # 项目配置
├── Justfile               # 构建命令
├── BUILD.md               # 构建说明
└── README.md              # 项目文档
```

---

## 🧱 数据模型设计（`models.py`）

```python
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime

class ProxyServer(BaseModel):
    """代理服务器配置模型"""
    name: str = Field(..., min_length=1, max_length=50)
    base_url: str = Field(...)
    api_key: str = Field(..., min_length=3)
    description: str = Field(default="", max_length=200)
    tags: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    is_active: bool = Field(default=True)

class ProxyConfig(BaseModel):
    """代理配置文件模型"""
    version: str = Field(default="1.0")
    current_proxy: Optional[str] = Field(default=None)
    proxies: Dict[str, ProxyServer] = Field(default_factory=dict)
    settings: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class ExportFormat(BaseModel):
    """环境变量导出格式配置"""
    shell_type: str = Field(default="bash")
    include_comments: bool = Field(default=True)
    prefix: str = Field(default="ANTHROPIC_")
    export_all: bool = Field(default=False)
```

---

## 🛠 核心逻辑（`manager.py`）

### 主要类和方法：

**ProxyManager 类**：
- `__init__()` - 初始化管理器，加载配置
- `load_config() -> ProxyConfig` - 从文件加载配置
- `save_config()` - 保存配置到文件
- `add_proxy(proxy: ProxyServer)` - 添加新代理
- `remove_proxy(name: str) -> bool` - 删除代理
- `set_current_proxy(name: str) -> bool` - 设置当前代理
- `get_current_proxy() -> Optional[ProxyServer]` - 获取当前代理
- `list_proxies() -> Dict[str, ProxyServer]` - 列出所有代理
- `get_active_proxies() -> Dict[str, ProxyServer]` - 获取启用的代理
- `export_env_vars(format: ExportFormat) -> str` - 导出环境变量
- `backup_config()` - 备份配置文件
- `validate_proxy_connection(name: str) -> bool` - 验证代理连接

---

## ⚙ 配置文件结构（TOML 格式）

文件路径：`~/.claudewarp/config.toml`

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

---

## 🧑‍💻 CLI 功能设计（Typer）

| 命令 | 说明 | 示例 |
|------|------|------|
| `cw add` | 添加新的代理服务器 | `cw add --name proxy-hk --url https://hk.api.com/ --key sk-xxx` |
| `cw list` | 列出所有代理服务器 | `cw list` |
| `cw use <name>` | 切换到指定代理 | `cw use proxy-cn` |
| `cw current` | 显示当前活跃代理 | `cw current` |
| `cw remove <name>` | 删除指定代理 | `cw remove proxy-old` |
| `cw export` | 导出环境变量 | `cw export --shell bash` |
| `cw test <name>` | 测试代理连通性 | `cw test proxy-cn` |

### CLI 特性：
- 基于 Typer 框架，支持丰富的命令行选项
- 使用 Rich 库提供美观的输出格式
- 支持多种 Shell 格式的环境变量导出（bash, fish, powershell, zsh）
- 集成详细的帮助信息和错误处理
- 支持 JSON、YAML 等多种输出格式

---

## 🪟 GUI 功能设计（基于 PySide6）

### 主窗口功能：
- **当前代理展示**: 状态栏显示当前活跃代理的名称和状态
- **代理列表管理**: 表格显示所有代理，支持排序和筛选
- **快速操作**: 添加、删除、编辑、切换代理的按钮
- **环境变量导出**: 导出对话框，支持多种 Shell 格式
- **设置面板**: 应用程序设置和偏好配置

### 对话框设计：
- **添加/编辑代理对话框**: 表单输入代理信息，实时验证
- **确认删除对话框**: 安全删除确认
- **导出环境变量对话框**: 选择 Shell 类型和导出选项
- **设置对话框**: 应用程序偏好设置

### GUI 特性：
- 现代化界面设计，响应式布局
- 支持系统主题（深色/浅色模式）
- 键盘快捷键支持
- 拖拽排序代理优先级
- 实时状态更新和通知
- 多语言界面支持（中文/英文）

---

## 🧪 测试策略

### 单元测试 (Unit Tests)
- **核心模型测试**: 验证 Pydantic 模型的数据验证逻辑
- **管理器测试**: ProxyManager 的所有方法测试
- **配置文件测试**: 配置读写、备份恢复功能
- **工具函数测试**: 各种辅助函数的边界情况

### 集成测试 (Integration Tests)
- **CLI 命令测试**: 所有 CLI 命令的端到端测试
- **GUI 组件测试**: 使用 pytest-qt 测试 GUI 交互
- **配置持久化测试**: 跨会话的配置保存和恢复
- **环境变量导出测试**: 多种 Shell 格式的导出验证

### 测试覆盖范围
- 代码覆盖率目标：≥80%
- 关键路径覆盖率：≥95%
- 错误处理路径测试
- 边界条件和异常情况测试

### 测试工具
- **pytest**: 主要测试框架
- **pytest-qt**: GUI 测试支持
- **pytest-cov**: 覆盖率报告
- **pytest-mock**: Mock 对象支持

---

## 📦 安装与运行方式（Python 环境）

```bash
uv sync

# CLI
python cli/main.py list
python cli/main.py use <proxy-name>

# GUI
python gui/app.py
```

---

## 📚 依赖建议

```text
typer
pydantic
toml
pyside6 ; for gui
```

---

## ✅ 最小可运行版本 (MVP) 功能建议

- CLI 支持添加、删除、切换、导出
- GUI 支持列表展示与切换操作
- 所有功能依赖 `core/` 封装，易维护与扩展

---

## 👨‍💻 开发建议

- 使用uv来管理依赖
- 初期专注 CLI 逻辑正确性，再绑定 GUI
- 持续集成（CI）可添加 Pytest 验证 CLI 行为
