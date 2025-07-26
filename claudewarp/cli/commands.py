"""
CLI命令处理模块

使用Typer实现所有命令行命令的处理逻辑。
"""

import logging
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.prompt import Confirm, Prompt

from claudewarp.cli.formatters import (
    format_export_output,
    format_proxy_info,
    format_proxy_table,
    format_success,
)
from claudewarp.core.exceptions import (
    ClaudeWarpError,
    DuplicateProxyError,
    ProxyNotFoundError,
    ValidationError,
)
from claudewarp.core.manager import ProxyManager
from claudewarp.core.models import ExportFormat, ProxyServer

# 创建控制台对象
console = Console()

# 创建日志器
logger = logging.getLogger(__name__)

# 创建Typer应用
app = typer.Typer(
    name="claudewarp",
    help="Claude中转站管理工具 - 管理和切换Claude API代理服务器",
    no_args_is_help=True,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
)


def get_proxy_manager() -> ProxyManager:
    """获取代理管理器实例"""
    try:
        logger.debug("初始化代理管理器")
        return ProxyManager()
    except Exception as e:
        logger.error(f"代理管理器初始化失败: {e}")
        raise typer.Exit(1) from None


def _update_proxy_with_rename(
    manager: ProxyManager, old_name: str, new_name: str, update_kwargs: dict
) -> None:
    """处理代理重命名的更新逻辑

    Args:
        manager: 代理管理器实例
        old_name: 原始代理名称
        new_name: 新的代理名称
        update_kwargs: 要更新的其他字段
    """
    # 获取原始代理信息
    old_proxy = manager.get_proxy(old_name)

    # 检查是否为当前代理
    current_proxy = manager.get_current_proxy()
    was_current = current_proxy and current_proxy.name == old_name

    # 准备新代理的数据，使用原始数据作为默认值
    proxy_data = {
        "name": new_name,
        "base_url": update_kwargs.get("base_url", old_proxy.base_url),
        "api_key": update_kwargs.get("api_key", old_proxy.api_key),
        "description": update_kwargs.get("description", old_proxy.description),
        "tags": update_kwargs.get("tags", old_proxy.tags),
        "is_active": update_kwargs.get("is_active", old_proxy.is_active),
    }

    # 删除旧代理
    manager.remove_proxy(old_name)

    # 添加新代理
    manager.add_proxy(
        name=proxy_data["name"],
        base_url=proxy_data["base_url"],
        api_key=proxy_data["api_key"],
        description=proxy_data["description"],
        tags=proxy_data["tags"],
        is_active=proxy_data["is_active"],
    )

    # 如果原代理是当前代理，切换到新名称
    if was_current:
        manager.switch_proxy(new_name)


@app.command()
def add(
    name: Optional[str] = typer.Option(None, "--name", "-n", help="代理名称"),
    url: Optional[str] = typer.Option(None, "--url", "-u", help="代理服务器URL"),
    key: Optional[str] = typer.Option(None, "--key", "-k", help="API密钥"),
    description: Optional[str] = typer.Option("", "--desc", "-d", help="描述信息"),
    tags: Optional[str] = typer.Option(None, "--tags", "-t", help="标签列表，用逗号分隔"),
    interactive: bool = typer.Option(True, "--interactive/--no-interactive", help="交互式输入"),
):
    """添加新的代理服务器"""

    try:
        manager = get_proxy_manager()

        # 交互式输入
        if interactive:
            console.print("[bold blue]添加新的代理服务器[/bold blue]")
            console.print()

            if name is None:
                name = typer.prompt("代理名称")

            if url is None:
                url = typer.prompt("代理服务器URL")

            if key is None:
                key = typer.prompt("API密钥", hide_input=True)

            if not description:
                description = typer.prompt("描述信息", default="")

            if tags is None:
                tags_input = typer.prompt("标签 (用逗号分隔)", default="")
                tags_list = (
                    [tag.strip() for tag in tags_input.split(",") if tag.strip()]
                    if tags_input
                    else []
                )
            else:
                tags_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        else:
            # 非交互式模式，检查必需参数
            if not name:
                logger.error("代理名称是必需的")
                raise typer.Exit(1)
            if not url:
                logger.error("代理服务器URL是必需的")
                raise typer.Exit(1)
            if not key:
                logger.error("API密钥是必需的")
                raise typer.Exit(1)

            tags_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else []

        # 创建代理对象
        proxy = ProxyServer(
            name=name, base_url=url, api_key=key, description=description, tags=tags_list
        )

        # 添加代理
        logger.info(f"添加代理: {name}")
        manager.add_proxy(
            name=proxy.name,
            base_url=proxy.base_url,
            api_key=proxy.api_key,
            description=proxy.description,
            tags=proxy.tags,
            is_active=proxy.is_active,
        )

        console.print(format_success(f"代理 '{name}' 添加成功"))
        logger.info(f"代理 '{name}' 添加成功")

        # 显示代理信息
        console.print()
        console.print(format_proxy_info(proxy))

    except (DuplicateProxyError, ValidationError) as e:
        logger.error(f"代理添加失败: {e}")
        raise typer.Exit(1) from None
    except ClaudeWarpError as e:
        logger.error(f"操作失败: {e}")
        raise typer.Exit(1) from None
    except Exception as e:
        logger.error(f"未知错误: {e}")
        raise typer.Exit(1) from None


