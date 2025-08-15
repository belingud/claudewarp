help:
    @just -l

# UV sync environment
sync:
    @echo "Syncing dependencies..."
    @uv sync --all-groups --all-extras

# Platform-specific build commands
build-mac:
    @echo "Building for macOS..."
    @./scripts/nuitka_mac.sh

build-linux:
    @echo "Building for Linux..."
    @./scripts/nuitka_linux.sh

build-windows:
    @echo "Building for Windows..."
    @powershell -ExecutionPolicy Bypass -File scripts/nuitka.ps1

# Auto-detect platform and build
build:
    @echo "Auto-detecting platform and building..."
    @{{ if os() == "macos" { "just build-mac" } else if os() == "linux" { "just build-linux" } else if os() == "windows" { "just build-windows" } else { "echo 'Unsupported platform: " + os() + "'" } }}

# Legacy nuitka command (basic macOS build)
nuitka:
    @echo "Building GUI application with basic Nuitka command (macOS only)..."
    @uv run nuitka --standalone --onefile --enable-plugin=pyside6 --macos-create-app-bundle --output-dir=build --assume-yes-for-download --macos-app-icon=claudewarp/gui/resources/icons/claudewarp.icns main.py

# Format with ruff and isort
format:
    @echo "Formatting code with uv..."
    @uv run ruff check --fix claudewarp
    @uv run ruff format claudewarp
    @uv run isort claudewarp

# Build wheel
uv-build:
    @echo "Delete dist..."
    @rm -rf dist
    @echo "Building wheel..."
    @uv build
