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

from core.config import ConfigManager
from core.manager import ProxyManager

# 导入需要的模块
from core.models import ProxyConfig, ProxyServer


@pytest.fixture(scope="session")
def temp_dir():
    """会话级临时目录"""
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
def temp_config_manager(temp_dir):
    """临时配置管理器fixture"""
    config_path = temp_dir / "test_config.toml"
    return ConfigManager(config_path=config_path)


@pytest.fixture
def temp_proxy_manager(temp_config_manager):
    """临时代理管理器fixture"""
    return ProxyManager(config_manager=temp_config_manager)


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
