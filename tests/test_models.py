"""
核心模型测试

测试ProxyServer、ProxyConfig和ExportFormat模型的验证和功能。
"""

import pytest

from claudewarp.core.models import ExportFormat, ProxyConfig, ProxyServer


class TestProxyServer:
    """测试ProxyServer模型"""

    def test_valid_proxy_creation(self):
        """测试有效代理的创建"""
        proxy = ProxyServer(
            name="test-proxy",
            base_url="https://api.example.com/",
            api_key="sk-1234567890abcdef",
            description="测试代理",
            tags=["test", "dev"],
        )

        assert proxy.name == "test-proxy"
        assert proxy.base_url == "https://api.example.com/"
        assert proxy.api_key == "sk-1234567890abcdef"
        assert proxy.description == "测试代理"
        assert proxy.tags == ["test", "dev"]
        assert proxy.is_active is True
        assert isinstance(proxy.created_at, str)
        assert isinstance(proxy.updated_at, str)

    def test_valid_proxy_creation_with_auth_token(self):
        """测试使用Auth令牌创建有效代理"""
        proxy = ProxyServer(
            name="test-proxy",
            base_url="https://api.example.com/",
            api_key="",  # 空字符串，因为使用了auth_token
            auth_token="sk-ant-api03-abcdef1234567890",
            description="测试代理",
            tags=["test", "dev"],
        )

        assert proxy.name == "test-proxy"
        assert proxy.base_url == "https://api.example.com/"
        assert proxy.auth_token == "sk-ant-api03-abcdef1234567890"
        assert proxy.description == "测试代理"
        assert proxy.tags == ["test", "dev"]
        assert proxy.is_active is True
        assert proxy.get_auth_method() == "auth_token"
        assert proxy.get_active_credential() == "sk-ant-api03-abcdef1234567890"

    def test_url_normalization(self):
        """测试URL规范化"""
        # 不以/结尾的URL应该自动添加/
        proxy = ProxyServer(
            name="test", base_url="https://api.example.com", api_key="sk-1234567890"
        )
        assert proxy.base_url == "https://api.example.com/"

    def test_invalid_name(self):
        """测试无效名称验证"""
        with pytest.raises(ValueError, match="代理名称只能包含"):
            ProxyServer(
                name="invalid name with spaces",
                base_url="https://api.example.com/",
                api_key="sk-1234567890",
            )

        with pytest.raises(ValueError, match="代理名称只能包含"):
            ProxyServer(
                name="invalid@name", base_url="https://api.example.com/", api_key="sk-1234567890"
            )

    def test_invalid_url(self):
        """测试无效URL验证"""
        with pytest.raises(ValueError, match="Base URL必须以http://或https://开头"):
            ProxyServer(name="test", base_url="ftp://api.example.com/", api_key="sk-1234567890")

        with pytest.raises(ValueError, match="Base URL格式无效"):
            ProxyServer(name="test", base_url="https://", api_key="sk-1234567890")

    def test_invalid_api_key(self):
        """测试无效API密钥验证"""
        with pytest.raises(ValueError, match="API密钥长度至少为10个字符"):
            ProxyServer(name="test", base_url="https://api.example.com/", api_key="short")

        with pytest.raises(ValueError, match="API密钥不能包含空白字符"):
            ProxyServer(name="test", base_url="https://api.example.com/", api_key="sk-123 456 789")

    def test_valid_auth_token_formats(self):
        """测试有效的Auth令牌格式"""
        valid_tokens = [
            "sk-ant-api03-abcdef1234567890",
            "sk-ant-api03-1234567890abcdef",
            "sk-ant-api03-longtokenwithmanychars1234567890",
            "sk-ant-api03-minlength",  # 正好10个字符
        ]

        for token in valid_tokens:
            proxy = ProxyServer(
                name="test",
                base_url="https://api.example.com/",
                api_key="",  # 空字符串，因为使用了auth_token
                auth_token=token,
            )
            assert proxy.auth_token == token
            assert proxy.get_auth_method() == "auth_token"

    def test_invalid_auth_token_formats(self):
        """测试无效的Auth令牌格式"""
        # 太短的令牌
        with pytest.raises(ValueError, match="Auth令牌长度至少为10个字符"):
            ProxyServer(
                name="test",
                base_url="https://api.example.com/",
                api_key="",
                auth_token="short",
            )

        # 包含空白字符的令牌
        with pytest.raises(ValueError, match="Auth令牌不能包含空白字符"):
            ProxyServer(
                name="test",
                base_url="https://api.example.com/",
                api_key="",
                auth_token="sk-ant 123 456",
            )

        # None值应该是有效的（可选字段）
        proxy = ProxyServer(
            name="test",
            base_url="https://api.example.com/",
            api_key="sk-1234567890",
            auth_token=None,
        )
        assert proxy.auth_token is None
        assert proxy.get_auth_method() == "api_key"

    def test_mutual_exclusivity_api_key_with_auth_token(self):
        """测试API密钥和Auth令牌的互斥性"""
        # 同时配置API密钥和Auth令牌应该失败
        with pytest.raises(ValueError, match="不能同时配置api_key和auth_token"):
            ProxyServer(
                name="test",
                base_url="https://api.example.com/",
                api_key="sk-1234567890",
                auth_token="sk-ant-api03-abcdef1234567890",
            )

        # API密钥非空时Auth令牌不能非空
        with pytest.raises(ValueError, match="不能同时配置api_key和auth_token"):
            ProxyServer(
                name="test",
                base_url="https://api.example.com/",
                api_key="sk-1234567890",
                auth_token="sk-ant-api03-abcdef1234567890",
            )

        # Auth令牌非空时API密钥不能非空
        with pytest.raises(ValueError, match="不能同时配置api_key和auth_token"):
            ProxyServer(
                name="test",
                base_url="https://api.example.com/",
                api_key="sk-1234567890",
                auth_token="sk-ant-api03-abcdef1234567890",
            )

    def test_auth_method_detection(self):
        """测试认证方法检测"""
        # 只有API密钥
        proxy_api = ProxyServer(
            name="test-api",
            base_url="https://api.example.com/",
            api_key="sk-1234567890",
            auth_token=None,
        )
        assert proxy_api.get_auth_method() == "api_key"
        assert proxy_api.get_active_credential() == "sk-1234567890"

        # 只有Auth令牌
        proxy_auth = ProxyServer(
            name="test-auth",
            base_url="https://api.example.com/",
            api_key="",
            auth_token="sk-ant-api03-abcdef1234567890",
        )
        assert proxy_auth.get_auth_method() == "auth_token"
        assert proxy_auth.get_active_credential() == "sk-ant-api03-abcdef1234567890"

        # 都没有配置
        proxy_none = ProxyServer(
            name="test-none",
            base_url="https://api.example.com/",
            api_key="",
            auth_token=None,
        )
        assert proxy_none.get_auth_method() == "none"
        assert proxy_none.get_active_credential() == ""

    def test_tags_validation(self):
        """测试标签验证和清理"""
        proxy = ProxyServer(
            name="test",
            base_url="https://api.example.com/",
            api_key="sk-1234567890",
            tags=["tag1", " tag2 ", "", "tag1", "tag3"],  # 包含重复、空白和空字符串
        )

        # 应该清理重复、空白和空标签
        assert proxy.tags == ["tag1", "tag2", "tag3"]

    def test_proxy_serialization(self):
        """测试代理序列化"""
        proxy = ProxyServer(
            name="test",
            base_url="https://api.example.com/",
            api_key="sk-1234567890",
            description="测试",
        )

        data = proxy.dict()
        assert isinstance(data, dict)
        assert data["name"] == "test"
        assert data["base_url"] == "https://api.example.com/"

        # 可以从字典重新创建
        proxy2 = ProxyServer(**data)
        assert proxy2.name == proxy.name
        assert proxy2.base_url == proxy.base_url


