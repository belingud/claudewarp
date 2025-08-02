"""
配置管理器测试
测试 ConfigManager 的配置文件读写、验证、备份和恢复功能
"""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
import toml

from claudewarp.core.config import ConfigManager, CURRENT_CONFIG_VERSION, SUPPORTED_CONFIG_VERSIONS
from claudewarp.core.exceptions import (
    ConfigError,
    ConfigFileCorruptedError,
    ConfigFileNotFoundError,
    ConfigPermissionError,
    ValidationError,
)
from claudewarp.core.models import ProxyConfig
from pydantic import ValidationError as PydanticValidationError


class TestConfigManager:
    """ConfigManager 基础功能测试"""

    def test_init_with_default_path(self):
        """测试使用默认路径初始化"""
        manager = ConfigManager()
        
        assert manager.config_path is not None
        assert manager.config_path.name == "config.toml"
        assert manager.auto_backup is True
        assert manager.max_backups == 5

    def test_init_with_custom_path(self, temp_dir):
        """测试使用自定义路径初始化"""
        custom_path = temp_dir / "custom_config.toml"
        manager = ConfigManager(config_path=custom_path, auto_backup=False, max_backups=10)
        
        assert manager.config_path == custom_path
        assert manager.auto_backup is False
        assert manager.max_backups == 10

    def test_config_environment_setup(self, temp_dir):
        """测试配置环境设置"""
        config_path = temp_dir / "subdir" / "config.toml"
        ConfigManager(config_path=config_path)
        
        # 应该自动创建父目录
        assert config_path.parent.exists()
        assert config_path.parent.is_dir()

    def test_get_default_config_path(self):
        """测试获取默认配置路径"""
        manager = ConfigManager()
        default_path = manager._get_default_config_path()
        
        assert default_path.name == "config.toml"
        assert "claudewarp" in str(default_path)


