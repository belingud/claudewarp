"""
CLI功能测试

测试命令行界面的各种命令和功能。
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from cli.commands import app
from core.config import ConfigManager
from core.exceptions import DuplicateProxyError, ProxyNotFoundError, ValidationError
from core.manager import ProxyManager
from core.models import ProxyServer


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
        with patch("cli.commands.get_proxy_manager") as mock_get_manager:
            mock_manager = Mock(spec=ProxyManager)
            mock_get_manager.return_value = mock_manager

            # 模拟交互式输入
            with patch("cli.commands.Prompt.ask") as mock_prompt:
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
        with patch("cli.commands.get_proxy_manager") as mock_get_manager:
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
        with patch("cli.commands.get_proxy_manager") as mock_get_manager:
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
        with patch("cli.commands.get_proxy_manager") as mock_get_manager:
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
        with patch("cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy):
            result = runner.invoke(app, ["list"])

            assert result.exit_code == 0
            assert "test-proxy" in result.stdout
            assert "https://api.example.com/" in result.stdout

    def test_list_command_empty(self, runner):
        """测试列出空代理列表"""
        with patch("cli.commands.get_proxy_manager") as mock_get_manager:
            mock_manager = Mock(spec=ProxyManager)
            mock_manager.list_proxies.return_value = {}
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["list"])

            assert result.exit_code == 0
            assert "暂无代理" in result.stdout

    def test_list_command_json_format(self, runner, mock_manager_with_proxy):
        """测试JSON格式输出"""
        with patch("cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy):
            result = runner.invoke(app, ["list", "--format", "json"])

            assert result.exit_code == 0
            assert '"test-proxy"' in result.stdout
            assert '"current_proxy"' in result.stdout

    def test_list_command_simple_format(self, runner, mock_manager_with_proxy):
        """测试简单格式输出"""
        with patch("cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy):
            result = runner.invoke(app, ["list", "--format", "simple"])

            assert result.exit_code == 0
            assert "test-proxy" in result.stdout

    def test_list_command_search(self, runner):
        """测试搜索功能"""
        with patch("cli.commands.get_proxy_manager") as mock_get_manager:
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
        with patch("cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy):
            result = runner.invoke(app, ["use", "test-proxy"])

            assert result.exit_code == 0
            mock_manager_with_proxy.switch_proxy.assert_called_with("test-proxy")

    def test_use_command_proxy_not_found(self, runner):
        """测试切换不存在的代理"""
        with patch("cli.commands.get_proxy_manager") as mock_get_manager:
            mock_manager = Mock(spec=ProxyManager)
            mock_manager.get_proxy.side_effect = ProxyNotFoundError("代理不存在")
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["use", "nonexistent"])

            assert result.exit_code == 1
            assert "不存在" in result.stdout

    def test_use_command_inactive_proxy(self, runner):
        """测试切换未启用的代理"""
        with patch("cli.commands.get_proxy_manager") as mock_get_manager:
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
            with patch("cli.commands.Confirm.ask", return_value=True):
                result = runner.invoke(app, ["use", "inactive-proxy"])

                assert result.exit_code == 0
                mock_manager.switch_proxy.assert_called_with("inactive-proxy")


class TestCurrentCommand:
    """测试current命令"""

    def test_current_command_with_proxy(self, runner, mock_manager_with_proxy):
        """测试显示当前代理"""
        with patch("cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy):
            result = runner.invoke(app, ["current"])

            assert result.exit_code == 0
            assert "当前代理" in result.stdout
            assert "test-proxy" in result.stdout

    def test_current_command_no_proxy(self, runner):
        """测试没有当前代理"""
        with patch("cli.commands.get_proxy_manager") as mock_get_manager:
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
        with patch("cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy):
            with patch("cli.commands.Confirm.ask", return_value=True):
                result = runner.invoke(app, ["remove", "test-proxy"])

                assert result.exit_code == 0
                mock_manager_with_proxy.remove_proxy.assert_called_with("test-proxy")

    def test_remove_command_cancelled(self, runner, mock_manager_with_proxy):
        """测试取消删除代理"""
        with patch("cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy):
            with patch("cli.commands.Confirm.ask", return_value=False):
                result = runner.invoke(app, ["remove", "test-proxy"])

                assert result.exit_code == 0
                assert "取消" in result.stdout
                mock_manager_with_proxy.remove_proxy.assert_not_called()

    def test_remove_command_force(self, runner, mock_manager_with_proxy):
        """测试强制删除代理"""
        with patch("cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy):
            result = runner.invoke(app, ["remove", "test-proxy", "--force"])

            assert result.exit_code == 0
            mock_manager_with_proxy.remove_proxy.assert_called_with("test-proxy")

    def test_remove_command_proxy_not_found(self, runner):
        """测试删除不存在的代理"""
        with patch("cli.commands.get_proxy_manager") as mock_get_manager:
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

        with patch("cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy):
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

        with patch("cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy):
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

        with patch("cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy):
            result = runner.invoke(app, ["export", "--shell", "powershell"])

            assert result.exit_code == 0
            assert "$env:ANTHROPIC_BASE_URL" in result.stdout

    def test_export_command_no_comments(self, runner, mock_manager_with_proxy):
        """测试导出不包含注释"""
        mock_manager_with_proxy.export_environment.return_value = """
