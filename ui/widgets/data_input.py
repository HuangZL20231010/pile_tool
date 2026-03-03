"""
数据输入组件

提供多行文本框让用户输入或粘贴深度和位移数据。
支持从Excel等工具复制的数据格式，以及CSV/Excel文件导入。
"""

from __future__ import annotations

from typing import List
from PyQt6 import QtCore, QtWidgets
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from core import file_importer


class DataInputGroup(QtWidgets.QGroupBox):
    """
    数据输入组件

    提供多行文本框让用户输入或粘贴深度和位移数据。
    支持从Excel等工具复制的数据格式。
    """
    # 数据变化信号，当文本框内容变化时发出
    data_changed = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        """
        初始化数据输入组件

        创建带占位符的文本编辑框，显示输入格式示例。
        """
        # 设置分组框标题，显示数据格式说明
        super().__init__("数据输入 (深度[m], 位移[mm])", parent)

        # 创建多行文本编辑框作为主要输入控件
        self.text_edit = QtWidgets.QTextEdit()
        # 设置最小高度，确保 placeholder 文本完整显示
        self.text_edit.setMinimumHeight(150)
        # 设置占位符文本，展示数据格式示例与默认数据说明
        self.text_edit.setPlaceholderText(
            "示例格式（可粘贴Excel两列，支持逗号/空格/Tab）：\n"
            "0.50  -0.29\n"
            "1.00  -0.81\n"
            "1.50  -1.06\n"
            "2.00  -0.98\n"
            "...\n\n"
            "留空则自动使用默认样例数据与参数"
        )

        # 创建导入按钮
        self.import_button = QtWidgets.QPushButton("从文件中读取（支持.csv和.xlsx）")
        self.import_button.clicked.connect(self.on_import_button_clicked)

        # 创建按钮行布局（水平布局）
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(self.import_button)
        button_layout.addStretch(1)  # 添加弹性空间，将按钮推到左侧

        # ===== 边界条件设置 =====
        # 复选框样式：蓝色边框
        checkbox_style = """
            QCheckBox::indicator {
                border: 2px solid #3b82f6;
                border-radius: 3px;
                width: 14px;
                height: 14px;
            }
            QCheckBox::indicator:checked {
                background-color: #3b82f6;
                border: 2px solid #3b82f6;
            }
        """

        # 桩顶边界条件行
        self.top_bc_checkbox = QtWidgets.QCheckBox("设置桩顶")
        self.top_bc_checkbox.setStyleSheet(checkbox_style)
        self.top_depth_input = QtWidgets.QLineEdit("0")
        self.top_depth_input.setFixedWidth(60)
        self.top_depth_input.setEnabled(False)
        self.top_disp_input = QtWidgets.QLineEdit("0")
        self.top_disp_input.setFixedWidth(60)
        self.top_disp_input.setEnabled(False)

        top_bc_layout = QtWidgets.QHBoxLayout()
        top_bc_layout.addWidget(self.top_bc_checkbox)
        top_bc_layout.addWidget(QtWidgets.QLabel("深度:"))
        top_bc_layout.addWidget(self.top_depth_input)
        top_bc_layout.addSpacing(10)
        top_bc_layout.addWidget(QtWidgets.QLabel("位移:"))
        top_bc_layout.addWidget(self.top_disp_input)
        top_bc_layout.addStretch(1)

        # 桩底边界条件行
        self.bottom_bc_checkbox = QtWidgets.QCheckBox("设置桩底")
        self.bottom_bc_checkbox.setStyleSheet(checkbox_style)
        self.bottom_depth_input = QtWidgets.QLineEdit()
        self.bottom_depth_input.setFixedWidth(60)
        self.bottom_depth_input.setPlaceholderText("m")
        self.bottom_depth_input.setEnabled(False)
        self.bottom_disp_input = QtWidgets.QLineEdit("0")
        self.bottom_disp_input.setFixedWidth(60)
        self.bottom_disp_input.setEnabled(False)

        bottom_bc_layout = QtWidgets.QHBoxLayout()
        bottom_bc_layout.addWidget(self.bottom_bc_checkbox)
        bottom_bc_layout.addWidget(QtWidgets.QLabel("深度:"))
        bottom_bc_layout.addWidget(self.bottom_depth_input)
        bottom_bc_layout.addSpacing(10)
        bottom_bc_layout.addWidget(QtWidgets.QLabel("位移:"))
        bottom_bc_layout.addWidget(self.bottom_disp_input)
        bottom_bc_layout.addStretch(1)

        # 连接复选框信号
        self.top_bc_checkbox.toggled.connect(self._on_top_bc_toggled)
        self.bottom_bc_checkbox.toggled.connect(self._on_bottom_bc_toggled)

        # 连接文本变化信号
        self.text_edit.textChanged.connect(self.data_changed)

        # 设置垂直布局
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.text_edit)
        layout.addLayout(button_layout)
        layout.addLayout(top_bc_layout)
        layout.addLayout(bottom_bc_layout)
        self.setLayout(layout)

    def on_import_button_clicked(self):
        """
        处理导入按钮点击事件

        打开文件选择对话框，允许用户选择CSV或Excel文件。
        读取文件内容并将其格式化后填充到文本编辑框中。
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择数据文件",
            "",
            "数据文件 (*.csv *.xlsx);;CSV文件 (*.csv);;Excel文件 (*.xlsx);;所有文件 (*.*)"
        )

        if not file_path:
            return

        try:
            depths, disps = file_importer.load_data_from_file(file_path)
            formatted_text = self._format_data_to_text(depths, disps)
            self.text_edit.setPlainText(formatted_text)

            QMessageBox.information(
                self,
                "导入成功",
                f"成功导入 {len(depths)} 组数据"
            )

        except FileNotFoundError:
            QMessageBox.warning(self, "错误", "文件未找到")
        except ValueError as e:
            QMessageBox.warning(self, "错误", f"数据格式错误: {str(e)}")
        except PermissionError:
            QMessageBox.warning(self, "错误", "无法访问文件（权限不足或文件被占用）")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"导入失败: {str(e)}")

    def _format_data_to_text(self, depths: List[float], disps: List[float]) -> str:
        """
        将深度和位移数据格式化为文本

        Args:
            depths (List[float]): 深度列表（米）
            disps (List[float]): 位移列表（毫米）

        Returns:
            str: 格式化后的文本，每行格式为 "深度\\t位移\\n"
        """
        lines = []
        for depth, disp in zip(depths, disps):
            lines.append(f"{depth}\t{disp}")
        return "\n".join(lines)

    def _on_top_bc_toggled(self, checked: bool):
        """桩顶边界条件复选框切换处理"""
        self.top_depth_input.setEnabled(checked)
        self.top_disp_input.setEnabled(checked)
        if not checked and self.bottom_bc_checkbox.isChecked():
            self.bottom_bc_checkbox.setChecked(False)

    def _on_bottom_bc_toggled(self, checked: bool):
        """桩底边界条件复选框切换处理"""
        self.bottom_depth_input.setEnabled(checked)
        self.bottom_disp_input.setEnabled(checked)
        if checked and not self.top_bc_checkbox.isChecked():
            self.top_bc_checkbox.setChecked(True)

    def get_boundary_conditions(self) -> dict:
        """
        获取边界条件设置

        Returns:
            dict: 边界条件字典
        """
        result = {
            'top_enabled': self.top_bc_checkbox.isChecked(),
            'top_depth': 0.0,
            'top_disp': 0.0,
            'bottom_enabled': self.bottom_bc_checkbox.isChecked(),
            'bottom_depth': 0.0,
            'bottom_disp': 0.0,
        }

        if result['top_enabled']:
            try:
                result['top_depth'] = float(self.top_depth_input.text())
            except ValueError:
                result['top_depth'] = 0.0
            try:
                result['top_disp'] = float(self.top_disp_input.text())
            except ValueError:
                result['top_disp'] = 0.0

        if result['bottom_enabled']:
            try:
                result['bottom_depth'] = float(self.bottom_depth_input.text())
            except ValueError:
                result['bottom_depth'] = 0.0
            try:
                result['bottom_disp'] = float(self.bottom_disp_input.text())
            except ValueError:
                result['bottom_disp'] = 0.0

        return result
