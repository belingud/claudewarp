help:
    @just -l

sync:
    @echo "Syncing dependencies..."
    @uv sync --all-groups --all-extras

# Nuitka build commands
nuitka:
    @echo "Building GUI application with Nuitka (optimized)..."
    @python scripts/build_nuitka.py --mode gui --optimization prod

nuitka-dev:
    @echo "Building GUI application with Nuitka (development)..."
    @python scripts/build_nuitka.py --mode gui --optimization dev --debug

nuitka-universal:
    @echo "Building universal application with Nuitka..."
    @python scripts/build_nuitka.py --mode universal --optimization prod

# Direct Nuitka command with specified parameters
nuitka-direct:
    @echo "Building GUI application with direct Nuitka command..."
    @uv run nuitka --standalone --onefile --enable-plugin=pyside6 --macos-create-app-bundle --output-dir=build --macos-app-icon=claudewarp/gui/resources/icons/claudewarp.ico --assume-yes-for-download --disable-console main.py

# Legacy PyInstaller support (deprecated)
pyinstaller:
    @echo "⚠️  PyInstaller support is deprecated. Use 'just nuitka' instead."
    @echo "Building application with uv and PyInstaller..."
    @echo "UV version: $(uv --version)"
    @bash scripts/build_pyinstaller.sh

format:
    @echo "Formatting code with uv..."
    @uv run ruff check --fix claudewarp
    @uv run ruff format claudewarp
    @uv run isort claudewarp
