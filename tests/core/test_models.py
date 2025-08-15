"""
数据模型测试
测试 ProxyServer, ProxyConfig, ExportFormat 数据模型的验证逻辑和方法
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from claudewarp.core.models import ProxyServer, ProxyConfig, ExportFormat


class TestProxyServer:
    """ProxyServer 模型测试"""

    def test_valid_proxy_creation(self):
        """测试创建有效的代理服务器"""
        proxy = ProxyServer(
            name="test-proxy",
            base_url="https://api.example.com",
            api_key="sk-1234567890abcdef",
            description="测试代理",
            tags=["test", "primary"],
        )
        
        assert proxy.name == "test-proxy"
        assert str(proxy.base_url) == "https://api.example.com/"  # 自动添加结尾斜杠
        assert proxy.api_key == "sk-1234567890abcdef"
        assert proxy.description == "测试代理"
        assert set(proxy.tags) == {"test", "primary"}  # 使用set比较，因为标签会去重
        assert proxy.is_active is True
        assert proxy.auth_token is None
        assert proxy.api_key_helper is None
        assert proxy.bigmodel is None
        assert proxy.smallmodel is None

    def test_auth_token_creation(self):
        """测试使用认证令牌创建代理"""
        proxy = ProxyServer(
            name="auth-proxy",
            base_url="https://api.example.com",
            auth_token="sk-ant-api03-abcdef123456",
            description="认证代理",
        )
        
        assert proxy.auth_token == "sk-ant-api03-abcdef123456"
        assert proxy.api_key is None
        assert proxy.get_auth_method() == "auth_token"
        assert proxy.get_active_credential() == "sk-ant-api03-abcdef123456"

    def test_api_key_helper_creation(self):
        """测试使用API密钥助手创建代理"""
        proxy = ProxyServer(
            name="helper-proxy",
            base_url="https://api.example.com",
            api_key_helper="echo 'sk-xxx'",
            description="助手代理",
        )
        
        assert proxy.api_key_helper == "echo 'sk-xxx'"
        assert proxy.api_key is None
        assert proxy.auth_token is None
        assert proxy.get_auth_method() == "api_key_helper"
        assert proxy.get_active_credential() == "echo 'sk-xxx'"

    def test_name_validation(self):
        """测试代理名称验证"""
        # 有效名称
        valid_names = ["test", "proxy-1", "proxy_2", "test123", "a"]
        for name in valid_names:
            proxy = ProxyServer(name=name, base_url="https://api.example.com", api_key="sk-test")
            assert proxy.name == name

        # 无效名称 - 空字符串会触发Pydantic的min_length验证
        with pytest.raises(ValidationError):
            ProxyServer(name="", base_url="https://api.example.com", api_key="sk-test")
        
        # 无效名称格式
        invalid_names = ["test proxy", "test@proxy", "test.proxy", "测试代理"]
        for name in invalid_names:
            with pytest.raises(ValidationError, match="代理名称只能包含字母、数字、下划线和横线"):
                ProxyServer(name=name, base_url="https://api.example.com", api_key="sk-test")

    def test_base_url_validation(self):
        """测试基础URL验证"""
        # 有效URL (HttpUrl会标准化URL格式但不一定添加结尾斜杠)
        valid_urls = [
            ("https://api.example.com", "https://api.example.com/"),
            ("http://localhost:8080", "http://localhost:8080/"),
            ("https://192.168.1.1", "https://192.168.1.1/"),
            ("https://api.example.com/", "https://api.example.com/"),
            ("https://api.example.com/v1", "https://api.example.com/v1"),  # 路径不会自动添加斜杠
        ]
        
        for input_url, expected_url in valid_urls:
            proxy = ProxyServer(name="test", base_url=input_url, api_key="sk-test")
            assert str(proxy.base_url) == expected_url

        # 无效URL
        invalid_urls = [
            "api.example.com",  # 缺少协议
            "ftp://api.example.com",  # 不支持的协议
            "",  # 空URL
            "https://",  # 不完整的URL
        ]
        
        for url in invalid_urls:
            with pytest.raises(ValidationError):
                ProxyServer(name="test", base_url=url, api_key="sk-test")

    def test_api_key_validation(self):
        """测试API密钥验证"""
        # 有效API密钥
        valid_keys = ["sk-1234567890abcdef", "sk-a", "very-long-api-key-12345"]
        for key in valid_keys:
            proxy = ProxyServer(name="test", base_url="https://api.example.com", api_key=key)
            assert proxy.api_key == key

        # 无效API密钥 - 长度太短，但需要先提供一个有效的认证方法
        invalid_keys = ["a", "sk"]  # 太短但不为空
        for key in invalid_keys:
            with pytest.raises(ValidationError, match="API Key至少需要3个字符"):
                ProxyServer(name="test", base_url="https://api.example.com", api_key=key)
        
        # 空字符串会触发模型验证器检查"至少有一个认证方法"
        with pytest.raises(ValidationError, match="至少有一个必须存在"):
            ProxyServer(name="test", base_url="https://api.example.com", api_key="")

    def test_auth_token_validation(self):
        """测试认证令牌验证"""
        # 有效认证令牌
        valid_tokens = ["sk-ant-api03-abcdef123456", "token123", "very-long-auth-token"]
        for token in valid_tokens:
            proxy = ProxyServer(name="test", base_url="https://api.example.com", auth_token=token)
            assert proxy.auth_token == token

        # 无效认证令牌 - 长度太短，但需要先提供一个有效的认证方法
        invalid_tokens = ["a", "to"]  # 太短但不为空
        for token in invalid_tokens:
            with pytest.raises(ValidationError, match="Auth令牌至少需要3个字符"):
                ProxyServer(name="test", base_url="https://api.example.com", auth_token=token)
        
        # 空字符串会触发模型验证器检查"至少有一个认证方法"
        with pytest.raises(ValidationError, match="至少有一个必须存在"):
            ProxyServer(name="test", base_url="https://api.example.com", auth_token="")

    def test_tags_validation(self):
        """测试标签验证和去重"""
        # 标签去重和清理
        proxy = ProxyServer(
            name="test",
            base_url="https://api.example.com",
            api_key="sk-test",
            tags=["test", "primary", "test", " secondary ", "primary"]
        )
        
        # 应该去重并清理空格
        assert "test" in proxy.tags
        assert "primary" in proxy.tags
        assert "secondary" in proxy.tags
        assert len(proxy.tags) == 3  # 去重后只有3个

    def test_mutual_exclusive_auth_methods(self):
        """测试互斥的认证方式"""
        # 只有api_key
        proxy1 = ProxyServer(name="test1", base_url="https://api.example.com", api_key="sk-test")
        assert proxy1.api_key == "sk-test"
        assert proxy1.auth_token is None
        assert proxy1.api_key_helper is None

        # 只有auth_token
        proxy2 = ProxyServer(name="test2", base_url="https://api.example.com", auth_token="token-test")
        assert proxy2.auth_token == "token-test"
        assert proxy2.api_key is None
        assert proxy2.api_key_helper is None

        # 只有api_key_helper
        proxy3 = ProxyServer(name="test3", base_url="https://api.example.com", api_key_helper="echo sk-test")
        assert proxy3.api_key_helper == "echo sk-test"
        assert proxy3.api_key is None
        assert proxy3.auth_token is None

        # 同时存在多个认证方式应该报错
        with pytest.raises(ValidationError, match="只能存在一个"):
            ProxyServer(
                name="test",
                base_url="https://api.example.com",
                api_key="sk-test",
                auth_token="token-test"
            )

        # 没有任何认证方式应该报错
        with pytest.raises(ValidationError, match="至少有一个必须存在"):
            ProxyServer(name="test", base_url="https://api.example.com")

    def test_timestamp_auto_update(self):
        """测试时间戳自动更新"""
        before_creation = datetime.now()
        proxy = ProxyServer(name="test", base_url="https://api.example.com", api_key="sk-test")
        after_creation = datetime.now()
        
        created_time = datetime.fromisoformat(proxy.created_at)
        updated_time = datetime.fromisoformat(proxy.updated_at)
        
        assert before_creation <= created_time <= after_creation
        assert before_creation <= updated_time <= after_creation

    def test_get_auth_method(self):
        """测试获取认证方式"""
        proxy_api_key = ProxyServer(name="test1", base_url="https://api.example.com", api_key="sk-test")
        assert proxy_api_key.get_auth_method() == "api_key"

        proxy_auth_token = ProxyServer(name="test2", base_url="https://api.example.com", auth_token="token-test")
        assert proxy_auth_token.get_auth_method() == "auth_token"

        proxy_helper = ProxyServer(name="test3", base_url="https://api.example.com", api_key_helper="echo sk-test")
        assert proxy_helper.get_auth_method() == "api_key_helper"

    def test_get_active_credential(self):
        """测试获取活跃凭据"""
        proxy_api_key = ProxyServer(name="test1", base_url="https://api.example.com", api_key="sk-test")
        assert proxy_api_key.get_active_credential() == "sk-test"

        proxy_auth_token = ProxyServer(name="test2", base_url="https://api.example.com", auth_token="token-test")
        assert proxy_auth_token.get_active_credential() == "token-test"

        proxy_helper = ProxyServer(name="test3", base_url="https://api.example.com", api_key_helper="echo sk-test")
        assert proxy_helper.get_active_credential() == "echo sk-test"


class TestProxyConfig:
    """ProxyConfig 模型测试"""

    def test_empty_config_creation(self):
        """测试创建空配置"""
        config = ProxyConfig()
        
        assert config.version == "1.0"
        assert config.current_proxy is None
        assert config.proxies == {}
        assert config.settings == {}
        assert config.created_at is not None
        assert config.updated_at is not None

    def test_config_with_proxies(self, sample_proxy):
        """测试包含代理的配置"""
        config = ProxyConfig(
            current_proxy="test-proxy",
            proxies={"test-proxy": sample_proxy}
        )
        
        assert config.current_proxy == "test-proxy"
        assert "test-proxy" in config.proxies
        assert config.proxies["test-proxy"] == sample_proxy

    def test_current_proxy_validation(self, sample_proxy):
        """测试当前代理验证"""
        # 有效的当前代理
        config = ProxyConfig(
            current_proxy="test-proxy",
            proxies={"test-proxy": sample_proxy}
        )
        assert config.current_proxy == "test-proxy"

        # 无效的当前代理（不在代理列表中）
        with pytest.raises(ValidationError, match='当前代理 "nonexistent" 不存在于代理列表中'):
            ProxyConfig(
                current_proxy="nonexistent",
                proxies={"test-proxy": sample_proxy}
            )

    def test_proxy_name_consistency_validation(self):
        """测试代理名称一致性验证"""
        proxy = ProxyServer(name="test-proxy", base_url="https://api.example.com", api_key="sk-test")
        
        # 有效：字典key与代理名称一致
        config = ProxyConfig(proxies={"test-proxy": proxy})
        assert "test-proxy" in config.proxies

        # 无效：字典key与代理名称不一致
        with pytest.raises(ValidationError, match="代理名称不一致"):
            ProxyConfig(proxies={"wrong-name": proxy})

    def test_get_current_proxy(self, sample_proxy):
        """测试获取当前代理"""
        config = ProxyConfig(
            current_proxy="test-proxy",
            proxies={"test-proxy": sample_proxy}
        )
        
        current = config.get_current_proxy()
        assert current == sample_proxy

        # 无当前代理
        config_no_current = ProxyConfig(proxies={"test-proxy": sample_proxy})
        assert config_no_current.get_current_proxy() is None

    def test_add_proxy(self):
        """测试添加代理"""
        config = ProxyConfig()
        proxy = ProxyServer(name="new-proxy", base_url="https://api.example.com", api_key="sk-test")
        
        config.add_proxy(proxy)
        
        assert "new-proxy" in config.proxies
        assert config.proxies["new-proxy"] == proxy
        assert config.current_proxy == "new-proxy"  # 第一个代理自动设置为当前

        # 添加第二个代理
        proxy2 = ProxyServer(name="proxy2", base_url="https://api2.example.com", api_key="sk-test2")
        config.add_proxy(proxy2)
        
        assert "proxy2" in config.proxies
        assert config.current_proxy == "new-proxy"  # 当前代理不变

    def test_remove_proxy(self):
        """测试删除代理"""
        proxy1 = ProxyServer(name="proxy1", base_url="https://api1.example.com", api_key="sk-test1")
        proxy2 = ProxyServer(name="proxy2", base_url="https://api2.example.com", api_key="sk-test2")
        
        config = ProxyConfig(
            current_proxy="proxy1",
            proxies={"proxy1": proxy1, "proxy2": proxy2}
        )
        
        # 删除非当前代理
        result = config.remove_proxy("proxy2")
        assert result is True
        assert "proxy2" not in config.proxies
        assert config.current_proxy == "proxy1"

        # 删除当前代理，应该自动切换
        result = config.remove_proxy("proxy1")
        assert result is True
        assert "proxy1" not in config.proxies
        assert config.current_proxy is None  # 没有其他代理了

        # 删除不存在的代理
        result = config.remove_proxy("nonexistent")
        assert result is False

    def test_set_current_proxy(self, sample_proxy):
        """测试设置当前代理"""
        config = ProxyConfig(proxies={"test-proxy": sample_proxy})
        
        # 设置存在的代理
        result = config.set_current_proxy("test-proxy")
        assert result is True
        assert config.current_proxy == "test-proxy"

        # 设置不存在的代理
        result = config.set_current_proxy("nonexistent")
        assert result is False
        assert config.current_proxy == "test-proxy"  # 保持原值

    def test_get_proxy_names(self):
        """测试获取代理名称列表"""
        proxy1 = ProxyServer(name="proxy1", base_url="https://api1.example.com", api_key="sk-test1")
        proxy2 = ProxyServer(name="proxy2", base_url="https://api2.example.com", api_key="sk-test2")
        
        config = ProxyConfig(proxies={"proxy1": proxy1, "proxy2": proxy2})
        
        names = config.get_proxy_names()
        assert "proxy1" in names
        assert "proxy2" in names
        assert len(names) == 2

    def test_get_active_proxies(self):
        """测试获取活跃代理"""
        proxy1 = ProxyServer(name="proxy1", base_url="https://api1.example.com", api_key="sk-test1", is_active=True)
        proxy2 = ProxyServer(name="proxy2", base_url="https://api2.example.com", api_key="sk-test2", is_active=False)
        
        config = ProxyConfig(proxies={"proxy1": proxy1, "proxy2": proxy2})
        
        active_proxies = config.get_active_proxies()
        assert "proxy1" in active_proxies
        assert "proxy2" not in active_proxies
        assert len(active_proxies) == 1


class TestExportFormat:
    """ExportFormat 模型测试"""

    def test_default_export_format(self):
        """测试默认导出格式"""
        format_config = ExportFormat()
        
        assert format_config.shell_type == "bash"
        assert format_config.include_comments is True
        assert format_config.prefix == "ANTHROPIC_"
        assert format_config.export_all is False

    def test_custom_export_format(self):
        """测试自定义导出格式"""
        format_config = ExportFormat(
            shell_type="fish",
            include_comments=False,
            prefix="CLAUDE_",
            export_all=True
        )
        
        assert format_config.shell_type == "fish"
        assert format_config.include_comments is False
        assert format_config.prefix == "CLAUDE_"
        assert format_config.export_all is True

    def test_shell_type_validation(self):
        """测试Shell类型验证"""
        # 有效的Shell类型
        valid_shells = ["bash", "fish", "powershell", "zsh"]
        for shell in valid_shells:
            format_config = ExportFormat(shell_type=shell)
            assert format_config.shell_type == shell

        # 大小写不敏感
        format_config = ExportFormat(shell_type="BASH")
        assert format_config.shell_type == "bash"

        # 无效的Shell类型
        invalid_shells = ["cmd", "sh", "tcsh", ""]
        for shell in invalid_shells:
            with pytest.raises(ValidationError, match="不支持的Shell类型"):
                ExportFormat(shell_type=shell)

    def test_prefix_validation(self):
        """测试环境变量前缀验证"""
        # 有效前缀
        valid_prefixes = [
            ("ANTHROPIC", "ANTHROPIC_"),
            ("CLAUDE", "CLAUDE_"),
            ("API", "API_"),
            ("_TEST", "_TEST_"),
            ("A", "A_"),
        ]
        
        for input_prefix, expected_prefix in valid_prefixes:
            format_config = ExportFormat(prefix=input_prefix)
            assert format_config.prefix == expected_prefix

        # 自动添加下划线
        format_config = ExportFormat(prefix="ANTHROPIC_")
        assert format_config.prefix == "ANTHROPIC_"

        # 无效前缀
        invalid_prefixes = [
            "anthropic",  # 小写
            "123ABC",     # 数字开头
            "ABC-DEF",    # 包含连字符
            "",           # 空字符串
            "ABC DEF",    # 包含空格
        ]
        
        for prefix in invalid_prefixes:
            with pytest.raises(ValidationError, match="环境变量前缀必须"):
                ExportFormat(prefix=prefix)


class TestDataModelEdgeCases:
    """数据模型边界情况测试"""

    def test_proxy_server_maximum_values(self):
        """测试代理服务器最大值限制"""
        # 最大长度的名称
        max_name = "a" * 50
        proxy = ProxyServer(name=max_name, base_url="https://api.example.com", api_key="sk-test")
        assert proxy.name == max_name

        # 超过最大长度的名称
        too_long_name = "a" * 51
        with pytest.raises(ValidationError):
            ProxyServer(name=too_long_name, base_url="https://api.example.com", api_key="sk-test")

        # 最大长度的描述
        max_description = "d" * 200
        proxy = ProxyServer(
            name="test",
            base_url="https://api.example.com",
            api_key="sk-test",
            description=max_description
        )
        assert proxy.description == max_description

        # 超过最大长度的描述
        too_long_description = "d" * 201
        with pytest.raises(ValidationError):
            ProxyServer(
                name="test",
                base_url="https://api.example.com",
                api_key="sk-test",
                description=too_long_description
            )

    def test_proxy_server_minimum_values(self):
        """测试代理服务器最小值限制"""
        # 最小长度的名称
        min_name = "a"
        proxy = ProxyServer(name=min_name, base_url="https://api.example.com", api_key="sk-test")
        assert proxy.name == min_name

        # 空名称
        with pytest.raises(ValidationError):
            ProxyServer(name="", base_url="https://api.example.com", api_key="sk-test")

    def test_complex_url_validation(self):
        """测试复杂URL验证"""
        # 带端口的URL
        proxy = ProxyServer(name="test", base_url="https://api.example.com:8443", api_key="sk-test")
        assert str(proxy.base_url) == "https://api.example.com:8443/"

        # 带路径的URL
        proxy = ProxyServer(name="test", base_url="https://api.example.com/v1/api", api_key="sk-test")
        assert str(proxy.base_url) == "https://api.example.com/v1/api"

        # 本地IP地址
        proxy = ProxyServer(name="test", base_url="http://192.168.1.100", api_key="sk-test")
        assert str(proxy.base_url) == "http://192.168.1.100/"

        # localhost
        proxy = ProxyServer(name="test", base_url="http://localhost:3000", api_key="sk-test")
        assert str(proxy.base_url) == "http://localhost:3000/"

    def test_unicode_and_special_characters(self):
        """测试Unicode和特殊字符处理"""
        # 描述中的Unicode字符
        proxy = ProxyServer(
            name="test",
            base_url="https://api.example.com",
            api_key="sk-test",
            description="测试代理 🚀 emoji support",
            tags=["测试", "emoji🎯"]
        )
        
        assert "测试代理 🚀 emoji support" in proxy.description
        assert "测试" in proxy.tags
        assert "emoji🎯" in proxy.tags

    def test_config_version_edge_cases(self):
        """测试配置版本边界情况"""
        # 默认版本
        config = ProxyConfig()
        assert config.version == "1.0"

        # 自定义版本
        config = ProxyConfig(version="2.0")
        assert config.version == "2.0"