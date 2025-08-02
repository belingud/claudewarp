"""
异常类测试
测试所有自定义异常类的创建、属性和工具函数
"""


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
    """基础异常类测试"""

    def test_basic_error_creation(self):
        """测试基础异常创建"""
        error = ClaudeWarpError("测试错误")
        
        assert str(error) == "测试错误"
        assert error.message == "测试错误"
        assert error.error_code == "ClaudeWarpError"
        assert error.details == {}

    def test_error_with_code_and_details(self):
        """测试包含错误代码和详情的异常"""
        details = {"key": "value", "number": 123}
        error = ClaudeWarpError(
            message="详细错误",
            error_code="CUSTOM_ERROR",
            details=details
        )
        
        assert error.message == "详细错误"
        assert error.error_code == "CUSTOM_ERROR"
        assert error.details == details

    def test_error_repr(self):
        """测试异常的字符串表示"""
        error = ClaudeWarpError("测试", error_code="TEST_ERROR")
        repr_str = repr(error)
        
        assert "ClaudeWarpError" in repr_str
        assert "测试" in repr_str
        assert "TEST_ERROR" in repr_str

    def test_error_to_dict(self):
        """测试异常转换为字典"""
        error = ClaudeWarpError(
            message="测试错误",
            error_code="TEST_ERROR",
            details={"context": "test"}
        )
        
        error_dict = error.to_dict()
        
        assert error_dict["error_type"] == "ClaudeWarpError"
        assert error_dict["error_code"] == "TEST_ERROR"
        assert error_dict["message"] == "测试错误"
        assert error_dict["details"]["context"] == "test"


class TestConfigExceptions:
    """配置相关异常测试"""

    def test_config_error(self):
        """测试基础配置错误"""
        error = ConfigError("配置错误", config_path="/path/to/config")
        
        assert str(error) == "配置错误"
        assert error.config_path == "/path/to/config"
        assert error.details["config_path"] == "/path/to/config"

    def test_config_file_not_found_error(self):
        """测试配置文件未找到错误"""
        config_path = "/path/to/missing/config.toml"
        error = ConfigFileNotFoundError(config_path)
        
        assert "配置文件不存在" in str(error)
        assert config_path in str(error)
        assert error.config_path == config_path
        assert error.error_code == "CONFIG_FILE_NOT_FOUND"

    def test_config_file_corrupted_error(self):
        """测试配置文件损坏错误"""
        config_path = "/path/to/corrupted.toml"
        parse_error = "Invalid TOML syntax"
        
        error = ConfigFileCorruptedError(config_path, parse_error)
        
        assert "配置文件格式错误" in str(error)
        assert config_path in str(error)
        assert parse_error in str(error)
        assert error.config_path == config_path
        assert error.error_code == "CONFIG_FILE_CORRUPTED"
        assert error.details["parse_error"] == parse_error

    def test_config_file_corrupted_error_without_parse_error(self):
        """测试没有解析错误详情的配置文件损坏错误"""
        config_path = "/path/to/corrupted.toml"
        error = ConfigFileCorruptedError(config_path)
        
        assert config_path in str(error)
        assert "parse_error" not in error.details

    def test_config_permission_error(self):
        """测试配置文件权限错误"""
        config_path = "/path/to/readonly.toml"
        operation = "写入"
        
        error = ConfigPermissionError(config_path, operation)
        
        assert "权限不足" in str(error)
        assert operation in str(error)
        assert config_path in str(error)
        assert error.config_path == config_path
        assert error.error_code == "CONFIG_PERMISSION_ERROR"
        assert error.details["operation"] == operation

    def test_config_permission_error_default_operation(self):
        """测试默认操作的配置权限错误"""
        error = ConfigPermissionError("/path/config")
        assert "访问" in str(error)
        assert error.details["operation"] == "访问"


