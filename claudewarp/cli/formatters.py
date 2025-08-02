"""
CLI输出格式化模块

使用Rich库提供美观的命令行输出格式。
"""

from datetime import datetime
from typing import Dict, Optional

from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from ..core.models import ProxyServer
from ..util import _format_datetime, _mask_api_key


def format_proxy_table(
    proxies: Dict[str, ProxyServer], current_proxy: Optional[str] = None
) -> Table:
    """格式化代理列表为表格

    Args:
        proxies: 代理字典
        current_proxy: 当前代理名称

    Returns:
        Table: 格式化的表格
    """
    table = Table(title="代理服务列表", box=box.ROUNDED, show_header=True, header_style="bold blue")

    # 添加列
    table.add_column("状态", style="", width=6, justify="center")
    table.add_column("名称", style="bold")
    table.add_column("URL", style="dim")
    table.add_column("认证", style="yellow")
    table.add_column("描述", style="")
    table.add_column("标签", style="cyan")
    table.add_column("更新时间", style="dim")

    # 添加行
    for name, proxy in proxies.items():
        # 状态指示器
        if name == current_proxy:
            status = "[bold green]●[/bold green] [green]当前[/green]"
        elif proxy.is_active:
            status = "[green]●[/green] 启用"
        else:
            status = "[red]●[/red] 禁用"

        # 格式化URL（显示简短版本）
        url_display = proxy.base_url
        if len(url_display) > 30:
            url_display = url_display[:27] + "..."

        # 格式化认证方式
        auth_method = proxy.get_auth_method()
        if auth_method == "auth_token":
            auth_display = "[yellow]Token[/yellow]"
        elif auth_method == "api_key":
            auth_display = "[cyan]API Key[/cyan]"
        else:
            auth_display = "[red]None[/red]"

        # 格式化标签
        tags_display = ", ".join(proxy.tags) if proxy.tags else "-"
        if len(tags_display) > 20:
            tags_display = tags_display[:17] + "..."

        # 格式化时间
        try:
            update_time = datetime.fromisoformat(proxy.updated_at)
            time_display = update_time.strftime("%Y-%m-%d %H:%M")
        except Exception as e:
            print(f"Unexpected error: {e}")
            time_display = "-"

        # 名称样式
        name_style = "bold green" if name == current_proxy else ""

        table.add_row(
            status,
            f"[{name_style}]{name}[/{name_style}]" if name_style else name,
            url_display,
            auth_display,
            proxy.description or "-",
            tags_display,
            time_display,
        )

    return table


def format_proxy_info(proxy: ProxyServer, detailed: bool = True) -> Panel:
    """格式化代理详细信息

    Args:
        proxy: 代理服务器对象
        detailed: 是否显示详细信息

    Returns:
        Panel: 格式化的面板
    """
    # 基本信息
    info_lines = [
        f"[bold]名称:[/bold] {proxy.name}",
        f"[bold]URL:[/bold] {proxy.base_url}",
        f"[bold]状态:[/bold] {'[green]启用[/green]' if proxy.is_active else '[red]禁用[/red]'}",
    ]

    if proxy.description:
        info_lines.append(f"[bold]描述:[/bold] {proxy.description}")

    if proxy.tags:
        tags_text = ", ".join(f"[cyan]{tag}[/cyan]" for tag in proxy.tags)
        info_lines.append(f"[bold]标签:[/bold] {tags_text}")

    # 模型配置
    if proxy.bigmodel:
        info_lines.append(f"[bold]大模型:[/bold] [yellow]{proxy.bigmodel}[/yellow]")

    if proxy.smallmodel:
        info_lines.append(f"[bold]小模型:[/bold] [yellow]{proxy.smallmodel}[/yellow]")

    if detailed:
        # 认证信息
        auth_method = proxy.get_auth_method()
        if auth_method == "auth_token":
            info_lines.append("[bold]认证方式:[/bold] [yellow]Auth Token[/yellow]")
            info_lines.append(
                f"[bold]Auth令牌:[/bold] {_mask_api_key(proxy.auth_token or '******')}"
            )
        else:
            info_lines.append("[bold]认证方式:[/bold] [yellow]API Key[/yellow]")
            info_lines.append(f"[bold]API密钥:[/bold] {_mask_api_key(proxy.api_key)}")

        # 详细信息
        info_lines.extend(
            [
                f"[bold]创建时间:[/bold] {_format_datetime(proxy.created_at)}",
                f"[bold]更新时间:[/bold] {_format_datetime(proxy.updated_at)}",
            ]
        )

    content = Group(*info_lines)

    return Panel(
        content,
        title=f"[bold blue]{proxy.name}[/bold blue]",
        border_style="blue",
        padding=(1, 2),
        expand=False,
    )


def format_export_output(export_content: str, shell_type: str) -> Syntax:
    """格式化环境变量导出输出

    Args:
        export_content: 导出内容
        shell_type: Shell类型

    Returns:
        Syntax: 格式化的语法高亮文本
    """
    # 根据shell类型选择语法高亮
    syntax_map = {"bash": "bash", "fish": "fish", "powershell": "powershell", "zsh": "bash"}

    lexer = syntax_map.get(shell_type, "bash")

    syntax = Syntax(
        export_content, lexer, theme="default", line_numbers=False, background_color="default"
    )

    return syntax


def format_success(message: str) -> Text:
    """格式化成功消息

    Args:
        message: 消息内容

    Returns:
        Text: 格式化的文本
    """
    return Text.from_markup(f"[bold green]✓[/bold green] {message}")


# 导出所有格式化函数
__all__ = [
    "format_proxy_table",
    "format_proxy_info",
    "format_export_output",
    "format_success",
]
