# ClaudeWarp 打包构建指南

本文档介绍如何为 ClaudeWarp 项目创建跨平台安装包。该项目使用 Nuitka 进行打包构建。

## 支持平台

- ✅ **macOS** (Intel & Apple Silicon)
- ✅ **Windows** (x64)
- ✅ **Linux** (x64)

## 快速开始

### 前置要求

1. **Python 3.8+** (推荐 3.11)
2. **Git**
3. **uv** (Python 包管理器)
4. **Nuitka** (通过 uv 自动安装)
5. **PySide6** (GUI 框架依赖)

### 本地构建

```bash
# 克隆项目
git clone https://github.com/your-username/claudewarp.git
cd claudewarp

# 同步依赖
uv sync --all-groups --all-extras

# 根据平台选择构建命令
# macOS
./scripts/nuitka_mac.sh

# Linux
./scripts/nuitka_linux.sh

# Windows (PowerShell)
.\scripts\nuitka.ps1

# 或使用简化的 just 命令 (仅适用于 macOS)
just nuitka

# 输出文件在 build/ 目录中
```

## 详细构建指南

### 1. 环境准备

```bash
# 安装 uv (如果尚未安装)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 同步项目依赖
uv sync --all-groups --all-extras
```

### 2. 构建选项

#### 使用平台特定脚本 (推荐)

```bash
# macOS 构建
./scripts/nuitka_mac.sh

# Linux 构建
./scripts/nuitka_linux.sh

# Windows 构建 (PowerShell)
.\scripts\nuitka.ps1
```

#### 使用 Just 命令 (仅限 macOS)

```bash
# 简化的 macOS 构建命令
just nuitka
```

**注意**: `just nuitka` 命令仅包含基础的 macOS 参数，不包含完整的优化配置。推荐使用平台特定脚本获得最佳构建效果。

#### 手动构建

```bash
# 基础 Nuitka 命令
uv run nuitka \
    --standalone \
    --onefile \
    --enable-plugin=pyside6 \
    --output-dir=build \
    --assume-yes-for-download \
    --include-data-dir=claudewarp/gui/resources=claudewarp/gui/resources \
    main.py
```

### 3. 输出文件

构建完成后，会生成：

#### macOS
- `main.app` - 应用程序包 (在 build/ 文件夹中)
- 自动配置的 Info.plist 和图标

#### Windows
- `main.exe` - 可执行文件 (在 build/ 文件夹中)
- 集成图标和无控制台窗口

#### Linux
- `main.bin` - 可执行二进制文件 (在 build/ 文件夹中)

### 4. 代码格式化

```bash
# 格式化代码
just format
```

## Nuitka 配置说明

### 主要参数

- `--standalone`: 创建独立的分发包
- `--onefile`: 创建单文件可执行程序
- `--enable-plugin=pyside6`: 启用 PySide6 插件支持
- `--output-dir=build`: 指定输出目录
- `--assume-yes-for-download`: 自动下载依赖

### 平台特定参数

#### macOS
- `--macos-create-app-bundle`: 创建 .app 包
- `--macos-app-name=ClaudeWarp`: 设置应用名称
- `--macos-app-icon=claudewarp/gui/resources/icons/claudewarp.icns`: 设置应用图标

#### Windows
- `--windows-disable-console`: 禁用控制台窗口
- `--windows-icon-from-ico=claudewarp/gui/resources/icons/claudewarp.ico`: 设置应用图标

### 排除模块优化

项目配置了大量 `--nofollow-import-to` 参数来排除不必要的模块，包括：

- **Qt 组件**: QtOpenGL, QtMultimedia, QtWebEngineWidgets 等
- **开发工具**: pytest, pre_commit, pyright 等
- **CLI 相关**: [`claudewarp.cli`](claudewarp/cli) (仅构建 GUI 部分)
- **系统模块**: bdb, pdb, trace 等调试模块

### 包含模块和资源

- `--include-module=typing_inspection`: 包含类型检查支持
- `--include-data-dir=claudewarp/gui/resources=claudewarp/gui/resources`: 包含 GUI 资源文件

## 自动化构建

### GitHub Actions

项目配置了自动化构建，会在以下情况触发：

1. **标签推送**: `git tag v1.0.0 && git push origin v1.0.0`
2. **主分支提交**: 推送到 `main` 或 `develop` 分支
3. **手动触发**: 在 GitHub Actions 页面手动运行

### 发布流程

```bash
# 1. 更新版本号
# 编辑 [`pyproject.toml`](pyproject.toml) 中的 version

# 2. 创建并推送标签
git tag v1.0.0
git push origin v1.0.0

# 3. GitHub Actions 自动构建并创建 Release
```

## 平台特定配置

### macOS

#### 应用包后处理
macOS 构建脚本包含后处理步骤：
- 自动创建 Resources 目录
- 生成自定义 Info.plist 文件
- 复制应用图标到正确位置

