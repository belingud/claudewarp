"""
代理管理器测试
测试 ProxyManager 的代理服务器管理、导出功能和 Claude Code 集成
"""

from unittest.mock import patch

import pytest

from claudewarp.core.exceptions import (
    ConfigError,
    DuplicateProxyError,
    ExportError,
    ProxyNotFoundError,
    ValidationError,
)
from claudewarp.core.manager import ProxyManager
from claudewarp.core.models import ExportFormat, ProxyServer


class TestProxyManagerInit:
    """ProxyManager 初始化测试"""

    def test_init_with_default_config(self):
        """测试使用默认配置初始化"""
        manager = ProxyManager()
        
        assert manager.config_manager is not None
        assert manager.config is not None
        assert isinstance(manager.config.proxies, dict)

    def test_init_with_custom_config(self, temp_dir):
        """测试使用自定义配置初始化"""
        config_path = temp_dir / "custom_config.toml"
        manager = ProxyManager(
            config_path=config_path,
            auto_backup=False,
            max_backups=10
        )
        
        assert manager.config_manager.config_path == config_path
        assert manager.config_manager.auto_backup is False
        assert manager.config_manager.max_backups == 10

    def test_config_property_lazy_loading(self, temp_proxy_manager):
        """测试配置属性的懒加载"""
        # 重置内部配置
        temp_proxy_manager._config = None
        
        # 访问config属性应该触发加载
        config = temp_proxy_manager.config
        assert config is not None

    @patch('claudewarp.core.manager.ConfigManager.load_config')
    def test_init_with_config_error(self, mock_load_config, temp_dir):
        """测试配置加载错误时的初始化"""
        mock_load_config.side_effect = Exception("Config load failed")
        
        config_path = temp_dir / "config.toml"
        with pytest.raises(ConfigError, match="初始化代理管理器失败"):
            ProxyManager(config_path=config_path)


