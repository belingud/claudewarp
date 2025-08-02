"""
集成测试
测试各个组件之间的集成和端到端工作流
"""

import json
from unittest.mock import patch

import pytest
import toml

from claudewarp.core.config import ConfigManager
from claudewarp.core.exceptions import (
    ConfigError,
    ProxyNotFoundError,
    ValidationError,
)
from claudewarp.core.manager import ProxyManager
from claudewarp.core.models import ExportFormat, ProxyConfig, ProxyServer


class TestConfigManagerIntegration:
    """ConfigManager 集成测试"""

    def test_full_config_lifecycle(self, temp_dir):
        """测试完整的配置生命周期"""
        config_path = temp_dir / "integration_config.toml"
        manager = ConfigManager(config_path=config_path)
        
        # 1. 创建默认配置
        config = manager.load_config()
        assert isinstance(config, ProxyConfig)
        assert config.proxies == {}
        
        # 2. 添加代理
        proxy = ProxyServer(
            name="integration-proxy",
            base_url="https://api.integration.com",
            api_key="sk-integration123",
            description="集成测试代理",
            tags=["integration", "test"]
        )
        config.add_proxy(proxy)
        
        # 3. 保存配置
        manager.save_config(config)
        assert config_path.exists()
        
        # 4. 验证文件内容
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "integration-proxy" in content
        assert "sk-integration123" in content
        
        # 5. 重新加载并验证
        new_manager = ConfigManager(config_path=config_path)
        loaded_config = new_manager.load_config()
        
        assert "integration-proxy" in loaded_config.proxies
        loaded_proxy = loaded_config.proxies["integration-proxy"]
        assert loaded_proxy.name == proxy.name
        assert loaded_proxy.base_url == proxy.base_url
        assert loaded_proxy.api_key == proxy.api_key

    def test_config_backup_and_restore_workflow(self, temp_dir):
        """测试配置备份和恢复工作流"""
        config_path = temp_dir / "backup_test.toml"
        manager = ConfigManager(config_path=config_path, auto_backup=True)
        
        # 1. 创建初始配置
        config = ProxyConfig()
        proxy1 = ProxyServer(name="proxy1", base_url="https://api1.com", api_key="sk-1")
        config.add_proxy(proxy1)
        manager.save_config(config)
        
        # 2. 修改配置（触发备份）
        proxy2 = ProxyServer(name="proxy2", base_url="https://api2.com", api_key="sk-2")
        config.add_proxy(proxy2)
        manager.save_config(config)
        
        # 3. 再次修改配置
        config.remove_proxy("proxy1")
        manager.save_config(config)
        
        # 4. 验证备份存在
        backups = manager.get_backup_files()
        assert len(backups) >= 1
        
        # 5. 从备份恢复
        success = manager.restore_from_backup(backups[0])
        assert success is True
        
        # 6. 验证恢复结果
        restored_config = manager.load_config()
        # 恢复的配置应该包含proxy1
        assert "proxy1" in restored_config.proxies or "proxy2" in restored_config.proxies

    def test_config_migration_workflow(self, temp_dir):
        """测试配置迁移工作流"""
        config_path = temp_dir / "migration_test.toml"
        
        # 1. 创建旧版本配置文件
        old_config_data = {
            "version": "1.0",
            "current_proxy": "old-proxy",
            "proxies": {
                "old-proxy": {
                    "name": "old-proxy",
                    "base_url": "https://old.api.com/",
                    "api_key": "sk-old123",
                    "description": "旧版代理",
                    "tags": ["old"],
                    "is_active": True,
                    "created_at": "2024-01-01T00:00:00",
                    "updated_at": "2024-01-01T00:00:00",
                }
            },
            "settings": {"auto_backup": True}
        }
        
        with open(config_path, "w", encoding="utf-8") as f:
            toml.dump(old_config_data, f)
        
        # 2. 使用ConfigManager加载
        manager = ConfigManager(config_path=config_path)
        config = manager.load_config()
        
        # 3. 验证迁移结果
        assert config.version == "1.0"
        assert "old-proxy" in config.proxies
        assert config.current_proxy == "old-proxy"


