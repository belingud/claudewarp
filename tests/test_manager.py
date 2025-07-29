"""
代理管理器测试

测试ProxyManager的代理管理和环境变量导出功能。
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from claudewarp.core.config import ConfigManager
from claudewarp.core.exceptions import (
    ConfigError,
    DuplicateProxyError,
    ProxyNotFoundError,
    ValidationError,
)
from claudewarp.core.manager import ProxyManager
from claudewarp.core.models import ExportFormat, ProxyConfig, ProxyServer


class TestProxyManager:
    """测试ProxyManager类"""

    @pytest.fixture
    def temp_config_dir(self):
        """临时配置目录fixture"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def temp_manager(self, temp_config_dir):
        """临时代理管理器fixture"""
        config_path = temp_config_dir / "config.toml"
        config_manager = ConfigManager(config_path=config_path)
        return ProxyManager(config_manager=config_manager)

    @pytest.fixture
    def sample_proxy(self):
        """示例代理fixture"""
        return ProxyServer(
            name="test-proxy",
            base_url="https://api.example.com/",
            api_key="sk-1234567890abcdef",
            description="测试代理",
            tags=["test"],
        )

    def test_init_with_default_config_manager(self):
        """测试使用默认配置管理器初始化"""
        manager = ProxyManager()

        assert manager.config_manager is not None
        assert isinstance(manager.config_manager, ConfigManager)
        assert manager._config is None

    def test_init_with_custom_config_manager(self, temp_config_dir):
        """测试使用自定义配置管理器初始化"""
        config_path = temp_config_dir / "config.toml"
        config_manager = ConfigManager(config_path=config_path)
        manager = ProxyManager(config_manager=config_manager)

        assert manager.config_manager == config_manager

    def test_config_property_lazy_loading(self, temp_manager):
        """测试配置属性的懒加载"""
        assert temp_manager._config is None

        # 首次访问应该加载配置
        config = temp_manager.config
        assert temp_manager._config is not None
        assert isinstance(config, ProxyConfig)

        # 再次访问应该返回缓存的配置
        config2 = temp_manager.config
        assert config is config2

    def test_refresh_config(self, temp_manager):
        """测试刷新配置"""
        # 访问配置以触发加载
        _ = temp_manager.config
        assert temp_manager._config is not None

        # 刷新配置
        temp_manager.refresh_config()
        assert temp_manager._config is None

    def test_add_proxy_success(self, temp_manager, sample_proxy):
        """测试成功添加代理"""
        result = temp_manager.add_proxy(sample_proxy)

        assert result is True
        assert sample_proxy.name in temp_manager.config.proxies
        assert temp_manager.config.current_proxy == sample_proxy.name  # 第一个代理应该成为当前代理

    def test_add_proxy_duplicate(self, temp_manager, sample_proxy):
        """测试添加重复代理"""
        # 首次添加
        temp_manager.add_proxy(sample_proxy)

        # 再次添加同名代理
        duplicate_proxy = ProxyServer(
            name=sample_proxy.name,
            base_url="https://different.example.com/",
            api_key="sk-different-key",
        )

        with pytest.raises(DuplicateProxyError, match="代理.*已存在"):
            temp_manager.add_proxy(duplicate_proxy)

    def test_add_proxy_invalid(self, temp_manager):
        """测试添加无效代理"""
        invalid_proxy = ProxyServer(
            name="test",
            base_url="invalid-url",  # 无效URL
            api_key="sk-1234567890",
        )

        with pytest.raises(ValidationError):
            temp_manager.add_proxy(invalid_proxy)

    def test_remove_proxy_success(self, temp_manager, sample_proxy):
        """测试成功删除代理"""
        # 先添加代理
        temp_manager.add_proxy(sample_proxy)

        # 删除代理
        result = temp_manager.remove_proxy(sample_proxy.name)

        assert result is True
        assert sample_proxy.name not in temp_manager.config.proxies
        assert temp_manager.config.current_proxy is None  # 删除唯一代理后应该清空当前代理

    def test_remove_proxy_not_found(self, temp_manager):
        """测试删除不存在的代理"""
        with pytest.raises(ProxyNotFoundError, match="代理.*不存在"):
            temp_manager.remove_proxy("nonexistent")

    def test_remove_current_proxy_with_others(self, temp_manager):
        """测试删除当前代理但还有其他代理"""
        # 添加多个代理
        proxy1 = ProxyServer(name="proxy1", base_url="https://api1.com/", api_key="sk-1111111111")
        proxy2 = ProxyServer(name="proxy2", base_url="https://api2.com/", api_key="sk-2222222222")

        temp_manager.add_proxy(proxy1)
        temp_manager.add_proxy(proxy2)

        # 设置当前代理为proxy1
        temp_manager.switch_proxy("proxy1")
        assert temp_manager.config.current_proxy == "proxy1"

        # 删除当前代理
        temp_manager.remove_proxy("proxy1")

        # 应该自动切换到其他代理
        assert temp_manager.config.current_proxy == "proxy2"

    def test_switch_proxy_success(self, temp_manager, sample_proxy):
        """测试成功切换代理"""
        # 添加代理
        temp_manager.add_proxy(sample_proxy)

        # 切换代理
        result = temp_manager.switch_proxy(sample_proxy.name)

        assert result is True
        assert temp_manager.config.current_proxy == sample_proxy.name

    def test_switch_proxy_not_found(self, temp_manager):
        """测试切换到不存在的代理"""
        with pytest.raises(ProxyNotFoundError, match="代理.*不存在"):
            temp_manager.switch_proxy("nonexistent")

    def test_switch_proxy_inactive(self, temp_manager):
        """测试切换到未启用的代理"""
        inactive_proxy = ProxyServer(
            name="inactive",
            base_url="https://api.example.com/",
            api_key="sk-1234567890",
            is_active=False,
        )

        temp_manager.add_proxy(inactive_proxy)

        # 应该可以切换到未启用的代理（只是发出警告）
        result = temp_manager.switch_proxy("inactive")
        assert result is True
        assert temp_manager.config.current_proxy == "inactive"

    def test_get_current_proxy_exists(self, temp_manager, sample_proxy):
        """测试获取存在的当前代理"""
        temp_manager.add_proxy(sample_proxy)

        current = temp_manager.get_current_proxy()
        assert current == sample_proxy

    def test_get_current_proxy_none(self, temp_manager):
        """测试获取不存在的当前代理"""
        current = temp_manager.get_current_proxy()
        assert current is None

    def test_get_proxy_success(self, temp_manager, sample_proxy):
        """测试获取存在的代理"""
        temp_manager.add_proxy(sample_proxy)

        proxy = temp_manager.get_proxy(sample_proxy.name)
        assert proxy == sample_proxy

    def test_get_proxy_not_found(self, temp_manager):
        """测试获取不存在的代理"""
        with pytest.raises(ProxyNotFoundError, match="代理.*不存在"):
            temp_manager.get_proxy("nonexistent")

    def test_list_proxies_include_inactive(self, temp_manager):
        """测试列出所有代理（包括未启用的）"""
        active_proxy = ProxyServer(
            name="active", base_url="https://api1.com/", api_key="sk-1111111111", is_active=True
        )
        inactive_proxy = ProxyServer(
            name="inactive", base_url="https://api2.com/", api_key="sk-2222222222", is_active=False
        )

        temp_manager.add_proxy(active_proxy)
        temp_manager.add_proxy(inactive_proxy)

        proxies = temp_manager.list_proxies(include_inactive=True)
        assert len(proxies) == 2
        assert "active" in proxies
        assert "inactive" in proxies

    def test_list_proxies_exclude_inactive(self, temp_manager):
        """测试列出活跃代理（不包括未启用的）"""
        active_proxy = ProxyServer(
            name="active", base_url="https://api1.com/", api_key="sk-1111111111", is_active=True
        )
        inactive_proxy = ProxyServer(
            name="inactive", base_url="https://api2.com/", api_key="sk-2222222222", is_active=False
        )

        temp_manager.add_proxy(active_proxy)
        temp_manager.add_proxy(inactive_proxy)

        proxies = temp_manager.list_proxies(include_inactive=False)
        assert len(proxies) == 1
        assert "active" in proxies
        assert "inactive" not in proxies

    def test_get_proxy_names(self, temp_manager):
        """测试获取代理名称列表"""
        proxy1 = ProxyServer(name="proxy1", base_url="https://api1.com/", api_key="sk-1111111111")
        proxy2 = ProxyServer(name="proxy2", base_url="https://api2.com/", api_key="sk-2222222222")

        temp_manager.add_proxy(proxy1)
        temp_manager.add_proxy(proxy2)

        names = temp_manager.get_proxy_names()
        assert len(names) == 2
        assert "proxy1" in names
        assert "proxy2" in names

    def test_update_proxy_success(self, temp_manager, sample_proxy):
        """测试成功更新代理"""
        temp_manager.add_proxy(sample_proxy)

        # 更新代理
        result = temp_manager.update_proxy(
            sample_proxy.name, description="更新后的描述", tags=["updated", "test"]
        )

        assert result is True

        updated_proxy = temp_manager.get_proxy(sample_proxy.name)
        assert updated_proxy.description == "更新后的描述"
        assert updated_proxy.tags == ["updated", "test"]

    def test_update_proxy_name_change(self, temp_manager, sample_proxy):
        """测试更新代理名称"""
        temp_manager.add_proxy(sample_proxy)
        original_name = sample_proxy.name
        new_name = "new-proxy-name"

        result = temp_manager.update_proxy(original_name, name=new_name)

        assert result is True
        assert original_name not in temp_manager.config.proxies
        assert new_name in temp_manager.config.proxies

        # 如果是当前代理，current_proxy也应该更新
        if temp_manager.config.current_proxy == original_name:
            assert temp_manager.config.current_proxy == new_name

    def test_update_proxy_name_conflict(self, temp_manager):
        """测试更新代理名称冲突"""
        proxy1 = ProxyServer(name="proxy1", base_url="https://api1.com/", api_key="sk-1111111111")
        proxy2 = ProxyServer(name="proxy2", base_url="https://api2.com/", api_key="sk-2222222222")

        temp_manager.add_proxy(proxy1)
        temp_manager.add_proxy(proxy2)

        with pytest.raises(DuplicateProxyError, match="代理.*已存在"):
            temp_manager.update_proxy("proxy1", name="proxy2")

    def test_update_proxy_not_found(self, temp_manager):
        """测试更新不存在的代理"""
        with pytest.raises(ProxyNotFoundError, match="代理.*不存在"):
            temp_manager.update_proxy("nonexistent", description="new desc")

    def test_toggle_proxy_status(self, temp_manager, sample_proxy):
        """测试切换代理状态"""
        temp_manager.add_proxy(sample_proxy)
        original_status = sample_proxy.is_active

        new_status = temp_manager.toggle_proxy_status(sample_proxy.name)

        assert new_status != original_status

        updated_proxy = temp_manager.get_proxy(sample_proxy.name)
        assert updated_proxy.is_active == new_status

    def test_search_proxies_by_name(self, temp_manager):
        """测试按名称搜索代理"""
        proxy1 = ProxyServer(
            name="test-proxy", base_url="https://api1.com/", api_key="sk-1111111111"
        )
        proxy2 = ProxyServer(
            name="prod-proxy", base_url="https://api2.com/", api_key="sk-2222222222"
        )

        temp_manager.add_proxy(proxy1)
        temp_manager.add_proxy(proxy2)

        results = temp_manager.search_proxies("test")
        assert len(results) == 1
        assert "test-proxy" in results

    def test_search_proxies_by_description(self, temp_manager):
        """测试按描述搜索代理"""
        proxy1 = ProxyServer(
            name="proxy1",
            base_url="https://api1.com/",
            api_key="sk-1111111111",
            description="测试环境",
        )
        proxy2 = ProxyServer(
            name="proxy2",
            base_url="https://api2.com/",
            api_key="sk-2222222222",
            description="生产环境",
        )

        temp_manager.add_proxy(proxy1)
        temp_manager.add_proxy(proxy2)

        results = temp_manager.search_proxies("测试")
        assert len(results) == 1
        assert "proxy1" in results

    def test_search_proxies_by_tags(self, temp_manager):
        """测试按标签搜索代理"""
        proxy1 = ProxyServer(
            name="proxy1",
            base_url="https://api1.com/",
            api_key="sk-1111111111",
            tags=["dev", "test"],
        )
        proxy2 = ProxyServer(
            name="proxy2",
            base_url="https://api2.com/",
            api_key="sk-2222222222",
            tags=["prod", "stable"],
        )

        temp_manager.add_proxy(proxy1)
        temp_manager.add_proxy(proxy2)

        results = temp_manager.search_proxies("dev")
        assert len(results) == 1
        assert "proxy1" in results

    def test_search_proxies_custom_fields(self, temp_manager):
        """测试按自定义字段搜索代理"""
        proxy1 = ProxyServer(
            name="test-proxy",
            base_url="https://api1.com/",
            api_key="sk-1111111111",
            description="测试环境",
        )
        proxy2 = ProxyServer(
            name="prod-proxy",
            base_url="https://api2.com/",
            api_key="sk-2222222222",
            description="生产环境",
        )

        temp_manager.add_proxy(proxy1)
        temp_manager.add_proxy(proxy2)

        # 只搜索名称字段
        results = temp_manager.search_proxies("测试", fields=["name"])
        assert len(results) == 0  # 名称中没有"测试"

        # 只搜索描述字段
        results = temp_manager.search_proxies("测试", fields=["description"])
        assert len(results) == 1
        assert "test-proxy" in results

    def test_get_statistics(self, temp_manager):
        """测试获取统计信息"""
        # 添加一些代理
        active_proxy = ProxyServer(
            name="active",
            base_url="https://api1.com/",
            api_key="sk-1111111111",
            is_active=True,
            tags=["prod"],
        )
        inactive_proxy = ProxyServer(
            name="inactive",
            base_url="https://api2.com/",
            api_key="sk-2222222222",
            is_active=False,
            tags=["dev"],
        )

        temp_manager.add_proxy(active_proxy)
        temp_manager.add_proxy(inactive_proxy)
        temp_manager.switch_proxy("active")

        stats = temp_manager.get_statistics()

        assert stats["total_proxies"] == 2
        assert stats["active_proxies"] == 1
        assert stats["inactive_proxies"] == 1
        assert stats["current_proxy"] == "active"
        assert stats["has_current_proxy"] is True
        assert "prod" in stats["tag_distribution"]
        assert "dev" in stats["tag_distribution"]
        assert stats["tag_distribution"]["prod"] == 1
        assert stats["tag_distribution"]["dev"] == 1

    def test_validate_proxy_connection_valid(self, temp_manager, sample_proxy):
        """测试有效代理连接验证"""
        temp_manager.add_proxy(sample_proxy)

        is_valid, message = temp_manager.validate_proxy_connection(sample_proxy.name)

        assert is_valid is True
        assert "有效" in message

    def test_validate_proxy_connection_invalid_url(self, temp_manager):
        """测试无效URL的代理连接验证"""
        invalid_proxy = ProxyServer(
            name="invalid", base_url="ftp://invalid.com/", api_key="sk-1234567890"
        )

        # 绕过添加时的验证
        temp_manager.config.proxies["invalid"] = invalid_proxy

        is_valid, message = temp_manager.validate_proxy_connection("invalid")

        assert is_valid is False
        assert "URL格式无效" in message

    def test_validate_proxy_connection_not_found(self, temp_manager):
        """测试不存在代理的连接验证"""
        is_valid, message = temp_manager.validate_proxy_connection("nonexistent")

        assert is_valid is False
        assert "不存在" in message

    def test_backup_config(self, temp_manager, sample_proxy):
        """测试手动备份配置"""
        temp_manager.add_proxy(sample_proxy)

        with patch("core.utils.create_backup") as mock_backup:
            mock_backup.return_value = Path("/tmp/backup.toml")

            backup_path = temp_manager.backup_config()

            assert backup_path == "/tmp/backup.toml"
            mock_backup.assert_called_once()

    def test_get_proxy_count(self, temp_manager):
        """测试获取代理数量"""
        assert temp_manager.get_proxy_count() == 0

        proxy1 = ProxyServer(name="proxy1", base_url="https://api1.com/", api_key="sk-1111111111")
        proxy2 = ProxyServer(name="proxy2", base_url="https://api2.com/", api_key="sk-2222222222")

        temp_manager.add_proxy(proxy1)
        assert temp_manager.get_proxy_count() == 1

        temp_manager.add_proxy(proxy2)
        assert temp_manager.get_proxy_count() == 2

    def test_has_proxies(self, temp_manager, sample_proxy):
        """测试检查是否有代理"""
        assert temp_manager.has_proxies() is False

        temp_manager.add_proxy(sample_proxy)
        assert temp_manager.has_proxies() is True

    def test_has_current_proxy(self, temp_manager, sample_proxy):
        """测试检查是否有当前代理"""
        assert temp_manager.has_current_proxy() is False

        temp_manager.add_proxy(sample_proxy)
        assert temp_manager.has_current_proxy() is True


