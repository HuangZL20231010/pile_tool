"""
材料与截面参数设置组件

整合截面类型选择、尺寸输入和 Bs 迭代参数。
根据选择的截面类型动态显示相应的输入框。
"""

from __future__ import annotations

from PyQt6 import QtWidgets


class ParamsGroup(QtWidgets.QGroupBox):
    """
    材料与截面参数设置组件

    整合了截面类型选择、尺寸输入和 Bs 迭代参数。
    根据选择的截面类型动态显示相应的输入框。
    两种截面都使用 Bs 迭代刚度计算。
    """

    def __init__(self, parent=None):
        """
        初始化参数设置组件

        创建所有参数输入控件并安排布局。
        默认选择圆形截面。
        """
        super().__init__("材料与截面参数", parent)

        # 截面类型单选按钮
        self.circle_radio = QtWidgets.QRadioButton("圆形")
        self.rect_radio = QtWidgets.QRadioButton("矩形")
        self.circle_radio.setChecked(True)

        self.section_group = QtWidgets.QButtonGroup(self)
        self.section_group.addButton(self.circle_radio)
        self.section_group.addButton(self.rect_radio)

        # 圆形截面输入框
        self.D_label = QtWidgets.QLabel("D (mm)")
        self.D_input = QtWidgets.QLineEdit()
        self.D_input.setPlaceholderText("直径")

        self.cover_label = QtWidgets.QLabel("cover (mm)")
        self.cover_input = QtWidgets.QLineEdit()
        self.cover_input.setPlaceholderText("保护层厚度")

        # 矩形截面输入框
        self.b_label = QtWidgets.QLabel("b (mm)")
        self.b_input = QtWidgets.QLineEdit()
        self.b_input.setPlaceholderText("宽度")

        self.h_label = QtWidgets.QLabel("h (mm)")
        self.h_input = QtWidgets.QLineEdit()
        self.h_input.setPlaceholderText("高度")

        self.rect_cover_label = QtWidgets.QLabel("cover (mm)")
        self.rect_cover_input = QtWidgets.QLineEdit()
        self.rect_cover_input.setPlaceholderText("保护层厚度")

        # 共用 Bs 迭代参数输入框
        self.Ec_label = QtWidgets.QLabel("Ec (MPa)")
        self.Ec_input = QtWidgets.QLineEdit()
        self.Ec_input.setPlaceholderText("混凝土弹模")

        self.As_label = QtWidgets.QLabel("As (mm²)")
        self.As_input = QtWidgets.QLineEdit()
        self.As_input.setPlaceholderText("钢筋面积")

        self.ftk_label = QtWidgets.QLabel("ftk (MPa)")
        self.ftk_input = QtWidgets.QLineEdit()
        self.ftk_input.setPlaceholderText("抗拉标准值")

        self.Es_label = QtWidgets.QLabel("Es = 200000 MPa (内置)")
        self.Es_label.setStyleSheet("color: #64748b; font-size: 12px;")

        # 使用网格布局排列控件
        top = QtWidgets.QGridLayout()

        # 行0：截面类型选择
        top.addWidget(self.circle_radio, 0, 0)
        top.addWidget(self.rect_radio, 0, 1)

        # 行1-2：圆形专用（D, cover）
        top.addWidget(self.D_label, 1, 0)
        top.addWidget(self.D_input, 1, 1)
        top.addWidget(self.cover_label, 2, 0)
        top.addWidget(self.cover_input, 2, 1)

        # 行3-5：矩形专用（b, h, cover）
        top.addWidget(self.b_label, 3, 0)
        top.addWidget(self.b_input, 3, 1)
        top.addWidget(self.h_label, 4, 0)
        top.addWidget(self.h_input, 4, 1)
        top.addWidget(self.rect_cover_label, 5, 0)
        top.addWidget(self.rect_cover_input, 5, 1)

        # 行6-8：共用 Bs 参数（Ec, As, ftk）
        top.addWidget(self.Ec_label, 6, 0)
        top.addWidget(self.Ec_input, 6, 1)
        top.addWidget(self.As_label, 7, 0)
        top.addWidget(self.As_input, 7, 1)
        top.addWidget(self.ftk_label, 8, 0)
        top.addWidget(self.ftk_input, 8, 1)

        # 行9：Es 标签
        top.addWidget(self.Es_label, 9, 0, 1, 2)

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
        """根据截面类型显示/隐藏对应输入框。"""
        circle = self.circle_radio.isChecked()
        # 圆形专用：D, cover
        self.D_label.setVisible(circle)
        self.D_input.setVisible(circle)
        self.cover_label.setVisible(circle)
        self.cover_input.setVisible(circle)
        # 矩形专用：b, h, cover
        self.b_label.setVisible(not circle)
        self.b_input.setVisible(not circle)
        self.h_label.setVisible(not circle)
        self.h_input.setVisible(not circle)
        self.rect_cover_label.setVisible(not circle)
        self.rect_cover_input.setVisible(not circle)

    def get_bs_params(self) -> dict:
        """
        获取 Bs 迭代参数（两种截面通用）

        圆形截面使用等效矩形截面法：
            h_eq = 0.866 × D
            b_eq = 0.886 × D
            h0_eq = h_eq - cover

        Returns:
            dict: Bs 参数字典
        """
        if self.circle_radio.isChecked():
            D = float(self.D_input.text() or 0)
            cover = float(self.cover_input.text() or 0)
            h_eq = 0.866 * D
            b_eq = 0.886 * D
            h0_eq = h_eq - cover
            return {
                'h0': h0_eq,
                'Ec': float(self.Ec_input.text() or 0),
                'As': float(self.As_input.text() or 0),
                'ftk': float(self.ftk_input.text() or 0),
                'b_eq': b_eq,
                'h_eq': h_eq,
            }
        h = float(self.h_input.text() or 0)
        cover = float(self.rect_cover_input.text() or 0)
        return {
            'h0': h - cover,
            'Ec': float(self.Ec_input.text() or 0),
            'As': float(self.As_input.text() or 0),
            'ftk': float(self.ftk_input.text() or 0),
        }
