"""
现代卡片式设计主题

提供统一的 UI 主题样式，包括调色板和样式表设置。
"""

from __future__ import annotations

from PyQt6 import QtGui, QtWidgets


def apply_theme(window: QtWidgets.QMainWindow):
    """
    应用现代卡片式设计主题

    设置现代化的卡片风格UI，包括阴影、圆角和精致的间距。
    包括调色板和样式表两部分设置。

    Args:
        window: 主窗口实例
    """
    # ===== 调色板设置 =====
    palette = QtGui.QPalette()
    palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor("#f8fafc"))
    palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor("#ffffff"))
    palette.setColor(QtGui.QPalette.ColorRole.Text, QtGui.QColor("#0f172a"))
    palette.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QColor("#2563eb"))
    palette.setColor(QtGui.QPalette.ColorRole.ButtonText, QtGui.QColor("#ffffff"))
    window.setPalette(palette)

    # 配色方案
    accent = "#2563eb"          # 主题蓝色
    accent_hover = "#1d4ed8"    # 深蓝色（hover）
    accent_light = "#dbeafe"    # 浅蓝色背景
    border = "#e2e8f0"          # 边框颜色
    border_light = "#f1f5f9"    # 浅边框
    text_primary = "#0f172a"    # 主文本
    text_muted = "#64748b"      # 次要文本
    bg_card = "#ffffff"         # 卡片背景
    bg_panel = "#f8fafc"        # 面板背景

    window.setStyleSheet(
        f"""
        /* 全局样式 */
        QWidget {{
            color: {text_primary};
            background-color: {bg_panel};
            font-size: 14px;
            font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
        }}

        /* 左侧面板背景 */
        #leftPanel {{
            background-color: {bg_panel};
        }}

        /* 左侧滚动区域 */
        #leftScroll {{
            background-color: {bg_panel};
            border-right: 1px solid {border_light};
        }}

        /* 右侧面板背景 */
        #rightPanel {{
            background-color: {bg_panel};
        }}

        /* 右侧堆叠容器 */
        #rightStack {{
            background-color: {bg_panel};
        }}

        /* 结果页面 */
        #resultsPage {{
            background-color: {bg_panel};
        }}

        /* 图表容器卡片样式 */
        #plotContainer {{
            background-color: {bg_card};
            border: 1px solid {border};
            border-radius: 12px;
        }}

        /* 卡片样式的GroupBox */
        QGroupBox {{
            background-color: {bg_card};
            border: 1px solid {border};
            border-radius: 12px;
            margin-top: 16px;
            padding: 20px 16px 16px 16px;
            font-weight: 500;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 16px;
            top: 8px;
            padding: 0 8px;
            color: {text_primary};
            font-size: 15px;
            font-weight: 600;
            background-color: {bg_card};
        }}

        /* 输入框样式 */
        QLineEdit {{
            background-color: {bg_panel};
            border: 2px solid {border};
            border-radius: 8px;
            padding: 8px 12px;
            font-size: 14px;
            color: {text_primary};
        }}
        QLineEdit:focus {{
            border-color: {accent};
            background-color: #ffffff;
        }}
        QLineEdit:hover {{
            border-color: {accent_light};
        }}

        /* 文本编辑框样式 */
        QTextEdit {{
            background-color: {bg_panel};
            border: 2px solid {border};
            border-radius: 8px;
            padding: 12px;
            font-size: 13px;
            line-height: 1.5;
            color: {text_primary};
        }}
        QTextEdit:focus {{
            border-color: {accent};
            background-color: #ffffff;
        }}

        /* 主要按钮样式 */
        QPushButton {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                       stop:0 {accent}, stop:1 {accent_hover});
            color: #ffffff;
            border: none;
            border-radius: 8px;
            padding: 10px 20px;
            font-size: 14px;
            font-weight: 600;
            min-height: 20px;
        }}
        QPushButton:hover {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                       stop:0 {accent_hover}, stop:1 #1e40af);
        }}
        QPushButton:pressed {{
            background: #1e3a8a;
            padding-top: 11px;
            padding-bottom: 9px;
        }}
        QPushButton:disabled {{
            background: #cbd5e1;
            color: #94a3b8;
        }}

        /* 下拉框样式 */
        QComboBox {{
            background-color: {bg_panel};
            border: 2px solid {border};
            border-radius: 8px;
            padding: 8px 12px;
            min-width: 80px;
        }}
        QComboBox:hover {{
            border-color: {accent_light};
        }}
        QComboBox:focus {{
            border-color: {accent};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 30px;
        }}
        QComboBox::down-arrow {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid {text_muted};
            margin-right: 8px;
        }}

        /* 单选按钮样式 */
        QRadioButton {{
            spacing: 8px;
            color: {text_primary};
            font-size: 14px;
        }}
        QRadioButton::indicator {{
            width: 18px;
            height: 18px;
            border-radius: 9px;
            border: 2px solid {border};
            background-color: #ffffff;
        }}
        QRadioButton::indicator:hover {{
            border-color: {accent_light};
        }}
        QRadioButton::indicator:checked {{
            border-color: {accent};
            background-color: {accent};
            border: 5px solid {accent};
        }}

        /* 滑块样式 */
        QSlider::groove:horizontal {{
            height: 8px;
            background: {border_light};
            border-radius: 4px;
        }}
        QSlider::handle:horizontal {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                       stop:0 {accent}, stop:1 {accent_hover});
            width: 20px;
            height: 20px;
            margin: -6px 0;
            border-radius: 10px;
            border: 2px solid #ffffff;
        }}
        QSlider::handle:horizontal:hover {{
            background: {accent_hover};
            width: 22px;
            height: 22px;
            margin: -7px 0;
        }}
        QSlider::sub-page:horizontal {{
            background: {accent};
            border-radius: 4px;
        }}

        /* 标签样式 */
        QLabel {{
            color: {text_primary};
            background: transparent;
            padding: 2px;
        }}

        /* 统计栏样式 */
        #statsBar {{
            background-color: {bg_card};
            border: 1px solid {border};
            border-radius: 12px;
        }}
        #statsBar QLabel {{
            font-size: 14px;
            font-weight: 500;
            color: {text_primary};
        }}
        """
    )
