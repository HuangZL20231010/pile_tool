"""
拟合控制组件

提供论文样条算法选择、参数调节滑块和计算按钮。
滑块语义固定为论文样条的误差限 δ。
"""

from __future__ import annotations

from PyQt6 import QtCore, QtWidgets


class FitControlGroup(QtWidgets.QGroupBox):
    """
    拟合控制组件

    提供论文样条算法选择、参数调节滑块和计算按钮。
    滑块语义固定为论文样条的误差限 δ。
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
        self.mao_radio = QtWidgets.QRadioButton("论文样条")
        self.mao_radio.setChecked(True)

        # 创建按钮组确保单选行为
        self.algo_group = QtWidgets.QButtonGroup(self)
        self.algo_group.addButton(self.mao_radio)

        algo_layout = QtWidgets.QVBoxLayout()
        algo_layout.addWidget(self.mao_radio)

        # ===== 参数滑块 =====
        self.slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(2500)
        self.slider.setValue(500)
        self.slider.valueChanged.connect(self.degree_changed)

        # 显示当前参数的标签
        self.label = QtWidgets.QLabel("误差限 δ: 0.500 mm")

        # 显示平滑因子 s 的标签（仅样条模式显示）
        self.s_label = QtWidgets.QLabel("逐点误差控制: |Dᵢ| ≤ δ")
        self.s_label.setStyleSheet("color: #64748b; font-size: 12px;")
        self.s_label.setVisible(True)

        # 显示平滑因子公式（仅样条模式显示）
        self.formula_label = QtWidgets.QLabel("公式: min ∫y''²dx, s.t. |yᵢ-ŷᵢ| ≤ δ")
        self.formula_label.setStyleSheet("color: #94a3b8; font-size: 11px; font-style: italic;")
        self.formula_label.setVisible(True)

        # 自动选择 δ 按钮
        self.auto_btn = QtWidgets.QPushButton("自动")
        self.auto_btn.setToolTip("自动选择最优误差限 δ")
        self.auto_btn.setFixedWidth(70)
        self.auto_btn.setVisible(True)
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
        self.mao_radio.toggled.connect(self._on_algo_changed)

    def _on_algo_changed(self, checked: bool):
        """
        算法切换时更新滑块配置
        """
        if not checked:
            return

        if self.mao_radio.isChecked():
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
        if self.mao_radio.isChecked():
            delta = val / 1000.0
            self.label.setText(f"误差限 δ: {delta:.3f} mm")
        self.degree_changed.emit(val)

    def get_algo_type(self) -> str:
        """
        获取当前选中的算法类型

        Returns:
            str: 固定返回 "mao_spline"
        """
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
        self.s_label.setText(f"误差限 δ = {sigma_mm:.3f} mm (逐点)")

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
        max_mm = round(n_points * 0.155, 1)

        max_val = int(max_mm * 1000)

        current_val = min(self.slider.value(), max_val)
        self.slider.setMaximum(max_val)
        self.slider.setValue(current_val)
