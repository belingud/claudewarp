"""
应用程序集成测试

测试整个应用程序的集成功能和端到端工作流程。
"""
# ruff: noqa: E401

import sys
import tempfile
from pathlib import Path

import pytest

from claudewarp.core.config import ConfigManager
from claudewarp.core.manager import ProxyManager
from claudewarp.core.models import ProxyServer


class TestApplicationIntegration:
    """应用程序集成测试"""

    @pytest.fixture
    def temp_config_dir(self):
        """临时配置目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def integrated_manager(self, temp_config_dir):
        """集成的代理管理器"""
        config_path = temp_config_dir / "config.toml"
        config_manager = ConfigManager(config_path=config_path)
        return ProxyManager(config_manager=config_manager)

    def test_end_to_end_proxy_management(self, integrated_manager):
        """端到端代理管理测试"""
        # 1. 验证初始状态
        assert integrated_manager.get_proxy_count() == 0
        assert integrated_manager.get_current_proxy() is None

        # 2. 添加第一个代理
        proxy1 = ProxyServer(
            name="proxy-1",
            base_url="https://api1.example.com/",
            api_key="sk-1111111111111111",
            description="第一个代理",
            tags=["primary", "test"],
        )

        result = integrated_manager.add_proxy(proxy1)
        assert result is True
        assert integrated_manager.get_proxy_count() == 1
        assert integrated_manager.get_current_proxy().name == "proxy-1"

        # 3. 添加第二个代理
        proxy2 = ProxyServer(
            name="proxy-2",
            base_url="https://api2.example.com/",
            api_key="sk-2222222222222222",
            description="第二个代理",
            tags=["secondary", "test"],
        )

        integrated_manager.add_proxy(proxy2)
        assert integrated_manager.get_proxy_count() == 2

        # 4. 测试代理列表
        proxies = integrated_manager.list_proxies()
        assert len(proxies) == 2
        assert "proxy-1" in proxies
        assert "proxy-2" in proxies

        # 5. 切换代理
        integrated_manager.switch_proxy("proxy-2")
        assert integrated_manager.get_current_proxy().name == "proxy-2"

        # 6. 更新代理
        integrated_manager.update_proxy("proxy-1", description="更新后的描述")
        updated_proxy = integrated_manager.get_proxy("proxy-1")
        assert updated_proxy.description == "更新后的描述"

        # 7. 测试搜索
        search_results = integrated_manager.search_proxies("primary")
        assert len(search_results) == 1
        assert "proxy-1" in search_results

        # 8. 测试环境变量导出
        export_content = integrated_manager.export_environment()
        assert "ANTHROPIC_BASE_URL" in export_content
        assert "https://api2.example.com/" in export_content  # 当前代理

        # 9. 删除代理
        integrated_manager.remove_proxy("proxy-1")
        assert integrated_manager.get_proxy_count() == 1
        assert integrated_manager.get_current_proxy().name == "proxy-2"

        # 10. 删除最后一个代理
        integrated_manager.remove_proxy("proxy-2")
        assert integrated_manager.get_proxy_count() == 0
        assert integrated_manager.get_current_proxy() is None

    def test_configuration_persistence(self, temp_config_dir):
        """测试配置持久化"""
        config_path = temp_config_dir / "config.toml"

        # 创建第一个管理器实例
        config_manager1 = ConfigManager(config_path=config_path)
        manager1 = ProxyManager(config_manager=config_manager1)

        # 添加代理
        proxy = ProxyServer(
            name="persistent-proxy",
            base_url="https://api.example.com/",
            api_key="sk-1234567890abcdef",
            description="持久化测试代理",
        )
        manager1.add_proxy(proxy)

        # 验证配置文件存在
        assert config_path.exists()

        # 创建第二个管理器实例（模拟重启）
        config_manager2 = ConfigManager(config_path=config_path)
        manager2 = ProxyManager(config_manager=config_manager2)

        # 验证数据持久化
        assert manager2.get_proxy_count() == 1
        loaded_proxy = manager2.get_proxy("persistent-proxy")
        assert loaded_proxy.name == proxy.name
        assert loaded_proxy.base_url == proxy.base_url
        assert loaded_proxy.description == proxy.description
        assert manager2.get_current_proxy().name == "persistent-proxy"

    def test_error_recovery_and_validation(self, integrated_manager):
        """测试错误恢复和验证"""
        # 1. 测试添加无效代理
        with pytest.raises(Exception):  # 应该抛出验证异常
            invalid_proxy = ProxyServer(
                name="invalid proxy name",  # 无效名称
                base_url="https://api.example.com/",
                api_key="sk-1234567890",
            )
            integrated_manager.add_proxy(invalid_proxy)

        # 2. 测试操作不存在的代理
        with pytest.raises(Exception):
            integrated_manager.get_proxy("nonexistent")

        with pytest.raises(Exception):
            integrated_manager.switch_proxy("nonexistent")

        with pytest.raises(Exception):
            integrated_manager.remove_proxy("nonexistent")

        # 3. 测试重复代理
        proxy = ProxyServer(
            name="test-proxy", base_url="https://api.example.com/", api_key="sk-1234567890abcdef"
        )
        integrated_manager.add_proxy(proxy)

        with pytest.raises(Exception):  # 应该抛出重复代理异常
            integrated_manager.add_proxy(proxy)

    def test_statistics_and_monitoring(self, integrated_manager):
        """测试统计信息和监控功能"""
        # 添加不同状态的代理
        active_proxy = ProxyServer(
            name="active-proxy",
            base_url="https://api1.example.com/",
            api_key="sk-1111111111",
            is_active=True,
            tags=["prod", "main"],
        )

        inactive_proxy = ProxyServer(
            name="inactive-proxy",
            base_url="https://api2.example.com/",
            api_key="sk-2222222222",
            is_active=False,
            tags=["dev", "backup"],
        )

        integrated_manager.add_proxy(active_proxy)
        integrated_manager.add_proxy(inactive_proxy)

        # 获取统计信息
        stats = integrated_manager.get_statistics()

        assert stats["total_proxies"] == 2
        assert stats["active_proxies"] == 1
        assert stats["inactive_proxies"] == 1
        assert stats["current_proxy"] == "active-proxy"
        assert stats["has_current_proxy"] is True

        # 验证标签分布
        tag_dist = stats["tag_distribution"]
        assert "prod" in tag_dist
        assert "dev" in tag_dist
        assert "main" in tag_dist
        assert "backup" in tag_dist

        # 测试代理验证
        is_valid, message = integrated_manager.validate_proxy_connection("active-proxy")
        assert is_valid is True
        assert "有效" in message

    def test_export_functionality_comprehensive(self, integrated_manager):
        """测试全面的导出功能"""
        # 添加代理
        proxy = ProxyServer(
            name="export-test",
            base_url="https://export.example.com/",
            api_key="sk-export-key-123456",
            description="导出测试代理",
        )
        integrated_manager.add_proxy(proxy)

        # 测试不同格式的导出
        from core.models import ExportFormat

        # Bash格式
        bash_format = ExportFormat(shell_type="bash", include_comments=True)
        bash_content = integrated_manager.export_environment(bash_format)
        assert "export ANTHROPIC_BASE_URL=" in bash_content
        assert "export ANTHROPIC_API_KEY=" in bash_content
        assert "https://export.example.com/" in bash_content
        assert "sk-export-key-123456" in bash_content
        assert "# Claude中转站环境变量配置" in bash_content

        # Fish格式
        fish_format = ExportFormat(shell_type="fish", include_comments=False)
        fish_content = integrated_manager.export_environment(fish_format)
        assert "set -x ANTHROPIC_BASE_URL" in fish_content
        assert "set -x ANTHROPIC_API_KEY" in fish_content
        assert "# Claude中转站环境变量配置" not in fish_content

        # PowerShell格式
        ps_format = ExportFormat(shell_type="powershell", prefix="CUSTOM_")
        ps_content = integrated_manager.export_environment(ps_format)
        assert "$env:CUSTOM_BASE_URL=" in ps_content
        assert "$env:CUSTOM_API_KEY=" in ps_content

        # 指定代理导出
        specific_content = integrated_manager.export_environment(
            bash_format, proxy_name="export-test"
        )
        assert "https://export.example.com/" in specific_content

    def test_concurrent_operations_safety(self, temp_config_dir):
        """测试并发操作安全性"""
        config_path = temp_config_dir / "config.toml"

        # 创建两个管理器实例模拟并发访问
        manager1 = ProxyManager(ConfigManager(config_path=config_path))
        manager2 = ProxyManager(ConfigManager(config_path=config_path))

        # 实例1添加代理
        proxy1 = ProxyServer(
            name="concurrent-1", base_url="https://api1.example.com/", api_key="sk-1111111111"
        )
        manager1.add_proxy(proxy1)

        # 实例2刷新配置并操作
        manager2.refresh_config()
        proxy2 = ProxyServer(
            name="concurrent-2", base_url="https://api2.example.com/", api_key="sk-2222222222"
        )
        manager2.add_proxy(proxy2)

        # 验证两个代理都存在
        manager1.refresh_config()
        assert manager1.get_proxy_count() == 2
        assert "concurrent-1" in manager1.list_proxies()
        assert "concurrent-2" in manager1.list_proxies()


class TestMainEntryPoints:
    """测试主程序入口点"""

    def test_main_py_structure(self):
        """测试main.py结构"""
        # 验证main.py可以导入
        try:
            import main

            assert hasattr(main, "main")
            assert hasattr(main, "parse_arguments")
        except ImportError:
            pytest.skip("main.py not available for import")

    def test_cli_entry_point(self):
        """测试CLI入口点"""
        try:
            from cli.main import main as cli_main

            assert callable(cli_main)
        except ImportError:
            pytest.skip("CLI module not available")

    def test_gui_entry_point(self):
        """测试GUI入口点"""
        try:
            from gui.app import main as gui_main

            assert callable(gui_main)
        except ImportError:
            pytest.skip("GUI module not available")


class TestSystemRequirements:
    """测试系统需求和兼容性"""

    def test_python_version_compatibility(self):
        """测试Python版本兼容性"""
        assert sys.version_info >= (3, 8), "需要Python 3.8或更高版本"

    def test_required_modules_import(self):
        """测试必需模块导入"""
        # 核心模块

        # CLI模块
        try:
            import cli.commands
            import cli.formatters
            import cli.main
        except ImportError as e:
            pytest.skip(f"CLI modules not available: {e}")

        # 测试Pydantic

        # 测试TOML

    def test_optional_dependencies(self):
        """测试可选依赖"""
        # GUI依赖
        try:
            from PySide6.QtCore import Qt
            from PySide6.QtWidgets import QApplication

            gui_available = True
        except ImportError:
            gui_available = False

        # Rich依赖（CLI美化）
        try:
            from rich.console import Console  # noqa: F401
            from rich.table import Table  # noqa: F401

            rich_available = True
        except ImportError:
            rich_available = False

        # Typer依赖（CLI框架）
        try:
            import typer  # noqa: F401

            typer_available = True
        except ImportError:
            typer_available = False

        print(f"GUI支持: {gui_available}")
        print(f"Rich支持: {rich_available}")
        print(f"Typer支持: {typer_available}")


class TestPerformanceRequirements:
    """测试性能需求"""

    def test_config_load_performance(self, temp_config_dir):
        """测试配置加载性能"""
        import time

        # 创建配置文件
        config_path = temp_config_dir / "config.toml"
        manager = ProxyManager(ConfigManager(config_path=config_path))

        # 添加一些代理
        for i in range(10):
            proxy = ProxyServer(
                name=f"perf-proxy-{i}",
                base_url=f"https://api{i}.example.com/",
                api_key=f"sk-{'1' * 10}{i}",
            )
            manager.add_proxy(proxy)

        # 测试加载性能
        start_time = time.time()
        new_manager = ProxyManager(ConfigManager(config_path=config_path))
        _ = new_manager.config  # 触发配置加载
        load_time = time.time() - start_time

        # 配置加载应该在100ms内完成
        assert load_time < 0.1, f"配置加载时间过长: {load_time:.3f}s"

    def test_proxy_switch_performance(self, integrated_manager):
        """测试代理切换性能"""
        import time

        # 添加多个代理
        for i in range(5):
            proxy = ProxyServer(
                name=f"switch-proxy-{i}",
                base_url=f"https://api{i}.example.com/",
                api_key=f"sk-{'1' * 10}{i}",
            )
            integrated_manager.add_proxy(proxy)

        # 测试切换性能
        start_time = time.time()
        integrated_manager.switch_proxy("switch-proxy-2")
        switch_time = time.time() - start_time

        # 代理切换应该在50ms内完成
        assert switch_time < 0.05, f"代理切换时间过长: {switch_time:.3f}s"


@pytest.mark.integration
class TestFullApplicationWorkflow:
    """完整应用程序工作流程测试"""

    def test_complete_user_workflow(self, temp_config_dir):
        """测试完整用户工作流程"""
        # 模拟用户完整使用流程
        config_path = temp_config_dir / "config.toml"
        manager = ProxyManager(ConfigManager(config_path=config_path))

        # 1. 用户首次使用，添加第一个代理
        proxy1 = ProxyServer(
            name="my-first-proxy",
            base_url="https://api.claude-proxy.com/",
            api_key="sk-user-real-api-key-123456",
            description="我的第一个Claude代理",
            tags=["personal", "main"],
        )
        manager.add_proxy(proxy1)

        # 2. 用户测试代理连接
        is_valid, message = manager.validate_proxy_connection("my-first-proxy")
        assert is_valid, f"代理验证失败: {message}"

        # 3. 用户导出环境变量使用
        export_content = manager.export_environment()
        assert "export ANTHROPIC_BASE_URL=" in export_content

        # 4. 用户添加第二个代理（备用）
        proxy2 = ProxyServer(
            name="backup-proxy",
            base_url="https://backup.claude-proxy.com/",
            api_key="sk-backup-api-key-789012",
            description="备用代理服务器",
            tags=["backup", "secondary"],
        )
        manager.add_proxy(proxy2)

        # 5. 用户在不同代理间切换
        manager.switch_proxy("backup-proxy")
        assert manager.get_current_proxy().name == "backup-proxy"

        manager.switch_proxy("my-first-proxy")
        assert manager.get_current_proxy().name == "my-first-proxy"

        # 6. 用户搜索和管理代理
        main_proxies = manager.search_proxies("main")
        assert len(main_proxies) == 1
        assert "my-first-proxy" in main_proxies

        # 7. 用户更新代理信息
        manager.update_proxy("backup-proxy", description="更新后的备用代理描述")
        updated = manager.get_proxy("backup-proxy")
        assert updated.description == "更新后的备用代理描述"

        # 8. 用户查看统计信息
        stats = manager.get_statistics()
        assert stats["total_proxies"] == 2
        assert stats["current_proxy"] == "my-first-proxy"

        # 9. 用户导出特定代理的环境变量
        backup_export = manager.export_environment(proxy_name="backup-proxy")
        assert "backup.claude-proxy.com" in backup_export

        # 10. 用户清理不需要的代理
        manager.remove_proxy("backup-proxy")
        assert manager.get_proxy_count() == 1

        # 11. 验证配置持久化
        new_manager = ProxyManager(ConfigManager(config_path=config_path))
        assert new_manager.get_proxy_count() == 1
        assert new_manager.get_current_proxy().name == "my-first-proxy"
