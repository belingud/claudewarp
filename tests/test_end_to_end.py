"""
端到端系统测试

测试完整的系统工作流程，包括配置管理、代理操作、导出功能等的端到端场景。
"""

import json
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Any
from unittest.mock import patch

import pytest
import toml

from claudewarp.core.config import ConfigManager
from claudewarp.core.manager import ProxyManager
from claudewarp.core.models import ProxyServer, ProxyConfig, ExportFormat
from claudewarp.core.exceptions import (
    ProxyNotFoundError,
    DuplicateProxyError,
    ValidationError,
    ConfigError
)


class TestEndToEndWorkflows:
    """端到端工作流程测试"""

    @pytest.fixture
    def isolated_environment(self):
        """创建隔离的测试环境"""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            
            # 创建配置目录结构
            config_dir = base_path / "config"
            claude_dir = base_path / "claude"
            backup_dir = base_path / "backups"
            
            for directory in [config_dir, claude_dir, backup_dir]:
                directory.mkdir(parents=True)
            
            yield {
                "base_path": base_path,
                "config_dir": config_dir,
                "claude_dir": claude_dir,
                "backup_dir": backup_dir,
                "config_file": config_dir / "config.toml",
                "claude_settings": claude_dir / "settings.json"
            }

    def test_complete_proxy_lifecycle(self, isolated_environment):
        """测试完整的代理生命周期"""
        env = isolated_environment
        
        # 1. 初始化管理器
        manager = ProxyManager(config_path=env["config_file"])
        
        # 验证初始状态
        assert not env["config_file"].exists()
        assert len(manager.list_proxies()) == 0
        assert manager.get_current_proxy() is None
        
        # 2. 添加第一个代理
        proxy1 = ProxyServer(
            name="production-proxy",
            base_url="https://api.production.com/",
            api_key="sk-prod-1234567890abcdef1234567890abcdef",
            description="生产环境代理",
            tags=["production", "primary"],
            bigmodel="claude-3-5-sonnet-20241022",
            smallmodel="claude-3-haiku-20240307"
        )
        
        result = manager.add_proxy(proxy1)
        assert result is True
        
        # 验证配置文件已创建
        assert env["config_file"].exists()
        
        # 验证代理已添加并设为当前代理
        assert len(manager.list_proxies()) == 1
        current_proxy = manager.get_current_proxy()
        assert current_proxy is not None
        assert current_proxy.name == "production-proxy"
        
        # 3. 添加更多代理
        proxy2 = ProxyServer(
            name="development-proxy",
            base_url="https://api.development.com/",
            auth_token="sk-ant-api03-dev-token-abcdef1234567890",
            description="开发环境代理",
            tags=["development", "testing"]
        )
        
        proxy3 = ProxyServer(
            name="backup-proxy",
            base_url="https://api.backup.com/",
            api_key_helper="get-backup-key.sh",
            description="备用代理",
            tags=["backup", "emergency"],
            is_active=True
        )
        
        manager.add_proxy(proxy2)
        manager.add_proxy(proxy3)
        
        # 验证所有代理已添加
        all_proxies = manager.list_proxies()
        assert len(all_proxies) == 3
        assert "production-proxy" in all_proxies
        assert "development-proxy" in all_proxies
        assert "backup-proxy" in all_proxies
        
        # 4. 代理切换
        result = manager.switch_proxy("development-proxy")
        assert result is True
        
        current = manager.get_current_proxy()
        assert current.name == "development-proxy"
        assert current.get_auth_method() == "auth_token"
        
        # 5. 搜索和过滤
        prod_proxies = manager.search_proxies("production")
        assert len(prod_proxies) == 1
        assert "production-proxy" in prod_proxies
        
        dev_proxies = manager.search_proxies("development", fields=["tags"])
        assert len(dev_proxies) == 1
        assert "development-proxy" in dev_proxies
        
        # 6. 统计信息
        stats = manager.get_statistics()
        assert stats["total_proxies"] == 3
        assert stats["active_proxies"] == 3
        assert stats["current_proxy"] == "development-proxy"
        assert "production" in stats["tag_distribution"]
        assert "development" in stats["tag_distribution"]
        
        # 7. 配置持久化验证
        # 重新创建管理器，验证数据持久化
        manager2 = ProxyManager(config_path=env["config_file"])
        reloaded_proxies = manager2.list_proxies()
        
        assert len(reloaded_proxies) == 3
        assert manager2.get_current_proxy().name == "development-proxy"
        
        # 8. 更新代理
        result = manager2.update_proxy(
            "backup-proxy",
            description="更新后的备用代理",
            tags=["backup", "updated", "emergency"]
        )
        assert result is True
        
        updated_proxy = manager2.get_proxy("backup-proxy")
        assert updated_proxy.description == "更新后的备用代理"
        assert "updated" in updated_proxy.tags
        
        # 9. 删除代理
        result = manager2.remove_proxy("backup-proxy")
        assert result is True
        
        remaining_proxies = manager2.list_proxies()
        assert len(remaining_proxies) == 2
        assert "backup-proxy" not in remaining_proxies
        
        # 10. 最终状态验证
        final_stats = manager2.get_statistics()
        assert final_stats["total_proxies"] == 2
        assert final_stats["current_proxy"] == "development-proxy"

    def test_configuration_backup_and_recovery_workflow(self, isolated_environment):
        """测试配置备份和恢复工作流程"""
        env = isolated_environment
        
        # 使用启用备份的管理器
        manager = ProxyManager(
            config_path=env["config_file"],
            auto_backup=True,
            max_backups=3
        )
        
        # 添加初始代理
        proxy1 = ProxyServer(
            name="initial-proxy",
            base_url="https://api.initial.com/",
            api_key="sk-initial-1234567890abcdef",
            description="初始代理"
        )
        manager.add_proxy(proxy1)
        
        # 模拟多次配置变更以创建备份
        for i in range(5):
            proxy = ProxyServer(
                name=f"backup-test-{i}",
                base_url=f"https://api{i}.backup-test.com/",
                api_key=f"sk-backup-{i:04d}-{'1' * 20}",
                description=f"备份测试代理 {i}"
            )
            manager.add_proxy(proxy)
            
            # 短暂等待以确保时间戳不同
            time.sleep(0.1)
        
        # 验证创建了备份文件
        backup_files = manager.config_manager.get_backup_files()
        assert len(backup_files) <= 3  # 最大备份数限制
        
        # 获取当前配置状态
        current_proxies = manager.list_proxies()
        current_count = len(current_proxies)
        
        # 模拟配置文件损坏
        env["config_file"].write_text("corrupted configuration data")
        
        # 尝试从备份恢复
        if backup_files:
            latest_backup = backup_files[0]
            result = manager.config_manager.restore_from_backup(latest_backup)
            assert result is True
            
            # 验证恢复后的配置
            manager._config = None  # 清除缓存以强制重新加载
            recovered_proxies = manager.list_proxies()
            
            # 恢复的配置应该接近原始状态
            assert len(recovered_proxies) > 0
            assert "initial-proxy" in recovered_proxies

    def test_multi_format_export_workflow(self, isolated_environment):
        """测试多格式导出工作流程"""
        env = isolated_environment
        manager = ProxyManager(config_path=env["config_file"])
        
        # 创建不同类型的代理
        proxies = [
            ProxyServer(
                name="api-key-proxy",
                base_url="https://api-key.example.com/",
                api_key="sk-api-key-1234567890abcdef1234567890abcdef",
                description="API密钥代理",
                bigmodel="claude-3-5-sonnet-20241022"
            ),
            ProxyServer(
                name="auth-token-proxy",  
                base_url="https://auth-token.example.com/",
                auth_token="sk-ant-api03-auth-token-abcdef1234567890",
                description="认证令牌代理",
                smallmodel="claude-3-haiku-20240307"
            ),
            ProxyServer(
                name="helper-proxy",
                base_url="https://helper.example.com/",
                api_key_helper="get-dynamic-key.sh",
                description="API密钥助手代理"
            )
        ]
        
        for proxy in proxies:
            manager.add_proxy(proxy)
        
        # 测试所有支持的格式导出
        export_formats = [
            ExportFormat(shell_type="bash", include_comments=True),
            ExportFormat(shell_type="fish", include_comments=True),
            ExportFormat(shell_type="powershell", include_comments=True),
            ExportFormat(shell_type="zsh", include_comments=False),
        ]
        
        export_results = {}
        
        for proxy in proxies:
            manager.switch_proxy(proxy.name)
            
            for export_format in export_formats:
                content = manager.export_environment(export_format)
                
                # 验证导出内容
                assert len(content) > 0
                assert proxy.base_url in content
                
                # 根据认证方式验证内容
                auth_method = proxy.get_auth_method()
                if auth_method == "api_key":
                    assert proxy.api_key in content
                elif auth_method == "auth_token":
                    assert proxy.auth_token in content
                elif auth_method == "api_key_helper":
                    assert proxy.api_key_helper in content
                
                # 存储结果用于后续验证
                key = f"{proxy.name}_{export_format.shell_type}"
                export_results[key] = content
        
        # 验证不同格式的特征
        assert "export " in export_results["api-key-proxy_bash"]
        assert "set -gx " in export_results["api-key-proxy_fish"]
        assert "$env:" in export_results["api-key-proxy_powershell"]
        
        # 测试export_all选项
        export_all_format = ExportFormat(shell_type="bash", export_all=True)
        manager.switch_proxy("api-key-proxy")
        all_content = manager.export_environment(export_all_format)
        
        # 应该包含所有代理的信息
        for proxy in proxies:
            if proxy.name != "api-key-proxy":  # 当前代理用标准变量名
                safe_name = proxy.name.upper().replace("-", "_")
                assert f"{safe_name}_API_BASE_URL" in all_content

    def test_claude_code_integration_workflow(self, isolated_environment):
        """测试Claude Code集成工作流程"""
        env = isolated_environment
        
        with patch('claudewarp.core.manager.ProxyManager._get_claude_code_config_dir') as mock_get_dir:
            mock_get_dir.return_value = env["claude_dir"]
            
            manager = ProxyManager(config_path=env["config_file"])
            
            # 添加代理
            proxy = ProxyServer(
                name="claude-integration",
                base_url="https://api.claude-integration.com/",
                api_key="sk-claude-integration-1234567890abcdef",
                description="Claude Code集成测试代理",
                bigmodel="claude-3-5-sonnet-20241022",
                smallmodel="claude-3-haiku-20240307"
            )
            manager.add_proxy(proxy)
            
            # 手动应用Claude Code设置
            result = manager.apply_claude_code_setting()
            assert result is True
            
            # 验证Claude Code配置文件已创建
            settings_file = env["claude_settings"]
            assert settings_file.exists()
            
            # 验证配置文件内容
            with open(settings_file, 'r', encoding='utf-8') as f:
                claude_config = json.load(f)
            
            assert "env" in claude_config
            env_vars = claude_config["env"]
            
            assert env_vars["ANTHROPIC_API_KEY"] == proxy.api_key
            assert env_vars["ANTHROPIC_BASE_URL"] == proxy.base_url
            assert env_vars["ANTHROPIC_MODEL"] == proxy.bigmodel
            assert env_vars["ANTHROPIC_SMALL_FAST_MODEL"] == proxy.smallmodel
            assert env_vars["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] == 1
            
            # 测试代理切换时的自动Claude Code集成
            proxy2 = ProxyServer(
                name="auto-integration",
                base_url="https://api.auto-integration.com/",
                auth_token="sk-ant-api03-auto-integration-token",
                description="自动集成测试代理"
            )
            manager.add_proxy(proxy2)
            
            # 切换代理（应该自动更新Claude Code配置）
            result = manager.switch_proxy("auto-integration")
            assert result is True
            
            # 验证配置文件已更新
            with open(settings_file, 'r', encoding='utf-8') as f:
                updated_config = json.load(f)
            
            updated_env = updated_config["env"]
            assert updated_env["ANTHROPIC_AUTH_TOKEN"] == proxy2.auth_token
            assert updated_env["ANTHROPIC_BASE_URL"] == proxy2.base_url
            assert "ANTHROPIC_API_KEY" not in updated_env  # 应该被清除
            assert "ANTHROPIC_MODEL" not in updated_env  # proxy2没有设置模型
            
            # 测试现有Claude Code配置的合并
            # 手动添加一些自定义配置
            custom_config = {
                "env": {
                    "CUSTOM_VAR": "custom_value",
                    "ANTHROPIC_API_KEY": "old-key-to-be-replaced"
                },
                "permissions": {
                    "allow": ["custom_permission"],
                    "deny": []
                },
                "custom_setting": "preserve_me"
            }
            
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(custom_config, f, indent=2)
            
            # 再次应用Claude Code设置
            result = manager.apply_claude_code_setting("claude-integration")
            assert result is True
            
            # 验证配置合并
            with open(settings_file, 'r', encoding='utf-8') as f:
                merged_config = json.load(f)
            
            merged_env = merged_config["env"]
            
            # 自定义变量应该被保留
            assert merged_env["CUSTOM_VAR"] == "custom_value"
            
            # Claude Warp变量应该被更新
            assert merged_env["ANTHROPIC_API_KEY"] == proxy.api_key
            assert merged_env["ANTHROPIC_BASE_URL"] == proxy.base_url
            
            # 权限应该被保留
            assert merged_config["permissions"]["allow"] == ["custom_permission"]
            
            # 自定义设置应该被保留
            assert merged_config["custom_setting"] == "preserve_me"

    def test_error_handling_and_recovery_workflow(self, isolated_environment):
        """测试错误处理和恢复工作流程"""
        env = isolated_environment
        manager = ProxyManager(config_path=env["config_file"])
        
        # 1. 测试重复代理错误处理
        proxy1 = ProxyServer(
            name="duplicate-test",
            base_url="https://api1.duplicate-test.com/",
            api_key="sk-duplicate-test-1234567890abcdef"
        )
        
        result = manager.add_proxy(proxy1)
        assert result is True
        
        # 尝试添加重复代理
        proxy1_duplicate = ProxyServer(
            name="duplicate-test",  # 同名
            base_url="https://api2.duplicate-test.com/",
            api_key="sk-different-key-1234567890abcdef"
        )
        
        with pytest.raises(DuplicateProxyError):
            manager.add_proxy(proxy1_duplicate)
        
        # 验证原代理未被修改
        original_proxy = manager.get_proxy("duplicate-test")
        assert original_proxy.base_url == "https://api1.duplicate-test.com/"
        
        # 2. 测试无效代理数据处理
        invalid_proxies = [
            # 无效URL
            {
                "name": "invalid-url",
                "base_url": "not-a-valid-url",
                "api_key": "sk-1234567890abcdef"
            },
            # 无效API密钥
            {
                "name": "invalid-key",
                "base_url": "https://api.example.com/",
                "api_key": "too-short"
            },
            # 无效名称
            {
                "name": "invalid name with spaces",
                "base_url": "https://api.example.com/",
                "api_key": "sk-1234567890abcdef"
            }
        ]
        
        for invalid_data in invalid_proxies:
            with pytest.raises(ValidationError):
                ProxyServer(**invalid_data)
        
        # 3. 测试不存在代理的操作
        with pytest.raises(ProxyNotFoundError):
            manager.get_proxy("nonexistent-proxy")
        
        with pytest.raises(ProxyNotFoundError):
            manager.switch_proxy("nonexistent-proxy")
        
        with pytest.raises(ProxyNotFoundError):
            manager.remove_proxy("nonexistent-proxy")
        
        # 4. 测试配置文件损坏的恢复
        # 添加一些有效数据
        valid_proxy = ProxyServer(
            name="recovery-test",
            base_url="https://api.recovery-test.com/",
            api_key="sk-recovery-test-1234567890abcdef"
        )
        manager.add_proxy(valid_proxy)
        
        # 人为损坏配置文件
        env["config_file"].write_text("invalid toml content <<<")
        
        # 创建新管理器实例（触发配置加载）
        with pytest.raises(ConfigError):
            ProxyManager(config_path=env["config_file"])
        
        # 5. 测试部分失败的批量操作
        batch_proxies = []
        for i in range(10):
            try:
                if i == 5:
                    # 故意插入一个重复的代理名称
                    proxy = ProxyServer(
                        name="duplicate-test",  # 已存在
                        base_url=f"https://api{i}.batch-test.com/",
                        api_key=f"sk-batch-{i:04d}-{'1' * 20}"
                    )
                else:
                    proxy = ProxyServer(
                        name=f"batch-proxy-{i}",
                        base_url=f"https://api{i}.batch-test.com/",
                        api_key=f"sk-batch-{i:04d}-{'1' * 20}"
                    )
                
                # 重新创建管理器以绕过损坏的配置
                if i == 0:
                    env["config_file"].unlink()  # 删除损坏的配置
                    manager = ProxyManager(config_path=env["config_file"])
                    manager.add_proxy(proxy1)  # 重新添加原始代理
                
                manager.add_proxy(proxy)
                batch_proxies.append(proxy.name)
                
            except DuplicateProxyError:
                # 预期的错误，继续处理其他代理
                continue
        
        # 验证部分成功的结果
        final_proxies = manager.list_proxies()
        
        # 应该包含原始代理和大部分批量代理（除了重复的那个）
        assert "duplicate-test" in final_proxies
        assert len([name for name in final_proxies.keys() if name.startswith("batch-proxy-")]) == 9

    def test_performance_under_load_workflow(self, isolated_environment):
        """测试负载下的性能工作流程"""
        env = isolated_environment
        manager = ProxyManager(config_path=env["config_file"])
        
        # 添加大量代理
        proxy_count = 1000
        batch_size = 100
        
        start_time = time.time()
        
        for batch in range(0, proxy_count, batch_size):
            batch_proxies = []
            
            for i in range(batch, min(batch + batch_size, proxy_count)):
                proxy = ProxyServer(
                    name=f"perf-proxy-{i:04d}",
                    base_url=f"https://api{i:04d}.perf-test.com/",
                    api_key=f"sk-perf-{i:04d}-{'1' * 20}",
                    description=f"性能测试代理 {i}",
                    tags=[f"batch-{batch//batch_size}", "performance", "test"]
                )
                manager.add_proxy(proxy)
            
            # 每批次后验证状态
            if (batch + batch_size) % (batch_size * 5) == 0:
                current_count = len(manager.list_proxies())
                expected_count = min(batch + batch_size, proxy_count)
                assert current_count == expected_count
        
        total_add_time = time.time() - start_time
        
        # 性能测试
        performance_tests = {}
        
        # 测试列表性能
        start_time = time.time()
        all_proxies = manager.list_proxies()
        performance_tests['list_all'] = time.time() - start_time
        assert len(all_proxies) == proxy_count
        
        # 测试搜索性能
        start_time = time.time()
        search_results = manager.search_proxies("perf-proxy-0500")
        performance_tests['search_exact'] = time.time() - start_time
        assert len(search_results) == 1
        
        # 测试批量搜索性能
        start_time = time.time()
        batch_results = manager.search_proxies("batch-5", fields=["tags"])
        performance_tests['search_batch'] = time.time() - start_time
        assert len(batch_results) == batch_size
        
        # 测试代理切换性能
        start_time = time.time()
        result = manager.switch_proxy("perf-proxy-0500")
        performance_tests['switch_proxy'] = time.time() - start_time
        assert result is True
        
        # 测试统计信息性能
        start_time = time.time()
        stats = manager.get_statistics()
        performance_tests['get_statistics'] = time.time() - start_time
        assert stats["total_proxies"] == proxy_count
        
        # 测试配置保存性能
        start_time = time.time()
        manager.config_manager.save_config(manager.config)
        performance_tests['save_config'] = time.time() - start_time
        
        # 性能断言
        assert total_add_time < 30.0  # 添加1000个代理应该在30秒内完成
        assert performance_tests['list_all'] < 2.0  # 列出所有代理应该在2秒内
        assert performance_tests['search_exact'] < 0.5  # 精确搜索应该在0.5秒内
        assert performance_tests['search_batch'] < 1.0  # 批量搜索应该在1秒内
        assert performance_tests['switch_proxy'] < 0.1  # 代理切换应该在0.1秒内
        assert performance_tests['get_statistics'] < 1.0  # 统计信息应该在1秒内
        assert performance_tests['save_config'] < 5.0  # 配置保存应该在5秒内
        
        print(f"\n性能测试结果 ({proxy_count}个代理):")
        print(f"总添加时间: {total_add_time:.2f}s")
        for operation, duration in performance_tests.items():
            print(f"{operation}: {duration:.4f}s")

    @pytest.mark.slow
    def test_long_running_stability_workflow(self, isolated_environment):
        """测试长时间运行稳定性工作流程"""
        env = isolated_environment
        manager = ProxyManager(config_path=env["config_file"])
        
        # 模拟长时间运行的操作序列
        operation_cycles = 50
        operations_per_cycle = 20
        
        for cycle in range(operation_cycles):
            cycle_proxies = []
            
            # 添加代理
            for i in range(operations_per_cycle):
                proxy = ProxyServer(
                    name=f"stability-{cycle:03d}-{i:03d}",
                    base_url=f"https://api{cycle:03d}-{i:03d}.stability-test.com/",
                    api_key=f"sk-stability-{cycle:03d}-{i:03d}-{'1' * 12}",
                    description=f"稳定性测试代理 {cycle}-{i}"
                )
                manager.add_proxy(proxy)
                cycle_proxies.append(proxy.name)
            
            # 随机操作
            import random
            for _ in range(operations_per_cycle // 2):
                operation = random.choice(['switch', 'search', 'update', 'stats'])
                
                try:
                    if operation == 'switch' and cycle_proxies:
                        proxy_name = random.choice(cycle_proxies)
                        manager.switch_proxy(proxy_name)
                    
                    elif operation == 'search':
                        search_term = f"stability-{cycle:03d}"
                        manager.search_proxies(search_term)
                    
                    elif operation == 'update' and cycle_proxies:
                        proxy_name = random.choice(cycle_proxies)
                        manager.update_proxy(
                            proxy_name,
                            description=f"更新的描述 {cycle}-{random.randint(1000, 9999)}"
                        )
                    
                    elif operation == 'stats':
                        manager.get_statistics()
                
                except (ProxyNotFoundError, ValidationError):
                    # 在并发或复杂操作中可能出现的预期错误
                    continue
            
            # 删除部分代理以避免无限增长
            if cycle % 5 == 4:  # 每5个周期清理一次
                proxies_to_delete = cycle_proxies[::2]  # 删除一半
                for proxy_name in proxies_to_delete:
                    try:
                        manager.remove_proxy(proxy_name)
                    except ProxyNotFoundError:
                        continue
            
            # 定期验证系统状态
            if cycle % 10 == 9:
                all_proxies = manager.list_proxies()
                current = manager.get_current_proxy()
                
                # 基本健康检查
                assert len(all_proxies) > 0
                assert current is not None
                assert current.name in all_proxies
                
                # 验证配置文件完整性
                assert env["config_file"].exists()
                assert env["config_file"].stat().st_size > 0
        
        # 最终稳定性验证
        final_proxies = manager.list_proxies()
        final_stats = manager.get_statistics()
        
        # 系统应该仍然功能正常
        assert len(final_proxies) > 0
        assert final_stats["total_proxies"] == len(final_proxies)
        assert final_stats["current_proxy"] is not None
        
        # 配置文件应该可以被重新加载
        manager2 = ProxyManager(config_path=env["config_file"])
        reloaded_proxies = manager2.list_proxies()
        assert len(reloaded_proxies) == len(final_proxies)