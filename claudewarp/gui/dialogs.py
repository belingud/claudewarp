"""
GUI对话框组件

提供各种对话框窗口，包括添加代理、编辑代理、确认删除等。
"""

from pathlib import Path
from typing import Any, Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QProgressDialog,
    QVBoxLayout,
)

# PyQt-Fluent-Widgets imports
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    CheckBox,
    ComboBox,
    LineEdit,
    PrimaryPushButton,
    TextEdit,
    TitleLabel,
)

from claudewarp.core.models import ExportFormat, ProxyServer
from claudewarp.util import format_validation_error


def get_app_icon() -> QIcon:
    """获取应用程序图标"""
    try:
        icon_path = Path(__file__).parent / "resources" / "icons" / "claudewarp.ico"
        if icon_path.exists():
            return QIcon(str(icon_path))
    except Exception:
        pass
    return QIcon()  # 返回空图标作为后备


class BaseProxyDialog(QDialog):
    """代理对话框基类，封装共同功能"""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(450, 350)
        self.setModal(True)
        self.setWindowIcon(get_app_icon())

        # 初始化UI组件
        self.name_edit = None
        self.url_edit = None
        self.auth_method_combo = None
        self.credential_edit = None
        self.show_key_check = None
        self.desc_edit = None
        self.tags_edit = None
        self.active_check = None
        self.bigmodel_edit = None
        self.smallmodel_edit = None
        self.button_box = None
        self._input_min_width = 300

        self.setup_ui()
        self.setup_connections()
    
    def set_input_min_width(self, edit: LineEdit):
        """设置输入框最小宽度"""
        edit.setMinimumWidth(self._input_min_width)

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 表单布局
        form_layout = QFormLayout()

        # 设置表单布局属性以优化空间使用
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        form_layout.setHorizontalSpacing(10)
        form_layout.setVerticalSpacing(8)

        # 名称
        self.name_edit = LineEdit()
        self.name_edit.setPlaceholderText("输入代理名称，如: proxy-cn")
        self.set_input_min_width(self.name_edit)
        form_layout.addRow("代理名称 *:", self.name_edit)

        # URL
        self.url_edit = LineEdit()
        self.url_edit.setPlaceholderText("输入代理URL，如: https://api.example.com/")
        self.set_input_min_width(self.url_edit)
        form_layout.addRow("代理URL *:", self.url_edit)

        # 认证方式
        self.auth_method_combo = ComboBox()
        self.auth_method_combo.addItems(["API KEY", "AUTH TOKEN", "API KEY HELPER"])
        self.set_input_min_width(self.auth_method_combo)
        form_layout.addRow("认证方式 *:", self.auth_method_combo)

        # 凭据
        self.credential_edit = LineEdit()
        self.credential_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.credential_edit.setPlaceholderText("选择认证方式后输入凭据")
        self.set_input_min_width(self.credential_edit)
        form_layout.addRow("凭据 *:", self.credential_edit)

        # 显示密钥复选框
        self.show_key_check = CheckBox("显示密钥")
        form_layout.addRow("", self.show_key_check)

        # 描述
        self.desc_edit = LineEdit()
        self.desc_edit.setPlaceholderText("输入描述信息（可选）")
        self.set_input_min_width(self.desc_edit)
        form_layout.addRow("描述:", self.desc_edit)

        # 标签
        self.tags_edit = LineEdit()
        self.tags_edit.setPlaceholderText("输入标签，用逗号分隔（可选）")
        self.set_input_min_width(self.tags_edit)
        form_layout.addRow("标签:", self.tags_edit)

        # 启用状态
        self.active_check = CheckBox("启用此代理")
        self.active_check.setChecked(True)
        form_layout.addRow("", self.active_check)

        # 模型配置分割线
        model_line = QFrame()
        model_line.setFrameShape(QFrame.Shape.HLine)
        model_line.setFrameShadow(QFrame.Shadow.Sunken)
        form_layout.addRow("", model_line)

        # 模型配置标题
        model_title = BodyLabel("模型配置 (可选)")
        model_title.setStyleSheet("font-weight: bold; color: #333;")
        form_layout.addRow("", model_title)

        # 大模型
        self.bigmodel_edit = LineEdit()
        self.bigmodel_edit.setPlaceholderText("如: claude-sonnet-4-20250514")
        self.set_input_min_width(self.bigmodel_edit)
        form_layout.addRow("大模型:", self.bigmodel_edit)

        # 小模型
        self.smallmodel_edit = LineEdit()
        self.smallmodel_edit.setPlaceholderText("如: claude-3-5-haiku-20241022")
        self.set_input_min_width(self.smallmodel_edit)
        form_layout.addRow("小模型:", self.smallmodel_edit)

        layout.addLayout(form_layout)

        # 添加子类自定义内容
        self.add_custom_ui(layout)

        # 按钮
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        layout.addWidget(self.button_box)

        # 设置按钮文本
        self.setup_button_texts()

        # 连接信号
        self.button_box.accepted.connect(self.accept_dialog)
        self.button_box.rejected.connect(self.reject)

    def add_custom_ui(self, layout):
        """子类可重写此方法添加自定义UI元素"""
        pass

    def setup_button_texts(self):
        """子类可重写此方法设置按钮文本"""
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText("确定")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")

    def setup_connections(self):
        """设置信号连接"""
        # 显示/隐藏密钥
        self.show_key_check.toggled.connect(self.toggle_key_visibility)

        # 认证方式切换
        self.auth_method_combo.currentTextChanged.connect(self.on_auth_method_changed)

        # 实时验证
        self.name_edit.textChanged.connect(self.validate_input)
        self.url_edit.textChanged.connect(self.validate_input)
        self.credential_edit.textChanged.connect(self.validate_input)

        # 初始验证
        self.validate_input()

    def toggle_key_visibility(self, visible: bool):
        """切换密钥显示状态"""
        if visible:
            self.credential_edit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.credential_edit.setEchoMode(QLineEdit.EchoMode.Password)

    def on_auth_method_changed(self, auth_method: str):
        """处理认证方式切换"""
        placeholders = {
            "API KEY": "输入API Key",
            "AUTH TOKEN": "输入AuthToken",
            "API KEY HELPER": "输入API Key Helper",
        }
        self.credential_edit.setPlaceholderText(placeholders.get(auth_method, "输入凭据"))
        self.validate_input()

    def validate_input(self):
        """验证输入"""
        name = self.name_edit.text().strip()
        url = self.url_edit.text().strip()
        credential = self.credential_edit.text().strip()

        # 检查必填字段
        valid = bool(name and url and credential)

        # 启用/禁用确定按钮
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(valid)

    def accept_dialog(self):
        """确认对话框 - 子类应重写此方法"""
        raise NotImplementedError("子类必须实现 accept_dialog 方法")

    def get_auth_credentials(self) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """获取认证凭据"""
        auth_method = self.auth_method_combo.currentText()
        credential = self.credential_edit.text().strip()

        api_key = credential if auth_method == "API KEY" else None
        auth_token = credential if auth_method == "AUTH TOKEN" else None
        api_key_helper = credential if auth_method == "API KEY HELPER" else None

        return api_key, auth_token, api_key_helper

    def get_common_data(self) -> Dict[str, Any]:
        """获取通用数据"""
        tags_text = self.tags_edit.text().strip()
        tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()] if tags_text else []

        api_key, auth_token, api_key_helper = self.get_auth_credentials()

        return {
            "name": self.name_edit.text().strip(),
            "base_url": self.url_edit.text().strip(),
            "api_key": api_key,
            "auth_token": auth_token,
            "api_key_helper": api_key_helper,
            "description": self.desc_edit.text().strip(),
            "tags": tags,
            "is_active": self.active_check.isChecked(),
            "bigmodel": self.bigmodel_edit.text().strip() or None,
            "smallmodel": self.smallmodel_edit.text().strip() or None,
        }


