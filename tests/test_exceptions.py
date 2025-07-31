"""
异常系统测试

测试ClaudeWarp异常体系的完整性、错误分类和处理功能。
"""

import pytest
from typing import Dict, Any, List

from claudewarp.core.exceptions import (
    # 基础异常
    ClaudeWarpError,
    
    # 配置相关异常
    ConfigError,
    ConfigFileNotFoundError,
    ConfigFileCorruptedError,
    ConfigPermissionError,
    
    # 代理相关异常
    ProxyNotFoundError,
    DuplicateProxyError,
    ProxyConnectionError,
    
    # 验证异常
    ValidationError,
    
    # 网络异常
    NetworkError,
    APIKeyError,
    
    # 操作异常
    OperationError,
    ExportError,
    ImportError,
    
    # 系统异常
    SystemError,
    DiskSpaceError,
    PermissionError,
    
    # 严重异常
    CriticalError,
    
    # 工具函数和常量
    ErrorCodes,
    EXCEPTION_CATEGORIES,
    is_recoverable_error,
    get_error_category,
)


class TestClaudeWarpError:
    """测试基础异常类"""
    
    def test_basic_error_creation(self):
        """测试基础异常创建"""
        error = ClaudeWarpError("Test error message")
        
        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.error_code == "ClaudeWarpError"
        assert error.details == {}
    
    def test_error_with_code_and_details(self):
        """测试带错误代码和详情的异常"""
        details = {"field": "test_field", "value": "test_value"}
        error = ClaudeWarpError(
            message="Test error with details",
            error_code="CUSTOM_ERROR",
            details=details
        )
        
        assert error.message == "Test error with details"
        assert error.error_code == "CUSTOM_ERROR"
        assert error.details == details
    
    def test_error_repr(self):
        """测试异常的repr表示"""
        error = ClaudeWarpError("Test message", error_code="TEST_CODE")
        
        repr_str = repr(error)
        assert "ClaudeWarpError" in repr_str
        assert "Test message" in repr_str
        assert "TEST_CODE" in repr_str
    
    def test_error_to_dict(self):
        """测试异常转换为字典"""
        details = {"context": "test_context"}
        error = ClaudeWarpError(
            message="Test message",
            error_code="TEST_CODE",
            details=details
        )
        
        error_dict = error.to_dict()
        
        expected = {
            "error_type": "ClaudeWarpError",
            "error_code": "TEST_CODE",
            "message": "Test message",
            "details": details
        }
        
        assert error_dict == expected


class TestConfigErrors:
    """测试配置相关异常"""
    
    def test_config_error_basic(self):
        """测试基础配置错误"""
        error = ConfigError("Config operation failed")
        
        assert str(error) == "Config operation failed"
        assert error.error_code == "ConfigError"
        assert error.config_path is None
    
    def test_config_error_with_path(self):
        """测试带路径的配置错误"""
        config_path = "/test/config.toml"
        error = ConfigError(
            message="Config failed",
            config_path=config_path,
            error_code="CUSTOM_CONFIG_ERROR"
        )
        
        assert error.config_path == config_path
        assert error.details["config_path"] == config_path
        assert error.error_code == "CUSTOM_CONFIG_ERROR"
    
    def test_config_file_not_found_error(self):
        """测试配置文件未找到错误"""
        config_path = "/nonexistent/config.toml"
        error = ConfigFileNotFoundError(config_path)
        
        assert f"配置文件不存在: {config_path}" in str(error)
        assert error.error_code == "CONFIG_FILE_NOT_FOUND"
        assert error.config_path == config_path
        assert error.details["config_path"] == config_path
    
    def test_config_file_corrupted_error(self):
        """测试配置文件损坏错误"""
        config_path = "/test/config.toml"
        parse_error = "Invalid TOML format"
        
        error = ConfigFileCorruptedError(config_path, parse_error)
        
        assert "配置文件格式错误" in str(error)
        assert config_path in str(error)
        assert parse_error in str(error)
        assert error.error_code == "CONFIG_FILE_CORRUPTED"
        assert error.details["parse_error"] == parse_error
    
    def test_config_file_corrupted_error_without_parse_error(self):
        """测试不带解析错误的配置文件损坏错误"""
        config_path = "/test/config.toml"
        error = ConfigFileCorruptedError(config_path)
        
        assert "配置文件格式错误" in str(error)
        assert config_path in str(error)
        assert "parse_error" not in error.details
    
    def test_config_permission_error(self):
        """测试配置文件权限错误"""
        config_path = "/restricted/config.toml"
        operation = "写入"
        
        error = ConfigPermissionError(config_path, operation)
        
        assert f"无法{operation}" in str(error)
        assert config_path in str(error)
        assert error.error_code == "CONFIG_PERMISSION_ERROR"
        assert error.details["operation"] == operation
    
    def test_config_permission_error_default_operation(self):
        """测试默认操作的配置权限错误"""
        config_path = "/restricted/config.toml"
        error = ConfigPermissionError(config_path)
        
        assert "无法访问" in str(error)
        assert error.details["operation"] == "访问"