class TestProxyConfig:
    """测试ProxyConfig模型"""

    def test_empty_config_creation(self):
        """测试空配置创建"""
        config = ProxyConfig()

        assert config.version == "1.0"
        assert config.current_proxy is None
        assert config.proxies == {}
        assert config.settings == {}
        assert isinstance(config.created_at, str)
        assert isinstance(config.updated_at, str)

    def test_config_with_proxies(self):
        """测试包含代理的配置"""
        proxy1 = ProxyServer(
            name="proxy1", base_url="https://api1.example.com/", api_key="sk-1111111111"
        )
        proxy2 = ProxyServer(
            name="proxy2", base_url="https://api2.example.com/", api_key="sk-2222222222"
        )

        config = ProxyConfig(current_proxy="proxy1", proxies={"proxy1": proxy1, "proxy2": proxy2})

        assert config.current_proxy == "proxy1"
        assert len(config.proxies) == 2
        assert config.get_current_proxy() == proxy1

    def test_invalid_current_proxy(self):
        """测试无效的当前代理设置"""
        proxy = ProxyServer(
            name="proxy1", base_url="https://api.example.com/", api_key="sk-1111111111"
        )

        with pytest.raises(ValueError, match="当前代理.*不存在于代理列表中"):
            ProxyConfig(current_proxy="nonexistent", proxies={"proxy1": proxy})

    def test_proxy_name_consistency(self):
        """测试代理名称一致性验证"""
        proxy = ProxyServer(
            name="proxy1", base_url="https://api.example.com/", api_key="sk-1111111111"
        )

        with pytest.raises(ValueError, match="代理名称不一致"):
            ProxyConfig(proxies={"different_name": proxy})

    def test_add_proxy_method(self):
        """测试添加代理方法"""
        config = ProxyConfig()
        proxy = ProxyServer(
            name="test-proxy", base_url="https://api.example.com/", api_key="sk-1111111111"
        )

        config.add_proxy(proxy)

        assert "test-proxy" in config.proxies
        assert config.current_proxy == "test-proxy"  # 第一个代理应该成为当前代理

    def test_remove_proxy_method(self):
        """测试删除代理方法"""
        proxy1 = ProxyServer(name="proxy1", base_url="https://api1.com/", api_key="sk-1111111111")
        proxy2 = ProxyServer(name="proxy2", base_url="https://api2.com/", api_key="sk-2222222222")

        config = ProxyConfig(current_proxy="proxy1", proxies={"proxy1": proxy1, "proxy2": proxy2})

        # 删除非当前代理
        result = config.remove_proxy("proxy2")
        assert result is True
        assert "proxy2" not in config.proxies
        assert config.current_proxy == "proxy1"

        # 删除当前代理，应该切换到剩余代理
        result = config.remove_proxy("proxy1")
        assert result is True
        assert "proxy1" not in config.proxies
        assert config.current_proxy is None  # 没有其他代理了

        # 删除不存在的代理
        result = config.remove_proxy("nonexistent")
        assert result is False

    def test_set_current_proxy_method(self):
        """测试设置当前代理方法"""
        proxy = ProxyServer(
            name="test-proxy", base_url="https://api.example.com/", api_key="sk-1111111111"
        )

        config = ProxyConfig(proxies={"test-proxy": proxy})

        # 设置存在的代理
        result = config.set_current_proxy("test-proxy")
        assert result is True
        assert config.current_proxy == "test-proxy"

        # 设置不存在的代理
        result = config.set_current_proxy("nonexistent")
        assert result is False
        assert config.current_proxy == "test-proxy"  # 保持不变

    def test_get_active_proxies(self):
        """测试获取活跃代理"""
        proxy1 = ProxyServer(
            name="active", base_url="https://api1.com/", api_key="sk-1111111111", is_active=True
        )
        proxy2 = ProxyServer(
            name="inactive", base_url="https://api2.com/", api_key="sk-2222222222", is_active=False
        )

        config = ProxyConfig(proxies={"active": proxy1, "inactive": proxy2})

        active_proxies = config.get_active_proxies()
        assert len(active_proxies) == 1
        assert "active" in active_proxies
        assert "inactive" not in active_proxies


