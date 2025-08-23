# This script compiles the Claudewarp GUI application into a single executable for Windows using Nuitka and PowerShell.

# Ensure the script is run from the project root directory.

# If you are using a virtual environment, make sure it's activated before running this script.
# For example:
# .\.venv\Scripts\Activate.ps1

# Load common functions
. ".\scripts\nuitka_common.ps1"

Write-Host "Starting Nuitka compilation for Windows (Single File)..."

try {
    Invoke-NuitkaBuild -BuildType "onefile" -ReportName "report_onefile.html"
    Write-Host "Compilation finished."
    Show-BuildResults -BuildType "Single-file"
} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}