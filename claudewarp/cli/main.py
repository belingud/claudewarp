"""
CLI应用主程序

基于Typer的命令行界面入口点。
提供完整的命令行交互功能，支持所有代理管理操作。
"""

import logging
import sys

import colorlog

from claudewarp.core.utils import LevelAlignFilter


# 设置彩色日志
def setup_colored_logging():
    """设置彩色日志配置"""
    handler = colorlog.StreamHandler()
    handler.addFilter(LevelAlignFilter())
    handler.setFormatter(
        colorlog.ColoredFormatter(
            "%(log_color)s%(levelname_padded)s%(reset)s%(asctime)s: %(message)s",
            datefmt="%H:%M:%S",
            reset=True,
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white",
            },
            secondary_log_colors={},
            style="%",
        )
    )

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)


# 设置彩色日志
setup_colored_logging()


def main() -> int:
    """CLI主程序入口"""
    try:
        # 导入commands模块并运行Typer应用
        from claudewarp.cli.commands import main as typer_main

        typer_main()
        return 0

    except KeyboardInterrupt:
        print("\n操作已取消")
        return 130
    except Exception as e:
        print(f"CLI执行失败: {e}")
        return 1


# 兼容性函数，用于从主程序调用
def cli_main(args=None) -> int:
    """CLI兼容性入口函数

    Args:
        args: 命令行参数（保留接口兼容性）

    Returns:
        int: 退出码
    """
    # 忽略传入的args参数，直接调用main()
    # 因为我们使用Typer处理命令行参数
    return main()


if __name__ == "__main__":
    sys.exit(main())
