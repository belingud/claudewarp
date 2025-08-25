# This script creates a Windows installer for ClaudeWarp using Inno Setup
# Prerequisites: 
# 1. Multi-file build must be completed first (run nuitka_multifile.ps1)
# 2. Inno Setup must be installed (https://jrsoftware.org/isinfo.php)

Write-Host "Building ClaudeWarp Windows Installer..."

# Check if build files exist
$exePath = "build/main.exe"
$distPath = "build/main.dist"

if (!(Test-Path $exePath)) {
    Write-Host "Error: Multi-file executable not found at $exePath" -ForegroundColor Red
    Write-Host "Please run nuitka_multifile.ps1 first to create the multi-file build." -ForegroundColor Yellow
    exit 1
}

if (!(Test-Path $distPath)) {
    Write-Host "Error: Distribution folder not found at $distPath" -ForegroundColor Red
    Write-Host "Please run nuitka_multifile.ps1 first to create the multi-file build." -ForegroundColor Yellow
    exit 1
}

# Check if Inno Setup is installed
$innoSetupPath = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 5\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 5\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if (!$innoSetupPath) {
    Write-Host "Error: Inno Setup not found!" -ForegroundColor Red
    Write-Host "Please install Inno Setup from: https://jrsoftware.org/isinfo.php" -ForegroundColor Yellow
    Write-Host "Supported versions: Inno Setup 5 or 6" -ForegroundColor Yellow
    exit 1
}

Write-Host "Found Inno Setup at: $innoSetupPath"

# Create installer output directory
$installerDir = "build\installer"
if (!(Test-Path $installerDir)) {
    New-Item -ItemType Directory -Path $installerDir -Force | Out-Null
    Write-Host "Created installer output directory: $installerDir"
}

# Check if installer script exists
$installerScript = "scripts\installer.iss"
if (!(Test-Path $installerScript)) {
    Write-Host "Error: Installer script not found at $installerScript" -ForegroundColor Red
    exit 1
}

# Show build information
Write-Host ""
Write-Host "=== Build Information ==="
$exeSize = [math]::Round((Get-Item $exePath).Length / 1MB, 2)
$fileCount = (Get-ChildItem -Path $distPath -Recurse -File).Count
$totalSize = (Get-ChildItem -Path $distPath -Recurse -File | Measure-Object -Property Length -Sum).Sum
$totalSizeMB = [math]::Round($totalSize / 1MB, 2)

Write-Host "Executable: $exePath ($exeSize MB)"
Write-Host "Distribution: $distPath ($fileCount files, $totalSizeMB MB)"

# Compile installer
Write-Host ""
Write-Host "=== Compiling Installer ==="
Write-Host "Script: $installerScript"

try {
    $startTime = Get-Date
    & "$innoSetupPath" "$installerScript"
    $endTime = Get-Date
    $duration = $endTime - $startTime
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Installer compilation completed successfully in $($duration.TotalSeconds.ToString('F2')) seconds" -ForegroundColor Green
        
        # Find and display installer file information
        $installerFiles = Get-ChildItem -Path $installerDir -Filter "*.exe" | Sort-Object LastWriteTime -Descending
        
        if ($installerFiles.Count -gt 0) {
            $installerFile = $installerFiles[0]
            $installerSizeMB = [math]::Round($installerFile.Length / 1MB, 2)
            
            Write-Host ""
            Write-Host "=== Installer Created ===" -ForegroundColor Green
            Write-Host "File: $($installerFile.FullName)"
            Write-Host "Size: $installerSizeMB MB ($($installerFile.Length) bytes)"
            Write-Host "Created: $($installerFile.LastWriteTime)"
            
            # Show installation instructions
            Write-Host ""
            Write-Host "=== Installation Instructions ===" -ForegroundColor Cyan
            Write-Host "1. Run the installer as administrator for system-wide installation"
            Write-Host "2. Or run normally for user-only installation"
            Write-Host "3. The installer includes options to:"
            Write-Host "   - Create desktop shortcut"
            Write-Host "   - Add to PATH environment variable"
            Write-Host "   - Create Start menu entries"
        } else {
            Write-Host "Warning: Installer compilation completed but no .exe found in $installerDir" -ForegroundColor Yellow
        }
    } else {
        Write-Host "Error: Installer compilation failed with exit code $LASTEXITCODE" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "Error compiling installer: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Installer build completed successfully!" -ForegroundColor Green