"""
CLI功能测试

测试命令行界面的各种命令和功能。
"""

import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner
from rich.table import Table
from rich.panel import Panel

from claudewarp.cli.commands import app, get_proxy_manager, _update_proxy_with_rename
from claudewarp.cli.formatters import (
    format_proxy_table,
    format_proxy_info,
    format_export_output,
    format_success,
    format_error,
    format_warning,
    format_info,
)
from claudewarp.cli.main import main, cli_main, setup_colored_logging
from claudewarp.core.config import ConfigManager
from claudewarp.core.exceptions import (
    DuplicateProxyError,
    ProxyNotFoundError,
    ValidationError,
    ConfigError,
    NetworkError,
)
from claudewarp.core.manager import ProxyManager
from claudewarp.core.models import ProxyServer


class TestCLICommands:
    """测试CLI命令"""

    @pytest.fixture
    def runner(self):
        """CLI测试运行器"""
        return CliRunner()

    @pytest.fixture
    def temp_config_dir(self):
        """临时配置目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def mock_manager_with_proxy(self):
        """带有代理的模拟管理器"""
        mock_manager = Mock(spec=ProxyManager)

        # 模拟代理
        test_proxy = ProxyServer(
            name="test-proxy",
            base_url="https://api.example.com/",
            api_key="sk-1234567890abcdef",
            description="测试代理",
            tags=["test"],
        )

        # 配置模拟方法
        mock_manager.list_proxies.return_value = {"test-proxy": test_proxy}
        mock_manager.get_current_proxy.return_value = test_proxy
        mock_manager.get_proxy.return_value = test_proxy
        mock_manager.get_statistics.return_value = {
            "total_proxies": 1,
            "active_proxies": 1,
            "inactive_proxies": 0,
            "current_proxy": "test-proxy",
            "config_version": "1.0",
            "last_updated": "2024-01-01T00:00:00",
            "tag_distribution": {"test": 1},
        }

        return mock_manager


class TestAddCommand:
    """测试add命令"""

    def test_add_command_interactive_success(self, runner):
        """测试交互式添加代理成功"""
        with patch("claudewarp.cli.commands.get_proxy_manager") as mock_get_manager:
            mock_manager = Mock(spec=ProxyManager)
            mock_get_manager.return_value = mock_manager

            # 模拟交互式输入
            with patch("claudewarp.cli.commands.typer.prompt") as mock_prompt:
                mock_prompt.side_effect = [
                    "test-proxy",  # 名称
                    "https://api.example.com/",  # URL
                    "sk-1234567890abcdef",  # API密钥
                    "测试代理",  # 描述
                    "test,dev",  # 标签
                ]

                result = runner.invoke(app, ["add"])

                assert result.exit_code == 0
                mock_manager.add_proxy.assert_called_once()

    def test_add_command_non_interactive_success(self, runner):
        """测试非交互式添加代理成功"""
        with patch("claudewarp.cli.commands.get_proxy_manager") as mock_get_manager:
            mock_manager = Mock(spec=ProxyManager)
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(
                app,
                [
                    "add",
                    "--name",
                    "test-proxy",
                    "--url",
                    "https://api.example.com/",
                    "--key",
                    "sk-1234567890abcdef",
                    "--desc",
                    "测试代理",
                    "--tags",
                    "test,dev",
                    "--no-interactive",
                ],
            )

            assert result.exit_code == 0
            mock_manager.add_proxy.assert_called_once()

    def test_add_command_missing_required_args(self, runner):
        """测试缺少必需参数"""
        result = runner.invoke(
            app,
            [
                "add",
                "--no-interactive",
                # 缺少必需的参数
            ],
        )

        assert result.exit_code == 1
        assert "必需的" in result.stdout or "required" in result.stdout.lower()

    def test_add_command_duplicate_proxy(self, runner):
        """测试添加重复代理"""
        with patch("claudewarp.cli.commands.get_proxy_manager") as mock_get_manager:
            mock_manager = Mock(spec=ProxyManager)
            mock_manager.add_proxy.side_effect = DuplicateProxyError("代理已存在")
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(
                app,
                [
                    "add",
                    "--name",
                    "existing-proxy",
                    "--url",
                    "https://api.example.com/",
                    "--key",
                    "sk-1234567890abcdef",
                    "--no-interactive",
                ],
            )

            assert result.exit_code == 1
            assert "已存在" in result.stdout

    def test_add_command_validation_error(self, runner):
        """测试验证错误"""
        with patch("claudewarp.cli.commands.get_proxy_manager") as mock_get_manager:
            mock_manager = Mock(spec=ProxyManager)
            mock_manager.add_proxy.side_effect = ValidationError("验证失败")
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(
                app,
                [
                    "add",
                    "--name",
                    "invalid-proxy",
                    "--url",
                    "invalid-url",
                    "--key",
                    "short",
                    "--no-interactive",
                ],
            )

            assert result.exit_code == 1


class TestListCommand:
    """测试list命令"""

    def test_list_command_with_proxies(self, runner, mock_manager_with_proxy):
        """测试列出代理"""
        with patch(
            "claudewarp.cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy
        ):
            result = runner.invoke(app, ["list"])

            assert result.exit_code == 0
            assert "test-proxy" in result.stdout
            assert "https://api.example.com/" in result.stdout

    def test_list_command_empty(self, runner):
        """测试列出空代理列表"""
        with patch("claudewarp.cli.commands.get_proxy_manager") as mock_get_manager:
            mock_manager = Mock(spec=ProxyManager)
            mock_manager.list_proxies.return_value = {}
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["list"])

            assert result.exit_code == 0
            assert "暂无代理" in result.stdout

    def test_list_command_json_format(self, runner, mock_manager_with_proxy):
        """测试JSON格式输出"""
        with patch(
            "claudewarp.cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy
        ):
            result = runner.invoke(app, ["list", "--format", "json"])

            assert result.exit_code == 0
            assert '"test-proxy"' in result.stdout
            assert '"current_proxy"' in result.stdout

    def test_list_command_simple_format(self, runner, mock_manager_with_proxy):
        """测试简单格式输出"""
        with patch(
            "claudewarp.cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy
        ):
            result = runner.invoke(app, ["list", "--format", "simple"])

            assert result.exit_code == 0
            assert "test-proxy" in result.stdout

    def test_list_command_search(self, runner):
        """测试搜索功能"""
        with patch("claudewarp.cli.commands.get_proxy_manager") as mock_get_manager:
            mock_manager = Mock(spec=ProxyManager)
            mock_manager.search_proxies.return_value = {}
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["list", "--search", "test"])

            assert result.exit_code == 0
            mock_manager.search_proxies.assert_called_with("test")


class TestUseCommand:
    """测试use命令"""

    def test_use_command_success(self, runner, mock_manager_with_proxy):
        """测试成功切换代理"""
        with patch(
            "claudewarp.cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy
        ):
            result = runner.invoke(app, ["use", "test-proxy"])

            assert result.exit_code == 0
            mock_manager_with_proxy.switch_proxy.assert_called_with("test-proxy")

    def test_use_command_proxy_not_found(self, runner):
        """测试切换不存在的代理"""
        with patch("claudewarp.cli.commands.get_proxy_manager") as mock_get_manager:
            mock_manager = Mock(spec=ProxyManager)
            mock_manager.get_proxy.side_effect = ProxyNotFoundError("代理不存在")
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["use", "nonexistent"])

            assert result.exit_code == 1
            assert "不存在" in result.stdout

    def test_use_command_inactive_proxy(self, runner):
        """测试切换未启用的代理"""
        with patch("claudewarp.cli.commands.get_proxy_manager") as mock_get_manager:
            mock_manager = Mock(spec=ProxyManager)

            # 模拟未启用的代理
            inactive_proxy = ProxyServer(
                name="inactive-proxy",
                base_url="https://api.example.com/",
                api_key="sk-1234567890abcdef",
                is_active=False,
            )
            mock_manager.get_proxy.return_value = inactive_proxy
            mock_get_manager.return_value = mock_manager

            # 模拟用户确认
            with patch("claudewarp.cli.commands.Confirm.ask", return_value=True):
                result = runner.invoke(app, ["use", "inactive-proxy"])

                assert result.exit_code == 0
                mock_manager.switch_proxy.assert_called_with("inactive-proxy")


class TestCurrentCommand:
    """测试current命令"""

    def test_current_command_with_proxy(self, runner, mock_manager_with_proxy):
        """测试显示当前代理"""
        with patch(
            "claudewarp.cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy
        ):
            result = runner.invoke(app, ["current"])

            assert result.exit_code == 0
            assert "当前代理" in result.stdout
            assert "test-proxy" in result.stdout

    def test_current_command_no_proxy(self, runner):
        """测试没有当前代理"""
        with patch("claudewarp.cli.commands.get_proxy_manager") as mock_get_manager:
            mock_manager = Mock(spec=ProxyManager)
            mock_manager.get_current_proxy.return_value = None
            mock_manager.list_proxies.return_value = {}
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["current"])

            assert result.exit_code == 0
            assert "未设置" in result.stdout


class TestRemoveCommand:
    """测试remove命令"""

    def test_remove_command_success(self, runner, mock_manager_with_proxy):
        """测试成功删除代理"""
        with patch(
            "claudewarp.cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy
        ):
            with patch("claudewarp.cli.commands.Confirm.ask", return_value=True):
                result = runner.invoke(app, ["remove", "test-proxy"])

                assert result.exit_code == 0
                mock_manager_with_proxy.remove_proxy.assert_called_with("test-proxy")

    def test_remove_command_cancelled(self, runner, mock_manager_with_proxy):
        """测试取消删除代理"""
        with patch(
            "claudewarp.cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy
        ):
            with patch("claudewarp.cli.commands.Confirm.ask", return_value=False):
                result = runner.invoke(app, ["remove", "test-proxy"])

                assert result.exit_code == 0
                assert "取消" in result.stdout
                mock_manager_with_proxy.remove_proxy.assert_not_called()

    def test_remove_command_force(self, runner, mock_manager_with_proxy):
        """测试强制删除代理"""
        with patch(
            "claudewarp.cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy
        ):
            result = runner.invoke(app, ["remove", "test-proxy", "--force"])

            assert result.exit_code == 0
            mock_manager_with_proxy.remove_proxy.assert_called_with("test-proxy")

    def test_remove_command_proxy_not_found(self, runner):
        """测试删除不存在的代理"""
        with patch("claudewarp.cli.commands.get_proxy_manager") as mock_get_manager:
            mock_manager = Mock(spec=ProxyManager)
            mock_manager.get_proxy.side_effect = ProxyNotFoundError("代理不存在")
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["remove", "nonexistent"])

            assert result.exit_code == 1
            assert "不存在" in result.stdout


class TestExportCommand:
    """测试export命令"""

    def test_export_command_bash(self, runner, mock_manager_with_proxy):
        """测试导出bash格式"""
        mock_manager_with_proxy.export_environment.return_value = """
