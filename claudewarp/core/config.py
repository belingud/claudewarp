"""
配置文件管理器

负责处理TOML格式的配置文件读写、验证和管理。
支持跨平台路径处理、文件安全和备份恢复功能。
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import toml

from .exceptions import (
    ConfigError,
    ConfigFileCorruptedError,
    ConfigFileNotFoundError,
    ConfigPermissionError,
    SystemError,
    ValidationError,
)
from .models import ProxyConfig, ProxyServer
from .utils import (
    atomic_write,
    check_disk_space,
    check_file_permissions,
    create_backup,
    ensure_directory,
    get_config_directory,
    set_file_permissions,
)

# 配置文件版本，用于兼容性检查
CURRENT_CONFIG_VERSION = "1.0"

# 支持的配置文件版本列表
SUPPORTED_CONFIG_VERSIONS = ["1.0"]


class ConfigManager:
    """配置文件管理器

    负责处理配置文件的读取、写入、验证和备份。
    支持TOML格式，具有跨平台兼容性和安全性保障。
    """

    def __init__(
        self, config_path: Optional[Path] = None, auto_backup: bool = True, max_backups: int = 5
    ):
        """初始化配置管理器

        Args:
            config_path: 配置文件路径，为None时使用默认路径
            auto_backup: 是否自动备份
            max_backups: 最大备份数量
        """
        self.config_path = config_path or self._get_default_config_path()
        self.auto_backup = auto_backup
        self.max_backups = max_backups
        self.logger = logging.getLogger(__name__)

        # 确保配置目录存在
        self._ensure_config_environment()

    def _get_default_config_path(self) -> Path:
        """获取默认配置文件路径

        Returns:
            Path: 默认配置文件路径
        """
        config_dir = get_config_directory("claudewarp")
        return config_dir / "config.toml"

    def _ensure_config_environment(self) -> None:
        """确保配置环境正常

        创建必要的目录并设置适当的权限。

        Raises:
            ConfigPermissionError: 权限不足
            SystemError: 系统错误
        """
        try:
            # 确保配置目录存在
            config_dir = self.config_path.parent
            ensure_directory(config_dir, mode=0o700)

            # 如果配置文件存在，检查权限
            if self.config_path.exists():
                permissions = check_file_permissions(self.config_path)
                if not permissions["readable"]:
                    raise ConfigPermissionError(str(self.config_path), "读取")
                if not permissions["writable"]:
                    raise ConfigPermissionError(str(self.config_path), "写入")

            self.logger.debug(f"配置环境已准备: {config_dir}")

        except (OSError, PermissionError) as e:
            raise ConfigPermissionError(str(self.config_path), "初始化配置环境") from e

    def load_config(self) -> ProxyConfig:
        """加载配置文件

        Returns:
            ProxyConfig: 配置对象

        Raises:
            ConfigFileNotFoundError: 配置文件不存在
            ConfigFileCorruptedError: 配置文件损坏
            ConfigPermissionError: 权限不足
            ValidationError: 数据验证失败
        """
        if not self.config_path.exists():
            self.logger.info("配置文件不存在，创建默认配置")
            return self._create_default_config()

        try:
            self.logger.debug(f"加载配置文件: {self.config_path}")

            # 读取TOML文件
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = toml.load(f)

            # 验证配置版本
            self._validate_config_version(data)

            # 转换为ProxyConfig对象
            config = self._parse_config_data(data)

            self.logger.info(f"成功加载配置，包含 {len(config.proxies)} 个代理服务器")
            return config

        except toml.TomlDecodeError as e:
            self.logger.error(f"TOML格式错误: {e}")
            raise ConfigFileCorruptedError(str(self.config_path), str(e)) from None

        except (OSError, PermissionError) as e:
            self.logger.error(f"文件访问错误: {e}")
            raise ConfigPermissionError(str(self.config_path), "读取") from None

        except ValidationError:
            # 重新抛出验证错误
            raise

        except Exception as e:
            self.logger.error(f"配置加载失败: {e}")
            raise ConfigError(f"加载配置失败: {e}") from None

    def save_config(self, config: ProxyConfig) -> bool:
        """保存配置文件

        Args:
            config: 配置对象

        Returns:
            bool: 是否成功保存

        Raises:
            ValidationError: 配置验证失败
            ConfigPermissionError: 权限不足
            SystemError: 系统错误
        """
        try:
            # 验证配置
            self._validate_config(config)

            # 检查磁盘空间
            config_data = self._serialize_config(config)
            estimated_size = len(config_data.encode("utf-8")) * 2  # 预留空间
            check_disk_space(self.config_path.parent, estimated_size)

            # 创建备份
            if self.auto_backup and self.config_path.exists():
                backup_path = create_backup(self.config_path, max_backups=self.max_backups)
                if backup_path:
                    self.logger.debug(f"已创建备份: {backup_path}")

            # 原子性写入
            success = atomic_write(self.config_path, config_data, encoding="utf-8")

            if success:
                # 设置文件权限
                set_file_permissions(self.config_path, 0o600)
                self.logger.info(f"配置已保存: {self.config_path}")
                return True
            else:
                raise SystemError("写入配置文件失败")

        except ValidationError:
            # 重新抛出验证错误
            raise

        except (OSError, PermissionError) as e:
            self.logger.error(f"保存配置失败: {e}")
            raise ConfigPermissionError(str(self.config_path), "写入") from None

        except Exception as e:
            self.logger.error(f"保存配置失败: {e}")
            raise ConfigError(f"保存配置失败: {e}") from None

    def _create_default_config(self) -> ProxyConfig:
        """创建默认配置

        Returns:
            ProxyConfig: 默认配置对象
        """
        config = ProxyConfig(
            version=CURRENT_CONFIG_VERSION,
            current_proxy=None,
            proxies={},
            settings={
                "auto_backup": self.auto_backup,
                "max_backups": self.max_backups,
                "check_updates": True,
                "theme": "auto",
            },
        )

        # 保存默认配置
        self.save_config(config)
        self.logger.info("已创建默认配置文件")

        return config

    def _validate_config_version(self, data: Dict[str, Any]) -> None:
        """验证配置文件版本

        Args:
            data: 配置数据

        Raises:
            ValidationError: 版本不支持
        """
        version = data.get("version", "1.0")

        if version not in SUPPORTED_CONFIG_VERSIONS:
            raise ValidationError(
                f"不支持的配置文件版本: {version}。支持的版本: {', '.join(SUPPORTED_CONFIG_VERSIONS)}"
            )

    def _parse_config_data(self, data: Dict[str, Any]) -> ProxyConfig:
        """解析配置数据

        Args:
            data: 原始配置数据

        Returns:
            ProxyConfig: 配置对象

        Raises:
            ValidationError: 数据验证失败
        """
        try:
            # 处理代理服务器数据
            proxies = {}
            proxy_data = data.get("proxies", {})

            for name, proxy_info in proxy_data.items():
                # 确保proxy_info是字典类型
                if not isinstance(proxy_info, dict):
                    raise ValidationError(f"代理 '{name}' 的配置格式错误")

                # 确保名称一致
                proxy_info["name"] = name

                # 创建ProxyServer对象
                proxy = ProxyServer(**proxy_info)
                proxies[name] = proxy

            # 创建配置对象
            config = ProxyConfig(
                version=data.get("version", CURRENT_CONFIG_VERSION),
                current_proxy=data.get("current_proxy"),
                proxies=proxies,
                settings=data.get("settings", {}),
                created_at=data.get("created_at", datetime.now().isoformat()),
                updated_at=datetime.now().isoformat(),
            )

            return config

        except Exception as e:
            self.logger.error(f"解析配置数据失败: {e}")
            import traceback
            traceback.print_exc()
            raise ValidationError(f"配置数据格式错误: {e}") from None

    def _serialize_config(self, config: ProxyConfig) -> str:
        """序列化配置为TOML格式

        Args:
            config: 配置对象

        Returns:
            str: TOML格式的配置字符串
        """
        # 转换为字典格式
        data = {
            "version": config.version,
            "current_proxy": config.current_proxy,
            "created_at": config.created_at,
            "updated_at": config.updated_at,
            "settings": config.settings,
            "proxies": {},
        }

        # 转换代理服务器数据
        for name, proxy in config.proxies.items():
            data["proxies"][name] = proxy.dict()

        # 生成TOML字符串
        try:
            toml_content = toml.dumps(data)

            # 添加文件头注释
            header = f"""# Claude中转站管理工具配置文件