class TestProxyErrors:
    """测试代理相关异常"""
    
    def test_proxy_not_found_error(self):
        """测试代理未找到错误"""
        proxy_name = "nonexistent-proxy"
        error = ProxyNotFoundError(proxy_name)
        
        assert f"代理服务器不存在: {proxy_name}" in str(error)
        assert error.error_code == "PROXY_NOT_FOUND"
        assert error.proxy_name == proxy_name
        assert error.details["proxy_name"] == proxy_name
    
    def test_duplicate_proxy_error(self):
        """测试重复代理错误"""
        proxy_name = "existing-proxy"
        error = DuplicateProxyError(proxy_name)
        
        assert f"代理服务器已存在: {proxy_name}" in str(error)
        assert error.error_code == "DUPLICATE_PROXY"
        assert error.proxy_name == proxy_name
        assert error.details["proxy_name"] == proxy_name
    
    def test_proxy_connection_error_basic(self):
        """测试基础代理连接错误"""
        proxy_name = "test-proxy"
        url = "https://api.example.com"
        
        error = ProxyConnectionError(proxy_name, url)
        
        assert f"无法连接到代理服务器 '{proxy_name}'" in str(error)
        assert url in str(error)
        assert error.error_code == "PROXY_CONNECTION_ERROR"
        assert error.proxy_name == proxy_name
        assert error.details["proxy_name"] == proxy_name
        assert error.url == url
    
    def test_proxy_connection_error_with_reason(self):
        """测试带原因的代理连接错误"""
        proxy_name = "test-proxy"
        url = "https://api.example.com"
        reason = "Connection timeout"
        
        error = ProxyConnectionError(proxy_name, url, reason)
        
        assert reason in str(error)
        assert error.details["proxy_name"] == proxy_name


class TestValidationError:
    """测试验证异常"""
    
    def test_validation_error_basic(self):
        """测试基础验证错误"""
        message = "Validation failed"
        error = ValidationError(message)
        
        assert str(error) == message
        assert error.error_code == "VALIDATION_ERROR"
        assert error.field is None
        assert error.value is None
    
    def test_validation_error_with_field_and_value(self):
        """测试带字段和值的验证错误"""
        message = "Invalid field value"
        field = "api_key"
        value = "invalid_key"
        
        error = ValidationError(message, field=field, value=value)
        
        assert error.field == field
        assert error.value == value
        assert error.details["field"] == field
        assert error.details["value"] == str(value)


class TestNetworkErrors:
    """测试网络相关异常"""
    
    def test_network_error_basic(self):
        """测试基础网络错误"""
        message = "Network operation failed"
        error = NetworkError(message)
        
        assert str(error) == message
        assert error.error_code == "NETWORK_ERROR"
        assert error.url is None
        assert error.status_code is None
        assert error.timeout is False
    
    def test_network_error_with_details(self):
        """测试带详情的网络错误"""
        message = "Request failed"
        url = "https://api.example.com"
        status_code = 404
        timeout = True
        
        error = NetworkError(
            message=message,
            url=url,
            status_code=status_code,
            timeout=timeout
        )
        
        assert error.url == url
        assert error.status_code == status_code
        assert error.timeout == timeout
        assert error.details["url"] == url
        assert error.details["status_code"] == status_code
        assert error.details["timeout"] is True
    
    def test_api_key_error_default(self):
        """测试默认API密钥错误"""
        error = APIKeyError()
        
        assert "API密钥无效或已过期" in str(error)
        assert error.error_code == "API_KEY_ERROR"
    
    def test_api_key_error_custom_message(self):
        """测试自定义消息的API密钥错误"""
        custom_message = "API key is too short"
        error = APIKeyError(custom_message)
        
        assert str(error) == custom_message
        assert error.error_code == "API_KEY_ERROR"