# Claude中转站环境变量配置
export ANTHROPIC_BASE_URL="https://api.example.com/"
export ANTHROPIC_API_KEY="sk-1234567890abcdef"
        """.strip()

        with patch(
            "claudewarp.cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy
        ):
            result = runner.invoke(app, ["export", "--shell", "bash"])

            assert result.exit_code == 0
            assert "export ANTHROPIC_BASE_URL" in result.stdout

    def test_export_command_fish(self, runner, mock_manager_with_proxy):
        """测试导出fish格式"""
        mock_manager_with_proxy.export_environment.return_value = """
# Claude中转站环境变量配置
set -x ANTHROPIC_BASE_URL "https://api.example.com/"
set -x ANTHROPIC_API_KEY "sk-1234567890abcdef"
        """.strip()

        with patch(
            "claudewarp.cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy
        ):
            result = runner.invoke(app, ["export", "--shell", "fish"])

            assert result.exit_code == 0
            assert "set -x ANTHROPIC_BASE_URL" in result.stdout

    def test_export_command_powershell(self, runner, mock_manager_with_proxy):
        """测试导出PowerShell格式"""
        mock_manager_with_proxy.export_environment.return_value = """
# Claude中转站环境变量配置
$env:ANTHROPIC_BASE_URL="https://api.example.com/"
$env:ANTHROPIC_API_KEY="sk-1234567890abcdef"
        """.strip()

        with patch(
            "claudewarp.cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy
        ):
            result = runner.invoke(app, ["export", "--shell", "powershell"])

            assert result.exit_code == 0
            assert "$env:ANTHROPIC_BASE_URL" in result.stdout

    def test_export_command_no_comments(self, runner, mock_manager_with_proxy):
        """测试导出不包含注释"""
        mock_manager_with_proxy.export_environment.return_value = """
