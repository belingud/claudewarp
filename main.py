#!/usr/bin/env python3
"""
Claude中转站管理工具主入口

支持CLI和GUI两种模式，根据命令行参数选择运行模式。
"""

import argparse
import sys
from typing import List, Optional


def parse_arguments(args: Optional[List[str]] = None) -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        prog="claudewarp",
        description="Claude API proxy management tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--debug", action="store_true", help="启用调试模式")

    return parser.parse_args(args)


def run_gui_mode(debug: bool = False) -> int:
    """运行GUI模式"""
    from claudewarp.gui.app import main as gui_main

    gui_main()
    # try:
    #     # 延迟导入GUI模块，避免在CLI模式下加载PySide6
    #     from claudewarp.gui.app import main as gui_main

    #     return gui_main(debug=debug)
    # # except ImportError as e:
    # #     print(f"错误: 无法启动GUI模式，缺少PySide6依赖: {e}")
    # #     print("请运行: pip install 'claudewarp[gui]' 或 pip install PySide6")
    # #     return 1
    # except Exception as e:
    #     print(f"GUI模式启动失败: {e}")
    #     return 1


def main() -> int:
    """主入口函数"""
    try:
        args = parse_arguments()

        return run_gui_mode(debug=getattr(args, "debug", False))

    except KeyboardInterrupt:
        print("\n用户中断操作")
        return 130
    except Exception as e:
        print(f"程序运行出错: {e}")
        if "--debug" in sys.argv:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