class TestProxyManagerExport:
    """测试代理管理器环境变量导出功能"""

    @pytest.fixture
    def temp_manager_with_proxy(self, temp_config_dir):
        """带有代理的临时管理器"""
        config_path = temp_config_dir / "config.toml"
        config_manager = ConfigManager(config_path=config_path)
        manager = ProxyManager(config_manager=config_manager)

        proxy = ProxyServer(
            name="test-proxy",
            base_url="https://api.example.com/",
            api_key="sk-1234567890abcdef",
            description="测试代理",
        )
        manager.add_proxy(proxy)

        return manager

    def test_export_environment_bash_default(self, temp_manager_with_proxy):
        """测试导出bash格式环境变量（默认格式）"""
        content = temp_manager_with_proxy.export_environment()

        assert "export ANTHROPIC_BASE_URL=" in content
        assert "export ANTHROPIC_API_KEY=" in content
        assert "https://api.example.com/" in content
        assert "sk-1234567890abcdef" in content
        assert "# Claude中转站环境变量配置" in content

    def test_export_environment_bash_custom_format(self, temp_manager_with_proxy):
        """测试导出bash格式环境变量（自定义格式）"""
        export_format = ExportFormat(shell_type="bash", include_comments=False, prefix="CUSTOM_")

        content = temp_manager_with_proxy.export_environment(export_format)

        assert "export CUSTOM_BASE_URL=" in content
        assert "export CUSTOM_API_KEY=" in content
        assert "# Claude中转站环境变量配置" not in content

    def test_export_environment_fish(self, temp_manager_with_proxy):
        """测试导出fish格式环境变量"""
        export_format = ExportFormat(shell_type="fish")

        content = temp_manager_with_proxy.export_environment(export_format)

        assert "set -x ANTHROPIC_BASE_URL" in content
        assert "set -x ANTHROPIC_API_KEY" in content
        assert "https://api.example.com/" in content

    def test_export_environment_powershell(self, temp_manager_with_proxy):
        """测试导出PowerShell格式环境变量"""
        export_format = ExportFormat(shell_type="powershell")

        content = temp_manager_with_proxy.export_environment(export_format)

        assert "$env:ANTHROPIC_BASE_URL=" in content
        assert "$env:ANTHROPIC_API_KEY=" in content
        assert "https://api.example.com/" in content

    def test_export_environment_zsh(self, temp_manager_with_proxy):
        """测试导出zsh格式环境变量（应该使用bash格式）"""
        export_format = ExportFormat(shell_type="zsh")

        content = temp_manager_with_proxy.export_environment(export_format)

        # zsh应该使用bash格式
        assert "export ANTHROPIC_BASE_URL=" in content
        assert "export ANTHROPIC_API_KEY=" in content

    def test_export_environment_unsupported_shell(self, temp_manager_with_proxy):
        """测试导出不支持的shell格式"""
        # 手动创建无效格式（绕过Pydantic验证）
        export_format = ExportFormat(shell_type="bash")
        export_format.shell_type = "unsupported"

        with pytest.raises(ValidationError, match="不支持的Shell类型"):
            temp_manager_with_proxy.export_environment(export_format)

    def test_export_environment_specific_proxy(self, temp_manager_with_proxy):
        """测试导出指定代理的环境变量"""
        # 添加另一个代理
        proxy2 = ProxyServer(
            name="proxy2", base_url="https://api2.example.com/", api_key="sk-different-key"
        )
        temp_manager_with_proxy.add_proxy(proxy2)

        # 导出指定代理
        content = temp_manager_with_proxy.export_environment(proxy_name="proxy2")

        assert "https://api2.example.com/" in content
        assert "sk-different-key" in content

    def test_export_environment_no_current_proxy(self, temp_config_dir):
        """测试没有当前代理时导出环境变量"""
        config_path = temp_config_dir / "config.toml"
        config_manager = ConfigManager(config_path=config_path)
        manager = ProxyManager(config_manager=config_manager)

        with pytest.raises(ProxyNotFoundError, match="未设置当前代理"):
            manager.export_environment()

    def test_export_environment_proxy_not_found(self, temp_manager_with_proxy):
        """测试导出不存在的代理环境变量"""
        with pytest.raises(ProxyNotFoundError, match="代理.*不存在"):
            temp_manager_with_proxy.export_environment(proxy_name="nonexistent")


