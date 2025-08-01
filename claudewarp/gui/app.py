"""
GUI应用主程序

基于PySide6的图形用户界面入口点。
"""

import logging
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase, QIcon
from PySide6.QtWidgets import QApplication

from claudewarp.core.utils import LevelAlignFilter


def setup_logging(debug: bool = False) -> None:
    """设置日志配置

    Args:
        debug: 是否启用调试模式
    """
    try:
        import colorlog

        # 创建 colorlog handler
        handler = colorlog.StreamHandler()
        handler.addFilter(LevelAlignFilter())
        handler.setFormatter(
            colorlog.ColoredFormatter(
                "%(log_color)s%(levelname_padded)s%(reset)s %(asctime)s %(name)s %(filename)s:%(lineno)d - %(message)s",
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


def set_default_font(app: QApplication) -> None:
    """根据操作系统设置默认字体，避免字体缺失警告"""
    font_families = []
    if sys.platform == "win32":
        # Windows: 优先使用微软雅黑UI
        font_families = ["Microsoft YaHei UI", "Tahoma"]
    elif sys.platform == "darwin":
        # macOS: 优先使用苹方
        font_families = ["PingFang SC", "Helvetica Neue", "Arial"]
    else:
        # Linux: 常见中文字体
        font_families = ["Noto Sans CJK SC", "WenQuanYi Micro Hei", "sans-serif"]

    for family in font_families:
        if family in QFontDatabase.families():
            app.setFont(QFont(family, 10))
            logging.getLogger(__name__).info(f"设置默认字体为: {family}")
            return

    logging.getLogger(__name__).warning("未找到推荐的默认字体，使用系统默认字体。")


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
        set_default_font(app)
 
        # 设置应用程序属性
        logger.debug("设置应用程序属性")
        app.setApplicationName("Claude Proxy Manager")
        app.setApplicationDisplayName("Claude中转站管理工具")
        app.setApplicationVersion("0.1.0")
        app.setOrganizationName("claudewarp")
        app.setOrganizationDomain("claudewarp.local")

        # 启用高DPI支持
        logger.debug("启用高DPI支持")
        app.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
        app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

        # 设置Fluent主题
        logger.debug("设置Fluent主题")
        from qfluentwidgets import Theme, setTheme

        setTheme(Theme.AUTO)  # 自动主题，根据系统设置切换

        # 创建主窗口
        logger.info("创建主窗口")
        from claudewarp.gui.main_window import MainWindow

        window = MainWindow()

        # 设置窗口图标
        try:
            icon_path = Path(__file__).parent / "resources" / "icons" / "claudewarp.ico"
            if icon_path.exists():
                icon = QIcon(str(icon_path))
                app.setWindowIcon(icon)
                logger.debug(f"设置应用图标: {icon_path}")
            else:
                logger.warning(f"图标文件不存在: {icon_path}")
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
