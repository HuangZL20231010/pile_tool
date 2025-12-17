"""
围护桩反分析工具可复用UI组件库

定义了所有用户界面组件，包括数据输入、参数设置、控制面板等。
这些组件采用模块化设计，便于维护和扩展。
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

        # 设置垂直布局
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.text_edit)
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def on_import_button_clicked(self):
        """
        处理导入按钮点击事件

        打开文件选择对话框，允许用户选择CSV或Excel文件。
        读取文件内容并将其格式化后填充到文本编辑框中。
        如果读取过程中出现错误，显示错误消息对话框。
        """
        # 打开文件选择对话框
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择数据文件",
            "",
            "数据文件 (*.csv *.xlsx);;CSV文件 (*.csv);;Excel文件 (*.xlsx);;所有文件 (*.*)"
        )

        # 如果用户取消选择，直接返回
        if not file_path:
            return

        try:
            # 从文件加载数据
            depths, disps = file_importer.load_data_from_file(file_path)

            # 格式化数据为文本
            formatted_text = self._format_data_to_text(depths, disps)

            # 填充到文本编辑框
            self.text_edit.setPlainText(formatted_text)

            # 显示成功消息（可选）
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

        将数据列表格式化为制表符分隔的文本格式，
        与现有的 parse_depth_disp() 函数兼容。

        Args:
            depths (List[float]): 深度列表（米）
            disps (List[float]): 位移列表（毫米）

        Returns:
            str: 格式化后的文本，每行格式为 "深度\t位移\n"

        Note:
            - 使用制表符作为分隔符，与 Excel 复制粘贴格式一致
            - 返回的文本可直接填充到 QTextEdit 中
        """
        lines = []
        for depth, disp in zip(depths, disps):
            lines.append(f"{depth}\t{disp}")
        return "\n".join(lines)


class ParamsGroup(QtWidgets.QGroupBox):
    """
    材料与截面参数设置组件

    整合了弹性模量输入、单位选择、截面类型选择和尺寸输入。
    根据选择的截面类型动态显示相应的尺寸输入框。
    """

    def __init__(self, parent=None):
        """
        初始化参数设置组件

        创建所有参数输入控件并安排布局。
        默认选择圆形截面，隐藏矩形尺寸输入框。
        """
        # 设置分组框标题
        super().__init__("材料与截面参数", parent)

        # 弹性模量输入框
        self.E_input = QtWidgets.QLineEdit()
        self.E_input.setPlaceholderText("E 值")

        # 弹性模量单位选择下拉框
        self.E_unit = QtWidgets.QComboBox()
        self.E_unit.addItems(["MPa", "kPa"])

        # 截面类型单选按钮
        self.circle_radio = QtWidgets.QRadioButton("圆形")
        self.rect_radio = QtWidgets.QRadioButton("矩形")
        # 默认选择圆形截面
        self.circle_radio.setChecked(True)

        # 创建按钮组确保单选行为
        self.section_group = QtWidgets.QButtonGroup(self)
        self.section_group.addButton(self.circle_radio)
        self.section_group.addButton(self.rect_radio)

        # 尺寸输入框
        self.D_input = QtWidgets.QLineEdit()
        self.D_input.setPlaceholderText("D (mm)")  # 圆形直径

        self.b_input = QtWidgets.QLineEdit()
        self.b_input.setPlaceholderText("b (mm)")  # 矩形宽度

        self.h_input = QtWidgets.QLineEdit()
        self.h_input.setPlaceholderText("h (mm)")  # 矩形高度

        # 使用网格布局排列控件
        top = QtWidgets.QGridLayout()
        # 第一行：弹性模量标签、输入框、单位选择
        top.addWidget(QtWidgets.QLabel("E:"), 0, 0)
        top.addWidget(self.E_input, 0, 1)
        top.addWidget(self.E_unit, 0, 2)

        # 第二行：截面类型选择按钮
        top.addWidget(self.circle_radio, 1, 0)
        top.addWidget(self.rect_radio, 1, 1)

        # 第三行：圆形直径输入（跨三列）
        top.addWidget(self.D_input, 2, 0, 1, 3)
        # 第四行：矩形宽度输入（跨三列）
        top.addWidget(self.b_input, 3, 0, 1, 3)
        # 第五行：矩形高度输入（跨三列）
        top.addWidget(self.h_input, 4, 0, 1, 3)

        # 设置第二列（输入框列）可伸缩
        top.setColumnStretch(1, 1)
        self.setLayout(top)

        # 根据截面类型动态显示尺寸输入
        self.circle_radio.toggled.connect(self.update_section_inputs)
        self.rect_radio.toggled.connect(self.update_section_inputs)
        self.update_section_inputs()

    def section_type(self) -> str:
        """
        获取当前选择的截面类型

        Returns:
            str: "circle" 表示圆形，"rect" 表示矩形
        """
        return "circle" if self.circle_radio.isChecked() else "rect"

    def update_section_inputs(self):
        """根据截面类型显示/隐藏对应尺寸输入框。"""
        circle = self.circle_radio.isChecked()
        self.D_input.setVisible(circle)
        self.b_input.setVisible(not circle)
        self.h_input.setVisible(not circle)


