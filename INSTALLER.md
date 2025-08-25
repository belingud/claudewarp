# Windows 安装程序构建指南

本文档介绍如何为 ClaudeWarp 创建 Windows 安装程序，让用户可以像安装普通软件一样安装你的应用。

## 📋 前置要求

### 1. 安装 Inno Setup
下载并安装 Inno Setup（免费的 Windows 安装程序制作工具）：
- 官网: https://jrsoftware.org/isinfo.php
- 推荐版本: Inno Setup 6.x（也支持 5.x）
- 安装到默认路径即可，脚本会自动检测

### 2. 完成应用打包
确保已经成功打包了多文件版本的应用：
```powershell
.\scripts\nuitka_multifile.ps1
```

## 🚀 构建安装程序

### 方法 1: 自动构建（推荐）
运行完整的打包脚本，会自动构建安装程序：
```powershell
.\scripts\nuitka.ps1
```

### 方法 2: 单独构建安装程序
如果已有打包文件，可以单独构建安装程序：
```powershell
.\scripts\build_installer.ps1
```

### 方法 3: 手动构建
如果需要自定义，可以直接使用 Inno Setup：
```powershell
# 使用 Inno Setup 编译器
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "scripts\installer.iss"
```

## 📁 输出文件

成功构建后，安装程序将位于：
```
build/installer/ClaudeWarp-0.1.8-Setup.exe
```

## 🎯 安装程序功能

创建的安装程序具有以下功能：

### 安装选项
- **用户级安装**: 默认安装到用户目录，无需管理员权限
- **系统级安装**: 以管理员身份运行可安装到 Program Files
- **自定义安装路径**: 用户可选择安装位置

### 集成功能
- ✅ **桌面快捷方式**: 可选创建桌面图标
- ✅ **开始菜单**: 自动创建开始菜单项
- ✅ **PATH 环境变量**: 可选添加到系统 PATH
- ✅ **卸载程序**: 完整的卸载支持
- ✅ **多语言支持**: 支持中文和英文界面

### 文件关联
- 安装所有必需的 DLL 和依赖文件
- 包含许可证和说明文档
- 自动创建卸载信息

## ⚙️ 自定义配置

### 修改安装程序信息
编辑 `scripts/installer.iss` 文件中的配置：

```ini
#define MyAppName "ClaudeWarp"
#define MyAppVersion "0.1.8"
#define MyAppPublisher "ClaudeWarp"
#define MyAppURL "https://github.com/belingud/claudewarp"
```

### 修改安装选项
在 `[Tasks]` 段落中调整默认选项：
```ini
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "addtopath"; Description: "Add to PATH environment variable"; GroupDescription: "System Integration:"
```

### 添加更多文件
在 `[Files]` 段落中添加额外文件：
```ini
Source: "path\to\your\file"; DestDir: "{app}"; Flags: ignoreversion
```

## 🐛 故障排除

### 常见问题

1. **Inno Setup 未找到**
   ```
   Error: Inno Setup not found!
   ```
   - 解决: 下载安装 Inno Setup
   - 确保安装到默认路径

2. **构建文件不存在**
   ```
   Error: Multi-file executable not found
   ```
   - 解决: 先运行 `.\scripts\nuitka_multifile.ps1`

3. **权限问题**
   ```
   Access denied
   ```
   - 解决: 以管理员身份运行 PowerShell

4. **编译失败**
   - 检查 `scripts/installer.iss` 文件语法
   - 确保所有引用的文件都存在
   - 查看 Inno Setup 的错误输出

### 调试技巧

1. **查看详细日志**
   ```powershell
   # 启用详细输出
   $VerbosePreference = "Continue"
   .\scripts\build_installer.ps1
   ```

2. **手动测试**
   ```powershell
   # 直接运行 Inno Setup
   & "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "scripts\installer.iss"
   ```

3. **验证文件**
   ```powershell
   # 检查必需文件
   Test-Path "build/main.exe"
   Test-Path "build/main.dist"
   Test-Path "scripts/installer.iss"
   ```

## 📋 发布检查清单

在发布安装程序前，请确认：

- [ ] 应用程序正常运行
- [ ] 安装程序可以成功安装
- [ ] 桌面快捷方式工作正常
- [ ] 开始菜单项正确创建
- [ ] PATH 环境变量正确添加（如果选择）
- [ ] 卸载程序完全清理所有文件
- [ ] 在干净的 Windows 系统上测试安装

## 📝 版本更新

更新版本号时，需要修改：
1. `pyproject.toml` 中的版本号
2. `scripts/installer.iss` 中的 `MyAppVersion`
3. 确保 GUID 保持不变（用于升级检测）

## 🔧 高级配置

### 代码签名
为了避免 Windows SmartScreen 警告，建议对安装程序进行代码签名：

```ini
[Setup]
SignTool=standard
SignedUninstaller=yes
```

### 静默安装
支持静默安装模式：
```cmd
ClaudeWarp-0.1.8-Setup.exe /SILENT
```

### 自动更新
可以集成自动更新功能，通过检查版本号实现升级。

## 📞 支持

如果遇到问题，请：
1. 查看本文档的故障排除部分
2. 检查 Inno Setup 官方文档
3. 在 GitHub 项目中提交 Issue