class TestOperationErrors:
    """测试操作异常"""
    
    def test_operation_error_basic(self):
        """测试基础操作错误"""
        message = "Operation failed"
        error = OperationError(message)
        
        assert str(error) == message
        assert error.error_code == "OPERATION_ERROR"
        assert error.operation is None
        assert error.target is None
    
    def test_operation_error_with_details(self):
        """测试带详情的操作错误"""
        message = "Delete operation failed"
        operation = "delete"
        target = "proxy-1"
        
        error = OperationError(
            message=message,
            operation=operation,
            target=target
        )
        
        assert error.operation == operation
        assert error.target == target
        assert error.details["operation"] == operation
        assert error.details["target"] == target
    
    def test_export_error(self):
        """测试导出错误"""
        message = "Export failed"
        format_type = "bash"
        
        error = ExportError(message, format_type)
        
        assert str(error) == message
        assert error.error_code == "EXPORT_ERROR"
        assert error.operation == "export"
        assert error.format_type == format_type
        assert error.details["format_type"] == format_type
    
    def test_import_error(self):
        """测试导入错误"""
        message = "Import failed"
        source = "/path/to/file.json"
        
        error = ImportError(message, source)
        
        assert str(error) == message
        assert error.error_code == "IMPORT_ERROR"
        assert error.operation == "import"
        assert error.source == source
        assert error.details["source"] == source


class TestSystemErrors:
    """测试系统异常"""
    
    def test_system_error_basic(self):
        """测试基础系统错误"""
        message = "System operation failed"
        error = SystemError(message)
        
        assert str(error) == message
        assert error.error_code == "SYSTEM_ERROR"
        assert error.system_error is None
    
    def test_system_error_with_system_error(self):
        """测试带系统错误的系统异常"""
        message = "System operation failed"
        system_error = OSError("Permission denied")
        
        error = SystemError(message, system_error)
        
        assert error.system_error == system_error
        assert error.details["system_error"] == str(system_error)
        assert error.details["system_error_type"] == "OSError"
    
    def test_disk_space_error_basic(self):
        """测试基础磁盘空间错误"""
        path = "/tmp"
        error = DiskSpaceError(path)
        
        assert f"磁盘空间不足: {path}" in str(error)
        assert error.error_code == "DISK_SPACE_ERROR"
        assert error.path == path
        assert error.required_space is None
        assert error.details["path"] == path
    
    def test_disk_space_error_with_required_space(self):
        """测试带所需空间的磁盘空间错误"""
        path = "/tmp"
        required_space = 1024 * 1024  # 1MB
        
        error = DiskSpaceError(path, required_space)
        
        assert f"需要 {required_space} 字节" in str(error)
        assert error.required_space == required_space
        assert error.details["required_space"] == required_space
    
    def test_permission_error_default_operation(self):
        """测试默认操作的权限错误"""
        path = "/restricted/file"
        error = PermissionError(path)
        
        assert "无法访问" in str(error)
        assert path in str(error)
        assert error.error_code == "PERMISSION_ERROR"
        assert error.path == path
        assert error.operation == "访问"
        assert error.details["operation"] == "访问"
    
    def test_permission_error_custom_operation(self):
        """测试自定义操作的权限错误"""
        path = "/restricted/file"
        operation = "删除"
        
        error = PermissionError(path, operation)
        
        assert f"无法{operation}" in str(error)
        assert error.operation == operation
        assert error.details["operation"] == operation


class TestCriticalError:
    """测试严重异常"""
    
    def test_critical_error_basic(self):
        """测试基础严重错误"""
        message = "Critical system failure"
        error = CriticalError(message)
        
        assert str(error) == message
        assert error.error_code == "CRITICAL_ERROR"
        assert error.cause is None
    
    def test_critical_error_with_cause(self):
        """测试带原因的严重错误"""
        message = "Critical system failure"
        cause = RuntimeError("Memory corruption detected")
        
        error = CriticalError(message, cause)
        
        assert error.cause == cause
        assert error.details["cause"] == str(cause)
        assert error.details["cause_type"] == "RuntimeError"