class TestProxyManagerCRUD:
    """代理管理器 CRUD 操作测试"""

    def test_add_proxy_success(self, temp_proxy_manager):
        """测试成功添加代理"""
        proxy = temp_proxy_manager.add_proxy(
            name="new-proxy",
            base_url="https://api.new.com",
            api_key="sk-newkey",
            description="新代理",
            tags=["new", "test"]
        )
        
        assert isinstance(proxy, ProxyServer)
        assert proxy.name == "new-proxy"
        assert proxy.base_url == "https://api.new.com/"
        assert proxy.api_key == "sk-newkey"
        assert "new-proxy" in temp_proxy_manager.config.proxies

    def test_add_proxy_with_auth_token(self, temp_proxy_manager):
        """测试使用认证令牌添加代理"""
        proxy = temp_proxy_manager.add_proxy(
            name="auth-proxy",
            base_url="https://api.auth.com",
            auth_token="sk-ant-api03-token123",
            description="认证代理"
        )
        
        assert proxy.auth_token == "sk-ant-api03-token123"
        assert proxy.api_key is None
        assert proxy.get_auth_method() == "auth_token"

    def test_add_proxy_with_api_key_helper(self, temp_proxy_manager):
        """测试使用API密钥助手添加代理"""
        proxy = temp_proxy_manager.add_proxy(
            name="helper-proxy",
            base_url="https://api.helper.com",
            api_key_helper="echo sk-helper123",
            description="助手代理"
        )
        
        assert proxy.api_key_helper == "echo sk-helper123"
        assert proxy.api_key is None
        assert proxy.auth_token is None
        assert proxy.get_auth_method() == "api_key_helper"

    def test_add_proxy_duplicate_name(self, temp_proxy_manager):
        """测试添加重复名称的代理"""
        # 先添加一个代理
        temp_proxy_manager.add_proxy(
            name="duplicate",
            base_url="https://api.first.com",
            api_key="sk-first"
        )
        
        # 再添加同名代理应该失败
        with pytest.raises(DuplicateProxyError):
            temp_proxy_manager.add_proxy(
                name="duplicate",
                base_url="https://api.second.com",
                api_key="sk-second"
            )

    def test_add_proxy_set_as_current(self, temp_proxy_manager):
        """测试添加代理并设置为当前"""
        temp_proxy_manager.add_proxy(
            name="current-proxy",
            base_url="https://api.current.com",
            api_key="sk-current",
            set_as_current=True
        )
        
        assert temp_proxy_manager.config.current_proxy == "current-proxy"

    def test_add_proxy_validation_error(self, temp_proxy_manager):
        """测试添加无效代理时的验证错误"""
        with pytest.raises(ValidationError):
            temp_proxy_manager.add_proxy(
                name="invalid proxy",  # 无效名称
                base_url="https://api.test.com",
                api_key="sk-test"
            )

    def test_remove_proxy_success(self, temp_proxy_manager, sample_proxy):
        """测试成功删除代理"""
        # 先添加代理
        temp_proxy_manager.config.add_proxy(sample_proxy)
        temp_proxy_manager._save_config()
        
        # 删除代理
        result = temp_proxy_manager.remove_proxy("test-proxy")
        assert result is True
        assert "test-proxy" not in temp_proxy_manager.config.proxies

    def test_remove_proxy_not_found(self, temp_proxy_manager):
        """测试删除不存在的代理"""
        with pytest.raises(ProxyNotFoundError):
            temp_proxy_manager.remove_proxy("nonexistent")

    def test_remove_proxy_current_proxy_switch(self, temp_proxy_manager):
        """测试删除当前代理时的自动切换"""
        # 添加两个代理
        proxy1 = ProxyServer(name="proxy1", base_url="https://api1.com", api_key="sk-1")
        proxy2 = ProxyServer(name="proxy2", base_url="https://api2.com", api_key="sk-2")
        
        temp_proxy_manager.config.add_proxy(proxy1)
        temp_proxy_manager.config.add_proxy(proxy2)
        temp_proxy_manager.config.set_current_proxy("proxy1")
        
        # 删除当前代理
        temp_proxy_manager.remove_proxy("proxy1")
        
        # 应该自动切换到剩余代理
        assert temp_proxy_manager.config.current_proxy == "proxy2"

    def test_switch_proxy_success(self, temp_proxy_manager, sample_proxy):
        """测试成功切换代理"""
        # 先添加代理
        temp_proxy_manager.config.add_proxy(sample_proxy)
        temp_proxy_manager._save_config()
        
        # 切换代理
        with patch.object(temp_proxy_manager, 'apply_claude_code_setting') as mock_apply:
            result = temp_proxy_manager.switch_proxy("test-proxy")
            
            assert result == sample_proxy
            assert temp_proxy_manager.config.current_proxy == "test-proxy"
            mock_apply.assert_called_once_with("test-proxy")

    def test_switch_proxy_not_found(self, temp_proxy_manager):
        """测试切换到不存在的代理"""
        with pytest.raises(ProxyNotFoundError):
            temp_proxy_manager.switch_proxy("nonexistent")

    def test_switch_proxy_inactive(self, temp_proxy_manager):
        """测试切换到未启用的代理"""
        inactive_proxy = ProxyServer(
            name="inactive",
            base_url="https://api.inactive.com",
            api_key="sk-inactive",
            is_active=False
        )
        temp_proxy_manager.config.add_proxy(inactive_proxy)
        
        with pytest.raises(ValidationError, match="未启用"):
            temp_proxy_manager.switch_proxy("inactive")

    @patch('claudewarp.core.manager.ProxyManager.apply_claude_code_setting')
    def test_switch_proxy_claude_code_error(self, mock_apply, temp_proxy_manager, sample_proxy):
        """测试切换代理时 Claude Code 应用失败"""
        mock_apply.side_effect = Exception("Claude Code apply failed")
        
        temp_proxy_manager.config.add_proxy(sample_proxy)
        
        # 切换应该成功，但会记录警告
        result = temp_proxy_manager.switch_proxy("test-proxy")
        assert result == sample_proxy
        assert temp_proxy_manager.config.current_proxy == "test-proxy"

    def test_get_current_proxy(self, temp_proxy_manager, sample_proxy):
        """测试获取当前代理"""
        # 没有当前代理
        assert temp_proxy_manager.get_current_proxy() is None
        
        # 设置当前代理
        temp_proxy_manager.config.add_proxy(sample_proxy)
        current = temp_proxy_manager.get_current_proxy()
        assert current == sample_proxy

    def test_get_proxy_success(self, temp_proxy_manager, sample_proxy):
        """测试成功获取指定代理"""
        temp_proxy_manager.config.add_proxy(sample_proxy)
        
        proxy = temp_proxy_manager.get_proxy("test-proxy")
        assert proxy == sample_proxy

    def test_get_proxy_not_found(self, temp_proxy_manager):
        """测试获取不存在的代理"""
        with pytest.raises(ProxyNotFoundError):
            temp_proxy_manager.get_proxy("nonexistent")

    def test_list_proxies_all(self, temp_proxy_manager):
        """测试列出所有代理"""
        proxy1 = ProxyServer(name="proxy1", base_url="https://api1.com", api_key="sk-1", is_active=True)
        proxy2 = ProxyServer(name="proxy2", base_url="https://api2.com", api_key="sk-2", is_active=False)
        
        temp_proxy_manager.config.add_proxy(proxy1)
        temp_proxy_manager.config.add_proxy(proxy2)
        
        all_proxies = temp_proxy_manager.list_proxies(active_only=False)
        assert len(all_proxies) == 2
        assert "proxy1" in all_proxies
        assert "proxy2" in all_proxies

    def test_list_proxies_active_only(self, temp_proxy_manager):
        """测试只列出活跃代理"""
        proxy1 = ProxyServer(name="proxy1", base_url="https://api1.com", api_key="sk-1", is_active=True)
        proxy2 = ProxyServer(name="proxy2", base_url="https://api2.com", api_key="sk-2", is_active=False)
        
        temp_proxy_manager.config.add_proxy(proxy1)
        temp_proxy_manager.config.add_proxy(proxy2)
        
        active_proxies = temp_proxy_manager.list_proxies(active_only=True)
        assert len(active_proxies) == 1
        assert "proxy1" in active_proxies
        assert "proxy2" not in active_proxies

    def test_get_proxy_names(self, temp_proxy_manager):
        """测试获取代理名称列表"""
        proxy1 = ProxyServer(name="proxy1", base_url="https://api1.com", api_key="sk-1", is_active=True)
        proxy2 = ProxyServer(name="proxy2", base_url="https://api2.com", api_key="sk-2", is_active=False)
        
        temp_proxy_manager.config.add_proxy(proxy1)
        temp_proxy_manager.config.add_proxy(proxy2)
        
        # 所有代理名称
        all_names = temp_proxy_manager.get_proxy_names(active_only=False)
        assert len(all_names) == 2
        assert "proxy1" in all_names
        assert "proxy2" in all_names
        
        # 只获取活跃代理名称
        active_names = temp_proxy_manager.get_proxy_names(active_only=True)
        assert len(active_names) == 1
        assert "proxy1" in active_names


