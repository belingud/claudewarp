# GitHub Actions 自动化构建指南

本文档介绍如何使用 GitHub Actions 自动化构建 ClaudeWarp 的 Windows 安装程序。

## 📋 概述

现在项目包含两个主要的 GitHub Actions 工作流：

1. **`build.yml`** - 主构建工作流（所有平台）
2. **`windows-installer.yml`** - 专门的 Windows 安装程序构建工作流

## 🚀 工作流功能

### 1. 主构建工作流 (`build.yml`)

**触发条件：**
- 推送标签（如 `v0.1.8`）
- 手动触发

**构建内容：**
- macOS 版本（Intel + Apple Silicon）
- Windows 版本（单文件 + 多文件 + 安装程序）
- Linux 版本（AppImage + ZIP）

**新增功能：**
- ✅ 自动安装 Inno Setup
- ✅ 自动构建 Windows 安装程序
- ✅ 自动打包所有版本
- ✅ 自动发布到 GitHub Releases

### 2. Windows 安装程序工作流 (`windows-installer.yml`)

**触发条件：**
- 推送标签（如 `v0.1.8`）
- 手动触发（可指定版本号）

**专门功能：**
- 🎯 专注于 Windows 安装程序构建
- 🧪 包含安装程序测试步骤
- 📦 生成完整的 Windows 发布包
- 🔍 详细的构建验证和报告

## 📂 输出文件

### 自动生成的发布文件

每次成功构建后，会在 GitHub Releases 中生成以下文件：

```
# macOS
ClaudeWarp-0.1.8-macos-x64.zip
ClaudeWarp-0.1.8-macos-x64.dmg
ClaudeWarp-0.1.8-macos-arm64.zip
ClaudeWarp-0.1.8-macos-arm64.dmg

# Windows
ClaudeWarp-0.1.8-windows-x64-installer.exe    # 🆕 安装程序
ClaudeWarp-0.1.8-windows-x64-onefile.zip      # 单文件版本
ClaudeWarp-0.1.8-windows-x64-multifile.zip    # 多文件版本

# Linux
ClaudeWarp-0.1.8-linux-x64.zip
ClaudeWarp-0.1.8-linux-x64.AppImage
```

## 🔄 使用方法

### 方法 1: 标签发布（推荐）

```bash
# 1. 更新版本号（在 pyproject.toml 和 installer.iss 中）
# 2. 提交更改
git add .
git commit -m "bump: version 0.1.8"

# 3. 创建并推送标签
git tag v0.1.8
git push origin v0.1.8

# 4. GitHub Actions 会自动触发构建和发布
```

### 方法 2: 手动触发

1. 进入 GitHub 仓库的 **Actions** 标签页
2. 选择 **"Build and Release"** 或 **"Windows Installer Build"**
3. 点击 **"Run workflow"**
4. 选择分支并启动

### 方法 3: 仅 Windows 安装程序

```bash
# 手动触发 Windows 专用工作流
# 在 GitHub Actions 页面选择 "Windows Installer Build"
# 输入版本号（可选）并运行
```

## ⚙️ 配置说明

### 环境变量

```yaml
env:
  PROJECT_NAME: ClaudeWarp
  PYTHON_VERSION: "3.11"
```

### 权限设置

工作流需要以下权限：
```yaml
permissions:
  contents: write  # 用于创建和上传 releases
```

### 密钥配置

确保仓库中配置了以下 secrets：
- `GITHUB_TOKEN` - 自动提供，用于发布 releases

## 🛠️ 自定义配置

### 修改版本号

更新以下文件中的版本号：
1. `pyproject.toml` - Python 包版本
2. `scripts/installer.iss` - 安装程序版本

### 修改构建选项

编辑 `.github/workflows/build.yml` 或 `windows-installer.yml`：

```yaml
# 添加新的构建平台
strategy:
  matrix:
    include:
      - os: windows-latest
        platform: windows
        arch: x64
      # 添加新配置...
```

### 自定义发布说明

