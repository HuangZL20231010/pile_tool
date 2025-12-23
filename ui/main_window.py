"""
PileBackAnalysis主窗口

这是应用程序的主界面窗口，负责整合所有UI组件和业务逻辑。
采用左右分栏布局：左侧控制面板，右侧绘图和统计区域。
"""

from __future__ import annotations

from PyQt6 import QtCore, QtGui, QtWidgets

from core.calculator import PileSolver
from core import utils
from .components import DataInputGroup, FitControlGroup, ParamsGroup, QueryGroup, StatsBar, WelcomePlaceholder
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

        # 应用浅色科技风主题
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

        # 初始状态下禁用查询按钮（需要先计算才能查询）
        self.query_group.query_btn.setEnabled(False)

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
        left_panel.setSpacing(16)  # 增加组件之间的间距
        left_panel.setContentsMargins(16, 16, 16, 16)  # 添加内边距

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
        left_widget.setFixedWidth(400)
        # 设置左侧面板背景色，与右侧区分
        left_widget.setObjectName("leftPanel")

        # ===== 右侧绘图面板 =====
        # 创建堆叠窗口，用于切换欢迎页和结果页
        self.right_stack = QtWidgets.QStackedWidget()
        self.right_stack.setObjectName("rightStack")

        # Page 0: 欢迎占位页面（计算前显示）
        self.welcome_page = WelcomePlaceholder()
        self.right_stack.addWidget(self.welcome_page)

        # Page 1: 结果页面（计算后显示）
        results_widget = QtWidgets.QWidget()
        results_widget.setObjectName("resultsPage")
        results_layout = QtWidgets.QVBoxLayout(results_widget)
        results_layout.setSpacing(16)
        results_layout.setContentsMargins(16, 16, 16, 16)

        # 图表容器（带卡片样式）
        plot_container = QtWidgets.QWidget()
        plot_container.setObjectName("plotContainer")
        plot_container_layout = QtWidgets.QVBoxLayout(plot_container)
        plot_container_layout.setContentsMargins(0, 0, 0, 0)
        plot_container_layout.addWidget(self.plot_canvas)

        results_layout.addWidget(plot_container, stretch=1)  # 绘图画布（占用大部分空间）
        results_layout.addWidget(self.stats_bar)  # 统计信息栏（底部）

        self.right_stack.addWidget(results_widget)

        # 默认显示欢迎页面
        self.right_stack.setCurrentIndex(0)

        # 创建右侧面板容器控件
        right_panel = QtWidgets.QVBoxLayout()
        right_panel.setSpacing(0)
        right_panel.setContentsMargins(0, 0, 0, 0)
        right_panel.addWidget(self.right_stack)

        right_widget = QtWidgets.QWidget()
        right_widget.setObjectName("rightPanel")
        right_widget.setLayout(right_panel)

        # ===== 主布局 =====
        main_layout = QtWidgets.QHBoxLayout()
        main_layout.setSpacing(0)  # 取消间距，让左右面板紧贴
        main_layout.setContentsMargins(0, 0, 0, 0)  # 取消边距
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

    def keyPressEvent(self, event):
        """
        处理键盘按键事件

        Args:
            event: QKeyEvent 键盘事件对象
        """
        # 检测ESC键
        if event.key() == QtCore.Qt.Key.Key_Escape:
            # 关闭窗口，退出程序
            self.close()
        else:
            # 其他按键交给父类处理
            super().keyPressEvent(event)

    def _apply_theme(self):
        """
        应用现代卡片式设计主题

        设置现代化的卡片风格UI，包括阴影、圆角和精致的间距。
        包括调色板和样式表两部分设置。
        """
        # ===== 调色板设置 =====
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor("#f8fafc"))
        palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor("#ffffff"))
        palette.setColor(QtGui.QPalette.ColorRole.Text, QtGui.QColor("#0f172a"))
        palette.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QColor("#2563eb"))
        palette.setColor(QtGui.QPalette.ColorRole.ButtonText, QtGui.QColor("#ffffff"))
        self.setPalette(palette)

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

        self.setStyleSheet(
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

    def _fill_default_data_to_textbox(self, depths, disps):
        """
        将默认数据填充到文本框

        Args:
            depths: 深度列表
            disps: 位移列表
        """
        # 构建文本内容，每行格式：深度\t位移
        lines = [f"{d:.2f}\t{disp:.2f}" for d, disp in zip(depths, disps)]
        text = "\n".join(lines)
        self.data_group.text_edit.setPlainText(text)

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
                # 将默认数据填充到文本框
                self._fill_default_data_to_textbox(depths, disps)
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
            algo_type = self.fit_group.get_algo_type()
            param_value = self.fit_group.slider.value()
            print(f"[DEBUG] 参数: E={E_val}{E_unit}, section={section_type}, dims={dims}, algo={algo_type}, param={param_value}")

            # ===== 步骤3: 执行计算 =====
            # 连接 solver 到绘图画布，用于交互式十字线跟踪
            self.plot_canvas.set_solver(self.solver)
            self.solver.set_parameters(E_val, E_unit, section_type, dims)
            # 根据算法类型选择参数
            if algo_type == "polynomial":
                self.solver.fit_data(depths, disps, degree=param_value, algo_type="polynomial")
            elif algo_type == "spline":
                sigma = self.fit_group.get_sigma_value()
                self.solver.fit_data(depths, disps, algo_type="spline", sigma_mm=sigma)
                # 计算并打印 s 值
                sigma_m = sigma / 1000.0
                s = len(depths) * (sigma_m ** 2)
                print(f"[DEBUG] 样条参数: σ={sigma:.3f}mm, N={len(depths)}, s={s}")
                # 更新 s 显示
                self.fit_group.update_s_display(len(depths))
            else:
                # 五次样条
                sigma = self.fit_group.get_sigma_value()
                self.solver.fit_data(depths, disps, algo_type="spline5", sigma_mm=sigma)
                # 计算并打印 s 值
                sigma_m = sigma / 1000.0
                s = len(depths) * (sigma_m ** 2)
                print(f"[DEBUG] 样条参数: σ={sigma:.3f}mm, N={len(depths)}, s={s}")
                # 更新 s 显示
                self.fit_group.update_s_display(len(depths))
            depth_dense, disp_fit_mm, moment, shear, pressure = self.solver.get_results_arrays()
            print(f"[DEBUG] 拟合完成: algo={algo_type}")

            # ===== 步骤4: 计算统计信息 =====
            import numpy as np
            mmax = float(np.max(np.abs(moment))) if len(moment) else 0.0
            qmax = float(np.max(np.abs(shear))) if len(shear) else 0.0
            pmax = float(np.max(np.abs(pressure))) if len(pressure) else 0.0
            r2 = self.solver.fitting_stats.get("R2", 0.0)
            rmse_mm = self.solver.fitting_stats.get("RMSE_mm", 0.0)
            print(f"[DEBUG] 统计: R2={r2:.4f}, RMSE={rmse_mm:.4f}mm, Mmax={mmax:.3f}kN·m, Qmax={qmax:.3f}kN, pmax={pmax:.3f}kPa")

            # ===== 步骤5: 更新界面 =====
            # 获取多项式表达式
            poly_expr = self.solver.get_polynomial_expression()
            # 获取弯矩函数表达式
            moment_expr = self.solver.get_moment_expression()
            # 更新图表和统计信息
            self.plot_canvas.plot(depths, disps, depth_dense, disp_fit_mm, moment, shear, pressure)
            self.stats_bar.update_stats(r2, rmse_mm, mmax, qmax, pmax, poly_expr, moment_expr, algo_type)

            # 切换到结果页面
            self.right_stack.setCurrentIndex(1)

            # 启用查询按钮
            self.query_group.query_btn.setEnabled(True)

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
                f"弯矩: {result.moment:.3f} kN·m\n"    # 弯矩值
                f"剪力: {result.shear:.3f} kN\n"       # 剪力值
                f"土压力: {result.pressure:.3f} kPa"   # 土压力值
            )

            # 显示信息对话框
            QtWidgets.QMessageBox.information(self, "查询结果", msg)

        except Exception as exc:  # noqa: BLE001
            # 显示警告对话框提示错误
            QtWidgets.QMessageBox.warning(self, "提示", str(exc))