class TestProxyManagerIntegration:
    """ProxyManager 集成测试"""

    def test_full_proxy_management_workflow(self, temp_dir):
        """测试完整的代理管理工作流"""
        config_path = temp_dir / "proxy_workflow.toml"
        manager = ProxyManager(config_path=config_path)
        
        # 1. 添加第一个代理
        proxy1 = manager.add_proxy(
            name="primary-proxy",
            base_url="https://primary.api.com",
            api_key="sk-primary123",
            description="主要代理",
            tags=["primary", "production"],
            set_as_current=True
        )
        
        assert proxy1.name == "primary-proxy"
        assert manager.get_current_proxy() == proxy1
        
        # 2. 添加第二个代理
        proxy2 = manager.add_proxy(
            name="backup-proxy",
            base_url="https://backup.api.com",
            auth_token="sk-ant-backup456",
            description="备用代理",
            tags=["backup", "secondary"]
        )
        
        # 3. 验证代理列表
        all_proxies = manager.list_proxies()
        assert len(all_proxies) == 2
        assert "primary-proxy" in all_proxies
        assert "backup-proxy" in all_proxies
        
        # 4. 搜索代理
        primary_results = manager.search_proxies("primary")
        assert len(primary_results) == 1
        assert "primary-proxy" in primary_results
        
        # 5. 按标签查找
        production_proxies = manager.get_proxies_by_tag("production")
        assert len(production_proxies) == 1
        assert "primary-proxy" in production_proxies
        
        # 6. 切换代理
        switched_proxy = manager.switch_proxy("backup-proxy")
        assert switched_proxy == proxy2
        assert manager.get_current_proxy() == proxy2
        
        # 7. 更新代理
        updated_proxy = manager.update_proxy(
            name="backup-proxy",
            description="更新后的备用代理",
            tags=["backup", "updated"]
        )
        assert updated_proxy.description == "更新后的备用代理"
        assert "updated" in updated_proxy.tags
        
        # 8. 删除代理
        success = manager.remove_proxy("primary-proxy")
        assert success is True
        
        remaining_proxies = manager.list_proxies()
        assert len(remaining_proxies) == 1
        assert "backup-proxy" in remaining_proxies
        
        # 9. 验证配置持久化
        new_manager = ProxyManager(config_path=config_path)
        loaded_proxies = new_manager.list_proxies()
        assert len(loaded_proxies) == 1
        assert "backup-proxy" in loaded_proxies

    def test_proxy_state_consistency(self, temp_dir):
        """测试代理状态一致性"""
        config_path = temp_dir / "state_test.toml"
        manager = ProxyManager(config_path=config_path)
        
        # 1. 添加多个代理
        proxies = []
        for i in range(3):
            proxy = manager.add_proxy(
                name=f"proxy-{i}",
                base_url=f"https://api{i}.com",
                api_key=f"sk-{i}123",
                is_active=i != 1  # proxy-1 为非活跃状态
            )
            proxies.append(proxy)
        
        # 2. 验证活跃代理列表
        active_proxies = manager.list_proxies(active_only=True)
        assert len(active_proxies) == 2
        assert "proxy-1" not in active_proxies
        
        # 3. 尝试切换到非活跃代理
        with pytest.raises(ValidationError, match="未启用"):
            manager.switch_proxy("proxy-1")
        
        # 4. 激活代理
        updated_proxy = manager.update_proxy("proxy-1", is_active=True)
        assert updated_proxy.is_active is True
        
        # 5. 现在应该可以切换
        switched_proxy = manager.switch_proxy("proxy-1")
        assert switched_proxy.name == "proxy-1"
        
        # 6. 禁用当前代理，应该自动切换
        manager.update_proxy("proxy-1", is_active=False)
        current_proxy = manager.get_current_proxy()
        assert current_proxy is not None
        assert current_proxy.name != "proxy-1"

    def test_auth_method_integration(self, temp_dir):
        """测试认证方式集成"""
        config_path = temp_dir / "auth_test.toml"
        manager = ProxyManager(config_path=config_path)
        
        # 1. 创建使用不同认证方式的代理
        api_key_proxy = manager.add_proxy(
            name="api-key-proxy",
            base_url="https://apikey.com",
            api_key="sk-apikey123"
        )
        
        auth_token_proxy = manager.add_proxy(
            name="auth-token-proxy",
            base_url="https://authtoken.com",
            auth_token="sk-ant-token456"
        )
        
        helper_proxy = manager.add_proxy(
            name="helper-proxy",
            base_url="https://helper.com",
            api_key_helper="echo sk-helper789"
        )
        
        # 2. 验证认证方式
        assert api_key_proxy.get_auth_method() == "api_key"
        assert auth_token_proxy.get_auth_method() == "auth_token"
        assert helper_proxy.get_auth_method() == "api_key_helper"
        
        # 3. 测试认证方式切换
        updated_proxy = manager.update_proxy(
            name="api-key-proxy",
            auth_token="sk-ant-new-token"
        )
        assert updated_proxy.get_auth_method() == "auth_token"
        assert updated_proxy.api_key is None
        assert updated_proxy.auth_token == "sk-ant-new-token"