class TestErrorCodes:
    """测试错误代码常量"""
    
    def test_error_codes_constants(self):
        """测试错误代码常量的存在"""
        # 配置相关
        assert hasattr(ErrorCodes, 'CONFIG_FILE_NOT_FOUND')
        assert hasattr(ErrorCodes, 'CONFIG_FILE_CORRUPTED')
        assert hasattr(ErrorCodes, 'CONFIG_PERMISSION_ERROR')
        
        # 代理相关
        assert hasattr(ErrorCodes, 'PROXY_NOT_FOUND')
        assert hasattr(ErrorCodes, 'DUPLICATE_PROXY')
        assert hasattr(ErrorCodes, 'PROXY_CONNECTION_ERROR')
        
        # 验证相关
        assert hasattr(ErrorCodes, 'VALIDATION_ERROR')
        
        # 网络相关
        assert hasattr(ErrorCodes, 'NETWORK_ERROR')
        assert hasattr(ErrorCodes, 'API_KEY_ERROR')
        
        # 操作相关
        assert hasattr(ErrorCodes, 'OPERATION_ERROR')
        assert hasattr(ErrorCodes, 'EXPORT_ERROR')
        assert hasattr(ErrorCodes, 'IMPORT_ERROR')
        
        # 系统相关
        assert hasattr(ErrorCodes, 'SYSTEM_ERROR')
        assert hasattr(ErrorCodes, 'DISK_SPACE_ERROR')
        assert hasattr(ErrorCodes, 'PERMISSION_ERROR')
        
        # 严重错误
        assert hasattr(ErrorCodes, 'CRITICAL_ERROR')
    
    def test_error_codes_values(self):
        """测试错误代码的值"""
        assert ErrorCodes.CONFIG_FILE_NOT_FOUND == "CONFIG_FILE_NOT_FOUND"
        assert ErrorCodes.PROXY_NOT_FOUND == "PROXY_NOT_FOUND"
        assert ErrorCodes.VALIDATION_ERROR == "VALIDATION_ERROR"
        assert ErrorCodes.CRITICAL_ERROR == "CRITICAL_ERROR"


class TestExceptionCategories:
    """测试异常分类"""
    
    def test_exception_categories_structure(self):
        """测试异常分类结构"""
        assert isinstance(EXCEPTION_CATEGORIES, dict)
        
        expected_categories = [
            "config", "proxy", "validation", "network", 
            "operation", "system", "critical"
        ]
        
        for category in expected_categories:
            assert category in EXCEPTION_CATEGORIES
            assert isinstance(EXCEPTION_CATEGORIES[category], list)
    
    def test_config_category(self):
        """测试配置异常分类"""
        config_exceptions = EXCEPTION_CATEGORIES["config"]
        
        assert ConfigError in config_exceptions
        assert ConfigFileNotFoundError in config_exceptions
        assert ConfigFileCorruptedError in config_exceptions
        assert ConfigPermissionError in config_exceptions
    
    def test_proxy_category(self):
        """测试代理异常分类"""
        proxy_exceptions = EXCEPTION_CATEGORIES["proxy"]
        
        assert ProxyNotFoundError in proxy_exceptions
        assert DuplicateProxyError in proxy_exceptions
        assert ProxyConnectionError in proxy_exceptions
    
    def test_network_category(self):
        """测试网络异常分类"""
        network_exceptions = EXCEPTION_CATEGORIES["network"]
        
        assert NetworkError in network_exceptions
        assert APIKeyError in network_exceptions
        assert ProxyConnectionError in network_exceptions
    
    def test_critical_category(self):
        """测试严重异常分类"""
        critical_exceptions = EXCEPTION_CATEGORIES["critical"]
        
        assert CriticalError in critical_exceptions


