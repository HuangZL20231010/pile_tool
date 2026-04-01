"""
围护桩反分析工具核心计算引擎

负责多项式拟合、弯矩计算、统计评估等核心算法实现。
采用最小二乘法多项式拟合，通过二阶导数计算曲率，再结合材料参数计算弯矩。
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np

from . import utils
from .mao_spline import prepare_mao_bc, solve_mao_spline, eval_mao_spline
from .bs_stiffness import precompute_bs_params, compute_bs_single, compute_bs_moment
from .optimization import find_optimal_sigma as _find_optimal_sigma

try:
    from numpy import RankWarning
except Exception:  # pragma: no cover
    class RankWarning(UserWarning):
        ...


@dataclass
class QueryResult:
    """
    单点查询结果数据类

    Attributes:
        y_mm (float): 该点的位移值，单位为毫米 (mm)
        curvature (float): 该点的曲率，单位为每米 (1/m)
        moment (float): 该点的弯矩，单位为千牛·米 (kN·m)
        shear (float): 该点的剪力，单位为千牛 (kN)
        pressure (float): 该点的土压力，单位为千帕 (kPa)
    """
    y_mm: float
    curvature: float
    moment: float
    shear: float = 0.0
    pressure: float = 0.0


class PileSolver:
    """
    围护桩计算求解器

    这是整个软件的核心计算引擎，负责：
    - 多项式拟合位移数据
    - 计算二阶导数（曲率）
    - 基于弯曲应力公式 M = E * I * y'' 计算弯矩
    - 提供拟合统计信息和单点查询功能
    """

    def __init__(self):
        """
        初始化求解器

        设置所有计算相关的实例变量为初始状态。
        """
        # 多项式拟合系数，从高次项到低次项排列 [an, an-1, ..., a0]
        self.poly_coeffs: np.ndarray | None = None
        # 位移拟合多项式对象，用于计算任意点的位移值
        self.poly = None
        # 二阶导数多项式对象，用于计算曲率（位移的二阶导数）
        self.poly_second = None
        # 三次样条对象（用于样条拟合模式）
        self.spline = None
        # 当前算法类型：'polynomial' 或 'spline'
        self.algo_type: str = "polynomial"
        # 弹性模量，单位为千帕 (kPa)
        self.E_kpa: float = 0.0
        # 截面惯性矩，单位为立方米 (m^4)
        self.I_m4: float = 0.0
        # 拟合统计信息，包含 R2 和 RMSE
        self.fitting_stats: Dict[str, float] = {}
        # 数据深度范围 (最小深度, 最大深度)，用于生成绘图数组
        self._x_range: Tuple[float, float] | None = None
        # 原始输入的深度数据数组
        self._x_data = None
        # 边界条件设置
        self._boundary_conditions: dict | None = None
        # 论文样条（毛朝辉2006）相关数据
        self._mao_x: np.ndarray | None = None
        self._mao_y_corrected: np.ndarray | None = None
        self._mao_M: np.ndarray | None = None
        self._mao_h: np.ndarray | None = None
        # Bs 迭代刚度（矩形截面钢筋混凝土短期刚度）
        self.use_bs: bool = False
        self._bs_params: dict | None = None

    def _apply_odd_symmetric_mirror(self, x: np.ndarray, y_m: np.ndarray,
                                     bc: dict, n_mirror: int = 5) -> Tuple[np.ndarray, np.ndarray]:
        """
        对数据应用奇对称镜像增强以施加边界条件

        奇对称镜像原理：
        - 对于边界点 (x₀, y₀)，将数据点 (xᵢ, yᵢ) 镜像为 (2x₀-xᵢ, 2y₀-yᵢ)
        - 这使得拟合曲线过 (x₀, y₀) 且在该点二阶导数为 0

        Args:
            x: 深度数组 (m)，已排序
            y_m: 位移数组 (m)
            bc: 边界条件字典
            n_mirror: 镜像点数量，默认5

        Returns:
            (x_augmented, y_augmented): 增强后的排序去重数据
        """
        result_x = list(x)
        result_y = list(y_m)

        # 处理桩顶边界条件
        if bc.get('top_enabled'):
            top_depth = bc['top_depth']
            top_disp_m = bc['top_disp'] / 1000.0

            # 取靠近桩顶的 n_mirror 个点
            n_top = min(n_mirror, len(x))
            x_head = x[:n_top]
            y_head = y_m[:n_top]

            # 生成关于 (top_depth, top_disp_m) 的奇对称镜像
            x_mirror = 2 * top_depth - x_head[::-1]
            y_mirror = 2 * top_disp_m - y_head[::-1]

            # 添加镜像点和边界点
            result_x = list(x_mirror) + [top_depth] + result_x
            result_y = list(y_mirror) + [top_disp_m] + result_y

        # 处理桩底边界条件
        if bc.get('bottom_enabled'):
            bottom_depth = bc['bottom_depth']
            bottom_disp_m = bc['bottom_disp'] / 1000.0

            # 取靠近桩底的 n_mirror 个点
            n_bottom = min(n_mirror, len(x))
            x_tail = x[-n_bottom:]
            y_tail = y_m[-n_bottom:]

            # 生成关于 (bottom_depth, bottom_disp_m) 的奇对称镜像
            x_mirror = 2 * bottom_depth - x_tail[::-1]
            y_mirror = 2 * bottom_disp_m - y_tail[::-1]

            # 添加边界点和镜像点
            result_x = result_x + [bottom_depth] + list(x_mirror)
            result_y = result_y + [bottom_disp_m] + list(y_mirror)

        # 转换为数组并排序去重
        x_aug = np.array(result_x)
        y_aug = np.array(result_y)
        sort_idx = np.argsort(x_aug)
        x_sorted = x_aug[sort_idx]
        y_sorted = y_aug[sort_idx]

        # 去除重复点（容差 1e-10）
        unique_mask = np.diff(x_sorted, prepend=-np.inf) > 1e-10
        return x_sorted[unique_mask], y_sorted[unique_mask]

    def set_parameters(self, E_val: float, E_unit: str, section_type: str, dims: dict,
                       bs_params: dict | None = None):
        """
        设置材料和截面参数

        将用户输入的弹性模量和截面参数转换为计算所需的标准单位。

        Args:
            E_val (float): 弹性模量数值
            E_unit (str): 弹性模量单位，'MPa' 或 'kPa'
            section_type (str): 截面类型，'circle' 为圆形，'rect' 为矩形
            dims (dict): 截面尺寸参数
                - 圆形: {'D': 直径值}，单位为毫米
                - 矩形: {'b': 宽度, 'h': 高度}，单位为毫米
            bs_params (dict | None): Bs 迭代参数（仅矩形截面），包含：
                - h0: 有效高度 (mm)
                - Ec: 混凝土弹性模量 (MPa)
                - As: 钢筋面积 (mm²)
                - ftk: 混凝土抗拉强度标准值 (MPa)

        Note:
            内部会自动转换为标准单位：E 转为 kPa，尺寸转为米
        """
        # 将弹性模量统一转换为 kPa
        self.E_kpa = utils.convert_E_to_kpa(E_val, E_unit)
        # 计算截面惯性矩，自动处理单位转换
        self.I_m4 = utils.compute_inertia(section_type, dims)

        # Bs 迭代刚度设置（两种截面钢筋混凝土）
        if bs_params is not None:
            self.use_bs = True
            Ec_MPa = bs_params['Ec']
            As_mm2 = bs_params['As']
            h0_mm = bs_params['h0']
            ftk_MPa = bs_params['ftk']

            if section_type == "circle":
                # 圆形截面：使用等效矩形参数
                b_mm = bs_params['b_eq']
                h_mm = bs_params['h_eq']
            else:
                b_mm = dims['b']
                h_mm = dims['h']

            self._bs_params = precompute_bs_params(
                Ec_MPa, As_mm2, h0_mm, ftk_MPa, b_mm, h_mm, self.I_m4)
        else:
            self.use_bs = False
            self._bs_params = None

    def fit_data(self, x_depths, y_disps_mm, degree: int = 5,
                 algo_type: str = "polynomial", sigma_mm: float = 0.5,
                 boundary_conditions: dict = None):
        """
        执行数据拟合

        根据选择的算法类型，使用多项式或样条对位移数据进行拟合。

        Args:
            x_depths: 深度数据数组，单位为米 (m)
            y_disps_mm: 位移数据数组，单位为毫米 (mm)
            degree (int): 多项式阶数，默认值为 5（仅多项式模式使用）
            algo_type (str): 算法类型，'polynomial'、'spline' 或 'spline5'
            sigma_mm (float): 测斜仪预估误差，单位为毫米（仅样条模式使用）
                - 默认值 0.5mm
                - 平滑因子 s = N × σ²
            boundary_conditions (dict): 边界条件设置

        Raises:
            ValueError: 当数据点少于 2 个时抛出
        """
        # 将输入数据转换为 numpy 数组，确保数据类型为 float
        x = np.asarray(x_depths, dtype=float)
        # 将位移从毫米转换为米，因为计算公式需要 SI 单位制
        y_m = np.asarray(y_disps_mm, dtype=float) / 1000.0

        # 数据点数量检查，至少需要 2 个点才能进行拟合
        if x.size < 2:
            raise ValueError("至少需要两组数据点用于拟合")

        # 保存算法类型和边界条件
        self.algo_type = algo_type
        self._boundary_conditions = boundary_conditions

        # 检查是否需要应用边界条件
        use_bc = (boundary_conditions is not None and
                  (boundary_conditions.get('top_enabled') or
                   boundary_conditions.get('bottom_enabled')))

        if algo_type == "polynomial":
            # ===== 多项式拟合 =====
            deg = utils.clamp_degree(degree)
            deg = min(deg, x.size - 1) if x.size > 1 else deg

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RankWarning)
                self.poly_coeffs = np.polyfit(x, y_m, deg)

            self.poly = np.poly1d(self.poly_coeffs)
            self.poly_second = np.polyder(self.poly, 2)
            self.spline = None

            y_fit_m = self.poly(x)
        elif algo_type == "spline":
            # ===== 三次样条平滑 =====
            from scipy.interpolate import UnivariateSpline

            sigma_m = sigma_mm / 1000.0
            s = len(y_m) * (sigma_m ** 2)

            sort_idx = np.argsort(x)
            x_sorted = x[sort_idx]
            y_sorted = y_m[sort_idx]

            if use_bc:
                x_fit, y_fit = self._apply_odd_symmetric_mirror(x_sorted, y_sorted, boundary_conditions)
            else:
                x_fit, y_fit = x_sorted, y_sorted

            self.spline = UnivariateSpline(x_fit, y_fit, k=3, s=s)

            self.poly = None
            self.poly_coeffs = None
            self.poly_second = None

            y_fit_m = self.spline(x)

        elif algo_type == "spline5":
            # ===== 五次样条平滑 =====
            from scipy.interpolate import UnivariateSpline

            if x.size < 6:
                raise ValueError("五次样条拟合需要至少6个数据点")

            sigma_m = sigma_mm / 1000.0
            s = len(y_m) * (sigma_m ** 2)

            sort_idx = np.argsort(x)
            x_sorted = x[sort_idx]
            y_sorted = y_m[sort_idx]

            if use_bc:
                x_fit, y_fit = self._apply_odd_symmetric_mirror(x_sorted, y_sorted, boundary_conditions)
            else:
                x_fit, y_fit = x_sorted, y_sorted

            self.spline = UnivariateSpline(x_fit, y_fit, k=5, s=s)

            self.poly = None
            self.poly_coeffs = None
            self.poly_second = None

            y_fit_m = self.spline(x)

        else:
            # ===== 论文样条（毛朝辉2006）=====
            if x.size < 4:
                raise ValueError("论文样条拟合需要至少4个数据点")

            delta_m = sigma_mm / 1000.0

            sort_idx = np.argsort(x)
            x_sorted = x[sort_idx]
            y_sorted = y_m[sort_idx]

            locked = set()
            if use_bc:
                x_fit, y_fit, locked = prepare_mao_bc(x_sorted, y_sorted, boundary_conditions)
            else:
                x_fit, y_fit = x_sorted, y_sorted

            y_corrected, M_full, h_arr = solve_mao_spline(x_fit, y_fit, delta_m,
                                                           locked_indices=locked)

            self._mao_x = x_fit
            self._mao_y_corrected = y_corrected
            self._mao_M = M_full
            self._mao_h = h_arr

            self.poly = None
            self.poly_coeffs = None
            self.poly_second = None
            self.spline = None

            y_fit_m = eval_mao_spline(x, self._mao_x, self._mao_y_corrected,
                                      self._mao_M, self._mao_h, deriv=0)

        # 保存原始数据用于统计计算
        self._x_data = x

        # 记录数据深度范围
        x_min = float(x.min())
        x_max = float(x.max())
        if use_bc:
            if boundary_conditions.get('top_enabled'):
                x_min = min(x_min, boundary_conditions['top_depth'])
            if boundary_conditions.get('bottom_enabled'):
                x_max = max(x_max, boundary_conditions['bottom_depth'])
        self._x_range = (x_min, x_max)

        # 计算拟合统计信息
        ss_res = np.sum((y_m - y_fit_m) ** 2)
        ss_tot = np.sum((y_m - np.mean(y_m)) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot != 0 else 1.0
        rmse_mm = float(np.sqrt(np.mean((y_m - y_fit_m) ** 2)) * 1000.0)

        self.fitting_stats = {"R2": float(r2), "RMSE_mm": rmse_mm}

    def get_results_arrays(self, num_points: int = 100):
        """
        生成用于绘图的密集数据数组

        Args:
            num_points (int): 生成的数据点数量，默认 100

        Returns:
            tuple: (x_dense, y_fit_mm, moment, shear, pressure)

        Raises:
            RuntimeError: 当未执行拟合时抛出
        """
        if self._x_range is None:
            raise RuntimeError("请先执行拟合")

        if self.algo_type == "polynomial":
            if self.poly is None or self.poly_second is None:
                raise RuntimeError("请先执行拟合")
        elif self.algo_type == "mao_spline":
            if self._mao_x is None:
                raise RuntimeError("请先执行拟合")
        else:
            if self.spline is None:
                raise RuntimeError("请先执行拟合")

        x_min, x_max = self._x_range
        if x_min == x_max:
            x_min -= 1.0
            x_max += 1.0

        x_dense = np.linspace(x_min, x_max, num_points)

        if self.algo_type == "polynomial":
            y_fit_m = self.poly(x_dense)
            curvature = self.poly_second(x_dense)
            poly_third = np.polyder(self.poly, 3)
            third_deriv = poly_third(x_dense)
            poly_fourth = np.polyder(self.poly, 4)
            fourth_deriv = poly_fourth(x_dense)
        elif self.algo_type == "spline":
            y_fit_m = self.spline(x_dense)
            curvature = self.spline.derivative(2)(x_dense)
            third_deriv = self.spline.derivative(3)(x_dense)
            fourth_deriv = np.zeros_like(x_dense)
        elif self.algo_type == "spline5":
            y_fit_m = self.spline(x_dense)
            curvature = self.spline.derivative(2)(x_dense)
            third_deriv = self.spline.derivative(3)(x_dense)
            fourth_deriv = self.spline.derivative(4)(x_dense)
        elif self.algo_type == "mao_spline":
            y_fit_m = eval_mao_spline(x_dense, self._mao_x, self._mao_y_corrected,
                                      self._mao_M, self._mao_h, deriv=0)
            curvature = eval_mao_spline(x_dense, self._mao_x, self._mao_y_corrected,
                                        self._mao_M, self._mao_h, deriv=2)
            third_deriv = eval_mao_spline(x_dense, self._mao_x, self._mao_y_corrected,
                                          self._mao_M, self._mao_h, deriv=3)
            fourth_deriv = np.zeros_like(x_dense)

        # 计算弯矩、剪力、土压力
        if self.use_bs:
            moment = compute_bs_moment(curvature, self._bs_params)
            shear = np.gradient(moment, x_dense)
            pressure = np.gradient(shear, x_dense)
        else:
            moment = self.E_kpa * self.I_m4 * curvature
            shear = self.E_kpa * self.I_m4 * third_deriv
            pressure = self.E_kpa * self.I_m4 * fourth_deriv

        y_fit_mm = y_fit_m * 1000.0

        return x_dense, y_fit_mm, moment, shear, pressure

    def query_single_point(self, x_query: float) -> QueryResult:
        """
        查询特定深度的计算结果

        Args:
            x_query (float): 查询的深度，单位为米

        Returns:
            QueryResult: 包含位移、曲率、弯矩、剪力和土压力的查询结果对象

        Raises:
            RuntimeError: 当未执行拟合时抛出
        """
        if self.algo_type == "polynomial":
            if self.poly is None or self.poly_second is None:
                raise RuntimeError("请先执行拟合")
            y_m = float(self.poly(x_query))
            curvature = float(self.poly_second(x_query))
            poly_third = np.polyder(self.poly, 3)
            third_deriv = float(poly_third(x_query))
            poly_fourth = np.polyder(self.poly, 4)
            fourth_deriv = float(poly_fourth(x_query))
        elif self.algo_type == "spline":
            if self.spline is None:
                raise RuntimeError("请先执行拟合")
            y_m = float(self.spline(x_query))
            curvature = float(self.spline.derivative(2)(x_query))
            third_deriv = float(self.spline.derivative(3)(x_query))
            fourth_deriv = 0.0
        elif self.algo_type == "spline5":
            if self.spline is None:
                raise RuntimeError("请先执行拟合")
            y_m = float(self.spline(x_query))
            curvature = float(self.spline.derivative(2)(x_query))
            third_deriv = float(self.spline.derivative(3)(x_query))
            fourth_deriv = float(self.spline.derivative(4)(x_query))
        elif self.algo_type == "mao_spline":
            if self._mao_x is None:
                raise RuntimeError("请先执行拟合")
            x_arr = np.array([x_query])
            y_m = float(eval_mao_spline(x_arr, self._mao_x, self._mao_y_corrected,
                                        self._mao_M, self._mao_h, deriv=0)[0])
            curvature = float(eval_mao_spline(x_arr, self._mao_x, self._mao_y_corrected,
                                              self._mao_M, self._mao_h, deriv=2)[0])
            third_deriv = float(eval_mao_spline(x_arr, self._mao_x, self._mao_y_corrected,
                                                self._mao_M, self._mao_h, deriv=3)[0])
            fourth_deriv = 0.0

        # 计算弯矩、剪力、土压力
        if self.use_bs:
            _, moment = compute_bs_single(curvature, self._bs_params)
            moment = float(moment)
            # 用中心差分求 Q 和 p
            dx = 0.001
            x_pts = np.array([x_query - dx, x_query, x_query + dx])
            if self.algo_type == "polynomial":
                curv_pts = np.array([float(self.poly_second(xp)) for xp in x_pts])
            elif self.algo_type in ("spline", "spline5"):
                curv_pts = np.array([float(self.spline.derivative(2)(xp)) for xp in x_pts])
            elif self.algo_type == "mao_spline":
                curv_pts = eval_mao_spline(x_pts, self._mao_x, self._mao_y_corrected,
                                           self._mao_M, self._mao_h, deriv=2)
            m_pts = np.array([compute_bs_single(float(c), self._bs_params)[1] for c in curv_pts])
            shear = float((m_pts[2] - m_pts[0]) / (2 * dx))
            pressure = float((m_pts[2] - 2 * m_pts[1] + m_pts[0]) / (dx ** 2))
        else:
            moment = float(self.E_kpa * self.I_m4 * curvature)
            shear = float(self.E_kpa * self.I_m4 * third_deriv)
            pressure = float(self.E_kpa * self.I_m4 * fourth_deriv)

        return QueryResult(
            y_mm=y_m * 1000.0,
            curvature=curvature,
            moment=moment,
            shear=shear,
            pressure=pressure
        )

    def get_polynomial_expression(self, precision: int = 4) -> str:
        """
        获取格式化的拟合函数表达式

        Args:
            precision: 小数精度，默认 4 位

        Returns:
            格式化的表达式字符串
        """
        if self.algo_type == "spline":
            if self.spline is None:
                return ""
            return "Cubic Smoothing Spline (分段函数)"

        if self.algo_type == "spline5":
            if self.spline is None:
                return ""
            return "Quintic Smoothing Spline (分段函数)"

        if self.algo_type == "mao_spline":
            if self._mao_x is None:
                return ""
            return "光顺样条 (分段函数)"

        if self.poly_coeffs is None:
            return ""

        return utils.format_polynomial(self.poly_coeffs, var='x', precision=precision)

    def get_moment_expression(self, precision: int = 3) -> str:
        """
        获取格式化的弯矩函数表达式

        Args:
            precision: 小数精度，默认 3 位

        Returns:
            格式化的弯矩表达式字符串
        """
        if self.algo_type in ("spline", "spline5", "mao_spline"):
            if self.algo_type == "mao_spline":
                if self._mao_x is None:
                    return ""
            else:
                if self.spline is None:
                    return ""
            if self.use_bs:
                return "M(x) = Bs(x)·y''(x) (逐点迭代)"
            return "M(x) = E·I·y''(x) (分段函数)"

        if self.poly_second is None or self.E_kpa is None or self.I_m4 is None:
            return ""

        if self.use_bs:
            return "M(x) = Bs(x)·y''(x) (逐点迭代)"

        second_deriv_coeffs = self.poly_second.coefficients
        moment_coeffs = second_deriv_coeffs * self.E_kpa * self.I_m4

        moment_expr = utils.format_polynomial(moment_coeffs, var='x', precision=precision)

        if moment_expr.startswith("y = "):
            return "M(x) = " + moment_expr[4:]

        return moment_expr

    def find_optimal_sigma(self, x_depths, y_disps_mm,
                           algo_type: str = "spline",
                           sigma_range: tuple = (0.001, 1.0),
                           n_candidates: int = 50,
                           boundary_conditions: dict = None) -> float:
        """
        使用 L-curve 法自动选择最优 σ

        Args:
            x_depths: 深度数据数组 (m)
            y_disps_mm: 位移数据数组 (mm)
            algo_type: 算法类型
            sigma_range: σ 搜索范围 (mm)
            n_candidates: 候选 σ 数量
            boundary_conditions: 边界条件设置

        Returns:
            float: 最优 σ 值 (mm)
        """
        x = np.asarray(x_depths, dtype=float)
        y_mm = np.asarray(y_disps_mm, dtype=float)

        # 排序
        sort_idx = np.argsort(x)
        x = x[sort_idx]
        y_mm = y_mm[sort_idx]

        return _find_optimal_sigma(
            x, y_mm,
            algo_type=algo_type,
            sigma_range=sigma_range,
            n_candidates=n_candidates,
            bc=boundary_conditions,
            mirror_fn=self._apply_odd_symmetric_mirror,
            mao_bc_fn=prepare_mao_bc,
            mao_solve_fn=solve_mao_spline,
            mao_eval_fn=eval_mao_spline,
        )
