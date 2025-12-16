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
    """
    y_mm: float
    curvature: float
    moment: float


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

    def fit_data(self, x_depths, y_disps_mm, degree: int = 5):
        """
        执行多项式拟合

        使用最小二乘法对位移数据进行多项式拟合，计算拟合统计信息。

        Args:
            x_depths: 深度数据数组，单位为米 (m)
            y_disps_mm: 位移数据数组，单位为毫米 (mm)
            degree (int): 多项式阶数，默认值为 5

        Raises:
            ValueError: 当数据点少于 2 个时抛出

        Note:
            - 内部将位移从 mm 转换为 m 进行计算
            - 自动限制阶数不超过数据点数-1
            - 忽略 NumPy 的 RankWarning（当阶数过高时）
        """
        # 将输入数据转换为 numpy 数组，确保数据类型为 float
        x = np.asarray(x_depths, dtype=float)
        # 将位移从毫米转换为米，因为计算公式需要 SI 单位制
        y_m = np.asarray(y_disps_mm, dtype=float) / 1000.0

        # 数据点数量检查，至少需要 2 个点才能进行线性拟合
        if x.size < 2:
            raise ValueError("至少需要两组数据点用于拟合")

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

        # 保存原始数据用于统计计算
        self._x_data = x
        # 记录数据深度范围，用于生成绘图数据
        self._x_range = (float(x.min()), float(x.max()))

        # 计算拟合统计信息
        # 1. 计算拟合值
        y_fit_m = self.poly(x)
        # 2. 计算残差平方和 (Sum of Squares of Residuals)
        ss_res = np.sum((y_m - y_fit_m) ** 2)
        # 3. 计算总平方和 (Total Sum of Squares)
        ss_tot = np.sum((y_m - np.mean(y_m)) ** 2)
        # 4. 计算决定系数 R² (Coefficient of Determination)
        r2 = 1 - ss_res / ss_tot if ss_tot != 0 else 1.0
        # 5. 计算均方根误差 RMSE，转换回毫米单位
        rmse_mm = float(np.sqrt(np.mean((y_m - y_fit_m) ** 2)) * 1000.0)

        # 保存统计结果
        self.fitting_stats = {"R2": float(r2), "RMSE_mm": rmse_mm}

    def get_results_arrays(self, num_points: int = 100):
        """
        生成用于绘图的密集数据数组

        在数据范围内生成等间距的点，计算对应的位移和弯矩值，用于绘制拟合曲线。

        Args:
            num_points (int): 生成的数据点数量，默认 100

        Returns:
            tuple: (x_dense, y_fit_mm, moment)
                - x_dense: 深度数组，单位为米
                - y_fit_mm: 拟合位移数组，单位为毫米
                - moment: 弯矩数组，单位为 kN·m

        Raises:
            RuntimeError: 当未执行拟合时抛出
        """
        # 检查是否已执行拟合
        if self.poly is None or self.poly_second is None or self._x_range is None:
            raise RuntimeError("请先执行拟合")

        # 获取数据深度范围
        x_min, x_max = self._x_range
        # 处理边界情况：如果所有数据点深度相同，扩展范围
        if x_min == x_max:
            x_min -= 1.0
            x_max += 1.0

        # 生成密集的深度坐标点，用于绘制平滑曲线
        x_dense = np.linspace(x_min, x_max, num_points)

        # 计算拟合位移值（米）
        y_fit_m = self.poly(x_dense)
        # 计算曲率（位移的二阶导数，1/m）
        curvature = self.poly_second(x_dense)
        # 计算弯矩：M = E * I * y'' (kN·m)
        moment = self.E_kpa * self.I_m4 * curvature

        # 将位移转换回毫米单位，用于显示
        y_fit_mm = y_fit_m * 1000.0

        return x_dense, y_fit_mm, moment

    def query_single_point(self, x_query: float) -> QueryResult:
        """
        查询特定深度的计算结果

        计算指定深度的位移、曲率和弯矩值。

        Args:
            x_query (float): 查询的深度，单位为米

        Returns:
            QueryResult: 包含位移、曲率和弯矩的查询结果对象

        Raises:
            RuntimeError: 当未执行拟合时抛出
        """
        # 检查是否已执行拟合
        if self.poly is None or self.poly_second is None:
            raise RuntimeError("请先执行拟合")

        # 计算指定深度的位移值（米）
        y_m = float(self.poly(x_query))
        # 计算指定深度的曲率（1/m）
        curvature = float(self.poly_second(x_query))
        # 计算指定深度的弯矩（kN·m）：M = E * I * y''
        moment = float(self.E_kpa * self.I_m4 * curvature)

        # 返回查询结果，位移转换为毫米
        return QueryResult(y_mm=y_m * 1000.0, curvature=curvature, moment=moment)