class TestErrorUtilityFunctions:
    """测试异常工具函数"""
    
    def test_is_recoverable_error_critical_errors(self):
        """测试严重错误的可恢复性判断"""
        critical_error = CriticalError("Critical failure")
        system_error = SystemError("System failure")
        
        assert is_recoverable_error(critical_error) is False
        assert is_recoverable_error(system_error) is False
    
    def test_is_recoverable_error_network_errors(self):
        """测试网络错误的可恢复性判断"""
        network_error = NetworkError("Connection failed")
        proxy_connection_error = ProxyConnectionError("test-proxy", "https://api.example.com")
        
        assert is_recoverable_error(network_error) is True
        assert is_recoverable_error(proxy_connection_error) is True
    
    def test_is_recoverable_error_config_errors(self):
        """测试配置错误的可恢复性判断"""
        config_not_found = ConfigFileNotFoundError("/path/to/config.toml")
        config_corrupted = ConfigFileCorruptedError("/path/to/config.toml")
        config_permission = ConfigPermissionError("/path/to/config.toml")
        
        assert is_recoverable_error(config_not_found) is True
        assert is_recoverable_error(config_corrupted) is False
        assert is_recoverable_error(config_permission) is False
    
    def test_is_recoverable_error_validation_errors(self):
        """测试验证错误的可恢复性判断"""
        validation_error = ValidationError("Invalid input")
        
        assert is_recoverable_error(validation_error) is True
    
    def test_is_recoverable_error_proxy_errors(self):
        """测试代理错误的可恢复性判断"""
        proxy_not_found = ProxyNotFoundError("test-proxy")
        duplicate_proxy = DuplicateProxyError("test-proxy")
        
        assert is_recoverable_error(proxy_not_found) is True
        assert is_recoverable_error(duplicate_proxy) is True
    
    def test_is_recoverable_error_unknown_error(self):
        """测试未知错误的可恢复性判断"""
        unknown_error = ValueError("Unknown error")
        
        # 默认认为可恢复
        assert is_recoverable_error(unknown_error) is True
    
    def test_get_error_category_known_errors(self):
        """测试已知错误的分类获取"""
        config_error = ConfigError("Config failed")
        proxy_error = ProxyNotFoundError("test-proxy")
        validation_error = ValidationError("Validation failed")
        network_error = NetworkError("Network failed")
        operation_error = OperationError("Operation failed")
        system_error = SystemError("System failed")
        critical_error = CriticalError("Critical failed")
        
        assert get_error_category(config_error) == "config"
        assert get_error_category(proxy_error) == "proxy"
        assert get_error_category(validation_error) == "validation"
        assert get_error_category(network_error) == "network"
        assert get_error_category(operation_error) == "operation"
        assert get_error_category(system_error) == "system"
        assert get_error_category(critical_error) == "critical"
    
    def test_get_error_category_unknown_error(self):
        """测试未知错误的分类获取"""
        unknown_error = ValueError("Unknown error")
        
        assert get_error_category(unknown_error) == "unknown"
    
    def test_get_error_category_inheritance(self):
        """测试继承关系的错误分类"""
        # ConfigFileNotFoundError 继承自 ConfigError
        config_file_error = ConfigFileNotFoundError("/path/to/config.toml")
        
        # 应该被归类为配置错误
        assert get_error_category(config_file_error) == "config"
        
        # ProxyConnectionError 在多个分类中
        proxy_connection_error = ProxyConnectionError("test-proxy", "https://api.example.com")
        
        # 应该返回第一个匹配的分类
        category = get_error_category(proxy_connection_error)
        assert category in ["proxy", "network"]


class TestErrorInheritanceChain:
    """测试异常继承链"""
    
    def test_all_errors_inherit_from_base(self):
        """测试所有异常都继承自基础异常"""
        error_classes = [
            ConfigError, ConfigFileNotFoundError, ConfigFileCorruptedError, ConfigPermissionError,
            ProxyNotFoundError, DuplicateProxyError, ProxyConnectionError,
            ValidationError,
            NetworkError, APIKeyError,
            OperationError, ExportError, ImportError,
            SystemError, DiskSpaceError, PermissionError,
            CriticalError
        ]
        
        for error_class in error_classes:
            assert issubclass(error_class, ClaudeWarpError)
    
    def test_specific_inheritance_chains(self):
        """测试特定的继承链"""
        # 配置错误继承链
        assert issubclass(ConfigFileNotFoundError, ConfigError)
        assert issubclass(ConfigFileCorruptedError, ConfigError)
        assert issubclass(ConfigPermissionError, ConfigError)
        
        # 网络错误继承链
        assert issubclass(APIKeyError, NetworkError)
        assert issubclass(ProxyConnectionError, NetworkError)
        
        # 操作错误继承链
        assert issubclass(ExportError, OperationError)
        assert issubclass(ImportError, OperationError)
        
        # 系统错误继承链
        assert issubclass(DiskSpaceError, SystemError)
        assert issubclass(PermissionError, SystemError)


