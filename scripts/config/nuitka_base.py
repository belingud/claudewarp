"""
Nuitka build configuration system

This module provides the core configuration classes and utilities for
building ClaudeWarp with Nuitka optimization.
"""

import platform
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set


class Platform(Enum):
    """Supported target platforms"""

    MACOS = "macos"
    LINUX = "linux"
    WINDOWS = "windows"

    @classmethod
    def current(cls) -> "Platform":
        """Detect current platform"""
        system = platform.system().lower()
        if system == "darwin":
            return cls.MACOS
        elif system == "linux":
            return cls.LINUX
        elif system == "windows":
            return cls.WINDOWS
        else:
            raise ValueError(f"Unsupported platform: {system}")


class BuildMode(Enum):
    """Build mode targeting different functionality"""

    GUI_ONLY = "gui_only"  # GUI-only build excluding CLI dependencies
    CLI_ONLY = "cli_only"  # CLI-only build excluding GUI dependencies
    UNIVERSAL = "universal"  # Full build with both GUI and CLI


class OptimizationLevel(Enum):
    """Build optimization levels"""

    DEVELOPMENT = "development"  # Fast builds for testing
    PRODUCTION = "production"  # Optimized builds for distribution


class OutputFormat(Enum):
    """Output format options"""

    ONEFILE = "onefile"  # Single executable file
    STANDALONE = "standalone"  # Directory with executable and dependencies
    APP_BUNDLE = "app_bundle"  # macOS .app bundle