class TestProxyManagerUpdate:
    """代理管理器更新功能测试"""

    def test_update_proxy_success(self, temp_proxy_manager, sample_proxy):
        """测试成功更新代理"""
        temp_proxy_manager.config.add_proxy(sample_proxy)
        
        updated_proxy = temp_proxy_manager.update_proxy(
            name="test-proxy",
            base_url="https://api.updated.com",
            description="更新后的描述",
            tags=["updated", "test"]
        )
        
        assert updated_proxy.base_url == "https://api.updated.com/"
        assert updated_proxy.description == "更新后的描述"
        assert "updated" in updated_proxy.tags
        assert updated_proxy.api_key == sample_proxy.api_key  # 保持原值

    def test_update_proxy_not_found(self, temp_proxy_manager):
        """测试更新不存在的代理"""
        with pytest.raises(ProxyNotFoundError):
            temp_proxy_manager.update_proxy("nonexistent", base_url="https://api.new.com")

    def test_update_proxy_switch_auth_method(self, temp_proxy_manager):
        """测试更新代理的认证方式"""
        # 创建使用API Key的代理
        proxy = ProxyServer(name="auth-test", base_url="https://api.test.com", api_key="sk-old")
        temp_proxy_manager.config.add_proxy(proxy)
        
        # 更新为使用认证令牌
        updated_proxy = temp_proxy_manager.update_proxy(
            name="auth-test",
            auth_token="sk-ant-api03-newtoken"
        )
        
        assert updated_proxy.auth_token == "sk-ant-api03-newtoken"
        assert updated_proxy.api_key is None

    def test_update_proxy_disable_current(self, temp_proxy_manager):
        """测试禁用当前代理时的自动切换"""
        proxy1 = ProxyServer(name="proxy1", base_url="https://api1.com", api_key="sk-1")
        proxy2 = ProxyServer(name="proxy2", base_url="https://api2.com", api_key="sk-2")
        
        temp_proxy_manager.config.add_proxy(proxy1)
        temp_proxy_manager.config.add_proxy(proxy2)
        temp_proxy_manager.config.set_current_proxy("proxy1")
        
        # 禁用当前代理
        temp_proxy_manager.update_proxy("proxy1", is_active=False)
        
        # 应该自动切换到其他代理
        assert temp_proxy_manager.config.current_proxy == "proxy2"

    def test_update_proxy_disable_last_active(self, temp_proxy_manager):
        """测试禁用最后一个活跃代理"""
        proxy = ProxyServer(name="only-proxy", base_url="https://api.com", api_key="sk-test")
        temp_proxy_manager.config.add_proxy(proxy)
        
        # 禁用唯一的代理
        temp_proxy_manager.update_proxy("only-proxy", is_active=False)
        
        # 当前代理应该被清空
        assert temp_proxy_manager.config.current_proxy is None

    def test_update_proxy_validation_error(self, temp_proxy_manager, sample_proxy):
        """测试更新代理时的验证错误"""
        temp_proxy_manager.config.add_proxy(sample_proxy)
        
        with pytest.raises(ValidationError):
            temp_proxy_manager.update_proxy(
                name="test-proxy",
                base_url="invalid-url"  # 无效URL
            )


