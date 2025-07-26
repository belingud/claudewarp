help:
    @just -l

sync:
    @echo "Syncing dependencies..."
    @uv sync --all-groups --all-extras


nuitka:
    @echo "Building application with uv and Nuitka..."
    @echo "UV version: $(uv --version)"
    @uv run python -m nuitka --standalone \
        --macos-create-app-bundle \
        --enable-plugin=pyside6 \
        --macos-app-icon=claudewarp/gui/resources/icons/claudewarp.ico \
        --macos-app-name=ClaudeWarp \
        --output-filename=claudewarp \
        --verbose \
        --show-progress \
        main.py
    @if [ -d "main.app" ]; then mv main.app ClaudeWarp.app; echo "✅ Renamed to ClaudeWarp.app"; fi

format:
    @echo "Formatting code with uv..."
    @uv run ruff check --fix claudewarp
    @uv run ruff format claudewarp
    @uv run isort claudewarp