class TestProxyExceptions:
    """代理相关异常测试"""

    def test_proxy_not_found_error(self):
        """测试代理未找到错误"""
        proxy_name = "missing-proxy"
        error = ProxyNotFoundError(proxy_name)
        
        assert "代理服务器不存在" in str(error)
        assert proxy_name in str(error)
        assert error.proxy_name == proxy_name
        assert error.error_code == "PROXY_NOT_FOUND"
        assert error.details["proxy_name"] == proxy_name

    def test_duplicate_proxy_error(self):
        """测试重复代理错误"""
        proxy_name = "existing-proxy"
        error = DuplicateProxyError(proxy_name)
        
        assert "代理服务器已存在" in str(error)
        assert proxy_name in str(error)
        assert error.proxy_name == proxy_name
        assert error.error_code == "DUPLICATE_PROXY"
        assert error.details["proxy_name"] == proxy_name

    def test_proxy_connection_error(self):
        """测试代理连接错误"""
        proxy_name = "test-proxy"
        url = "https://api.test.com"
        reason = "Connection timeout"
        
        error = ProxyConnectionError(proxy_name, url, reason)
        
        assert proxy_name in str(error)
        assert url in str(error)
        assert reason in str(error)
        assert error.proxy_name == proxy_name
        assert error.url == url
        assert error.error_code == "PROXY_CONNECTION_ERROR"
        assert error.details["proxy_name"] == proxy_name

    def test_proxy_connection_error_without_reason(self):
        """测试没有原因的代理连接错误"""
        error = ProxyConnectionError("test-proxy", "https://api.test.com")
        assert "test-proxy" in str(error)
        assert "https://api.test.com" in str(error)


class TestValidationException:
    """验证异常测试"""

    def test_validation_error_basic(self):
        """测试基础验证错误"""
        error = ValidationError("数据验证失败")
        
        assert str(error) == "数据验证失败"
        assert error.error_code == "VALIDATION_ERROR"
        assert error.field is None
        assert error.value is None

    def test_validation_error_with_field_and_value(self):
        """测试包含字段和值的验证错误"""
        error = ValidationError("字段验证失败", field="name", value="invalid_name")
        
        assert str(error) == "字段验证失败"
        assert error.field == "name"
        assert error.value == "invalid_name"
        assert error.details["field"] == "name"
        assert error.details["value"] == "invalid_name"

    def test_validation_error_with_none_value(self):
        """测试值为None的验证错误"""
        error = ValidationError("空值错误", field="required_field", value=None)
        
        assert error.field == "required_field"
        assert error.value is None
        # value为None时不应该添加到details中
        assert "value" not in error.details


class TestNetworkExceptions:
    """网络异常测试"""

    def test_network_error_basic(self):
        """测试基础网络错误"""
        error = NetworkError("网络连接失败")
        
        assert str(error) == "网络连接失败"
        assert error.error_code == "NETWORK_ERROR"
        assert error.url is None
        assert error.status_code is None
        assert error.timeout is False

    def test_network_error_with_details(self):
        """测试包含详细信息的网络错误"""
        error = NetworkError(
            message="HTTP请求失败",
            url="https://api.example.com",
            status_code=404,
            timeout=True
        )
        
        assert error.url == "https://api.example.com"
        assert error.status_code == 404
        assert error.timeout is True
        assert error.details["url"] == "https://api.example.com"
        assert error.details["status_code"] == 404
        assert error.details["timeout"] is True

    def test_api_key_error(self):
        """测试API密钥错误"""
        error = APIKeyError()
        
        assert "API密钥无效或已过期" in str(error)
        assert error.error_code == "API_KEY_ERROR"

    def test_api_key_error_custom_message(self):
        """测试自定义消息的API密钥错误"""
        custom_message = "API密钥格式错误"
        error = APIKeyError(custom_message)
        
        assert str(error) == custom_message
        assert error.error_code == "API_KEY_ERROR"