# 配置文件版本: {config.version}
# 最后更新: {config.updated_at}
# 警告: 请勿手动编辑此文件，除非您了解其格式

"""

            return header + toml_content

        except Exception as e:
            raise ConfigError(f"序列化配置失败: {e}") from None

    def _validate_config(self, config: ProxyConfig) -> None:
        """验证配置对象

        Args:
            config: 配置对象

        Raises:
            ValidationError: 验证失败
        """
        # 使用Pydantic的内置验证
        try:
            # 触发完整验证
            config.model_dump()
        except Exception as e:
            raise ValidationError(f"配置验证失败: {e}") from None

        # 额外的业务逻辑验证
        if config.current_proxy:
            if config.current_proxy not in config.proxies:
                raise ValidationError(f"当前代理 '{config.current_proxy}' 不存在于代理列表中")

    def get_backup_files(self) -> List[Path]:
        """获取备份文件列表

        Returns:
            List[Path]: 备份文件路径列表
        """
        backup_dir = self.config_path.parent / "backups"
        if not backup_dir.exists():
            return []

        pattern = f"{self.config_path.stem}_*.toml"
        backup_files = list(backup_dir.glob(pattern))

        # 按修改时间排序，最新的在前
        backup_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        return backup_files

    def restore_from_backup(self, backup_path: Path) -> bool:
        """从备份恢复配置

        Args:
            backup_path: 备份文件路径

        Returns:
            bool: 是否成功恢复

        Raises:
            ConfigFileNotFoundError: 备份文件不存在
            ConfigError: 恢复失败
        """
        if not backup_path.exists():
            raise ConfigFileNotFoundError(str(backup_path))

        try:
            # 验证备份文件
            # with open(backup_path, 'r', encoding='utf-8') as f:
            #     data = toml.load(f)

            # 解析为配置对象进行验证
            # config = self._parse_config_data(data)

            # 备份当前配置
            if self.config_path.exists():
                current_backup = create_backup(self.config_path)
                self.logger.info(f"已备份当前配置: {current_backup}")

            # 复制备份文件到配置路径
            import shutil

            shutil.copy2(backup_path, self.config_path)
            set_file_permissions(self.config_path, 0o600)

            self.logger.info(f"已从备份恢复配置: {backup_path}")
            return True

        except Exception as e:
            self.logger.error(f"从备份恢复失败: {e}")
            raise ConfigError(f"从备份恢复失败: {e}") from None

    def get_config_info(self) -> Dict[str, Any]:
        """获取配置文件信息

        Returns:
            Dict[str, Any]: 配置文件信息
        """
        info = {
            "config_path": str(self.config_path),
            "exists": self.config_path.exists(),
            "auto_backup": self.auto_backup,
            "max_backups": self.max_backups,
        }

        if self.config_path.exists():
            stat = self.config_path.stat()
            info.update(
                {
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "permissions": oct(stat.st_mode)[-3:],
                }
            )

            # 获取备份信息
            backups = self.get_backup_files()
            info["backup_count"] = len(backups)
            if backups:
                latest_backup = backups[0]
                info["latest_backup"] = {
                    "path": str(latest_backup),
                    "created": datetime.fromtimestamp(latest_backup.stat().st_mtime).isoformat(),
                }

        return info

    def cleanup_old_backups(self) -> int:
        """清理旧备份文件

        Returns:
            int: 清理的备份文件数量
        """
        backup_files = self.get_backup_files()

        if len(backup_files) <= self.max_backups:
            return 0

        # 删除超出数量限制的备份
        files_to_delete = backup_files[self.max_backups :]
        deleted_count = 0

        for backup_file in files_to_delete:
            try:
                backup_file.unlink()
                deleted_count += 1
                self.logger.debug(f"已删除旧备份: {backup_file}")
            except OSError as e:
                self.logger.warning(f"删除备份文件失败: {backup_file}, 错误: {e}")

        return deleted_count

    def migrate_config(self, target_version: str = CURRENT_CONFIG_VERSION) -> bool:
        """迁移配置文件到新版本

        Args:
            target_version: 目标版本

        Returns:
            bool: 是否需要迁移

        Raises:
            ConfigError: 迁移失败
        """
        if not self.config_path.exists():
            return False

        try:
            # 加载当前配置
            config = self.load_config()

            if config.version == target_version:
                return False  # 无需迁移

            self.logger.info(f"开始配置迁移: {config.version} -> {target_version}")

            # 创建迁移前备份
            backup_path = create_backup(self.config_path)
            self.logger.info(f"迁移前备份: {backup_path}")

            # 执行版本迁移
            migrated_config = self._perform_migration(config, target_version)

            # 保存迁移后的配置
            self.save_config(migrated_config)

            self.logger.info(f"配置迁移完成: {target_version}")
            return True

        except Exception as e:
            self.logger.error(f"配置迁移失败: {e}")
            raise ConfigError(f"配置迁移失败: {e}") from None

    def _perform_migration(self, config: ProxyConfig, target_version: str) -> ProxyConfig:
        """执行具体的迁移逻辑

        Args:
            config: 当前配置
            target_version: 目标版本

        Returns:
            ProxyConfig: 迁移后的配置
        """
        # 目前只有1.0版本，暂时直接返回
        # 未来版本迁移逻辑将在这里实现

        if target_version == "1.0":
            config.version = target_version
            return config

        raise ConfigError(f"不支持迁移到版本: {target_version}")


# 导出配置管理器类
__all__ = [
    "ConfigManager",
    "CURRENT_CONFIG_VERSION",
    "SUPPORTED_CONFIG_VERSIONS",
]
