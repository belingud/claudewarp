"""
pytest配置文件

配置测试环境和共享fixture。
"""

import sys
import tempfile
from pathlib import Path

import pytest

# 将项目根目录添加到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from claudewarp.core.config import ConfigManager
from claudewarp.core.manager import ProxyManager

# 导入需要的模块
from claudewarp.core.models import ProxyConfig, ProxyServer, ExportFormat


@pytest.fixture
def temp_dir():
    """函数级临时目录"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_proxy():
    """示例代理fixture"""
    return ProxyServer(
        name="test-proxy",
        base_url="https://api.example.com/",
        api_key="sk-1234567890abcdef",
        description="测试代理",
        tags=["test"],
    )


@pytest.fixture
def sample_auth_token_proxy():
    """示例认证令牌代理fixture"""
    return ProxyServer(
        name="auth-proxy",
        base_url="https://api.auth.example.com/",
        auth_token="sk-ant-api03-token123456",
        description="认证令牌代理",
        tags=["auth", "test"],
    )


@pytest.fixture
def sample_api_key_helper_proxy():
    """示例API密钥助手代理fixture"""
    return ProxyServer(
        name="helper-proxy",
        base_url="https://api.helper.example.com/",
        api_key_helper="echo sk-helper123",
        description="API密钥助手代理",
        tags=["helper", "test"],
    )


@pytest.fixture
def sample_proxy_with_models():
    """包含模型配置的示例代理fixture"""
    return ProxyServer(
        name="model-proxy",
        base_url="https://api.model.example.com/",
        api_key="sk-model123456",
        description="包含模型配置的代理",
        tags=["model", "test"],
        bigmodel="claude-3-opus-20240229",
        smallmodel="claude-3-haiku-20240307",
    )


@pytest.fixture
def sample_inactive_proxy():
    """非活跃代理fixture"""
    return ProxyServer(
        name="inactive-proxy",
        base_url="https://api.inactive.example.com/",
        api_key="sk-inactive123",
        description="非活跃代理",
        tags=["inactive", "test"],
        is_active=False,
    )


@pytest.fixture
def sample_config():
    """示例配置fixture"""
    proxy = ProxyServer(
        name="test-proxy",
        base_url="https://api.example.com/",
        api_key="sk-1234567890abcdef",
        description="测试代理",
        tags=["test"],
    )

    return ProxyConfig(
        current_proxy="test-proxy", proxies={"test-proxy": proxy}, settings={"auto_backup": True}
    )


@pytest.fixture
def sample_config_multiple_proxies():
    """包含多个代理的示例配置fixture"""
    proxy1 = ProxyServer(
        name="proxy-1",
        base_url="https://api1.example.com/",
        api_key="sk-proxy1123",
        description="第一个代理",
        tags=["primary", "test"],
        is_active=True,
    )
    
    proxy2 = ProxyServer(
        name="proxy-2",
        base_url="https://api2.example.com/",
        auth_token="sk-ant-proxy2456",
        description="第二个代理",
        tags=["secondary", "test"],
        is_active=True,
    )
    
    proxy3 = ProxyServer(
        name="proxy-3",
        base_url="https://api3.example.com/",
        api_key="sk-proxy3789",
        description="第三个代理",
        tags=["backup", "test"],
        is_active=False,
    )

    return ProxyConfig(
        current_proxy="proxy-1",
        proxies={
            "proxy-1": proxy1,
            "proxy-2": proxy2,
            "proxy-3": proxy3,
        },
        settings={
            "auto_backup": True,
            "max_backups": 5,
            "theme": "auto",
        }
    )


@pytest.fixture
def sample_export_formats():
    """示例导出格式fixture"""
    return {
        "bash": ExportFormat(shell_type="bash", include_comments=True),
        "fish": ExportFormat(shell_type="fish", include_comments=False),
        "powershell": ExportFormat(shell_type="powershell", prefix="CLAUDE_"),
        "custom": ExportFormat(
            shell_type="bash",
            include_comments=True,
            prefix="CUSTOM_",
            export_all=True
        ),
    }


@pytest.fixture
def temp_config_manager(temp_dir):
    """临时配置管理器fixture"""
    config_path = temp_dir / "test_config.toml"
    return ConfigManager(config_path=config_path)


@pytest.fixture
def temp_proxy_manager(temp_config_manager):
    """临时代理管理器fixture"""
    return ProxyManager(
        config_path=temp_config_manager.config_path,
        auto_backup=temp_config_manager.auto_backup,
        max_backups=temp_config_manager.max_backups
    )


@pytest.fixture
def temp_proxy_manager_with_backups(temp_dir):
    """带备份功能的临时代理管理器fixture"""
    config_path = temp_dir / "backup_config.toml"
    return ProxyManager(config_path=config_path, auto_backup=True, max_backups=3)


@pytest.fixture
def populated_proxy_manager(temp_dir, sample_config_multiple_proxies):
    """预填充代理的管理器fixture"""
    config_path = temp_dir / "populated_config.toml"
    manager = ProxyManager(config_path=config_path)
    
    # 添加示例配置中的所有代理
    for _, proxy in sample_config_multiple_proxies.proxies.items():
        manager.config.add_proxy(proxy)
    
    # 设置当前代理
    if sample_config_multiple_proxies.current_proxy:
        manager.config.set_current_proxy(sample_config_multiple_proxies.current_proxy)
    
    # 保存配置
    manager._save_config()
    
    return manager


@pytest.fixture(autouse=True)
def mock_claude_code_config_dir(temp_dir, monkeypatch):
    """自动mock所有ProxyManager的Claude Code配置目录，避免访问真实配置文件"""
    from unittest.mock import patch
    
    def mock_get_claude_code_config_dir(self):
        return temp_dir / ".claude"
    
    # 对所有ProxyManager实例自动应用mock
    with patch.object(ProxyManager, '_get_claude_code_config_dir', mock_get_claude_code_config_dir):
        yield


# 测试配置
def pytest_configure(config):
    """pytest配置"""
    # 添加自定义标记
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")


# 测试收集配置
def pytest_collection_modifyitems(config, items):
    """修改测试收集"""
    # 自动添加标记
    for item in items:
        # 为集成测试添加标记
        if "integration" in item.nodeid or "test_integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)

        # 为单元测试添加标记
        elif any(name in item.nodeid for name in ["test_models", "test_config", "test_manager"]):
            item.add_marker(pytest.mark.unit)

        # 为慢测试添加标记
        if "slow" in item.keywords or "backup" in item.nodeid:
            item.add_marker(pytest.mark.slow)


# 测试工具函数
def create_test_proxy(name="test-proxy", **kwargs):
    """创建测试代理的工厂函数"""
    defaults = {
        "name": name,
        "base_url": "https://api.example.com/",
        "api_key": "sk-1234567890abcdef",
        "description": "测试代理",
        "tags": ["test"],
    }
    defaults.update(kwargs)
    return ProxyServer(**defaults)


def create_test_config(proxy_count=2, current_index=0):
    """创建测试配置的工厂函数"""
    proxies = {}
    proxy_names = []

    for i in range(proxy_count):
        name = f"proxy-{i}"
        proxy = create_test_proxy(
            name=name, base_url=f"https://api{i}.example.com/", api_key=f"sk-{'1' * 10}{i}"
        )
        proxies[name] = proxy
        proxy_names.append(name)

    current_proxy = proxy_names[current_index] if proxy_names else None

    return ProxyConfig(current_proxy=current_proxy, proxies=proxies)
