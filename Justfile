help:
    @just -l

sync:
    @echo "Syncing dependencies..."
    @uv sync --all-groups --all-extras


pyinstaller:
    @echo "Building application with uv and PyInstaller..."
    @echo "UV version: $(uv --version)"
    @bash scripts/build_pyinstaller.sh

format:
    @echo "Formatting code with uv..."
    @uv run ruff check --fix claudewarp
    @uv run ruff format claudewarp
    @uv run isort claudewarp
