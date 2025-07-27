# Development Guidelines

This document contains critical information about working with this codebase. Follow these guidelines precisely.

## Core Development Rules

1. Package Management
   - ONLY use uv, NEVER pip
   - Installation: `uv add package`
   - Running tools: `uv run tool`
   - Upgrading: `uv add --dev package --upgrade-package package`
   - FORBIDDEN: `uv pip install`, `@latest` syntax

2. Code Quality
   - Type hints required for all code
   - Public APIs must have docstrings
   - Functions must be focused and small
   - Follow existing patterns exactly
   - Line length: 88 chars maximum

3. Testing Requirements
   - Framework: `uv run pytest`
   - Async testing: use anyio, not asyncio
   - Coverage: test edge cases and errors
   - New features require tests
   - Bug fixes require regression tests

4. Code Style
    - PEP 8 naming (snake_case for functions/variables)
    - Class names in PascalCase
    - Constants in UPPER_SNAKE_CASE
    - Document with docstrings
    - Use f-strings for formatting

- For commits fixing bugs or adding features based on user reports add:
  ```bash
  git commit --trailer "Reported-by:<name>"
  ```
  Where `<name>` is the name of the user.

- For commits related to a Github issue, add
  ```bash
  git commit --trailer "Github-Issue:#<number>"
  ```
- NEVER ever mention a `co-authored-by` or similar aspects. In particular, never
  mention the tool used to create the commit message or PR.

## Development Philosophy

- **Simplicity**: Write simple, straightforward code
- **Readability**: Make code easy to understand
- **Performance**: Consider performance without sacrificing readability
- **Maintainability**: Write code that's easy to update
- **Testability**: Ensure code is testable
- **Reusability**: Create reusable components and functions
- **Less Code = Less Debt**: Minimize code footprint

## Coding Best Practices

- **Early Returns**: Use to avoid nested conditions
- **Descriptive Names**: Use clear variable/function names (prefix handlers with "handle")
- **Constants Over Functions**: Use constants where possible
- **DRY Code**: Don't repeat yourself
- **Functional Style**: Prefer functional, immutable approaches when not verbose
- **Minimal Changes**: Only modify code related to the task at hand
- **Function Ordering**: Define composing functions before their components
- **TODO Comments**: Mark issues in existing code with "TODO:" prefix
- **Simplicity**: Prioritize simplicity and readability over clever solutions
- **Build Iteratively** Start with minimal functionality and verify it works before adding complexity
- **Run Tests**: Test your code frequently with realistic inputs and validate outputs
- **Build Test Environments**: Create testing environments for components that are difficult to validate directly
- **Functional Code**: Use functional and stateless approaches where they improve clarity
- **Clean logic**: Keep core logic clean and push implementation details to the edges
- **File Organsiation**: Balance file organization with simplicity - use an appropriate number of files for the project scale

## System Architecture

### 架构概述

ClaudeWarp 采用分层架构设计，实现 Claude API 代理服务器的统一管理。系统支持 CLI 和 GUI 双界面，通过模块化设计实现高内聚低耦合。

### 架构层次

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                       │
│  ┌─────────────────┐          ┌─────────────────────────┐   │
│  │   CLI Interface │          │     GUI Interface       │   │
│  │                 │          │                         │   │
│  │ • Typer Commands│          │ • PySide6 Widgets       │   │
│  │ • Rich Output   │          │ • QFluentWidgets Style  │   │
│  │ • Interactive   │          │ • Native Look & Feel    │   │
│  └─────────────────┘          └─────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Business Layer                           │
│  ┌─────────────────────────────────────────────────────────┐│
│  │               ProxyManager                              ││
│  │                                                         ││
│  │ • 代理服务器生命周期管理 (CRUD)                         ││
│  │ • 智能代理切换与状态管理                                ││
│  │ • Claude Code 自动配置集成                              ││
│  │ • 多格式环境变量导出                                    ││
│  │ • 搜索、过滤、标签管理                                  ││
│  │ • 连接验证与健康检查                                    ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Data Layer                              │
│┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐│
││ ConfigManager   │  │  Data Models    │  │   Utilities     ││
││                 │  │                 │  │                 ││
││ • JSON配置持久化│  │ • ProxyServer   │  │ • 文件操作      ││
││ • 自动备份机制  │  │ • ProxyConfig   │  │ • 原子写入      ││
││ • 版本管理      │  │ • ExportFormat  │  │ • 路径管理      ││
││ • 配置验证      │  │ • Pydantic验证  │  │ • 异常处理      ││
│└─────────────────┘  └─────────────────┘  └─────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### 核心特性

#### 1. 双界面支持
- **CLI模式**: 基于 Typer 的命令行工具，支持脚本自动化
- **GUI模式**: 基于 PySide6 + QFluentWidgets 的现代化界面

#### 2. 智能配置管理
- **自动备份**: 配置变更前自动创建备份
- **原子操作**: 确保配置文件操作的原子性和一致性
- **版本控制**: 配置文件版本管理和兼容性检查

