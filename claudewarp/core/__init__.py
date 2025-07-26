"""
Claude中转站管理工具 - 核心模块

提供配置管理、代理服务器管理等核心功能。
"""

__version__ = "0.1.0"
__author__ = "claudewarp"

from .exceptions import (
    ClaudeWarpError,
    ConfigError,
    DuplicateProxyError,
    ProxyNotFoundError,
)
from .models import ExportFormat, ProxyConfig, ProxyServer

# ConfigManager and ProxyManager require external dependencies
# They will be imported only when available
try:
    from .config import ConfigManager

    _CONFIG_AVAILABLE = True
except ImportError:
    _CONFIG_AVAILABLE = False
    ConfigManager = None

try:
    from .manager import ProxyManager

    _MANAGER_AVAILABLE = True
except ImportError:
    _MANAGER_AVAILABLE = False
    ProxyManager = None

__all__ = [
    "ClaudeWarpError",
    "ConfigError",
    "ProxyNotFoundError",
    "DuplicateProxyError",
    "ProxyServer",
    "ProxyConfig",
    "ExportFormat",
]

# Add available components
if _CONFIG_AVAILABLE:
    __all__.append("ConfigManager")
if _MANAGER_AVAILABLE:
    __all__.append("ProxyManager")
