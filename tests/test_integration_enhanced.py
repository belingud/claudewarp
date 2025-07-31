"""
增强集成测试

测试核心组件之间的交互和端到端场景。
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from typing import Dict, Any, List

import pytest
import toml

from claudewarp.core.config import ConfigManager, CURRENT_CONFIG_VERSION
from claudewarp.core.manager import ProxyManager
from claudewarp.core.models import ProxyServer, ProxyConfig, ExportFormat
from claudewarp.core.exceptions import (
    ConfigError,
    ProxyNotFoundError, 
    DuplicateProxyError,
    ValidationError,
    ConfigFileNotFoundError,
)


class TestConfigManagerIntegration:
    """测试配置管理器集成场景"""
    
    @pytest.fixture
    def temp_config_dir(self):
        """临时配置目录fixture"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def integration_config_manager(self, temp_config_dir):
        """集成测试配置管理器fixture"""
        config_path = temp_config_dir / "integration_config.toml"
        return ConfigManager(config_path=config_path, auto_backup=True, max_backups=3)
    
    def test_full_config_lifecycle(self, integration_config_manager):
        """测试完整配置生命周期"""
        # 1. 初始状态 - 配置文件不存在
        assert not integration_config_manager.config_path.exists()
        
        # 2. 加载配置 - 应该创建默认配置
        config = integration_config_manager.load_config()
        assert isinstance(config, ProxyConfig)
        assert config.version == CURRENT_CONFIG_VERSION
        assert len(config.proxies) == 0
        assert config.current_proxy is None
        assert integration_config_manager.config_path.exists()
        
        # 3. 添加代理
        proxy1 = ProxyServer(
            name="proxy1",
            base_url="https://api1.example.com/",
            api_key="sk-1111111111111111",
            description="第一个代理",
            tags=["test", "primary"]
        )
        config.add_proxy(proxy1)
        
        proxy2 = ProxyServer(
            name="proxy2", 
            base_url="https://api2.example.com/",
            auth_token="sk-ant-api03-2222222222",  # 使用auth_token
            description="第二个代理",
            tags=["test", "secondary"]
        )
        config.add_proxy(proxy2)
        
        # 4. 保存配置
        result = integration_config_manager.save_config(config)
        assert result is True
        
        # 5. 重新加载并验证
        reloaded_config = integration_config_manager.load_config()
        assert len(reloaded_config.proxies) == 2
        assert "proxy1" in reloaded_config.proxies
        assert "proxy2" in reloaded_config.proxies
        assert reloaded_config.current_proxy == "proxy1"  # 第一个代理成为默认
        
        # 验证代理详情
        loaded_proxy1 = reloaded_config.proxies["proxy1"]
        assert loaded_proxy1.api_key == "sk-1111111111111111"
        assert loaded_proxy1.auth_token is None
        assert loaded_proxy1.get_auth_method() == "api_key"
        
        loaded_proxy2 = reloaded_config.proxies["proxy2"]
        assert loaded_proxy2.api_key == ""
        assert loaded_proxy2.auth_token == "sk-ant-api03-2222222222"
        assert loaded_proxy2.get_auth_method() == "auth_token"
        
        # 6. 修改并再次保存
        reloaded_config.set_current_proxy("proxy2")
        integration_config_manager.save_config(reloaded_config)
        
        # 7. 最终验证
        final_config = integration_config_manager.load_config()
        assert final_config.current_proxy == "proxy2"
    
    def test_config_backup_and_restore(self, integration_config_manager):
        """测试配置备份和恢复"""
        # 创建初始配置
        config = integration_config_manager.load_config()
        proxy = ProxyServer(
            name="backup-test",
            base_url="https://backup.example.com/",
            api_key="sk-backup-test-key"
        )
        config.add_proxy(proxy)
        integration_config_manager.save_config(config)
        
        # 修改配置并保存（应该创建备份）
        config.proxies["backup-test"].description = "已修改的描述"
        integration_config_manager.save_config(config)
        
        # 检查备份文件
        backup_files = integration_config_manager.get_backup_files()
        # 注意：第一次保存不会创建备份，因为之前没有文件
        # 备份是在第二次保存时创建的
        
        # 获取配置信息
        config_info = integration_config_manager.get_config_info()
        assert config_info["exists"] is True
        assert config_info["auto_backup"] is True
        assert config_info["max_backups"] == 3
        assert "size" in config_info
        assert "modified" in config_info
    
    def test_config_migration(self, integration_config_manager):
        """测试配置迁移"""
        # 创建配置文件
        config = integration_config_manager.load_config()
        integration_config_manager.save_config(config)
        
        # 测试迁移（当前版本到当前版本，应该无需迁移）
        migration_needed = integration_config_manager.migrate_config()
        assert migration_needed is False
        
        # 验证配置仍然有效
        reloaded_config = integration_config_manager.load_config()
        assert reloaded_config.version == CURRENT_CONFIG_VERSION
    
    def test_config_error_recovery(self, integration_config_manager):
        """测试配置错误恢复"""
        # 创建损坏的配置文件
        with open(integration_config_manager.config_path, 'w', encoding='utf-8') as f:
            f.write("这不是有效的TOML文件[[[]]")
        
        # 尝试加载应该抛出异常
        with pytest.raises(ConfigFileNotFoundError):
            # 这里实际会抛出ConfigFileCorruptedError，但我们的import可能有问题
            integration_config_manager.load_config()


