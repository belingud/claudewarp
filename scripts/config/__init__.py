"""
Nuitka configuration package

Provides configuration classes and utilities for building ClaudeWarp with Nuitka.
"""

from .nuitka_base import (
    BuildMode,
    NuitkaConfig,
    OptimizationLevel,
    OutputFormat,
    Platform,
    GUI_EXCLUSIONS,
    CLI_EXCLUSIONS,
    COMMON_EXCLUSIONS,
)

from .nuitka_platforms import (
    MacOSConfig,
    LinuxConfig,
    WindowsConfig,
    create_platform_config,
    create_cross_platform_config,
    MACOS_OPTIMIZATIONS,
    LINUX_OPTIMIZATIONS,
    WINDOWS_OPTIMIZATIONS,
)

__all__ = [
    # Base classes
    "BuildMode",
    "NuitkaConfig",
    "OptimizationLevel",
    "OutputFormat",
    "Platform",
    # Platform-specific classes
    "MacOSConfig",
    "LinuxConfig",
    "WindowsConfig",
    # Factory functions
    "create_platform_config",
    "create_cross_platform_config",
    # Exclusion sets
    "GUI_EXCLUSIONS",
    "CLI_EXCLUSIONS",
    "COMMON_EXCLUSIONS",
    # Optimization presets
    "MACOS_OPTIMIZATIONS",
    "LINUX_OPTIMIZATIONS",
    "WINDOWS_OPTIMIZATIONS",
]
