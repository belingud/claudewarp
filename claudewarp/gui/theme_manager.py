"""
主题管理器

提供自动主题检测和切换功能，支持系统主题自动适配和手动主题选择。
"""

import logging
from enum import Enum
from pathlib import Path
from typing import Optional

try:
    import winreg  # type: ignore
except ImportError:
    winreg = None

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication

from claudewarp.core.manager import ProxyManager

try:
    from qfluentwidgets import Theme as QFluentTheme  # type: ignore
    from qfluentwidgets import isDarkTheme, setTheme  # type: ignore

    _HAS_QFLUENT = True
except ImportError:
    # 如果没有安装 qfluentwidgets，提供备用实现
    from enum import Enum as EnumBase

    class QFluentTheme(EnumBase):
        LIGHT = "Light"
        DARK = "Dark"
        AUTO = "Auto"

    def setTheme(theme: QFluentTheme) -> None:
        _ = theme  # 避免未使用参数警告
        pass

    def isDarkTheme() -> bool:
        return False

    _HAS_QFLUENT = False

import darkdetect


class ThemeMode(Enum):
    """主题模式枚举"""

    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"


class ThemeManager(QObject):
    """主题管理器

    提供自动主题检测、主题切换和主题持久化功能。
    支持跟随系统主题变化自动切换。
    """

    # 主题变化信号
    theme_changed = Signal(str)  # 发送新主题名称

    def __init__(self, proxy_manager: ProxyManager, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.proxy_manager = proxy_manager

        # QSS 文件路径
        self.qss_dir = Path(__file__).parent / "resources" / "qss"

        # 当前主题模式和实际主题
        self._theme_mode = ThemeMode.AUTO
        self._current_theme = None

        # 系统主题检测定时器
        self.theme_timer = QTimer(self)  # 设置父对象
        self.theme_timer.timeout.connect(self._check_system_theme)
        self.theme_timer.setInterval(5000)  # 每5秒检查一次

        # 初始化
        self._load_settings()

        # 延迟初始化主题，确保在Qt应用程序上下文中
        self._delayed_init_theme()

        self.logger.info(f"主题管理器初始化完成，当前模式: {self._theme_mode.value}")

    def _delayed_init_theme(self):
        """延迟初始化主题，确保在Qt应用程序上下文中执行"""
        try:
            # 检查是否有QApplication实例
            app = QApplication.instance()
            if app is not None:
                self.logger.debug("检测到QApplication实例，立即初始化主题")
                self._init_theme()
            else:
                self.logger.debug("未检测到QApplication实例，延迟初始化主题")
                # 使用QTimer延迟执行，等待QApplication创建
                QTimer.singleShot(100, self._try_init_theme)
        except Exception as e:
            self.logger.error(f"延迟初始化主题失败: {e}")

    def _try_init_theme(self):
        """尝试初始化主题"""
        try:
            app = QApplication.instance()
            if app is not None:
                self.logger.debug("延迟检测到QApplication实例，开始初始化主题")
                self._init_theme()
            else:
                self.logger.warning("仍未检测到QApplication实例，使用基本主题初始化")
                # 至少设置当前主题，即使无法应用样式
                self._current_theme = self._detect_system_theme()
                if self._theme_mode == ThemeMode.AUTO:
                    # 尝试启动定时器
                    try:
                        self.theme_timer.start()
                        self.logger.info("定时器启动成功")
                    except Exception as e:
                        self.logger.warning(f"定时器启动失败: {e}")
        except Exception as e:
            self.logger.error(f"尝试初始化主题失败: {e}")

    def _load_settings(self):
        """加载主题设置"""
        theme_mode_str = ""
        try:
            # 从设置中加载主题模式
            theme_mode_str = self.proxy_manager.get_theme_setting()
            self._theme_mode = ThemeMode(theme_mode_str)
            self.logger.debug(f"从设置中加载主题模式: {self._theme_mode.value}")
        except (ValueError, AttributeError):
            self.logger.warning(f"无效的主题模式设置: {theme_mode_str}，使用默认值")
            self._theme_mode = ThemeMode.AUTO

    def _save_settings(self):
        """保存主题设置"""
        try:
            self.proxy_manager.save_theme_setting(self._theme_mode.value)
            self.logger.debug(f"保存主题模式设置: {self._theme_mode.value}")
        except Exception as e:
            self.logger.error(f"通过 ProxyManager 保存主题设置失败: {e}")

    def _init_theme(self):
        """初始化主题"""
        self.logger.info(f"初始化主题，模式: {self._theme_mode.value}")

        # 停止现有的定时器
        if self.theme_timer.isActive():
            self.theme_timer.stop()
            self.logger.debug("停止现有的主题监控定时器")

        if self._theme_mode == ThemeMode.AUTO:
            self.logger.info("应用系统主题")
            self._apply_system_theme()
            # 启动系统主题监控
            try:
                # 检查是否在Qt线程中
                app = QApplication.instance()
                if app is not None:
                    self.theme_timer.start()
                    self.logger.info(
                        f"系统主题监控已启动，检查间隔: {self.theme_timer.interval()}ms"
                    )
                else:
                    self.logger.warning("没有QApplication实例，无法启动定时器")
            except Exception as e:
                self.logger.error(f"启动主题监控定时器失败: {e}")
        else:
            self.logger.info("应用手动主题")
            self._apply_manual_theme()
            self.logger.info("系统主题监控已停止")

    def _detect_system_theme(self) -> str:
        """检测系统主题

        使用多种方法检测系统主题，支持 macOS、Windows 和部分 Linux 环境。

        Returns:
            系统主题名称: 'dark' 或 'light'
        """
        try:
            # 方法1: 使用 darkdetect 检测系统主题
            detected_theme = darkdetect.theme()

            if detected_theme is not None:
                # darkdetect 返回 "Dark" 或 "Light"，转换为小写
                theme = detected_theme.lower()
                self.logger.debug(f"darkdetect 检测到系统主题: {theme}")
                return theme

            self.logger.warning("darkdetect 无法检测系统主题，尝试备用方法")

            # 方法2: 尝试使用 QFluentWidgets 的检测
            if _HAS_QFLUENT:
                try:
                    is_dark = isDarkTheme()
                    theme = "dark" if is_dark else "light"
                    self.logger.debug(f"QFluentWidgets 检测到系统主题: {theme}")
                    return theme
                except Exception as e:
                    self.logger.warning(f"QFluentWidgets 检测失败: {e}")

            # 方法3: 平台特定的检测方法
            import platform

            system = platform.system().lower()

            if system == "darwin":  # macOS
                try:
                    import subprocess

                    result = subprocess.run(
                        ["defaults", "read", "-g", "AppleInterfaceStyle"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode == 0 and "dark" in result.stdout.lower():
                        self.logger.debug("macOS 系统检测到深色主题")
                        return "dark"
                    else:
                        self.logger.debug("macOS 系统检测到浅色主题")
                        return "light"
                except Exception as e:
                    self.logger.warning(f"macOS 主题检测失败: {e}")

            elif system == "windows":  # Windows
                try:
                    if winreg is not None:
                        registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)  # type: ignore
                        key = winreg.OpenKey(  # type: ignore
                            registry,
                            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize",
                        )
                        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")  # type: ignore
                        winreg.CloseKey(key)  # type: ignore
                        theme = "light" if value else "dark"
                    else:
                        theme = "light"  # fallback
                    self.logger.debug(f"Windows 系统检测到主题: {theme}")
                    return theme
                except Exception as e:
                    self.logger.warning(f"Windows 主题检测失败: {e}")

            # 默认返回浅色主题
            self.logger.warning("所有检测方法都失败，使用默认浅色主题")
            return "light"

        except Exception as e:
            self.logger.error(f"检测系统主题时发生异常: {e}")
            return "light"

    def _apply_system_theme(self):
        """应用系统主题"""
        system_theme = self._detect_system_theme()
        self.logger.debug(f"检测到系统主题: {system_theme}")
        self._apply_theme(system_theme)

    def _apply_manual_theme(self):
        """应用手动设置的主题"""
        if self._theme_mode == ThemeMode.LIGHT:
            self._apply_theme("light")
        elif self._theme_mode == ThemeMode.DARK:
            self._apply_theme("dark")

    def _apply_theme(self, theme_name: str):
        """应用指定主题

        Args:
            theme_name: 主题名称 ('light' 或 'dark')
        """
        self.logger.debug(f"准备应用主题: {theme_name}, 当前主题: {self._current_theme}")
        if self._current_theme == theme_name:
            self.logger.debug(f"主题未变化，跳过应用: {theme_name}")
            return  # 主题未变化

        try:
            self.logger.info(f"开始应用主题: {theme_name}")

            # 设置 QFluentWidgets 主题
            if theme_name == "dark":
                setTheme(QFluentTheme.DARK)
                self.logger.debug("已设置 QFluentWidgets 为深色主题")
            else:
                setTheme(QFluentTheme.LIGHT)
                self.logger.debug("已设置 QFluentWidgets 为浅色主题")

            # 加载对应的 QSS 文件
            self._load_qss_theme(theme_name)

            # 更新当前主题
            old_theme = self._current_theme
            self._current_theme = theme_name
            self.logger.debug(f"已更新当前主题: {old_theme} -> {theme_name}")

            # 发送主题变化信号
            self.theme_changed.emit(theme_name)
            self.logger.debug("已发送主题变化信号")

            self.logger.info(f"主题切换成功: {old_theme} -> {theme_name}")

        except Exception as e:
            self.logger.error(f"应用主题失败: {e}")
            import traceback

            self.logger.error(f"详细错误信息: {traceback.format_exc()}")

    def _load_qss_theme(self, theme_name: str):
        """加载 QSS 主题文件

        Args:
            theme_name: 主题名称
        """
        try:
            self.logger.debug(f"开始加载 QSS 主题: {theme_name}")

            # 检查是否有QApplication实例
            app = QApplication.instance()
            if app is None:
                self.logger.debug("没有QApplication实例，跳过QSS样式应用")
                return

            # 根据主题名称选择 QSS 文件
            if theme_name == "dark":
                qss_file = self.qss_dir / "dark.qss"
            else:
                qss_file = self.qss_dir / "bright.qss"

            self.logger.debug(f"QSS 文件路径: {qss_file}")
            self.logger.debug(f"QSS 目录存在: {self.qss_dir.exists()}")
            self.logger.debug(f"QSS 文件存在: {qss_file.exists()}")

            if not qss_file.exists():
                self.logger.warning(f"QSS 文件不存在: {qss_file}")
                # 尝试创建基本的QSS内容
                self._apply_fallback_theme(theme_name)
                return

            # 读取并应用 QSS
            with open(qss_file, "r", encoding="utf-8") as f:
                qss_content = f.read()

            self.logger.debug(f"QSS 内容长度: {len(qss_content)} 字符")

            if hasattr(app, "setStyleSheet"):
                app.setStyleSheet(qss_content)  # type: ignore
                self.logger.info(f"成功应用 QSS 文件: {qss_file.name}")
            else:
                self.logger.warning("QApplication 没有 setStyleSheet 方法")

        except Exception as e:
            self.logger.error(f"加载 QSS 主题失败: {e}")
            # 尝试应用备用主题
            self._apply_fallback_theme(theme_name)

    def _apply_fallback_theme(self, theme_name: str):
        """应用备用主题样式

        Args:
            theme_name: 主题名称
        """
        try:
            self.logger.info(f"应用备用 {theme_name} 主题样式")

            if theme_name == "dark":
                fallback_qss = """
                QMainWindow {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QWidget {
                    background-color: #3c3c3c;
                    color: #ffffff;
                }
                QTableWidget {
                    background-color: #404040;
                    color: #ffffff;
                    selection-background-color: #555555;
                }
                QPushButton {
                    background-color: #505050;
                    color: #ffffff;
                    border: 1px solid #666666;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: #606060;
                }
                QLineEdit, QTextEdit {
                    background-color: #404040;
                    color: #ffffff;
                    border: 1px solid #666666;
                }
                """
            else:
                fallback_qss = """
                QMainWindow {
                    background-color: #ffffff;
                    color: #000000;
                }
                QWidget {
                    background-color: #f5f5f5;
                    color: #000000;
                }
                QTableWidget {
                    background-color: #ffffff;
                    color: #000000;
                    selection-background-color: #e0e0e0;
                }
                QPushButton {
                    background-color: #f0f0f0;
                    color: #000000;
                    border: 1px solid #cccccc;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
                QLineEdit, QTextEdit {
                    background-color: #ffffff;
                    color: #000000;
                    border: 1px solid #cccccc;
                }
                """

            app = QApplication.instance()
            if app:
                if hasattr(app, "setStyleSheet"):
                    app.setStyleSheet(fallback_qss)  # type: ignore
                    self.logger.info(f"成功应用备用 {theme_name} 主题")
                else:
                    self.logger.warning("QApplication 没有 setStyleSheet 方法")

        except Exception as e:
            self.logger.error(f"应用备用主题失败: {e}")

    def _check_system_theme(self):
        """定期检查系统主题变化"""
        try:
            if self._theme_mode != ThemeMode.AUTO:
                self.logger.debug("当前不是自动主题模式，跳过系统主题检查")
                return

            system_theme = self._detect_system_theme()
            self.logger.debug(f"检查系统主题 - 当前: {self._current_theme}, 系统: {system_theme}")

            if system_theme != self._current_theme:
                self.logger.info(f"检测到系统主题变化: {self._current_theme} -> {system_theme}")
                self._apply_theme(system_theme)
            else:
                self.logger.debug("系统主题未变化")

        except Exception as e:
            self.logger.error(f"检查系统主题时发生错误: {e}")

    # 公共接口

    def get_theme_mode(self) -> ThemeMode:
        """获取当前主题模式"""
        return self._theme_mode

    def get_current_theme(self) -> Optional[str]:
        """获取当前实际应用的主题"""
        return self._current_theme

    def set_theme_mode(self, mode: ThemeMode):
        """设置主题模式

        Args:
            mode: 主题模式
        """
        if self._theme_mode == mode:
            return

        self.logger.info(f"设置主题模式: {self._theme_mode.value} -> {mode.value}")
        self._theme_mode = mode
        self._save_settings()

        # 重新初始化主题
        self._init_theme()

    def set_light_theme(self):
        """设置浅色主题"""
        self.set_theme_mode(ThemeMode.LIGHT)

    def set_dark_theme(self):
        """设置深色主题"""
        self.set_theme_mode(ThemeMode.DARK)

    def set_auto_theme(self):
        """设置自动主题（跟随系统）"""
        self.set_theme_mode(ThemeMode.AUTO)

    def toggle_theme(self):
        """切换主题（在浅色和深色之间）"""
        if self._current_theme == "dark":
            self.set_light_theme()
        else:
            self.set_dark_theme()

    def refresh_theme(self):
        """刷新主题（重新检测和应用）"""
        self.logger.info("手动刷新主题")
        try:
            if self._theme_mode == ThemeMode.AUTO:
                self.logger.debug("刷新自动主题")
                self._apply_system_theme()
            else:
                self.logger.debug("刷新手动主题")
                self._apply_manual_theme()
        except Exception as e:
            self.logger.error(f"刷新主题失败: {e}")

    def force_theme_detection(self) -> str:
        """强制检测系统主题（用于调试）

        Returns:
            检测到的主题名称
        """
        self.logger.info("强制检测系统主题")
        detected_theme = self._detect_system_theme()
        self.logger.info(f"强制检测结果: {detected_theme}")
        return detected_theme

    def get_theme_info(self) -> dict:
        """获取主题信息（用于调试）

        Returns:
            包含主题信息的字典
        """
        return {
            "theme_mode": self._theme_mode.value,
            "current_theme": self._current_theme,
            "timer_active": self.theme_timer.isActive(),
            "timer_interval": self.theme_timer.interval(),
            "qss_dir_exists": self.qss_dir.exists(),
            "dark_qss_exists": (self.qss_dir / "dark.qss").exists(),
            "bright_qss_exists": (self.qss_dir / "bright.qss").exists(),
        }


# 单例主题管理器实例
_theme_manager_instance: Optional[ThemeManager] = None


def get_theme_manager(proxy_manager: Optional[ProxyManager] = None) -> ThemeManager:
    """获取主题管理器单例实例"""
    global _theme_manager_instance
    if _theme_manager_instance is None:
        if proxy_manager is None:
            # 在某些情况下（如CLI），可能没有proxy_manager
            # 但对于GUI，必须提供
            raise ValueError("首次获取ThemeManager时必须提供ProxyManager实例")
        _theme_manager_instance = ThemeManager(proxy_manager)
    return _theme_manager_instance


def set_theme_manager(manager: ThemeManager):
    """设置主题管理器实例（用于测试）"""
    global _theme_manager_instance
    _theme_manager_instance = manager


# 导出
__all__ = ["ThemeMode", "ThemeManager", "get_theme_manager", "set_theme_manager"]