@app.command()
def list(
    format: str = typer.Option("table", "--format", "-f", help="输出格式: table, json, simple"),
    search: Optional[str] = typer.Option(None, "--search", "-s", help="搜索关键词"),
):
    """列出所有代理服务器"""

    try:
        manager = get_proxy_manager()

        # 获取代理列表
        if search:
            proxies = manager.search_proxies(search)
            if not proxies:
                logger.warning(f"未找到匹配 '{search}' 的代理")
                return
        else:
            proxies = manager.list_proxies()

        if not proxies:
            logger.warning("暂无代理服务器配置")
            return

        # 获取当前代理
        current_proxy = manager.get_current_proxy()
        current_name = current_proxy.name if current_proxy else None

        # 格式化输出
        if format == "table":
            table = format_proxy_table(proxies, current_name)
            console.print(table)
        elif format == "json":
            import json

            data = {
                "current_proxy": current_name,
                "proxies": {name: proxy.dict() for name, proxy in proxies.items()},
            }
            console.print(json.dumps(data, indent=2, ensure_ascii=False))
        elif format == "simple":
            for name, proxy in proxies.items():
                status = "✓" if proxy.is_active else "✗"
                current = " (当前)" if name == current_name else ""
                console.print(f"{status} {name}{current} - {proxy.base_url}")
        else:
            logger.error(f"不支持的输出格式: {format}")
            return

    except ClaudeWarpError as e:
        logger.error(f"操作失败: {e}")
        raise typer.Exit(1) from None
    except Exception as e:
        logger.error(f"未知错误: {e}")
        raise typer.Exit(1) from None


@app.command()
def use(
    name: str = typer.Argument(..., help="代理名称"),
    force: bool = typer.Option(False, "--force", "-f", help="强制切换(即使代理未启用)"),
):
    """切换到指定的代理服务器"""

    try:
        manager = get_proxy_manager()

        # 检查代理是否存在
        proxy = manager.get_proxy(name)

        # 检查代理状态
        if not proxy.is_active and not force:
            logger.warning(f"代理 '{name}' 未启用")
            console.print("使用 --force 强制切换，或先启用该代理")
            if not Confirm.ask("是否强制切换?", default=False):
                logger.info("用户取消操作")
                return

        # 切换代理
        logger.info(f"切换到代理: {name}")
        manager.switch_proxy(name)

        logger.info(f"成功切换到代理: {name}")

        # 显示代理信息
        console.print()
        console.print(format_proxy_info(proxy))

    except ProxyNotFoundError as e:
        logger.error(str(e))
        raise typer.Exit(1) from None
    except ClaudeWarpError as e:
        logger.error(f"操作失败: {e}")
        raise typer.Exit(1) from None
    except Exception as e:
        logger.error(f"未知错误: {e}")
        raise typer.Exit(1) from None


@app.command()
def current():
    """显示当前代理服务器信息"""

    try:
        manager = get_proxy_manager()

        current_proxy = manager.get_current_proxy()

        if current_proxy is None:
            logger.warning("未设置当前代理")
            # 显示可用代理列表
            proxies = manager.list_proxies()
            if proxies:
                console.print("\n可用的代理服务器:")
                for name in sorted(proxies.keys()):
                    console.print(f"  • {name}")
                console.print("\n使用 'claudewarp use <name>' 切换代理")
            else:
                console.print("暂无代理服务器配置")
                console.print("使用 'claudewarp add' 添加代理")
            return

        console.print("[bold blue]当前代理服务器[/bold blue]")
        console.print()
        console.print(format_proxy_info(current_proxy))

    except ClaudeWarpError as e:
        logger.error(f"操作失败: {e}")
        raise typer.Exit(1) from None
    except Exception as e:
        logger.error(f"未知错误: {e}")
        raise typer.Exit(1) from None


