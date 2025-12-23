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

    def set_parameters(self, E_val: float, E_unit: str, section_type: str, dims: dict):
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

        Note:
            内部会自动转换为标准单位：E 转为 kPa，尺寸转为米
        """
        # 将弹性模量统一转换为 kPa
        self.E_kpa = utils.convert_E_to_kpa(E_val, E_unit)
        # 计算截面惯性矩，自动处理单位转换
        self.I_m4 = utils.compute_inertia(section_type, dims)

    def fit_data(self, x_depths, y_disps_mm, degree: int = 5,
                 algo_type: str = "polynomial", sigma_mm: float = 0.5):
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

        Raises:
            ValueError: 当数据点少于 2 个时抛出

        Note:
            - 内部将位移从 mm 转换为 m 进行计算
            - 多项式模式：自动限制阶数不超过数据点数-1
            - 样条模式：s = N × σ²，其中 N 为数据点数，σ 为误差（单位：米）
        """
        # 将输入数据转换为 numpy 数组，确保数据类型为 float
        x = np.asarray(x_depths, dtype=float)
        # 将位移从毫米转换为米，因为计算公式需要 SI 单位制
        y_m = np.asarray(y_disps_mm, dtype=float) / 1000.0

        # 数据点数量检查，至少需要 2 个点才能进行拟合
        if x.size < 2:
            raise ValueError("至少需要两组数据点用于拟合")

        # 保存算法类型
        self.algo_type = algo_type

        if algo_type == "polynomial":
            # ===== 多项式拟合 =====
            # 限制拟合阶数在合理范围内，避免过拟合
            deg = utils.clamp_degree(degree)
            # 确保阶数不超过数据点数-1（数学约束）
            deg = min(deg, x.size - 1) if x.size > 1 else deg

            # 执行多项式拟合，忽略可能出现的条件数警告
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RankWarning)
                # np.polyfit 返回从高次到低次的系数数组
                self.poly_coeffs = np.polyfit(x, y_m, deg)

            # 创建多项式对象，方便后续计算任意点的值
            self.poly = np.poly1d(self.poly_coeffs)
            # 计算二阶导数多项式，用于弯矩计算（M = E * I * y''）
            self.poly_second = np.polyder(self.poly, 2)
            # 清除样条对象
            self.spline = None

            # 计算拟合值
            y_fit_m = self.poly(x)
        elif algo_type == "spline":
            # ===== 三次样条平滑 =====
            from scipy.interpolate import UnivariateSpline

            # 计算平滑因子 s = N × σ²
            # σ 从 mm 转换为 m（与位移数据单位一致）
            sigma_m = sigma_mm / 1000.0
            s = len(y_m) * (sigma_m ** 2)

            # 创建三次样条，k=3 表示三次样条
            # 需要确保 x 是递增的
            sort_idx = np.argsort(x)
            x_sorted = x[sort_idx]
            y_sorted = y_m[sort_idx]

            self.spline = UnivariateSpline(x_sorted, y_sorted, k=3, s=s)

            # 清除多项式相关对象
            self.poly = None
            self.poly_coeffs = None
            self.poly_second = None

            # 计算拟合值
            y_fit_m = self.spline(x)

        else:
            # ===== 五次样条平滑 =====
            from scipy.interpolate import UnivariateSpline

            # 五次样条需要至少6个数据点
            if x.size < 6:
                raise ValueError("五次样条拟合需要至少6个数据点")

            # 计算平滑因子 s = N × σ²
            sigma_m = sigma_mm / 1000.0
            s = len(y_m) * (sigma_m ** 2)

            # 需要确保 x 是递增的
            sort_idx = np.argsort(x)
            x_sorted = x[sort_idx]
            y_sorted = y_m[sort_idx]

            # 创建五次样条，k=5 表示五次样条
            self.spline = UnivariateSpline(x_sorted, y_sorted, k=5, s=s)

            # 清除多项式相关对象
            self.poly = None
            self.poly_coeffs = None
            self.poly_second = None

            # 计算拟合值
            y_fit_m = self.spline(x)

        # 保存原始数据用于统计计算
        self._x_data = x
        # 记录数据深度范围，用于生成绘图数据
        self._x_range = (float(x.min()), float(x.max()))

        # 计算拟合统计信息
        # 1. 计算残差平方和 (Sum of Squares of Residuals)
        ss_res = np.sum((y_m - y_fit_m) ** 2)
        # 2. 计算总平方和 (Total Sum of Squares)
        ss_tot = np.sum((y_m - np.mean(y_m)) ** 2)
        # 3. 计算决定系数 R² (Coefficient of Determination)
        r2 = 1 - ss_res / ss_tot if ss_tot != 0 else 1.0
        # 4. 计算均方根误差 RMSE，转换回毫米单位
        rmse_mm = float(np.sqrt(np.mean((y_m - y_fit_m) ** 2)) * 1000.0)

        # 保存统计结果
        self.fitting_stats = {"R2": float(r2), "RMSE_mm": rmse_mm}

    def get_results_arrays(self, num_points: int = 100):
        """
        生成用于绘图的密集数据数组

        在数据范围内生成等间距的点，计算对应的位移、弯矩、剪力和土压力值。

        Args:
            num_points (int): 生成的数据点数量，默认 100

        Returns:
            tuple: (x_dense, y_fit_mm, moment, shear, pressure)
                - x_dense: 深度数组，单位为米
                - y_fit_mm: 拟合位移数组，单位为毫米
                - moment: 弯矩数组，单位为 kN·m
                - shear: 剪力数组，单位为 kN
                - pressure: 土压力数组，单位为 kPa

        Raises:
            RuntimeError: 当未执行拟合时抛出
        """
        # 检查是否已执行拟合
        if self._x_range is None:
            raise RuntimeError("请先执行拟合")

        if self.algo_type == "polynomial":
            if self.poly is None or self.poly_second is None:
                raise RuntimeError("请先执行拟合")
        else:
            if self.spline is None:
                raise RuntimeError("请先执行拟合")

        # 获取数据深度范围
        x_min, x_max = self._x_range
        # 处理边界情况：如果所有数据点深度相同，扩展范围
        if x_min == x_max:
            x_min -= 1.0
            x_max += 1.0

        # 生成密集的深度坐标点，用于绘制平滑曲线
        x_dense = np.linspace(x_min, x_max, num_points)

        if self.algo_type == "polynomial":
            # 多项式模式
            # 计算拟合位移值（米）
            y_fit_m = self.poly(x_dense)
            # 计算曲率（位移的二阶导数，1/m）
            curvature = self.poly_second(x_dense)
            # 计算三阶导数
            poly_third = np.polyder(self.poly, 3)
            third_deriv = poly_third(x_dense)
            # 计算四阶导数
            poly_fourth = np.polyder(self.poly, 4)
            fourth_deriv = poly_fourth(x_dense)
        elif self.algo_type == "spline":
            # 三次样条模式
            # 计算拟合位移值（米）
            y_fit_m = self.spline(x_dense)
            # 计算曲率（样条的二阶导数，1/m）
            curvature = self.spline.derivative(2)(x_dense)
            # 三次样条只能计算到二阶导数，三阶导数是常数，四阶导数为零
            third_deriv = self.spline.derivative(3)(x_dense)
            # 四阶导数为零（三次样条的三阶导数是分段常数）
            fourth_deriv = np.zeros_like(x_dense)
        else:
            # 五次样条模式
            # 计算拟合位移值（米）
            y_fit_m = self.spline(x_dense)
            # 计算曲率（样条的二阶导数，1/m）
            curvature = self.spline.derivative(2)(x_dense)
            # 计算三阶导数
            third_deriv = self.spline.derivative(3)(x_dense)
            # 计算四阶导数
            fourth_deriv = self.spline.derivative(4)(x_dense)

        # 计算弯矩：M = E * I * y'' (kN·m)
        moment = self.E_kpa * self.I_m4 * curvature
        # 计算剪力：Q = E * I * y''' (kN)
        shear = self.E_kpa * self.I_m4 * third_deriv
        # 计算土压力：p = E * I * y'''' (kPa)
        pressure = self.E_kpa * self.I_m4 * fourth_deriv

        # 将位移转换回毫米单位，用于显示
        y_fit_mm = y_fit_m * 1000.0

        return x_dense, y_fit_mm, moment, shear, pressure

    def query_single_point(self, x_query: float) -> QueryResult:
        """
        查询特定深度的计算结果

        计算指定深度的位移、曲率、弯矩、剪力和土压力值。

        Args:
            x_query (float): 查询的深度，单位为米

        Returns:
            QueryResult: 包含位移、曲率、弯矩、剪力和土压力的查询结果对象

        Raises:
            RuntimeError: 当未执行拟合时抛出
        """
        # 检查是否已执行拟合
        if self.algo_type == "polynomial":
            if self.poly is None or self.poly_second is None:
                raise RuntimeError("请先执行拟合")
            # 计算指定深度的位移值（米）
            y_m = float(self.poly(x_query))
            # 计算指定深度的曲率（1/m）
            curvature = float(self.poly_second(x_query))
            # 计算三阶导数
            poly_third = np.polyder(self.poly, 3)
            third_deriv = float(poly_third(x_query))
            # 计算四阶导数
            poly_fourth = np.polyder(self.poly, 4)
            fourth_deriv = float(poly_fourth(x_query))
        elif self.algo_type == "spline":
            if self.spline is None:
                raise RuntimeError("请先执行拟合")
            # 计算指定深度的位移值（米）
            y_m = float(self.spline(x_query))
            # 计算指定深度的曲率（1/m）
            curvature = float(self.spline.derivative(2)(x_query))
            # 三次样条的三阶导数
            third_deriv = float(self.spline.derivative(3)(x_query))
            # 四阶导数为零
            fourth_deriv = 0.0
        else:
            # 五次样条模式
            if self.spline is None:
                raise RuntimeError("请先执行拟合")
            # 计算指定深度的位移值（米）
            y_m = float(self.spline(x_query))
            # 计算指定深度的曲率（1/m）
            curvature = float(self.spline.derivative(2)(x_query))
            # 计算三阶导数
            third_deriv = float(self.spline.derivative(3)(x_query))
            # 计算四阶导数
            fourth_deriv = float(self.spline.derivative(4)(x_query))

        # 计算指定深度的弯矩（kN·m）：M = E * I * y''
        moment = float(self.E_kpa * self.I_m4 * curvature)
        # 计算剪力：Q = E * I * y'''（kN）
        shear = float(self.E_kpa * self.I_m4 * third_deriv)
        # 计算土压力：p = E * I * y''''（kPa）
        pressure = float(self.E_kpa * self.I_m4 * fourth_deriv)

        # 返回查询结果，位移转换为毫米
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
            格式化的表达式：
            - 多项式模式：如 "y = 0.5x³ - 2.3x² + 1.2x + 0.8"
            - 三次样条模式：返回 "Cubic Smoothing Spline (分段函数)"
            - 五次样条模式：返回 "Quintic Smoothing Spline (分段函数)"
            如果未执行拟合，返回空字符串
        """
        # 样条模式返回固定文本
        if self.algo_type == "spline":
            if self.spline is None:
                return ""
            return "Cubic Smoothing Spline (分段函数)"

        if self.algo_type == "spline5":
            if self.spline is None:
                return ""
            return "Quintic Smoothing Spline (分段函数)"

        # 多项式模式
        if self.poly_coeffs is None:
            return ""

        from core import utils
        return utils.format_polynomial(self.poly_coeffs, var='x', precision=precision)

    def get_moment_expression(self, precision: int = 3) -> str:
        """
        获取格式化的弯矩函数表达式

        弯矩计算公式：M(x) = E * I * y''(x)
        其中 y''(x) 是位移函数的二阶导数

        Args:
            precision: 小数精度，默认 3 位

        Returns:
            格式化的弯矩表达式：
            - 多项式模式：如 "M(x) = 2.5x² - 3.2x + 1.1"
            - 样条模式：返回 "M(x) = E·I·y''(x) (分段函数)"
            如果未执行拟合或参数未设置，返回空字符串

        Note:
            - 弯矩单位为 kN·m
            - 多项式模式：表达式已包含 E*I 的缩放系数
        """
        # 样条模式返回固定文本
        if self.algo_type in ("spline", "spline5"):
            if self.spline is None:
                return ""
            return "M(x) = E·I·y''(x) (分段函数)"

        # 多项式模式
        if self.poly_second is None or self.E_kpa is None or self.I_m4 is None:
            return ""

        # 获取二阶导数的系数（y''的多项式系数）
        second_deriv_coeffs = self.poly_second.coefficients

        # 将二阶导数系数乘以 E*I，得到弯矩函数的系数
        # E_kpa 单位是 kPa，I_m4 单位是 m⁴，结果单位是 kN·m
        moment_coeffs = second_deriv_coeffs * self.E_kpa * self.I_m4

        from core import utils
        # 格式化弯矩表达式
        moment_expr = utils.format_polynomial(moment_coeffs, var='x', precision=precision)

        # 将 "y =" 替换为 "M(x) ="
        if moment_expr.startswith("y = "):
            return "M(x) = " + moment_expr[4:]

        return moment_expr