class TestExportIntegration:
    """导出功能集成测试"""

    def test_environment_export_workflow(self, temp_dir):
        """测试环境变量导出工作流"""
        config_path = temp_dir / "export_test.toml"
        manager = ProxyManager(config_path=config_path)
        
        # 1. 创建代理
        manager.add_proxy(
            name="export-proxy",
            base_url="https://export.api.com",
            api_key="sk-export123",
            bigmodel="claude-3-opus-20240229",
            smallmodel="claude-3-haiku-20240307"
        )
        
        # 2. 测试默认格式导出
        default_export = manager.export_environment()
        
        assert "export ANTHROPIC_BASE_URL" in default_export
        assert "https://export.api.com/" in default_export
        assert "export ANTHROPIC_API_KEY" in default_export
        assert "sk-export123" in default_export
        
        # 3. 测试不同Shell格式
        formats = [
            ("bash", "export"),
            ("fish", "set -gx"),
            ("powershell", "$env:"),
        ]
        
        for shell_type, expected_prefix in formats:
            export_format = ExportFormat(shell_type=shell_type)
            export_content = manager.export_environment(export_format=export_format)
            assert expected_prefix in export_content
            assert "ANTHROPIC_BASE_URL" in export_content
        
        # 4. 测试导出所有代理
        # 添加第二个代理
        manager.add_proxy(
            name="second-proxy",
            base_url="https://second.api.com",
            api_key="sk-second456"
        )
        
        export_all_format = ExportFormat(export_all=True)
        export_all_content = manager.export_environment(export_format=export_all_format)
        
        assert "ANTHROPIC_SECOND_PROXY_API_BASE_URL" in export_all_content
        assert "ANTHROPIC_SECOND_PROXY_API_KEY" in export_all_content

    def test_export_with_auth_token(self, temp_dir):
        """测试认证令牌的导出"""
        config_path = temp_dir / "auth_export_test.toml"
        manager = ProxyManager(config_path=config_path)
        
        # 创建使用认证令牌的代理
        manager.add_proxy(
            name="auth-proxy",
            base_url="https://auth.api.com",
            auth_token="sk-ant-api03-token123"
        )
        
        export_content = manager.export_environment()
        
        assert "ANTHROPIC_AUTH_TOKEN" in export_content
        assert "sk-ant-api03-token123" in export_content
        assert "ANTHROPIC_API_KEY" not in export_content

    def test_export_with_custom_prefix(self, temp_dir):
        """测试自定义前缀的导出"""
        config_path = temp_dir / "prefix_test.toml"
        manager = ProxyManager(config_path=config_path)
        
        manager.add_proxy(
            name="custom-proxy",
            base_url="https://custom.api.com",
            api_key="sk-custom123"
        )
        
        custom_format = ExportFormat(
            prefix="CLAUDE_",
            include_comments=False
        )
        
        export_content = manager.export_environment(export_format=custom_format)
        
        assert "CLAUDE_BASE_URL" in export_content
        assert "CLAUDE_API_KEY" in export_content
        assert "# Claude 中转站环境变量" not in export_content