class TestErrorEdgeCases:
    """测试异常边界情况"""
    
    def test_error_with_none_values(self):
        """测试带None值的异常"""
        error = ClaudeWarpError("Test", error_code=None, details=None)
        
        assert error.error_code == "ClaudeWarpError"  # 应该使用默认值
        assert error.details == {}  # 应该使用默认空字典
    
    def test_error_with_empty_details(self):
        """测试带空详情的异常"""
        error = ClaudeWarpError("Test", details={})
        
        error_dict = error.to_dict()
        assert error_dict["details"] == {}
    
    def test_error_with_complex_details(self):
        """测试带复杂详情的异常"""
        complex_details = {
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "number": 42,
            "boolean": True,
            "none_value": None
        }
        
        error = ClaudeWarpError("Test", details=complex_details)
        
        assert error.details == complex_details
        
        # 测试字典转换
        error_dict = error.to_dict()
        assert error_dict["details"] == complex_details
    
    def test_error_str_and_repr_consistency(self):
        """测试异常的字符串表示一致性"""
        errors = [
            ClaudeWarpError("Test message"),
            ConfigError("Config failed", "/path/to/config"),
            ProxyNotFoundError("test-proxy"),
            ValidationError("Validation failed", field="test_field", value="test_value"),
            NetworkError("Network failed", url="https://example.com", status_code=404)
        ]
        
        for error in errors:
            # str() 应该返回可读的错误消息
            str_repr = str(error)
            assert isinstance(str_repr, str)
            assert len(str_repr) > 0
            
            # repr() 应该包含类名和关键信息
            repr_str = repr(error)
            assert error.__class__.__name__ in repr_str
            assert str(error) in repr_str


# 测试辅助函数
def create_all_error_types() -> List[ClaudeWarpError]:
    """创建所有类型的测试异常"""
    return [
        ClaudeWarpError("Base error"),
        ConfigError("Config error"),
        ConfigFileNotFoundError("/path/to/config.toml"),
        ConfigFileCorruptedError("/path/to/config.toml", "Parse error"),
        ConfigPermissionError("/path/to/config.toml", "read"),
        ProxyNotFoundError("test-proxy"),
        DuplicateProxyError("test-proxy"),
        ProxyConnectionError("test-proxy", "https://api.example.com", "Timeout"),
        ValidationError("Invalid data", field="test_field", value="test_value"),
        NetworkError("Network error", url="https://api.example.com", status_code=500),
        APIKeyError("Invalid API key"),
        OperationError("Operation failed", operation="delete", target="test-proxy"),
        ExportError("Export failed", format_type="bash"),
        ImportError("Import failed", source="/path/to/file.json"),
        SystemError("System error", OSError("Permission denied")),
        DiskSpaceError("/tmp", 1024),
        PermissionError("/restricted/file", "write"),
        CriticalError("Critical error", RuntimeError("System failure"))
    ]


class TestAllErrorTypes:
    """测试所有异常类型的基本功能"""
    
    def test_all_errors_can_be_created(self):
        """测试所有异常类型都可以正常创建"""
        errors = create_all_error_types()
        
        assert len(errors) == 18  # 确保测试了所有异常类型
        
        for error in errors:
            assert isinstance(error, ClaudeWarpError)
            assert isinstance(str(error), str)
            assert len(str(error)) > 0
            assert isinstance(error.error_code, str)
            assert len(error.error_code) > 0
            assert isinstance(error.details, dict)
    
    def test_all_errors_to_dict(self):
        """测试所有异常类型的字典转换"""
        errors = create_all_error_types()
        
        for error in errors:
            error_dict = error.to_dict()
            
            assert isinstance(error_dict, dict)
            assert "error_type" in error_dict
            assert "error_code" in error_dict
            assert "message" in error_dict
            assert "details" in error_dict
            
            assert error_dict["error_type"] == error.__class__.__name__
            assert error_dict["error_code"] == error.error_code
            assert error_dict["message"] == error.message
            assert error_dict["details"] == error.details
    
    def test_all_errors_inheritance(self):
        """测试所有异常类型的继承关系"""
        errors = create_all_error_types()
        
        for error in errors:
            assert isinstance(error, ClaudeWarpError)
            assert isinstance(error, Exception)


# Pytest fixtures
@pytest.fixture
def sample_errors():
    """提供示例异常的fixture"""
    return create_all_error_types()


@pytest.fixture
def config_error():
    """提供配置错误的fixture"""
    return ConfigError("Test config error", "/test/config.toml")


@pytest.fixture
def proxy_error():
    """提供代理错误的fixture"""
    return ProxyNotFoundError("test-proxy")


@pytest.fixture
def network_error():
    """提供网络错误的fixture"""
    return NetworkError(
        "Connection failed", 
        url="https://api.example.com", 
        status_code=500, 
        timeout=True
    )