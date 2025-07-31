"""
Claude Code集成功能增强测试

专门测试与Claude Code的集成功能，包括配置文件生成、环境变量设置等。
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from typing import Dict, Any

import pytest

from claudewarp.core.manager import ProxyManager
from claudewarp.core.models import ProxyServer, ExportFormat
from claudewarp.core.exceptions import ConfigError, ProxyNotFoundError


class TestClaudeCodeIntegration:
    """测试Claude Code集成功能"""

    @pytest.fixture
    def temp_manager(self):
        """临时管理器fixture"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.toml"
            manager = ProxyManager(config_path=config_path)
            yield manager

    @pytest.fixture
    def sample_proxies(self, temp_manager):
        """创建示例代理"""
        proxies = []
        
        # API Key代理
        api_proxy = ProxyServer(
            name="api-key-proxy",
            base_url="https://api-key.example.com/",
            api_key="sk-1234567890abcdef1234567890abcdef",
            description="API密钥代理",
            tags=["api-key", "test"],
            bigmodel="claude-3-5-sonnet-20241022",
            smallmodel="claude-3-haiku-20240307"
        )
        temp_manager.add_proxy(api_proxy)
        proxies.append(api_proxy)
        
        # Auth Token代理
        auth_proxy = ProxyServer(
            name="auth-token-proxy",
            base_url="https://auth-token.example.com/",
            auth_token="sk-ant-api03-abcdef1234567890abcdef1234567890abcdef",
            description="认证令牌代理",
            tags=["auth-token", "test"]
        )
        temp_manager.add_proxy(auth_proxy)
        proxies.append(auth_proxy)
        
        # API Key Helper代理
        helper_proxy = ProxyServer(
            name="helper-proxy",
            base_url="https://helper.example.com/",
            api_key_helper="echo 'sk-dynamic-key-12345'",
            description="API密钥助手代理",
            tags=["helper", "dynamic", "test"]
        )
        temp_manager.add_proxy(helper_proxy)
        proxies.append(helper_proxy)
        
        return proxies

    def test_claude_config_directory_detection(self, temp_manager):
        """测试Claude Code配置目录检测"""
        config_dir = temp_manager._get_claude_code_config_dir()
        
        assert isinstance(config_dir, Path)
        assert config_dir.name == ".claude"
        assert "claude" in str(config_dir).lower()

    def test_generate_claude_code_config_api_key(self, temp_manager, sample_proxies):
        """测试生成API密钥类型的Claude Code配置"""
        api_proxy = sample_proxies[0]  # API Key代理
        
        config = temp_manager._generate_claude_code_config(api_proxy)
        
        assert isinstance(config, dict)
        assert "env" in config
        assert "permissions" in config
        
        env = config["env"]
        assert "ANTHROPIC_API_KEY" in env
        assert "ANTHROPIC_BASE_URL" in env
        assert "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC" in env
        assert "ANTHROPIC_MODEL" in env
        assert "ANTHROPIC_SMALL_FAST_MODEL" in env
        
        # 验证值
        assert env["ANTHROPIC_API_KEY"] == api_proxy.api_key
        assert env["ANTHROPIC_BASE_URL"] == api_proxy.base_url
        assert env["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] == 1
        assert env["ANTHROPIC_MODEL"] == api_proxy.bigmodel
        assert env["ANTHROPIC_SMALL_FAST_MODEL"] == api_proxy.smallmodel
        
        # 不应该有AUTH_TOKEN
        assert "ANTHROPIC_AUTH_TOKEN" not in env

    def test_generate_claude_code_config_auth_token(self, temp_manager, sample_proxies):
        """测试生成认证令牌类型的Claude Code配置"""
        auth_proxy = sample_proxies[1]  # Auth Token代理
        
        config = temp_manager._generate_claude_code_config(auth_proxy)
        
        env = config["env"]
        assert "ANTHROPIC_AUTH_TOKEN" in env
        assert "ANTHROPIC_BASE_URL" in env
        assert "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC" in env
        
        # 验证值
        assert env["ANTHROPIC_AUTH_TOKEN"] == auth_proxy.auth_token
        assert env["ANTHROPIC_BASE_URL"] == auth_proxy.base_url
        assert env["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] == 1
        
        # 不应该有API_KEY
        assert "ANTHROPIC_API_KEY" not in env
        
        # 没有配置模型，不应该有模型环境变量
        assert "ANTHROPIC_MODEL" not in env
        assert "ANTHROPIC_SMALL_FAST_MODEL" not in env

    def test_merge_claude_code_config_new_file(self, temp_manager, sample_proxies):
        """测试合并Claude Code配置（新文件）"""
        api_proxy = sample_proxies[0]
        
        existing_config = {}  # 空配置，模拟新文件
        merged_config = temp_manager._merge_claude_code_config(existing_config, api_proxy)
        
        assert "env" in merged_config
        assert "permissions" in merged_config
        
        env = merged_config["env"]
        assert env["ANTHROPIC_API_KEY"] == api_proxy.api_key
        assert env["ANTHROPIC_BASE_URL"] == api_proxy.base_url
        
        # 应该设置默认权限
        permissions = merged_config["permissions"]
        assert "allow" in permissions
        assert "deny" in permissions

    def test_merge_claude_code_config_existing_file(self, temp_manager, sample_proxies):
        """测试合并Claude Code配置（现有文件）"""
        api_proxy = sample_proxies[0]
        
        # 模拟现有配置
        existing_config = {
            "env": {
                "OTHER_VAR": "other_value",
                "ANTHROPIC_AUTH_TOKEN": "old-token",  # 应该被清除
                "ANTHROPIC_MODEL": "old-model"  # 应该被覆盖
            },
            "permissions": {
                "allow": ["existing_permission"],
                "deny": ["some_restriction"]
            },
            "other_setting": "should_be_preserved"
        }
        
        merged_config = temp_manager._merge_claude_code_config(existing_config, api_proxy)
        
        # 验证环境变量
        env = merged_config["env"]
        assert env["OTHER_VAR"] == "other_value"  # 保留现有变量
        assert env["ANTHROPIC_API_KEY"] == api_proxy.api_key  # 新的API密钥
        assert env["ANTHROPIC_BASE_URL"] == api_proxy.base_url  # 新的基础URL
        assert env["ANTHROPIC_MODEL"] == api_proxy.bigmodel  # 覆盖模型
        assert "ANTHROPIC_AUTH_TOKEN" not in env  # 清除冲突的认证方式
        
        # 验证权限被保留
        permissions = merged_config["permissions"]
        assert permissions["allow"] == ["existing_permission"]
        assert permissions["deny"] == ["some_restriction"]
        
        # 验证其他设置被保留
        assert merged_config["other_setting"] == "should_be_preserved"

    def test_merge_claude_code_config_auth_method_switch(self, temp_manager, sample_proxies):
        """测试认证方式切换时的配置合并"""
        auth_proxy = sample_proxies[1]  # Auth Token代理
        
        # 现有配置使用API密钥
        existing_config = {
            "env": {
                "ANTHROPIC_API_KEY": "old-api-key",
                "ANTHROPIC_BASE_URL": "https://old.example.com/",
                "OTHER_VAR": "preserve_me"
            }
        }
        
        merged_config = temp_manager._merge_claude_code_config(existing_config, auth_proxy)
        
        env = merged_config["env"]
        
        # 应该切换到AUTH_TOKEN
        assert "ANTHROPIC_AUTH_TOKEN" in env
        assert env["ANTHROPIC_AUTH_TOKEN"] == auth_proxy.auth_token
        
        # 应该清除API_KEY
        assert "ANTHROPIC_API_KEY" not in env
        
        # 应该更新BASE_URL
        assert env["ANTHROPIC_BASE_URL"] == auth_proxy.base_url
        
        # 应该保留其他变量
        assert env["OTHER_VAR"] == "preserve_me"

    @patch('claudewarp.core.manager.Path.exists')
    @patch('claudewarp.core.manager.open', new_callable=mock_open)
    @patch('claudewarp.core.utils.atomic_write')
    @patch('claudewarp.core.utils.ensure_directory')
    def test_apply_claude_code_setting_success(
        self, mock_ensure_dir, mock_atomic_write, mock_file, mock_exists, 
        temp_manager, sample_proxies
    ):
        """测试成功应用Claude Code设置"""
        mock_exists.return_value = False  # 配置文件不存在
        mock_atomic_write.return_value = True
        
        api_proxy = sample_proxies[0]
        temp_manager.switch_proxy(api_proxy.name)
        
        result = temp_manager.apply_claude_code_setting()
        
        assert result is True
        mock_ensure_dir.assert_called_once()
        mock_atomic_write.assert_called_once()
        
        # 验证写入的内容
        call_args = mock_atomic_write.call_args
        written_content = call_args[0][1]  # 第二个参数是内容
        
        assert isinstance(written_content, str)
        config_data = json.loads(written_content)
        
        assert "env" in config_data
        assert "ANTHROPIC_API_KEY" in config_data["env"]
        assert config_data["env"]["ANTHROPIC_API_KEY"] == api_proxy.api_key

    @patch('claudewarp.core.manager.Path.exists')
    @patch('claudewarp.core.manager.open', new_callable=mock_open, read_data='{"env": {"OLD_VAR": "old_value"}}')
    @patch('claudewarp.core.utils.atomic_write')
    @patch('claudewarp.core.utils.ensure_directory')
    @patch('claudewarp.core.utils.safe_copy_file')
    def test_apply_claude_code_setting_with_existing_config(
        self, mock_copy, mock_ensure_dir, mock_atomic_write, mock_file, mock_exists,
        temp_manager, sample_proxies
    ):
        """测试应用Claude Code设置到现有配置"""
        mock_exists.side_effect = lambda path: "settings.json" in str(path) and not "bak" in str(path)
        mock_atomic_write.return_value = True
        mock_copy.return_value = True
        
        auth_proxy = sample_proxies[1]
        temp_manager.switch_proxy(auth_proxy.name)
        
        result = temp_manager.apply_claude_code_setting()
        
        assert result is True
        
        # 应该创建备份
        mock_copy.assert_called_once()
        
        # 验证合并后的配置
        call_args = mock_atomic_write.call_args
        written_content = call_args[0][1]
        config_data = json.loads(written_content)
        
        # 应该保留旧变量
        assert config_data["env"]["OLD_VAR"] == "old_value"
        
        # 应该添加新的认证信息
        assert "ANTHROPIC_AUTH_TOKEN" in config_data["env"]
        assert config_data["env"]["ANTHROPIC_AUTH_TOKEN"] == auth_proxy.auth_token

    def test_apply_claude_code_setting_specific_proxy(self, temp_manager, sample_proxies):
        """测试应用指定代理的Claude Code设置"""
        with patch('claudewarp.core.utils.ensure_directory'), \
             patch('claudewarp.core.manager.Path.exists', return_value=False), \
             patch('claudewarp.core.utils.atomic_write', return_value=True) as mock_write:
            
            # 不设置当前代理，直接指定代理名称
            result = temp_manager.apply_claude_code_setting(proxy_name="auth-token-proxy")
            
            assert result is True
            
            # 验证使用了指定的代理
            call_args = mock_write.call_args
            written_content = call_args[0][1]
            config_data = json.loads(written_content)
            
            auth_proxy = sample_proxies[1]  # auth-token-proxy
            assert config_data["env"]["ANTHROPIC_AUTH_TOKEN"] == auth_proxy.auth_token

    def test_apply_claude_code_setting_no_current_proxy(self, temp_manager):
        """测试没有当前代理时应用Claude Code设置"""
        # 没有设置当前代理，也没有指定代理名称
        with pytest.raises(ConfigError, match="没有当前代理可供应用"):
            temp_manager.apply_claude_code_setting()

    def test_apply_claude_code_setting_proxy_not_found(self, temp_manager):
        """测试指定不存在的代理应用Claude Code设置"""
        with pytest.raises(ProxyNotFoundError):
            temp_manager.apply_claude_code_setting(proxy_name="nonexistent-proxy")

    @patch('claudewarp.core.utils.atomic_write')
    def test_apply_claude_code_setting_write_failure(self, mock_write, temp_manager, sample_proxies):
        """测试Claude Code配置写入失败"""
        mock_write.return_value = False
        
        api_proxy = sample_proxies[0]
        temp_manager.switch_proxy(api_proxy.name)
        
        with patch('claudewarp.core.utils.ensure_directory'), \
             patch('claudewarp.core.manager.Path.exists', return_value=False):
            
            with pytest.raises(ConfigError, match="写入 Claude Code 配置文件失败"):
                temp_manager.apply_claude_code_setting()

    def test_claude_code_config_model_handling(self, temp_manager):
        """测试Claude Code配置中的模型处理"""
        # 只有大模型的代理
        proxy_big_only = ProxyServer(
            name="big-model-only",
            base_url="https://big-only.example.com/",
            api_key="sk-1234567890abcdef",
            bigmodel="claude-3-5-sonnet-20241022"
        )
        temp_manager.add_proxy(proxy_big_only)
        
        config = temp_manager._generate_claude_code_config(proxy_big_only)
        env = config["env"]
        
        assert "ANTHROPIC_MODEL" in env
        assert env["ANTHROPIC_MODEL"] == "claude-3-5-sonnet-20241022"
        assert "ANTHROPIC_SMALL_FAST_MODEL" not in env
        
        # 只有小模型的代理
        proxy_small_only = ProxyServer(
            name="small-model-only",
            base_url="https://small-only.example.com/",
            api_key="sk-1234567890abcdef",
            smallmodel="claude-3-haiku-20240307"
        )
        temp_manager.add_proxy(proxy_small_only)
        
        config = temp_manager._generate_claude_code_config(proxy_small_only)
        env = config["env"]
        
        assert "ANTHROPIC_SMALL_FAST_MODEL" in env
        assert env["ANTHROPIC_SMALL_FAST_MODEL"] == "claude-3-haiku-20240307"
        assert "ANTHROPIC_MODEL" not in env
        
        # 没有模型的代理
        proxy_no_model = ProxyServer(
            name="no-model",
            base_url="https://no-model.example.com/",
            api_key="sk-1234567890abcdef"
        )
        temp_manager.add_proxy(proxy_no_model)
        
        config = temp_manager._generate_claude_code_config(proxy_no_model)
        env = config["env"]
        
        assert "ANTHROPIC_MODEL" not in env
        assert "ANTHROPIC_SMALL_FAST_MODEL" not in env

    def test_claude_code_integration_with_proxy_switching(self, temp_manager, sample_proxies):
        """测试代理切换与Claude Code集成"""
        with patch('claudewarp.core.utils.ensure_directory'), \
             patch('claudewarp.core.manager.Path.exists', return_value=False), \
             patch('claudewarp.core.utils.atomic_write', return_value=True) as mock_write:
            
            # 切换到API密钥代理
            api_proxy = sample_proxies[0]
            result = temp_manager.switch_proxy(api_proxy.name)
            assert result is True
            
            # 应该自动调用Claude Code设置
            assert mock_write.call_count >= 1
            
            # 验证最后一次写入的内容
            last_call = mock_write.call_args
            written_content = last_call[0][1]
            config_data = json.loads(written_content)
            
            assert "ANTHROPIC_API_KEY" in config_data["env"]
            assert config_data["env"]["ANTHROPIC_API_KEY"] == api_proxy.api_key

    @patch('claudewarp.core.manager.ProxyManager.apply_claude_code_setting')
    def test_proxy_switching_claude_code_failure_handling(self, mock_apply, temp_manager, sample_proxies):
        """测试代理切换时Claude Code集成失败的处理"""
        # 模拟Claude Code设置失败
        mock_apply.side_effect = Exception("Claude Code设置失败")
        
        api_proxy = sample_proxies[0]
        
        # 代理切换应该成功，即使Claude Code集成失败
        result = temp_manager.switch_proxy(api_proxy.name)
        assert result is True
        
        # 验证代理确实切换了
        current_proxy = temp_manager.get_current_proxy()
        assert current_proxy.name == api_proxy.name
        
        # Claude Code设置应该被调用（但失败了）
        mock_apply.assert_called_once()


class TestEnvironmentVariableExportEnhanced:
    """增强的环境变量导出测试"""

    @pytest.fixture
    def temp_manager_with_diverse_proxies(self):
        """创建包含多种类型代理的临时管理器"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.toml"
            manager = ProxyManager(config_path=config_path)
            
            # 添加各种类型的代理
            proxies = [
                ProxyServer(
                    name="api-key-basic",
                    base_url="https://api1.example.com/",
                    api_key="sk-basic-key-1234567890",
                    description="基础API密钥代理"
                ),
                ProxyServer(
                    name="auth-token-advanced",
                    base_url="https://api2.example.com/",
                    auth_token="sk-ant-api03-advanced-token-123456",
                    description="高级认证令牌代理",
                    tags=["advanced", "auth"]
                ),
                ProxyServer(
                    name="helper-dynamic",
                    base_url="https://api3.example.com/",
                    api_key_helper="get-dynamic-key.sh",
                    description="动态密钥助手代理",
                    tags=["dynamic", "helper"]
                ),
                ProxyServer(
                    name="full-featured",
                    base_url="https://api4.example.com/",
                    api_key="sk-full-featured-key-1234",
                    description="全功能代理",
                    tags=["full", "featured", "production"],
                    bigmodel="claude-3-5-sonnet-20241022",
                    smallmodel="claude-3-haiku-20240307"
                )
            ]
            
            for proxy in proxies:
                manager.add_proxy(proxy)
            
            yield manager

    def test_export_environment_all_auth_methods(self, temp_manager_with_diverse_proxies):
        """测试所有认证方法的环境变量导出"""
        manager = temp_manager_with_diverse_proxies
        
        # 测试API密钥类型
        content = manager.export_environment(proxy_name="api-key-basic")
        assert "export ANTHROPIC_API_KEY=" in content
        assert "sk-basic-key-1234567890" in content
        assert "ANTHROPIC_AUTH_TOKEN" not in content
        
        # 测试认证令牌类型
        content = manager.export_environment(proxy_name="auth-token-advanced")
        assert "export ANTHROPIC_AUTH_TOKEN=" in content
        assert "sk-ant-api03-advanced-token-123456" in content
        assert "ANTHROPIC_API_KEY" not in content
        
        # 测试API密钥助手类型
        content = manager.export_environment(proxy_name="helper-dynamic")
        assert "export ANTHROPIC_API_KEY=" in content  # 助手也使用API_KEY变量
        assert "get-dynamic-key.sh" in content

    def test_export_environment_all_shell_formats(self, temp_manager_with_diverse_proxies):
        """测试所有Shell格式的环境变量导出"""
        manager = temp_manager_with_diverse_proxies
        manager.switch_proxy("full-featured")
        
        # Bash格式
        bash_format = ExportFormat(shell_type="bash", include_comments=True)
        bash_content = manager.export_environment(bash_format)
        assert "export ANTHROPIC_BASE_URL=" in bash_content
        assert "export ANTHROPIC_API_KEY=" in bash_content
        assert "# Claude 中转站环境变量" in bash_content
        
        # Fish格式
        fish_format = ExportFormat(shell_type="fish", include_comments=True)
        fish_content = manager.export_environment(fish_format)
        assert "set -gx ANTHROPIC_BASE_URL" in fish_content
        assert "set -gx ANTHROPIC_API_KEY" in fish_content
        assert "# Claude 中转站环境变量" in fish_content
        
        # PowerShell格式
        ps_format = ExportFormat(shell_type="powershell", include_comments=True)
        ps_content = manager.export_environment(ps_format)
        assert "$env:ANTHROPIC_BASE_URL=" in ps_content
        assert "$env:ANTHROPIC_API_KEY=" in ps_content
        assert "# Claude 中转站环境变量" in ps_content
        
        # Zsh格式（应该与Bash相同）
        zsh_format = ExportFormat(shell_type="zsh", include_comments=False)
        zsh_content = manager.export_environment(zsh_format)
        assert "export ANTHROPIC_BASE_URL=" in zsh_content
        assert "export ANTHROPIC_API_KEY=" in zsh_content
        assert "# Claude 中转站环境变量" not in zsh_content

    def test_export_environment_custom_prefix(self, temp_manager_with_diverse_proxies):
        """测试自定义前缀的环境变量导出"""
        manager = temp_manager_with_diverse_proxies
        manager.switch_proxy("api-key-basic")
        
        custom_format = ExportFormat(
            shell_type="bash",
            prefix="CUSTOM_AI_",
            include_comments=False
        )
        
        content = manager.export_environment(custom_format)
        
        assert "export CUSTOM_AI_BASE_URL=" in content
        assert "export CUSTOM_AI_API_KEY=" in content
        assert "ANTHROPIC_" not in content  # 不应该有默认前缀
        assert "https://api1.example.com/" in content
        assert "sk-basic-key-1234567890" in content

    def test_export_environment_export_all_option(self, temp_manager_with_diverse_proxies):
        """测试导出所有代理选项"""
        manager = temp_manager_with_diverse_proxies
        manager.switch_proxy("api-key-basic")
        
        export_all_format = ExportFormat(
            shell_type="bash",
            export_all=True,
            include_comments=True
        )
        
        content = manager.export_environment(export_all_format)
        
        # 应该包含当前代理的标准变量
        assert "export ANTHROPIC_BASE_URL=" in content
        assert "export ANTHROPIC_API_KEY=" in content
        
        # 应该包含所有其他代理的变量
        assert "FULL_FEATURED_API_BASE_URL=" in content
        assert "AUTH_TOKEN_ADVANCED_API_BASE_URL=" in content
        assert "HELPER_DYNAMIC_API_BASE_URL=" in content
        
        # 验证不同认证方式的处理
        assert "FULL_FEATURED_API_KEY=" in content
        assert "AUTH_TOKEN_ADVANCED_AUTH_TOKEN=" in content
        assert "HELPER_DYNAMIC_API_KEY=" in content
        
        # 应该包含注释
        assert "所有可用代理" in content

    def test_export_environment_with_special_characters(self, temp_manager_with_diverse_proxies):
        """测试包含特殊字符的导出"""
        manager = temp_manager_with_diverse_proxies
        
        # 添加包含特殊字符的代理
        special_proxy = ProxyServer(
            name="special-chars",
            base_url="https://api-special.example.com/v1/",
            api_key="sk-special!@#$%^&*()_+-=[]{}|;:,.<>?",
            description="包含特殊字符的代理: !@#$%^&*()"
        )
        manager.add_proxy(special_proxy)
        
        content = manager.export_environment(proxy_name="special-chars")
        
        # 特殊字符应该被正确转义或处理
        assert "sk-special!@#$%^&*()_+-=[]{}|;:,.<>?" in content
        assert "包含特殊字符的代理" in content
        
        # URL中的特殊字符应该保持
        assert "https://api-special.example.com/v1/" in content

    def test_export_environment_unicode_support(self, temp_manager_with_diverse_proxies):
        """测试Unicode字符支持"""
        manager = temp_manager_with_diverse_proxies
        
        # 添加包含Unicode的代理
        unicode_proxy = ProxyServer(
            name="unicode-proxy",
            base_url="https://api-unicode.example.com/",
            api_key="sk-unicode-测试-1234567890",
            description="Unicode测试代理: 中文 русский العربية 🌍"
        )
        manager.add_proxy(unicode_proxy)
        
        content = manager.export_environment(proxy_name="unicode-proxy")
        
        # Unicode字符应该被正确处理
        assert "sk-unicode-测试-1234567890" in content
        assert "Unicode测试代理: 中文 русский العربية 🌍" in content

    def test_export_environment_empty_values_handling(self, temp_manager_with_diverse_proxies):
        """测试空值处理"""
        manager = temp_manager_with_diverse_proxies
        
        # 添加包含空值的代理
        empty_proxy = ProxyServer(
            name="empty-values",
            base_url="https://api-empty.example.com/",
            api_key="sk-empty-test-1234567890",
            description="",  # 空描述
            tags=[]  # 空标签
        )
        manager.add_proxy(empty_proxy)
        
        content = manager.export_environment(proxy_name="empty-values")
        
        # 基本变量应该存在
        assert "export ANTHROPIC_BASE_URL=" in content
        assert "export ANTHROPIC_API_KEY=" in content
        
        # 空描述的注释处理
        assert "代理名称: empty-values" in content
        # 描述为空时不应该显示描述行，或显示空的描述行
        
        # 空标签不应该影响导出
        assert "https://api-empty.example.com/" in content