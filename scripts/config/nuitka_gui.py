"""
GUI-only build configuration for ClaudeWarp

This module provides optimized configuration specifically for GUI-only builds
that exclude all CLI dependencies to minimize executable size.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Set

from .nuitka_base import BuildMode, NuitkaConfig, OptimizationLevel, Platform


# CLI dependencies to exclude from GUI builds
CLI_DEPENDENCIES = {
    # Core CLI frameworks
    "typer",
    "click",
    "rich.prompt",
    "rich.progress",
    "rich.tree",
    "rich.live",
    # CLI-specific rich components
    "rich.console._environ",
    "rich.highlighter",
    "rich.markup",
    "rich.pager",
    "rich.spinner",
    # Command line parsing
    "argparse._subparsers",
    "cmd",
    "readline",
    "rlcompleter",
}

# Development and testing tools (not needed in production GUI)
DEVELOPMENT_DEPENDENCIES = {
    "pytest",
    "pytest_qt",
    "pytest_cov",
    "pytest_mock",
    "coverage",
    "mypy",
    "black",
    "ruff",
    "isort",
    "pre_commit",
    "bump2version",
}

# System tools not needed for GUI applications
SYSTEM_TOOLS = {
    "subprocess",
    "os.system",
    "shutil.which",
    "distutils",
    "setuptools",
    "pip",
    "pkg_resources",
}

# GUI framework alternatives we don't use
UNUSED_GUI_FRAMEWORKS = {
    "tkinter",
    "tkinter.ttk",
    "tkinter.filedialog",
    "tkinter.messagebox",
    "wx",
    "wxPython",
    "PyQt5",
    "PyQt6",
    "kivy",
    "toga",
}

# Data science and scientific libraries (typically not needed for proxy management)
SCIENTIFIC_LIBRARIES = {
    "numpy",
    "pandas",
    "matplotlib",
    "scipy",
    "sklearn",
    "scikit-learn",
    "seaborn",
    "plotly",
    "bokeh",
    "altair",
    "jupyter",
    "IPython",
    "notebook",
    "jupyterlab",
}

# Machine learning and AI libraries
ML_LIBRARIES = {
    "torch",
    "pytorch",
    "tensorflow",
    "tf",
    "keras",
    "transformers",
    "diffusers",
    "accelerate",
    "datasets",
    "tokenizers",
}


@dataclass
class GUIOnlyConfig(NuitkaConfig):
    """Specialized configuration for GUI-only builds"""

    def __post_init__(self):
        """Configure GUI-only specific settings"""
        # Set build mode
        self.build_mode = BuildMode.GUI_ONLY

        # Call parent configuration
        super().__post_init__()

        # Add comprehensive exclusions for GUI-only builds
        self.exclusions.update(CLI_DEPENDENCIES)
        self.exclusions.update(DEVELOPMENT_DEPENDENCIES)
        self.exclusions.update(SYSTEM_TOOLS)
        self.exclusions.update(UNUSED_GUI_FRAMEWORKS)
        self.exclusions.update(SCIENTIFIC_LIBRARIES)
        self.exclusions.update(ML_LIBRARIES)

        # GUI-specific optimizations
        self.disable_console = True

        # Ensure GUI entry point
        if not self.entry_point:
            self.entry_point = Path("main_gui.py")

        # Add GUI-specific hidden imports
        gui_imports = [
            "claudewarp.gui.app",
            "claudewarp.gui.main_window",
            "claudewarp.gui.dialogs",
            "claudewarp.gui.theme_manager",
            # Core modules needed by GUI
            "claudewarp.core.config",
            "claudewarp.core.manager",
            "claudewarp.core.models",
            "claudewarp.core.utils",
            "claudewarp.core.exceptions",
            # Essential PySide6 modules
            "PySide6.QtCore",
            "PySide6.QtGui",
            "PySide6.QtWidgets",
            "PySide6.QtSvg",  # For icon support
            # QFluentWidgets components
            "qfluentwidgets",
            "qfluentwidgets.components",
            "qfluentwidgets.common",
            # Theme detection
            "darkdetect",
            # Essential utilities
            "toml",
            "pydantic",
            "colorlog",
        ]

        # Add to existing hidden imports
        for import_name in gui_imports:
            if import_name not in self.hidden_imports:
                self.hidden_imports.append(import_name)


def create_gui_only_config(
    platform: Platform = None,
    optimization: OptimizationLevel = OptimizationLevel.PRODUCTION,
    **kwargs,
) -> GUIOnlyConfig:
    """Create optimized GUI-only build configuration

    Args:
        platform: Target platform (auto-detected if None)
        optimization: Optimization level
        **kwargs: Additional configuration options

    Returns:
        Configured GUIOnlyConfig instance
    """
    if platform is None:
        platform = Platform.current()

    config = GUIOnlyConfig(target_platform=platform, optimization_level=optimization, **kwargs)

    return config


def create_minimal_gui_config(**kwargs) -> GUIOnlyConfig:
    """Create minimally-sized GUI configuration with maximum exclusions"""
    config = create_gui_only_config(**kwargs)

    # Add even more aggressive exclusions for minimal size
    additional_exclusions = {
        # Network libraries (if not needed for proxy management)
        "urllib3.contrib",
        "requests.packages",
        "certifi.core",
        # Encoding libraries we might not need
        "encodings.idna",
        "encodings.punycode",
        # Debugging and profiling
        "pdb",
        "cProfile",
        "profile",
        "trace",
        # Documentation and help
        "pydoc",
        "doctest",
        "help",
        # Alternative JSON libraries
        "ujson",
        "orjson",
        "simplejson",
    }

    config.exclusions.update(additional_exclusions)

    return config


def validate_gui_exclusions(exclusions: Set[str]) -> Set[str]:
    """Validate that GUI exclusions don't break required functionality

    Args:
        exclusions: Set of modules to exclude

    Returns:
        Set of safe exclusions (removes any that might break GUI)
    """
    # Modules that should NEVER be excluded from GUI builds
    essential_modules = {
        "sys",
        "os",
        "pathlib",
        "json",
        "logging",
        "traceback",
        "PySide6",
        "qfluentwidgets",
        "darkdetect",
        "pydantic",
        "toml",
        "colorlog",
    }

    # Remove any essential modules from exclusions
    safe_exclusions = {
        module
        for module in exclusions
        if not any(module.startswith(essential) for essential in essential_modules)
    }

    removed = exclusions - safe_exclusions
    if removed:
        print(f"⚠️  Removed essential modules from exclusions: {removed}")

    return safe_exclusions