export ANTHROPIC_BASE_URL="https://api.example.com/"
export ANTHROPIC_API_KEY="sk-1234567890abcdef"
        """.strip()

        with patch("cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy):
            result = runner.invoke(app, ["export", "--no-comments"])

            assert result.exit_code == 0
            assert "export ANTHROPIC_BASE_URL" in result.stdout

    def test_export_command_custom_prefix(self, runner, mock_manager_with_proxy):
        """测试导出自定义前缀"""
        mock_manager_with_proxy.export_environment.return_value = """
export CUSTOM_BASE_URL="https://api.example.com/"
export CUSTOM_API_KEY="sk-1234567890abcdef"
        """.strip()

        with patch("cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy):
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

        with patch("cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy):
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
        with patch("cli.commands.get_proxy_manager") as mock_get_manager:
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
        with patch("cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy):
            mock_manager_with_proxy.validate_proxy_connection.return_value = (True, "配置格式有效")

            result = runner.invoke(app, ["info", "test-proxy"])

            assert result.exit_code == 0
            assert "test-proxy" in result.stdout
            assert "详细信息" in result.stdout

    def test_info_command_statistics(self, runner, mock_manager_with_proxy):
        """测试显示统计信息"""
        with patch("cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy):
            result = runner.invoke(app, ["info"])

            assert result.exit_code == 0
            assert "统计信息" in result.stdout
            assert "总代理数量" in result.stdout


class TestEditCommand:
    """测试edit命令"""

    def test_edit_command_success(self, runner, mock_manager_with_proxy):
        """测试成功编辑代理"""
        with patch("cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy):
            result = runner.invoke(app, ["edit", "test-proxy", "--desc", "新的描述"])

            assert result.exit_code == 0
            mock_manager_with_proxy.update_proxy.assert_called_once()

    def test_edit_command_no_changes(self, runner, mock_manager_with_proxy):
        """测试没有指定更新字段"""
        with patch("cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy):
            result = runner.invoke(app, ["edit", "test-proxy"])

            assert result.exit_code == 0
            assert "没有指定" in result.stdout


class TestSearchCommand:
    """测试search命令"""

    def test_search_command_with_results(self, runner, mock_manager_with_proxy):
        """测试搜索有结果"""
        with patch("cli.commands.get_proxy_manager", return_value=mock_manager_with_proxy):
            mock_manager_with_proxy.search_proxies.return_value = {
                "test-proxy": mock_manager_with_proxy.get_proxy.return_value
            }

            result = runner.invoke(app, ["search", "test"])

            assert result.exit_code == 0
            assert "test-proxy" in result.stdout

    def test_search_command_no_results(self, runner):
        """测试搜索无结果"""
        with patch("cli.commands.get_proxy_manager") as mock_get_manager:
            mock_manager = Mock(spec=ProxyManager)
            mock_manager.search_proxies.return_value = {}
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["search", "nonexistent"])

            assert result.exit_code == 0
            assert "未找到" in result.stdout


class TestCLIErrorHandling:
    """测试CLI错误处理"""

    def test_get_proxy_manager_failure(self, runner):
        """测试代理管理器初始化失败"""
        with patch("cli.commands.get_proxy_manager") as mock_get_manager:
            mock_get_manager.side_effect = Exception("初始化失败")

            result = runner.invoke(app, ["list"])

            assert result.exit_code == 1

    def test_keyboard_interrupt_handling(self, runner):
        """测试键盘中断处理"""
        with patch("cli.commands.get_proxy_manager") as mock_get_manager:
            mock_get_manager.side_effect = KeyboardInterrupt()

            result = runner.invoke(app, ["list"])

            # 键盘中断应该被优雅处理
            assert result.exit_code != 0


class TestCLIHelpers:
    """测试CLI辅助功能"""

    def test_main_function(self):
        """测试主函数"""
        with patch("cli.commands.app") as mock_app:
            from cli.commands import main

            main()
            mock_app.assert_called_once()

    def test_get_proxy_manager_default(self):
        """测试获取默认代理管理器"""
        from cli.commands import get_proxy_manager

        manager = get_proxy_manager()
        assert isinstance(manager, ProxyManager)


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

        with patch("cli.commands.get_proxy_manager") as mock_get_manager:
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
