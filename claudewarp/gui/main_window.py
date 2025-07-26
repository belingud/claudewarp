"""
GUI主窗口实现

基于PySide6的主窗口，提供代理管理的图形界面。
"""

import logging
import sys
from datetime import datetime
from typing import Dict, Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QSplitter,
    QStatusBar,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

# PyQt-Fluent-Widgets imports
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CardWidget,
    ComboBox,
    FluentIcon,
    LineEdit,
    PrimaryPushButton,
    PushButton,
    StrongBodyLabel,
    TableWidget,
    TextEdit,
    TitleLabel,
)

from claudewarp.core.manager import ProxyManager
from claudewarp.core.models import ExportFormat, ProxyServer
from claudewarp.gui.dialogs import (
    AboutDialog,
    AddProxyDialog,
    ConfirmDialog,
    EditProxyDialog,
    ExportDialog,
)


class MainWindow(QMainWindow):
    """主窗口类

    提供完整的代理管理图形界面，包含代理列表、操作按钮、
    当前代理信息显示和环境变量导出功能。
    """

    # 信号定义
    proxy_changed = Signal(str)  # 代理切换信号
    proxy_added = Signal(str)  # 代理添加信号
    proxy_removed = Signal(str)  # 代理删除信号

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("初始化主窗口")

        # 初始化代理管理器
        try:
            self.logger.debug("初始化代理管理器")
            self.proxy_manager = ProxyManager()
            self.logger.info("代理管理器初始化成功")
        except Exception as e:
            self.logger.error(f"初始化代理管理器失败: {e}")
            QMessageBox.critical(None, "初始化失败", f"无法初始化代理管理器:\n{e}")
            sys.exit(1)

        # 初始化UI
        self.logger.debug("设置用户界面")
        self.setup_ui()
        self.setup_menu_bar()
        self.setup_status_bar()
        self.setup_connections()

        # 加载数据
        self.logger.debug("加载初始数据")
        self.refresh_data()

        # 设置定时器用于状态更新
        self.logger.debug("设置状态更新定时器")
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(5000)  # 每5秒更新一次状态

        self.logger.info("主窗口初始化完成")

    def setup_ui(self):
        """设置用户界面"""
        self.setWindowTitle("Claude Proxy Manager")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)

        # 创建中央widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建主布局
        main_layout = QHBoxLayout(central_widget)

        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # 左侧：代理列表和操作区域
        left_widget = self.create_left_panel()
        splitter.addWidget(left_widget)

        # 右侧：当前代理信息和导出区域
        right_widget = self.create_right_panel()
        splitter.addWidget(right_widget)

        # 设置分割器比例
        splitter.setSizes([600, 400])

    def create_left_panel(self) -> QWidget:
        """创建左侧面板（代理列表和操作）"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 搜索栏
        search_group = self.create_search_group()
        layout.addWidget(search_group)

        # 代理列表
        proxy_list_group = self.create_proxy_list_group()
        layout.addWidget(proxy_list_group)

        # 操作按钮
        action_group = self.create_action_group()
        layout.addWidget(action_group)

        return widget

    def create_right_panel(self) -> QWidget:
        """创建右侧面板（信息和导出）"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 当前代理信息
        current_group = self.create_current_proxy_group()
        layout.addWidget(current_group)

        # 导出功能
        export_group = self.create_export_group()
        layout.addWidget(export_group)

        # 统计信息
        stats_group = self.create_stats_group()
        layout.addWidget(stats_group)

        return widget

    def create_search_group(self) -> CardWidget:
        """创建搜索组"""
        group = CardWidget()
        layout = QVBoxLayout(group)

        # 添加标题
        title = TitleLabel("搜索和筛选")
        layout.addWidget(title)

        # 创建内容布局
        content_layout = QHBoxLayout()

        # 搜索框
        self.search_edit = LineEdit()
        self.search_edit.setPlaceholderText("搜索代理名称、描述或标签...")
        self.search_edit.setClearButtonEnabled(True)
        content_layout.addWidget(BodyLabel("搜索:"))
        content_layout.addWidget(self.search_edit)

        # 状态筛选
        self.status_filter = ComboBox()
        self.status_filter.addItems(["全部", "启用", "禁用"])
        content_layout.addWidget(BodyLabel("状态:"))
        content_layout.addWidget(self.status_filter)

        # 清除按钮
        self.clear_search_btn = PushButton("清除")
        self.clear_search_btn.setIcon(FluentIcon.DELETE)
        content_layout.addWidget(self.clear_search_btn)

        layout.addLayout(content_layout)

        return group

    def create_proxy_list_group(self) -> CardWidget:
        """创建代理列表组"""
        group = CardWidget()
        layout = QVBoxLayout(group)

        # 添加标题
        title = TitleLabel("代理服务器列表")
        layout.addWidget(title)

        # 创建表格
        self.proxy_table = TableWidget()
        self.proxy_table.setColumnCount(5)
        self.proxy_table.setHorizontalHeaderLabels(["状态", "名称", "URL", "描述", "更新时间"])

        # 设置表格属性
        self.proxy_table.setAlternatingRowColors(True)
        self.proxy_table.setSelectionBehavior(TableWidget.SelectRows)
        self.proxy_table.setSelectionMode(TableWidget.SingleSelection)
        self.proxy_table.setSortingEnabled(True)

        # 设置列宽
        header = self.proxy_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 状态
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 名称
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # URL
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # 描述
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 时间

        layout.addWidget(self.proxy_table)

        return group

    def create_action_group(self) -> CardWidget:
        """创建操作按钮组"""
        group = CardWidget()
        layout = QVBoxLayout(group)

        # 添加标题
        title = TitleLabel("操作")
        layout.addWidget(title)

        # 创建按钮布局
        button_layout = QHBoxLayout()

        # 创建按钮
        self.add_btn = PrimaryPushButton("添加")
        self.add_btn.setIcon(FluentIcon.ADD)
        self.edit_btn = PushButton("编辑")
        self.edit_btn.setIcon(FluentIcon.EDIT)
        self.remove_btn = PushButton("删除")
        self.remove_btn.setIcon(FluentIcon.DELETE)
        self.switch_btn = PrimaryPushButton("切换")
        self.switch_btn.setIcon(FluentIcon.SYNC)
        self.toggle_btn = PushButton("启用/禁用")
        self.toggle_btn.setIcon(FluentIcon.POWER_BUTTON)
        self.refresh_btn = PushButton("刷新")
        self.refresh_btn.setIcon(FluentIcon.SYNC)

        # 设置按钮提示文本
        self.add_btn.setToolTip("添加新的代理")
        self.edit_btn.setToolTip("编辑选中的代理")
        self.remove_btn.setToolTip("删除选中的代理")
        self.switch_btn.setToolTip("切换到选中的代理")
        self.toggle_btn.setToolTip("切换启用状态")
        self.refresh_btn.setToolTip("刷新代理列表")

        # 添加按钮到布局
        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.edit_btn)
        button_layout.addWidget(self.remove_btn)
        button_layout.addWidget(self.switch_btn)
        button_layout.addWidget(self.toggle_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.refresh_btn)

        layout.addLayout(button_layout)

        # 默认禁用需要选择的按钮
        self.edit_btn.setEnabled(False)
        self.remove_btn.setEnabled(False)
        self.switch_btn.setEnabled(False)
        self.toggle_btn.setEnabled(False)

        return group

    def create_current_proxy_group(self) -> CardWidget:
        """创建当前代理信息组"""
        group = CardWidget()
        layout = QVBoxLayout(group)

        # 添加标题
        title = TitleLabel("当前代理信息")
        layout.addWidget(title)

        # 当前代理标签
        self.current_proxy_label = StrongBodyLabel("未设置代理")
        self.current_proxy_label.setStyleSheet("color: #666; padding: 10px;")
        layout.addWidget(self.current_proxy_label)

        # 代理详细信息
        self.proxy_info_text = TextEdit()
        self.proxy_info_text.setReadOnly(True)
        self.proxy_info_text.setMaximumHeight(200)
        layout.addWidget(self.proxy_info_text)

        return group

    def create_export_group(self) -> CardWidget:
        """创建导出组"""
        group = CardWidget()
        layout = QVBoxLayout(group)

        # 添加标题
        title = TitleLabel("环境变量导出")
        layout.addWidget(title)

        # 导出按钮布局
        button_layout = QHBoxLayout()

        self.export_bash_btn = PushButton("Bash")
        self.export_fish_btn = PushButton("Fish")
        self.export_ps_btn = PushButton("PowerShell")
        self.export_custom_btn = PushButton("自定义...")

        # 添加图标
        self.export_bash_btn.setIcon(FluentIcon.DEVELOPER_TOOLS)
        self.export_fish_btn.setIcon(FluentIcon.DEVELOPER_TOOLS)
        self.export_ps_btn.setIcon(FluentIcon.DEVELOPER_TOOLS)
        self.export_custom_btn.setIcon(FluentIcon.SETTING)

        button_layout.addWidget(self.export_bash_btn)
        button_layout.addWidget(self.export_fish_btn)
        button_layout.addWidget(self.export_ps_btn)
        button_layout.addWidget(self.export_custom_btn)
        button_layout.addStretch()

        layout.addLayout(button_layout)

        # 导出内容显示
        self.export_text = TextEdit()
        self.export_text.setMaximumHeight(120)
        self.export_text.setReadOnly(True)
        self.export_text.setPlaceholderText("导出的环境变量将显示在这里...")
        layout.addWidget(self.export_text)

        # 按钮布局
        btn_layout = QHBoxLayout()

        # 复制按钮
        copy_layout = QHBoxLayout()
        self.copy_btn = PushButton("复制到剪贴板")
        self.copy_btn.setIcon(FluentIcon.COPY)
        self.save_btn = PushButton("保存到文件")
        self.save_btn.setIcon(FluentIcon.SAVE)
        copy_layout.addWidget(self.copy_btn)
        copy_layout.addWidget(self.save_btn)
        copy_layout.addStretch()

        layout.addLayout(btn_layout)
        layout.addLayout(copy_layout)

        return group

    def create_stats_group(self) -> CardWidget:
        """创建统计信息组"""
        group = CardWidget()
        layout = QVBoxLayout(group)

        # 添加标题
        title = TitleLabel("统计信息")
        layout.addWidget(title)

        self.stats_label = BodyLabel("加载中...")
        self.stats_label.setWordWrap(True)
        layout.addWidget(self.stats_label)

        return group

    def setup_menu_bar(self):
        """设置菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")

        # 添加代理
        add_action = QAction("添加代理(&A)", self)
        add_action.setShortcut("Ctrl+N")
        add_action.triggered.connect(self.add_proxy)
        file_menu.addAction(add_action)

        file_menu.addSeparator()

        # 导入/导出
        import_action = QAction("导入配置(&I)", self)
        import_action.triggered.connect(self.import_config)
        file_menu.addAction(import_action)

        export_config_action = QAction("导出配置(&E)", self)
        export_config_action.triggered.connect(self.export_config)
        file_menu.addAction(export_config_action)

        file_menu.addSeparator()

        # 退出
        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 编辑菜单
        edit_menu = menubar.addMenu("编辑(&E)")

        refresh_action = QAction("刷新(&R)", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh_data)
        edit_menu.addAction(refresh_action)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")

        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def setup_status_bar(self):
        """设置状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # 状态标签
        self.status_label = BodyLabel("就绪")
        self.status_bar.addWidget(self.status_label)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)

        # 代理数量标签
        self.proxy_count_label = CaptionLabel()
        self.status_bar.addPermanentWidget(self.proxy_count_label)

    def setup_connections(self):
        """设置信号连接"""
        # 表格选择变化
        self.proxy_table.itemSelectionChanged.connect(self.on_selection_changed)
        self.proxy_table.itemDoubleClicked.connect(self.edit_proxy)

        # 搜索和筛选
        self.search_edit.textChanged.connect(self.on_search_changed)
        self.status_filter.currentTextChanged.connect(self.on_filter_changed)
        self.clear_search_btn.clicked.connect(self.clear_search)

        # 操作按钮
        self.add_btn.clicked.connect(self.add_proxy)
        self.edit_btn.clicked.connect(self.edit_proxy)
        self.remove_btn.clicked.connect(self.remove_proxy)
        self.switch_btn.clicked.connect(self.switch_proxy)
        self.toggle_btn.clicked.connect(self.toggle_proxy_status)
        self.refresh_btn.clicked.connect(self.refresh_data)

        # 导出按钮
        self.export_bash_btn.clicked.connect(lambda: self.export_environment("bash"))
        self.export_fish_btn.clicked.connect(lambda: self.export_environment("fish"))
        self.export_ps_btn.clicked.connect(lambda: self.export_environment("powershell"))
        self.export_custom_btn.clicked.connect(self.show_export_dialog)

        # 复制和保存
        self.copy_btn.clicked.connect(self.copy_export_content)
        self.save_btn.clicked.connect(self.save_export_content)

    def apply_claude_setting(self):
        """应用代理配置到Claude Code"""
        self.logger.info("开始应用Claude Code配置")
        try:
            # 获取选中的代理名称
            proxy_name = self.get_selected_proxy_name()
            if not proxy_name:
                self.logger.debug("未选中代理，尝试使用当前代理")
                # 如果没有选中代理，使用当前代理
                current = self.proxy_manager.get_current_proxy()
                if not current:
                    self.logger.warning("没有当前代理可用")
                    QMessageBox.warning(self, "应用失败", "请先选择一个代理或设置当前代理")
                    return
                proxy_name = current.name
                self.logger.debug(f"使用当前代理: {proxy_name}")
            else:
                self.logger.debug(f"使用选中代理: {proxy_name}")

            # 应用配置
            self.logger.info(f"开始应用代理 '{proxy_name}' 的配置到Claude Code")
            success = self.proxy_manager.apply_claude_code_setting(proxy_name)
            if success:
                self.logger.info(f"成功应用代理 '{proxy_name}' 到Claude Code")
                QMessageBox.information(
                    self,
                    "应用成功",
                    f"已成功将代理 '{proxy_name}' 的配置应用到 Claude Code\n\n"
                    "现在可以重启 Claude Code 应用以使用新配置。",
                )
            else:
                self.logger.error("应用Claude Code配置失败")
                QMessageBox.warning(self, "应用失败", "无法应用配置到 Claude Code")

        except Exception as e:
            self.logger.error(f"应用Claude Code配置时发生异常: {e}")
            QMessageBox.critical(
                self,
                "应用失败",
                f"应用配置时发生错误：\n{e}\n\n请检查您是否有权限访问 Claude 配置目录。",
            )

    def refresh_data(self):
        """刷新所有数据"""
        try:
            self.proxy_manager.reload_config()
            self.update_proxy_table()
            self.update_current_proxy_info()
            self.update_statistics()
            self.status_label.setText("数据已刷新")
        except Exception as e:
            self.show_error(f"刷新数据失败: {e}")

    def update_proxy_table(self):
        """更新代理表格"""
        try:
            # 获取代理列表
            proxies = self.proxy_manager.list_proxies()
            current_proxy = self.proxy_manager.get_current_proxy()
            current_name = current_proxy.name if current_proxy else None

            # 应用搜索和筛选
            filtered_proxies = self.apply_filters(proxies)

            # 设置表格行数
            self.proxy_table.setRowCount(len(filtered_proxies))

            # 填充数据
            for row, (name, proxy) in enumerate(filtered_proxies.items()):
                # 状态
                if name == current_name:
                    status_text = "● 当前"
                elif proxy.is_active:
                    status_text = "● 启用"
                else:
                    status_text = "○ 禁用"

                status_item = QTableWidgetItem(status_text)
                if name == current_name:
                    status_item.setForeground(Qt.darkGreen)
                elif proxy.is_active:
                    status_item.setForeground(Qt.blue)
                else:
                    status_item.setForeground(Qt.gray)

                self.proxy_table.setItem(row, 0, status_item)

                # 名称
                name_item = QTableWidgetItem(name)
                if name == current_name:
                    name_item.setFont(QFont("Arial", 9, QFont.Bold))
                self.proxy_table.setItem(row, 1, name_item)

                # URL
                url_item = QTableWidgetItem(proxy.base_url)
                self.proxy_table.setItem(row, 2, url_item)

                # 描述
                desc_item = QTableWidgetItem(proxy.description or "-")
                self.proxy_table.setItem(row, 3, desc_item)

                # 更新时间
                try:
                    update_time = datetime.fromisoformat(proxy.updated_at)
                    time_text = update_time.strftime("%m-%d %H:%M")
                except Exception:
                    time_text = "-"

                time_item = QTableWidgetItem(time_text)
                self.proxy_table.setItem(row, 4, time_item)

            # 更新代理数量显示
            self.proxy_count_label.setText(f"代理数量: {len(filtered_proxies)}/{len(proxies)}")

        except Exception as e:
            self.show_error(f"更新代理表格失败: {e}")

    def apply_filters(self, proxies: Dict[str, ProxyServer]) -> Dict[str, ProxyServer]:
        """应用搜索和状态筛选"""
        filtered = {}

        search_text = self.search_edit.text().lower()
        status_filter = self.status_filter.currentText()

        for name, proxy in proxies.items():
            # 状态筛选
            if status_filter == "启用" and not proxy.is_active:
                continue
            elif status_filter == "禁用" and proxy.is_active:
                continue

            # 搜索筛选
            if search_text:
                searchable_text = f"{name} {proxy.description} {' '.join(proxy.tags)}".lower()
                if search_text not in searchable_text:
                    continue

            filtered[name] = proxy

        return filtered

    def update_current_proxy_info(self):
        """更新当前代理信息显示"""
        try:
            current_proxy = self.proxy_manager.get_current_proxy()

            if current_proxy is None:
                self.current_proxy_label.setText("未设置代理")
                self.current_proxy_label.setStyleSheet("color: #999; padding: 10px;")
                self.proxy_info_text.clear()
                self.proxy_info_text.setPlaceholderText("请先选择一个代理服务器")
            else:
                self.current_proxy_label.setText(f"当前代理: {current_proxy.name}")
                self.current_proxy_label.setStyleSheet(
                    "color: #2E8B57; font-weight: bold; padding: 10px;"
                )

                # 格式化代理信息
                info_text = f"""
<b>名称:</b> {current_proxy.name}<br>
<b>URL:</b> {current_proxy.base_url}<br>
<b>状态:</b> {"启用" if current_proxy.is_active else "禁用"}<br>
<b>描述:</b> {current_proxy.description or "无"}<br>
<b>标签:</b> {", ".join(current_proxy.tags) if current_proxy.tags else "无"}<br>
<b>创建时间:</b> {self.format_datetime(current_proxy.created_at)}<br>
<b>更新时间:</b> {self.format_datetime(current_proxy.updated_at)}
                """.strip()

                self.proxy_info_text.setHtml(info_text)

        except Exception as e:
            self.show_error(f"更新当前代理信息失败: {e}")

    def update_statistics(self):
        """更新统计信息"""
        try:
            status = self.proxy_manager.get_status()

            # 计算未启用代理数量
            inactive_proxies = status["total_proxies"] - status["active_proxies"]

            # 获取所有代理的标签分布
            tag_distribution = {}
            all_proxies = self.proxy_manager.list_proxies()
            for proxy in all_proxies.values():
                for tag in proxy.tags:
                    tag_distribution[tag] = tag_distribution.get(tag, 0) + 1

            stats_text = f"""
<b>总代理数量:</b> {status["total_proxies"]}<br>
<b>活跃代理:</b> {status["active_proxies"]}<br>
<b>未启用代理:</b> {inactive_proxies}<br>
<b>配置版本:</b> {status["config_version"]}<br>
<b>最后更新:</b> {self.format_datetime(status["config_updated_at"])}
            """.strip()

            if tag_distribution:
                stats_text += "<br><br><b>标签分布:</b><br>"
                for tag, count in tag_distribution.items():
                    stats_text += f"• {tag}: {count}<br>"

            self.stats_label.setText(stats_text)

        except Exception as e:
            self.show_error(f"更新统计信息失败: {e}")

    def format_datetime(self, iso_string: str) -> str:
        """格式化日期时间"""
        try:
            dt = datetime.fromisoformat(iso_string)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return iso_string

    # 槽函数实现继续在下一部分...

    def on_selection_changed(self):
        """表格选择变化处理"""
        selected_rows = self.proxy_table.selectionModel().selectedRows()
        has_selection = len(selected_rows) > 0

        # 启用/禁用按钮
        self.edit_btn.setEnabled(has_selection)
        self.remove_btn.setEnabled(has_selection)
        self.switch_btn.setEnabled(has_selection)
        self.toggle_btn.setEnabled(has_selection)

    def on_search_changed(self):
        """搜索文本变化处理"""
        self.update_proxy_table()

    def on_filter_changed(self):
        """筛选条件变化处理"""
        self.update_proxy_table()

    def clear_search(self):
        """清除搜索条件"""
        self.search_edit.clear()
        self.status_filter.setCurrentIndex(0)

    def get_selected_proxy_name(self) -> Optional[str]:
        """获取选中的代理名称"""
        selected_rows = self.proxy_table.selectionModel().selectedRows()
        if not selected_rows:
            return None

        row = selected_rows[0].row()
        name_item = self.proxy_table.item(row, 1)
        return name_item.text() if name_item else None

    # 代理操作方法
    def add_proxy(self):
        """添加代理"""
        self.logger.info("开始添加新代理")
        dialog = AddProxyDialog(self)
        if dialog.exec() == AddProxyDialog.Accepted:
            proxy_data = dialog.get_proxy_data()
            self.logger.debug(f"获取代理数据: {proxy_data['name']}")
            try:
                # 直接传递参数给add_proxy方法
                proxy = self.proxy_manager.add_proxy(
                    name=proxy_data["name"],
                    base_url=proxy_data["base_url"],
                    api_key=proxy_data["api_key"],
                    description=proxy_data.get("description", ""),
                    tags=proxy_data.get("tags", []),
                    is_active=proxy_data.get("is_active", True),
                    set_as_current=proxy_data.get("set_as_current", False),
                )
                self.logger.info(f"代理 '{proxy.name}' 添加成功")
                self.refresh_data()
                self.status_label.setText(f"代理 '{proxy.name}' 添加成功")
                self.proxy_added.emit(proxy.name)
            except Exception as e:
                self.logger.error(f"添加代理失败: {e}")
                self.show_error(f"添加代理失败: {e}")
        else:
            self.logger.debug("用户取消了添加代理操作")

    def edit_proxy(self):
        """编辑代理"""
        proxy_name = self.get_selected_proxy_name()
        if not proxy_name:
            return

        try:
            proxy = self.proxy_manager.get_proxy(proxy_name)
            dialog = EditProxyDialog(proxy, self)
            if dialog.exec() == EditProxyDialog.Accepted:
                update_data = dialog.get_update_data()
                new_name = update_data.pop("name", proxy_name)

                # 如果名称发生了变化，需要先删除旧代理再添加新代理
                if new_name != proxy_name:
                    # 先检查原代理是否为当前代理
                    current_proxy = self.proxy_manager.get_current_proxy()
                    was_current = current_proxy and current_proxy.name == proxy_name

                    # 删除旧代理
                    self.proxy_manager.remove_proxy(proxy_name)
                    # 添加新代理
                    self.proxy_manager.add_proxy(
                        name=new_name,
                        base_url=update_data["base_url"],
                        api_key=update_data["api_key"],
                        description=update_data["description"],
                        tags=update_data["tags"],
                        is_active=update_data["is_active"],
                    )
                    # 如果原代理是当前代理，切换到新名称
                    if was_current:
                        self.proxy_manager.switch_proxy(new_name)
                else:
                    # 名称没有变化，直接更新
                    self.proxy_manager.update_proxy(proxy_name, **update_data)
                self.refresh_data()
                self.status_label.setText(f"代理 '{new_name}' 更新成功")
        except Exception as e:
            self.show_error(f"编辑代理失败: {e}")

    def remove_proxy(self):
        """删除代理"""
        proxy_name = self.get_selected_proxy_name()
        if not proxy_name:
            return

        # 确认删除
        if ConfirmDialog.confirm(self, "确认删除", f"确定要删除 '{proxy_name}' 吗?"):
            try:
                self.proxy_manager.remove_proxy(proxy_name)
                self.refresh_data()
                self.status_label.setText(f"'{proxy_name}' 删除成功")
                self.proxy_removed.emit(proxy_name)
            except Exception as e:
                self.show_error(f"删除失败: {e}")

    def switch_proxy(self):
        """切换代理"""
        proxy_name = self.get_selected_proxy_name()
        if not proxy_name:
            return

        try:
            self.proxy_manager.switch_proxy(proxy_name)
            self.refresh_data()
            self.status_label.setText(f"已切换到: {proxy_name}")
            self.proxy_changed.emit(proxy_name)
        except Exception as e:
            self.show_error(f"切换失败: {e}")

    def toggle_proxy_status(self):
        """切换代理启用状态"""
        proxy_name = self.get_selected_proxy_name()
        if not proxy_name:
            return

        try:
            # 获取当前代理状态
            proxy = self.proxy_manager.get_proxy(proxy_name)
            # 切换状态
            new_status = not proxy.is_active
            # 更新代理状态
            self.proxy_manager.update_proxy(proxy_name, is_active=new_status)
            self.refresh_data()
            status_text = "启用" if new_status else "禁用"
            self.status_label.setText(f"'{proxy_name}' 已{status_text}")
        except Exception as e:
            self.show_error(f"切换代理状态失败: {e}")

    # 导出功能
    def export_environment(self, shell_type: str):
        """导出环境变量"""
        try:
            export_format = ExportFormat(shell_type=shell_type)
            content = self.proxy_manager.export_environment(export_format)
            self.export_text.setPlainText(content)
            self.status_label.setText(f"已生成 {shell_type.upper()} 环境变量")
        except Exception as e:
            self.show_error(f"导出环境变量失败: {e}")

    def show_export_dialog(self):
        """显示自定义导出对话框"""
        dialog = ExportDialog(self)
        if dialog.exec() == ExportDialog.Accepted:
            export_format = dialog.get_export_format()
            try:
                content = self.proxy_manager.export_environment(export_format)
                self.export_text.setPlainText(content)
                self.status_label.setText("已生成自定义格式环境变量")
            except Exception as e:
                self.show_error(f"导出环境变量失败: {e}")

    def copy_export_content(self):
        """复制导出内容到剪贴板"""
        content = self.export_text.toPlainText()
        if not content:
            self.show_warning("没有可复制的内容")
            return

        from PySide6.QtWidgets import QApplication

        clipboard = QApplication.clipboard()
        clipboard.setText(content)
        self.status_label.setText("已复制到剪贴板")

    def save_export_content(self):
        """保存导出内容到文件"""
        content = self.export_text.toPlainText()
        if not content:
            self.show_warning("没有可保存的内容")
            return

        from PySide6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存环境变量文件",
            "claude-env.sh",
            "Shell脚本 (*.sh);;Fish脚本 (*.fish);;PowerShell脚本 (*.ps1);;所有文件 (*.*)",
        )

        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.status_label.setText(f"已保存到: {file_path}")
            except Exception as e:
                self.show_error(f"保存文件失败: {e}")

    # 菜单功能
    def import_config(self):
        """导入配置"""
        # TODO: 实现配置导入功能
        self.show_info("配置导入功能正在开发中")

    def export_config(self):
        """导出配置"""
        # TODO: 实现配置导出功能
        self.show_info("配置导出功能正在开发中")

    def show_about(self):
        """显示关于对话框"""
        dialog = AboutDialog(self)
        dialog.exec()

    def update_status(self):
        """定期更新状态"""
        try:
            # 检查配置文件是否被外部修改
            # TODO: 实现配置文件监控
            pass
        except Exception:
            pass

    # 消息显示方法
    def show_error(self, message: str):
        """显示错误消息"""
        QMessageBox.critical(self, "错误", message)
        self.status_label.setText("操作失败")

    def show_warning(self, message: str):
        """显示警告消息"""
        QMessageBox.warning(self, "警告", message)

    def show_info(self, message: str):
        """显示信息消息"""
        QMessageBox.information(self, "信息", message)

    def closeEvent(self, event):
        """窗口关闭事件"""
        # 停止定时器
        if hasattr(self, "status_timer"):
            self.status_timer.stop()

        # 确认退出
        if ConfirmDialog.confirm(self, "确认退出", "确定要退出Claude代理管理器吗?"):
            event.accept()
        else:
            event.ignore()


# 导出主窗口类
__all__ = ["MainWindow"]