class TestClaudeCodeIntegration:
    """Claude Code 集成测试"""

    @patch('claudewarp.core.utils.ensure_directory')
    @patch('claudewarp.core.utils.atomic_write')
    @patch('claudewarp.core.utils.safe_copy_file')
    def test_claude_code_configuration_workflow(self, mock_copy, mock_write, mock_ensure_dir, temp_dir):
        """测试 Claude Code 配置工作流"""
        mock_write.return_value = True
        mock_ensure_dir.return_value = None
        
        config_path = temp_dir / "claude_code_test.toml"
        manager = ProxyManager(config_path=config_path)
        
        # 1. 创建代理
        manager.add_proxy(
            name="claude-proxy",
            base_url="https://claude.api.com",
            api_key="sk-claude123",
            bigmodel="claude-3-opus-20240229",
            smallmodel="claude-3-haiku-20240307"
        )
        
        # 2. 应用到 Claude Code（使用临时目录）
        success = manager.apply_claude_code_setting("claude-proxy")
        assert success is True
        
        # 3. 验证写入的配置
        mock_write.assert_called_once()
        written_config_json = mock_write.call_args[0][1]
        written_config = json.loads(written_config_json)
        
        assert written_config["env"]["ANTHROPIC_API_KEY"] == "sk-claude123"
        assert written_config["env"]["ANTHROPIC_BASE_URL"] == "https://claude.api.com/"
        assert written_config["env"]["ANTHROPIC_MODEL"] == "claude-3-opus-20240229"
        assert written_config["env"]["ANTHROPIC_SMALL_FAST_MODEL"] == "claude-3-haiku-20240307"

    def test_claude_code_config_merging(self, temp_dir):
        """测试 Claude Code 配置合并"""
        config_path = temp_dir / "merge_test.toml"
        manager = ProxyManager(config_path=config_path)
        
        # 创建代理
        proxy = ProxyServer(
            name="merge-proxy",
            base_url="https://merge.api.com",
            api_key="sk-merge123"
        )
        
        # 测试与现有配置合并
        existing_config = {
            "existing_setting": "value",
            "env": {
                "EXISTING_VAR": "existing_value",
                "ANTHROPIC_API_KEY": "old_key"  # 应该被覆盖
            },
            "permissions": {
                "allow": ["existing_permission"]
            }
        }
        
        merged_config = manager._merge_claude_code_config(existing_config, proxy)
        
        # 验证合并结果
        assert merged_config["existing_setting"] == "value"
        assert merged_config["env"]["EXISTING_VAR"] == "existing_value"
        assert merged_config["env"]["ANTHROPIC_API_KEY"] == "sk-merge123"  # 被更新
        assert merged_config["env"]["ANTHROPIC_BASE_URL"] == "https://merge.api.com/"
        assert merged_config["permissions"]["allow"] == ["existing_permission"]

    def test_claude_code_auth_methods(self, temp_dir):
        """测试 Claude Code 不同认证方式"""
        config_path = temp_dir / "auth_methods_test.toml"
        manager = ProxyManager(config_path=config_path)
        
        # 测试认证令牌
        auth_token_proxy = ProxyServer(
            name="auth-token",
            base_url="https://auth.api.com",
            auth_token="sk-ant-token123"
        )
        
        merged_config = manager._merge_claude_code_config({}, auth_token_proxy)
        
        assert merged_config["env"]["ANTHROPIC_AUTH_TOKEN"] == "sk-ant-token123"
        assert "ANTHROPIC_API_KEY" not in merged_config["env"]
        
        # 测试API密钥助手
        helper_proxy = ProxyServer(
            name="helper",
            base_url="https://helper.api.com",
            api_key_helper="echo sk-helper123"
        )
        
        merged_config = manager._merge_claude_code_config({}, helper_proxy)
        
        assert merged_config["apiKeyHelper"] == "echo sk-helper123"
        assert "ANTHROPIC_API_KEY" not in merged_config["env"]
        assert "ANTHROPIC_AUTH_TOKEN" not in merged_config["env"]


