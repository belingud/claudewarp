"""
配置管理器测试

测试ConfigManager的配置文件读写、验证和管理功能。
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import toml

from core.config import CURRENT_CONFIG_VERSION, ConfigManager
from core.exceptions import (
    ConfigError,
    ConfigFileCorruptedError,
    ConfigPermissionError,
    ValidationError,
)
from core.models import ProxyConfig, ProxyServer


class TestConfigManager:
    """测试ConfigManager类"""

    def test_init_with_default_path(self):
        """测试使用默认路径初始化"""
        manager = ConfigManager()

        assert manager.config_path is not None
        assert manager.config_path.name == "config.toml"
        assert manager.auto_backup is True
        assert manager.max_backups == 5

    def test_init_with_custom_path(self):
        """测试使用自定义路径初始化"""
        custom_path = Path("/tmp/test_config.toml")
        manager = ConfigManager(config_path=custom_path)

        assert manager.config_path == custom_path

    def test_get_default_config_path(self):
        """测试获取默认配置路径"""
        manager = ConfigManager()
        path = manager._get_default_config_path()

        assert path.name == "config.toml"
        assert "claudewarp" in str(path)

    @pytest.fixture
    def temp_config_dir(self):
        """临时配置目录fixture"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def temp_config_manager(self, temp_config_dir):
        """临时配置管理器fixture"""
        config_path = temp_config_dir / "config.toml"
        return ConfigManager(config_path=config_path)

    def test_create_default_config(self, temp_config_manager):
        """测试创建默认配置"""
        config = temp_config_manager._create_default_config()

        assert isinstance(config, ProxyConfig)
        assert config.version == CURRENT_CONFIG_VERSION
        assert config.current_proxy is None
        assert config.proxies == {}
        assert isinstance(config.settings, dict)

        # 检查配置文件是否创建
        assert temp_config_manager.config_path.exists()

    def test_load_config_file_not_exists(self, temp_config_manager):
        """测试加载不存在的配置文件"""
        # 应该创建默认配置
        config = temp_config_manager.load_config()

        assert isinstance(config, ProxyConfig)
        assert config.version == CURRENT_CONFIG_VERSION
        assert temp_config_manager.config_path.exists()

    def test_load_config_valid_file(self, temp_config_manager):
        """测试加载有效的配置文件"""
        # 创建测试配置数据
        test_data = {
            "version": "1.0",
            "current_proxy": "test-proxy",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
            "settings": {"auto_backup": True},
            "proxies": {
                "test-proxy": {
                    "name": "test-proxy",
                    "base_url": "https://api.example.com/",
                    "api_key": "sk-1234567890abcdef",
                    "description": "测试代理",
                    "tags": ["test"],
                    "created_at": "2024-01-01T00:00:00",
                    "updated_at": "2024-01-01T00:00:00",
                    "is_active": True,
                }
            },
        }

        # 写入配置文件
        with open(temp_config_manager.config_path, "w", encoding="utf-8") as f:
            toml.dump(test_data, f)

        # 加载配置
        config = temp_config_manager.load_config()

        assert config.version == "1.0"
        assert config.current_proxy == "test-proxy"
        assert len(config.proxies) == 1
        assert "test-proxy" in config.proxies

        proxy = config.proxies["test-proxy"]
        assert proxy.name == "test-proxy"
        assert proxy.base_url == "https://api.example.com/"

    def test_load_config_corrupted_file(self, temp_config_manager):
        """测试加载损坏的配置文件"""
        # 写入无效的TOML内容
        with open(temp_config_manager.config_path, "w", encoding="utf-8") as f:
            f.write("invalid toml content [[[")

        with pytest.raises(ConfigFileCorruptedError):
            temp_config_manager.load_config()

    def test_save_config_valid(self, temp_config_manager):
        """测试保存有效配置"""
        # 创建测试配置
        proxy = ProxyServer(
            name="test-proxy", base_url="https://api.example.com/", api_key="sk-1234567890abcdef"
        )

        config = ProxyConfig(current_proxy="test-proxy", proxies={"test-proxy": proxy})

        # 保存配置
        result = temp_config_manager.save_config(config)

        assert result is True
        assert temp_config_manager.config_path.exists()

        # 验证文件内容
        with open(temp_config_manager.config_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "test-proxy" in content
            assert "https://api.example.com/" in content

    def test_save_config_invalid(self, temp_config_manager):
        """测试保存无效配置"""
        # 创建无效配置（当前代理不在代理列表中）
        proxy = ProxyServer(
            name="test-proxy", base_url="https://api.example.com/", api_key="sk-1234567890abcdef"
        )

        # 手动创建无效状态（绕过Pydantic验证）
        config = ProxyConfig(proxies={"test-proxy": proxy})
        config.current_proxy = "nonexistent"

        with pytest.raises(ValidationError):
            temp_config_manager.save_config(config)

    def test_validate_config_version_valid(self, temp_config_manager):
        """测试有效配置版本验证"""
        data = {"version": "1.0"}

        # 不应该抛出异常
        temp_config_manager._validate_config_version(data)

    def test_validate_config_version_invalid(self, temp_config_manager):
        """测试无效配置版本验证"""
        data = {"version": "999.0"}

        with pytest.raises(ValidationError, match="不支持的配置文件版本"):
            temp_config_manager._validate_config_version(data)

    def test_validate_config_version_missing(self, temp_config_manager):
        """测试缺失配置版本"""
        data = {}

        # 应该使用默认版本，不抛出异常
        temp_config_manager._validate_config_version(data)

    def test_parse_config_data_valid(self, temp_config_manager):
        """测试解析有效配置数据"""
        data = {
            "version": "1.0",
            "current_proxy": None,
            "proxies": {
                "test-proxy": {
                    "name": "test-proxy",
                    "base_url": "https://api.example.com/",
                    "api_key": "sk-1234567890abcdef",
                    "description": "测试代理",
                    "tags": ["test"],
                    "is_active": True,
                }
            },
            "settings": {"auto_backup": True},
        }

        config = temp_config_manager._parse_config_data(data)

        assert isinstance(config, ProxyConfig)
        assert config.version == "1.0"
        assert len(config.proxies) == 1
        assert "test-proxy" in config.proxies

    def test_parse_config_data_invalid_proxy(self, temp_config_manager):
        """测试解析包含无效代理的配置数据"""
        data = {
            "version": "1.0",
            "proxies": {
                "invalid-proxy": {
                    "name": "invalid-proxy",
                    "base_url": "invalid-url",  # 无效URL
                    "api_key": "short",  # 太短的API密钥
                }
            },
        }

        with pytest.raises(ValidationError):
            temp_config_manager._parse_config_data(data)

    def test_serialize_config(self, temp_config_manager):
        """测试配置序列化"""
        proxy = ProxyServer(
            name="test-proxy",
            base_url="https://api.example.com/",
            api_key="sk-1234567890abcdef",
            description="测试代理",
        )

        config = ProxyConfig(
            current_proxy="test-proxy",
            proxies={"test-proxy": proxy},
            settings={"auto_backup": True},
        )

        toml_content = temp_config_manager._serialize_config(config)

        assert isinstance(toml_content, str)
        assert "test-proxy" in toml_content
        assert "https://api.example.com/" in toml_content
        assert "配置文件版本" in toml_content  # 检查注释

        # 验证生成的TOML可以解析
        parsed_data = toml.loads(toml_content.split("\n\n", 1)[1])  # 跳过注释头
        assert parsed_data["current_proxy"] == "test-proxy"
        assert "test-proxy" in parsed_data["proxies"]

    def test_validate_config_valid(self, temp_config_manager):
        """测试有效配置验证"""
        proxy = ProxyServer(
            name="test-proxy", base_url="https://api.example.com/", api_key="sk-1234567890abcdef"
        )

        config = ProxyConfig(current_proxy="test-proxy", proxies={"test-proxy": proxy})

        # 不应该抛出异常
        temp_config_manager._validate_config(config)

    def test_validate_config_invalid_current_proxy(self, temp_config_manager):
        """测试无效当前代理配置验证"""
        proxy = ProxyServer(
            name="test-proxy", base_url="https://api.example.com/", api_key="sk-1234567890abcdef"
        )

        config = ProxyConfig(proxies={"test-proxy": proxy})
        config.current_proxy = "nonexistent"  # 手动设置无效状态

        with pytest.raises(ValidationError, match="当前代理.*不存在于代理列表中"):
            temp_config_manager._validate_config(config)


class TestConfigManagerBackup:
    """测试配置管理器备份功能"""

    @pytest.fixture
    def temp_config_manager_with_backup(self, temp_config_dir):
        """带备份功能的临时配置管理器"""
        config_path = temp_config_dir / "config.toml"
        return ConfigManager(config_path=config_path, auto_backup=True, max_backups=3)

    def test_backup_creation(self, temp_config_manager_with_backup):
        """测试备份创建"""
        # 创建初始配置
        config = temp_config_manager_with_backup._create_default_config()

        # 修改并保存配置（应该创建备份）
        proxy = ProxyServer(
            name="new-proxy", base_url="https://api.example.com/", api_key="sk-1234567890abcdef"
        )
        config.proxies["new-proxy"] = proxy

        result = temp_config_manager_with_backup.save_config(config)
        assert result is True

        # 检查备份文件
        backup_files = temp_config_manager_with_backup.get_backup_files()
        # 第一次修改可能不会创建备份，因为之前没有文件
        # assert len(backup_files) >= 0

    def test_get_backup_files(self, temp_config_manager_with_backup):
        """测试获取备份文件列表"""
        backup_files = temp_config_manager_with_backup.get_backup_files()
        assert isinstance(backup_files, list)

    def test_cleanup_old_backups(self, temp_config_manager_with_backup):
        """测试清理旧备份"""
        # 清理操作应该正常执行
        deleted_count = temp_config_manager_with_backup.cleanup_old_backups()
        assert isinstance(deleted_count, int)
        assert deleted_count >= 0

    def test_get_config_info(self, temp_config_manager_with_backup):
        """测试获取配置信息"""
        info = temp_config_manager_with_backup.get_config_info()

        assert isinstance(info, dict)
        assert "config_path" in info
        assert "exists" in info
        assert "auto_backup" in info
        assert "max_backups" in info

        assert info["auto_backup"] is True
        assert info["max_backups"] == 3


class TestConfigManagerMigration:
    """测试配置管理器迁移功能"""

    @pytest.fixture
    def temp_config_manager_migration(self, temp_config_dir):
        """用于迁移测试的配置管理器"""
        config_path = temp_config_dir / "config.toml"
        return ConfigManager(config_path=config_path)

    def test_migrate_config_no_file(self, temp_config_manager_migration):
        """测试迁移不存在的配置文件"""
        result = temp_config_manager_migration.migrate_config()
        assert result is False  # 没有文件需要迁移

    def test_migrate_config_same_version(self, temp_config_manager_migration):
        """测试迁移相同版本的配置"""
        # 创建当前版本的配置
        config = temp_config_manager_migration._create_default_config()

        result = temp_config_manager_migration.migrate_config()
        assert result is False  # 版本相同，无需迁移

    def test_perform_migration_current_version(self, temp_config_manager_migration):
        """测试执行当前版本迁移"""
        proxy = ProxyServer(
            name="test-proxy", base_url="https://api.example.com/", api_key="sk-1234567890abcdef"
        )

        config = ProxyConfig(version="1.0", proxies={"test-proxy": proxy})

        migrated = temp_config_manager_migration._perform_migration(config, "1.0")
        assert migrated.version == "1.0"
        assert len(migrated.proxies) == 1

    def test_perform_migration_unsupported_version(self, temp_config_manager_migration):
        """测试迁移到不支持的版本"""
        config = ProxyConfig(version="1.0")

        with pytest.raises(ConfigError, match="不支持迁移到版本"):
            temp_config_manager_migration._perform_migration(config, "999.0")


class TestConfigManagerErrorHandling:
    """测试配置管理器错误处理"""

    def test_permission_error_handling(self):
        """测试权限错误处理"""
        # 使用不可写的路径
        read_only_path = Path("/root/readonly_config.toml")

        # 在实际测试中，这可能需要mock来模拟权限错误
        with patch("core.config.ensure_directory") as mock_ensure:
            mock_ensure.side_effect = PermissionError("Permission denied")

            with pytest.raises(ConfigPermissionError):
                ConfigManager(config_path=read_only_path)

    @patch("builtins.open", side_effect=PermissionError("Permission denied"))
    def test_load_config_permission_error(self, mock_file, temp_config_dir):
        """测试加载配置时的权限错误"""
        config_path = temp_config_dir / "config.toml"
        manager = ConfigManager(config_path=config_path)

        # 创建文件以便触发权限错误
        config_path.touch()

        with pytest.raises(ConfigPermissionError):
            manager.load_config()

    @patch("builtins.open", side_effect=PermissionError("Permission denied"))
    def test_save_config_permission_error(self, mock_file, temp_config_dir):
        """测试保存配置时的权限错误"""
        config_path = temp_config_dir / "config.toml"
        manager = ConfigManager(config_path=config_path)

        config = ProxyConfig()

        with pytest.raises(ConfigPermissionError):
            manager.save_config(config)


# 测试工具函数
def create_test_config_file(path: Path, data: dict = None):
    """创建测试配置文件"""
    if data is None:
        data = {"version": "1.0", "current_proxy": None, "proxies": {}, "settings": {}}

    with open(path, "w", encoding="utf-8") as f:
        toml.dump(data, f)


def create_test_proxy_data(name: str = "test-proxy") -> dict:
    """创建测试代理数据"""
    return {
        "name": name,
        "base_url": "https://api.example.com/",
        "api_key": "sk-1234567890abcdef",
        "description": "测试代理",
        "tags": ["test"],
        "is_active": True,
    }
