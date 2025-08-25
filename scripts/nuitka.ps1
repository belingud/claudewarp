# This script compiles the Claudewarp GUI application into both single-file and multi-file distributions for Windows using Nuitka and PowerShell.

# Ensure the script is run from the project root directory.

# If you are using a virtual environment, make sure it's activated before running this script.
# For example:
# .\.venv\Scripts\Activate.ps1

Write-Host "Starting Nuitka compilation for Windows (Both Single-File and Multi-File)..."

# Clean previous builds
if (Test-Path "build") {
    Write-Host "Cleaning previous builds..."
    Remove-Item -Path "build" -Recurse -Force
}

$success = $true

Write-Host ""
Write-Host "=== Building Single-File Version ==="

# Execute single-file build script
try {
    & "$PSScriptRoot\nuitka_onefile.ps1"
    if ($LASTEXITCODE -ne 0) {
        throw "Single-file build script failed with exit code $LASTEXITCODE"
    }
    
    # Backup the single-file executable
    if (Test-Path "build/main.exe") {
        Copy-Item "build/main.exe" "build/main_onefile.exe"
        Write-Host "Success: Single-file build backed up as main_onefile.exe"
    }
} catch {
    Write-Host "Error in single-file build: $($_.Exception.Message)" -ForegroundColor Red
    $success = $false
}

Write-Host ""
Write-Host "=== Building Multi-File Version ==="

# Execute multi-file build script
try {
    & "$PSScriptRoot\nuitka_multifile.ps1"
    if ($LASTEXITCODE -ne 0) {
        throw "Multi-file build script failed with exit code $LASTEXITCODE"
    }
    
    # Backup the multi-file executable
    if (Test-Path "build/main.exe") {
        Copy-Item "build/main.exe" "build/main_multifile.exe"
        Write-Host "Success: Multi-file build backed up as main_multifile.exe"
    }
} catch {
    Write-Host "Error in multi-file build: $($_.Exception.Message)" -ForegroundColor Red
    $success = $false
}

Write-Host ""
Write-Host "=== Final Build Summary ==="

# Show results for single-file build
if (Test-Path "build/main_onefile.exe") {
    $fileSizeBytes = (Get-Item "build/main_onefile.exe").Length
    $fileSizeMB = [math]::Round($fileSizeBytes / 1MB, 2)
    Write-Host "Success: Single-file build: build/main_onefile.exe - $($fileSizeMB) MB"
} else {
    Write-Host "Error: Single-file build failed" -ForegroundColor Red
    $success = $false
}

# Show results for multi-file build
if (Test-Path "build/main_multifile.exe") {
    $fileSizeBytes = (Get-Item "build/main_multifile.exe").Length
    $fileSizeMB = [math]::Round($fileSizeBytes / 1MB, 2)
    Write-Host "Success: Multi-file build: build/main_multifile.exe - $($fileSizeMB) MB"
    
    if (Test-Path "build/main.dist") {
        $fileCount = (Get-ChildItem -Path "build/main.dist" -Recurse -File).Count
        $totalSize = (Get-ChildItem -Path "build/main.dist" -Recurse -File | Measure-Object -Property Length -Sum).Sum
        $totalSizeMB = [math]::Round($totalSize / 1MB, 2)
        Write-Host "  Distribution folder: build/main.dist ($fileCount files, $($totalSizeMB) MB total)"
    }
} else {
    Write-Host "Error: Multi-file build failed" -ForegroundColor Red
    $success = $false
}

Write-Host ""
if ($success) {
    Write-Host "Build process completed successfully!" -ForegroundColor Green
    
    # Try to build Windows installer if multi-file build succeeded
    if (Test-Path "build/main_multifile.exe" -and Test-Path "build/main.dist") {
        Write-Host ""
        Write-Host "=== Creating Windows Installer ==="
        
        try {
            & "$PSScriptRoot\build_installer.ps1"
            if ($LASTEXITCODE -eq 0) {
                Write-Host "Windows installer created successfully!" -ForegroundColor Green
            } else {
                Write-Host "Installer creation failed, but builds are still available" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "Could not create installer: $($_.Exception.Message)" -ForegroundColor Yellow
            Write-Host "You can manually run: .\scripts\build_installer.ps1" -ForegroundColor Yellow
        }
    }
    
    Write-Host ""
    Write-Host "Available scripts:"
    Write-Host "  - .\scripts\nuitka_onefile.ps1 (single-file only)"
    Write-Host "  - .\scripts\nuitka_multifile.ps1 (multi-file only)"
    Write-Host "  - .\scripts\build_installer.ps1 (installer only)"
} else {
    Write-Host "Build process completed with errors!" -ForegroundColor Red
    exit 1
}