#### 3. Claude Code 集成
- **无缝集成**: 自动生成和更新 Claude Code 配置文件
- **智能合并**: 保留用户现有配置，只更新代理相关设置
- **环境变量**: 支持多种 Shell 格式的环境变量导出

#### 4. 数据验证与安全
- **Pydantic模型**: 全面的数据验证和类型安全
- **输入验证**: URL格式、API密钥格式、名称合规性检查
- **错误处理**: 结构化异常体系和详细错误信息

### 技术栈

#### 核心依赖
- **应用框架**: Python 3.8+
- **CLI框架**: Typer (命令行处理)
- **GUI框架**: PySide6 + QFluentWidgets (现代化界面)
- **数据验证**: Pydantic (模型验证)
- **配置管理**: TOML (项目配置)
- **输出美化**: Rich (CLI美化输出)
- **日志系统**: ColorLog (彩色日志)

#### 开发工具
- **构建系统**: Hatchling
- **任务管理**: Just (命令定义)
- **测试框架**: Pytest + pytest-qt
- **代码格式**: Ruff
- **类型检查**: Pyright
- **版本管理**: bump2version
- **CI/CD**: GitHub Actions

### 数据流向

```
用户输入 → 界面层验证 → 业务逻辑处理 → 数据模型验证 → 配置持久化
    ↓
Claude Code配置 ← 环境变量导出 ← 代理状态管理 ← 配置变更通知
```

### 部署架构

#### 开发环境
- **包管理**: uv (快速依赖管理)
- **虚拟环境**: uv自动管理
- **开发服务**: 热重载支持

#### 生产环境
- **打包方式**: Python Wheel + 可执行文件
- **跨平台**: Windows/macOS/Linux支持
- **单文件部署**: Nuitka编译优化

## Core Components

```
claudewarp/
├── claudewarp/              # 主应用包
│   ├── __init__.py         # 包初始化
│   ├── core/               # 核心业务逻辑层
│   │   ├── __init__.py
│   │   ├── config.py       # 配置文件管理器
│   │   ├── manager.py      # 代理服务器管理器
│   │   ├── models.py       # Pydantic数据模型
│   │   ├── exceptions.py   # 自定义异常类
│   │   └── utils.py        # 工具函数库
│   ├── cli/                # 命令行界面层
│   │   ├── __init__.py
│   │   ├── commands.py     # Typer命令处理器
│   │   ├── formatters.py   # Rich输出格式化器
│   │   └── main.py         # CLI应用入口
│   └── gui/                # 图形用户界面层
│       ├── __init__.py
│       ├── app.py          # PySide6 GUI应用
│       ├── main_window.py  # 主窗口实现
│       ├── dialogs.py      # 对话框组件
│       └── resources/      # 资源文件
│           └── icons/      # 应用图标
├── tests/                  # 测试套件
│   ├── __init__.py
│   ├── conftest.py        # pytest配置
│   ├── test_cli.py        # CLI功能测试
│   ├── test_config.py     # 配置管理测试
│   ├── test_integration.py # 集成测试
│   ├── test_manager.py    # 管理器测试
│   └── test_models.py     # 数据模型测试
├── .github/                # CI/CD配置
│   └── workflows/
│       └── build.yml      # GitHub Actions构建流程
├── scripts/               # 构建脚本
├── main.py               # 应用程序入口点
├── pyproject.toml        # 项目配置和依赖
├── Justfile             # 构建命令定义
├── BUILD.md             # 构建说明文档
├── README.md            # 用户指南
└── LICENSE              # MIT许可证
```


## Pull Requests

- Create a detailed message of what changed. Focus on the high level description of
  the problem it tries to solve, and how it is solved. Don't go into the specifics of the
  code unless it adds clarity.

- Always add `ArthurClune` as reviewer.

- NEVER ever mention a `co-authored-by` or similar aspects. In particular, never
  mention the tool used to create the commit message or PR.

## Python Tools

## Code Formatting

1. Ruff
   - Format: `uv run ruff format .`
   - Check: `uv run ruff check .`
   - Fix: `uv run ruff check . --fix`
   - Critical issues:
     - Line length (88 chars)
     - Import sorting (I001)
     - Unused imports
   - Line wrapping:
     - Strings: use parentheses
     - Function calls: multi-line with proper indent
     - Imports: split into multiple lines

2. Type Checking
   - Tool: `uv run pyright`
   - Requirements:
     - Explicit None checks for Optional
     - Type narrowing for strings
     - Version warnings can be ignored if checks pass

## Error Resolution

1. CI Failures
   - Fix order:
     1. Formatting
     2. Type errors
     3. Linting
   - Type errors:
     - Get full line context
     - Check Optional types
     - Add type narrowing
     - Verify function signatures

2. Common Issues
   - Line length:
     - Break strings with parentheses
     - Multi-line function calls
     - Split imports
   - Types:
     - Add None checks
     - Narrow string types
     - Match existing patterns

3. Best Practices
   - Check git status before commits
   - Run formatters before type checks
   - Keep changes minimal
   - Follow existing patterns
   - Document public APIs
   - Test thoroughly