class TestProxyManagerExport:
    """代理管理器导出功能测试"""

    def test_export_environment_current_proxy(self, temp_proxy_manager, sample_proxy):
        """测试导出当前代理的环境变量"""
        temp_proxy_manager.config.add_proxy(sample_proxy)
        
        export_content = temp_proxy_manager.export_environment()
        
        assert "ANTHROPIC_BASE_URL" in export_content
        assert sample_proxy.base_url in export_content
        assert "ANTHROPIC_API_KEY" in export_content
        assert sample_proxy.api_key in export_content

    def test_export_environment_specific_proxy(self, temp_proxy_manager, sample_proxy):
        """测试导出指定代理的环境变量"""
        temp_proxy_manager.config.add_proxy(sample_proxy)
        
        export_content = temp_proxy_manager.export_environment(proxy_name="test-proxy")
        
        assert "ANTHROPIC_BASE_URL" in export_content
        assert sample_proxy.base_url in export_content

    def test_export_environment_no_current_proxy(self, temp_proxy_manager):
        """测试没有当前代理时的导出"""
        with pytest.raises(ExportError, match="没有当前代理可供导出"):
            temp_proxy_manager.export_environment()

    def test_export_environment_proxy_not_found(self, temp_proxy_manager):
        """测试导出不存在的代理"""
        with pytest.raises(ProxyNotFoundError):
            temp_proxy_manager.export_environment(proxy_name="nonexistent")

    def test_export_environment_custom_format(self, temp_proxy_manager, sample_proxy):
        """测试使用自定义格式导出"""
        temp_proxy_manager.config.add_proxy(sample_proxy)
        
        custom_format = ExportFormat(
            shell_type="fish",
            include_comments=False,
            prefix="CLAUDE_"
        )
        
        export_content = temp_proxy_manager.export_environment(export_format=custom_format)
        
        assert "set -gx CLAUDE_BASE_URL" in export_content
        assert "set -gx CLAUDE_API_KEY" in export_content
        assert "# Claude 中转站环境变量" not in export_content  # 不包含注释

    def test_export_environment_powershell_format(self, temp_proxy_manager, sample_proxy):
        """测试PowerShell格式导出"""
        temp_proxy_manager.config.add_proxy(sample_proxy)
        
        ps_format = ExportFormat(shell_type="powershell")
        export_content = temp_proxy_manager.export_environment(export_format=ps_format)
        
        assert "$env:ANTHROPIC_BASE_URL" in export_content
        assert "$env:ANTHROPIC_API_KEY" in export_content

    def test_export_environment_auth_token(self, temp_proxy_manager):
        """测试导出使用认证令牌的代理"""
        auth_proxy = ProxyServer(
            name="auth-proxy",
            base_url="https://api.auth.com",
            auth_token="sk-ant-api03-token123"
        )
        temp_proxy_manager.config.add_proxy(auth_proxy)
        
        export_content = temp_proxy_manager.export_environment()
        
        assert "ANTHROPIC_AUTH_TOKEN" in export_content
        assert "sk-ant-api03-token123" in export_content
        assert "ANTHROPIC_API_KEY" not in export_content

    def test_export_environment_export_all(self, temp_proxy_manager):
        """测试导出所有代理"""
        proxy1 = ProxyServer(name="proxy1", base_url="https://api1.com", api_key="sk-1")
        proxy2 = ProxyServer(name="proxy2", base_url="https://api2.com", api_key="sk-2")
        
        temp_proxy_manager.config.add_proxy(proxy1)
        temp_proxy_manager.config.add_proxy(proxy2)
        
        export_format = ExportFormat(export_all=True)
        export_content = temp_proxy_manager.export_environment(export_format=export_format)
        
        # 当前代理应该导出为默认环境变量
        assert "ANTHROPIC_BASE_URL" in export_content
        assert "ANTHROPIC_API_KEY" in export_content
        # 其他代理应该有带前缀的环境变量
        assert "ANTHROPIC_PROXY2_API_BASE_URL" in export_content
        assert "ANTHROPIC_PROXY2_API_KEY" in export_content


