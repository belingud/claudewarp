"""
核心数据模型

定义代理服务器和配置相关的数据模型，使用Pydantic进行数据验证。
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Self

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_core.core_schema import ValidationInfo

class ProxyServer(BaseModel):
    """代理服务器配置模型

    表示单个Claude API中转站的配置信息，包含名称、URL、API密钥等。
    """

    name: str = Field(
        ..., min_length=1, max_length=50, description="代理服务器名称，用于标识和选择"
    )
    base_url: str = Field(..., description="代理服务器的基础URL，必须是有效的HTTP/HTTPS地址")
    api_key: Optional[str] = Field(default=None, min_length=3, description="API密钥，用于身份验证")
    description: str = Field(default="", max_length=200, description="代理服务器的描述信息")
    tags: List[str] = Field(default_factory=list, description="标签列表，用于分类和筛选")
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(), description="创建时间，ISO格式"
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(), description="最后更新时间，ISO格式"
    )
    is_active: bool = Field(default=True, description="是否启用该代理服务器")
    bigmodel: Optional[str] = Field(default=None, description="大模型名称")
    smallmodel: Optional[str] = Field(default=None, description="小模型名称")
    auth_token: Optional[str] = Field(
        default=None, min_length=3, description="Auth令牌，用于身份验证（与api_key互斥）"
    )
    @field_validator("name")
    def validate_name(cls, v: str) -> str:
        """验证代理名称格式"""
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("代理名称只能包含字母、数字、下划线和横线")
        return v

    @field_validator("base_url")
    def validate_base_url(cls, v: str) -> str:
        """验证和规范化base_url"""
        # 检查URL格式
        if not re.match(r"^https?://", v):
            raise ValueError("Base URL必须以http://或https://开头")

        # 确保URL以/结尾
        if not v.endswith("/"):
            v += "/"

        # 基本URL格式验证
        url_pattern = re.compile(
            r"^https?://"  # http:// or https://
            r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain
            r"localhost|"  # localhost
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # IP
            r"(?::\d+)?"  # optional port
            r"(?:/?|[/?]\S+)$",
            re.IGNORECASE,
        )

        if not url_pattern.match(v):
            raise ValueError("Base URL格式无效")

        return v

    @field_validator("tags")
    def validate_tags(cls, v: List[str]) -> List[str]:
        """验证标签列表"""
        return list(set(i.strip() for i in v))

    @field_validator("updated_at")
    def update_timestamp(cls, v: str, values: dict) -> str:
        """自动更新时间戳"""
        return datetime.now().isoformat()
    
    @model_validator(mode="after")
    def api_key_or_auth_token(cls, values: Self) -> Self:
        """确保api_key或auth_token至少有一个"""
        if values.api_key and values.auth_token:
            raise ValueError("api_key或auth_token只能存在一个")
        if not values.api_key and not values.auth_token:
            raise ValueError("api_key或auth_token至少有一个必须存在")
        return values

    def get_auth_method(self) -> str:
        """获取当前使用的认证方法"""
        if self.auth_token:
            return "auth_token"
        elif self.api_key:
            return "api_key"
        else:
            return "none"

    def get_active_credential(self) -> Optional[str]:
        """获取当前活跃的认证凭据"""
        if self.auth_token:
            return self.auth_token
        elif self.api_key:
            return self.api_key
        return None

    class Config:
        """Pydantic配置"""

        # 允许字段别名
        validate_by_name = True
        # 验证赋值
        validate_assignment = True
        # JSON编码器配置
        json_encoders = {datetime: lambda v: v.isoformat()}

        # 模型示例
        json_schema_extra = {
            "example": {
                "name": "proxy-cn",
                "base_url": "https://api.claude-proxy.com/",
                "api_key": "sk-1234567890abcdef",
                "description": "国内主力节点",
                "tags": ["china", "primary"],
                "is_active": True,
            },
            "examples": [
                {
                    "name": "proxy-auth",
                    "base_url": "https://api.claude-proxy.com/",
                    "auth_token": "sk-ant-api03-abcdef123456",
                    "description": "使用Auth令牌的代理",
                    "tags": ["auth", "primary"],
                    "is_active": True,
                }
            ],
        }


class ProxyConfig(BaseModel):
    """代理配置文件模型

    表示整个应用程序的配置，包含所有代理服务器和全局设置。
    """

    version: str = Field(default="1.0", description="配置文件版本")
    current_proxy: Optional[str] = Field(default=None, description="当前活跃的代理服务器名称")
    proxies: Dict[str, ProxyServer] = Field(
        default_factory=dict, description="代理服务器字典，key为代理名称"
    )
    settings: Dict[str, Any] = Field(default_factory=dict, description="应用程序设置")
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(), description="配置创建时间"
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(), description="配置最后更新时间"
    )

    @field_validator("current_proxy")
    def validate_current_proxy(cls, v: Optional[str], values: ValidationInfo) -> Optional[str]:
        """验证当前代理是否存在于代理列表中"""
        if v is not None and "proxies" in values.data:
            proxies = values.data["proxies"]
            if v not in proxies:
                raise ValueError(f'当前代理 "{v}" 不存在于代理列表中')
        return v

    @field_validator("proxies")
    def validate_proxies(cls, v: Dict[str, ProxyServer]) -> Dict[str, ProxyServer]:
        """验证代理字典的一致性"""
        for name, proxy in v.items():
            if proxy.name != name:
                raise ValueError(
                    f'代理名称不一致: 字典key为"{name}", 但代理对象name为"{proxy.name}"'
                )
        return v

    @field_validator("updated_at")
    def update_timestamp(cls, v: str, values: dict) -> str:
        """自动更新时间戳"""
        return datetime.now().isoformat()

    def get_current_proxy(self) -> Optional[ProxyServer]:
        """获取当前活跃的代理服务器"""
        if self.current_proxy and self.current_proxy in self.proxies:
            return self.proxies[self.current_proxy]
        return None

    def add_proxy(self, proxy: ProxyServer) -> None:
        """添加代理服务器"""
        self.proxies[proxy.name] = proxy
        # 如果是第一个代理，设置为当前代理
        if len(self.proxies) == 1:
            self.current_proxy = proxy.name

    def remove_proxy(self, name: str) -> bool:
        """删除代理服务器"""
        if name not in self.proxies:
            return False

        del self.proxies[name]

        # 如果删除的是当前代理，切换到其他代理或清空
        if self.current_proxy == name:
            if self.proxies:
                self.current_proxy = next(iter(self.proxies))
            else:
                self.current_proxy = None

        return True

    def set_current_proxy(self, name: str) -> bool:
        """设置当前代理"""
        if name not in self.proxies:
            return False
        self.current_proxy = name
        return True

    def get_proxy_names(self) -> List[str]:
        """获取所有代理名称列表"""
        return list(self.proxies.keys())

    def get_active_proxies(self) -> Dict[str, ProxyServer]:
        """获取所有启用的代理服务器"""
        return {name: proxy for name, proxy in self.proxies.items() if proxy.is_active}

    class Config:
        """Pydantic配置"""

        validate_by_name = True
        validate_assignment = True
        json_encoders = {datetime: lambda v: v.isoformat()}

        json_schema_extra = {
            "example": {
                "version": "1.0",
                "current_proxy": "proxy-cn",
                "proxies": {
                    "proxy-cn": {
                        "name": "proxy-cn",
                        "base_url": "https://proxy-cn.example.com/",
                        "api_key": "sk-1234567890abcdef",
                        "description": "国内主力节点",
                        "tags": ["china", "primary"],
                    }
                },
                "settings": {"auto_backup": True, "backup_count": 5},
            }
        }


class ExportFormat(BaseModel):
    """环境变量导出格式配置

    定义如何导出环境变量的格式和选项。
    """

    shell_type: str = Field(default="bash", description="Shell类型: bash, fish, powershell")
    include_comments: bool = Field(default=True, description="是否包含注释")
    prefix: str = Field(default="ANTHROPIC_", description="环境变量前缀")
    export_all: bool = Field(default=False, description="是否导出所有代理（默认只导出当前代理）")

    @field_validator("shell_type")
    def validate_shell_type(cls, v: str) -> str:
        """验证Shell类型"""
        valid_shells = {"bash", "fish", "powershell", "zsh"}
        v = v.lower()
        if v not in valid_shells:
            raise ValueError(f"不支持的Shell类型: {v}. 支持的类型: {', '.join(valid_shells)}")
        return v

    @field_validator("prefix")
    def validate_prefix(cls, v: str) -> str:
        """验证环境变量前缀"""
        if not re.match(r"^[A-Z_][A-Z0-9_]*$", v):
            raise ValueError(
                "环境变量前缀必须以大写字母或下划线开头，只能包含大写字母、数字和下划线"
            )
        if not v.endswith("_"):
            v += "_"
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "shell_type": "bash",
                "include_comments": True,
                "prefix": "ANTHROPIC_",
                "export_all": False,
            }
        }


# 用于类型提示的导出
__all__ = ["ProxyServer", "ProxyConfig", "ExportFormat"]
