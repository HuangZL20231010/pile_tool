"""
统计信息显示栏

使用现代卡片式设计显示拟合统计信息和函数表达式。
"""

from __future__ import annotations

from PyQt6 import QtWidgets


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

        extreme_layout = QtWidgets.QHBoxLayout()
        extreme_layout.setSpacing(24)
        extreme_layout.addWidget(self.mmax_label)
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
            poly_expr (str): 位移拟合函数表达式
            moment_expr (str): 弯矩函数表达式
            algo_type (str): 算法类型
        """
        self.r2_label.setText(f"R² = {r2:.4f}")
        self.rmse_label.setText(f"RMSE = {rmse_mm:.2f} mm")
        self.mmax_label.setText(f"Mmax = {mmax:.2f} kN·m")

        if algo_type == "spline":
            self.disp_title.setText("位移拟合函数 y(x) - 三次样条")
        elif algo_type == "spline5":
            self.disp_title.setText("位移拟合函数 y(x) - 五次样条")
        elif algo_type == "mao_spline":
            self.disp_title.setText("位移拟合函数 y(x) - 光顺样条")
        else:
            self.disp_title.setText("位移拟合函数 y(x)")

        if poly_expr:
            self.poly_label.setText(poly_expr)
        else:
            self.poly_label.setText("-")

        if moment_expr:
            self.moment_expr_label.setText(moment_expr)
        else:
            self.moment_expr_label.setText("-")