class TestOperationExceptions:
    """操作异常测试"""

    def test_operation_error_basic(self):
        """测试基础操作错误"""
        error = OperationError("操作失败")
        
        assert str(error) == "操作失败"
        assert error.error_code == "OPERATION_ERROR"
        assert error.operation is None
        assert error.target is None

    def test_operation_error_with_operation_and_target(self):
        """测试包含操作和目标的操作错误"""
        error = OperationError(
            message="删除操作失败",
            operation="delete",
            target="test-file.txt"
        )
        
        assert error.operation == "delete"
        assert error.target == "test-file.txt"
        assert error.details["operation"] == "delete"
        assert error.details["target"] == "test-file.txt"

    def test_export_error(self):
        """测试导出错误"""
        error = ExportError("导出失败", format_type="json")
        
        assert str(error) == "导出失败"
        assert error.error_code == "EXPORT_ERROR"
        assert error.operation == "export"
        assert error.format_type == "json"
        assert error.details["format_type"] == "json"

    def test_export_error_without_format(self):
        """测试没有格式类型的导出错误"""
        error = ExportError("导出失败")
        assert error.format_type is None
        assert "format_type" not in error.details

    def test_import_error(self):
        """测试导入错误"""
        error = ImportError("导入失败", source="file.json")
        
        assert str(error) == "导入失败"
        assert error.error_code == "IMPORT_ERROR"
        assert error.operation == "import"
        assert error.source == "file.json"
        assert error.details["source"] == "file.json"


class TestSystemExceptions:
    """系统异常测试"""

    def test_system_error_basic(self):
        """测试基础系统错误"""
        error = SystemError("系统错误")
        
        assert str(error) == "系统错误"
        assert error.error_code == "SYSTEM_ERROR"
        assert error.system_error is None

    def test_system_error_with_system_error(self):
        """测试包含系统错误的系统异常"""
        original_error = OSError("磁盘空间不足")
        error = SystemError("文件操作失败", system_error=original_error)
        
        assert error.system_error == original_error
        assert error.details["system_error"] == str(original_error)
        assert error.details["system_error_type"] == "OSError"

    def test_disk_space_error(self):
        """测试磁盘空间错误"""
        path = "/tmp"
        required_space = 1024 * 1024  # 1MB
        
        error = DiskSpaceError(path, required_space)
        
        assert path in str(error)
        assert str(required_space) in str(error)
        assert error.path == path
        assert error.required_space == required_space
        assert error.error_code == "DISK_SPACE_ERROR"
        assert error.details["path"] == path
        assert error.details["required_space"] == required_space

    def test_disk_space_error_without_required_space(self):
        """测试没有所需空间信息的磁盘空间错误"""
        error = DiskSpaceError("/tmp")
        
        assert error.required_space is None
        assert "required_space" not in error.details

    def test_permission_error(self):
        """测试权限错误"""
        path = "/etc/passwd"
        operation = "写入"
        
        error = PermissionError(path, operation)
        
        assert path in str(error)
        assert operation in str(error)
        assert error.path == path
        assert error.operation == operation
        assert error.error_code == "PERMISSION_ERROR"
        assert error.details["path"] == path
        assert error.details["operation"] == operation

    def test_permission_error_default_operation(self):
        """测试默认操作的权限错误"""
        error = PermissionError("/path")
        
        assert "访问" in str(error)
        assert error.operation == "访问"


class TestCriticalError:
    """严重错误测试"""

    def test_critical_error_basic(self):
        """测试基础严重错误"""
        error = CriticalError("严重系统错误")
        
        assert str(error) == "严重系统错误"
        assert error.error_code == "CRITICAL_ERROR"
        assert error.cause is None

    def test_critical_error_with_cause(self):
        """测试包含原因的严重错误"""
        cause = RuntimeError("内存溢出")
        error = CriticalError("系统崩溃", cause=cause)
        
        assert error.cause == cause
        assert error.details["cause"] == str(cause)
        assert error.details["cause_type"] == "RuntimeError"


class TestErrorCodes:
    """错误代码常量测试"""

    def test_error_codes_exist(self):
        """测试错误代码常量存在"""
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
        assert ErrorCodes.NETWORK_ERROR == "NETWORK_ERROR"
        assert ErrorCodes.CRITICAL_ERROR == "CRITICAL_ERROR"