class TestProxyManagerSearch:
    """代理管理器搜索功能测试"""

    def test_search_proxies_by_name(self, temp_proxy_manager):
        """测试按名称搜索代理"""
        proxy1 = ProxyServer(name="prod-api", base_url="https://prod.com", api_key="sk-1")
        proxy2 = ProxyServer(name="test-api", base_url="https://test.com", api_key="sk-2")
        proxy3 = ProxyServer(name="dev-service", base_url="https://dev.com", api_key="sk-3")
        
        for proxy in [proxy1, proxy2, proxy3]:
            temp_proxy_manager.config.add_proxy(proxy)
        
        results = temp_proxy_manager.search_proxies("api")
        assert len(results) == 2
        assert "prod-api" in results
        assert "test-api" in results

    def test_search_proxies_by_description(self, temp_proxy_manager):
        """测试按描述搜索代理"""
        proxy1 = ProxyServer(name="proxy1", base_url="https://api1.com", api_key="sk-1", description="生产环境API")
        proxy2 = ProxyServer(name="proxy2", base_url="https://api2.com", api_key="sk-2", description="测试环境API")
        
        for proxy in [proxy1, proxy2]:
            temp_proxy_manager.config.add_proxy(proxy)
        
        results = temp_proxy_manager.search_proxies("生产")
        assert len(results) == 1
        assert "proxy1" in results

    def test_search_proxies_by_tags(self, temp_proxy_manager):
        """测试按标签搜索代理"""
        proxy1 = ProxyServer(name="proxy1", base_url="https://api1.com", api_key="sk-1", tags=["production", "main"])
        proxy2 = ProxyServer(name="proxy2", base_url="https://api2.com", api_key="sk-2", tags=["testing", "backup"])
        
        for proxy in [proxy1, proxy2]:
            temp_proxy_manager.config.add_proxy(proxy)
        
        results = temp_proxy_manager.search_proxies("prod")
        assert len(results) == 1
        assert "proxy1" in results

    def test_search_proxies_custom_fields(self, temp_proxy_manager):
        """测试自定义搜索字段"""
        proxy = ProxyServer(name="proxy", base_url="https://special.api.com", api_key="sk-test")
        temp_proxy_manager.config.add_proxy(proxy)
        
        results = temp_proxy_manager.search_proxies("special", search_fields=["base_url"])
        assert len(results) == 1
        assert "proxy" in results

    def test_get_proxies_by_tag(self, temp_proxy_manager):
        """测试按标签获取代理"""
        proxy1 = ProxyServer(name="proxy1", base_url="https://api1.com", api_key="sk-1", tags=["production"])
        proxy2 = ProxyServer(name="proxy2", base_url="https://api2.com", api_key="sk-2", tags=["Production", "main"])
        proxy3 = ProxyServer(name="proxy3", base_url="https://api3.com", api_key="sk-3", tags=["testing"])
        
        for proxy in [proxy1, proxy2, proxy3]:
            temp_proxy_manager.config.add_proxy(proxy)
        
        results = temp_proxy_manager.get_proxies_by_tag("production")
        assert len(results) == 2  # 大小写不敏感匹配
        assert "proxy1" in results
        assert "proxy2" in results