class AddProxyDialog(BaseProxyDialog):
    """添加代理对话框"""

    def __init__(self, parent=None):
        super().__init__("添加代理服务器", parent)

    def add_custom_ui(self, layout):
        """添加自定义UI元素"""
        # 提示信息
        info_label = BodyLabel("* 表示必填字段")
        info_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(info_label)

    def setup_button_texts(self):
        """设置按钮文本"""
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText("添加")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")

    def accept_dialog(self):
        """确认对话框"""
        try:
            # 获取并验证数据
            proxy_data = self.get_common_data()
            print(f"proxy_data: {proxy_data}")

            # 使用Pydantic验证数据
            ProxyServer(**proxy_data)

            # 验证通过，接受对话框
            self.accept()

        except Exception as e:
            err_msg = format_validation_error(e)
            QMessageBox.critical(self, "输入错误", f"数据验证失败:\n{err_msg}")


class EditProxyDialog(BaseProxyDialog):
    """编辑代理对话框"""

    def __init__(self, proxy: ProxyServer, parent=None):
        self.original_proxy = proxy
        super().__init__(f"编辑代理: {proxy.name}", parent)
        self.load_proxy_data()

    def setup_button_texts(self):
        """设置按钮文本"""
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText("更新")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")

    def load_proxy_data(self):
        """加载代理数据"""
        self.name_edit.setText(self.original_proxy.name)
        self.url_edit.setText(self.original_proxy.base_url)
        self.desc_edit.setText(self.original_proxy.description)
        self.tags_edit.setText(", ".join(self.original_proxy.tags))
        self.active_check.setChecked(self.original_proxy.is_active)
        self.bigmodel_edit.setText(self.original_proxy.bigmodel or "")
        self.smallmodel_edit.setText(self.original_proxy.smallmodel or "")

        # 设置认证方式和凭据
        if self.original_proxy.auth_token:
            self.auth_method_combo.setCurrentText("AUTH TOKEN")
            self.credential_edit.setText(self.original_proxy.auth_token)
        elif self.original_proxy.api_key_helper:
            self.auth_method_combo.setCurrentText("API KEY HELPER")
            self.credential_edit.setText(self.original_proxy.api_key_helper)
        else:
            self.auth_method_combo.setCurrentText("API KEY")
            self.credential_edit.setText(self.original_proxy.api_key or "")


    def accept_dialog(self):
        """确认对话框"""
        try:
            # 获取并验证数据
            update_data = self.get_common_data()

            # 创建临时对象验证数据
            temp_data = self.original_proxy.model_dump()
            temp_data.update(update_data)
            ProxyServer(**temp_data)

            # 验证通过，接受对话框
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "输入错误", f"数据验证失败:\\n{e}")


