# PyInstaller build script for ClaudeWarp GUI application (Windows)
# This script creates a standalone GUI executable with PySide6

param(
    [switch]$Clean = $false
)

# Colors for output
$ErrorActionPreference = "Stop"

# Project settings
$PROJECT_NAME = "claudewarp"
$MAIN_SCRIPT = "main.py"
$BUILD_DIR = "build"
$DIST_DIR = "dist"
$SPEC_FILE = "$PROJECT_NAME.spec"

Write-Host "=== ClaudeWarp GUI PyInstaller Build Script (Windows) ===" -ForegroundColor Blue
Write-Host "Project root: $(Get-Location)" -ForegroundColor Blue

# Clean previous builds
Write-Host "Cleaning previous builds..." -ForegroundColor Yellow
Remove-Item -Path $BUILD_DIR -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path $DIST_DIR -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path $SPEC_FILE -Force -ErrorAction SilentlyContinue

# Install GUI dependencies and PyInstaller
Write-Host "Installing GUI dependencies..." -ForegroundColor Yellow
& uv add --dev pyinstaller
& uv sync --group gui

# Build with PyInstaller
Write-Host "Building GUI application with PyInstaller..." -ForegroundColor Yellow

$pyinstallerArgs = @(
    "--name=$PROJECT_NAME"
    "--onefile"
    "--windowed"
    "--clean"
    "--noconfirm"
    "--optimize=2"
    "--icon=claudewarp/gui/resources/icons/claudewarp.ico"
    "--exclude-module=tkinter"
    "--exclude-module=matplotlib"
    "--exclude-module=numpy"
    "--exclude-module=scipy"
    "--exclude-module=pandas"
    "--exclude-module=jupyter"
    "--exclude-module=IPython"
    "--hidden-import=toml"
    "--hidden-import=rich"
    "--hidden-import=colorlog"
    "--hidden-import=typer"
    "--hidden-import=pydantic"
    "--hidden-import=PySide6.QtCore"
    "--hidden-import=PySide6.QtGui"
    "--hidden-import=PySide6.QtWidgets"
    "--hidden-import=qfluentwidgets"
    "--hidden-import=claudewarp.gui"
    "--hidden-import=claudewarp.gui.app"
    "--hidden-import=claudewarp.gui.main_window"
    "--hidden-import=claudewarp.gui.dialogs"
    "--hidden-import=claudewarp.cli"
    "--hidden-import=claudewarp.core"
    "--hidden-import=claudewarp.cli.main"
    "--hidden-import=claudewarp.cli.commands"
    "--hidden-import=claudewarp.cli.formatters"
    "--hidden-import=claudewarp.core.config"
    "--hidden-import=claudewarp.core.manager"
    "--hidden-import=claudewarp.core.models"
    "--hidden-import=claudewarp.core.utils"
    "--hidden-import=claudewarp.core.exceptions"
    "--add-data=claudewarp;claudewarp"
    "--add-data=claudewarp/gui/resources;claudewarp/gui/resources"
    "--distpath=$DIST_DIR"
    "--workpath=$BUILD_DIR"
    "--specpath=."
    $MAIN_SCRIPT
)

& uv run pyinstaller @pyinstallerArgs

# Check if build was successful
$executablePath = "$DIST_DIR\$PROJECT_NAME.exe"
if (Test-Path $executablePath) {
    Write-Host "✅ Build successful!" -ForegroundColor Green
    
    # Get file size
    $fileSize = (Get-Item $executablePath).Length
    $fileSizeFormatted = [math]::Round($fileSize / 1MB, 2)
    Write-Host "📦 Executable size: $fileSizeFormatted MB" -ForegroundColor Green
    Write-Host "📍 Location: $executablePath" -ForegroundColor Green
    
    Write-Host "✅ Windows executable created successfully!" -ForegroundColor Green
    Write-Host "You can run the application with: $executablePath" -ForegroundColor Green
    
} else {
    Write-Host "❌ Build failed! $PROJECT_NAME.exe not found" -ForegroundColor Red
    Write-Host "Check the output above for errors." -ForegroundColor Red
    Get-ChildItem $DIST_DIR -ErrorAction SilentlyContinue
    exit 1
}

# Create portable package
Write-Host "Creating portable package..." -ForegroundColor Yellow
$packageName = "$PROJECT_NAME-Windows-$(if ([Environment]::Is64BitOperatingSystem) { 'x64' } else { 'x86' })"
$packageDir = "$DIST_DIR\$packageName"

New-Item -ItemType Directory -Path $packageDir -Force | Out-Null

# Copy executable
Copy-Item -Path $executablePath -Destination $packageDir

# Copy documentation files
if (Test-Path "README.md") {
    Copy-Item -Path "README.md" -Destination $packageDir
}
if (Test-Path "LICENSE") {
    Copy-Item -Path "LICENSE" -Destination $packageDir
}

# Create usage file
$usageContent = @"
ClaudeWarp GUI Application

This is the graphical user interface version of ClaudeWarp.

Usage:
  Double-click $PROJECT_NAME.exe to launch the GUI application
  
Features:
  - Manage Claude API proxy servers
  - Add, edit, and delete proxy configurations
  - Switch between different proxies
  - Export settings for Claude Code integration
  - Visual status indicators and notifications

For command-line usage, please download the CLI version instead.
"@

Set-Content -Path "$packageDir\USAGE.txt" -Value $usageContent -Encoding UTF8

Write-Host "📦 Portable package created: $packageDir" -ForegroundColor Green

# Create ZIP package for distribution
Write-Host "Creating ZIP package for distribution..." -ForegroundColor Yellow
$zipName = "ClaudeWarp-Windows-$(if ([Environment]::Is64BitOperatingSystem) { 'x64' } else { 'x86' }).zip"
Compress-Archive -Path $executablePath -DestinationPath $zipName -Force
Write-Host "✅ ZIP package created: $zipName" -ForegroundColor Green

Write-Host "=== Build Summary ===" -ForegroundColor Blue
Write-Host "Executable: $executablePath ($fileSizeFormatted MB)" -ForegroundColor Blue
Write-Host "Package: $packageDir" -ForegroundColor Blue
Write-Host "ZIP: $zipName" -ForegroundColor Blue
Write-Host "Windows application ready for distribution! 🎉" -ForegroundColor Green