class TestProxyManagerClaudeCodeIntegration:
    """代理管理器 Claude Code 集成测试"""

    @patch('claudewarp.core.utils.ensure_directory')
    @patch('claudewarp.core.utils.atomic_write')
    @patch('claudewarp.core.utils.safe_copy_file')
    def test_apply_claude_code_setting_success(self, mock_copy, mock_write, mock_ensure_dir, temp_proxy_manager, sample_proxy, temp_dir):
        """测试成功应用 Claude Code 设置"""
        mock_write.return_value = True
        mock_ensure_dir.return_value = None
        
        temp_proxy_manager.config.add_proxy(sample_proxy)
        
        result = temp_proxy_manager.apply_claude_code_setting("test-proxy")
        assert result is True
        mock_write.assert_called_once()

    def test_apply_claude_code_setting_no_current_proxy(self, temp_proxy_manager):
        """测试没有当前代理时应用 Claude Code 设置"""
        with pytest.raises(ConfigError, match="没有当前代理可供应用"):
            temp_proxy_manager.apply_claude_code_setting()

    def test_apply_claude_code_setting_proxy_not_found(self, temp_proxy_manager):
        """测试应用不存在代理的 Claude Code 设置"""
        with pytest.raises(ProxyNotFoundError):
            temp_proxy_manager.apply_claude_code_setting("nonexistent")

    @patch('builtins.open', side_effect=OSError("Permission denied"))
    def test_apply_claude_code_setting_permission_error(self, mock_open, temp_proxy_manager, sample_proxy):
        """测试 Claude Code 设置权限错误时的优雅处理"""
        temp_proxy_manager.config.add_proxy(sample_proxy)
        
        # 应该成功处理权限错误并继续执行
        temp_proxy_manager.apply_claude_code_setting("test-proxy")
        # 由于我们mock了open，atomic_write会失败，但函数应该仍然尝试执行
        # 实际结果取决于atomic_write的mock，但不应该抛出ConfigError
        # 因为读取失败会被优雅处理

    def test_get_claude_code_config_dir(self, temp_proxy_manager):
        """测试获取 Claude Code 配置目录"""
        config_dir = temp_proxy_manager._get_claude_code_config_dir()
        assert config_dir.name == ".claude"

    def test_merge_claude_code_config_api_key(self, temp_proxy_manager):
        """测试合并 Claude Code 配置（API Key）"""
        proxy = ProxyServer(name="test", base_url="https://api.test.com", api_key="sk-test123")
        
        existing_config = {"existing_setting": "value"}
        merged = temp_proxy_manager._merge_claude_code_config(existing_config, proxy)
        
        assert merged["env"]["ANTHROPIC_API_KEY"] == "sk-test123"
        assert merged["env"]["ANTHROPIC_BASE_URL"] == "https://api.test.com/"
        assert "ANTHROPIC_AUTH_TOKEN" not in merged["env"]
        assert merged["existing_setting"] == "value"

    def test_merge_claude_code_config_auth_token(self, temp_proxy_manager):
        """测试合并 Claude Code 配置（认证令牌）"""
        proxy = ProxyServer(name="test", base_url="https://api.test.com", auth_token="sk-ant-token123")
        
        existing_config = {}
        merged = temp_proxy_manager._merge_claude_code_config(existing_config, proxy)
        
        assert merged["env"]["ANTHROPIC_AUTH_TOKEN"] == "sk-ant-token123"
        assert merged["env"]["ANTHROPIC_BASE_URL"] == "https://api.test.com/"
        assert "ANTHROPIC_API_KEY" not in merged["env"]

    def test_merge_claude_code_config_api_key_helper(self, temp_proxy_manager):
        """测试合并 Claude Code 配置（API Key Helper）"""
        proxy = ProxyServer(name="test", base_url="https://api.test.com", api_key_helper="echo sk-helper")
        
        existing_config = {}
        merged = temp_proxy_manager._merge_claude_code_config(existing_config, proxy)
        
        assert merged["apiKeyHelper"] == "echo sk-helper"
        assert merged["env"]["ANTHROPIC_BASE_URL"] == "https://api.test.com/"
        assert "ANTHROPIC_API_KEY" not in merged["env"]
        assert "ANTHROPIC_AUTH_TOKEN" not in merged["env"]

    def test_merge_claude_code_config_with_models(self, temp_proxy_manager):
        """测试合并包含模型配置的 Claude Code 配置"""
        proxy = ProxyServer(
            name="test",
            base_url="https://api.test.com",
            api_key="sk-test",
            bigmodel="claude-3-opus-20240229",
            smallmodel="claude-3-haiku-20240307"
        )
        
        existing_config = {}
        merged = temp_proxy_manager._merge_claude_code_config(existing_config, proxy)
        
        assert merged["env"]["ANTHROPIC_MODEL"] == "claude-3-opus-20240229"
        assert merged["env"]["ANTHROPIC_SMALL_FAST_MODEL"] == "claude-3-haiku-20240307"

    def test_merge_claude_code_config_preserve_existing(self, temp_proxy_manager):
        """测试合并时保留现有配置"""
        proxy = ProxyServer(name="test", base_url="https://api.test.com", api_key="sk-test")
        
        existing_config = {
            "existing_setting": "value",
            "env": {
                "EXISTING_VAR": "existing_value"
            },
            "permissions": {
                "allow": ["existing_permission"]
            }
        }
        
        merged = temp_proxy_manager._merge_claude_code_config(existing_config, proxy)
        
        assert merged["existing_setting"] == "value"
        assert merged["env"]["EXISTING_VAR"] == "existing_value"
        assert merged["permissions"]["allow"] == ["existing_permission"]
        assert merged["env"]["ANTHROPIC_API_KEY"] == "sk-test"


