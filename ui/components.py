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

    提供算法选择（多项式/三次样条/五次样条）、参数调节滑块和计算按钮。
    支持动态切换算法类型，滑块语义和范围随之变化。
    """
    # 定义信号：参数改变时发出
    degree_changed = QtCore.pyqtSignal(int)
    algo_changed = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        """
        初始化拟合控制组件

        创建算法选择器、参数滑块、显示标签和计算按钮。
        多项式模式：阶数范围3-9，默认5
        样条模式：预估误差 σ 范围 0.1-5.0mm，默认 0.5mm
        """
        # 设置分组框标题
        super().__init__("拟合控制", parent)

        # ===== 算法选择 Radio Buttons =====
        self.poly_radio = QtWidgets.QRadioButton("多项式拟合")
        self.spline_radio = QtWidgets.QRadioButton("三次样条")
        self.spline5_radio = QtWidgets.QRadioButton("五次样条")
        self.poly_radio.setChecked(True)  # 默认选中多项式

        # 创建按钮组确保单选行为
        self.algo_group = QtWidgets.QButtonGroup(self)
        self.algo_group.addButton(self.poly_radio)
        self.algo_group.addButton(self.spline_radio)
        self.algo_group.addButton(self.spline5_radio)

        # 算法选择水平布局
        algo_layout = QtWidgets.QHBoxLayout()
        algo_layout.addWidget(self.poly_radio)
        algo_layout.addWidget(self.spline_radio)
        algo_layout.addWidget(self.spline5_radio)

        # ===== 参数滑块 =====
        # 创建水平滑块用于调节参数
        self.slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.slider.setMinimum(3)  # 多项式模式：最小阶数
        self.slider.setMaximum(9)  # 多项式模式：最大阶数
        self.slider.setValue(5)    # 多项式模式：默认阶数
        # 连接滑块值改变信号到自定义信号
        self.slider.valueChanged.connect(self.degree_changed)

        # 显示当前参数的标签
        self.label = QtWidgets.QLabel("阶数: 5")

        # 显示平滑因子 s 的标签（仅样条模式显示）
        self.s_label = QtWidgets.QLabel("平滑因子 s: -")
        self.s_label.setStyleSheet("color: #64748b; font-size: 12px;")
        self.s_label.setVisible(False)  # 默认隐藏

        # 显示平滑因子公式（仅样条模式显示）
        self.formula_label = QtWidgets.QLabel("公式: s = N × σ²")
        self.formula_label.setStyleSheet("color: #94a3b8; font-size: 11px; font-style: italic;")
        self.formula_label.setVisible(False)  # 默认隐藏

        # 创建计算按钮
        btn = QtWidgets.QPushButton("开始计算")
        self.calc_button = btn

        # 设置垂直布局
        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(algo_layout)
        layout.addWidget(self.label)
        layout.addWidget(self.slider)
        layout.addWidget(self.s_label)
        layout.addWidget(self.formula_label)
        layout.addWidget(btn)
        self.setLayout(layout)

        # 连接信号
        self.slider.valueChanged.connect(self._update_label)
        self.poly_radio.toggled.connect(self._on_algo_changed)
        self.spline_radio.toggled.connect(self._on_algo_changed)
        self.spline5_radio.toggled.connect(self._on_algo_changed)

    def _on_algo_changed(self, checked: bool):
        """
        算法切换时更新滑块配置

        根据选中的算法类型，调整滑块的范围、默认值和标签文本。
        多项式：阶数 3-9，默认 5
        样条：预估误差 σ 0.000-0.600mm，默认 0.250mm（滑块范围 0-600，精度 0.001mm）
        """
        if not checked:
            return  # 只在选中时处理

        if self.poly_radio.isChecked():
            # 切换到多项式模式
            self.slider.setMinimum(3)
            self.slider.setMaximum(9)
            self.slider.setValue(5)
            self.label.setText("阶数: 5")
            self.s_label.setVisible(False)
            self.formula_label.setVisible(False)
            self.algo_changed.emit("polynomial")
        elif self.spline_radio.isChecked():
            # 切换到三次样条模式（滑块 0-600 对应 0.000mm-0.600mm）
            self.slider.setMinimum(0)
            self.slider.setMaximum(600)
            self.slider.setValue(300)  # 默认 0.300mm
            self.label.setText("预估误差 σ: 0.300 mm")
            self.s_label.setVisible(True)
            self.s_label.setText("平滑因子 s: -")
            self.formula_label.setVisible(True)
            self.algo_changed.emit("spline")
        else:
            # 切换到五次样条模式
            self.slider.setMinimum(0)
            self.slider.setMaximum(600)
            self.slider.setValue(150)  # 默认 0.150mm
            self.label.setText("预估误差 σ: 0.150 mm")
            self.s_label.setVisible(True)
            self.s_label.setText("平滑因子 s: -")
            self.formula_label.setVisible(True)
            self.algo_changed.emit("spline5")

    def _update_label(self, val: int):
        """
        更新参数显示标签

        当滑块值改变时，根据当前算法类型更新标签文本。

        Args:
            val (int): 新的参数值
        """
        if self.poly_radio.isChecked():
            self.label.setText(f"阶数: {val}")
        else:
            # 样条模式：滑块值除以1000显示为 σ (mm)
            sigma = val / 1000.0
            self.label.setText(f"预估误差 σ: {sigma:.3f} mm")
        # 发出参数改变信号
        self.degree_changed.emit(val)

    def get_algo_type(self) -> str:
        """
        获取当前选中的算法类型

        Returns:
            str: "polynomial" 表示多项式，"spline" 表示三次样条，"spline5" 表示五次样条
        """
        if self.poly_radio.isChecked():
            return "polynomial"
        elif self.spline_radio.isChecked():
            return "spline"
        else:
            return "spline5"

    def get_sigma_value(self) -> float:
        """
        获取预估误差 σ（单位：mm）

        Returns:
            float: 预估误差，范围 0.000-0.600 mm
        """
        return self.slider.value() / 1000.0

    def update_s_display(self, n_points: int):
        """
        根据数据点数更新平滑因子 s 的显示

        Args:
            n_points (int): 数据点数量
        """
        sigma_mm = self.get_sigma_value()
        sigma_m = sigma_mm / 1000.0  # 转换为米
        s = n_points * (sigma_m ** 2)
        # 转换为百分比显示（s * 100）
        s_percent = s * 100
        self.s_label.setText(f"平滑因子 s: {s_percent:.6f}%")


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
    包括拟合质量指标、弯矩信息、剪力信息、土压力信息和函数表达式。
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

        # 极值信息组（弯矩、剪力、土压力）
        extreme_title = QtWidgets.QLabel("极值信息")
        extreme_title.setStyleSheet("font-weight: 600; font-size: 13px; color: #64748b;")

        self.mmax_label = QtWidgets.QLabel("Mmax = -")
        self.mmax_label.setStyleSheet("font-size: 16px; font-weight: 600; color: #0f172a;")

        self.qmax_label = QtWidgets.QLabel("Qmax = -")
        self.qmax_label.setStyleSheet("font-size: 16px; font-weight: 600; color: #0f172a;")

        self.pmax_label = QtWidgets.QLabel("pmax = -")
        self.pmax_label.setStyleSheet("font-size: 16px; font-weight: 600; color: #0f172a;")

        extreme_layout = QtWidgets.QHBoxLayout()
        extreme_layout.setSpacing(24)
        extreme_layout.addWidget(self.mmax_label)
        extreme_layout.addWidget(self.qmax_label)
        extreme_layout.addWidget(self.pmax_label)
        extreme_layout.addStretch()

        extreme_card = QtWidgets.QVBoxLayout()
        extreme_card.setSpacing(8)
        extreme_card.addWidget(extreme_title)
        extreme_card.addLayout(extreme_layout)

        # 第一行：质量指标和极值信息
        top_row = QtWidgets.QHBoxLayout()
        top_row.setSpacing(48)
        top_row.addLayout(quality_card, 1)
        top_row.addLayout(extreme_card, 2)

        # ========== 创建函数表达式卡片 ==========
        # 位移拟合函数
        self.disp_title = QtWidgets.QLabel("位移拟合函数 y(x)")
        self.disp_title.setStyleSheet(
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
        disp_func_layout.addWidget(self.disp_title)
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
        qmax: float = 0.0,
        pmax: float = 0.0,
        poly_expr: str = "",
        moment_expr: str = "",
        algo_type: str = "polynomial",
    ):
        """
        更新统计信息显示

        Args:
            r2 (float): 决定系数R²
            rmse_mm (float): 均方根误差（毫米）
            mmax (float): 最大弯矩值（kN·m）
            qmax (float): 最大剪力值（kN）
            pmax (float): 最大土压力值（kPa）
            poly_expr (str): 位移拟合函数表达式，可选
            moment_expr (str): 弯矩函数表达式，可选
            algo_type (str): 算法类型，'polynomial'、'spline' 或 'spline5'
        """
        # 更新拟合质量指标
        self.r2_label.setText(f"R² = {r2:.4f}")

        # RMSE添加单位标注
        self.rmse_label.setText(f"RMSE = {rmse_mm:.2f} mm")

        # 更新最大弯矩
        self.mmax_label.setText(f"Mmax = {mmax:.2f} kN·m")

        # 更新最大剪力
        self.qmax_label.setText(f"Qmax = {qmax:.2f} kN")

        # 更新最大土压力
        if algo_type == "spline":
            self.pmax_label.setText("pmax = N/A")
        else:
            self.pmax_label.setText(f"pmax = {pmax:.2f} kPa")

        # 根据算法类型更新标题
        if algo_type == "spline":
            self.disp_title.setText("位移拟合函数 y(x) - 三次样条")
        elif algo_type == "spline5":
            self.disp_title.setText("位移拟合函数 y(x) - 五次样条")
        else:
            self.disp_title.setText("位移拟合函数 y(x)")

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


class WelcomePlaceholder(QtWidgets.QWidget):
    """
    欢迎占位组件

    在用户点击"开始计算"之前显示，提供友好的引导提示。
    使用与左侧面板一致的卡片式设计风格。
    """

    def __init__(self, parent=None):
        """
        初始化欢迎占位组件

        创建居中显示的引导提示内容。
        """
        super().__init__(parent)
        self.setObjectName("welcomePlaceholder")

        # 主标题
        title_label = QtWidgets.QLabel("围护桩反分析工具")
        title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(
            "font-size: 40px; font-weight: 700; color: #0f172a; "
            "margin-bottom: 16px;"
        )

        # 副标题/引导文字
        subtitle_label = QtWidgets.QLabel("Pile Back Analysis Tool")
        subtitle_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet(
            "font-size: 14px; color: #64748b; margin-bottom: 32px;"
        )

        # 引导步骤
        step1 = QtWidgets.QLabel("1. 在左侧输入深度-位移数据")
        step1.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        step1.setStyleSheet("font-size: 15px; color: #475569; margin: 4px 0;")

        step2 = QtWidgets.QLabel("2. 设置材料参数和截面信息")
        step2.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        step2.setStyleSheet("font-size: 15px; color: #475569; margin: 4px 0;")

        step3 = QtWidgets.QLabel("3. 点击「开始计算」按钮")
        step3.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        step3.setStyleSheet("font-size: 15px; color: #475569; margin: 4px 0;")

        # 提示文字
        hint_label = QtWidgets.QLabel("计算结果将在此处显示")
        hint_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        hint_label.setStyleSheet(
            "font-size: 13px; color: #94a3b8; margin-top: 32px; font-style: italic;"
        )

        # 内容容器（用于居中显示）
        content_widget = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        content_layout.setSpacing(4)
        content_layout.addWidget(title_label)
        content_layout.addWidget(subtitle_label)
        content_layout.addSpacing(16)
        content_layout.addWidget(step1)
        content_layout.addWidget(step2)
        content_layout.addWidget(step3)
        # content_layout.addWidget(hint_label)

        # 主布局（使内容垂直居中）
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addStretch(1)
        main_layout.addWidget(content_widget, 0, QtCore.Qt.AlignmentFlag.AlignCenter)
        main_layout.addStretch(1)

        # 设置样式
        self.setStyleSheet(
            """
            WelcomePlaceholder {
                background-color: #f8fafc;
            }
            """
        )

