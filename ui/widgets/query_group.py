"""
任意深度查询组件

允许用户输入特定深度，查询该点的计算结果。
"""

from __future__ import annotations

from PyQt6 import QtCore, QtWidgets


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