@dataclass
class NuitkaConfig:
    """Nuitka build configuration"""

    # Target configuration
    target_platform: Platform = field(default_factory=Platform.current)
    build_mode: BuildMode = BuildMode.GUI_ONLY
    optimization_level: OptimizationLevel = OptimizationLevel.PRODUCTION
    output_format: OutputFormat = OutputFormat.ONEFILE

    # Entry point
    entry_point: Optional[Path] = None

    # Output configuration
    output_dir: Path = Path("build")
    output_name: Optional[str] = None

    # Dependencies and exclusions
    exclusions: Set[str] = field(default_factory=set)
    plugins: List[str] = field(default_factory=list)
    hidden_imports: List[str] = field(default_factory=list)

    # Optimization flags
    enable_optimizations: bool = True
    enable_lto: bool = True  # Link-time optimization
    disable_console: bool = True  # For GUI applications

    # Platform-specific options
    platform_options: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize platform-specific defaults"""
        self._setup_platform_defaults()
        self._setup_mode_defaults()

    def _setup_platform_defaults(self):
        """Configure platform-specific defaults"""
        if self.target_platform == Platform.MACOS:
            if self.output_format == OutputFormat.ONEFILE:
                self.output_format = OutputFormat.APP_BUNDLE
            self.platform_options.update(
                {
                    "macos-create-app-bundle": "",
                    "macos-app-icon": "claudewarp/gui/resources/icons/claudewarp.ico",
                }
            )
        elif self.target_platform == Platform.LINUX:
            self.platform_options.update(
                {"linux-icon": "claudewarp/gui/resources/icons/claudewarp.ico"}
            )
        elif self.target_platform == Platform.WINDOWS:
            self.platform_options.update(
                {"windows-icon-from-ico": "claudewarp/gui/resources/icons/claudewarp.ico"}
            )

    def _setup_mode_defaults(self):
        """Configure build mode defaults"""
        if self.build_mode == BuildMode.GUI_ONLY:
            # GUI-only exclusions
            self.exclusions.update(
                {
                    # CLI frameworks
                    "typer",
                    "click",
                    "rich.prompt",
                    "rich.progress",
                    # Development tools
                    "pytest",
                    "coverage",
                    "mypy",
                    "black",
                    "ruff",
                    # Unused GUI components
                    "tkinter",
                    "matplotlib",
                    "jupyter",
                    "IPython",
                    # System tools not needed for GUI
                    "subprocess",
                    "shutil.which",
                }
            )

            # GUI-specific plugins and imports
            self.plugins.extend(["pyside6"])
            self.hidden_imports.extend(
                [
                    "PySide6.QtCore",
                    "PySide6.QtGui",
                    "PySide6.QtWidgets",
                    "qfluentwidgets",
                    "claudewarp.gui.app",
                    "claudewarp.gui.main_window",
                    "claudewarp.gui.dialogs",
                    "claudewarp.core.config",
                    "claudewarp.core.manager",
                    "claudewarp.core.models",
                    "claudewarp.core.utils",
                ]
            )

            # Set GUI entry point
            if not self.entry_point:
                self.entry_point = Path("main.py")

        elif self.build_mode == BuildMode.CLI_ONLY:
            # CLI-only exclusions
            self.exclusions.update(
                {
                    # GUI frameworks
                    "PySide6",
                    "qfluentwidgets",
                    "darkdetect",
                    # Unused CLI components
                    "tkinter",
                    "matplotlib",
                    "jupyter",
                }
            )

            # CLI-specific imports
            self.hidden_imports.extend(
                [
                    "typer",
                    "rich.console",
                    "rich.table",
                    "claudewarp.cli.main",
                    "claudewarp.cli.commands",
                    "claudewarp.cli.formatters",
                    "claudewarp.core.config",
                    "claudewarp.core.manager",
                    "claudewarp.core.models",
                    "claudewarp.core.utils",
                ]
            )

            # Set CLI entry point
            if not self.entry_point:
                self.entry_point = Path("main_cli.py")

        elif self.build_mode == BuildMode.UNIVERSAL:
            # Universal build - include everything
            self.plugins.extend(["pyside6"])
            self.hidden_imports.extend(
                [
                    # GUI imports
                    "PySide6.QtCore",
                    "PySide6.QtGui",
                    "PySide6.QtWidgets",
                    "qfluentwidgets",
                    "claudewarp.gui.app",
                    "claudewarp.gui.main_window",
                    # CLI imports
                    "typer",
                    "rich.console",
                    "rich.table",
                    "claudewarp.cli.main",
                    "claudewarp.cli.commands",
                    # Core imports
                    "claudewarp.core.config",
                    "claudewarp.core.manager",
                    "claudewarp.core.models",
                    "claudewarp.core.utils",
                ]
            )

            # Set universal entry point
            if not self.entry_point:
                self.entry_point = Path("main.py")

    def to_command_args(self) -> List[str]:
        """Convert configuration to Nuitka command line arguments"""
        args = []

        # Basic flags - always use both --standalone and --onefile for optimal packaging
        args.extend(["--standalone", "--onefile"])

        # Output configuration
        args.extend([f"--output-dir={self.output_dir}", "--assume-yes-for-downloads"])

        if self.output_name:
            args.append(f"--output-filename={self.output_name}")

        # Plugins
        for plugin in self.plugins:
            args.append(f"--enable-plugin={plugin}")

        # Hidden imports
        for hidden_import in self.hidden_imports:
            args.append(f"--include-module={hidden_import}")

        # Exclusions
        for exclusion in self.exclusions:
            args.append(f"--nofollow-import-to={exclusion}")

        # Optimization flags - use correct Nuitka syntax
        if self.enable_optimizations:
            args.append("--python-flag=-O")

        if self.enable_lto:
            args.append("--lto=yes")

        if self.disable_console:
            args.append("--disable-console")

        # Platform-specific options
        for option, value in self.platform_options.items():
            if value == "":
                args.append(f"--{option}")
            else:
                args.append(f"--{option}={value}")

        # Entry point
        if self.entry_point:
            args.append(str(self.entry_point))

        return args

    @classmethod
    def gui_only(cls, **kwargs) -> "NuitkaConfig":
        """Create GUI-only build configuration"""
        return cls(build_mode=BuildMode.GUI_ONLY, **kwargs)

    @classmethod
    def cli_only(cls, **kwargs) -> "NuitkaConfig":
        """Create CLI-only build configuration"""
        return cls(build_mode=BuildMode.CLI_ONLY, **kwargs)

    @classmethod
    def universal(cls, **kwargs) -> "NuitkaConfig":
        """Create universal build configuration"""
        return cls(build_mode=BuildMode.UNIVERSAL, **kwargs)

    @classmethod
    def development(cls, **kwargs) -> "NuitkaConfig":
        """Create development build configuration"""
        return cls(
            optimization_level=OptimizationLevel.DEVELOPMENT,
            enable_optimizations=False,
            enable_lto=False,
            **kwargs,
        )


# Common exclusion sets for reuse
GUI_EXCLUSIONS = {
    "typer",
    "click",
    "rich.prompt",
    "rich.progress",
    "pytest",
    "coverage",
    "mypy",
    "black",
    "ruff",
    "tkinter",
    "matplotlib",
    "jupyter",
    "IPython",
}

CLI_EXCLUSIONS = {"PySide6", "qfluentwidgets", "darkdetect", "tkinter", "matplotlib", "jupyter"}

COMMON_EXCLUSIONS = {
    "numpy",
    "pandas",
    "scipy",
    "sklearn",
    "torch",
    "tensorflow",
    "keras",
    "jupyter",
    "IPython",
    "notebook",
}