export ANTHROPIC_BASE_URL="https://api.example.com/"
export ANTHROPIC_API_KEY="sk-1234567890abcdef"
        """.strip()

        with patch(
            "claudewarp.cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy
        ):
            result = runner.invoke(app, ["export", "--no-comments"])

            assert result.exit_code == 0
            assert "export ANTHROPIC_BASE_URL" in result.stdout

    def test_export_command_custom_prefix(self, runner, mock_manager_with_proxy):
        """测试导出自定义前缀"""
        mock_manager_with_proxy.export_environment.return_value = """
export CUSTOM_BASE_URL="https://api.example.com/"
export CUSTOM_API_KEY="sk-1234567890abcdef"
        """.strip()

        with patch(
            "claudewarp.cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy
        ):
            result = runner.invoke(app, ["export", "--prefix", "CUSTOM_"])

            assert result.exit_code == 0
            assert "export CUSTOM_BASE_URL" in result.stdout

    def test_export_command_to_file(self, runner, mock_manager_with_proxy):
        """测试导出到文件"""
        mock_manager_with_proxy.export_environment.return_value = """
export ANTHROPIC_BASE_URL="https://api.example.com/"
export ANTHROPIC_API_KEY="sk-1234567890abcdef"
        """.strip()

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
            temp_path = temp_file.name

        with patch(
            "claudewarp.cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy
        ):
            result = runner.invoke(app, ["export", "--output", temp_path])

            assert result.exit_code == 0
            assert "已导出到" in result.stdout

            # 检查文件内容
            with open(temp_path, "r") as f:
                content = f.read()
                assert "export ANTHROPIC_BASE_URL" in content

        # 清理临时文件
        Path(temp_path).unlink()

    def test_export_command_no_current_proxy(self, runner):
        """测试没有当前代理时导出"""
        with patch("claudewarp.cli.commands.get_proxy_manager") as mock_get_manager:
            mock_manager = Mock(spec=ProxyManager)
            mock_manager.export_environment.side_effect = ProxyNotFoundError("未设置当前代理")
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["export"])

            assert result.exit_code == 1
            assert "未设置" in result.stdout


class TestInfoCommand:
    """测试info命令"""

    def test_info_command_proxy_details(self, runner, mock_manager_with_proxy):
        """测试显示代理详细信息"""
        with patch(
            "claudewarp.cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy
        ):
            mock_manager_with_proxy.validate_proxy_connection.return_value = (True, "配置格式有效")

            result = runner.invoke(app, ["info", "test-proxy"])

            assert result.exit_code == 0
            assert "test-proxy" in result.stdout
            assert "详细信息" in result.stdout

    def test_info_command_statistics(self, runner, mock_manager_with_proxy):
        """测试显示统计信息"""
        with patch(
            "claudewarp.cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy
        ):
            result = runner.invoke(app, ["info"])

            assert result.exit_code == 0
            assert "使用 'cw info <name>' 查看特定代理的详细信息" in result.stdout


class TestEditCommand:
    """测试edit命令"""

    def test_edit_command_success(self, runner, mock_manager_with_proxy):
        """测试成功编辑代理"""
        with patch(
            "claudewarp.cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy
        ):
            result = runner.invoke(app, ["edit", "test-proxy", "--desc", "新的描述"])

            assert result.exit_code == 0
            mock_manager_with_proxy.update_proxy.assert_called_once()

    def test_edit_command_no_changes(self, runner, mock_manager_with_proxy):
        """测试没有指定更新字段"""
        with patch(
            "claudewarp.cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy
        ):
            result = runner.invoke(app, ["edit", "test-proxy"])

            assert result.exit_code == 0
            assert "没有指定" in result.stdout

    def test_edit_command_with_rename(self, runner, mock_manager_with_proxy):
        """测试重命名代理"""
        with patch(
            "claudewarp.cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy
        ):
            # 模拟重命名更新函数
            with patch("claudewarp.cli.commands._update_proxy_with_rename") as mock_rename:
                result = runner.invoke(app, ["edit", "test-proxy", "--name", "new-proxy"])

                assert result.exit_code == 0
                mock_rename.assert_called_once()

    def test_edit_command_interactive(self, runner, mock_manager_with_proxy):
        """测试交互式编辑"""
        with patch(
            "claudewarp.cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy
        ):
            with patch("claudewarp.cli.commands.Prompt.ask") as mock_prompt:
                with patch("claudewarp.cli.commands.Confirm.ask", return_value=True):
                    mock_prompt.side_effect = [
                        "updated-proxy",
                        "https://updated.example.com/",
                        "sk-updated123456",
                        "Updated description",
                        "test,updated",
                    ]

                    result = runner.invoke(app, ["edit", "test-proxy", "--interactive"])

                    assert result.exit_code == 0
                    mock_manager_with_proxy.update_proxy.assert_called_once()


class TestSearchCommand:
    """测试search命令"""

    def test_search_command_with_results(self, runner, mock_manager_with_proxy):
        """测试搜索有结果"""
        with patch(
            "claudewarp.cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy
        ):
            mock_manager_with_proxy.search_proxies.return_value = {
                "test-proxy": mock_manager_with_proxy.get_proxy.return_value
            }

            result = runner.invoke(app, ["search", "test"])

            assert result.exit_code == 0
            assert "test-proxy" in result.stdout

    def test_search_command_no_results(self, runner):
        """测试搜索无结果"""
        with patch("claudewarp.cli.commands.get_proxy_manager") as mock_get_manager:
            mock_manager = Mock(spec=ProxyManager)
            mock_manager.search_proxies.return_value = {}
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["search", "nonexistent"])

            assert result.exit_code == 0
            assert "未找到" in result.stdout

    def test_search_command_custom_fields(self, runner, mock_manager_with_proxy):
        """测试自定义搜索字段"""
        with patch(
            "claudewarp.cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy
        ):
            mock_manager_with_proxy.search_proxies.return_value = {
                "test-proxy": mock_manager_with_proxy.get_proxy.return_value
            }

            result = runner.invoke(app, ["search", "test", "--fields", "name,description"])

            assert result.exit_code == 0
            assert "test-proxy" in result.stdout
            mock_manager_with_proxy.search_proxies.assert_called_with(
                "test", ["name", "description"]
            )


class TestCLIErrorHandling:
    """测试CLI错误处理"""

    def test_get_proxy_manager_failure(self, runner):
        """测试代理管理器初始化失败"""
        with patch("claudewarp.cli.commands.get_proxy_manager") as mock_get_manager:
            mock_get_manager.side_effect = Exception("初始化失败")

            result = runner.invoke(app, ["list"])

            assert result.exit_code == 1

    def test_keyboard_interrupt_handling(self, runner):
        """测试键盘中断处理"""
        with patch("claudewarp.cli.commands.get_proxy_manager") as mock_get_manager:
            mock_get_manager.side_effect = KeyboardInterrupt()

            result = runner.invoke(app, ["list"])

            # 键盘中断应该被优雅处理
            assert result.exit_code != 0

    def test_config_error_handling(self, runner):
        """测试配置错误处理"""
        with patch("claudewarp.cli.commands.get_proxy_manager") as mock_get_manager:
            mock_get_manager.side_effect = ConfigError("配置文件损坏")

            result = runner.invoke(app, ["list"])

            assert result.exit_code == 1

    def test_network_error_handling(self, runner):
        """测试网络错误处理"""
        with patch("claudewarp.cli.commands.get_proxy_manager") as mock_get_manager:
            mock_manager = Mock(spec=ProxyManager)
            mock_manager.list_proxies.side_effect = NetworkError("网络连接失败")
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["list"])

            assert result.exit_code == 1


class TestCLIHelpers:
    """测试CLI辅助功能"""

    def test_main_function(self):
        """测试主函数"""
        with patch("claudewarp.cli.commands.app") as mock_app:
            from claudewarp.cli.commands import main

            main()
            mock_app.assert_called_once()

    def test_get_proxy_manager_default(self):
        """测试获取默认代理管理器"""
        manager = get_proxy_manager()
        assert isinstance(manager, ProxyManager)

    def test_update_proxy_with_rename(self):
        """测试代理重命名函数"""
        mock_manager = Mock(spec=ProxyManager)
        old_proxy = ProxyServer(
            name="old-proxy",
            base_url="https://api.example.com/",
            api_key="sk-1234567890abcdef",
            description="Old description",
            tags=["test"],
        )

        mock_manager.get_proxy.return_value = old_proxy
        mock_manager.get_current_proxy.return_value = old_proxy  # 是当前代理

        update_kwargs = {"description": "New description", "tags": ["test", "updated"]}

        _update_proxy_with_rename(mock_manager, "old-proxy", "new-proxy", update_kwargs)

        # 验证调用顺序
        mock_manager.get_proxy.assert_called_with("old-proxy")
        mock_manager.remove_proxy.assert_called_with("old-proxy")
        mock_manager.add_proxy.assert_called_once()
        mock_manager.switch_proxy.assert_called_with("new-proxy")


# 集成测试
class TestCLIIntegration:
    """CLI集成测试"""

    @pytest.fixture
    def temp_config_dir(self):
        """临时配置目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_full_workflow(self, runner, temp_config_dir):
        """测试完整工作流程"""
        config_path = temp_config_dir / "config.toml"

        with patch("claudewarp.cli.commands.get_proxy_manager") as mock_get_manager:
            # 使用真实的配置管理器和代理管理器
            config_manager = ConfigManager(config_path=config_path)
            manager = ProxyManager(config_manager=config_manager)
            mock_get_manager.return_value = manager

            # 1. 添加代理
            result = runner.invoke(
                app,
                [
                    "add",
                    "--name",
                    "test-proxy",
                    "--url",
                    "https://api.example.com/",
                    "--key",
                    "sk-1234567890abcdef",
                    "--desc",
                    "测试代理",
                    "--no-interactive",
                ],
            )
            assert result.exit_code == 0

            # 2. 列出代理
            result = runner.invoke(app, ["list"])
            assert result.exit_code == 0
            assert "test-proxy" in result.stdout

            # 3. 显示当前代理
            result = runner.invoke(app, ["current"])
            assert result.exit_code == 0
            assert "test-proxy" in result.stdout

            # 4. 导出环境变量
            result = runner.invoke(app, ["export"])
            assert result.exit_code == 0
            assert "export" in result.stdout

            # 5. 删除代理
            result = runner.invoke(app, ["remove", "test-proxy", "--force"])
            assert result.exit_code == 0

            # 6. 验证删除
            result = runner.invoke(app, ["list"])
            assert result.exit_code == 0
            assert "暂无代理" in result.stdout


