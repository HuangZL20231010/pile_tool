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
import mplcursors


class CrosshairCursor:
    """
    交互式十字线光标

    跟踪鼠标移动并显示对应深度的位移和弯矩信息。
    当鼠标离开图表时自动隐藏。
    """

    def __init__(self, ax_disp, ax_moment, solver):
        """
        初始化十字线光标

        Args:
            ax_disp: 位移子图
            ax_moment: 弯矩子图
            solver: PileSolver 实例，用于查询数值
        """
        self.ax_disp = ax_disp
        self.ax_moment = ax_moment
        self.solver = solver

        # 创建水平线（跟踪深度）
        self.hline_disp = ax_disp.axhline(
            y=0, color='#6366f1', linewidth=1,
            linestyle='--', alpha=0.7, visible=False
        )
        self.hline_moment = ax_moment.axhline(
            y=0, color='#6366f1', linewidth=1,
            linestyle='--', alpha=0.7, visible=False
        )

        # 创建标注框
        self.annot_disp = ax_disp.annotate(
            '', xy=(0, 0), xytext=(10, 10),
            textcoords='offset points',
            bbox=dict(boxstyle='round,pad=0.5', fc='#ffffff',
                     ec='#2563eb', alpha=0.95, linewidth=2),
            fontsize=10, visible=False
        )
        self.annot_moment = ax_moment.annotate(
            '', xy=(0, 0), xytext=(10, 10),
            textcoords='offset points',
            bbox=dict(boxstyle='round,pad=0.5', fc='#ffffff',
                     ec='#16a34a', alpha=0.95, linewidth=2),
            fontsize=10, visible=False
        )

        # 跟踪可见状态
        self.visible = False

    def update(self, depth_y):
        """
        更新光标位置并查询该深度的数值

        Args:
            depth_y: 深度值（米）
        """
        try:
            # 查询该深度的数值
            result = self.solver.query_single_point(depth_y)

            # 更新水平线位置
            self.hline_disp.set_ydata([depth_y])
            self.hline_moment.set_ydata([depth_y])

            # 更新位移标注
            self.annot_disp.xy = (result.y_mm, depth_y)
            self.annot_disp.set_text(
                f"深度: {depth_y:.2f} m\n"
                f"位移: {result.y_mm:.2f} mm"
            )

            # 更新弯矩标注
            self.annot_moment.xy = (result.moment, depth_y)
            self.annot_moment.set_text(
                f"深度: {depth_y:.2f} m\n"
                f"弯矩: {result.moment:.2f} kN·m"
            )

            # 显示所有元素
            self.show()

        except (RuntimeError, ValueError):
            # Solver 未准备好或深度无效
            self.hide()

    def show(self):
        """显示光标和标注"""
        self.hline_disp.set_visible(True)
        self.hline_moment.set_visible(True)
        self.annot_disp.set_visible(True)
        self.annot_moment.set_visible(True)
        self.visible = True

    def hide(self):
        """隐藏光标和标注"""
        self.hline_disp.set_visible(False)
        self.hline_moment.set_visible(False)
        self.annot_disp.set_visible(False)
        self.annot_moment.set_visible(False)
        self.visible = False


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

        # 十字线光标和事件连接
        self.crosshair = None
        self.solver = None
        self._motion_cid = None
        self._leave_cid = None

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
        scatter_disp = self.ax_disp.scatter(disp_raw_mm, depth_raw, color="#2563eb", label="原始点")
        # 绘制拟合曲线：紫色实线，标签为"拟合曲线"
        line_disp = self.ax_disp.plot(disp_fit_mm, depth_dense, color="#7c3aed", label="拟合曲线")[0]

        # 设置标题和坐标轴标签
        self.ax_disp.set_title("多项式拟合函数", fontsize=12, fontweight='bold', pad=10)
        self.ax_disp.set_xlabel("位移 (mm)")
        self.ax_disp.set_ylabel("深度 (m)")

        # 添加网格线，透明度0.3
        self.ax_disp.grid(True, alpha=0.3, color="#d1d5db")
        # 添加图例，位置自动选择最佳
        self.ax_disp.legend(loc="best")

        # ===== 右侧弯矩子图 =====
        # 绘制弯矩曲线：绿色实线，标签为"弯矩"
        # X轴是弯矩，Y轴是深度
        line_moment = self.ax_moment.plot(moment, depth_dense, color="#16a34a", label="弯矩")[0]

        # 设置标题和坐标轴标签
        self.ax_moment.set_title("弯矩函数", fontsize=12, fontweight='bold', pad=10)
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

        # ===== 为原始数据点添加悬停提示 =====
        # 使用 mplcursors 显示原始测量点的精确数据
        # hover=2: 鼠标悬停时显示，移开时自动移除
        cursor_scatter = mplcursors.cursor(scatter_disp, hover=2)
        cursor_scatter.connect(
            "add", lambda sel: sel.annotation.set_text(
                f"原始点\n深度: {sel.target[1]:.2f} m\n位移: {sel.target[0]:.2f} mm"
            )
        )

        # ===== 初始化交互式十字线跟踪 =====
        if self.solver is not None:
            # 每次都重新创建 CrosshairCursor，因为 clear() 删除了之前的图形元素
            self.crosshair = CrosshairCursor(
                self.ax_disp, self.ax_moment, self.solver
            )

            # 仅在首次时连接鼠标事件
            if self._motion_cid is None:
                self._motion_cid = self.mpl_connect(
                    'motion_notify_event', self._on_mouse_move
                )
            if self._leave_cid is None:
                self._leave_cid = self.mpl_connect(
                    'axes_leave_event', self._on_axes_leave
                )

        # 延迟绘制，提高性能
        self.draw_idle()

    def set_solver(self, solver):
        """
        设置 PileSolver 实例用于交互式查询

        Args:
            solver: PileSolver 实例，已完成数据拟合
        """
        self.solver = solver

    def _on_mouse_move(self, event):
        """
        处理鼠标移动事件

        Args:
            event: matplotlib motion_notify_event
        """
        if self.crosshair is None:
            return

        # 检查鼠标是否在任一子图中
        if event.inaxes in [self.ax_disp, self.ax_moment]:
            # 使用 Y 坐标作为深度（Y 轴已反转）
            depth_y = event.ydata
            if depth_y is not None:
                self.crosshair.update(depth_y)
                self.draw_idle()
        else:
            # 鼠标在图形区域但不在子图内
            self.crosshair.hide()
            self.draw_idle()

    def _on_axes_leave(self, event):
        """
        处理鼠标离开子图事件

        Args:
            event: matplotlib axes_leave_event
        """
        if self.crosshair is not None:
            self.crosshair.hide()
            self.draw_idle()

    def cleanup_events(self):
        """断开事件处理器，防止内存泄漏"""
        if self._motion_cid is not None:
            self.mpl_disconnect(self._motion_cid)
            self._motion_cid = None
        if self._leave_cid is not None:
            self.mpl_disconnect(self._leave_cid)
            self._leave_cid = None

