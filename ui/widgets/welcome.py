"""
欢迎占位组件

在用户点击"开始计算"之前显示，提供友好的引导提示。
"""

from __future__ import annotations

from PyQt6 import QtCore, QtWidgets


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