class TestExceptionCategories:
    """异常分类测试"""

    def test_exception_categories_structure(self):
        """测试异常分类结构"""
        expected_categories = [
            "config", "proxy", "validation", "network", 
            "operation", "system", "critical"
        ]
        
        for category in expected_categories:
            assert category in EXCEPTION_CATEGORIES
            assert isinstance(EXCEPTION_CATEGORIES[category], list)
            assert len(EXCEPTION_CATEGORIES[category]) > 0

    def test_config_category_exceptions(self):
        """测试配置类异常分类"""
        config_exceptions = EXCEPTION_CATEGORIES["config"]
        
        assert ConfigError in config_exceptions
        assert ConfigFileNotFoundError in config_exceptions
        assert ConfigFileCorruptedError in config_exceptions
        assert ConfigPermissionError in config_exceptions

    def test_proxy_category_exceptions(self):
        """测试代理类异常分类"""
        proxy_exceptions = EXCEPTION_CATEGORIES["proxy"]
        
        assert ProxyNotFoundError in proxy_exceptions
        assert DuplicateProxyError in proxy_exceptions
        assert ProxyConnectionError in proxy_exceptions

    def test_validation_category_exceptions(self):
        """测试验证类异常分类"""
        validation_exceptions = EXCEPTION_CATEGORIES["validation"]
        assert ValidationError in validation_exceptions

    def test_network_category_exceptions(self):
        """测试网络类异常分类"""
        network_exceptions = EXCEPTION_CATEGORIES["network"]
        
        assert NetworkError in network_exceptions
        assert APIKeyError in network_exceptions
        assert ProxyConnectionError in network_exceptions

    def test_operation_category_exceptions(self):
        """测试操作类异常分类"""
        operation_exceptions = EXCEPTION_CATEGORIES["operation"]
        
        assert OperationError in operation_exceptions
        assert ExportError in operation_exceptions
        assert ImportError in operation_exceptions

    def test_system_category_exceptions(self):
        """测试系统类异常分类"""
        system_exceptions = EXCEPTION_CATEGORIES["system"]
        
        assert SystemError in system_exceptions
        assert DiskSpaceError in system_exceptions
        assert PermissionError in system_exceptions

    def test_critical_category_exceptions(self):
        """测试严重错误类异常分类"""
        critical_exceptions = EXCEPTION_CATEGORIES["critical"]
        assert CriticalError in critical_exceptions


class TestUtilityFunctions:
    """工具函数测试"""

    def test_is_recoverable_error_recoverable_errors(self):
        """测试可恢复错误判断"""
        recoverable_errors = [
            NetworkError("网络错误"),
            ProxyConnectionError("proxy", "url"),
            ConfigFileNotFoundError("/path"),
            ValidationError("验证错误"),
            ProxyNotFoundError("proxy"),
            DuplicateProxyError("proxy"),
        ]
        
        for error in recoverable_errors:
            assert is_recoverable_error(error) is True

    def test_is_recoverable_error_non_recoverable_errors(self):
        """测试不可恢复错误判断"""
        non_recoverable_errors = [
            CriticalError("严重错误"),
            SystemError("系统错误"),
            ConfigFileCorruptedError("/path", "parse error"),
            ConfigPermissionError("/path"),
        ]
        
        for error in non_recoverable_errors:
            assert is_recoverable_error(error) is False

    def test_is_recoverable_error_unknown_error(self):
        """测试未知错误的可恢复性判断"""
        unknown_error = RuntimeError("未知错误")
        # 默认认为可恢复
        assert is_recoverable_error(unknown_error) is True

    def test_get_error_category_known_errors(self):
        """测试已知错误的分类获取"""
        test_cases = [
            (ConfigError("config"), "config"),
            (ProxyNotFoundError("proxy"), "proxy"),
            (ValidationError("validation"), "validation"),
            (NetworkError("network"), "network"),
            (OperationError("operation"), "operation"),
            (SystemError("system"), "system"),
            (CriticalError("critical"), "critical"),
        ]
        
        for error, expected_category in test_cases:
            assert get_error_category(error) == expected_category

    def test_get_error_category_unknown_error(self):
        """测试未知错误的分类获取"""
        unknown_error = RuntimeError("未知错误")
        assert get_error_category(unknown_error) == "unknown"

    def test_get_error_category_multiple_inheritance(self):
        """测试多重继承异常的分类"""
        # ProxyConnectionError 同时在 proxy 和 network 分类中
        # 应该返回第一个匹配的分类
        error = ProxyConnectionError("proxy", "url")
        category = get_error_category(error)
        # 根据EXCEPTION_CATEGORIES的顺序，应该先匹配到proxy
        assert category in ["proxy", "network"]