@app.command()
def remove(
    name: str = typer.Argument(..., help="代理名称"),
    force: bool = typer.Option(False, "--force", "-f", help="强制删除(不询问确认)"),
):
    """删除指定的代理服务器"""

    try:
        manager = get_proxy_manager()

        # 检查代理是否存在
        proxy = manager.get_proxy(name)

        # 确认删除
        if not force:
            console.print(f"即将删除代理: [bold red]{name}[/bold red]")
            console.print(f"URL: {proxy.base_url}")
            console.print(f"描述: {proxy.description}")
            console.print()

            if not Confirm.ask("确定要删除吗?", console=console):
                logger.info("用户取消操作")
                return

        # 检查是否是当前代理
        current_proxy = manager.get_current_proxy()
        is_current = current_proxy and current_proxy.name == name

        # 删除代理
        logger.info(f"删除代理: {name}")
        manager.remove_proxy(name)

        console.print(format_success(f"代理 '{name}' 删除成功"))
        logger.info(f"代理 '{name}' 删除成功")

        if is_current:
            new_current = manager.get_current_proxy()
            if new_current:
                console.print(f"[yellow]当前代理已切换到: {new_current.name}[/yellow]")
            else:
                console.print("[yellow]已清空当前代理设置[/yellow]")

    except ProxyNotFoundError as e:
        logger.error(str(e))
        raise typer.Exit(1) from None
    except ClaudeWarpError as e:
        logger.error(f"操作失败: {e}")
        raise typer.Exit(1) from None
    except Exception as e:
        logger.error(f"未知错误: {e}")
        raise typer.Exit(1) from None


@app.command()
def export(
    proxy_name: Optional[str] = typer.Option(
        None, "--name", "-n", help="指定代理名称(默认使用当前代理)"
    ),
    shell: str = typer.Option(
        "bash", "--shell", "-s", help="Shell类型: bash, fish, powershell, zsh"
    ),
    no_comments: bool = typer.Option(False, "--no-comments", help="不包含注释"),
    prefix: str = typer.Option("ANTHROPIC_", "--prefix", "-p", help="环境变量前缀"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="输出到文件"),
):
    """导出环境变量设置命令"""

    try:
        manager = get_proxy_manager()

        # 创建导出格式配置
        export_format = ExportFormat(
            shell_type=shell, include_comments=not no_comments, prefix=prefix
        )

        # 导出环境变量
        export_content = manager.export_environment(export_format, proxy_name)

        # 输出或保存到文件
        if output:
            try:
                with open(output, "w", encoding="utf-8") as f:
                    f.write(export_content)
                console.print(format_success(f"环境变量已导出到: {output}"))
            except Exception as e:
                logger.error(f"写入文件失败: {e}")
                raise typer.Exit(1) from None
        else:
            console.print(format_export_output(export_content, shell))

    except ProxyNotFoundError as e:
        logger.error(str(e))
        raise typer.Exit(1) from None
    except ValidationError as e:
        logger.error(str(e))
        raise typer.Exit(1) from None
    except ClaudeWarpError as e:
        logger.error(f"操作失败: {e}")
        raise typer.Exit(1) from None
    except Exception as e:
        logger.error(f"未知错误: {e}")
        raise typer.Exit(1) from None


@app.command()
def info(name: Optional[str] = typer.Argument(None, help="代理名称(不指定则显示统计信息)")):
    """显示代理详细信息或统计信息"""
    if not name:
        console.print("使用 'cw info <name>' 查看特定代理的详细信息")
        return

    try:
        manager = get_proxy_manager()

        # 显示指定代理的详细信息
        proxy = manager.get_proxy(name)
        console.print(f"[bold blue]代理服务器详细信息: {name}[/bold blue]")
        console.print()
        console.print(format_proxy_info(proxy, detailed=True))

    except ProxyNotFoundError as e:
        logger.error(str(e))
        raise typer.Exit(1) from None
    except ClaudeWarpError as e:
        logger.error(f"操作失败: {e}")
        raise typer.Exit(1) from None
    except Exception:
        logger.exception("未知错误")
        raise typer.Exit(1) from None