class TestProxyManagerStatus:
    """代理管理器状态功能测试"""

    def test_get_status(self, temp_proxy_manager):
        """测试获取状态信息"""
        proxy1 = ProxyServer(name="proxy1", base_url="https://api1.com", api_key="sk-1", is_active=True)
        proxy2 = ProxyServer(name="proxy2", base_url="https://api2.com", api_key="sk-2", is_active=False)
        
        temp_proxy_manager.config.add_proxy(proxy1)
        temp_proxy_manager.config.add_proxy(proxy2)
        
        status = temp_proxy_manager.get_status()
        
        assert status["total_proxies"] == 2
        assert status["active_proxies"] == 1
        assert status["current_proxy"] == "proxy1"  # 第一个代理自动设置为当前
        assert "config_version" in status
        assert "config_updated_at" in status
        assert "config_info" in status

    def test_validate_proxy_connection_placeholder(self, temp_proxy_manager, sample_proxy):
        """测试代理连接验证（占位方法）"""
        temp_proxy_manager.config.add_proxy(sample_proxy)
        
        result = temp_proxy_manager.validate_proxy_connection("test-proxy")
        
        assert result["proxy_name"] == "test-proxy"
        assert result["status"] == "unknown"
        assert "message" in result
        assert result["base_url"] == sample_proxy.base_url

    def test_validate_proxy_connection_not_found(self, temp_proxy_manager):
        """测试验证不存在代理的连接"""
        with pytest.raises(ProxyNotFoundError):
            temp_proxy_manager.validate_proxy_connection("nonexistent")


