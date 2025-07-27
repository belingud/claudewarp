# Python Project Guide

## Build/Test/Lint Commands
- Install deps: `uv sync`
- Run all tests: `uv run pytest --cache-clear -vv tests`
- Run specific test: `uv run pytest tests/path/to/test_file.py::test_function_name -v`
- Run with coverage: `just test`
- Format code: `just format` (runs ruff, isort)
- Individual formatting:
  - Ruff: `just ruff`
  - Isort: `just isort`

## Code Style Guidelines
- Python 3.9+ compatible code
- Type hints required for all functions and methods
- Classes: PascalCase with descriptive names
- Functions/Variables: snake_case
- Constants: UPPERCASE_WITH_UNDERSCORES
- Imports organization with isort:
  1. Standard library imports
  2. Third-party imports
  3. Local application imports
- Error handling: Use specific exception types
- Logging: Use the colorlog for console log format
- Use dataclasses for structured data when applicable
- Use pydantic for data validation and serialization

## Project Conventions
- Use uv for dependency management
- Add tests for all new functionality
- Maintain >80% test coverage (current min: 81%)
- Document public APIs with docstrings