class FitControlGroup(QtWidgets.QGroupBox):
    """
    拟合控制组件

    提供多项式阶数调节滑块和计算按钮。
    当阶数改变时发出信号供其他组件响应。
    """
    # 定义信号：阶数改变时发出
    degree_changed = QtCore.pyqtSignal(int)

    def __init__(self, parent=None):
        """
        初始化拟合控制组件

        创建阶数滑块、显示标签和计算按钮。
        阶数范围限制在3-9之间，默认值为5。
        """
        # 设置分组框标题
        super().__init__("拟合控制", parent)

        # 创建水平滑块用于调节多项式阶数
        self.slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.slider.setMinimum(3)  # 最小阶数
        self.slider.setMaximum(9)  # 最大阶数
        self.slider.setValue(5)    # 默认阶数
        # 连接滑块值改变信号到自定义信号
        self.slider.valueChanged.connect(self.degree_changed)

        # 显示当前阶数的标签
        self.label = QtWidgets.QLabel("阶数: 5")

        # 创建计算按钮
        btn = QtWidgets.QPushButton("开始计算")
        self.calc_button = btn

        # 设置垂直布局
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.slider)
        layout.addWidget(btn)
        self.setLayout(layout)

        # 连接滑块到标签更新函数
        self.slider.valueChanged.connect(self._update_label)

    def _update_label(self, val: int):
        """
        更新阶数显示标签

        当滑块值改变时，更新标签文本并发出信号。

        Args:
            val (int): 新的阶数值
        """
        self.label.setText(f"阶数: {val}")
        # 发出阶数改变信号
        self.degree_changed.emit(val)


class QueryGroup(QtWidgets.QGroupBox):
    """
    任意深度查询组件

    允许用户输入特定深度，查询该点的计算结果。
    点击查询按钮时发出信号。
    """
    # 定义信号：点击查询按钮时发出
    query_clicked = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        """
        初始化查询组件

        创建深度输入框和查询按钮。
        """
        # 设置分组框标题
        super().__init__("任意深度查询", parent)

        # 创建深度输入框
        self.depth_input = QtWidgets.QLineEdit()
        self.depth_input.setPlaceholderText("深度 x (m)")

        # 创建查询按钮，点击时发出信号
        self.query_btn = QtWidgets.QPushButton("查询")
        self.query_btn.clicked.connect(self.query_clicked.emit)

        # 设置水平布局
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.depth_input)
        layout.addWidget(self.query_btn)
        self.setLayout(layout)