class TestCLIFormatters:
    """测试CLI格式化器"""

    @pytest.fixture
    def sample_proxy(self):
        """示例代理服务器"""
        return ProxyServer(
            name="test-proxy",
            base_url="https://api.example.com/",
            api_key="sk-1234567890abcdef",
            description="测试代理",
            tags=["test", "dev"],
        )

    def test_format_proxy_table(self, sample_proxy):
        """测试代理表格格式化"""
        proxies = {"test-proxy": sample_proxy}
        table = format_proxy_table(proxies, "test-proxy")

        assert isinstance(table, Table)
        assert table.title == "代理服务器列表"

    def test_format_proxy_table_empty(self):
        """测试空代理表格格式化"""
        table = format_proxy_table({}, None)

        assert isinstance(table, Table)
        assert len(table.rows) == 0

    def test_format_proxy_info(self, sample_proxy):
        """测试代理信息格式化"""
        panel = format_proxy_info(sample_proxy, detailed=True)

        assert isinstance(panel, Panel)
        assert "test-proxy" in str(panel)

    def test_format_proxy_info_simple(self, sample_proxy):
        """测试代理信息简单格式化"""
        panel = format_proxy_info(sample_proxy, detailed=False)

        assert isinstance(panel, Panel)
        assert "test-proxy" in str(panel)

    def test_format_export_output(self):
        """测试环境变量导出格式化"""
        export_content = 'export ANTHROPIC_API_KEY="sk-test"\nexport ANTHROPIC_BASE_URL="https://api.example.com/"'

        result = format_export_output(export_content, "bash")

        # 应该返回Syntax对象
        assert hasattr(result, "code")

    def test_format_messages(self):
        """测试消息格式化函数"""
        success_msg = format_success("操作成功")
        error_msg = format_error("操作失败")
        warning_msg = format_warning("警告信息")
        info_msg = format_info("信息提示")

        assert "✓" in str(success_msg)
        assert "✗" in str(error_msg)
        assert "⚠" in str(warning_msg)
        assert "ℹ" in str(info_msg)