编辑 `.github/templates/github/release_notes.md` 模板文件。

## 🔍 监控构建状态

### 查看构建日志

1. 进入 GitHub 仓库的 **Actions** 标签页
2. 点击最新的工作流运行
3. 查看各个步骤的详细日志

### 构建状态指示器

在 README.md 中添加状态徽章：

```markdown
[![Build Status](https://github.com/belingud/claudewarp/workflows/Build%20and%20Release/badge.svg)](https://github.com/belingud/claudewarp/actions)
```

## 🧪 测试和验证

### 自动测试

工作流包含以下验证步骤：
- ✅ 构建文件存在性检查
- ✅ 文件大小验证
- ✅ 安装程序响应性测试
- ✅ 包完整性验证

### 手动测试

下载构建的文件进行测试：
```bash
# 下载并测试单文件版本
curl -L -o claudewarp.exe "https://github.com/belingud/claudewarp/releases/latest/download/ClaudeWarp-*-onefile.zip"

# 下载并测试安装程序
curl -L -o installer.exe "https://github.com/belingud/claudewarp/releases/latest/download/ClaudeWarp-*-installer.exe"
```

## 🐛 故障排除

### 常见问题

1. **Inno Setup 安装失败**
   ```yaml
   # 解决方案：检查下载 URL 和安装参数
   - name: Install Inno Setup
     run: |
       # 添加重试逻辑和错误检查
   ```

2. **构建超时**
   ```yaml
   # 解决方案：增加超时时间
   jobs:
     build:
       timeout-minutes: 60  # 增加到 60 分钟
   ```

3. **文件上传失败**
   ```yaml
   # 解决方案：检查文件路径和权限
   - name: Upload artifacts
     uses: actions/upload-artifact@v4
     with:
       if-no-files-found: warn  # 添加此选项
   ```

### 调试技巧

1. **启用调试模式**
   ```yaml
   env:
     ACTIONS_STEP_DEBUG: true
   ```

2. **添加调试输出**
   ```yaml
   - name: Debug
     run: |
       echo "Current directory: $(pwd)"
       ls -la
       echo "Environment variables:"
       env | sort
   ```

3. **检查特定步骤**
   ```yaml
   - name: Check build results
     run: |
       if [ ! -f "build/main.exe" ]; then
         echo "❌ Build failed"
         exit 1
       fi
   ```

## 📈 高级功能

### 并行构建

工作流支持并行构建多个平台：
```yaml
strategy:
  matrix:
    include:
      - os: windows-latest
      - os: macos-latest
      - os: ubuntu-latest
  max-parallel: 3  # 最多同时运行 3 个任务
```

### 缓存优化

```yaml
- name: Cache Python dependencies
  uses: actions/cache@v3
  with:
    path: ~/.cache/uv
    key: ${{ runner.os }}-python-${{ hashFiles('**/pyproject.toml') }}
```

### 条件执行

```yaml
- name: Create installer
  if: matrix.platform == 'windows'
  run: |
    # 只在 Windows 平台执行
```

## 📋 检查清单

发布前确认：

- [ ] 版本号已更新（`pyproject.toml` 和 `installer.iss`）
- [ ] 更改日志已更新
- [ ] 所有测试通过
- [ ] GitHub Actions 工作流配置正确
- [ ] 必要的 secrets 已配置
- [ ] 发布说明模板准确

## 🚀 最佳实践

1. **版本管理**
   - 使用语义化版本号（如 v1.2.3）
   - 标签名与版本号保持一致

2. **构建优化**
   - 使用缓存加速构建
   - 并行执行独立的任务

3. **错误处理**
   - 添加适当的错误检查
   - 提供清晰的错误消息

4. **文档维护**
   - 保持 README 和文档同步
   - 更新发布说明模板

---

🎉 现在你的 ClaudeWarp 项目已经具备了完全自动化的 CI/CD 流程！每次推送标签都会自动构建并发布所有平台的版本，包括专业的 Windows 安装程序。