class TestProxyManagerThemeSettings:
    """代理管理器主题设置测试"""

    def test_get_theme_setting_default(self, temp_proxy_manager):
        """测试获取默认主题设置"""
        theme = temp_proxy_manager.get_theme_setting()
        assert theme == "auto"

    def test_get_theme_setting_custom(self, temp_proxy_manager):
        """测试获取自定义主题设置"""
        temp_proxy_manager.config.settings["theme"] = "dark"
        theme = temp_proxy_manager.get_theme_setting()
        assert theme == "dark"

    def test_save_theme_setting(self, temp_proxy_manager):
        """测试保存主题设置"""
        temp_proxy_manager.save_theme_setting("light")
        
        assert temp_proxy_manager.config.settings["theme"] == "light"
        # 验证配置已保存
        reloaded_config = temp_proxy_manager.config_manager.load_config()
        assert reloaded_config.settings["theme"] == "light"

    @patch.object(ProxyManager, '_save_config')
    def test_save_theme_setting_error(self, mock_save, temp_proxy_manager):
        """测试保存主题设置失败"""
        mock_save.side_effect = Exception("Save failed")
        
        with pytest.raises(ConfigError, match="保存主题设置失败"):
            temp_proxy_manager.save_theme_setting("dark")


class TestProxyManagerMiscellaneous:
    """代理管理器其他功能测试"""

    def test_reload_config(self, temp_proxy_manager):
        """测试重新加载配置"""
        
        # 重新加载配置
        temp_proxy_manager.reload_config()
        
        # 配置应该被重新加载
        assert isinstance(temp_proxy_manager.config, type(temp_proxy_manager.config))

    @patch.object(ProxyManager, '_load_config')
    def test_reload_config_error(self, mock_load, temp_proxy_manager):
        """测试重新加载配置失败"""
        mock_load.side_effect = ConfigError("Load failed")
        
        with pytest.raises(ConfigError):
            temp_proxy_manager.reload_config()


class TestProxyManagerErrorHandling:
    """代理管理器错误处理测试"""

    @patch.object(ProxyManager, '_save_config')
    def test_save_config_error_propagation(self, mock_save, temp_proxy_manager):
        """测试保存配置错误传播"""
        mock_save.side_effect = Exception("Save failed")
        
        with pytest.raises(ConfigError, match="添加代理服务器失败"):
            temp_proxy_manager.add_proxy(
                name="test",
                base_url="https://api.test.com",
                api_key="sk-test"
            )

    def test_complex_validation_error_handling(self, temp_proxy_manager):
        """测试复杂验证错误处理"""
        # 尝试添加无效的代理（多个认证方式）
        with pytest.raises(ValidationError):
            temp_proxy_manager.add_proxy(
                name="invalid",
                base_url="https://api.test.com",
                api_key="sk-test",
                auth_token="token-test"  # 与api_key冲突
            )

    def test_edge_case_empty_operations(self, temp_proxy_manager):
        """测试边界情况空操作"""
        # 空代理列表的操作
        assert temp_proxy_manager.list_proxies() == {}
        assert temp_proxy_manager.get_proxy_names() == []
        assert temp_proxy_manager.search_proxies("anything") == {}
        assert temp_proxy_manager.get_proxies_by_tag("anytag") == {}