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

    跟踪鼠标移动并显示对应深度的位移、弯矩、剪力和土压力信息。
    当鼠标离开图表时自动隐藏。
    """

    def __init__(self, ax_disp, ax_moment, ax_shear, ax_pressure, solver):
        """
        初始化十字线光标

        Args:
            ax_disp: 位移子图
            ax_moment: 弯矩子图
            ax_shear: 剪力子图
            ax_pressure: 土压力子图
            solver: PileSolver 实例，用于查询数值
        """
        self.ax_disp = ax_disp
        self.ax_moment = ax_moment
        self.ax_shear = ax_shear
        self.ax_pressure = ax_pressure
        self.solver = solver

        # 创建水平线（跟踪深度）- 四张图
        self.hline_disp = ax_disp.axhline(
            y=0, color='#6366f1', linewidth=1,
            linestyle='--', alpha=0.7, visible=False
        )
        self.hline_moment = ax_moment.axhline(
            y=0, color='#6366f1', linewidth=1,
            linestyle='--', alpha=0.7, visible=False
        )
        self.hline_shear = ax_shear.axhline(
            y=0, color='#6366f1', linewidth=1,
            linestyle='--', alpha=0.7, visible=False
        )
        self.hline_pressure = ax_pressure.axhline(
            y=0, color='#6366f1', linewidth=1,
            linestyle='--', alpha=0.7, visible=False
        )

        # 创建标注框 - 四张图
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
        self.annot_shear = ax_shear.annotate(
            '', xy=(0, 0), xytext=(10, 10),
            textcoords='offset points',
            bbox=dict(boxstyle='round,pad=0.5', fc='#ffffff',
                     ec='#f97316', alpha=0.95, linewidth=2),
            fontsize=10, visible=False
        )
        self.annot_pressure = ax_pressure.annotate(
            '', xy=(0, 0), xytext=(10, 10),
            textcoords='offset points',
            bbox=dict(boxstyle='round,pad=0.5', fc='#ffffff',
                     ec='#dc2626', alpha=0.95, linewidth=2),
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
            self.hline_shear.set_ydata([depth_y])
            self.hline_pressure.set_ydata([depth_y])

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

            # 更新剪力标注
            self.annot_shear.xy = (result.shear, depth_y)
            self.annot_shear.set_text(
                f"深度: {depth_y:.2f} m\n"
                f"剪力: {result.shear:.2f} kN"
            )

            # 更新土压力标注
            self.annot_pressure.xy = (result.pressure, depth_y)
            self.annot_pressure.set_text(
                f"深度: {depth_y:.2f} m\n"
                f"土压力: {result.pressure:.2f} kPa"
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
        self.hline_shear.set_visible(True)
        self.hline_pressure.set_visible(True)
        self.annot_disp.set_visible(True)
        self.annot_moment.set_visible(True)
        self.annot_shear.set_visible(True)
        self.annot_pressure.set_visible(True)
        self.visible = True

    def hide(self):
        """隐藏光标和标注"""
        self.hline_disp.set_visible(False)
        self.hline_moment.set_visible(False)
        self.hline_shear.set_visible(False)
        self.hline_pressure.set_visible(False)
        self.annot_disp.set_visible(False)
        self.annot_moment.set_visible(False)
        self.annot_shear.set_visible(False)
        self.annot_pressure.set_visible(False)
        self.visible = False


class PlotCanvas(FigureCanvasQTAgg):
    """
    自定义Matplotlib画布组件

    继承自FigureCanvasQTAgg，专门用于显示围护桩的位移、弯矩、剪力和土压力曲线。
    采用2×2网格布局，支持实时更新绘图。
    """

    def __init__(self, parent=None):
        """
        初始化绘图画布

        改为浅色背景，设置中文友好字体以避免缺字警告。
        使用2×2网格布局显示四张图表。
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

        # 创建2×2子图布局
        # 左上：位移曲线 (221)
        self.ax_disp = self.fig.add_subplot(221)
        # 右上：弯矩曲线 (222)
        self.ax_moment = self.fig.add_subplot(222)
        # 左下：剪力曲线 (223)
        self.ax_shear = self.fig.add_subplot(223)
        # 右下：土压力曲线 (224)
        self.ax_pressure = self.fig.add_subplot(224)

        # 预设Y轴方向：岩土工程习惯，深度向下为正
        self.ax_disp.invert_yaxis()
        self.ax_moment.invert_yaxis()
        self.ax_shear.invert_yaxis()
        self.ax_pressure.invert_yaxis()

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
        shear,
        pressure,
    ):
        """
        绘制位移、弯矩、剪力和土压力曲线

        清除旧图，在四个子图中分别绘制数据。
        采用科技风格配色。
        符合岩土工程习惯：X轴为物理量，Y轴为深度。

        Args:
            depth_raw: 原始深度数据数组
            disp_raw_mm: 原始位移数据数组（毫米）
            depth_dense: 密集深度坐标（用于绘制平滑曲线）
            disp_fit_mm: 拟合位移数据（毫米）
            moment: 弯矩数据（kN·m）
            shear: 剪力数据（kN）
            pressure: 土压力数据（kPa）
        """
        # 清除之前的绘图内容
        self.ax_disp.clear()
        self.ax_moment.clear()
        self.ax_shear.clear()
        self.ax_pressure.clear()

        # ===== 左上：位移子图 =====
        # 绘制原始数据点：蓝色圆点
        scatter_disp = self.ax_disp.scatter(disp_raw_mm, depth_raw, color="#2563eb", label="原始点")
        # 绘制拟合曲线：紫色实线
        self.ax_disp.plot(disp_fit_mm, depth_dense, color="#7c3aed", label="拟合曲线")

        self.ax_disp.set_title("位移曲线", fontsize=12, fontweight='bold', pad=10)
        self.ax_disp.set_xlabel("位移 (mm)")
        self.ax_disp.set_ylabel("深度 (m)")
        self.ax_disp.grid(True, alpha=0.3, color="#d1d5db")
        self.ax_disp.legend(loc="best")

        # ===== 右上：弯矩子图 =====
        self.ax_moment.plot(moment, depth_dense, color="#16a34a", label="弯矩", linewidth=2)

        self.ax_moment.set_title("弯矩曲线", fontsize=12, fontweight='bold', pad=10)
        self.ax_moment.set_xlabel("弯矩 (kN·m)")
        self.ax_moment.set_ylabel("深度 (m)")
        self.ax_moment.grid(True, alpha=0.3, color="#d1d5db")
        self.ax_moment.legend(loc="best")

        # ===== 左下：剪力子图 =====
        self.ax_shear.plot(shear, depth_dense, color="#f97316", label="剪力", linewidth=2)

        self.ax_shear.set_title("剪力曲线", fontsize=12, fontweight='bold', pad=10)
        self.ax_shear.set_xlabel("剪力 (kN)")
        self.ax_shear.set_ylabel("深度 (m)")
        self.ax_shear.grid(True, alpha=0.3, color="#d1d5db")
        self.ax_shear.legend(loc="best")

        # ===== 右下：土压力子图 =====
        self.ax_pressure.plot(pressure, depth_dense, color="#dc2626", label="土压力", linewidth=2)

        self.ax_pressure.set_title("土压力曲线（仅供参考，数值可能极不稳定）", fontsize=12, fontweight='bold', pad=10)
        self.ax_pressure.set_xlabel("土压力 (kPa)")
        self.ax_pressure.set_ylabel("深度 (m)")
        self.ax_pressure.grid(True, alpha=0.3, color="#d1d5db")
        self.ax_pressure.legend(loc="best")

        # 反转Y轴：岩土工程习惯，深度向下为正
        self.ax_disp.invert_yaxis()
        self.ax_moment.invert_yaxis()
        self.ax_shear.invert_yaxis()
        self.ax_pressure.invert_yaxis()

        # 重新调整布局，确保元素不重叠
        self.fig.tight_layout(pad=2.0)

        # ===== 为原始数据点添加悬停提示 =====
        cursor_scatter = mplcursors.cursor(scatter_disp, hover=2)
        cursor_scatter.connect(
            "add", lambda sel: sel.annotation.set_text(
                f"原始点\n深度: {sel.target[1]:.2f} m\n位移: {sel.target[0]:.2f} mm"
            )
        )

        # ===== 初始化交互式十字线跟踪 =====
        if self.solver is not None:
            self.crosshair = CrosshairCursor(
                self.ax_disp, self.ax_moment, self.ax_shear, self.ax_pressure, self.solver
            )

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
        if event.inaxes in [self.ax_disp, self.ax_moment, self.ax_shear, self.ax_pressure]:
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