class ConfirmDialog(QDialog):
    """确认对话框"""

    def __init__(self, title: str, message: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumSize(300, 150)
        self.setWindowIcon(get_app_icon())

        layout = QVBoxLayout(self)

        # 消息标签
        message_label = BodyLabel(message)
        message_label.setWordWrap(True)
        layout.addWidget(message_label)

        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.No
        )
        button_box.button(QDialogButtonBox.StandardButton.Yes).setText("确定")
        button_box.button(QDialogButtonBox.StandardButton.No).setText("取消")

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addWidget(button_box)

    @staticmethod
    def confirm(parent, title: str, message: str) -> bool:
        """显示确认对话框"""
        dialog = ConfirmDialog(title, message, parent)
        return dialog.exec() == QDialog.DialogCode.Accepted


class ExportDialog(QDialog):
    """环境变量导出对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("自定义")
        self.setMinimumSize(450, 300)
        self.setModal(True)
        self.setWindowIcon(get_app_icon())

        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 表单布局
        form_layout = QFormLayout()

        # 设置表单布局属性以优化空间使用
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        form_layout.setHorizontalSpacing(10)
        form_layout.setVerticalSpacing(8)

        # Shell类型
        self.shell_combo = ComboBox()
        self.shell_combo.addItems(["bash", "fish", "powershell", "zsh"])
        self.shell_combo.setMinimumWidth(200)
        form_layout.addRow("Shell类型:", self.shell_combo)

        # 环境变量前缀
        self.prefix_edit = LineEdit()
        self.prefix_edit.setText("ANTHROPIC_")
        self.prefix_edit.setMinimumWidth(200)
        form_layout.addRow("变量前缀:", self.prefix_edit)

        # 导出所有代理
        self.export_all_check = CheckBox("导出所有代理（默认只导出当前代理）")
        form_layout.addRow("", self.export_all_check)

        layout.addLayout(form_layout)

        # 预览区域
        preview_group = CardWidget()
        preview_layout = QVBoxLayout(preview_group)

        preview_title = TitleLabel("预览")
        preview_layout.addWidget(preview_title)

        self.preview_text = TextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(100)
        preview_layout.addWidget(self.preview_text)

        layout.addWidget(preview_group)

        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText("导出")
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addWidget(button_box)

        # 更新预览
        self.update_preview()

    def setup_connections(self):
        """设置信号连接"""
        self.shell_combo.currentTextChanged.connect(self.update_preview)
        self.prefix_edit.textChanged.connect(self.update_preview)
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

            self.preview_text.setPlainText(example)

        except Exception as e:
            self.preview_text.setPlainText(f"预览错误: {e}")

    def get_export_format(self) -> ExportFormat:
        """获取导出格式"""
        return ExportFormat(
            shell_type=self.shell_combo.currentText(),
            include_comments=False,  # 固定为 False，不包含注释
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
        self.setWindowIcon(get_app_icon())

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

        app_name = TitleLabel("Claude中转站管理工具")
        title_info.addWidget(app_name)

        version_label = BodyLabel("版本 0.1.0")
        version_label.setStyleSheet("color: #666;")
        title_info.addWidget(version_label)

        title_layout.addLayout(title_info)
        title_layout.addStretch()

        layout.addLayout(title_layout)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        # 描述信息
        description = BodyLabel(
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
        description.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(description)

        layout.addStretch()

        # 关闭按钮
        close_btn = PrimaryPushButton("关闭")
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
        self.setCancelButton(None)  # type:ignore

    def update_progress(self, value: int, message: Optional[str] = None):
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
