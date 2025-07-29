"""
代理服务器管理器

提供中转站的增删改查、切换和导出功能。
负责协调ConfigManager、数据模型和异常处理。
"""

import logging
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import ConfigManager
from .exceptions import (
    ConfigError,
    DuplicateProxyError,
    ExportError,
    OperationError,
    ProxyNotFoundError,
    ValidationError,
)
from .models import ExportFormat, ProxyConfig, ProxyServer


class ProxyManager:
    """代理服务器管理器

    提供统一的代理服务器管理接口，包括添加、删除、切换、查询和导出功能。
    与ConfigManager集成，使用现有的数据模型和异常体系。
    """

    def __init__(
        self, config_path: Optional[Path] = None, auto_backup: bool = True, max_backups: int = 5
    ):
        """初始化代理管理器

        Args:
            config_path: 配置文件路径，为None时使用默认路径
            auto_backup: 是否自动备份配置文件
            max_backups: 最大备份数量
        """
        self.config_manager = ConfigManager(
            config_path=config_path, auto_backup=auto_backup, max_backups=max_backups
        )
        self.logger = logging.getLogger(__name__)

        # 加载配置
        self._config = None
        self._load_config()

    @property
    def config(self) -> ProxyConfig:
        if self._config is None:
            self._load_config()
        return self._config  # type: ignore

    def _load_config(self) -> ProxyConfig:
        """加载配置文件

        Raises:
            ConfigError: 配置加载失败
        """
        try:
            self._config = self.config_manager.load_config()
            self.logger.debug(f"已加载配置，包含 {len(self._config.proxies)} 个代理服务器")
            return self._config
        except Exception as e:
            self.logger.error(f"加载配置失败: {e}")
            raise ConfigError(f"初始化代理管理器失败: {e}") from None

    def _save_config(self) -> None:
        """保存配置文件

        Raises:
            ConfigError: 配置保存失败
        """
        try:
            success = self.config_manager.save_config(self.config)
            if not success:
                raise ConfigError("保存配置文件失败")
            self.logger.debug("配置已保存")
        except Exception as e:
            self.logger.error(f"保存配置失败: {e}")
            raise ConfigError(f"保存配置失败: {e}") from None

    def add_proxy(
        self,
        name: str,
        base_url: str,
        api_key: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        is_active: bool = True,
        set_as_current: bool = False,
        bigmodel: Optional[str] = None,
        smallmodel: Optional[str] = None,
        auth_token: Optional[str] = None,
    ) -> ProxyServer:
        """添加新的代理服务器

        Args:
            name: 代理服务器名称
            base_url: 代理服务器URL
            api_key: API密钥
            description: 描述信息
            tags: 标签列表
            is_active: 是否启用
            set_as_current: 是否设置为当前代理
            bigmodel: 大模型名称
            smallmodel: 小模型名称
            auth_token: Auth令牌（与api_key互斥）

        Returns:
            ProxyServer: 添加的代理服务器对象

        Raises:
            DuplicateProxyError: 代理服务器已存在
            ValidationError: 数据验证失败
            ConfigError: 配置操作失败
        """
        # 检查重复
        if name in self.config.proxies:
            raise DuplicateProxyError(name)

        try:
            # 创建代理服务器对象（会自动进行数据验证）
            proxy = ProxyServer(
                name=name,
                base_url=base_url,
                api_key=api_key,
                description=description,
                tags=tags or [],
                is_active=is_active,
                bigmodel=bigmodel,
                smallmodel=smallmodel,
                auth_token=auth_token,
            )

            # 添加到配置
            self.config.add_proxy(proxy)

            # 如果需要设置为当前代理
            if set_as_current:
                self.config.set_current_proxy(name)

            # 保存配置
            self._save_config()

            self.logger.info(f"已添加代理服务器: {name}")
            return proxy

        except ValueError as e:
            # Pydantic验证错误
            raise ValidationError(f"代理服务器数据验证失败: {e}") from None
        except Exception as e:
            self.logger.error(f"添加代理服务器失败: {e}")
            raise OperationError(
                f"添加代理服务器失败: {e}", operation="add_proxy", target=name
            ) from None

    def remove_proxy(self, name: str) -> bool:
        """删除代理服务器

        Args:
            name: 代理服务器名称

        Returns:
            bool: 是否成功删除

        Raises:
            ProxyNotFoundError: 代理服务器不存在
            ConfigError: 配置操作失败
        """
        if name not in self.config.proxies:
            raise ProxyNotFoundError(name)

        try:
            # 删除代理
            success = self.config.remove_proxy(name)

            if success:
                # 保存配置
                self._save_config()
                self.logger.info(f"已删除代理服务器: {name}")
                return True
            else:
                raise OperationError("删除代理服务器失败", operation="remove_proxy", target=name)

        except Exception as e:
            self.logger.error(f"删除代理服务器失败: {e}")
            raise ConfigError(f"删除代理服务器失败: {e}") from None

    def switch_proxy(self, name: str) -> ProxyServer:
        """切换当前代理服务器

        Args:
            name: 代理服务器名称

        Returns:
            ProxyServer: 切换后的当前代理服务器

        Raises:
            ProxyNotFoundError: 代理服务器不存在
            ValidationError: 代理服务器未启用
            ConfigError: 配置操作失败
        """
        if name not in self.config.proxies:
            raise ProxyNotFoundError(name)

        proxy = self.config.proxies[name]

        # 检查代理是否启用
        if not proxy.is_active:
            raise ValidationError(f"代理服务器 '{name}' 未启用，无法切换")

        try:
            # 设置当前代理
            success = self.config.set_current_proxy(name)

            if success:
                # 保存配置
                self._save_config()
                self.logger.info(f"已切换到代理服务器: {name}")

                # 自动应用到 Claude Code
                try:
                    self.apply_claude_code_setting(name)
                    self.logger.info(f"已自动应用代理 '{name}' 到 Claude Code")
                except Exception as e:
                    self.logger.warning(f"应用代理到 Claude Code 失败: {e}")
                    # 不影响代理切换的主要功能，只记录警告

                return proxy
            else:
                raise OperationError("切换代理服务器失败", operation="switch_proxy", target=name)

        except Exception as e:
            self.logger.error(f"切换代理服务器失败: {e}")
            raise ConfigError(f"切换代理服务器失败: {e}") from None

    def get_current_proxy(self) -> Optional[ProxyServer]:
        """获取当前代理服务器

        Returns:
            Optional[ProxyServer]: 当前代理服务器，如果没有则返回None
        """
        return self.config.get_current_proxy()

    def get_proxy(self, name: str) -> ProxyServer:
        """获取指定的代理服务器

        Args:
            name: 代理服务器名称

        Returns:
            ProxyServer: 代理服务器对象

        Raises:
            ProxyNotFoundError: 代理服务器不存在
        """
        if name not in self.config.proxies:
            raise ProxyNotFoundError(name)

        return self.config.proxies[name]

    def list_proxies(self, active_only: bool = False) -> Dict[str, ProxyServer]:
        """获取代理服务器列表

        Args:
            active_only: 是否只返回启用的代理服务器

        Returns:
            Dict[str, ProxyServer]: 代理服务器字典
        """
        if active_only:
            return self.config.get_active_proxies()
        else:
            return self.config.proxies.copy()

    def get_proxy_names(self, active_only: bool = False) -> List[str]:
        """获取代理服务器名称列表

        Args:
            active_only: 是否只返回启用的代理服务器名称

        Returns:
            List[str]: 代理服务器名称列表
        """
        if active_only:
            return list(self.config.get_active_proxies().keys())
        else:
            return self.config.get_proxy_names()

    def update_proxy(
        self,
        name: str,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        is_active: Optional[bool] = None,
        bigmodel: Optional[str] = None,
        smallmodel: Optional[str] = None,
        auth_token: Optional[str] = None,
    ) -> ProxyServer:
        """更新代理服务器信息

        Args:
            name: 代理服务器名称
            base_url: 新的URL（可选）
            api_key: 新的API密钥（可选）
            description: 新的描述（可选）
            tags: 新的标签列表（可选）
            is_active: 新的启用状态（可选）
            bigmodel: 新的大模型名称（可选）
            smallmodel: 新的小模型名称（可选）
            auth_token: 新的Auth令牌（可选，与api_key互斥）

        Returns:
            ProxyServer: 更新后的代理服务器对象

        Raises:
            ProxyNotFoundError: 代理服务器不存在
            ValidationError: 数据验证失败
            ConfigError: 配置操作失败
        """
        if name not in self.config.proxies:
            raise ProxyNotFoundError(name)

        try:
            proxy = self.config.proxies[name]

            # 准备更新数据
            update_data = {
                "name": name,
                "base_url": base_url if base_url is not None else proxy.base_url,
                "description": description if description is not None else proxy.description,
                "tags": tags if tags is not None else proxy.tags,
                "is_active": is_active if is_active is not None else proxy.is_active,
                "bigmodel": bigmodel if bigmodel is not None else proxy.bigmodel,
                "smallmodel": smallmodel if smallmodel is not None else proxy.smallmodel,
                "created_at": proxy.created_at,  # 保持原创建时间
            }

            # 处理互斥的认证方式
            if auth_token is not None:
                # 如果设置了auth_token，则清空api_key
                update_data["auth_token"] = auth_token
                update_data["api_key"] = None
            elif api_key is not None:
                # 如果设置了api_key，则清空auth_token
                update_data["api_key"] = api_key
                update_data["auth_token"] = None
            else:
                # 保持原来的认证方式
                update_data["api_key"] = proxy.api_key
                update_data["auth_token"] = proxy.auth_token

            # 创建新的代理对象（会自动进行数据验证和更新时间戳）
            updated_proxy = ProxyServer(**update_data)

            # 更新配置
            self.config.proxies[name] = updated_proxy

            # 如果代理被禁用且是当前代理，需要切换到其他代理
            if is_active is False and self.config.current_proxy == name:
                active_proxies = self.config.get_active_proxies()
                if active_proxies:
                    # 切换到第一个可用的代理
                    new_current = next(iter(active_proxies))
                    self.config.set_current_proxy(new_current)
                    self.logger.info(f"代理 '{name}' 被禁用，已自动切换到 '{new_current}'")
                else:
                    # 没有可用代理，清空当前代理
                    self.config.current_proxy = None
                    self.logger.warning(f"代理 '{name}' 被禁用且无其他可用代理")

            # 保存配置
            self._save_config()

            self.logger.info(f"已更新代理服务器: {name}")
            return updated_proxy

        except ValueError as e:
            # Pydantic验证错误
            raise ValidationError(f"代理服务器数据验证失败: {e}") from None
        except Exception as e:
            self.logger.error(f"更新代理服务器失败: {e}")
            raise ConfigError(f"更新代理服务器失败: {e}") from None

    def export_environment(
        self, export_format: Optional[ExportFormat] = None, proxy_name: Optional[str] = None
    ) -> str:
        """导出环境变量

        Args:
            export_format: 导出格式配置，为None时使用默认格式
            proxy_name: 指定代理名称，为None时使用当前代理

        Returns:
            str: 环境变量导出字符串

        Raises:
            ProxyNotFoundError: 指定的代理服务器不存在
            ExportError: 导出失败
        """
        # 使用默认导出格式
        if export_format is None:
            export_format = ExportFormat()

        try:
            # 确定要导出的代理
            if proxy_name:
                # 使用指定的代理
                if proxy_name not in self.config.proxies:
                    raise ProxyNotFoundError(proxy_name)
                proxy = self.config.proxies[proxy_name]
            else:
                # 使用当前代理
                proxy = self.get_current_proxy()
                if proxy is None:
                    raise ExportError("没有当前代理可供导出", export_format.shell_type)

            # 生成导出内容
            export_content = self._generate_export_content(proxy, export_format)

            self.logger.debug(f"已生成 {export_format.shell_type} 格式的环境变量导出")
            return export_content

        except Exception as e:
            self.logger.error(f"导出环境变量失败: {e}")
            if isinstance(e, (ProxyNotFoundError, ExportError)):
                raise
            else:
                raise ExportError(
                    f"导出环境变量失败: {e}",
                    export_format.shell_type if export_format else "unknown",
                ) from None

    def _generate_export_content(self, proxy: ProxyServer, export_format: ExportFormat) -> str:
        """生成环境变量导出内容

        Args:
            proxy: 代理服务器对象
            export_format: 导出格式配置

        Returns:
            str: 环境变量导出字符串
        """
        lines = []

        # 添加注释（如果启用）
        if export_format.include_comments:
            comment_char = "#" if export_format.shell_type != "powershell" else "#"
            lines.append(f"{comment_char} Claude 中转站环境变量")
            lines.append(f"{comment_char} 代理名称: {proxy.name}")
            lines.append(f"{comment_char} 代理URL: {proxy.base_url}")
            lines.append(f"{comment_char} 认证方式: {proxy.get_auth_method()}")
            if proxy.description:
                lines.append(f"{comment_char} 描述: {proxy.description}")
            lines.append("")

        # 生成环境变量
        base_url_var = f"{export_format.prefix}API_BASE_URL"

        # 根据认证方式选择要导出的凭据
        auth_method = proxy.get_auth_method()
        if auth_method == "auth_token":
            auth_var = f"{export_format.prefix}AUTH_TOKEN"
            auth_value = proxy.auth_token
        else:
            auth_var = f"{export_format.prefix}API_KEY"
            auth_value = proxy.api_key

        if export_format.shell_type == "powershell":
            # PowerShell格式
            lines.append(f'$env:{base_url_var} = "{proxy.base_url}"')
            lines.append(f'$env:{auth_var} = "{auth_value}"')
        elif export_format.shell_type == "fish":
            # Fish shell格式
            lines.append(f'set -gx {base_url_var} "{proxy.base_url}"')
            lines.append(f'set -gx {auth_var} "{auth_value}"')
        else:
            # Bash/Zsh格式（默认）
            lines.append(f'export {base_url_var}="{proxy.base_url}"')
            lines.append(f'export {auth_var}="{auth_value}"')

        # 如果需要导出所有代理
        if export_format.export_all and len(self.config.proxies) > 1:
            lines.append("")
            if export_format.include_comments:
                comment_char = "#" if export_format.shell_type != "powershell" else "#"
                lines.append(f"{comment_char} 所有可用代理")

            for name, p in self.config.proxies.items():
                if name != proxy.name:  # 跳过当前代理
                    safe_name = name.upper().replace("-", "_").replace(".", "_")
                    url_var = f"{export_format.prefix}{safe_name}_API_BASE_URL"

                    # 根据认证方式选择要导出的凭据
                    p_auth_method = p.get_auth_method()
                    if p_auth_method == "auth_token":
                        p_auth_var = f"{export_format.prefix}{safe_name}_AUTH_TOKEN"
                        p_auth_value = p.auth_token
                    else:
                        p_auth_var = f"{export_format.prefix}{safe_name}_API_KEY"
                        p_auth_value = p.api_key

                    if export_format.shell_type == "powershell":
                        lines.append(f'$env:{url_var} = "{p.base_url}"')
                        lines.append(f'$env:{p_auth_var} = "{p_auth_value}"')
                    elif export_format.shell_type == "fish":
                        lines.append(f'set -gx {url_var} "{p.base_url}"')
                        lines.append(f'set -gx {p_auth_var} = "{p_auth_value}"')
                    else:
                        lines.append(f'export {url_var}="{p.base_url}"')
                        lines.append(f'export {p_auth_var}="{p_auth_value}"')

        return "\n".join(lines)

    def get_status(self) -> Dict[str, Any]:
        """获取管理器状态信息

        Returns:
            Dict[str, Any]: 状态信息字典
        """
        current_proxy = self.get_current_proxy()
        active_proxies = self.config.get_active_proxies()

        return {
            "total_proxies": len(self.config.proxies),
            "active_proxies": len(active_proxies),
            "current_proxy": current_proxy.name if current_proxy else None,
            "config_version": self.config.version,
            "config_updated_at": self.config.updated_at,
            "config_info": self.config_manager.get_config_info(),
        }

    def validate_proxy_connection(self, name: str) -> Dict[str, Any]:
        """验证代理服务器连接（占位方法）

        Args:
            name: 代理服务器名称

        Returns:
            Dict[str, Any]: 验证结果

        Raises:
            ProxyNotFoundError: 代理服务器不存在

        Note:
            这是一个占位方法，具体的连接测试需要在后续版本中实现
        """
        if name not in self.config.proxies:
            raise ProxyNotFoundError(name)

        proxy = self.config.proxies[name]

        # TODO: 实现真实的连接测试
        return {
            "proxy_name": name,
            "status": "unknown",
            "message": "连接测试功能尚未实现",
            "base_url": proxy.base_url,
            "timestamp": proxy.updated_at,
        }

    def search_proxies(
        self, query: str, search_fields: Optional[List[str]] = None
    ) -> Dict[str, ProxyServer]:
        """搜索代理服务器

        Args:
            query: 搜索关键词
            search_fields: 搜索字段列表，默认搜索名称、描述和标签

        Returns:
            Dict[str, ProxyServer]: 匹配的代理服务器字典
        """
        if search_fields is None:
            search_fields = ["name", "description", "tags"]

        query = query.lower()
        results = {}

        for name, proxy in self.config.proxies.items():
            match = False

            # 搜索名称
            if "name" in search_fields and query in proxy.name.lower():
                match = True

            # 搜索描述
            if "description" in search_fields and query in proxy.description.lower():
                match = True

            # 搜索标签
            if "tags" in search_fields:
                for tag in proxy.tags:
                    if query in tag.lower():
                        match = True
                        break

            # 搜索URL
            if "base_url" in search_fields and query in proxy.base_url.lower():
                match = True

            if match:
                results[name] = proxy

        return results

    def get_proxies_by_tag(self, tag: str) -> Dict[str, ProxyServer]:
        """根据标签获取代理服务器

        Args:
            tag: 标签名称

        Returns:
            Dict[str, ProxyServer]: 包含指定标签的代理服务器字典
        """
        results = {}
        tag = tag.lower()

        for name, proxy in self.config.proxies.items():
            if any(tag in t.lower() for t in proxy.tags):
                results[name] = proxy

        return results

    def apply_claude_code_setting(self, proxy_name: Optional[str] = None) -> bool:
        """应用代理配置到 Claude Code

        Args:
            proxy_name: 指定代理名称，为None时使用当前代理

        Returns:
            bool: 是否成功应用配置

        Raises:
            ProxyNotFoundError: 指定的代理服务器不存在
            ConfigError: 配置操作失败
        """
        try:
            # 确定要应用的代理
            if proxy_name:
                if proxy_name not in self.config.proxies:
                    raise ProxyNotFoundError(proxy_name)
                proxy = self.config.proxies[proxy_name]
            else:
                proxy = self.get_current_proxy()
                if proxy is None:
                    raise ConfigError("没有当前代理可供应用")

            # 获取 Claude Code 配置目录 (~/.claude)
            claude_config_dir = self._get_claude_code_config_dir()

            # 确保目录存在
            from .utils import ensure_directory

            ensure_directory(claude_config_dir)

            # 配置文件路径
            setting_file = claude_config_dir / "settings.json"
            backup_file = claude_config_dir / "settings.json.claudewarp.bak"

            # 读取现有配置或创建新配置
            existing_config = {}
            if setting_file.exists():
                try:
                    with open(setting_file, "r", encoding="utf-8") as f:
                        existing_config = json.load(f)
                    self.logger.debug(f"已读取现有配置文件: {setting_file}")
                except (json.JSONDecodeError, Exception) as e:
                    self.logger.warning(f"读取现有配置文件失败，将创建新配置: {e}")
                    existing_config = {}

            # 备份现有配置（仅首次）
            if setting_file.exists() and not backup_file.exists():
                from .utils import safe_copy_file

                safe_copy_file(setting_file, backup_file, backup=False)
                self.logger.info(f"已备份现有 Claude Code 配置到: {backup_file}")

            # 合并配置
            merged_config = self._merge_claude_code_config(existing_config, proxy)

            from .utils import atomic_write

            config_json = json.dumps(merged_config, indent=2, ensure_ascii=False)

            if atomic_write(setting_file, config_json):
                self.logger.info(f"已应用代理 '{proxy.name}' 到 Claude Code: {setting_file}")
                return True
            else:
                raise ConfigError("写入 Claude Code 配置文件失败")

        except Exception as e:
            self.logger.error(f"应用 Claude Code 配置失败: {e}")
            if isinstance(e, (ProxyNotFoundError, ConfigError)):
                raise
            else:
                raise ConfigError(f"应用 Claude Code 配置失败: {e}") from None

    def _get_claude_code_config_dir(self) -> Path:
        """获取 Claude Code 配置目录

        Returns:
            Path: Claude Code 配置目录路径 (~/.claude)
        """
        from .utils import get_home_directory

        home_dir = get_home_directory()
        # Linux/macOS: ~/.claude
        return home_dir / ".claude"

    def _merge_claude_code_config(
        self, existing_config: Dict[str, Any], proxy: ProxyServer
    ) -> Dict[str, Any]:
        """合并现有配置和代理配置

        Args:
            existing_config: 现有的配置字典
            proxy: 代理服务器对象

        Returns:
            Dict[str, Any]: 合并后的配置字典
        """
        # 深拷贝现有配置作为基础
        import copy

        merged_config = copy.deepcopy(existing_config)

        # 确保 env 字段存在
        if "env" not in merged_config:
            merged_config["env"] = {}

        # 根据认证方式选择要设置的环境变量
        auth_method = proxy.get_auth_method()

        # 清除可能存在的认证环境变量，确保互斥性
        merged_config["env"].pop("ANTHROPIC_API_KEY", None)
        merged_config["env"].pop("ANTHROPIC_AUTH_TOKEN", None)

        # 设置对应的认证环境变量
        if auth_method == "auth_token":
            merged_config["env"]["ANTHROPIC_AUTH_TOKEN"] = proxy.auth_token
        else:
            merged_config["env"]["ANTHROPIC_API_KEY"] = proxy.api_key

        # 设置基础URL
        merged_config["env"]["ANTHROPIC_BASE_URL"] = proxy.base_url
        merged_config["env"]["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = 1

        # 如果配置了大模型，添加 ANTHROPIC_MODEL 环境变量
        if proxy.bigmodel:
            merged_config["env"]["ANTHROPIC_MODEL"] = proxy.bigmodel
        else:
            merged_config["env"].pop("ANTHROPIC_MODEL", None)

        # 如果配置了小模型，添加 ANTHROPIC_SMALL_FAST_MODEL 环境变量
        if proxy.smallmodel:
            merged_config["env"]["ANTHROPIC_SMALL_FAST_MODEL"] = proxy.smallmodel
        else:
            merged_config["env"].pop("ANTHROPIC_SMALL_FAST_MODEL", None)

        # 如果原配置中没有 permissions 字段，添加默认值
        if "permissions" not in merged_config:
            merged_config["permissions"] = {"allow": [], "deny": []}

        return merged_config

    def _generate_claude_code_config(self, proxy: ProxyServer) -> Dict[str, Any]:
        """生成 Claude Code 配置

        Args:
            proxy: 代理服务器对象

        Returns:
            Dict[str, Any]: Claude Code 配置字典
        """
        # 根据认证方式选择要设置的环境变量
        auth_method = proxy.get_auth_method()

        if auth_method == "auth_token":
            env_config = {
                "ANTHROPIC_AUTH_TOKEN": proxy.auth_token,
                "ANTHROPIC_BASE_URL": proxy.base_url,
                "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": 1,
            }
        else:
            env_config = {
                "ANTHROPIC_API_KEY": proxy.api_key,
                "ANTHROPIC_BASE_URL": proxy.base_url,
                "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": 1,
            }

        # 如果配置了大模型，添加 ANTHROPIC_MODEL 环境变量
        if proxy.bigmodel:
            env_config["ANTHROPIC_MODEL"] = proxy.bigmodel

        # 如果配置了小模型，添加 ANTHROPIC_SMALL_FAST_MODEL 环境变量
        if proxy.smallmodel:
            env_config["ANTHROPIC_SMALL_FAST_MODEL"] = proxy.smallmodel

        return {
            "env": env_config,
            "permissions": {"allow": [], "deny": []},
        }

    def reload_config(self) -> None:
        """重新加载配置文件

        Raises:
            ConfigError: 配置加载失败
        """
        self.logger.info("重新加载配置文件")
        self._load_config()


# 导出管理器类
__all__ = ["ProxyManager"]
