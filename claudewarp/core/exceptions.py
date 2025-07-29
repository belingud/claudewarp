"""
自定义异常类

定义Claude中转站管理工具的异常层次结构，提供清晰的错误分类和处理。
"""

from typing import Any, Dict, Optional


class ClaudeWarpError(Exception):
    """基础异常类

    所有Claude Warp相关异常的基类，提供统一的错误处理接口。
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """初始化异常

        Args:
            message: 错误消息
            error_code: 错误代码，用于程序化处理
            details: 额外的错误详情
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}

    def __str__(self) -> str:
        """返回错误消息字符串"""
        return self.message

    def __repr__(self) -> str:
        """返回详细的异常表示"""
        return f"{self.__class__.__name__}('{self.message}', code='{self.error_code}')"

    def to_dict(self) -> Dict[str, Any]:
        """将异常转换为字典格式"""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }


class ConfigError(ClaudeWarpError):
    """配置相关错误

    当配置文件读取、写入、解析或验证失败时抛出。
    """

    def __init__(
        self, message: str, config_path: Optional[str] = None, error_code: Optional[str] = None
    ):
        super().__init__(message, error_code)
        self.config_path = config_path
        if config_path:
            self.details["config_path"] = config_path


class ConfigFileNotFoundError(ConfigError):
    """配置文件未找到错误"""

    def __init__(self, config_path: str):
        super().__init__(
            f"配置文件不存在: {config_path}",
            config_path=config_path,
            error_code="CONFIG_FILE_NOT_FOUND",
        )


class ConfigFileCorruptedError(ConfigError):
    """配置文件损坏错误"""

    def __init__(self, config_path: str, parse_error: Optional[str] = None):
        message = f"配置文件格式错误: {config_path}"
        if parse_error:
            message += f" - {parse_error}"

        super().__init__(message, config_path=config_path, error_code="CONFIG_FILE_CORRUPTED")
        if parse_error:
            self.details["parse_error"] = parse_error


class ConfigPermissionError(ConfigError):
    """配置文件权限错误"""

    def __init__(self, config_path: str, operation: str = "访问"):
        super().__init__(
            f"配置文件权限不足，无法{operation}: {config_path}",
            config_path=config_path,
            error_code="CONFIG_PERMISSION_ERROR",
        )
        self.details["operation"] = operation


class ProxyNotFoundError(ClaudeWarpError):
    """代理服务器未找到错误

    当尝试访问不存在的代理服务器时抛出。
    """

    def __init__(self, proxy_name: str):
        super().__init__(f"代理服务器不存在: {proxy_name}", error_code="PROXY_NOT_FOUND")
        self.proxy_name = proxy_name
        self.details["proxy_name"] = proxy_name


class DuplicateProxyError(ClaudeWarpError):
    """重复代理错误

    当尝试添加已存在的代理服务器时抛出。
    """

    def __init__(self, proxy_name: str):
        super().__init__(f"代理服务器已存在: {proxy_name}", error_code="DUPLICATE_PROXY")
        self.proxy_name = proxy_name
        self.details["proxy_name"] = proxy_name


class ValidationError(ClaudeWarpError):
    """数据验证错误

    当数据验证失败时抛出。
    """

    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None):
        super().__init__(message, error_code="VALIDATION_ERROR")
        self.field = field
        self.value = value

        if field:
            self.details["field"] = field
        if value is not None:
            self.details["value"] = str(value)


class NetworkError(ClaudeWarpError):
    """网络相关错误

    当网络连接或API调用失败时抛出。
    """

    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        status_code: Optional[int] = None,
        timeout: Optional[bool] = False,
    ):
        super().__init__(message, error_code="NETWORK_ERROR")
        self.url = url
        self.status_code = status_code
        self.timeout = timeout

        if url:
            self.details["url"] = url
        if status_code:
            self.details["status_code"] = status_code
        if timeout:
            self.details["timeout"] = True


class APIKeyError(NetworkError):
    """API密钥错误"""

    def __init__(self, message: str = "API密钥无效或已过期"):
        super().__init__(message)
        self.error_code = "API_KEY_ERROR"


class ProxyConnectionError(NetworkError):
    """代理连接错误"""

    def __init__(self, proxy_name: str, url: str, reason: Optional[str] = None):
        message = f"无法连接到代理服务器 '{proxy_name}': {url}"
        if reason:
            message += f" - {reason}"

        super().__init__(message, url=url)
        self.error_code = "PROXY_CONNECTION_ERROR"
        self.proxy_name = proxy_name
        self.details["proxy_name"] = proxy_name


class OperationError(ClaudeWarpError):
    """操作错误

    当执行操作失败时抛出。
    """

    def __init__(self, message: str, operation: Optional[str] = None, target: Optional[str] = None):
        super().__init__(message, error_code="OPERATION_ERROR")
        self.operation = operation
        self.target = target

        if operation:
            self.details["operation"] = operation
        if target:
            self.details["target"] = target


class ExportError(OperationError):
    """导出错误"""

    def __init__(self, message: str, format_type: Optional[str] = None):
        super().__init__(message, operation="export")
        self.error_code = "EXPORT_ERROR"
        self.format_type = format_type
        if format_type:
            self.details["format_type"] = format_type


class ImportError(OperationError):
    """导入错误"""

    def __init__(self, message: str, source: Optional[str] = None):
        super().__init__(message, operation="import")
        self.error_code = "IMPORT_ERROR"
        self.source = source
        if source:
            self.details["source"] = source


class SystemError(ClaudeWarpError):
    """系统错误

    当系统级错误发生时抛出。
    """

    def __init__(self, message: str, system_error: Optional[Exception] = None):
        super().__init__(message, error_code="SYSTEM_ERROR")
        self.system_error = system_error

        if system_error:
            self.details["system_error"] = str(system_error)
            self.details["system_error_type"] = type(system_error).__name__