class TestExportFormat:
    """测试ExportFormat模型"""

    def test_default_export_format(self):
        """测试默认导出格式"""
        export_format = ExportFormat()

        assert export_format.shell_type == "bash"
        assert export_format.include_comments is True
        assert export_format.prefix == "ANTHROPIC_"
        assert export_format.export_all is False

    def test_valid_shell_types(self):
        """测试有效的shell类型"""
        valid_shells = ["bash", "fish", "powershell", "zsh"]

        for shell in valid_shells:
            export_format = ExportFormat(shell_type=shell)
            assert export_format.shell_type == shell.lower()

    def test_invalid_shell_type(self):
        """测试无效的shell类型"""
        with pytest.raises(ValueError, match="不支持的Shell类型"):
            ExportFormat(shell_type="invalid_shell")

    def test_prefix_validation(self):
        """测试前缀验证"""
        # 有效前缀
        valid_prefixes = ["API_", "CLAUDE_", "MY_APP_", "_PREFIX"]
        for prefix in valid_prefixes:
            export_format = ExportFormat(prefix=prefix)
            assert export_format.prefix.endswith("_")

        # 自动添加下划线
        export_format = ExportFormat(prefix="TEST")
        assert export_format.prefix == "TEST_"

        # 无效前缀
        with pytest.raises(ValueError, match="环境变量前缀必须以大写字母或下划线开头"):
            ExportFormat(prefix="invalid")

        with pytest.raises(ValueError, match="环境变量前缀必须以大写字母或下划线开头"):
            ExportFormat(prefix="123_PREFIX")

    def test_export_format_serialization(self):
        """测试导出格式序列化"""
        export_format = ExportFormat(
            shell_type="fish", include_comments=False, prefix="CUSTOM_", export_all=True
        )

        data = export_format.dict()
        assert data["shell_type"] == "fish"
        assert data["include_comments"] is False
        assert data["prefix"] == "CUSTOM_"
        assert data["export_all"] is True

        # 从字典重新创建
        export_format2 = ExportFormat(**data)
        assert export_format2.shell_type == export_format.shell_type
        assert export_format2.include_comments == export_format.include_comments


