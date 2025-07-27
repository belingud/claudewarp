# ClaudeWarp 打包构建指南

本文档介绍如何为 ClaudeWarp 项目创建跨平台安装包。该项目使用 PyInstaller 进行打包构建。

## 支持平台

- ✅ **macOS** (Intel & Apple Silicon)
- ✅ **Windows** (x64)
- 🔄 **Linux** (可选配置)

## 快速开始

### 前置要求

1. **Python 3.8+** (推荐 3.11)
2. **Git**
3. **uv** (Python 包管理器)
4. **构建依赖**：会自动安装

### 本地构建

```bash
# 克隆项目
git clone https://github.com/your-username/claudewarp.git
cd claudewarp

# 同步依赖
uv sync --all-groups --all-extras

# 构建应用
just pyinstaller

# 输出文件在当前目录
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

```bash
# 基础构建
just pyinstaller

# 手动构建 - GUI 应用程序 (macOS)
pyinstaller --name=ClaudeWarp \
    --onedir \
    --windowed \
    --icon=claudewarp/gui/resources/icons/claudewarp.ico \
    main.py

# Windows 构建
pyinstaller --name=claudewarp \
    --onefile \
    --windowed \
    --icon=claudewarp/gui/resources/icons/claudewarp.ico \
    main.py
```

### 3. 输出文件

构建完成后，会生成：

#### macOS
- `ClaudeWarp.app` - 应用程序包 (在 dist/ 文件夹中)
- 可选的 DMG 安装包

#### Windows
- `claudewarp.exe` - 可执行文件 (在 dist/ 文件夹中)

### 4. 代码格式化

```bash
# 格式化代码
just format
```

## 自动化构建

### GitHub Actions

项目配置了自动化构建，会在以下情况触发：

1. **标签推送**: `git tag v1.0.0 && git push origin v1.0.0`
2. **主分支提交**: 推送到 `main` 或 `develop` 分支
3. **手动触发**: 在 GitHub Actions 页面手动运行

### 发布流程

```bash
# 1. 更新版本号
# 编辑 pyproject.toml 中的 version

# 2. 创建并推送标签
git tag v1.0.0
git push origin v1.0.0

# 3. GitHub Actions 自动构建并创建 Release
```

## PyInstaller 配置说明

### 主要参数

- `--onedir`: 创建目录分发（macOS用于.app包）
- `--onefile`: 创建单文件可执行程序（Windows）
- `--windowed`: 无控制台窗口的GUI应用
- `--icon`: 设置应用图标
- `--hidden-import`: 指定需要包含的隐藏导入

### 图标配置

将应用图标放置在：
```
claudewarp/gui/resources/icons/claudewarp.ico
```

## 平台特定配置

### macOS

#### 代码签名（可选）
```bash
# 安装开发者证书后
codesign --force --verify --verbose --sign "Developer ID Application: Your Name" claudewarp.app
```

#### 公证（App Store 外分发）
```bash
# 需要 Apple Developer 账户
xcrun notarytool submit claudewarp.app.zip --keychain-profile "notarytool-profile" --wait
```

### Windows

#### 代码签名（可选）
需要代码签名证书，使用工具如 SignTool。

### Linux（可选）

#### AppImage 创建
```bash
# 安装 linuxdeploy
wget https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage
chmod +x linuxdeploy-x86_64.AppImage

# 创建 AppImage
./linuxdeploy-x86_64.AppImage --appdir claudewarp.dist --output appimage
```

## 故障排除

### 常见问题

#### 1. 模块导入错误
```bash
# 解决方案：添加 --hidden-import 参数
pyinstaller --hidden-import=缺失的模块名 ...
```

#### 2. 资源文件缺失
```bash
# 解决方案：添加 --add-data 参数
pyinstaller --add-data=源路径:目标路径 ...
```

#### 3. macOS 权限问题
```bash
# 首次运行需要允许
sudo spctl --master-disable  # 临时禁用 Gatekeeper
# 或在 系统偏好设置 > 安全性与隐私 中允许
```

#### 4. Windows 杀毒软件误报
- 构建后的 exe 可能被误报为病毒
- 解决方案：代码签名或添加到白名单

### 调试构建

#### 启用详细输出
```bash
# 添加调试参数
pyinstaller --debug=all --log-level=DEBUG ...
```

#### 性能优化

```bash
# 启用优化
pyinstaller --optimize=2 ...

# 减小包大小
pyinstaller --exclude-module=不需要的模块 ...
```

## 性能优化

### 减小包大小

1. **排除不必要的模块**：使用 `--exclude-module=模块名`
2. **优化图标和资源**：使用压缩后的图像
3. **启用优化**：使用 `--optimize=2`

### 提升启动速度

1. **避免重复导入**
2. **延迟导入非核心模块**
3. **优化初始化代码**

## 发布检查清单

- [ ] 更新版本号 (`pyproject.toml`)
- [ ] 运行本地测试 (`pytest`)
- [ ] 本地构建测试 (`just pyinstaller`)
- [ ] 检查生成的应用是否正常运行
- [ ] 更新 CHANGELOG.md
- [ ] 创建 Git 标签
- [ ] 推送到 GitHub
- [ ] 验证 GitHub Actions 构建
- [ ] 测试下载的发布包
- [ ] 更新文档（如需要）

## 进阶配置

### 自定义构建脚本

可以修改 `scripts/build_pyinstaller.sh` (Unix) 或 `scripts/build_pyinstaller.ps1` (Windows) 来：
- 添加预处理步骤
- 集成其他工具（如 DMG 创建）
- 添加验证步骤

### CI/CD 扩展

在 `.github/workflows/build.yml` 中可以：
- 添加更多测试平台
- 集成代码质量检查
- 配置自动部署

## 支持与反馈

如果在构建过程中遇到问题：

1. 查看本文档的故障排除部分
2. 检查 GitHub Issues
3. 创建新的 Issue 并提供：
   - 操作系统和版本
   - Python 版本
   - 完整的错误信息
   - 构建日志