@app.command()
def edit(
    name: str = typer.Argument(..., help="代理名称"),
    new_name: Optional[str] = typer.Option(None, "--name", help="新的代理名称"),
    url: Optional[str] = typer.Option(None, "--url", help="新的URL"),
    key: Optional[str] = typer.Option(None, "--key", help="新的API密钥"),
    description: Optional[str] = typer.Option(None, "--desc", help="新的描述"),
    tags: Optional[str] = typer.Option(None, "--tags", help="新的标签列表，用逗号分隔"),
    enable: Optional[bool] = typer.Option(None, "--enable/--disable", help="启用/禁用代理"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="交互式编辑"),
):
    """编辑代理服务器配置"""

    try:
        manager = get_proxy_manager()

        # 获取当前代理信息
        proxy = manager.get_proxy(name)

        if interactive:
            console.print(f"[bold blue]编辑代理服务器: {name}[/bold blue]")
            console.print()
            console.print("当前配置:")
            console.print(format_proxy_info(proxy))
            console.print()

            # 交互式编辑
            new_name = Prompt.ask("代理名称", default=proxy.name, console=console)
            url = Prompt.ask("代理服务器URL", default=proxy.base_url, console=console)
            key = Prompt.ask("API密钥", default=proxy.api_key, console=console, password=True)
            description = Prompt.ask("描述信息", default=proxy.description, console=console)
            tags_input = Prompt.ask(
                "标签 (用逗号分隔)", default=",".join(proxy.tags), console=console
            )
            tags_list = [tag.strip() for tag in tags_input.split(",") if tag.strip()]
            enable = Confirm.ask("启用代理", default=proxy.is_active, console=console)
        else:
            # 构建更新参数
            update_kwargs = {}

            if url:
                update_kwargs["base_url"] = url
            if key:
                update_kwargs["api_key"] = key
            if description is not None:
                update_kwargs["description"] = description
            if tags is not None:
                tags_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
                update_kwargs["tags"] = tags_list
            if enable is not None:
                update_kwargs["is_active"] = enable

            # 检查是否需要重命名
            if new_name and new_name != name:
                # 需要重命名，使用特殊的重命名逻辑
                _update_proxy_with_rename(manager, name, new_name, update_kwargs)
                final_name = new_name
            else:
                # 不需要重命名，直接更新
                if not update_kwargs:
                    logger.warning("没有指定要更新的字段")
                    console.print("使用 --interactive 进行交互式编辑，或指定具体的更新参数")
                    return

                manager.update_proxy(name, **update_kwargs)
                final_name = name

            logger.info(f"代理 '{final_name}' 更新成功")

            # 显示更新后的信息
            updated_proxy = manager.get_proxy(final_name)
            console.print()
            console.print(format_proxy_info(updated_proxy))
            return

        # 交互式编辑的更新逻辑
        update_kwargs = {
            "base_url": url,
            "api_key": key,
            "description": description,
            "tags": tags_list,
            "is_active": enable,
        }

        # 检查是否需要重命名
        if new_name and new_name != name:
            # 需要重命名，使用特殊的重命名逻辑
            _update_proxy_with_rename(manager, name, new_name, update_kwargs)
            final_name = new_name
        else:
            # 不需要重命名，直接更新
            manager.update_proxy(name, **update_kwargs)
            final_name = name

        logger.info(f"代理 '{final_name}' 更新成功")

        # 显示更新后的信息
        updated_proxy = manager.get_proxy(final_name)
        console.print()
        console.print(format_proxy_info(updated_proxy))

    except ProxyNotFoundError as e:
        logger.error(str(e))
        raise typer.Exit(1) from None
    except (DuplicateProxyError, ValidationError) as e:
        logger.error(str(e))
        raise typer.Exit(1) from None
    except ClaudeWarpError as e:
        logger.error(f"操作失败: {e}")
        raise typer.Exit(1) from None
    except Exception:
        logger.exception("未知错误")
        raise typer.Exit(1) from None


@app.command()
def search(
    query: str = typer.Argument(..., help="搜索关键词"),
    fields: Optional[str] = typer.Option(
        "name,description,tags", "--fields", help="搜索字段，用逗号分隔"
    ),
):
    """搜索代理服务器"""

    try:
        manager = get_proxy_manager()

        # 解析搜索字段
        search_fields = [field.strip() for field in fields.split(",")]

        # 执行搜索
        results = manager.search_proxies(query, search_fields)

        if not results:
            logger.warning(f"未找到匹配 '{query}' 的代理")
            return

        console.print(f"[bold blue]搜索结果: '{query}'[/bold blue]")
        console.print()

        # 获取当前代理
        current_proxy = manager.get_current_proxy()
        current_name = current_proxy.name if current_proxy else None

        # 显示搜索结果
        table = format_proxy_table(results, current_name)
        console.print(table)

        console.print(f"\\n[dim]找到 {len(results)} 个匹配的代理[/dim]")

    except ClaudeWarpError as e:
        logger.error(f"操作失败: {e}")
        raise typer.Exit(1) from None
    except Exception:
        logger.exception("未知错误")
        raise typer.Exit(1) from None


def main():
    """CLI主入口函数"""
    try:
        app()
    except KeyboardInterrupt:
        logger.info("用户中断操作")
        sys.exit(1)
    except Exception:
        logger.exception("程序异常")
        sys.exit(1)


if __name__ == "__main__":
    main()
