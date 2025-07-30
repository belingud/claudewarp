# This script compiles the Claudewarp GUI application into a single executable for Windows using Nuitka and PowerShell.

# Ensure the script is run from the project root directory.

# If you are using a virtual environment, make sure it's activated before running this script.
# For example:
# .\.venv\Scripts\Activate.ps1

Write-Host "Starting Nuitka compilation for Windows..."

# Run the Nuitka compilation command
uv run nuitka `
    --standalone `
    --onefile `
    --enable-plugin=pyside6 `
    --windows-disable-console `
    --windows-icon-from-ico=claudewarp/gui/resources/icons/claudewarp.ico `
    --output-dir=build `
    --assume-yes-for-download `
    --report=report.html `
    --nofollow-import-to=PySide6.QtOpenGL `
    --nofollow-import-to=PySide6.QtMultimedia `
    --nofollow-import-to=PySide6.QtMultimediaWidgets `
    --nofollow-import-to=PySide6.QtWebEngineWidgets `
    --nofollow-import-to=PySide6.QtQml `
    --nofollow-import-to=PySide6.QtQuick `
    --nofollow-import-to=PySide6.QtNetwork `
    --nofollow-import-to=imageio `
    --nofollow-import-to=numpy `
    --nofollow-import-to=PIL `
    --nofollow-import-to=markdown_it_py `
    --nofollow-import-to=mdurl `
    --nofollow-import-to=pygments `
    --nofollow-import-to=shellingham `
    --nofollow-import-to=bump2version `
    --nofollow-import-to=deptry `
    --nofollow-import-to=pyright `
    --nofollow-import-to=pre_commit `
    --nofollow-import-to=pytest `
    --nofollow-import-to=pytest_cov `
    --nofollow-import-to=pytest_qt `
    --nofollow-import-to=iniconfig `
    --nofollow-import-to=pluggy `
    --nofollow-import-to=virtualenv `
    --nofollow-import-to=platformdirs `
    --nofollow-import-to=filelock `
    --nofollow-import-to=cfgv `
    --nofollow-import-to=identify `
    --nofollow-import-to=nodeenv `
    --nofollow-import-to=pyyaml `
    --nofollow-import-to=claudewarp.cli `
    --nofollow-import-to=bdb `
    --nofollow-import-to=bz2 `
    --nofollow-import-to=calendar `
    --nofollow-import-to=cgi `
    --nofollow-import-to=cgitb `
    --nofollow-import-to=chunk `
    --nofollow-import-to=pdb `
    --nofollow-import-to=trace `
    --nofollow-import-to=tracemalloc `
    --nofollow-import-to=uu `
    --nofollow-import-to=xdrlib `
    --nofollow-import-to=imaplib `
    --nofollow-import-to=poplib `
    --nofollow-import-to=ftplib `
    --nofollow-import-to=socketserver `
    --include-module=typing_inspection `
    claudewarp/gui/app.py

Write-Host "Compilation finished."

# Define the path to the compiled executable
$exePath = "build/app.exe"

# Check if the file exists
if (Test-Path $exePath) {
    # Get the file size in bytes
    $fileSizeBytes = (Get-Item $exePath).Length

    # Convert to Megabytes and round to 2 decimal places
    $fileSizeMB = [math]::Round($fileSizeBytes / 1MB, 2)

    # Display the file size
    Write-Host "Output file: $exePath"
    Write-Host "File size: $($fileSizeMB) MB ($($fileSizeBytes) bytes)"
} else {
    Write-Host "Error: Compiled file not found at $exePath"
}

# Pause the script to see the output before the window closes.
Read-Host -Prompt "Press Enter to exit"
