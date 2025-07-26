"""
GUI对话框组件

提供各种对话框窗口，包括添加代理、编辑代理、确认删除等。
"""

from typing import Any, Dict

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from claudewarp.core.models import ExportFormat, ProxyServer


class AddProxyDialog(QDialog):
    """添加代理对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加代理服务器")
        self.setMinimumSize(400, 300)
        self.setModal(True)

        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 表单布局
        form_layout = QFormLayout()

        # 名称
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("输入代理名称，如: proxy-cn")
        form_layout.addRow("代理名称 *:", self.name_edit)

        # URL
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("输入代理URL，如: https://api.example.com/")
        form_layout.addRow("代理URL *:", self.url_edit)

        # API密钥
        self.key_edit = QLineEdit()
        self.key_edit.setEchoMode(QLineEdit.Password)
        self.key_edit.setPlaceholderText("输入API密钥")
        form_layout.addRow("API密钥 *:", self.key_edit)

        # 显示密钥复选框
        self.show_key_check = QCheckBox("显示密钥")
        form_layout.addRow("", self.show_key_check)

        # 描述
        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("输入描述信息（可选）")
        form_layout.addRow("描述:", self.desc_edit)

        # 标签
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("输入标签，用逗号分隔（可选）")
        form_layout.addRow("标签:", self.tags_edit)

        # 启用状态
        self.active_check = QCheckBox("启用此代理")
        self.active_check.setChecked(True)
        form_layout.addRow("", self.active_check)

        layout.addLayout(form_layout)

        # 提示信息
        info_label = QLabel("* 表示必填字段")
        info_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(info_label)

        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(button_box)

        # 设置按钮文本
        button_box.button(QDialogButtonBox.Ok).setText("添加")
        button_box.button(QDialogButtonBox.Cancel).setText("取消")

        # 连接信号
        button_box.accepted.connect(self.accept_dialog)
        button_box.rejected.connect(self.reject)

        # 保存引用
        self.button_box = button_box

    def setup_connections(self):
        """设置信号连接"""
        # 显示/隐藏密钥
        self.show_key_check.toggled.connect(self.toggle_key_visibility)

        # 实时验证
        self.name_edit.textChanged.connect(self.validate_input)
        self.url_edit.textChanged.connect(self.validate_input)
        self.key_edit.textChanged.connect(self.validate_input)

        # 初始验证
        self.validate_input()

    def toggle_key_visibility(self, visible: bool):
        """切换密钥显示状态"""
        if visible:
            self.key_edit.setEchoMode(QLineEdit.Normal)
        else:
            self.key_edit.setEchoMode(QLineEdit.Password)

    def validate_input(self):
        """验证输入"""
        name = self.name_edit.text().strip()
        url = self.url_edit.text().strip()
        key = self.key_edit.text().strip()

        # 检查必填字段
        valid = bool(name and url and key)

        # 启用/禁用确定按钮
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(valid)

    def accept_dialog(self):
        """确认对话框"""
        try:
            # 获取并验证数据
            proxy_data = self.get_proxy_data()

            # 使用Pydantic验证数据
            ProxyServer(**proxy_data)

            # 验证通过，接受对话框
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "输入错误", f"数据验证失败:\\n{e}")

    def get_proxy_data(self) -> Dict[str, Any]:
        """获取代理数据"""
        tags_text = self.tags_edit.text().strip()
        tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()] if tags_text else []

        return {
            "name": self.name_edit.text().strip(),
            "base_url": self.url_edit.text().strip(),
            "api_key": self.key_edit.text().strip(),
            "description": self.desc_edit.text().strip(),
            "tags": tags,
            "is_active": self.active_check.isChecked(),
        }


class EditProxyDialog(QDialog):
    """编辑代理对话框"""

    def __init__(self, proxy: ProxyServer, parent=None):
        super().__init__(parent)
        self.original_proxy = proxy
        self.setWindowTitle(f"编辑代理: {proxy.name}")
        self.setMinimumSize(400, 300)
        self.setModal(True)

        self.setup_ui()
        self.setup_connections()
        self.load_proxy_data()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 表单布局
        form_layout = QFormLayout()

        # 名称
        self.name_edit = QLineEdit()
        form_layout.addRow("代理名称 *:", self.name_edit)

        # URL
        self.url_edit = QLineEdit()
        form_layout.addRow("代理URL *:", self.url_edit)

        # API密钥
        self.key_edit = QLineEdit()
        self.key_edit.setEchoMode(QLineEdit.Password)
        form_layout.addRow("API密钥 *:", self.key_edit)

        # 显示密钥复选框
        self.show_key_check = QCheckBox("显示密钥")
        form_layout.addRow("", self.show_key_check)

        # 描述
        self.desc_edit = QLineEdit()
        form_layout.addRow("描述:", self.desc_edit)

        # 标签
        self.tags_edit = QLineEdit()
        form_layout.addRow("标签:", self.tags_edit)

        # 启用状态
        self.active_check = QCheckBox("启用此代理")
        form_layout.addRow("", self.active_check)

        layout.addLayout(form_layout)

        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(button_box)

        # 设置按钮文本
        button_box.button(QDialogButtonBox.Ok).setText("更新")
        button_box.button(QDialogButtonBox.Cancel).setText("取消")

        # 连接信号
        button_box.accepted.connect(self.accept_dialog)
        button_box.rejected.connect(self.reject)

        # 保存引用
        self.button_box = button_box

    def setup_connections(self):
        """设置信号连接"""
        # 显示/隐藏密钥
        self.show_key_check.toggled.connect(self.toggle_key_visibility)

        # 实时验证
        self.name_edit.textChanged.connect(self.validate_input)
        self.url_edit.textChanged.connect(self.validate_input)
        self.key_edit.textChanged.connect(self.validate_input)

    def load_proxy_data(self):
        """加载代理数据"""
        self.name_edit.setText(self.original_proxy.name)
        self.url_edit.setText(self.original_proxy.base_url)
        self.key_edit.setText(self.original_proxy.api_key)
        self.desc_edit.setText(self.original_proxy.description)
        self.tags_edit.setText(", ".join(self.original_proxy.tags))
        self.active_check.setChecked(self.original_proxy.is_active)

    def toggle_key_visibility(self, visible: bool):
        """切换密钥显示状态"""
        if visible:
            self.key_edit.setEchoMode(QLineEdit.Normal)
        else:
            self.key_edit.setEchoMode(QLineEdit.Password)

    def validate_input(self):
        """验证输入"""
        name = self.name_edit.text().strip()
        url = self.url_edit.text().strip()
        key = self.key_edit.text().strip()

        # 检查必填字段
        valid = bool(name and url and key)

        # 启用/禁用确定按钮
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(valid)

    def accept_dialog(self):
        """确认对话框"""
        try:
            # 获取并验证数据
            update_data = self.get_update_data()

            # 创建临时对象验证数据
            temp_data = self.original_proxy.dict()
            temp_data.update(update_data)
            ProxyServer(**temp_data)

            # 验证通过，接受对话框
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "输入错误", f"数据验证失败:\\n{e}")

    def get_update_data(self) -> Dict[str, Any]:
        """获取更新数据"""
        tags_text = self.tags_edit.text().strip()
        tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()] if tags_text else []

        return {
            "name": self.name_edit.text().strip(),
            "base_url": self.url_edit.text().strip(),
            "api_key": self.key_edit.text().strip(),
            "description": self.desc_edit.text().strip(),
            "tags": tags,
            "is_active": self.active_check.isChecked(),
        }


class ConfirmDialog(QDialog):
    """确认对话框"""

    def __init__(self, title: str, message: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumSize(300, 150)

        layout = QVBoxLayout(self)

        # 消息标签
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        layout.addWidget(message_label)

        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Yes | QDialogButtonBox.No)
        button_box.button(QDialogButtonBox.Yes).setText("确定")
        button_box.button(QDialogButtonBox.No).setText("取消")

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addWidget(button_box)

    @staticmethod
    def confirm(parent, title: str, message: str) -> bool:
        """显示确认对话框"""
        dialog = ConfirmDialog(title, message, parent)
        return dialog.exec() == QDialog.Accepted


class ExportDialog(QDialog):
    """环境变量导出对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("自定义环境变量导出")
        self.setMinimumSize(400, 250)
        self.setModal(True)

        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 表单布局
        form_layout = QFormLayout()

        # Shell类型
        self.shell_combo = QComboBox()
        self.shell_combo.addItems(["bash", "fish", "powershell", "zsh"])
        form_layout.addRow("Shell类型:", self.shell_combo)

        # 环境变量前缀
        self.prefix_edit = QLineEdit("ANTHROPIC_")
        form_layout.addRow("变量前缀:", self.prefix_edit)

        # 包含注释
        self.comments_check = QCheckBox("包含注释")
        self.comments_check.setChecked(True)
        form_layout.addRow("", self.comments_check)

        # 导出所有代理
        self.export_all_check = QCheckBox("导出所有代理（默认只导出当前代理）")
        form_layout.addRow("", self.export_all_check)

        layout.addLayout(form_layout)

        # 预览区域
        preview_group = QGroupBox("预览")
        preview_layout = QVBoxLayout(preview_group)

        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(100)
        preview_layout.addWidget(self.preview_text)

        layout.addWidget(preview_group)

        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Ok).setText("导出")
        button_box.button(QDialogButtonBox.Cancel).setText("取消")

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addWidget(button_box)

        # 更新预览
        self.update_preview()

    def setup_connections(self):
        """设置信号连接"""
        self.shell_combo.currentTextChanged.connect(self.update_preview)
        self.prefix_edit.textChanged.connect(self.update_preview)
        self.comments_check.toggled.connect(self.update_preview)
        self.export_all_check.toggled.connect(self.update_preview)

    def update_preview(self):
        """更新预览"""
        try:
            export_format = self.get_export_format()

            # 生成示例内容
            if export_format.shell_type == "bash":
                example = f'export {export_format.prefix}BASE_URL="https://example.com/"'
            elif export_format.shell_type == "fish":
                example = f'set -x {export_format.prefix}BASE_URL "https://example.com/"'
            elif export_format.shell_type == "powershell":
                example = f'$env:{export_format.prefix}BASE_URL="https://example.com/"'
            else:
                example = f'export {export_format.prefix}BASE_URL="https://example.com/"'

            if export_format.include_comments:
                example = f"# 示例环境变量\n{example}"

            self.preview_text.setPlainText(example)

        except Exception as e:
            self.preview_text.setPlainText(f"预览错误: {e}")

    def get_export_format(self) -> ExportFormat:
        """获取导出格式"""
        return ExportFormat(
            shell_type=self.shell_combo.currentText(),
            include_comments=self.comments_check.isChecked(),
            prefix=self.prefix_edit.text(),
            export_all=self.export_all_check.isChecked(),
        )