class TestExceptionInheritance:
    """异常继承关系测试"""

    def test_all_exceptions_inherit_from_claude_warp_error(self):
        """测试所有异常都继承自ClaudeWarpError"""
        exception_classes = [
            ConfigError, ConfigFileNotFoundError, ConfigFileCorruptedError, ConfigPermissionError,
            ProxyNotFoundError, DuplicateProxyError, ProxyConnectionError,
            ValidationError,
            NetworkError, APIKeyError,
            OperationError, ExportError, ImportError,
            SystemError, DiskSpaceError, PermissionError,
            CriticalError,
        ]
        
        for exc_class in exception_classes:
            assert issubclass(exc_class, ClaudeWarpError)

    def test_specific_inheritance_relationships(self):
        """测试特定的继承关系"""
        # 配置异常继承
        assert issubclass(ConfigFileNotFoundError, ConfigError)
        assert issubclass(ConfigFileCorruptedError, ConfigError)
        assert issubclass(ConfigPermissionError, ConfigError)
        
        # 网络异常继承
        assert issubclass(APIKeyError, NetworkError)
        assert issubclass(ProxyConnectionError, NetworkError)
        
        # 操作异常继承
        assert issubclass(ExportError, OperationError)
        assert issubclass(ImportError, OperationError)
        
        # 系统异常继承
        assert issubclass(DiskSpaceError, SystemError)
        assert issubclass(PermissionError, SystemError)

    def test_exception_instances_are_caught_by_base_class(self):
        """测试异常实例可以被基类捕获"""
        # 测试配置异常可以被ConfigError捕获
        try:
            raise ConfigFileNotFoundError("/path")
        except ConfigError as e:
            assert isinstance(e, ConfigFileNotFoundError)
        
        # 测试网络异常可以被NetworkError捕获
        try:
            raise APIKeyError("Invalid key")
        except NetworkError as e:
            assert isinstance(e, APIKeyError)
        
        # 测试所有异常可以被ClaudeWarpError捕获
        try:
            raise ValidationError("Test error")
        except ClaudeWarpError as e:
            assert isinstance(e, ValidationError)


class TestExceptionEdgeCases:
    """异常边界情况测试"""

    def test_empty_message(self):
        """测试空消息的异常"""
        error = ClaudeWarpError("")
        assert str(error) == ""
        assert error.message == ""

    def test_none_details(self):
        """测试None详情的异常"""
        error = ClaudeWarpError("test", details=None)
        assert error.details == {}

    def test_large_message(self):
        """测试大消息的异常"""
        large_message = "错误" * 1000
        error = ClaudeWarpError(large_message)
        assert error.message == large_message
        assert str(error) == large_message

    def test_unicode_message(self):
        """测试Unicode消息的异常"""
        unicode_message = "错误信息 🚨 emoji test 测试"
        error = ClaudeWarpError(unicode_message)
        assert error.message == unicode_message
        assert str(error) == unicode_message

    def test_complex_details(self):
        """测试复杂详情的异常"""
        complex_details = {
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "unicode": "测试 🎯",
            "number": 42,
            "boolean": True,
            "none": None
        }
        
        error = ClaudeWarpError("test", details=complex_details)
        assert error.details == complex_details
        
        error_dict = error.to_dict()
        assert error_dict["details"] == complex_details