class StatsBar(QtWidgets.QWidget):
    """
    统计信息显示栏

    使用现代卡片式设计显示拟合统计信息和函数表达式。
    包括拟合质量指标、弯矩信息、位移函数和弯矩函数。
    """

    def __init__(self, parent=None):
        """
        初始化统计栏

        创建美观的卡片式布局，分区显示不同类型的统计信息。
        """
        super().__init__(parent)
        self.setObjectName("statsBar")

        # ========== 创建统计指标卡片 ==========
        # 拟合质量组
        quality_title = QtWidgets.QLabel("拟合质量")
        quality_title.setStyleSheet("font-weight: 600; font-size: 13px; color: #64748b;")

        self.r2_label = QtWidgets.QLabel("R² = -")
        self.r2_label.setStyleSheet("font-size: 16px; font-weight: 600; color: #0f172a;")

        self.rmse_label = QtWidgets.QLabel("RMSE = -")
        self.rmse_label.setStyleSheet("font-size: 16px; font-weight: 600; color: #0f172a;")

        quality_layout = QtWidgets.QHBoxLayout()
        quality_layout.setSpacing(32)
        quality_layout.addWidget(self.r2_label)
        quality_layout.addWidget(self.rmse_label)
        quality_layout.addStretch()

        quality_card = QtWidgets.QVBoxLayout()
        quality_card.setSpacing(8)
        quality_card.addWidget(quality_title)
        quality_card.addLayout(quality_layout)

        # 弯矩信息组
        moment_title = QtWidgets.QLabel("弯矩信息")
        moment_title.setStyleSheet("font-weight: 600; font-size: 13px; color: #64748b;")

        self.mmax_label = QtWidgets.QLabel("Mmax = -")
        self.mmax_label.setStyleSheet("font-size: 16px; font-weight: 600; color: #0f172a;")

        moment_card = QtWidgets.QVBoxLayout()
        moment_card.setSpacing(8)
        moment_card.addWidget(moment_title)
        moment_card.addWidget(self.mmax_label)

        # 第一行：质量指标和弯矩信息
        top_row = QtWidgets.QHBoxLayout()
        top_row.setSpacing(48)
        top_row.addLayout(quality_card, 1)
        top_row.addLayout(moment_card, 1)
        top_row.addStretch(2)

        # ========== 创建函数表达式卡片 ==========
        # 位移拟合函数
        disp_title = QtWidgets.QLabel("位移拟合函数 y(x)")
        disp_title.setStyleSheet(
            "font-weight: 600; font-size: 13px; color: #64748b; margin-top: 4px;"
        )

        self.poly_label = QtWidgets.QLabel("-")
        self.poly_label.setWordWrap(True)
        self.poly_label.setStyleSheet(
            "font-size: 14px; color: #1e293b; padding: 8px 12px; "
            "background-color: #fef3c7; border-radius: 6px; "
            "font-family: 'Consolas', 'Courier New', monospace;"
        )

        disp_func_layout = QtWidgets.QVBoxLayout()
        disp_func_layout.setSpacing(6)
        disp_func_layout.addWidget(disp_title)
        disp_func_layout.addWidget(self.poly_label)

        # 弯矩函数
        moment_func_title = QtWidgets.QLabel("弯矩函数 M(x) = E·I·y''(x)")
        moment_func_title.setStyleSheet(
            "font-weight: 600; font-size: 13px; color: #64748b; margin-top: 4px;"
        )

        self.moment_expr_label = QtWidgets.QLabel("-")
        self.moment_expr_label.setWordWrap(True)
        self.moment_expr_label.setStyleSheet(
            "font-size: 14px; color: #1e293b; padding: 8px 12px; "
            "background-color: #fef3c7; border-radius: 6px; "
            "font-family: 'Consolas', 'Courier New', monospace;"
        )

        moment_func_layout = QtWidgets.QVBoxLayout()
        moment_func_layout.setSpacing(6)
        moment_func_layout.addWidget(moment_func_title)
        moment_func_layout.addWidget(self.moment_expr_label)

        # 函数表达式行
        func_row = QtWidgets.QHBoxLayout()
        func_row.setSpacing(24)
        func_row.addLayout(disp_func_layout, 1)
        func_row.addLayout(moment_func_layout, 1)

        # ========== 主布局 ==========
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(16)
        main_layout.addLayout(top_row)
        main_layout.addLayout(func_row)
        self.setLayout(main_layout)

        # 设置整体卡片样式
        self.setStyleSheet(
            """
            StatsBar {
                background-color: #ffffff;
                border-top: 2px solid #e2e8f0;
            }
            """
        )

    def update_stats(
        self,
        r2: float,
        rmse_mm: float,
        mmax: float,
        poly_expr: str = "",
        moment_expr: str = "",
    ):
        """
        更新统计信息显示

        Args:
            r2 (float): 决定系数R²
            rmse_mm (float): 均方根误差（毫米）
            mmax (float): 最大弯矩值（kN·m）
            poly_expr (str): 位移拟合函数表达式，可选
            moment_expr (str): 弯矩函数表达式，可选
        """
        # 更新拟合质量指标
        self.r2_label.setText(f"R² = {r2:.4f}")

        # RMSE添加单位标注
        self.rmse_label.setText(f"RMSE = {rmse_mm:.2f} mm")

        # 更新最大弯矩，使用醒目的红色
        self.mmax_label.setText(f"Mmax = {mmax:.2f} kN·m")

        # 更新位移拟合函数表达式
        if poly_expr:
            self.poly_label.setText(poly_expr)
        else:
            self.poly_label.setText("-")

        # 更新弯矩函数表达式
        if moment_expr:
            self.moment_expr_label.setText(moment_expr)
        else:
            self.moment_expr_label.setText("-")