#### 代码签名（可选）
```bash
# 安装开发者证书后
codesign --force --verify --verbose --sign "Developer ID Application: Your Name" build/main.app
```

#### 公证（App Store 外分发）
```bash
# 需要 Apple Developer 账户
xcrun notarytool submit build/main.app.zip --keychain-profile "notarytool-profile" --wait
```

### Windows

#### 特殊配置
- 自动禁用控制台窗口
- 集成应用图标
- 单文件可执行程序

#### 代码签名（可选）
需要代码签名证书，使用工具如 SignTool。

### Linux

#### 基础配置
- 单文件二进制输出
- 无特殊平台配置

#### AppImage 创建（可选）
```bash
# 安装 linuxdeploy
wget https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage
chmod +x linuxdeploy-x86_64.AppImage

# 创建 AppImage
./linuxdeploy-x86_64.AppImage --appdir build/main.dist --output appimage
```

## 故障排除

### 常见问题

#### 1. Nuitka 编译错误
```bash
# 解决方案：确保所有依赖已安装
uv sync --all-groups --all-extras

# 检查 Nuitka 版本
uv run nuitka --version
```

#### 2. PySide6 插件问题
```bash
# 解决方案：确保 PySide6 正确安装
uv add pyside6

# 验证插件可用性
uv run nuitka --plugin-list | grep pyside6
```

#### 3. 资源文件缺失
```bash
# 解决方案：检查资源目录路径
ls -la claudewarp/gui/resources/

# 确保 --include-data-dir 参数正确
```

#### 4. macOS 权限问题
```bash
# 首次运行需要允许
sudo spctl --master-disable  # 临时禁用 Gatekeeper
# 或在 系统偏好设置 > 安全性与隐私 中允许
```

#### 5. Windows 杀毒软件误报
- 构建后的 exe 可能被误报为病毒
- 解决方案：代码签名或添加到白名单

### 调试构建

#### 启用详细输出
```bash
# 添加调试参数
uv run nuitka --verbose --show-progress --show-scons ...
```

#### 生成构建报告
```bash
# 自动生成 report.html
# 报告文件会在项目根目录中生成
```

## 性能优化

### 减小包大小

1. **排除不必要的模块**: 使用 `--nofollow-import-to=模块名`
2. **优化资源文件**: 压缩图片和其他资源
3. **排除开发依赖**: 确保 CLI 和测试相关模块被排除

### 提升启动速度

1. **避免重复导入**
2. **延迟导入非核心模块**
3. **优化初始化代码**
4. **使用 Nuitka 的优化选项**

### Nuitka 特有优化

- **静态编译**: Nuitka 编译为机器码，比 PyInstaller 更快
- **内存优化**: 更低的内存占用
- **启动优化**: 更快的应用启动时间

## 发布检查清单

- [ ] 更新版本号 ([`pyproject.toml`](pyproject.toml))
- [ ] 运行本地测试 (`pytest`)
- [ ] 本地构建测试 (`just nuitka`)
- [ ] 检查生成的应用是否正常运行
- [ ] 验证 GUI 界面和功能
- [ ] 测试资源文件加载
- [ ] 更新 CHANGELOG.md
- [ ] 创建 Git 标签
- [ ] 推送到 GitHub
- [ ] 验证 GitHub Actions 构建
- [ ] 测试下载的发布包
- [ ] 更新文档（如需要）

## 进阶配置

### 自定义构建脚本

可以修改构建脚本来：
- [`scripts/nuitka_mac.sh`](scripts/nuitka_mac.sh) - macOS 特定配置
- [`scripts/nuitka_linux.sh`](scripts/nuitka_linux.sh) - Linux 特定配置  
- [`scripts/nuitka.ps1`](scripts/nuitka.ps1) - Windows 特定配置

### CI/CD 扩展

在 `.github/workflows/build.yml` 中可以：
- 添加更多测试平台
- 集成代码质量检查
- 配置自动部署
- 添加构建缓存

## Nuitka vs PyInstaller

### Nuitka 优势

1. **性能**: 编译为机器码，运行更快
2. **启动速度**: 比 PyInstaller 快 2-3 倍
3. **内存占用**: 更低的内存使用
4. **兼容性**: 更好的 Python 特性支持
5. **调试**: 更好的错误报告

### 注意事项

1. **编译时间**: 比 PyInstaller 更长
2. **依赖管理**: 需要更精确的模块配置
3. **平台差异**: 不同平台需要不同的配置参数

## 支持与反馈

如果在构建过程中遇到问题：

1. 查看本文档的故障排除部分
2. 检查 [`report.html`](report.html) 构建报告
3. 检查 GitHub Issues
4. 创建新的 Issue 并提供：
   - 操作系统和版本
   - Python 版本
   - Nuitka 版本
   - 完整的错误信息
   - 构建日志

## 相关文档

- [Nuitka 官方文档](https://nuitka.net/doc/user-manual.html)
- [PySide6 文档](https://doc.qt.io/qtforpython/)
- [项目 README](README.md)