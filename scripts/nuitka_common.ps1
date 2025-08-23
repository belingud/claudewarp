# Common build configuration and functions for Windows Nuitka builds
# This script contains shared configuration to avoid duplication

function Get-NuitkaCommonArgs {
    return @(
        "--standalone"
        "--enable-plugin=pyside6"
        "--windows-disable-console"
        "--windows-icon-from-ico=claudewarp/gui/resources/icons/claudewarp.ico"
        "--output-dir=build"
        "--assume-yes-for-download"
        "--nofollow-import-to=PySide6.QtOpenGL"
        "--nofollow-import-to=PySide6.QtMultimedia"
        "--nofollow-import-to=PySide6.QtMultimediaWidgets"
        "--nofollow-import-to=PySide6.QtWebEngineWidgets"
        "--nofollow-import-to=PySide6.QtQml"
        "--nofollow-import-to=PySide6.QtQuick"
        "--nofollow-import-to=PySide6.QtNetwork"
        "--nofollow-import-to=imageio"
        "--nofollow-import-to=numpy"
        "--nofollow-import-to=PIL"
        "--nofollow-import-to=markdown_it_py"
        "--nofollow-import-to=mdurl"
        "--nofollow-import-to=pygments"
        "--nofollow-import-to=shellingham"
        "--nofollow-import-to=bump2version"
        "--nofollow-import-to=deptry"
        "--nofollow-import-to=pyright"
        "--nofollow-import-to=pre_commit"
        "--nofollow-import-to=pytest"
        "--nofollow-import-to=pytest_cov"
        "--nofollow-import-to=pytest_qt"
        "--nofollow-import-to=iniconfig"
        "--nofollow-import-to=pluggy"
        "--nofollow-import-to=virtualenv"
        "--nofollow-import-to=platformdirs"
        "--nofollow-import-to=filelock"
        "--nofollow-import-to=cfgv"
        "--nofollow-import-to=identify"
        "--nofollow-import-to=nodeenv"
        "--nofollow-import-to=pyyaml"
        "--nofollow-import-to=claudewarp.cli"
        "--nofollow-import-to=bdb"
        "--nofollow-import-to=bz2"
        "--nofollow-import-to=calendar"
        "--nofollow-import-to=cgi"
        "--nofollow-import-to=cgitb"
        "--nofollow-import-to=chunk"
        "--nofollow-import-to=pdb"
        "--nofollow-import-to=trace"
        "--nofollow-import-to=tracemalloc"
        "--nofollow-import-to=uu"
        "--nofollow-import-to=xdrlib"
        "--nofollow-import-to=imaplib"
        "--nofollow-import-to=poplib"
        "--nofollow-import-to=ftplib"
        "--nofollow-import-to=socketserver"
        "--include-module=typing_inspection"
        "--include-data-dir=claudewarp/gui/resources=claudewarp/gui/resources"
        "main.py"
    )
}

function Invoke-NuitkaBuild {
    param(
        [string]$BuildType,  # "onefile" or "multifile"
        [string]$ReportName = "report.html"
    )
    
    $commonArgs = Get-NuitkaCommonArgs
    
    if ($BuildType -eq "onefile") {
        $args = @("--onefile") + $commonArgs
        $args += @("--report=$ReportName")
        Write-Host "Building single-file executable..."
    } elseif ($BuildType -eq "multifile") {
        $args = $commonArgs
        $args += @("--report=$ReportName")
        Write-Host "Building multi-file distribution..."
    } else {
        throw "Invalid build type: $BuildType. Use 'onefile' or 'multifile'"
    }
    
    # Execute Nuitka
    $command = "uv"
    $allArgs = @("run", "nuitka") + $args
    
    Write-Host "Executing: $command $($allArgs -join ' ')"
    & $command $allArgs
    
    if ($LASTEXITCODE -ne 0) {
        throw "Nuitka compilation failed with exit code $LASTEXITCODE"
    }
}

function Show-BuildResults {
    param([string]$BuildType)
    
    $exePath = "build/main.exe"
    $distPath = "build/main.dist"
    
    if (Test-Path $exePath) {
        $fileSizeBytes = (Get-Item $exePath).Length
        $fileSizeMB = [math]::Round($fileSizeBytes / 1MB, 2)
        
        Write-Host "✓ $BuildType build completed"
        Write-Host "  Executable: $exePath - $($fileSizeMB) MB"
        
        if ($BuildType -eq "multifile" -and (Test-Path $distPath)) {
            $fileCount = (Get-ChildItem -Path $distPath -Recurse -File).Count
            $totalSize = (Get-ChildItem -Path $distPath -Recurse -File | Measure-Object -Property Length -Sum).Sum
            $totalSizeMB = [math]::Round($totalSize / 1MB, 2)
            Write-Host "  Distribution folder: $distPath"
            Write-Host "  Total files: $fileCount"
            Write-Host "  Total size: $($totalSizeMB) MB"
        }
    } else {
        Write-Host "✗ $BuildType build failed: $exePath not found"
    }
}