class TestConfigLoadingSaving:
    """配置加载和保存测试"""

    def test_load_nonexistent_config_creates_default(self, temp_config_manager):
        """测试加载不存在的配置文件时创建默认配置"""
        config = temp_config_manager.load_config()
        
        assert isinstance(config, ProxyConfig)
        assert config.version == CURRENT_CONFIG_VERSION
        assert config.current_proxy is None
        assert config.proxies == {}
        assert config.settings["auto_backup"] is True

        # 配置文件应该被创建
        assert temp_config_manager.config_path.exists()

    def test_save_and_load_config(self, temp_config_manager, sample_config):
        """测试保存和加载配置"""
        # 保存配置
        success = temp_config_manager.save_config(sample_config)
        assert success is True
        assert temp_config_manager.config_path.exists()

        # 加载配置
        loaded_config = temp_config_manager.load_config()
        
        assert loaded_config.version == sample_config.version
        assert loaded_config.current_proxy == sample_config.current_proxy
        assert len(loaded_config.proxies) == len(sample_config.proxies)
        assert "test-proxy" in loaded_config.proxies

    def test_save_config_with_validation_error(self, temp_config_manager):
        """测试保存无效配置时的错误处理"""
        # 由于current_proxy验证已改为model validator，在创建对象时就会验证
        # 测试在创建ProxyConfig时就抛出ValidationError
        with pytest.raises(PydanticValidationError, match="当前代理"):
            ProxyConfig(
                current_proxy="nonexistent",
                proxies={}
            )

    def test_load_corrupted_config_file(self, temp_config_manager):
        """测试加载损坏的配置文件"""
        # 创建损坏的TOML文件
        with open(temp_config_manager.config_path, "w", encoding="utf-8") as f:
            f.write("invalid toml [[[")
        
        with pytest.raises(ConfigFileCorruptedError):
            temp_config_manager.load_config()

    def test_config_file_format(self, temp_config_manager, sample_config):
        """测试配置文件格式"""
        temp_config_manager.save_config(sample_config)
        
        # 读取生成的TOML文件
        with open(temp_config_manager.config_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 验证文件头注释
        assert "Claude中转站管理工具配置文件" in content
        assert f"配置文件版本: {sample_config.version}" in content
        
        # 验证TOML格式
        data = toml.loads(content)
        assert "version" in data
        assert "proxies" in data
        assert "settings" in data

    def test_config_serialization_and_parsing(self, temp_config_manager, sample_proxy):
        """测试配置序列化和解析"""
        # 创建包含复杂数据的配置
        config = ProxyConfig(
            current_proxy="test-proxy",
            proxies={"test-proxy": sample_proxy},
            settings={
                "auto_backup": True,
                "max_backups": 10,
                "theme": "dark",
                "nested": {"key": "value"}
            }
        )
        
        # 保存和加载
        temp_config_manager.save_config(config)
        loaded_config = temp_config_manager.load_config()
        
        # 验证所有字段
        assert loaded_config.current_proxy == config.current_proxy
        assert loaded_config.settings["auto_backup"] == config.settings["auto_backup"]
        assert loaded_config.settings["nested"]["key"] == config.settings["nested"]["key"]
        
        # 验证代理对象
        loaded_proxy = loaded_config.proxies["test-proxy"]
        assert loaded_proxy.name == sample_proxy.name
        assert loaded_proxy.base_url == sample_proxy.base_url
        assert loaded_proxy.api_key == sample_proxy.api_key


class TestConfigValidation:
    """配置验证测试"""

    def test_validate_config_version_valid(self, temp_config_manager):
        """测试有效配置版本验证"""
        for version in SUPPORTED_CONFIG_VERSIONS:
            data = {"version": version}
            # 不应该抛出异常
            temp_config_manager._validate_config_version(data)

    def test_validate_config_version_invalid(self, temp_config_manager):
        """测试无效配置版本验证"""
        data = {"version": "999.0"}
        
        with pytest.raises(ValidationError, match="不支持的配置文件版本"):
            temp_config_manager._validate_config_version(data)

    def test_validate_config_version_missing(self, temp_config_manager):
        """测试缺少版本信息时的默认处理"""
        data = {}  # 没有版本信息
        
        # 应该使用默认版本，不抛出异常
        temp_config_manager._validate_config_version(data)

    def test_parse_config_data_with_invalid_proxy(self, temp_config_manager):
        """测试解析包含无效代理的配置数据"""
        data = {
            "version": "1.0",
            "proxies": {
                "invalid-proxy": {
                    "name": "invalid-proxy",
                    "base_url": "invalid-url",  # 无效URL
                    "api_key": "sk-test"
                }
            }
        }
        
        with pytest.raises(ValidationError):
            temp_config_manager._parse_config_data(data)

    def test_parse_config_data_with_proxy_name_mismatch(self, temp_config_manager):
        """测试解析代理名称不匹配的配置数据"""
        data = {
            "version": "1.0",
            "proxies": {
                "dict-key": {
                    "name": "different-name",  # 与字典key不同
                    "base_url": "https://api.example.com",
                    "api_key": "sk-test"
                }
            }
        }
        
        # parse_config_data 会自动修正名称不匹配的问题
        config = temp_config_manager._parse_config_data(data)
        assert "dict-key" in config.proxies
        assert config.proxies["dict-key"].name == "dict-key"

    def test_validate_config_object(self, temp_config_manager, sample_config):
        """测试配置对象验证"""
        # 有效配置
        temp_config_manager._validate_config(sample_config)
        
        # 无效配置：由于current_proxy验证已改为model validator，在创建对象时就会验证
        # 测试在创建ProxyConfig时就抛出ValidationError
        with pytest.raises(PydanticValidationError, match="当前代理"):
            ProxyConfig(
                current_proxy="nonexistent",
                proxies={"test-proxy": sample_config.proxies["test-proxy"]}
            )


class TestConfigBackupRestore:
    """配置备份和恢复测试"""

    def test_automatic_backup_creation(self, temp_config_manager, sample_config):
        """测试自动备份创建"""
        # 先保存一个配置
        temp_config_manager.save_config(sample_config)
        
        # 修改配置并再次保存，应该创建备份
        sample_config.settings["new_setting"] = "test_value"
        temp_config_manager.save_config(sample_config)
        
        # 检查备份文件
        backups = temp_config_manager.get_backup_files()
        assert len(backups) >= 1

    def test_backup_creation_disabled(self, temp_dir):
        """测试禁用自动备份"""
        config_path = temp_dir / "config.toml"
        manager = ConfigManager(config_path=config_path, auto_backup=False)
        
        # 保存配置
        config = ProxyConfig()
        manager.save_config(config)
        
        # 再次保存，不应该创建备份
        config.settings["test"] = "value"
        manager.save_config(config)
        
        backups = manager.get_backup_files()
        assert len(backups) == 0

    def test_get_backup_files(self, temp_config_manager):
        """测试获取备份文件列表"""
        # 清理现有备份文件
        backup_dir = temp_config_manager.config_path.parent / "backups"
        if backup_dir.exists():
            import shutil
            shutil.rmtree(backup_dir)
        
        # 创建一些备份文件
        backup_dir.mkdir(exist_ok=True)
        
        backup_files = []
        config_stem = temp_config_manager.config_path.stem  # 获取正确的文件名前缀
        for i in range(3):
            backup_file = backup_dir / f"{config_stem}_{i}.toml"
            backup_file.write_text(f"# Backup {i}")
            backup_files.append(backup_file)
        
        # 获取备份列表
        backups = temp_config_manager.get_backup_files()
        assert len(backups) == 3

    def test_restore_from_backup_success(self, temp_config_manager, sample_config):
        """测试成功从备份恢复"""
        # 保存原始配置
        temp_config_manager.save_config(sample_config)
        
        # 修改并保存（创建备份）
        sample_config.settings["modified"] = True
        temp_config_manager.save_config(sample_config)
        
        # 获取备份文件
        backups = temp_config_manager.get_backup_files()
        assert len(backups) > 0
        
        # 从备份恢复
        success = temp_config_manager.restore_from_backup(backups[0])
        assert success is True
        
        # 验证恢复结果
        restored_config = temp_config_manager.load_config()
        assert "modified" not in restored_config.settings

    def test_restore_from_nonexistent_backup(self, temp_config_manager):
        """测试从不存在的备份文件恢复"""
        nonexistent_backup = Path("/nonexistent/backup.toml")
        
        with pytest.raises(ConfigFileNotFoundError):
            temp_config_manager.restore_from_backup(nonexistent_backup)

    def test_cleanup_old_backups(self, temp_config_manager):
        """测试清理旧备份"""
        # 设置最大备份数为2
        temp_config_manager.max_backups = 2
        
        # 创建多个备份文件
        backup_dir = temp_config_manager.config_path.parent / "backups"
        backup_dir.mkdir(exist_ok=True)
        
        for i in range(5):
            backup_file = backup_dir / f"{temp_config_manager.config_path.stem}_{i:02d}.toml"
            backup_file.write_text(f"# Backup {i}")
        
        # 清理旧备份
        deleted_count = temp_config_manager.cleanup_old_backups()
        
        # 应该删除3个文件（保留最新的2个）
        assert deleted_count == 3
        
        # 验证剩余备份数量
        remaining_backups = temp_config_manager.get_backup_files()
        assert len(remaining_backups) == 2


class TestConfigMigration:
    """配置迁移测试"""

    def test_migrate_config_no_migration_needed(self, temp_config_manager, sample_config):
        """测试不需要迁移的情况"""
        sample_config.version = CURRENT_CONFIG_VERSION
        temp_config_manager.save_config(sample_config)
        
        result = temp_config_manager.migrate_config()
        assert result is False  # 不需要迁移

    def test_migrate_config_nonexistent_file(self, temp_config_manager):
        """测试迁移不存在的配置文件"""
        result = temp_config_manager.migrate_config()
        assert result is False

    def test_perform_migration_same_version(self, temp_config_manager, sample_config):
        """测试相同版本的迁移"""
        migrated = temp_config_manager._perform_migration(sample_config, "1.0")
        assert migrated.version == "1.0"
        assert migrated == sample_config

    def test_perform_migration_unsupported_version(self, temp_config_manager, sample_config):
        """测试不支持版本的迁移"""
        with pytest.raises(ConfigError, match="不支持迁移到版本"):
            temp_config_manager._perform_migration(sample_config, "999.0")


class TestConfigManagerInfo:
    """配置管理器信息测试"""

    def test_get_config_info_file_exists(self, temp_config_manager, sample_config):
        """测试获取存在文件的配置信息"""
        temp_config_manager.save_config(sample_config)
        
        info = temp_config_manager.get_config_info()
        
        assert info["config_path"] == str(temp_config_manager.config_path)
        assert info["exists"] is True
        assert info["auto_backup"] == temp_config_manager.auto_backup
        assert info["max_backups"] == temp_config_manager.max_backups
        assert "size" in info
        assert "modified" in info
        assert "permissions" in info

    def test_get_config_info_file_not_exists(self, temp_config_manager):
        """测试获取不存在文件的配置信息"""
        info = temp_config_manager.get_config_info()
        
        assert info["config_path"] == str(temp_config_manager.config_path)
        assert info["exists"] is False
        assert info["auto_backup"] == temp_config_manager.auto_backup
        assert info["max_backups"] == temp_config_manager.max_backups
        assert "backup_count" not in info  # 文件不存在时没有备份信息

    def test_get_config_info_with_backups(self, temp_config_manager, sample_config):
        """测试包含备份信息的配置信息"""
        # 保存配置并创建备份
        temp_config_manager.save_config(sample_config)
        sample_config.settings["test"] = "value"
        temp_config_manager.save_config(sample_config)
        
        info = temp_config_manager.get_config_info()
        
        assert "backup_count" in info
        assert info["backup_count"] >= 1
        if info["backup_count"] > 0:
            assert "latest_backup" in info


class TestConfigManagerErrorHandling:
    """配置管理器错误处理测试"""

    @patch('claudewarp.core.config.check_disk_space')
    def test_disk_space_error_handling(self, mock_check_disk_space, temp_config_manager, sample_config):
        """测试磁盘空间不足错误处理"""
        from claudewarp.core.exceptions import DiskSpaceError
        
        # 模拟磁盘空间不足
        mock_check_disk_space.side_effect = DiskSpaceError("/tmp", 1000000)
        
        with pytest.raises(DiskSpaceError):
            temp_config_manager.save_config(sample_config)

    def test_file_lock_error_handling(self, temp_config_manager):
        """测试文件锁定错误处理"""
        # 创建一个被锁定的文件（通过打开文件句柄）
        with open(temp_config_manager.config_path, "w") as f:
            f.write("locked")
            # 在Windows上，这会创建一个文件锁
            
            if os.name == "nt":  # Windows
                config = ProxyConfig()
                # 这可能会导致权限错误
                try:
                    temp_config_manager.save_config(config)
                except ConfigPermissionError:
                    pass  # 预期的错误

    def test_invalid_toml_content(self, temp_config_manager):
        """测试无效TOML内容处理"""
        # 写入无效的TOML内容
        with open(temp_config_manager.config_path, "w", encoding="utf-8") as f:
            f.write('invalid = toml [ content')
        
        with pytest.raises(ConfigFileCorruptedError) as exc_info:
            temp_config_manager.load_config()
        
        assert "配置文件格式错误" in str(exc_info.value)

    def test_json_content_in_toml_file(self, temp_config_manager):
        """测试在TOML文件中写入JSON内容"""
        # 写入JSON内容到TOML文件
        with open(temp_config_manager.config_path, "w", encoding="utf-8") as f:
            json.dump({"version": "1.0", "proxies": {}}, f)
        
        with pytest.raises(ConfigFileCorruptedError):
            temp_config_manager.load_config()

    @patch('claudewarp.core.config.toml.dumps')
    def test_serialization_error_handling(self, mock_toml_dumps, temp_config_manager, sample_config):
        """测试序列化错误处理"""
        # 模拟TOML序列化失败
        mock_toml_dumps.side_effect = Exception("Serialization failed")
        
        with pytest.raises(ConfigError, match="序列化配置失败"):
            temp_config_manager.save_config(sample_config)


class TestConfigManagerEdgeCases:
    """配置管理器边界情况测试"""

    def test_config_with_empty_proxies(self, temp_config_manager):
        """测试空代理列表的配置"""
        config = ProxyConfig(proxies={})
        
        temp_config_manager.save_config(config)
        loaded_config = temp_config_manager.load_config()
        
        assert loaded_config.proxies == {}
        assert loaded_config.current_proxy is None

    def test_config_with_large_settings(self, temp_config_manager):
        """测试包含大量设置的配置"""
        large_settings = {f"setting_{i}": f"value_{i}" for i in range(1000)}
        config = ProxyConfig(settings=large_settings)
        
        temp_config_manager.save_config(config)
        loaded_config = temp_config_manager.load_config()
        
        assert len(loaded_config.settings) == 1000
        assert loaded_config.settings["setting_500"] == "value_500"

    def test_config_path_with_unicode(self, temp_dir):
        """测试包含Unicode字符的配置路径"""
        config_path = temp_dir / "测试配置_🚀.toml"
        manager = ConfigManager(config_path=config_path)
        
        config = ProxyConfig()
        manager.save_config(config)
        
        assert config_path.exists()
        loaded_config = manager.load_config()
        assert isinstance(loaded_config, ProxyConfig)

    def test_concurrent_access_simulation(self, temp_config_manager, sample_config):
        """测试模拟并发访问"""
        import threading
        
        results = []
        
        def save_config():
            try:
                config = ProxyConfig(settings={"thread_id": threading.current_thread().ident})
                temp_config_manager.save_config(config)
                results.append("success")
            except Exception as e:
                results.append(f"error: {e}")
        
        # 创建多个线程同时保存配置
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=save_config)
            threads.append(thread)
        
        # 启动所有线程
        for thread in threads:
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 至少应该有一些成功的操作
        success_count = sum(1 for r in results if r == "success")
        assert success_count > 0