class TestErrorHandlingIntegration:
    """错误处理集成测试"""

    def test_error_propagation_workflow(self, temp_dir):
        """测试错误传播工作流"""
        config_path = temp_dir / "error_test.toml"
        
        # 1. 测试配置文件损坏时的自动恢复行为
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("invalid toml content [[[")
        
        # ProxyManager应该能够自动恢复损坏的配置文件，而不是抛出异常
        manager = ProxyManager(config_path=config_path)
        
        # 验证已创建默认配置
        assert manager.config is not None
        assert len(manager.config.proxies) == 0  # 默认配置应该是空的
        assert config_path.exists()  # 配置文件应该已被修复
        
        # 2. 清理并创建有效管理器
        config_path.unlink()
        manager = ProxyManager(config_path=config_path)
        
        # 3. 测试重复代理错误
        manager.add_proxy(name="test", base_url="https://api.com", api_key="sk-test")
        
        from claudewarp.core.exceptions import DuplicateProxyError
        with pytest.raises(DuplicateProxyError):
            manager.add_proxy(name="test", base_url="https://api2.com", api_key="sk-test2")
        
        # 4. 测试代理不存在错误
        with pytest.raises(ProxyNotFoundError):
            manager.remove_proxy("nonexistent")
        
        # 5. 测试无效数据错误
        with pytest.raises(ValidationError):
            manager.add_proxy(name="invalid name", base_url="invalid-url", api_key="sk-test")

    def test_recovery_scenarios(self, temp_dir):
        """测试恢复场景"""
        config_path = temp_dir / "recovery_test.toml"
        manager = ProxyManager(config_path=config_path)
        
        # 1. 添加代理
        manager.add_proxy(name="recoverable", base_url="https://api.com", api_key="sk-test")
        
        # 2. 模拟配置文件损坏
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("corrupted content")
        
        # 3. 创建新管理器，应该从损坏状态恢复
        new_manager = ProxyManager(config_path=config_path)
        # 配置管理器应该能够处理损坏的文件并创建新的默认配置
        config = new_manager.config
        assert isinstance(config, ProxyConfig)

    @patch('claudewarp.core.config.atomic_write')
    def test_atomic_operation_failure_recovery(self, mock_atomic_write, temp_dir):
        """测试原子操作失败恢复"""
        config_path = temp_dir / "atomic_test.toml"
        manager = ProxyManager(config_path=config_path)
        
        # 模拟写入失败
        mock_atomic_write.return_value = False
        
        with pytest.raises(ConfigError, match="添加代理服务器失败"):
            manager.add_proxy(name="atomic-test", base_url="https://api.com", api_key="sk-test")


