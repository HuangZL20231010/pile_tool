"""
PileBackAnalysis应用程序入口点

这是围护桩反分析工具的启动文件，负责：
- 创建PyQt6应用程序实例
- 初始化主窗口
- 启动GUI事件循环

运行方式：
    python main.py
"""

from __future__ import annotations

import sys

from PyQt6 import QtWidgets

from ui.main_window import MainWindow


def main():
    """
    主函数：启动应用程序

    执行完整的应用程序启动流程：
    1. 创建QApplication实例（PyQt6应用的核心）
    2. 设置应用程序名称（用于系统任务管理器等）
    3. 创建并显示主窗口
    4. 进入事件循环，等待用户交互

    这是典型的PyQt6应用程序启动模式。
    """
    # 创建PyQt6应用程序实例
    # sys.argv 包含命令行参数，PyQt6会处理其中的GUI相关参数
    app = QtWidgets.QApplication(sys.argv)

    # 设置应用程序名称，这会显示在任务管理器、窗口标题等地方
    app.setApplicationName("PileBackAnalysis")

    # 创建主窗口实例
    window = MainWindow()

    # 显示主窗口（默认情况下窗口是隐藏的）
    window.show()

    # 进入应用程序事件循环
    # app.exec() 会阻塞直到应用程序退出
    # sys.exit() 确保以正确的退出码退出程序
    sys.exit(app.exec())


# Python惯用法：只有当此文件被直接运行时才执行main()
# 如果被其他文件import，则不会执行main()
if __name__ == "__main__":
    main()

