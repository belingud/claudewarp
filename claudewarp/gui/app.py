"""
GUI应用主程序

基于PySide6的图形用户界面入口点。
"""

import logging
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication


def setup_logging(debug: bool = False) -> None:
    """设置日志配置

    Args:
        debug: 是否启用调试模式
    """
    try:
        import colorlog

        # 创建 colorlog handler
        handler = colorlog.StreamHandler()
        handler.setFormatter(
            colorlog.ColoredFormatter(
                "%(log_color)s[%(levelname)s]%(reset)s %(asctime)s %(name)s %(filename)s:%(lineno)d - %(message)s",
                datefmt="%H:%M:%S",
                log_colors={
                    "DEBUG": "cyan",
                    "INFO": "green",
                    "WARNING": "yellow",
                    "ERROR": "red",
                    "CRITICAL": "red,bg_white",
                },
            )
        )

        # 设置根日志器
        root_logger = logging.getLogger()
        root_logger.handlers.clear()  # 清除默认处理器
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.DEBUG if debug else logging.INFO)

        # 设置具体模块的日志级别
        if debug:
            logging.getLogger("core").setLevel(logging.DEBUG)
            logging.getLogger("gui").setLevel(logging.DEBUG)
            logging.getLogger("__main__").setLevel(logging.DEBUG)
        else:
            logging.getLogger("core").setLevel(logging.INFO)
            logging.getLogger("gui").setLevel(logging.INFO)

        # 设置 PySide6 的日志级别（减少干扰）
        logging.getLogger("PySide6").setLevel(logging.WARNING)
        logging.getLogger("Qt").setLevel(logging.WARNING)

    except ImportError:
        # 如果没有 colorlog，使用默认配置
        logging.basicConfig(
            level=logging.DEBUG if debug else logging.INFO,
            format="[%(levelname)s] %(asctime)s %(name)s %(filename)s:%(lineno)d - %(message)s",
            datefmt="%H:%M:%S",
        )


def main(debug: bool = False) -> int:
    """GUI主程序入口"""
    # 设置日志
    setup_logging(debug)
    logger = logging.getLogger(__name__)

    logger.info(f"CloudWarp GUI 启动，调试模式: {debug}")

    try:
        # 创建QApplication实例
        logger.debug("创建 QApplication 实例")
        app = QApplication(sys.argv)

        # 设置应用程序属性
        logger.debug("设置应用程序属性")
        app.setApplicationName("Claude Proxy Manager")
        app.setApplicationDisplayName("Claude中转站管理工具")
        app.setApplicationVersion("0.1.0")
        app.setOrganizationName("claudewarp")
        app.setOrganizationDomain("claudewarp.local")

        # 启用高DPI支持
        logger.debug("启用高DPI支持")
        app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        # 设置应用样式
        logger.debug("设置应用样式为 Fusion")
        app.setStyle("Fusion")  # 使用Fusion样式获得更好的跨平台外观

        # 创建主窗口
        logger.info("创建主窗口")
        from claudewarp.gui.main_window import MainWindow

        window = MainWindow()

        # 设置窗口图标（如果有的话）
        try:
            # TODO: 添加应用图标
            # icon = QIcon(":/icons/app.png")
            # app.setWindowIcon(icon)
            logger.debug("尚未设置应用图标")
        except Exception as e:
            logger.warning(f"设置图标失败: {e}")

        # 显示窗口
        logger.info("显示主窗口")
        window.show()

        if debug:
            logger.info("GUI调试模式已启用")

        # 运行应用程序
        logger.info("应用程序进入主循环")
        return app.exec()

    except ImportError as e:
        logger.error(f"无法导入: {e}")
        return 1
    except Exception as e:
        logger.error(f"GUI启动失败: {e}")
        if debug:
            logger.exception("详细错误信息:")
        return 1


if __name__ == "__main__":
    import sys

    debug = "--debug" in sys.argv
    sys.exit(main(debug=debug))