class TestProxyManagerErrorHandling:
    """测试代理管理器错误处理"""

    @pytest.fixture
    def mock_config_manager(self):
        """模拟配置管理器"""
        mock_manager = Mock(spec=ConfigManager)
        mock_config = ProxyConfig()
        mock_manager.load_config.return_value = mock_config
        return mock_manager

    def test_config_load_error_handling(self, mock_config_manager):
        """测试配置加载错误处理"""
        mock_config_manager.load_config.side_effect = ConfigError("Load failed")

        manager = ProxyManager(config_manager=mock_config_manager)

        # 配置加载错误应该被传播
        with pytest.raises(ConfigError):
            _ = manager.config

    def test_config_save_error_handling(self, mock_config_manager):
        """测试配置保存错误处理"""
        mock_config_manager.save_config.side_effect = ConfigError("Save failed")

        manager = ProxyManager(config_manager=mock_config_manager)

        proxy = ProxyServer(
            name="test", base_url="https://api.example.com/", api_key="sk-1234567890"
        )

        with pytest.raises(ConfigError):
            manager.add_proxy(proxy)

    def test_unexpected_error_handling(self, mock_config_manager):
        """测试意外错误处理"""
        mock_config_manager.save_config.side_effect = Exception("Unexpected error")

        manager = ProxyManager(config_manager=mock_config_manager)

        proxy = ProxyServer(
            name="test", base_url="https://api.example.com/", api_key="sk-1234567890"
        )

        # 意外错误应该被包装为ConfigError
        with pytest.raises(ConfigError, match="添加代理失败"):
            manager.add_proxy(proxy)


# 测试工具函数
def create_test_manager_with_proxies(proxy_count: int = 2) -> ProxyManager:
    """创建带有代理的测试管理器"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "config.toml"
        config_manager = ConfigManager(config_path=config_path)
        manager = ProxyManager(config_manager=config_manager)

        for i in range(proxy_count):
            proxy = ProxyServer(
                name=f"proxy-{i}",
                base_url=f"https://api{i}.example.com/",
                api_key=f"sk-{'1' * 10}{i}",
                description=f"代理服务器 {i}",
                tags=[f"tag{i}", "test"],
            )
            manager.add_proxy(proxy)

        return manager