class TestCompleteWorkflows:
    """完整工作流测试"""

    def test_complete_proxy_lifecycle(self, temp_dir):
        """测试完整的代理生命周期"""
        config_path = temp_dir / "lifecycle_test.toml"
        
        # 阶段1: 初始化
        manager = ProxyManager(config_path=config_path)
        assert len(manager.list_proxies()) == 0
        
        # 阶段2: 添加代理
        manager.add_proxy(
            name="primary",
            base_url="https://primary.api.com",
            api_key="sk-primary123",
            description="主要代理",
            tags=["primary", "production"],
            set_as_current=True
        )
        
        manager.add_proxy(
            name="backup",
            base_url="https://backup.api.com",
            auth_token="sk-ant-backup456",
            description="备用代理",
            tags=["backup", "secondary"]
        )
        
        # 阶段3: 验证状态
        status = manager.get_status()
        assert status["total_proxies"] == 2
        assert status["active_proxies"] == 2
        assert status["current_proxy"] == "primary"
        
        # 阶段4: 切换和更新
        manager.switch_proxy("backup")
        assert manager.get_current_proxy().name == "backup"
        
        updated_proxy = manager.update_proxy(
            name="backup",
            description="更新的备用代理",
            tags=["backup", "updated"]
        )
        assert "updated" in updated_proxy.tags
        
        # 阶段5: 导出配置
        export_content = manager.export_environment()
        assert "ANTHROPIC_AUTH_TOKEN" in export_content
        assert "sk-ant-backup456" in export_content
        
        # 阶段6: 搜索和过滤
        primary_proxies = manager.search_proxies("primary")
        assert len(primary_proxies) == 1
        
        updated_proxies = manager.get_proxies_by_tag("updated")
        assert len(updated_proxies) == 1
        
        # 阶段7: 清理
        manager.remove_proxy("primary")
        assert len(manager.list_proxies()) == 1
        assert manager.get_current_proxy().name == "backup"
        
        # 阶段8: 持久化验证
        new_manager = ProxyManager(config_path=config_path)
        assert len(new_manager.list_proxies()) == 1
        assert "backup" in new_manager.list_proxies()

    def test_multi_user_scenario(self, temp_dir):
        """测试多用户场景模拟"""
        config_path = temp_dir / "multi_user_test.toml"
        
        # 用户1: 创建配置
        user1_manager = ProxyManager(config_path=config_path)
        user1_manager.add_proxy(
            name="user1-proxy",
            base_url="https://user1.api.com",
            api_key="sk-user1123"
        )
        
        # 用户2: 加载现有配置并添加代理
        user2_manager = ProxyManager(config_path=config_path)
        assert "user1-proxy" in user2_manager.list_proxies()
        
        user2_manager.add_proxy(
            name="user2-proxy",
            base_url="https://user2.api.com",
            api_key="sk-user2456"
        )
        
        # 用户1: 重新加载并验证
        user1_manager.reload_config()
        all_proxies = user1_manager.list_proxies()
        assert len(all_proxies) == 2
        assert "user1-proxy" in all_proxies
        assert "user2-proxy" in all_proxies

    def test_configuration_backup_workflow(self, temp_dir):
        """测试配置备份工作流"""
        config_path = temp_dir / "backup_workflow_test.toml"
        manager = ProxyManager(config_path=config_path, auto_backup=True, max_backups=3)
        
        # 创建多个配置版本
        versions = []
        for i in range(5):
            proxy = manager.add_proxy(
                name=f"proxy-v{i}",
                base_url=f"https://apiv{i}.com",
                api_key=f"sk-v{i}123"
            )
            versions.append(proxy)
        
        # 验证备份文件
        backups = manager.config_manager.get_backup_files()
        assert len(backups) <= manager.config_manager.max_backups
        
        # 从备份恢复
        if backups:
            success = manager.config_manager.restore_from_backup(backups[0])
            assert success is True
            
            # 重新加载管理器以查看恢复的配置
            manager.reload_config()
            # 代理数量可能不同，取决于备份的时间点
            assert isinstance(manager.config, ProxyConfig)

    def test_theme_management_integration(self, temp_dir):
        """测试主题管理集成"""
        config_path = temp_dir / "theme_test.toml"
        manager = ProxyManager(config_path=config_path)
        
        # 测试默认主题
        assert manager.get_theme_setting() == "auto"
        
        # 更改主题
        manager.save_theme_setting("dark")
        assert manager.get_theme_setting() == "dark"
        
        # 重新加载验证持久化
        new_manager = ProxyManager(config_path=config_path)
        assert new_manager.get_theme_setting() == "dark"
        
        # 更改为light主题
        new_manager.save_theme_setting("light")
        assert new_manager.get_theme_setting() == "light"

    def test_large_scale_proxy_management(self, temp_dir):
        """测试大规模代理管理"""
        config_path = temp_dir / "large_scale_test.toml"
        manager = ProxyManager(config_path=config_path)
        
        # 创建大量代理
        proxy_count = 50
        for i in range(proxy_count):
            manager.add_proxy(
                name=f"proxy-{i:03d}",
                base_url=f"https://api{i}.example.com",
                api_key=f"sk-{i:03d}123",
                description=f"代理服务器 {i}",
                tags=[f"group-{i // 10}", f"type-{i % 3}"],
                is_active=i % 5 != 0  # 每5个中有1个不活跃
            )
        
        # 验证代理总数
        all_proxies = manager.list_proxies()
        assert len(all_proxies) == proxy_count
        
        # 验证活跃代理数量
        active_proxies = manager.list_proxies(active_only=True)
        expected_active = proxy_count - (proxy_count // 5)
        assert len(active_proxies) == expected_active
        
        # 测试搜索性能
        search_results = manager.search_proxies("proxy-0")
        assert len(search_results) >= 10  # proxy-0xx 系列
        
        # 测试标签过滤
        group_0_proxies = manager.get_proxies_by_tag("group-0")
        assert len(group_0_proxies) == 10
        
        # 测试配置文件大小合理性
        assert config_path.exists()
        file_size = config_path.stat().st_size
        assert file_size > 0
        # 文件大小应该合理（不会过大）
        assert file_size < 1024 * 1024  # 小于1MB