"""
Platform-specific Nuitka configurations

This module provides specialized configuration classes for different platforms
with optimizations tailored to each operating system.
"""

from dataclasses import dataclass
from pathlib import Path

from .nuitka_base import NuitkaConfig, OutputFormat, Platform


@dataclass
class MacOSConfig(NuitkaConfig):
    """macOS-specific Nuitka configuration"""

    def __post_init__(self):
        """Configure macOS-specific settings"""
        super().__post_init__()

        # Force app bundle for GUI builds on macOS
        if self.build_mode.value in ["gui_only", "universal"]:
            self.output_format = OutputFormat.APP_BUNDLE

        # macOS-specific platform options
        self.platform_options.update(
            {
                "macos-create-app-bundle": "true",
                "macos-target-arch": "universal2",  # Support both Intel and Apple Silicon
                "macos-app-name": "ClaudeWarp",
                "macos-app-version": "1.0.0",
                "macos-bundle-identifier": "com.claudewarp.app",
            }
        )

        # Add macOS-specific icon
        icon_path = Path("claudewarp/gui/resources/icons/claudewarp.icns")
        if icon_path.exists():
            self.platform_options["macos-app-icon"] = str(icon_path)

        # macOS-specific exclusions
        self.exclusions.update(
            {
                # Windows-specific modules
                "winreg",
                "winsound",
                "msvcrt",
                # Linux-specific modules
                "termios",
                "fcntl",
                "resource",
            }
        )

        # macOS-specific optimizations
        if self.enable_optimizations:
            self.platform_options.update(
                {
                    "macos-sign-identity": "adhoc",  # Ad-hoc signing for local builds
                    "static-libpython": "no",  # Use dynamic linking for smaller size
                }
            )


@dataclass
class LinuxConfig(NuitkaConfig):
    """Linux-specific Nuitka configuration"""

    def __post_init__(self):
        """Configure Linux-specific settings"""
        super().__post_init__()

        # Linux-specific platform options
        self.platform_options.update(
            {
                "linux-icon": str(Path("claudewarp/gui/resources/icons/claudewarp.png")),
                "static-libpython": "auto",  # Let Nuitka decide based on system
            }
        )

        # Linux-specific exclusions
        self.exclusions.update(
            {
                # Windows-specific modules
                "winreg",
                "winsound",
                "msvcrt",
                "ctypes.wintypes",
                # macOS-specific modules
                "objc",
                "Foundation",
                "AppKit",
                "CoreFoundation",
            }
        )

        # Linux distribution-specific optimizations
        self.platform_options.update({"assume-yes-for-downloads": "true", "progress-bar": "true"})

        # Linux GUI-specific settings
        if self.build_mode.value in ["gui_only", "universal"]:
            # Ensure Qt plugins are included
            self.hidden_imports.extend(
                [
                    "PySide6.QtCore",
                    "PySide6.QtGui",
                    "PySide6.QtWidgets",
                    "PySide6.QtSvg",  # For SVG icon support
                ]
            )


@dataclass
class WindowsConfig(NuitkaConfig):
    """Windows-specific Nuitka configuration"""

    def __post_init__(self):
        """Configure Windows-specific settings"""
        super().__post_init__()

        # Windows-specific platform options
        icon_path = Path("claudewarp/gui/resources/icons/claudewarp.ico")
        if icon_path.exists():
            self.platform_options["windows-icon-from-ico"] = str(icon_path)

        self.platform_options.update(
            {
                "windows-uac-admin": "false",  # Don't require admin privileges
                "windows-file-description": "ClaudeWarp - Claude API Proxy Manager",
                "windows-product-name": "ClaudeWarp",
                "windows-company-name": "ClaudeWarp Team",
                "windows-product-version": "1.0.0",
                "windows-file-version": "1.0.0",
            }
        )

        # Windows-specific exclusions
        self.exclusions.update(
            {
                # Unix-specific modules
                "termios",
                "fcntl",
                "resource",
                "pwd",
                "grp",
                # macOS-specific modules
                "objc",
                "Foundation",
                "AppKit",
                "CoreFoundation",
            }
        )

        # Windows-specific optimizations
        if self.enable_optimizations:
            self.platform_options.update(
                {
                    "mingw64": "false",  # Use MSVC if available
                    "static-libpython": "auto",
                }
            )

        # Windows GUI-specific settings
        if self.build_mode.value in ["gui_only", "universal"]:
            # Ensure Windows-specific Qt components
            self.hidden_imports.extend(
                [
                    "PySide6.QtWinExtras",  # Windows-specific Qt extensions
                ]
            )


def create_platform_config(**kwargs) -> NuitkaConfig:
    """Create platform-specific configuration for current system"""
    current_platform = Platform.current()

    if current_platform == Platform.MACOS:
        return MacOSConfig(**kwargs)
    elif current_platform == Platform.LINUX:
        return LinuxConfig(**kwargs)
    elif current_platform == Platform.WINDOWS:
        return WindowsConfig(**kwargs)
    else:
        # Fallback to base configuration
        return NuitkaConfig(**kwargs)


def create_cross_platform_config(target_platform: Platform, **kwargs) -> NuitkaConfig:
    """Create configuration for specific target platform"""
    kwargs["target_platform"] = target_platform

    if target_platform == Platform.MACOS:
        return MacOSConfig(**kwargs)
    elif target_platform == Platform.LINUX:
        return LinuxConfig(**kwargs)
    elif target_platform == Platform.WINDOWS:
        return WindowsConfig(**kwargs)
    else:
        return NuitkaConfig(**kwargs)


# Platform-specific optimization presets
MACOS_OPTIMIZATIONS = {
    "enable_lto": True,
    "static_libpython": False,  # Dynamic linking for smaller size
    "macos_create_app_bundle": True,
    "macos_target_arch": "universal2",
}

LINUX_OPTIMIZATIONS = {
    "enable_lto": True,
    "static_libpython": "auto",
    "linux_distribution_install": True,
    "assume_yes_for_downloads": True,
}

WINDOWS_OPTIMIZATIONS = {
    "enable_lto": True,
    "static_libpython": "auto",
    "mingw64": False,  # Prefer MSVC
    "windows_disable_console": True,
}
