"""
PileBackAnalysis主窗口

这是应用程序的主界面窗口，负责整合所有UI组件和业务逻辑。
采用左右分栏布局：左侧控制面板，右侧绘图和统计区域。
"""

from __future__ import annotations

from PyQt6 import QtCore, QtGui, QtWidgets

from core.calculator import PileSolver
from core import utils
from .components import DataInputGroup, FitControlGroup, ParamsGroup, QueryGroup, StatsBar
from .plotting import PlotCanvas


class MainWindow(QtWidgets.QMainWindow):
    """
    主窗口类

    继承自QMainWindow，构建完整的应用程序界面。
    包含数据输入、参数设置、绘图显示、统计信息等所有功能模块。
    """

    def __init__(self):
        """
        初始化主窗口

        设置窗口基本属性，创建核心求解器实例和所有UI组件，
        然后构建布局并连接信号槽。
        """
        # 调用父类构造函数
        super().__init__()

        # 设置窗口标题和初始尺寸
        self.setWindowTitle("围护桩反分析工具 - PileBackAnalysis")
        self.resize(1200, 720)

        # 应用科技风格主题
        self._apply_theme()

        # 创建核心计算引擎实例
        self.solver = PileSolver()

        # 创建所有UI组件实例
        self.data_group = DataInputGroup()      # 数据输入组件
        self.params_group = ParamsGroup()       # 参数设置组件
        self.fit_group = FitControlGroup()      # 拟合控制组件
        self.query_group = QueryGroup()         # 查询组件
        self.stats_bar = StatsBar()             # 统计信息栏
        self.plot_canvas = PlotCanvas()         # 绘图画布

        # 构建窗口布局
        self._build_layout()
        # 连接信号和槽函数
        self._connect_signals()

    def _build_layout(self):
        """
        构建窗口布局

        创建左右分栏布局：
        - 左侧：控制面板（固定宽度）
        - 右侧：绘图和统计区域（可伸缩）
        """
        # ===== 左侧控制面板 =====
        left_panel = QtWidgets.QVBoxLayout()
        # 依次添加各个控制组件
        left_panel.addWidget(self.data_group)   # 数据输入
        left_panel.addWidget(self.params_group) # 参数设置
        left_panel.addWidget(self.fit_group)    # 拟合控制
        left_panel.addWidget(self.query_group)  # 查询功能
        # 添加伸缩空间，将以上组件推到顶部
        left_panel.addStretch(1)

        # 创建左侧面板容器控件
        left_widget = QtWidgets.QWidget()
        left_widget.setLayout(left_panel)
        # 设置固定宽度，确保布局稳定
        left_widget.setFixedWidth(360)

        # ===== 右侧绘图面板 =====
        right_panel = QtWidgets.QVBoxLayout()
        right_panel.addWidget(self.plot_canvas)  # 绘图画布（占用大部分空间）
        right_panel.addWidget(self.stats_bar)    # 统计信息栏（底部）

        # 创建右侧面板容器控件
        right_widget = QtWidgets.QWidget()
        right_widget.setLayout(right_panel)

        # ===== 主布局 =====
        main_layout = QtWidgets.QHBoxLayout()
        main_layout.addWidget(left_widget)           # 左侧面板
        main_layout.addWidget(right_widget, stretch=1)  # 右侧面板，可伸缩

        # 创建中央控件并设置为主窗口的中央部件
        central = QtWidgets.QWidget()
        central.setLayout(main_layout)
        self.setCentralWidget(central)

    def _connect_signals(self):
        """
        连接信号和槽函数

        建立UI组件的事件响应机制：
        - 计算按钮点击 -> 执行拟合计算
        - 查询按钮点击 -> 执行单点查询
        """
        # 连接计算按钮的点击信号到计算处理函数
        self.fit_group.calc_button.clicked.connect(self.on_calculate_clicked)
        # 连接查询按钮的点击信号到查询处理函数
        self.query_group.query_clicked.connect(self.on_query_clicked)

    def _apply_theme(self):
        """
        应用科技风格主题

        设置深色背景、霓虹色点缀的现代化UI风格。
        包括调色板和样式表两部分设置。
        """
        # ===== 调色板设置 =====
        palette = QtGui.QPalette()
        # 窗口背景色：深蓝黑
        palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor("#0b1224"))
        # 控件背景色：深蓝黑
        palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor("#0b1224"))
        # 文本颜色：浅灰白
        palette.setColor(QtGui.QPalette.ColorRole.Text, QtGui.QColor("#e2e8f0"))
        # 按钮背景色：深灰
        palette.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QColor("#111827"))
        # 按钮文本色：浅灰白
        palette.setColor(QtGui.QPalette.ColorRole.ButtonText, QtGui.QColor("#e2e8f0"))
        # 应用调色板到窗口
        self.setPalette(palette)

        # ===== 样式表设置 =====
        # 定义主题色：青色霓虹
        accent = "#00e5ff"

        # 设置详细的CSS样式
        self.setStyleSheet(
            f"""
            /* 全局样式 */
            QWidget {{
                color: #e2e8f0;                    /* 文本颜色 */
                background-color: #0b1224;        /* 背景色 */
            }}

            /* 分组框样式 */
            QGroupBox {{
                border: 1px solid #1f2937;        /* 边框色 */
                border-radius: 6px;              /* 圆角 */
                margin-top: 8px;                 /* 上边距 */
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;       /* 标题位置 */
                left: 10px;                      /* 左边距 */
                padding: 0 4px;                  /* 内边距 */
                color: #8b9cb8;                  /* 标题颜色 */
            }}

            /* 输入框样式 */
            QLineEdit, QTextEdit {{
                background-color: #0f172a;       /* 输入框背景 */
                border: 1px solid #1f2937;       /* 边框 */
                border-radius: 4px;             /* 圆角 */
            }}

            /* 按钮样式 */
            QPushButton {{
                background-color: #111827;       /* 按钮背景 */
                border: 1px solid #1f2937;       /* 边框 */
                border-radius: 4px;             /* 圆角 */
                padding: 6px 10px;              /* 内边距 */
            }}
            QPushButton:hover {{
                border-color: {accent};         /* 悬停边框色 */
                color: {accent};                /* 悬停文本色 */
            }}
            QPushButton:pressed {{
                background-color: #1f2937;      /* 按下背景色 */
            }}

            /* 滑块样式 */
            QSlider::groove:horizontal {{
                height: 6px;                    /* 滑轨高度 */
                background: #1f2937;            /* 滑轨背景 */
                border-radius: 3px;             /* 圆角 */
            }}
            QSlider::handle:horizontal {{
                background: {accent};           /* 滑块颜色 */
                width: 14px;                    /* 滑块宽度 */
                margin: -4px 0;                 /* 垂直居中 */
                border-radius: 7px;             /* 圆角 */
            }}
            """
        )

    def _get_default_data(self):
        """默认测试数据：深度(m), 位移(mm)。"""
        default_data = [
            (0.50, -0.29), (1.00, -0.81), (1.50, -1.06), (2.00, -0.98), (2.50, -0.41),
            (3.00, -0.16), (3.50, -0.07), (4.00, 0.24), (4.50, 0.53), (5.00, 0.83),
            (5.50, 1.17), (6.00, 1.17), (6.50, 1.33), (7.00, 1.69), (7.50, 1.93),
            (8.00, 1.45), (8.50, 0.84), (9.00, 0.63), (9.50, -0.14), (10.00, -0.32),
            (10.50, -0.35), (11.00, -0.66), (11.50, -0.75), (12.00, -0.15),
        ]
        depths = [d[0] for d in default_data]
        disps = [d[1] for d in default_data]
        return depths, disps

    def _set_default_params(self):
        """为默认数据写入参数：E=30000 MPa，圆形 D=800mm。"""
        self.params_group.E_input.setText("30000")
        self.params_group.E_unit.setCurrentText("MPa")
        self.params_group.circle_radio.setChecked(True)
        self.params_group.D_input.setText("800")

    def _read_section_dims(self, section_type: str):
        """
        读取截面尺寸参数

        根据截面类型从UI控件中读取相应的尺寸参数。

        Args:
            section_type (str): 截面类型，"circle" 或 "rect"

        Returns:
            dict: 尺寸参数字典
                - 圆形: {"D": 直径值}
                - 矩形: {"b": 宽度, "h": 高度}
        """
        if section_type == "circle":
            # 圆形截面：读取直径输入框的值
            return {"D": float(self.params_group.D_input.text() or 0)}
        else:
            # 矩形截面：读取宽度和高度输入框的值
            return {
                "b": float(self.params_group.b_input.text() or 0),  # 宽度
                "h": float(self.params_group.h_input.text() or 0),  # 高度
            }

    def on_calculate_clicked(self):
        """
        计算按钮点击处理函数

        执行完整的计算流程：
        1. 解析输入数据
        2. 读取参数设置
        3. 执行拟合计算
        4. 更新绘图和统计信息

        包含完善的错误处理，会弹出错误对话框提示用户。
        """
        try:
            # ===== 步骤1: 解析输入数据 =====
            raw_text = self.data_group.text_edit.toPlainText().strip()
            if not raw_text:
                depths, disps = self._get_default_data()
                self._set_default_params()
                print("[DEBUG] 使用默认数据与参数")
            else:
                depths, disps = utils.parse_depth_disp(raw_text)
            print(f"[DEBUG] 数据点数量={len(depths)}, depths[:3]={depths[:3]}")

            if len(depths) < 2:
                raise ValueError("请输入至少两行有效的深度/位移数据")

            # ===== 步骤2: 读取参数设置 =====
            E_val = float(self.params_group.E_input.text())
            E_unit = self.params_group.E_unit.currentText()
            section_type = self.params_group.section_type()
            dims = self._read_section_dims(section_type)
            degree = self.fit_group.slider.value()
            print(f"[DEBUG] 参数: E={E_val}{E_unit}, section={section_type}, dims={dims}, degree={degree}")

            # ===== 步骤3: 执行计算 =====
            self.solver.set_parameters(E_val, E_unit, section_type, dims)
            self.solver.fit_data(depths, disps, degree=degree)
            x_dense, y_fit_mm, moment = self.solver.get_results_arrays()
            print(f"[DEBUG] 拟合完成: coeffs={self.solver.poly_coeffs}")

            # ===== 步骤4: 计算统计信息 =====
            mmax = float(moment.max()) if len(moment) else 0.0
            r2 = self.solver.fitting_stats.get("R2", 0.0)
            rmse_mm = self.solver.fitting_stats.get("RMSE_mm", 0.0)
            print(f"[DEBUG] 统计: R2={r2:.4f}, RMSE={rmse_mm:.4f}mm, Mmax={mmax:.3f}kN·m")

            # ===== 步骤5: 更新界面 =====
            self.plot_canvas.plot(depths, disps, x_dense, y_fit_mm, moment)
            self.stats_bar.update_stats(r2, rmse_mm, mmax)

        except Exception as exc:  # noqa: BLE001
            import traceback

            traceback.print_exc()
            QtWidgets.QMessageBox.critical(self, "错误", str(exc))

    def on_query_clicked(self):
        """
        查询按钮点击处理函数

        执行单点查询功能：
        1. 读取输入的深度值
        2. 调用求解器查询该点的计算结果
        3. 以对话框形式显示结果

        包含错误处理，会显示警告对话框。
        """
        try:
            # 读取输入的深度字符串
            x_str = self.query_group.depth_input.text()
            # 转换为浮点数
            x_val = float(x_str)

            # 调用求解器执行单点查询
            result = self.solver.query_single_point(x_val)

            # 格式化结果信息
            msg = (
                f"深度 {x_val:.3f} m\n"           # 深度值
                f"位移: {result.y_mm:.3f} mm\n"   # 位移值
                f"曲率: {result.curvature:.6f} 1/m\n"  # 曲率值
                f"弯矩: {result.moment:.3f} kN·m"     # 弯矩值
            )

            # 显示信息对话框
            QtWidgets.QMessageBox.information(self, "查询结果", msg)

        except Exception as exc:  # noqa: BLE001
            # 显示警告对话框提示错误
            QtWidgets.QMessageBox.warning(self, "提示", str(exc))