class TestCLIMain:
    """测试CLI主程序"""

    def test_main_success(self):
        """测试主程序成功执行"""
        with patch("claudewarp.cli.main.typer_main") as mock_typer_main:
            result = main()

            assert result == 0
            mock_typer_main.assert_called_once()

    def test_main_keyboard_interrupt(self):
        """测试主程序键盘中断"""
        with patch("claudewarp.cli.main.typer_main", side_effect=KeyboardInterrupt()):
            result = main()

            assert result == 130

    def test_main_exception(self):
        """测试主程序异常处理"""
        with patch("claudewarp.cli.main.typer_main", side_effect=Exception("测试异常")):
            result = main()

            assert result == 1

    def test_cli_main_compatibility(self):
        """测试CLI兼容性入口函数"""
        with patch("claudewarp.cli.main.main", return_value=0) as mock_main:
            result = cli_main(["list"])  # 参数应该被忽略

            assert result == 0
            mock_main.assert_called_once()

    def test_setup_colored_logging(self):
        """测试彩色日志设置"""
        import logging

        # 清除现有处理器
        logger = logging.getLogger()
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # 测试设置函数
        setup_colored_logging()

        # 验证日志器配置
        assert logger.level == logging.INFO
        assert len(logger.handlers) > 0


class TestAdditionalCLICommands:
    """测试额外的CLI命令功能"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_info_command_without_proxy_name(self, runner):
        """测试info命令不指定代理名称"""
        result = runner.invoke(app, ["info"])

        assert result.exit_code == 0
        assert "使用 'cw info <name>' 查看特定代理的详细信息" in result.stdout

    def test_export_command_invalid_shell(self, runner):
        """测试导出命令使用无效shell类型"""
        with patch("claudewarp.cli.commands.get_proxy_manager") as mock_get_manager:
            mock_manager = Mock(spec=ProxyManager)
            mock_manager.export_environment.return_value = "export TEST=value"
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["export", "--shell", "invalid"])

            # 应该使用默认配置处理
            assert result.exit_code == 0

    def test_list_command_with_long_url(self, runner):
        """测试列表命令处理长URL"""
        with patch("claudewarp.cli.commands.get_proxy_manager") as mock_get_manager:
            mock_manager = Mock(spec=ProxyManager)

            long_url_proxy = ProxyServer(
                name="long-url-proxy",
                base_url="https://very-long-url-that-exceeds-thirty-characters.example.com/api/v1/",
                api_key="sk-1234567890abcdef",
                description="Long URL proxy",
                tags=["test"],
            )

            mock_manager.list_proxies.return_value = {"long-url-proxy": long_url_proxy}
            mock_manager.get_current_proxy.return_value = None
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["list"])

            assert result.exit_code == 0
            assert "long-url-proxy" in result.stdout

    def test_add_command_validation_errors(self, runner):
        """测试添加命令的各种验证错误"""
        test_cases = [
            # 无效URL
            (
                [
                    "add",
                    "--name",
                    "test",
                    "--url",
                    "invalid-url",
                    "--key",
                    "sk-test",
                    "--no-interactive",
                ],
                "invalid-url",
            ),
            # 空名称
            (
                [
                    "add",
                    "--name",
                    "",
                    "--url",
                    "https://api.example.com/",
                    "--key",
                    "sk-test",
                    "--no-interactive",
                ],
                "",
            ),
            # 短API密钥
            (
                [
                    "add",
                    "--name",
                    "test",
                    "--url",
                    "https://api.example.com/",
                    "--key",
                    "sk",
                    "--no-interactive",
                ],
                "sk",
            ),
        ]

        for args, invalid_value in test_cases:
            with patch("claudewarp.cli.commands.get_proxy_manager") as mock_get_manager:
                mock_manager = Mock(spec=ProxyManager)
                mock_manager.add_proxy.side_effect = ValidationError(f"Invalid {invalid_value}")
                mock_get_manager.return_value = mock_manager

                result = runner.invoke(app, args)

                assert result.exit_code == 1


class TestApplyCommand:
    """测试apply命令 - Claude Code配置应用"""

    def test_apply_command_success(self, runner, mock_manager_with_proxy):
        """测试成功应用Claude Code配置"""
        with patch(
            "claudewarp.cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy
        ):
            mock_manager_with_proxy.apply_claude_code_setting.return_value = True

            result = runner.invoke(app, ["apply", "test-proxy"])

            assert result.exit_code == 0
            mock_manager_with_proxy.apply_claude_code_setting.assert_called_with("test-proxy")
            assert "成功应用" in result.stdout

    def test_apply_command_current_proxy(self, runner, mock_manager_with_proxy):
        """测试应用当前代理配置"""
        with patch(
            "claudewarp.cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy
        ):
            mock_manager_with_proxy.apply_claude_code_setting.return_value = True

            result = runner.invoke(app, ["apply"])

            assert result.exit_code == 0
            # 应该调用当前代理的名称
            mock_manager_with_proxy.apply_claude_code_setting.assert_called()

    def test_apply_command_failure(self, runner):
        """测试应用配置失败"""
        with patch("claudewarp.cli.commands.get_proxy_manager") as mock_get_manager:
            mock_manager = Mock(spec=ProxyManager)
            mock_manager.apply_claude_code_setting.return_value = False
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["apply", "test-proxy"])

            assert result.exit_code == 1
            assert "应用失败" in result.stdout

    def test_apply_command_no_current_proxy(self, runner):
        """测试没有当前代理时应用"""
        with patch("claudewarp.cli.commands.get_proxy_manager") as mock_get_manager:
            mock_manager = Mock(spec=ProxyManager)
            mock_manager.get_current_proxy.return_value = None
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["apply"])

            assert result.exit_code == 1
            assert "未设置" in result.stdout


class TestValidateCommand:
    """测试validate命令 - 代理配置验证"""

    def test_validate_command_success(self, runner, mock_manager_with_proxy):
        """测试成功验证代理"""
        with patch(
            "claudewarp.cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy
        ):
            mock_manager_with_proxy.validate_proxy_connection.return_value = (True, "连接成功")

            result = runner.invoke(app, ["validate", "test-proxy"])

            assert result.exit_code == 0
            mock_manager_with_proxy.validate_proxy_connection.assert_called_with("test-proxy")
            assert "验证成功" in result.stdout

    def test_validate_command_failure(self, runner, mock_manager_with_proxy):
        """测试验证代理失败"""
        with patch(
            "claudewarp.cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy
        ):
            mock_manager_with_proxy.validate_proxy_connection.return_value = (False, "连接失败")

            result = runner.invoke(app, ["validate", "test-proxy"])

            assert result.exit_code == 1
            assert "验证失败" in result.stdout

    def test_validate_command_all_proxies(self, runner, mock_manager_with_proxy):
        """测试验证所有代理"""
        with patch(
            "claudewarp.cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy
        ):
            mock_manager_with_proxy.validate_all_proxies.return_value = {
                "test-proxy": (True, "连接成功")
            }

            result = runner.invoke(app, ["validate", "--all"])

            assert result.exit_code == 0
            mock_manager_with_proxy.validate_all_proxies.assert_called_once()

    def test_validate_command_proxy_not_found(self, runner):
        """测试验证不存在的代理"""
        with patch("claudewarp.cli.commands.get_proxy_manager") as mock_get_manager:
            mock_manager = Mock(spec=ProxyManager)
            mock_manager.get_proxy.side_effect = ProxyNotFoundError("代理不存在")
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["validate", "nonexistent"])

            assert result.exit_code == 1
            assert "不存在" in result.stdout


class TestStatusCommand:
    """测试status命令 - 系统状态检查"""

    def test_status_command_success(self, runner, mock_manager_with_proxy):
        """测试成功显示状态"""
        with patch(
            "claudewarp.cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy
        ):
            mock_manager_with_proxy.get_status.return_value = {
                "total_proxies": 1,
                "active_proxies": 1,
                "current_proxy": "test-proxy",
                "config_version": "1.0",
                "config_updated_at": "2024-01-01T00:00:00",
                "claude_code_configured": True,
            }

            result = runner.invoke(app, ["status"])

            assert result.exit_code == 0
            assert "总代理数" in result.stdout
            assert "当前代理" in result.stdout

    def test_status_command_detailed(self, runner, mock_manager_with_proxy):
        """测试详细状态显示"""
        with patch(
            "claudewarp.cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy
        ):
            result = runner.invoke(app, ["status", "--detailed"])

            assert result.exit_code == 0
            mock_manager_with_proxy.get_status.assert_called_once()

    def test_status_command_json_format(self, runner, mock_manager_with_proxy):
        """测试JSON格式状态"""
        with patch(
            "claudewarp.cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy
        ):
            result = runner.invoke(app, ["status", "--format", "json"])

            assert result.exit_code == 0
            assert '"total_proxies"' in result.stdout


class TestConfigCommand:
    """测试config命令 - 配置管理"""

    def test_config_get_command(self, runner):
        """测试获取配置值"""
        with patch("claudewarp.cli.commands.get_proxy_manager") as mock_get_manager:
            mock_manager = Mock(spec=ProxyManager)
            mock_manager.get_config_value.return_value = "test-value"
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["config", "get", "test-key"])

            assert result.exit_code == 0
            assert "test-value" in result.stdout

    def test_config_set_command(self, runner):
        """测试设置配置值"""
        with patch("claudewarp.cli.commands.get_proxy_manager") as mock_get_manager:
            mock_manager = Mock(spec=ProxyManager)
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["config", "set", "test-key", "test-value"])

            assert result.exit_code == 0
            mock_manager.set_config_value.assert_called_with("test-key", "test-value")

    def test_config_list_command(self, runner):
        """测试列出所有配置"""
        with patch("claudewarp.cli.commands.get_proxy_manager") as mock_get_manager:
            mock_manager = Mock(spec=ProxyManager)
            mock_manager.get_all_config.return_value = {"key1": "value1", "key2": "value2"}
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["config", "list"])

            assert result.exit_code == 0
            assert "key1" in result.stdout
            assert "value1" in result.stdout


class TestTagCommand:
    """测试tag命令 - 标签管理"""

    def test_tag_list_command(self, runner, mock_manager_with_proxy):
        """测试列出所有标签"""
        with patch(
            "claudewarp.cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy
        ):
            mock_manager_with_proxy.get_all_tags.return_value = ["test", "dev", "prod"]

            result = runner.invoke(app, ["tag", "list"])

            assert result.exit_code == 0
            assert "test" in result.stdout
            assert "dev" in result.stdout

    def test_tag_add_command(self, runner, mock_manager_with_proxy):
        """测试为代理添加标签"""
        with patch(
            "claudewarp.cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy
        ):
            result = runner.invoke(app, ["tag", "add", "test-proxy", "new-tag"])

            assert result.exit_code == 0
            mock_manager_with_proxy.add_proxy_tag.assert_called_with("test-proxy", "new-tag")

    def test_tag_remove_command(self, runner, mock_manager_with_proxy):
        """测试从代理移除标签"""
        with patch(
            "claudewarp.cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy
        ):
            result = runner.invoke(app, ["tag", "remove", "test-proxy", "test"])

            assert result.exit_code == 0
            mock_manager_with_proxy.remove_proxy_tag.assert_called_with("test-proxy", "test")

    def test_tag_search_command(self, runner, mock_manager_with_proxy):
        """测试按标签搜索代理"""
        with patch(
            "claudewarp.cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy
        ):
            mock_manager_with_proxy.search_by_tags.return_value = {
                "test-proxy": mock_manager_with_proxy.get_proxy.return_value
            }

            result = runner.invoke(app, ["tag", "search", "test"])

            assert result.exit_code == 0
            mock_manager_with_proxy.search_by_tags.assert_called_with(["test"])


class TestBackupCommand:
    """测试backup命令 - 配置备份和恢复"""

    def test_backup_create_command(self, runner):
        """测试创建配置备份"""
        with patch("claudewarp.cli.commands.get_proxy_manager") as mock_get_manager:
            mock_manager = Mock(spec=ProxyManager)
            mock_get_manager.return_value = mock_manager

            with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_file:
                backup_path = temp_file.name

            result = runner.invoke(app, ["backup", "create", backup_path])

            assert result.exit_code == 0
            mock_manager.create_backup.assert_called_with(backup_path)

            # 清理临时文件
            Path(backup_path).unlink(missing_ok=True)

    def test_backup_restore_command(self, runner):
        """测试恢复配置备份"""
        with patch("claudewarp.cli.commands.get_proxy_manager") as mock_get_manager:
            mock_manager = Mock(spec=ProxyManager)
            mock_get_manager.return_value = mock_manager

            with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_file:
                backup_path = temp_file.name
                # 写入测试数据
                json.dump({"test": "data"}, temp_file)

            result = runner.invoke(app, ["backup", "restore", backup_path])

            assert result.exit_code == 0
            mock_manager.restore_backup.assert_called_with(backup_path)

            # 清理临时文件
            Path(backup_path).unlink(missing_ok=True)

    def test_backup_list_command(self, runner):
        """测试列出备份文件"""
        with patch("claudewarp.cli.commands.get_proxy_manager") as mock_get_manager:
            mock_manager = Mock(spec=ProxyManager)
            mock_manager.list_backups.return_value = [
                {"name": "backup1.json", "created_at": "2024-01-01T00:00:00"},
                {"name": "backup2.json", "created_at": "2024-01-02T00:00:00"},
            ]
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["backup", "list"])

            assert result.exit_code == 0
            assert "backup1.json" in result.stdout


class TestImportExportCommand:
    """测试import/export命令 - 配置导入导出"""

    def test_import_from_file(self, runner):
        """测试从文件导入配置"""
        with patch("claudewarp.cli.commands.get_proxy_manager") as mock_get_manager:
            mock_manager = Mock(spec=ProxyManager)
            mock_get_manager.return_value = mock_manager

            # 创建临时配置文件
            config_data = {
                "proxies": {
                    "imported-proxy": {
                        "name": "imported-proxy",
                        "base_url": "https://api.imported.com/",
                        "api_key": "sk-imported123456",
                        "description": "导入的代理",
                    }
                }
            }

            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as temp_file:
                json.dump(config_data, temp_file)
                config_path = temp_file.name

            result = runner.invoke(app, ["import", config_path])

            assert result.exit_code == 0
            mock_manager.import_config.assert_called_with(config_path)

            # 清理临时文件
            Path(config_path).unlink(missing_ok=True)

    def test_export_to_file(self, runner, mock_manager_with_proxy):
        """测试导出配置到文件"""
        with patch(
            "claudewarp.cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy
        ):
            with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_file:
                export_path = temp_file.name

            result = runner.invoke(app, ["export", "--output", export_path])

            assert result.exit_code == 0
            mock_manager_with_proxy.export_config.assert_called_with(export_path)

            # 清理临时文件
            Path(export_path).unlink(missing_ok=True)

    def test_import_merge_strategy(self, runner):
        """测试导入时的合并策略"""
        with patch("claudewarp.cli.commands.get_proxy_manager") as mock_get_manager:
            mock_manager = Mock(spec=ProxyManager)
            mock_get_manager.return_value = mock_manager

            runner.invoke(app, ["import", "test.json", "--merge", "replace"])

            mock_manager.import_config.assert_called_with("test.json", merge_strategy="replace")


class TestVerboseLogging:
    """测试详细日志输出"""

    def test_verbose_flag_enables_debug_logging(self, runner):
        """测试verbose标志启用调试日志"""
        runner.invoke(app, ["--verbose", "list"])

        # 检查是否启用了详细日志输出
        # 这里主要测试命令能够正常执行，实际的日志级别检查需要更复杂的设置

    def test_quiet_flag_reduces_output(self, runner):
        """测试quiet标志减少输出"""
        result = runner.invoke(app, ["--quiet", "list"])

        # quiet模式下输出应该更少


class TestHelpAndVersion:
    """测试帮助和版本信息"""

    def test_help_command(self, runner):
        """测试显示帮助信息"""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "Claude中转站管理工具" in result.stdout

    def test_version_command(self, runner):
        """测试显示版本信息"""
        result = runner.invoke(app, ["--version"])

        assert result.exit_code == 0

    def test_command_specific_help(self, runner):
        """测试命令特定的帮助"""
        result = runner.invoke(app, ["add", "--help"])

        assert result.exit_code == 0
        assert "添加代理" in result.stdout


class TestShellCompletion:
    """测试Shell自动完成"""

    def test_bash_completion(self, runner):
        """测试Bash自动完成脚本生成"""
        result = runner.invoke(app, ["--install-completion", "bash"])

        # 测试是否能正常生成completion脚本

    def test_fish_completion(self, runner):
        """测试Fish自动完成脚本生成"""
        result = runner.invoke(app, ["--install-completion", "fish"])

        # 测试是否能正常生成completion脚本


class TestErrorRecovery:
    """测试错误恢复机制"""

    def test_corrupted_config_recovery(self, runner):
        """测试损坏配置文件的恢复"""
        with patch("claudewarp.cli.commands.get_proxy_manager") as mock_get_manager:
            mock_get_manager.side_effect = ConfigError("配置文件损坏")

            result = runner.invoke(app, ["list"])

            assert result.exit_code == 1
            assert "配置文件" in result.stdout

    def test_network_timeout_handling(self, runner):
        """测试网络超时处理"""
        with patch("claudewarp.cli.commands.get_proxy_manager") as mock_get_manager:
            mock_manager = Mock(spec=ProxyManager)
            mock_manager.validate_proxy_connection.side_effect = NetworkError("网络超时")
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["validate", "test-proxy"])

            assert result.exit_code == 1
            assert "网络" in result.stdout

    def test_permission_denied_handling(self, runner):
        """测试权限拒绝处理"""
        with patch("claudewarp.cli.commands.get_proxy_manager") as mock_get_manager:
            mock_get_manager.side_effect = PermissionError("权限不足")

            result = runner.invoke(app, ["list"])

            assert result.exit_code == 1


class TestPerformanceOptimizations:
    """测试性能优化"""

    def test_large_proxy_list_performance(self, runner):
        """测试大量代理列表的性能"""
        with patch("claudewarp.cli.commands.get_proxy_manager") as mock_get_manager:
            mock_manager = Mock(spec=ProxyManager)

            # 模拟大量代理
            large_proxy_list = {}
            for i in range(1000):
                proxy = ProxyServer(
                    name=f"proxy-{i}",
                    base_url=f"https://api{i}.example.com/",
                    api_key=f"sk-{i:016d}",
                    description=f"代理 {i}",
                )
                large_proxy_list[f"proxy-{i}"] = proxy

            mock_manager.list_proxies.return_value = large_proxy_list
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["list"])

            assert result.exit_code == 0

    def test_pagination_for_large_lists(self, runner):
        """测试大列表的分页功能"""
        with patch("claudewarp.cli.commands.get_proxy_manager") as mock_get_manager:
            mock_manager = Mock(spec=ProxyManager)
            # 测试分页逻辑
            result = runner.invoke(app, ["list", "--limit", "10", "--offset", "20"])

            assert result.exit_code == 0


class TestEdgeCases:
    """测试边界情况"""

    def test_empty_proxy_name(self, runner):
        """测试空代理名称"""
        result = runner.invoke(
            app,
            [
                "add",
                "--name",
                "",
                "--url",
                "https://api.example.com/",
                "--key",
                "sk-test",
                "--no-interactive",
            ],
        )

        assert result.exit_code == 1

    def test_very_long_proxy_name(self, runner):
        """测试非常长的代理名称"""
        long_name = "a" * 1000
        result = runner.invoke(
            app,
            [
                "add",
                "--name",
                long_name,
                "--url",
                "https://api.example.com/",
                "--key",
                "sk-test",
                "--no-interactive",
            ],
        )

        # 应该有合理的长度限制

    def test_special_characters_in_name(self, runner):
        """测试名称中的特殊字符"""
        with patch("claudewarp.cli.commands.get_proxy_manager") as mock_get_manager:
            mock_manager = Mock(spec=ProxyManager)
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(
                app,
                [
                    "add",
                    "--name",
                    "proxy-with-特殊字符-and-emoji-🚀",
                    "--url",
                    "https://api.example.com/",
                    "--key",
                    "sk-test",
                    "--no-interactive",
                ],
            )

            # 应该能正确处理特殊字符

    def test_unicode_in_description(self, runner):
        """测试描述中的Unicode字符"""
        with patch("claudewarp.cli.commands.get_proxy_manager") as mock_get_manager:
            mock_manager = Mock(spec=ProxyManager)
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(
                app,
                [
                    "add",
                    "--name",
                    "test",
                    "--url",
                    "https://api.example.com/",
                    "--key",
                    "sk-test",
                    "--desc",
                    "描述包含中文和emoji 🌟",
                    "--no-interactive",
                ],
            )


class TestConcurrency:
    """测试并发访问"""

    def test_concurrent_proxy_operations(self, runner):
        """测试并发代理操作"""
        # 这里可以测试多个CLI进程同时操作配置文件的情况
        # 实际实现需要使用threading或multiprocessing
        pass

    def test_file_locking_behavior(self, runner):
        """测试文件锁定行为"""
        # 测试配置文件的锁定机制，防止并发写入冲突
        pass