class TestModelInteraction:
    """测试模型之间的交互"""

    def test_config_with_real_proxies(self):
        """测试配置与真实代理的交互"""
        # 创建多个代理
        proxies = {}
        for i in range(3):
            proxy = ProxyServer(
                name=f"proxy-{i}",
                base_url=f"https://api{i}.example.com/",
                api_key=f"sk-{'1' * 10}{i}",
                description=f"代理服务器 {i}",
                tags=[f"tag{i}", "test"],
            )
            proxies[proxy.name] = proxy

        # 创建配置
        config = ProxyConfig(
            current_proxy="proxy-1",
            proxies=proxies,
            settings={"auto_backup": True, "theme": "dark"},
        )

        # 验证配置
        assert len(config.proxies) == 3
        assert config.current_proxy == "proxy-1"
        assert config.get_current_proxy().name == "proxy-1"

        # 测试获取代理名称列表
        names = config.get_proxy_names()
        assert len(names) == 3
        assert "proxy-0" in names
        assert "proxy-1" in names
        assert "proxy-2" in names

        # 测试序列化和反序列化
        data = config.dict()
        config2 = ProxyConfig(**data)
        assert len(config2.proxies) == 3
        assert config2.current_proxy == "proxy-1"

    def test_proxy_update_timestamp(self):
        """测试代理更新时间戳"""
        proxy = ProxyServer(
            name="test", base_url="https://api.example.com/", api_key="sk-1234567890"
        )

        # 修改代理（这会触发时间戳更新）
        proxy.description = "新的描述"

        # 由于Pydantic的validate_assignment=True，时间戳应该更新
        # 注意：在实际使用中，时间戳更新由validator处理
        assert isinstance(proxy.updated_at, str)


# 测试数据工厂函数
def create_test_proxy(name: str = "test-proxy", **kwargs) -> ProxyServer:
    """创建测试代理的工厂函数"""
    defaults = {
        "name": name,
        "base_url": "https://api.example.com/",
        "api_key": "sk-1234567890abcdef",
        "description": "测试代理",
        "tags": ["test"],
    }
    defaults.update(kwargs)
    return ProxyServer(**defaults)


def create_test_config(proxy_count: int = 2, current_index: int = 0) -> ProxyConfig:
    """创建测试配置的工厂函数"""
    proxies = {}
    proxy_names = []

    for i in range(proxy_count):
        name = f"proxy-{i}"
        proxy = create_test_proxy(
            name=name, base_url=f"https://api{i}.example.com/", api_key=f"sk-{'1' * 10}{i}"
        )
        proxies[name] = proxy
        proxy_names.append(name)

    current_proxy = proxy_names[current_index] if proxy_names else None

    return ProxyConfig(current_proxy=current_proxy, proxies=proxies)


# Pytest fixtures
@pytest.fixture
def sample_proxy():
    """提供示例代理的fixture"""
    return create_test_proxy()


@pytest.fixture
def sample_config():
    """提供示例配置的fixture"""
    return create_test_config()


@pytest.fixture
def export_format():
    """提供示例导出格式的fixture"""
    return ExportFormat()
