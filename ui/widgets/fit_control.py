"""
拟合控制组件

提供算法选择（多项式/三次样条/五次样条/论文样条）、参数调节滑块和计算按钮。
支持动态切换算法类型，滑块语义和范围随之变化。
"""

from __future__ import annotations

from PyQt6 import QtCore, QtWidgets


class FitControlGroup(QtWidgets.QGroupBox):
    """
    拟合控制组件

    提供算法选择（多项式/三次样条/五次样条）、参数调节滑块和计算按钮。
    支持动态切换算法类型，滑块语义和范围随之变化。
    """
    # 定义信号：参数改变时发出
    degree_changed = QtCore.pyqtSignal(int)
    algo_changed = QtCore.pyqtSignal(str)
    auto_sigma_requested = QtCore.pyqtSignal()  # 请求自动选择 σ

    def __init__(self, parent=None):
        """
        初始化拟合控制组件

        创建算法选择器、参数滑块、显示标签和计算按钮。
        """
        super().__init__("拟合控制", parent)

        # ===== 算法选择 Radio Buttons =====
        self.poly_radio = QtWidgets.QRadioButton("多项式拟合")
        self.spline_radio = QtWidgets.QRadioButton("三次样条")
        self.spline5_radio = QtWidgets.QRadioButton("五次样条")
        self.mao_radio = QtWidgets.QRadioButton("论文样条")
        self.poly_radio.setChecked(True)  # 默认选中多项式

        # 创建按钮组确保单选行为
        self.algo_group = QtWidgets.QButtonGroup(self)
        self.algo_group.addButton(self.poly_radio)
        self.algo_group.addButton(self.spline_radio)
        self.algo_group.addButton(self.spline5_radio)
        self.algo_group.addButton(self.mao_radio)

        # 算法选择布局（两行）
        algo_row1 = QtWidgets.QHBoxLayout()
        algo_row1.addWidget(self.poly_radio)
        algo_row1.addWidget(self.spline_radio)
        algo_row1.addWidget(self.spline5_radio)

        algo_row2 = QtWidgets.QHBoxLayout()
        algo_row2.addWidget(self.mao_radio)
        algo_row2.addStretch(1)

        algo_layout = QtWidgets.QVBoxLayout()
        algo_layout.addLayout(algo_row1)
        algo_layout.addLayout(algo_row2)

        # ===== 参数滑块 =====
        self.slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.slider.setMinimum(3)  # 多项式模式：最小阶数
        self.slider.setMaximum(9)  # 多项式模式：最大阶数
        self.slider.setValue(5)    # 多项式模式：默认阶数
        self.slider.valueChanged.connect(self.degree_changed)

        # 显示当前参数的标签
        self.label = QtWidgets.QLabel("阶数: 5")

        # 显示平滑因子 s 的标签（仅样条模式显示）
        self.s_label = QtWidgets.QLabel("平滑因子 s: -")
        self.s_label.setStyleSheet("color: #64748b; font-size: 12px;")
        self.s_label.setVisible(False)

        # 显示平滑因子公式（仅样条模式显示）
        self.formula_label = QtWidgets.QLabel("公式: s = N × σ²")
        self.formula_label.setStyleSheet("color: #94a3b8; font-size: 11px; font-style: italic;")
        self.formula_label.setVisible(False)

        # 自动选择 σ 按钮（仅样条模式显示）
        self.auto_btn = QtWidgets.QPushButton("自动")
        self.auto_btn.setToolTip("使用交叉验证自动选择最优 σ")
        self.auto_btn.setFixedWidth(70)
        self.auto_btn.setVisible(False)
        self.auto_btn.clicked.connect(self.auto_sigma_requested.emit)

        # 创建计算按钮
        btn = QtWidgets.QPushButton("开始计算")
        self.calc_button = btn

        # 滑块行布局（滑块 + 自动按钮）
        slider_layout = QtWidgets.QHBoxLayout()
        slider_layout.addWidget(self.slider)
        slider_layout.addWidget(self.auto_btn)

        # 设置垂直布局
        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(algo_layout)
        layout.addWidget(self.label)
        layout.addLayout(slider_layout)
        layout.addWidget(self.s_label)
        layout.addWidget(self.formula_label)
        layout.addWidget(btn)
        self.setLayout(layout)

        # 连接信号
        self.slider.valueChanged.connect(self._update_label)
        self.poly_radio.toggled.connect(self._on_algo_changed)
        self.spline_radio.toggled.connect(self._on_algo_changed)
        self.spline5_radio.toggled.connect(self._on_algo_changed)
        self.mao_radio.toggled.connect(self._on_algo_changed)

    def _on_algo_changed(self, checked: bool):
        """
        算法切换时更新滑块配置
        """
        if not checked:
            return

        if self.poly_radio.isChecked():
            self.slider.setMinimum(3)
            self.slider.setMaximum(9)
            self.slider.setValue(5)
            self.label.setText("阶数: 5")
            self.s_label.setVisible(False)
            self.formula_label.setVisible(False)
            self.auto_btn.setVisible(False)
            self.algo_changed.emit("polynomial")
        elif self.spline_radio.isChecked():
            self.slider.setMinimum(0)
            self.slider.setMaximum(2500)
            self.slider.setValue(500)
            self.label.setText("预估误差 σ: 0.500 mm")
            self.s_label.setVisible(True)
            self.s_label.setText("平滑因子 s: -")
            self.formula_label.setVisible(True)
            self.formula_label.setText("公式: s = N × σ²")
            self.auto_btn.setVisible(True)
            self.algo_changed.emit("spline")
        elif self.spline5_radio.isChecked():
            self.slider.setMinimum(0)
            self.slider.setMaximum(2500)
            self.slider.setValue(500)
            self.label.setText("预估误差 σ: 0.500 mm")
            self.s_label.setVisible(True)
            self.s_label.setText("平滑因子 s: -")
            self.formula_label.setVisible(True)
            self.formula_label.setText("公式: s = N × σ²")
            self.auto_btn.setVisible(True)
            self.algo_changed.emit("spline5")
        elif self.mao_radio.isChecked():
            self.slider.setMinimum(0)
            self.slider.setMaximum(2500)
            self.slider.setValue(500)
            self.label.setText("误差限 δ: 0.500 mm")
            self.s_label.setVisible(True)
            self.s_label.setText("逐点误差控制: |Dᵢ| ≤ δ")
            self.formula_label.setVisible(True)
            self.formula_label.setText("公式: min ∫y''²dx, s.t. |yᵢ-ŷᵢ| ≤ δ")
            self.auto_btn.setVisible(True)
            self.algo_changed.emit("mao_spline")

    def _update_label(self, val: int):
        """
        更新参数显示标签
        """
        if self.poly_radio.isChecked():
            self.label.setText(f"阶数: {val}")
        elif self.mao_radio.isChecked():
            delta = val / 1000.0
            self.label.setText(f"误差限 δ: {delta:.3f} mm")
        else:
            sigma = val / 1000.0
            self.label.setText(f"预估误差 σ: {sigma:.3f} mm")
        self.degree_changed.emit(val)

    def get_algo_type(self) -> str:
        """
        获取当前选中的算法类型

        Returns:
            str: "polynomial"、"spline"、"spline5" 或 "mao_spline"
        """
        if self.poly_radio.isChecked():
            return "polynomial"
        elif self.spline_radio.isChecked():
            return "spline"
        elif self.spline5_radio.isChecked():
            return "spline5"
        else:
            return "mao_spline"

    def get_sigma_value(self) -> float:
        """
        获取预估误差 σ（单位：mm）

        Returns:
            float: 预估误差
        """
        return self.slider.value() / 1000.0

    def update_s_display(self, n_points: int):
        """
        根据数据点数更新平滑因子 s 的显示

        Args:
            n_points (int): 数据点数量
        """
        sigma_mm = self.get_sigma_value()
        if self.mao_radio.isChecked():
            self.s_label.setText(f"误差限 δ = {sigma_mm:.3f} mm (逐点)")
        else:
            sigma_m = sigma_mm / 1000.0
            s = n_points * (sigma_m ** 2)
            s_percent = s * 100
            self.s_label.setText(f"平滑因子 s: {s_percent:.6f}%")

    def set_sigma_value(self, sigma_mm: float):
        """
        设置 σ 值（由自动选择调用）

        Args:
            sigma_mm (float): 预估误差 σ，单位为毫米
        """
        slider_val = int(sigma_mm * 1000)
        slider_val = max(0, min(self.slider.maximum(), slider_val))
        self.slider.setValue(slider_val)

    def update_sigma_max(self, n_points: int):
        """
        根据数据点数量更新 σ 滑块最大值

        Args:
            n_points (int): 数据点数量
        """
        if self.poly_radio.isChecked():
            return

        if self.mao_radio.isChecked():
            max_mm = round(n_points * 0.155, 1)
        elif n_points > 60:
            max_mm = 8.0
        elif n_points > 40:
            max_mm = 4.0
        else:
            max_mm = 2.5

        max_val = int(max_mm * 1000)

        current_val = min(self.slider.value(), max_val)
        self.slider.setMaximum(max_val)
        self.slider.setValue(current_val)