class AboutDialog(QDialog):
    """关于对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关于")
        self.setFixedSize(400, 300)
        self.setModal(True)

        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 应用图标和名称
        title_layout = QHBoxLayout()

        # TODO: 添加应用图标
        # icon_label = QLabel()
        # icon_pixmap = QPixmap(":/icons/app.png")
        # icon_label.setPixmap(icon_pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        # title_layout.addWidget(icon_label)

        title_info = QVBoxLayout()

        app_name = QLabel("Claude中转站管理工具")
        app_name.setFont(QFont("Arial", 16, QFont.Bold))
        title_info.addWidget(app_name)

        version_label = QLabel("版本 0.1.0")
        version_label.setStyleSheet("color: #666;")
        title_info.addWidget(version_label)

        title_layout.addLayout(title_info)
        title_layout.addStretch()

        layout.addLayout(title_layout)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        # 描述信息
        description = QLabel(
            """
一个用于管理和切换Claude API代理服务器的工具。

主要功能:
• 管理多个代理服务器配置
• 快速切换当前代理
• 导出环境变量设置
• 跨平台支持 (Windows/macOS/Linux)

技术栈:
• Python 3.8+
• PySide6 (Qt界面)
• Pydantic (数据验证)
• Typer (命令行界面)
        """.strip()
        )

        description.setWordWrap(True)
        description.setAlignment(Qt.AlignTop)
        layout.addWidget(description)

        layout.addStretch()

        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)


class ProgressDialog(QProgressDialog):
    """进度对话框"""

    def __init__(self, title: str, message: str, parent=None):
        super().__init__(message, "取消", 0, 100, parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumDuration(0)

        # 禁用取消按钮（根据需要）
        self.setCancelButton(None)

    def update_progress(self, value: int, message: str = None):
        """更新进度"""
        self.setValue(value)
        if message:
            self.setLabelText(message)


# 导出所有对话框类
__all__ = [
    "AddProxyDialog",
    "EditProxyDialog",
    "ConfirmDialog",
    "ExportDialog",
    "AboutDialog",
    "ProgressDialog",
]