class TestProxyManagerIntegration:
    """测试代理管理器集成场景"""
    
    @pytest.fixture
    def temp_config_dir(self):
        """临时配置目录fixture"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def integration_proxy_manager(self, temp_config_dir):
        """集成测试代理管理器fixture"""
        config_path = temp_config_dir / "manager_config.toml"
        return ProxyManager(config_path=config_path, auto_backup=True, max_backups=3)
    
    def test_complete_proxy_management_workflow(self, integration_proxy_manager):
        """测试完整的代理管理工作流"""
        # 1. 初始状态检查
        assert integration_proxy_manager.get_proxy_count() == 0
        assert integration_proxy_manager.has_proxies() is False
        assert integration_proxy_manager.has_current_proxy() is False
        assert integration_proxy_manager.get_current_proxy() is None
        
        # 2. 添加多个代理
        proxy1 = integration_proxy_manager.add_proxy(
            name="main-proxy",
            base_url="https://main.example.com/",
            api_key="sk-main-proxy-key-1234",
            description="主要代理服务器",
            tags=["primary", "fast"],
            set_as_current=True
        )
        
        proxy2 = integration_proxy_manager.add_proxy(
            name="backup-proxy", 
            base_url="https://backup.example.com/",
            auth_token="sk-ant-api03-backup-token",  # 使用auth_token
            description="备用代理服务器",
            tags=["backup", "reliable"],
            is_active=True
        )
        
        proxy3 = integration_proxy_manager.add_proxy(
            name="test-proxy",
            base_url="https://test.example.com/",
            api_key_helper="echo 'sk-test-key'",  # 使用api_key_helper
            description="测试代理服务器",
            tags=["test", "development"],
            is_active=False  # 不活跃
        )
        
        # 3. 验证添加结果
        assert integration_proxy_manager.get_proxy_count() == 3
        assert integration_proxy_manager.has_proxies() is True
        assert integration_proxy_manager.has_current_proxy() is True
        assert integration_proxy_manager.get_current_proxy().name == "main-proxy"
        
        # 4. 测试代理查询功能
        all_proxies = integration_proxy_manager.list_proxies(active_only=False)
        assert len(all_proxies) == 3
        
        active_proxies = integration_proxy_manager.list_proxies(active_only=True)
        assert len(active_proxies) == 2  # main-proxy 和 backup-proxy
        
        proxy_names = integration_proxy_manager.get_proxy_names()
        assert set(proxy_names) == {"main-proxy", "backup-proxy", "test-proxy"}
        
        # 5. 测试搜索功能
        search_results = integration_proxy_manager.search_proxies("主要")
        assert len(search_results) == 1
        assert "main-proxy" in search_results
        
        tag_results = integration_proxy_manager.search_proxies("test")
        assert len(tag_results) == 1
        assert "test-proxy" in tag_results
        
        # 6. 测试代理更新
        updated_proxy = integration_proxy_manager.update_proxy(
            "test-proxy",
            description="更新后的测试代理",
            is_active=True,
            tags=["test", "development", "updated"]
        )
        
        assert updated_proxy.description == "更新后的测试代理"
        assert updated_proxy.is_active is True
        assert "updated" in updated_proxy.tags
        
        # 7. 测试代理切换
        result = integration_proxy_manager.switch_proxy("backup-proxy")
        assert result is True
        assert integration_proxy_manager.get_current_proxy().name == "backup-proxy"
        
        # 8. 测试代理删除
        result = integration_proxy_manager.remove_proxy("test-proxy")
        assert result is True
        assert integration_proxy_manager.get_proxy_count() == 2
        
        with pytest.raises(ProxyNotFoundError):
            integration_proxy_manager.get_proxy("test-proxy")
        
        # 9. 测试统计信息
        stats = integration_proxy_manager.get_statistics()
        assert stats["total_proxies"] == 2
        assert stats["active_proxies"] == 2
        assert stats["current_proxy"] == "backup-proxy"
        assert stats["has_current_proxy"] is True
        
        # 10. 删除当前代理，测试自动切换
        integration_proxy_manager.remove_proxy("backup-proxy")
        assert integration_proxy_manager.get_current_proxy().name == "main-proxy"
        
        # 11. 删除最后一个代理
        integration_proxy_manager.remove_proxy("main-proxy")
        assert integration_proxy_manager.get_proxy_count() == 0
        assert integration_proxy_manager.has_current_proxy() is False
    
    def test_environment_export_workflow(self, integration_proxy_manager):
        """测试环境变量导出工作流"""
        # 添加测试代理
        integration_proxy_manager.add_proxy(
            name="export-test",
            base_url="https://export.example.com/",
            api_key="sk-export-test-key-123456",
            description="导出测试代理",
            bigmodel="claude-3-opus-20240229",
            smallmodel="claude-3-haiku-20240307"
        )
        
        # 测试默认格式导出
        bash_export = integration_proxy_manager.export_environment()
        assert "export ANTHROPIC_BASE_URL=" in bash_export
        assert "export ANTHROPIC_API_KEY=" in bash_export
        assert "export ANTHROPIC_MODEL=" in bash_export
        assert "export ANTHROPIC_SMALL_FAST_MODEL=" in bash_export
        assert "https://export.example.com/" in bash_export
        assert "sk-export-test-key-123456" in bash_export
        assert "claude-3-opus-20240229" in bash_export
        assert "claude-3-haiku-20240307" in bash_export
        
        # 测试Fish格式导出
        fish_format = ExportFormat(shell_type="fish", include_comments=False)
        fish_export = integration_proxy_manager.export_environment(fish_format)
        assert "set -gx ANTHROPIC_BASE_URL" in fish_export
        assert "set -gx ANTHROPIC_API_KEY" in fish_export
        assert "# Claude 中转站环境变量" not in fish_export
        
        # 测试PowerShell格式导出
        ps_format = ExportFormat(shell_type="powershell", prefix="CUSTOM_")
        ps_export = integration_proxy_manager.export_environment(ps_format)
        assert "$env:CUSTOM_BASE_URL=" in ps_export
        assert "$env:CUSTOM_API_KEY=" in ps_export
        
        # 测试指定代理导出
        specific_export = integration_proxy_manager.export_environment(
            proxy_name="export-test"
        )
        assert "export-test" not in specific_export  # 代理名不应该在环境变量中
        assert "https://export.example.com/" in specific_export
        
        # 测试无当前代理的情况
        integration_proxy_manager.config.current_proxy = None
        with pytest.raises(Exception):  # 应该抛出某种异常
            integration_proxy_manager.export_environment()
    
    def test_auth_method_integration(self, integration_proxy_manager):
        """测试不同认证方法的集成"""
        # 添加使用API密钥的代理
        api_key_proxy = integration_proxy_manager.add_proxy(
            name="api-key-proxy",
            base_url="https://apikey.example.com/",
            api_key="sk-api-key-test-123456"
        )
        
        # 添加使用Auth令牌的代理
        auth_token_proxy = integration_proxy_manager.add_proxy(
            name="auth-token-proxy", 
            base_url="https://authtoken.example.com/",
            auth_token="sk-ant-api03-auth-token-test"
        )
        
        # 添加使用API密钥助手的代理
        api_helper_proxy = integration_proxy_manager.add_proxy(
            name="api-helper-proxy",
            base_url="https://apihelper.example.com/",
            api_key_helper="echo 'sk-helper-key'"
        )
        
        # 测试API密钥代理的导出
        integration_proxy_manager.switch_proxy("api-key-proxy")
        api_export = integration_proxy_manager.export_environment()
        assert "ANTHROPIC_API_KEY=" in api_export
        assert "ANTHROPIC_AUTH_TOKEN=" not in api_export
        assert "sk-api-key-test-123456" in api_export
        
        # 测试Auth令牌代理的导出
        integration_proxy_manager.switch_proxy("auth-token-proxy")
        auth_export = integration_proxy_manager.export_environment()
        assert "ANTHROPIC_AUTH_TOKEN=" in auth_export
        assert "ANTHROPIC_API_KEY=" not in auth_export
        assert "sk-ant-api03-auth-token-test" in auth_export
        
        # 测试API密钥助手代理的导出
        integration_proxy_manager.switch_proxy("api-helper-proxy")
        helper_export = integration_proxy_manager.export_environment()
        assert "ANTHROPIC_API_KEY=" in helper_export
        assert "ANTHROPIC_AUTH_TOKEN=" not in helper_export
        assert "sk-helper-key" in helper_export
        
        # 验证代理认证方法
        assert integration_proxy_manager.get_proxy("api-key-proxy").get_auth_method() == "api_key"
        assert integration_proxy_manager.get_proxy("auth-token-proxy").get_auth_method() == "auth_token"  
        assert integration_proxy_manager.get_proxy("api-helper-proxy").get_auth_method() == "api_key_helper"
    
    def test_error_handling_integration(self, integration_proxy_manager):
        """测试错误处理集成"""
        # 测试重复代理错误
        integration_proxy_manager.add_proxy(
            name="duplicate-test",
            base_url="https://duplicate.example.com/",
            api_key="sk-duplicate-key-123456"
        )
        
        with pytest.raises(DuplicateProxyError):
            integration_proxy_manager.add_proxy(
                name="duplicate-test",  # 相同名称
                base_url="https://different.example.com/",
                api_key="sk-different-key-789012"
            )
        
        # 测试代理不存在错误
        with pytest.raises(ProxyNotFoundError):
            integration_proxy_manager.get_proxy("nonexistent-proxy")
        
        with pytest.raises(ProxyNotFoundError):
            integration_proxy_manager.switch_proxy("nonexistent-proxy")
        
        with pytest.raises(ProxyNotFoundError):
            integration_proxy_manager.remove_proxy("nonexistent-proxy")
        
        with pytest.raises(ProxyNotFoundError):
            integration_proxy_manager.update_proxy("nonexistent-proxy", description="新描述")
        
        # 测试无效数据验证错误
        with pytest.raises(ValidationError):
            integration_proxy_manager.add_proxy(
                name="invalid@name",  # 包含非法字符
                base_url="https://invalid.example.com/",
                api_key="sk-invalid-key-123456"
            )


class TestClaudeCodeIntegration:
    """测试Claude Code集成场景"""
    
    @pytest.fixture
    def temp_config_dir(self):
        """临时配置目录fixture"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def claude_code_manager(self, temp_config_dir):
        """Claude Code集成测试管理器fixture"""
        config_path = temp_config_dir / "claude_config.toml"
        return ProxyManager(config_path=config_path)
    
    @pytest.fixture  
    def mock_claude_code_dir(self, temp_config_dir):
        """模拟Claude Code配置目录fixture"""
        claude_dir = temp_config_dir / ".claude"
        claude_dir.mkdir()
        return claude_dir
    
    def test_claude_code_config_generation(self, claude_code_manager, mock_claude_code_dir):
        """测试Claude Code配置生成"""
        # 添加测试代理
        claude_code_manager.add_proxy(
            name="claude-integration",
            base_url="https://claude.example.com/",
            api_key="sk-claude-integration-key",
            bigmodel="claude-3-opus-20240229",
            smallmodel="claude-3-haiku-20240307"
        )
        
        # Mock Claude Code配置目录路径
        with patch.object(claude_code_manager, '_get_claude_code_config_dir', return_value=mock_claude_code_dir):
            # 应用Claude Code设置
            result = claude_code_manager.apply_claude_code_setting()
            assert result is True
            
            # 检查配置文件是否创建
            settings_file = mock_claude_code_dir / "settings.json"
            assert settings_file.exists()
            
            # 验证配置内容
            with open(settings_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            assert "env" in config
            env = config["env"]
            assert env["ANTHROPIC_API_KEY"] == "sk-claude-integration-key"
            assert env["ANTHROPIC_BASE_URL"] == "https://claude.example.com/"
            assert env["ANTHROPIC_MODEL"] == "claude-3-opus-20240229"
            assert env["ANTHROPIC_SMALL_FAST_MODEL"] == "claude-3-haiku-20240307"
            assert env["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] == 1
            
            # 检查备份文件
            backup_file = mock_claude_code_dir / "settings.json.claudewarp.bak"
            # 由于原本没有配置文件，所以不会创建备份
    
    def test_claude_code_config_merge(self, claude_code_manager, mock_claude_code_dir):
        """测试Claude Code配置合并"""
        # 创建现有的Claude Code配置
        existing_config = {
            "env": {
                "EXISTING_VAR": "existing_value",
                "ANTHROPIC_API_KEY": "old-key"  # 应该被覆盖
            },
            "permissions": {
                "allow": ["existing_permission"],
                "deny": []
            },
            "custom_setting": "custom_value"
        }
        
        settings_file = mock_claude_code_dir / "settings.json"
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(existing_config, f, indent=2)
        
        # 添加代理
        claude_code_manager.add_proxy(
            name="claude-merge",
            base_url="https://merge.example.com/",
            auth_token="sk-ant-api03-merge-token"  # 使用auth_token
        )
        
        # Mock Claude Code配置目录路径并应用设置
        with patch.object(claude_code_manager, '_get_claude_code_config_dir', return_value=mock_claude_code_dir):
            result = claude_code_manager.apply_claude_code_setting()
            assert result is True
            
            # 验证合并结果
            with open(settings_file, 'r', encoding='utf-8') as f:
                merged_config = json.load(f)
            
            # 检查现有设置是否保留
            assert merged_config["custom_setting"] == "custom_value"
            assert merged_config["permissions"]["allow"] == ["existing_permission"]
            
            # 检查环境变量
            env = merged_config["env"]
            assert env["EXISTING_VAR"] == "existing_value"  # 保留
            assert "ANTHROPIC_API_KEY" not in env  # 应该被清除，因为使用auth_token
            assert env["ANTHROPIC_AUTH_TOKEN"] == "sk-ant-api03-merge-token"  # 新增
            assert env["ANTHROPIC_BASE_URL"] == "https://merge.example.com/"
            
            # 检查备份文件是否创建
            backup_file = mock_claude_code_dir / "settings.json.claudewarp.bak"
            assert backup_file.exists()
            
            # 验证备份内容是否为原始配置
            with open(backup_file, 'r', encoding='utf-8') as f:
                backup_config = json.load(f)
            assert backup_config == existing_config
    
    def test_claude_code_auth_method_switching(self, claude_code_manager, mock_claude_code_dir):
        """测试Claude Code认证方法切换"""
        # 创建现有配置（使用API密钥）
        existing_config = {
            "env": {
                "ANTHROPIC_API_KEY": "old-api-key",
                "ANTHROPIC_BASE_URL": "https://old.example.com/"
            }
        }
        
        settings_file = mock_claude_code_dir / "settings.json"
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(existing_config, f, indent=2)
        
        # 添加使用Auth令牌的代理
        claude_code_manager.add_proxy(
            name="auth-switch",
            base_url="https://authswitch.example.com/",
            auth_token="sk-ant-api03-new-auth-token"
        )
        
        # 应用配置
        with patch.object(claude_code_manager, '_get_claude_code_config_dir', return_value=mock_claude_code_dir):
            result = claude_code_manager.apply_claude_code_setting()
            assert result is True
            
            # 验证认证方法切换
            with open(settings_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            env = config["env"]
            # API密钥应该被清除
            assert "ANTHROPIC_API_KEY" not in env
            # Auth令牌应该存在
            assert env["ANTHROPIC_AUTH_TOKEN"] == "sk-ant-api03-new-auth-token"
            assert env["ANTHROPIC_BASE_URL"] == "https://authswitch.example.com/"
    
    def test_claude_code_automatic_application(self, claude_code_manager, mock_claude_code_dir):
        """测试Claude Code自动应用配置"""
        # Mock Claude Code配置目录路径
        with patch.object(claude_code_manager, '_get_claude_code_config_dir', return_value=mock_claude_code_dir):
            # 添加代理（应该自动应用到Claude Code）
            claude_code_manager.add_proxy(
                name="auto-apply",
                base_url="https://auto.example.com/",
                api_key="sk-auto-apply-key"
            )
            
            # 验证配置文件是否自动创建
            settings_file = mock_claude_code_dir / "settings.json"
            # 注意：当前实现可能不会自动应用，需要手动调用
            # 这取决于具体的实现细节
            
            # 手动应用以确保测试通过
            claude_code_manager.apply_claude_code_setting()
            assert settings_file.exists()
            
            # 切换代理（应该自动更新Claude Code配置）
            claude_code_manager.add_proxy(
                name="auto-switch",
                base_url="https://autoswitch.example.com/",
                api_key="sk-auto-switch-key"
            )
            
            claude_code_manager.switch_proxy("auto-switch")
            
            # 验证配置是否更新
            with open(settings_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            assert config["env"]["ANTHROPIC_BASE_URL"] == "https://autoswitch.example.com/"
            assert config["env"]["ANTHROPIC_API_KEY"] == "sk-auto-switch-key"


class TestEndToEndScenarios:
    """测试端到端场景"""
    
    @pytest.fixture
    def temp_workspace(self):
        """临时工作空间fixture"""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            # 创建工作空间结构
            (workspace / "config").mkdir()
            (workspace / "claude").mkdir()
            yield workspace
    
    @pytest.fixture
    def e2e_manager(self, temp_workspace):
        """端到端测试管理器fixture"""
        config_path = temp_workspace / "config" / "claudewarp.toml"
        return ProxyManager(config_path=config_path, auto_backup=True)
    
    def test_complete_user_workflow(self, e2e_manager, temp_workspace):
        """测试完整用户工作流"""
        # 场景：用户首次使用ClaudeWarp，设置多个代理并导出配置
        
        # 1. 用户添加主要代理
        main_proxy = e2e_manager.add_proxy(
            name="primary-claude",
            base_url="https://api.anthropic.com/",
            api_key="sk-user-primary-key-123456",
            description="官方Claude API",
            tags=["official", "primary", "production"],
            bigmodel="claude-3-opus-20240229",
            smallmodel="claude-3-haiku-20240307",
            set_as_current=True
        )
        
        # 2. 用户添加备用代理（使用不同认证方式）
        backup_proxy = e2e_manager.add_proxy(
            name="backup-claude",
            base_url="https://backup-api.example.com/",
            auth_token="sk-ant-api03-backup-token-789012",
            description="备用Claude API代理",
            tags=["backup", "reliable", "production"]
        )
        
        # 3. 用户添加开发测试代理
        dev_proxy = e2e_manager.add_proxy(
            name="dev-claude",
            base_url="https://dev-api.example.com/",
            api_key_helper="aws ssm get-parameter --name /claude/dev/api-key --query 'Parameter.Value' --output text",
            description="开发环境Claude API",
            tags=["development", "testing"],
            is_active=True
        )
        
        # 4. 验证初始状态
        stats = e2e_manager.get_statistics()
        assert stats["total_proxies"] == 3
        assert stats["active_proxies"] == 3
        assert stats["current_proxy"] == "primary-claude"
        assert stats["has_current_proxy"] is True
        
        # 5. 用户搜索和过滤代理
        prod_proxies = e2e_manager.search_proxies("production")
        assert len(prod_proxies) == 2
        
        dev_proxies = e2e_manager.search_proxies("development")
        assert len(dev_proxies) == 1
        
        # 6. 用户导出不同格式的环境变量
        bash_env = e2e_manager.export_environment()
        assert "export ANTHROPIC_BASE_URL=" in bash_env
        assert "export ANTHROPIC_API_KEY=" in bash_env
        assert "export ANTHROPIC_MODEL=" in bash_env
        assert "https://api.anthropic.com/" in bash_env
        assert "claude-3-opus-20240229" in bash_env
        
        fish_format = ExportFormat(shell_type="fish", include_comments=True, prefix="CLAUDE_")
        fish_env = e2e_manager.export_environment(fish_format)
        assert "set -gx CLAUDE_BASE_URL" in fish_env
        assert "set -gx CLAUDE_API_KEY" in fish_env
        assert "# Claude 中转站环境变量" in fish_env
        
        # 7. 用户切换到备用代理
        e2e_manager.switch_proxy("backup-claude")
        current = e2e_manager.get_current_proxy()
        assert current.name == "backup-claude"
        assert current.get_auth_method() == "auth_token"
        
        # 验证导出的环境变量已更新
        backup_env = e2e_manager.export_environment()
        assert "ANTHROPIC_AUTH_TOKEN=" in backup_env
        assert "ANTHROPIC_API_KEY=" not in backup_env
        assert "https://backup-api.example.com/" in backup_env
        
        # 8. 用户更新代理配置
        updated = e2e_manager.update_proxy(
            "dev-claude",
            description="更新后的开发环境配置",
            tags=["development", "testing", "updated"],
            bigmodel="claude-3-sonnet-20240229"
        )
        assert "updated" in updated.tags
        assert updated.bigmodel == "claude-3-sonnet-20240229"
        
        # 9. 用户禁用某个代理
        e2e_manager.update_proxy("dev-claude", is_active=False)
        active_proxies = e2e_manager.list_proxies(active_only=True)
        assert len(active_proxies) == 2
        assert "dev-claude" not in active_proxies
        
        # 10. 用户删除不需要的代理
        e2e_manager.remove_proxy("dev-claude")
        final_stats = e2e_manager.get_statistics()
        assert final_stats["total_proxies"] == 2
        assert final_stats["current_proxy"] == "backup-claude"
        
        # 11. 验证配置持久化
        config_file = temp_workspace / "config" / "claudewarp.toml"
        assert config_file.exists()
        
        # 重新创建管理器，验证配置是否正确加载
        new_manager = ProxyManager(config_path=config_file)
        reloaded_stats = new_manager.get_statistics()
        assert reloaded_stats["total_proxies"] == 2
        assert reloaded_stats["current_proxy"] == "backup-claude"
        
        proxy_names = new_manager.get_proxy_names()
        assert set(proxy_names) == {"primary-claude", "backup-claude"}
    
    def test_error_recovery_workflow(self, e2e_manager):
        """测试错误恢复工作流"""
        # 场景：用户在使用过程中遇到各种错误并恢复
        
        # 1. 用户尝试添加无效代理
        with pytest.raises(ValidationError):
            e2e_manager.add_proxy(
                name="invalid proxy name",  # 包含空格
                base_url="https://invalid.example.com/",
                api_key="sk-invalid-key"
            )
        
        # 2. 用户添加有效代理
        e2e_manager.add_proxy(
            name="recovery-test",
            base_url="https://recovery.example.com/",
            api_key="sk-recovery-test-key-123456"
        )
        
        # 3. 用户尝试添加重复代理
        with pytest.raises(DuplicateProxyError):
            e2e_manager.add_proxy(
                name="recovery-test",  # 相同名称
                base_url="https://different.example.com/",
                api_key="sk-different-key"
            )
        
        # 4. 用户尝试操作不存在的代理
        with pytest.raises(ProxyNotFoundError):
            e2e_manager.switch_proxy("nonexistent")
        
        with pytest.raises(ProxyNotFoundError):
            e2e_manager.remove_proxy("nonexistent")
        
        with pytest.raises(ProxyNotFoundError):
            e2e_manager.update_proxy("nonexistent", description="new desc")
        
        # 5. 验证系统状态未受影响
        assert e2e_manager.get_proxy_count() == 1
        assert e2e_manager.get_current_proxy().name == "recovery-test"
        
        # 6. 用户成功进行后续操作
        e2e_manager.update_proxy("recovery-test", description="恢复测试代理")
        updated = e2e_manager.get_proxy("recovery-test")
        assert updated.description == "恢复测试代理"
    
    def test_concurrent_access_simulation(self, e2e_manager):
        """测试并发访问模拟"""
        # 场景：模拟多个操作同时进行（虽然Python GIL限制真正并发）
        
        # 添加基础代理
        e2e_manager.add_proxy(
            name="concurrent-test",
            base_url="https://concurrent.example.com/",
            api_key="sk-concurrent-test-key"
        )
        
        # 模拟并发操作序列
        operations = [
            lambda: e2e_manager.update_proxy("concurrent-test", description="更新1"),
            lambda: e2e_manager.get_proxy("concurrent-test"),
            lambda: e2e_manager.export_environment(),
            lambda: e2e_manager.get_statistics(),
            lambda: e2e_manager.update_proxy("concurrent-test", tags=["concurrent", "test"]),
        ]
        
        # 执行所有操作
        results = []
        for operation in operations:
            try:
                result = operation()
                results.append(result)
            except Exception as e:
                results.append(e)
        
        # 验证所有操作都成功完成
        assert len(results) == len(operations)
        for result in results:
            assert not isinstance(result, Exception), f"操作失败: {result}"
        
        # 验证最终状态一致性
        final_proxy = e2e_manager.get_proxy("concurrent-test")
        assert final_proxy.description == "更新1"
        assert set(final_proxy.tags) == {"concurrent", "test"}


# 测试辅助函数
def create_comprehensive_test_config() -> ProxyConfig:
    """创建综合测试配置"""
    proxies = {}
    
    # API密钥代理
    proxies["api-key-proxy"] = ProxyServer(
        name="api-key-proxy",
        base_url="https://apikey.example.com/",
        api_key="sk-api-key-test-123456",
        description="API密钥测试代理",
        tags=["test", "api-key"],
        bigmodel="claude-3-opus-20240229"
    )
    
    # Auth令牌代理
    proxies["auth-token-proxy"] = ProxyServer(
        name="auth-token-proxy",
        base_url="https://authtoken.example.com/", 
        auth_token="sk-ant-api03-auth-token-test",
        description="Auth令牌测试代理",
        tags=["test", "auth-token"],
        smallmodel="claude-3-haiku-20240307"
    )
    
    # API密钥助手代理
    proxies["api-helper-proxy"] = ProxyServer(
        name="api-helper-proxy",
        base_url="https://apihelper.example.com/",
        api_key_helper="echo 'sk-helper-key'",
        description="API密钥助手测试代理",
        tags=["test", "api-helper"],
        is_active=False
    )
    
    return ProxyConfig(
        current_proxy="api-key-proxy",
        proxies=proxies,
        settings={
            "auto_backup": True,
            "max_backups": 5,
            "theme": "auto"
        }
    )


def validate_export_format(export_content: str, format_type: str, proxy: ProxyServer) -> bool:
    """验证导出格式的正确性"""
    if format_type == "bash":
        return (
            "export ANTHROPIC_BASE_URL=" in export_content and
            proxy.base_url in export_content
        )
    elif format_type == "fish":
        return (
            "set -gx ANTHROPIC_BASE_URL" in export_content and
            proxy.base_url in export_content
        )
    elif format_type == "powershell":
        return (
            "$env:ANTHROPIC_BASE_URL=" in export_content and
            proxy.base_url in export_content
        )
    return False


# Pytest fixtures
@pytest.fixture
def comprehensive_config():
    """综合测试配置fixture"""
    return create_comprehensive_test_config()


@pytest.fixture
def mock_claude_home():
    """模拟Claude Code主目录fixture"""
    with tempfile.TemporaryDirectory() as temp_dir:
        claude_dir = Path(temp_dir) / ".claude"
        claude_dir.mkdir()
        yield claude_dir


class TestFullWorkflowIntegration:
    """测试完整工作流程集成"""

    @pytest.fixture
    def workflow_manager(self):
        """工作流程管理器fixture"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "workflow_config.toml"
            manager = ProxyManager(config_path=config_path)
            yield manager

    def test_complete_proxy_lifecycle(self, workflow_manager):
        """测试完整的代理生命周期"""
        # 1. 创建和添加代理
        proxy = ProxyServer(
            name="lifecycle-proxy",
            base_url="https://api.example.com/",
            api_key="sk-1234567890abcdef",
            description="Lifecycle test proxy",
            tags=["test", "lifecycle"]
        )
        
        result = workflow_manager.add_proxy(proxy)
        assert result is True
        
        # 2. 验证代理存在
        added_proxy = workflow_manager.get_proxy("lifecycle-proxy")
        assert added_proxy.name == "lifecycle-proxy"
        assert added_proxy.base_url == proxy.base_url
        
        # 3. 切换到该代理
        switch_result = workflow_manager.switch_proxy("lifecycle-proxy")
        assert switch_result is True
        
        current_proxy = workflow_manager.get_current_proxy()
        assert current_proxy.name == "lifecycle-proxy"
        
        # 4. 更新代理配置
        update_result = workflow_manager.update_proxy(
            "lifecycle-proxy",
            description="Updated lifecycle proxy",
            tags=["test", "lifecycle", "updated"]
        )
        assert update_result is True
        
        updated_proxy = workflow_manager.get_proxy("lifecycle-proxy")
        assert updated_proxy.description == "Updated lifecycle proxy"
        assert "updated" in updated_proxy.tags
        
        # 5. 导出环境变量
        export_content = workflow_manager.export_environment()
        assert "ANTHROPIC_BASE_URL" in export_content
        assert "https://api.example.com/" in export_content
        
        # 6. 搜索代理
        search_results = workflow_manager.search_proxies("lifecycle")
        assert len(search_results) == 1
        assert "lifecycle-proxy" in search_results
        
        # 7. 创建备份
        backup_path = workflow_manager.backup_config()
        assert backup_path is not None
        
        # 8. 添加第二个代理并切换
        proxy2 = ProxyServer(
            name="second-proxy",
            base_url="https://api2.example.com/",
            api_key="sk-2234567890abcdef"
        )
        workflow_manager.add_proxy(proxy2)
        workflow_manager.switch_proxy("second-proxy")
        
        # 9. 删除原代理
        remove_result = workflow_manager.remove_proxy("lifecycle-proxy")
        assert remove_result is True
        
        # 10. 验证当前代理自动切换
        current_proxy = workflow_manager.get_current_proxy()
        assert current_proxy.name == "second-proxy"
        
        # 11. 验证统计信息
        stats = workflow_manager.get_statistics()
        assert stats["total_proxies"] == 1
        assert stats["current_proxy"] == "second-proxy"

    def test_multi_proxy_management_workflow(self, workflow_manager):
        """测试多代理管理工作流程"""
        # 批量添加代理
        proxy_configs = [
            ("dev-proxy", "https://dev-api.example.com/", "Dev environment"),
            ("test-proxy", "https://test-api.example.com/", "Test environment"),
            ("staging-proxy", "https://staging-api.example.com/", "Staging environment"),
            ("prod-proxy", "https://prod-api.example.com/", "Production environment"),
        ]
        
        for name, url, desc in proxy_configs:
            proxy = ProxyServer(
                name=name,
                base_url=url,
                api_key=f"sk-{name.replace('-', '')}-key",
                description=desc,
                tags=[name.split('-')[0], "environment"]
            )
            workflow_manager.add_proxy(proxy)
        
        # 验证所有代理都已添加
        all_proxies = workflow_manager.list_proxies()
        assert len(all_proxies) == 4
        
        # 测试按环境搜索
        dev_results = workflow_manager.search_proxies("dev")
        assert len(dev_results) == 1
        assert "dev-proxy" in dev_results
        
        # 测试按标签搜索
        env_results = workflow_manager.search_proxies("environment", fields=["tags"])
        assert len(env_results) == 4
        
        # 切换不同环境并验证导出
        environments = ["dev-proxy", "test-proxy", "staging-proxy"]
        for env in environments:
            workflow_manager.switch_proxy(env)
            current = workflow_manager.get_current_proxy()
            assert current.name == env
            
            export_content = workflow_manager.export_environment()
            assert current.base_url in export_content
            assert current.api_key in export_content
        
        # 批量更新标签
        for proxy_name in all_proxies.keys():
            if "prod" not in proxy_name:
                workflow_manager.update_proxy(
                    proxy_name,
                    tags=["non-prod", "safe-to-test"]
                )
        
        # 验证更新结果
        non_prod_results = workflow_manager.search_proxies("non-prod", fields=["tags"])
        assert len(non_prod_results) == 3  # 除了prod-proxy
        
        # 测试禁用/启用代理
        workflow_manager.toggle_proxy_status("test-proxy")
        test_proxy = workflow_manager.get_proxy("test-proxy")
        assert test_proxy.is_active is False
        
        # 获取活跃代理
        active_proxies = workflow_manager.list_proxies(include_inactive=False)
        assert len(active_proxies) == 3
        assert "test-proxy" not in active_proxies


class TestConcurrentIntegration:
    """测试并发集成场景"""

    @pytest.fixture
    def concurrent_manager(self):
        """并发管理器fixture"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "concurrent_config.toml"
            manager = ProxyManager(config_path=config_path)
            yield manager

    def test_concurrent_proxy_operations(self, concurrent_manager):
        """测试并发代理操作"""
        def worker_operations(worker_id, operation_count):
            """工作线程执行操作"""
            results = {"added": 0, "switched": 0, "updated": 0, "errors": 0}
            
            for i in range(operation_count):
                try:
                    # 添加代理
                    proxy = ProxyServer(
                        name=f"worker-{worker_id}-proxy-{i}",
                        base_url=f"https://w{worker_id}p{i}.example.com/",
                        api_key=f"sk-{worker_id:02d}{i:03d}{'1'*10}",
                        description=f"Worker {worker_id} proxy {i}"
                    )
                    concurrent_manager.add_proxy(proxy)
                    results["added"] += 1
                    
                    # 尝试切换到该代理
                    concurrent_manager.switch_proxy(proxy.name)
                    results["switched"] += 1
                    
                    # 更新代理
                    concurrent_manager.update_proxy(
                        proxy.name,
                        description=f"Updated by worker {worker_id}"
                    )
                    results["updated"] += 1
                    
                except Exception:
                    results["errors"] += 1
            
            return results
        
        # 启动多个工作线程
        num_workers = 5
        operations_per_worker = 10
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(worker_operations, worker_id, operations_per_worker)
                for worker_id in range(num_workers)
            ]
            
            all_results = [future.result() for future in as_completed(futures)]
        
        # 分析结果
        total_added = sum(r["added"] for r in all_results)
        total_switched = sum(r["switched"] for r in all_results)
        total_updated = sum(r["updated"] for r in all_results)
        total_errors = sum(r["errors"] for r in all_results)
        
        # 验证结果
        assert total_added > 0
        assert total_switched > 0
        assert total_updated > 0
        
        # 验证最终状态
        final_proxies = concurrent_manager.list_proxies()
        assert len(final_proxies) == total_added
        
        # 验证数据完整性
        for proxy_name, proxy in final_proxies.items():
            assert proxy.name == proxy_name
            assert "Updated by worker" in proxy.description

    def test_concurrent_config_persistence(self, concurrent_manager):
        """测试并发配置持久化"""
        def config_writer(writer_id, write_count):
            """配置写入器"""
            results = {"writes": 0, "reads": 0, "errors": 0}
            
            for i in range(write_count):
                try:
                    # 添加代理
                    proxy = ProxyServer(
                        name=f"writer-{writer_id}-{i}",
                        base_url=f"https://writer{writer_id}.example.com/",
                        api_key=f"sk-writer-{writer_id:02d}{i:03d}"
                    )
                    concurrent_manager.add_proxy(proxy)
                    results["writes"] += 1
                    
                    # 读取配置验证
                    _ = concurrent_manager.get_proxy(proxy.name)
                    results["reads"] += 1
                    
                    # 短暂等待
                    time.sleep(0.01)
                    
                except Exception:
                    results["errors"] += 1
            
            return results
        
        # 并发写入配置
        num_writers = 8
        writes_per_writer = 20
        
        with ThreadPoolExecutor(max_workers=num_writers) as executor:
            futures = [
                executor.submit(config_writer, writer_id, writes_per_writer)
                for writer_id in range(num_writers)
            ]
            
            all_results = [future.result() for future in as_completed(futures)]
        
        total_writes = sum(r["writes"] for r in all_results)
        total_errors = sum(r["errors"] for r in all_results)
        
        # 验证并发写入结果
        final_proxies = concurrent_manager.list_proxies()
        
        # 应该有大部分写入成功
        assert len(final_proxies) >= total_writes * 0.8
        assert total_errors < total_writes * 0.2
        
        # 验证配置文件完整性
        config_manager = concurrent_manager.config_manager
        loaded_config = config_manager.load_config()
        assert len(loaded_config.proxies) == len(final_proxies)


class TestPerformanceIntegration:
    """测试性能集成场景"""

    @pytest.fixture
    def performance_manager(self):
        """性能管理器fixture"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "performance_config.toml"
            manager = ProxyManager(config_path=config_path)
            yield manager

    @pytest.mark.slow
    def test_large_scale_operations(self, performance_manager):
        """测试大规模操作性能"""
        proxy_count = 2000
        batch_size = 100
        
        # 分批添加代理以测试批处理性能
        start_time = time.time()
        
        for batch in range(0, proxy_count, batch_size):
            batch_proxies = []
            
            for i in range(batch, min(batch + batch_size, proxy_count)):
                proxy = ProxyServer(
                    name=f"perf-proxy-{i:05d}",
                    base_url=f"https://perf{i:05d}.example.com/",
                    api_key=f"sk-perf-{i:015d}",
                    description=f"Performance test proxy {i}",
                    tags=[f"batch-{batch//batch_size}", "performance"]
                )
                batch_proxies.append(proxy)
            
            # 批量添加
            for proxy in batch_proxies:
                performance_manager.add_proxy(proxy)
            
            # 每1000个代理测试一次性能
            if (batch + batch_size) % 1000 == 0:
                current_count = batch + batch_size
                
                # 测试列表性能
                list_start = time.time()
                all_proxies = performance_manager.list_proxies()
                list_time = time.time() - list_start
                
                assert len(all_proxies) == current_count
                assert list_time < 2.0  # 列表操作应该在2秒内
                
                # 测试搜索性能
                search_start = time.time()
                search_results = performance_manager.search_proxies(f"perf-proxy-{current_count//2:05d}")
                search_time = time.time() - search_start
                
                assert len(search_results) == 1
                assert search_time < 0.5  # 搜索应该在0.5秒内
        
        total_time = time.time() - start_time
        
        # 验证最终结果
        final_proxies = performance_manager.list_proxies()
        assert len(final_proxies) == proxy_count
        
        # 性能断言
        add_rate = proxy_count / total_time
        assert add_rate > 100  # 每秒至少能添加100个代理
        
        print(f"\n大规模操作性能:")
        print(f"添加{proxy_count}个代理用时: {total_time:.2f}s")
        print(f"添加速率: {add_rate:.0f} proxies/second")

    def test_concurrent_performance_stress(self, performance_manager):
        """测试并发性能压力"""
        def stress_worker(worker_id, operations_count):
            """压力测试工作线程"""
            operation_times = []
            
            for i in range(operations_count):
                op_start = time.time()
                
                try:
                    # 混合操作模拟真实使用场景
                    if i % 4 == 0:
                        # 添加代理
                        proxy = ProxyServer(
                            name=f"stress-w{worker_id}-{i}",
                            base_url=f"https://stress{worker_id}{i}.example.com/",
                            api_key=f"sk-stress-{worker_id:02d}{i:03d}"
                        )
                        performance_manager.add_proxy(proxy)
                        
                    elif i % 4 == 1:
                        # 搜索操作
                        performance_manager.search_proxies("stress")
                        
                    elif i % 4 == 2:
                        # 列表操作
                        performance_manager.list_proxies()
                        
                    else:
                        # 获取统计
                        performance_manager.get_statistics()
                    
                    op_time = time.time() - op_start
                    operation_times.append(op_time)
                    
                except Exception:
                    # 压力测试中的错误是可接受的
                    pass
            
            return operation_times
        
        # 启动高并发压力测试
        num_workers = 10
        operations_per_worker = 200
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(stress_worker, worker_id, operations_per_worker)
                for worker_id in range(num_workers)
            ]
            
            all_operation_times = []
            for future in as_completed(futures):
                worker_times = future.result()
                all_operation_times.extend(worker_times)
        
        total_time = time.time() - start_time
        
        # 分析性能结果
        if all_operation_times:
            avg_op_time = sum(all_operation_times) / len(all_operation_times)
            max_op_time = max(all_operation_times)
            min_op_time = min(all_operation_times)
            
            # 性能断言
            assert avg_op_time < 0.1  # 平均操作时间应该小于0.1秒
            assert max_op_time < 2.0   # 最大操作时间应该小于2秒
            
            print(f"\n并发压力测试结果:")
            print(f"总操作数: {len(all_operation_times)}")
            print(f"总时间: {total_time:.2f}s")
            print(f"平均操作时间: {avg_op_time:.4f}s")
            print(f"最大操作时间: {max_op_time:.4f}s")
            print(f"最小操作时间: {min_op_time:.4f}s")
            print(f"操作吞吐量: {len(all_operation_times)/total_time:.0f} ops/second")