help:
    @just -l

# UV sync environment
sync:
    @echo "Syncing dependencies..."
    @uv sync --all-groups --all-extras

# Nuitka build commands
nuitka:
    @echo "Building GUI application with direct Nuitka command..."
    @uv run nuitka --standalone --onefile --enable-plugin=pyside6 --macos-create-app-bundle --output-dir=build --assume-yes-for-download --macos-app-icon=claudewarp/gui/resources/icons/claudewarp.ico main.py

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
