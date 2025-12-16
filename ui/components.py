"""
围护桩反分析工具可复用UI组件库

定义了所有用户界面组件，包括数据输入、参数设置、控制面板等。
这些组件采用模块化设计，便于维护和扩展。
"""

from __future__ import annotations

from PyQt6 import QtCore, QtWidgets


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
        # 设置占位符文本，展示数据格式示例与默认数据说明
        self.text_edit.setPlaceholderText(
            "示例(可直接粘贴Excel两列，逗号/空格/Tab均可)：\n"
            "0.50\t-0.29\n1.00\t-0.81\n1.50\t-1.06\n2.00\t-0.98\n...\n"
            "留空则自动使用默认样例数据与参数"
        )

        # 设置垂直布局
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.text_edit)
        self.setLayout(layout)


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

    显示拟合统计信息：R²值、RMSE、最大弯矩。
    用于实时反馈计算结果的质量。
    """

    def __init__(self, parent=None):
        """
        初始化统计栏

        创建三个标签显示不同的统计信息。
        """
        super().__init__(parent)

        # R²决定系数标签
        self.r2_label = QtWidgets.QLabel("R2: -")
        # 均方根误差标签（毫米）
        self.rmse_label = QtWidgets.QLabel("RMSE(mm): -")
        # 最大弯矩标签
        self.mmax_label = QtWidgets.QLabel("Mmax(kN·m): -")

        # 设置水平布局
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.r2_label)
        layout.addWidget(self.rmse_label)
        layout.addWidget(self.mmax_label)
        # 添加伸缩空间将标签推到左侧
        layout.addStretch(1)
        self.setLayout(layout)

    def update_stats(self, r2: float, rmse_mm: float, mmax: float):
        """
        更新统计信息显示

        Args:
            r2 (float): 决定系数R²
            rmse_mm (float): 均方根误差（毫米）
            mmax (float): 最大弯矩值（kN·m）
        """
        # 格式化显示R²，保留4位小数
        self.r2_label.setText(f"R2: {r2:.4f}")
        # 格式化显示RMSE，保留2位小数
        self.rmse_label.setText(f"RMSE(mm): {rmse_mm:.2f}")
        # 格式化显示最大弯矩，保留2位小数
        self.mmax_label.setText(f"Mmax(kN·m): {mmax:.2f}")

