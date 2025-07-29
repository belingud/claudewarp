"""
CLI输出格式化模块

使用Rich库提供美观的命令行输出格式。
"""

from datetime import datetime
from typing import Any, Dict, Optional

from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from ..core.models import ProxyServer


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


def format_error(message: str) -> Text:
    """格式化错误消息

    Args:
        message: 错误消息

    Returns:
        Text: 格式化的文本
    """
    return Text.from_markup(f"[bold red]✗[/bold red] {message}")


def format_warning(message: str) -> Text:
    """格式化警告消息

    Args:
        message: 警告消息

    Returns:
        Text: 格式化的文本
    """
    return Text.from_markup(f"[bold yellow]⚠[/bold yellow] {message}")


def format_info(message: str) -> Text:
    """格式化信息消息

    Args:
        message: 信息消息

    Returns:
        Text: 格式化的文本
    """
    return Text.from_markup(f"[bold blue]ℹ[/bold blue] {message}")


def format_loading(message: str) -> Text:
    """格式化加载消息

    Args:
        message: 加载消息

    Returns:
        Text: 格式化的文本
    """
    return Text.from_markup(f"[bold cyan]⟳[/bold cyan] {message}")


def format_stats_table(stats: Dict[str, Any]) -> Table:
    """格式化统计信息表格

    Args:
        stats: 统计信息字典

    Returns:
        Table: 格式化的表格
    """
    table = Table(title="统计信息", box=box.ROUNDED, show_header=True, header_style="bold blue")

    table.add_column("项目", style="bold", min_width=15)
    table.add_column("值", style="", min_width=20)

    # 基本统计
    table.add_row("总代理数量", str(stats.get("total_proxies", 0)))
    table.add_row("活跃代理", f"[green]{stats.get('active_proxies', 0)}[/green]")
    table.add_row("未启用代理", f"[red]{stats.get('inactive_proxies', 0)}[/red]")
    table.add_row("当前代理", stats.get("current_proxy") or "[dim]未设置[/dim]")
    table.add_row("配置版本", stats.get("config_version", "unknown"))

    return table


def format_search_results(
    results: Dict[str, ProxyServer], query: str, current_proxy: Optional[str] = None
) -> Panel:
    """格式化搜索结果

    Args:
        results: 搜索结果
        query: 搜索关键词
        current_proxy: 当前代理名称

    Returns:
        Panel: 格式化的面板
    """
    if not results:
        content = f"[yellow]未找到匹配 '{query}' 的代理[/yellow]"
    else:
        table = format_proxy_table(results, current_proxy)
        content = table

    return Panel(content, title=f"[bold blue]搜索结果: '{query}'[/bold blue]", border_style="blue")


def format_progress_bar(current: int, total: int, description: str = "") -> str:
    """格式化进度条

    Args:
        current: 当前进度
        total: 总数
        description: 描述文本

    Returns:
        str: 格式化的进度条
    """
    if total == 0:
        return f"[dim]{description}[/dim]"

    percentage = current / total * 100
    bar_length = 20
    filled_length = int(bar_length * current // total)

    bar = "█" * filled_length + "░" * (bar_length - filled_length)

    return f"[bold blue]{description}[/bold blue] [{bar}] {percentage:.1f}% ({current}/{total})"


def _mask_api_key(api_key: str, show_chars: int = 4) -> str:
    """遮蔽API密钥

    Args:
        api_key: 原始API密钥
        show_chars: 显示的字符数

    Returns:
        str: 遮蔽后的API密钥
    """
    if len(api_key) <= show_chars * 2:
        return "*" * len(api_key)

    return f"{api_key[:show_chars]}{'*' * (len(api_key) - show_chars * 2)}{api_key[-show_chars:]}"


def _format_datetime(iso_string: str) -> str:
    """格式化日期时间

    Args:
        iso_string: ISO格式的日期时间字符串

    Returns:
        str: 格式化的日期时间
    """
    try:
        dt = datetime.fromisoformat(iso_string)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        print(f"Unexpected error: {e}")
        return iso_string


def create_banner(title: str, subtitle: str = "") -> Panel:
    """创建横幅

    Args:
        title: 主标题
        subtitle: 副标题

    Returns:
        Panel: 格式化的横幅
    """
    content = f"[bold blue]{title}[/bold blue]"
    if subtitle:
        content += f"\\n[dim]{subtitle}[/dim]"

    return Panel(content, border_style="blue", padding=(1, 2))


def create_help_table(commands: Dict[str, str]) -> Table:
    """创建帮助表格

    Args:
        commands: 命令字典 {命令: 描述}

    Returns:
        Table: 格式化的帮助表格
    """
    table = Table(title="可用命令", box=box.ROUNDED, show_header=True, header_style="bold blue")

    table.add_column("命令", style="bold cyan", min_width=15)
    table.add_column("描述", style="", min_width=30)

    for command, description in commands.items():
        table.add_row(command, description)

    return table


# 导出所有格式化函数
__all__ = [
    "format_proxy_table",
    "format_proxy_info",
    "format_export_output",
    "format_success",
    "format_error",
    "format_warning",
    "format_info",
    "format_loading",
    "format_stats_table",
    "format_search_results",
    "format_progress_bar",
    "create_banner",
    "create_help_table",
]
