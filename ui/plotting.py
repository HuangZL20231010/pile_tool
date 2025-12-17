"""
Matplotlib绘图画布组件

封装了位移和弯矩曲线的绘制功能，采用科技风格配色。
提供双子图布局：左侧位移图，右侧弯矩图。
"""

from __future__ import annotations

from typing import Iterable, Optional

import platform
import matplotlib
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure


class PlotCanvas(FigureCanvasQTAgg):
    """
    自定义Matplotlib画布组件

    继承自FigureCanvasQTAgg，专门用于显示围护桩的位移和弯矩曲线。
    采用深色科技风格，支持实时更新绘图。
    """

    def __init__(self, parent=None):
        """
        初始化绘图画布

        改为浅色背景，设置中文友好字体以避免缺字警告。
        """
        # 统一浅色主题与中文字体
        matplotlib.rcParams["axes.facecolor"] = "#ffffff"
        matplotlib.rcParams["figure.facecolor"] = "#ffffff"

        # 根据操作系统设置合适的字体
        system = platform.system()
        if system == "Windows":
            # Windows系统使用微软雅黑
            matplotlib.rcParams["font.family"] = ["Microsoft YaHei", "SimHei", "Arial", "DejaVu Sans"]
        elif system == "Darwin":  # macOS
            # macOS系统使用系统自带的中文字体
            matplotlib.rcParams["font.family"] = ["Songti SC", "STHeiti", "Hei", "Kaiti SC", "Arial", "DejaVu Sans"]
        else:  # Linux或其他系统
            # 使用通用字体
            matplotlib.rcParams["font.family"] = ["DejaVu Sans", "Arial", "Liberation Sans", "sans-serif"]

        # 创建Matplotlib图形对象
        self.fig = Figure(facecolor="#ffffff")

        # 调用父类构造函数，传入图形对象
        super().__init__(self.fig)

        # 创建双子图布局：1行2列
        # 左侧子图：位移曲线 (121表示1行2列的第1个)
        self.ax_disp = self.fig.add_subplot(121)
        # 右侧子图：弯矩曲线 (122表示1行2列的第2个)
        self.ax_moment = self.fig.add_subplot(122)

        # 预设Y轴方向：岩土工程习惯，深度向下为正
        self.ax_disp.invert_yaxis()
        self.ax_moment.invert_yaxis()

        # 调整子图间距，避免标签重叠
        self.fig.tight_layout(pad=2.0)

    def plot(
        self,
        depth_raw: Iterable[float],
        disp_raw_mm: Iterable[float],
        depth_dense,
        disp_fit_mm,
        moment,
    ):
        """
        绘制位移和弯矩曲线

        清除旧图，在两个子图中分别绘制位移和弯矩数据。
        采用科技风格配色：青色原始点，紫色拟合线，绿色弯矩线。
        符合岩土工程习惯：X轴为位移/弯矩，Y轴为深度。

        Args:
            depth_raw: 原始深度数据数组
            disp_raw_mm: 原始位移数据数组（毫米）
            depth_dense: 密集深度坐标（用于绘制平滑曲线）
            disp_fit_mm: 拟合位移数据（毫米）
            moment: 弯矩数据（kN·m）
        """
        # 清除之前的绘图内容
        self.ax_disp.clear()
        self.ax_moment.clear()

        # ===== 左侧位移子图 =====
        # 绘制原始数据点：蓝色圆点，标签为"原始点"
        # 注意：在岩土工程中，X轴是位移，Y轴是深度
        self.ax_disp.scatter(disp_raw_mm, depth_raw, color="#2563eb", label="原始点")
        # 绘制拟合曲线：紫色实线，标签为"拟合曲线"
        self.ax_disp.plot(disp_fit_mm, depth_dense, color="#7c3aed", label="拟合曲线")

        # 设置坐标轴标签 - 符合岩土工程习惯
        self.ax_disp.set_xlabel("位移 (mm)")
        self.ax_disp.set_ylabel("深度 (m)")

        # 添加网格线，透明度0.3
        self.ax_disp.grid(True, alpha=0.3, color="#d1d5db")
        # 添加图例，位置自动选择最佳
        self.ax_disp.legend(loc="best")

        # ===== 右侧弯矩子图 =====
        # 绘制弯矩曲线：绿色实线，标签为"弯矩"
        # X轴是弯矩，Y轴是深度
        self.ax_moment.plot(moment, depth_dense, color="#16a34a", label="弯矩")

        # 设置坐标轴标签
        self.ax_moment.set_xlabel("弯矩 (kN·m)")
        self.ax_moment.set_ylabel("深度 (m)")

        # 添加网格线和图例
        self.ax_moment.grid(True, alpha=0.3, color="#d1d5db")
        self.ax_moment.legend(loc="best")

        # 同样反转Y轴，与位移图保持一致
        self.ax_moment.invert_yaxis()

        # 重新调整布局，确保元素不重叠
        self.fig.tight_layout(pad=2.0)

        # 反转Y轴：岩土工程习惯，深度向下为正
        # 注意：必须在 tight_layout() 之后调用，以确保布局稳定后再翻转
        self.ax_disp.invert_yaxis()

        # 延迟绘制，提高性能
        self.draw_idle()