class DiskSpaceError(SystemError):
    """磁盘空间不足错误"""

    def __init__(self, path: str, required_space: Optional[int] = None):
        message = f"磁盘空间不足: {path}"
        if required_space:
            message += f" (需要 {required_space} 字节)"

        super().__init__(message)
        self.error_code = "DISK_SPACE_ERROR"
        self.path = path
        self.required_space = required_space
        self.details["path"] = path
        if required_space:
            self.details["required_space"] = required_space


class PermissionError(SystemError):
    """权限错误"""

    def __init__(self, path: str, operation: str = "访问"):
        super().__init__(f"权限不足，无法{operation}: {path}")
        self.error_code = "PERMISSION_ERROR"
        self.path = path
        self.operation = operation
        self.details["path"] = path
        self.details["operation"] = operation


class CriticalError(ClaudeWarpError):
    """严重错误

    当发生不可恢复的严重错误时抛出。
    """

    def __init__(self, message: str, cause: Optional[Exception] = None):
        super().__init__(message, error_code="CRITICAL_ERROR")
        self.cause = cause

        if cause:
            self.details["cause"] = str(cause)
            self.details["cause_type"] = type(cause).__name__


# 错误代码常量
class ErrorCodes:
    """错误代码常量"""

    # 配置相关
    CONFIG_FILE_NOT_FOUND = "CONFIG_FILE_NOT_FOUND"
    CONFIG_FILE_CORRUPTED = "CONFIG_FILE_CORRUPTED"
    CONFIG_PERMISSION_ERROR = "CONFIG_PERMISSION_ERROR"

    # 代理相关
    PROXY_NOT_FOUND = "PROXY_NOT_FOUND"
    DUPLICATE_PROXY = "DUPLICATE_PROXY"
    PROXY_CONNECTION_ERROR = "PROXY_CONNECTION_ERROR"

    # 验证相关
    VALIDATION_ERROR = "VALIDATION_ERROR"

    # 网络相关
    NETWORK_ERROR = "NETWORK_ERROR"
    API_KEY_ERROR = "API_KEY_ERROR"

    # 操作相关
    OPERATION_ERROR = "OPERATION_ERROR"
    EXPORT_ERROR = "EXPORT_ERROR"
    IMPORT_ERROR = "IMPORT_ERROR"

    # 系统相关
    SYSTEM_ERROR = "SYSTEM_ERROR"
    DISK_SPACE_ERROR = "DISK_SPACE_ERROR"
    PERMISSION_ERROR = "PERMISSION_ERROR"

    # 严重错误
    CRITICAL_ERROR = "CRITICAL_ERROR"


# 异常分类映射
EXCEPTION_CATEGORIES = {
    "config": [
        ConfigError,
        ConfigFileNotFoundError,
        ConfigFileCorruptedError,
        ConfigPermissionError,
    ],
    "proxy": [
        ProxyNotFoundError,
        DuplicateProxyError,
        ProxyConnectionError,
    ],
    "validation": [
        ValidationError,
    ],
    "network": [
        NetworkError,
        APIKeyError,
        ProxyConnectionError,
    ],
    "operation": [
        OperationError,
        ExportError,
        ImportError,
    ],
    "system": [
        SystemError,
        DiskSpaceError,
        PermissionError,
    ],
    "critical": [
        CriticalError,
    ],
}


def is_recoverable_error(error: Exception) -> bool:
    """判断错误是否可恢复

    Args:
        error: 异常对象

    Returns:
        bool: 如果错误可恢复返回True，否则返回False
    """
    # 严重错误和系统错误通常不可恢复
    if isinstance(error, (CriticalError, SystemError)):
        return False

    # 网络错误和代理连接错误可能可恢复
    if isinstance(error, (NetworkError, ProxyConnectionError)):
        return True

    # 配置错误中，文件不存在可以恢复（创建默认配置）
    if isinstance(error, ConfigFileNotFoundError):
        return True

    # 其他配置错误需要用户干预
    if isinstance(error, ConfigError):
        return False

    # 验证错误可以通过修正数据恢复
    if isinstance(error, ValidationError):
        return True

    # 代理不存在错误可以通过添加代理恢复
    if isinstance(error, ProxyNotFoundError):
        return True

    # 重复代理错误可以通过选择不同名称恢复
    if isinstance(error, DuplicateProxyError):
        return True

    # 默认认为可恢复
    return True


def get_error_category(error: Exception) -> str:
    """获取错误类别

    Args:
        error: 异常对象

    Returns:
        str: 错误类别名称
    """
    for category, exception_types in EXCEPTION_CATEGORIES.items():
        if any(isinstance(error, exc_type) for exc_type in exception_types):
            return category

    return "unknown"


# 导出所有异常类
__all__ = [
    # 基础异常
    "ClaudeWarpError",
    # 配置相关异常
    "ConfigError",
    "ConfigFileNotFoundError",
    "ConfigFileCorruptedError",
    "ConfigPermissionError",
    # 代理相关异常
    "ProxyNotFoundError",
    "DuplicateProxyError",
    "ProxyConnectionError",
    # 验证异常
    "ValidationError",
    # 网络异常
    "NetworkError",
    "APIKeyError",
    # 操作异常
    "OperationError",
    "ExportError",
    "ImportError",
    # 系统异常
    "SystemError",
    "DiskSpaceError",
    "PermissionError",
    # 严重异常
    "CriticalError",
    # 工具函数
    "ErrorCodes",
    "EXCEPTION_CATEGORIES",
    "is_recoverable_error",
    "get_error_category",
]
