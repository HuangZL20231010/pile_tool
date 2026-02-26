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
        # 边界条件设置
        self._boundary_conditions: dict | None = None
        # 论文样条（毛朝辉2006）相关数据
        self._mao_x: np.ndarray | None = None
        self._mao_y_corrected: np.ndarray | None = None
        self._mao_M: np.ndarray | None = None
        self._mao_h: np.ndarray | None = None

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

    def _solve_mao_spline(self, x: np.ndarray, y_m: np.ndarray,
                          delta_m: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        论文光顺三次样条算法（毛朝辉2006，公式3.15-3.21）

        使用逐点权因子 ρ_i 和五对角矩阵方程组，通过直接迭代
        ρ_i^(k+1) = δ/|D_i^(k)| 使得逐点偏差 |ρ_i·D_i| ≤ δ。

        Args:
            x: 深度数组 (m)，已排序，N 个点
            y_m: 位移数组 (m)
            delta_m: 允许的最大逐点偏差 δ (m)

        Returns:
            (y_corrected, M, h):
                y_corrected: 光顺后的位移值 (m)
                M: 各节点的二阶导数 (1/m)
                h: 间距数组
        """
        from scipy.linalg import solve_banded

        N = len(x)
        h = np.diff(x)  # h[i] = x[i+1] - x[i], 长度 N-1

        # 右端向量 g（不依赖 ρ），内部节点 i=1,...,N-2
        g = np.zeros(N - 2)
        for i in range(1, N - 1):
            g[i - 1] = (y_m[i + 1] - y_m[i]) / h[i] - (y_m[i] - y_m[i - 1]) / h[i - 1]

        # 初始化逐点权因子 ρ_i, i=0,...,N-1
        rho = np.ones(N)

        m = N - 2  # 内部未知量个数 (M_1,...,M_{N-2})
        max_iter = 100

        for iteration in range(max_iter):
            # 构建 (N-2)×(N-2) 五对角方程组
            # solve_banded((2,2), ab, rhs)，ab 为 5×m 矩阵
            ab = np.zeros((5, m))

            for r in range(m):
                i = r + 1  # 原始索引

                # 主对角线 a_i
                ab[2, r] = ((h[i - 1] + h[i]) / 3.0
                            + rho[i - 1] / h[i - 1]**2
                            + rho[i] * (1.0 / h[i - 1] + 1.0 / h[i])**2
                            + rho[i + 1] / h[i]**2)

                # 上1对角线 b_i (r -> r+1)
                if r < m - 1:
                    ab[1, r + 1] = (h[i] / 6.0
                                    - (1.0 / h[i]) * ((1.0 / h[i - 1] + 1.0 / h[i]) * rho[i]
                                                       + (1.0 / h[i] + 1.0 / h[i + 1]) * rho[i + 1]))

                # 上2对角线 c_i (r -> r+2)
                if r < m - 2:
                    ab[0, r + 2] = rho[i + 1] / (h[i] * h[i + 1])

                # 下1对角线 = b_r（对称）
                if r > 0:
                    j = r  # 对应 b_{r} 即 b_{(r-1)+1} = b_i where i=r
                    i_prev = r
                    ab[3, r - 1] = (h[i_prev] / 6.0
                                    - (1.0 / h[i_prev]) * ((1.0 / h[i_prev - 1] + 1.0 / h[i_prev]) * rho[i_prev]
                                                            + (1.0 / h[i_prev] + 1.0 / h[i_prev + 1]) * rho[i_prev + 1]))

                # 下2对角线 = c_{r-1}（对称）
                if r > 1:
                    i_prev2 = r - 1
                    ab[4, r - 2] = rho[i_prev2 + 1] / (h[i_prev2] * h[i_prev2 + 1])

            # 求解 M 内部节点
            M_inner = solve_banded((2, 2), ab, g)

            # 完整 M 向量（自然样条边界 M_0 = M_{N-1} = 0）
            M_full = np.zeros(N)
            M_full[1:-1] = M_inner

            # 计算 D_i（公式 3.19）
            D = np.zeros(N)
            D[0] = (M_full[1] - M_full[0]) / h[0]             # = M_1 / h_0
            for i in range(1, N - 1):
                D[i] = (M_full[i + 1] - M_full[i]) / h[i] - (M_full[i] - M_full[i - 1]) / h[i - 1]
            D[N - 1] = -(M_full[N - 1] - M_full[N - 2]) / h[N - 2]  # = M_{N-2} / h_{N-2}

            # 检查收敛：max|ρ_i · D_i| ≤ δ
            if np.max(np.abs(rho * D)) <= delta_m:
                break

            # 更新 ρ_i（公式 3.21）
            for i in range(N):
                abs_Di = abs(D[i])
                if abs_Di != 0:
                    rho[i] = delta_m / abs_Di
                else:
                    rho[i] = 0.0

        # 计算光顺后位移（公式 3.18）
        y_corrected = y_m - rho * D

        return y_corrected, M_full, h

    def _eval_mao_spline(self, x_eval: np.ndarray, deriv: int = 0) -> np.ndarray:
        """
        用存储的论文样条数据在任意点求值

        三次样条分段公式：
        S(x) = Mᵢ(x_{i+1}-x)³/(6hᵢ) + M_{i+1}(x-xᵢ)³/(6hᵢ)
               + (ŷᵢ - Mᵢhᵢ²/6)(x_{i+1}-x)/hᵢ
               + (ŷ_{i+1} - M_{i+1}hᵢ²/6)(x-xᵢ)/hᵢ

        Args:
            x_eval: 求值点数组
            deriv: 导数阶数 (0,1,2,3)

        Returns:
            对应阶导数的值数组
        """
        x = self._mao_x
        y = self._mao_y_corrected
        M = self._mao_M
        h = self._mao_h

        n = len(x)
        # 定位区间
        idx = np.searchsorted(x, x_eval, side='right') - 1
        idx = np.clip(idx, 0, n - 2)

        hi = h[idx]
        Mi = M[idx]
        Mi1 = M[idx + 1]
        yi = y[idx]
        yi1 = y[idx + 1]

        dx_right = x[idx + 1] - x_eval  # x_{i+1} - x
        dx_left = x_eval - x[idx]       # x - xᵢ

        if deriv == 0:
            # S(x)
            result = (Mi * dx_right**3 / (6 * hi) +
                      Mi1 * dx_left**3 / (6 * hi) +
                      (yi - Mi * hi**2 / 6) * dx_right / hi +
                      (yi1 - Mi1 * hi**2 / 6) * dx_left / hi)
        elif deriv == 1:
            # S'(x)
            result = (-Mi * dx_right**2 / (2 * hi) +
                      Mi1 * dx_left**2 / (2 * hi) -
                      (yi - Mi * hi**2 / 6) / hi +
                      (yi1 - Mi1 * hi**2 / 6) / hi)
        elif deriv == 2:
            # S''(x) = Mᵢ(x_{i+1}-x)/hᵢ + M_{i+1}(x-xᵢ)/hᵢ
            result = Mi * dx_right / hi + Mi1 * dx_left / hi
        elif deriv == 3:
            # S'''(x) = (M_{i+1} - Mᵢ) / hᵢ
            result = (Mi1 - Mi) / hi
        else:
            result = np.zeros_like(x_eval)

        return result

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
            boundary_conditions (dict): 边界条件设置，包含：
                - top_enabled: 是否启用桩顶边界条件
                - top_depth: 桩顶深度 (m)
                - top_disp: 桩顶位移 (mm)
                - bottom_enabled: 是否启用桩底边界条件
                - bottom_depth: 桩底深度 (m)
                - bottom_disp: 桩底位移 (mm)

        Raises:
            ValueError: 当数据点少于 2 个时抛出

        Note:
            - 内部将位移从 mm 转换为 m 进行计算
            - 多项式模式：自动限制阶数不超过数据点数-1
            - 样条模式：s = N × σ²，其中 N 为数据点数，σ 为误差（单位：米）
            - 启用边界条件时，使用奇对称镜像法强制曲线满足边界约束
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

            # 先对原始数据排序
            sort_idx = np.argsort(x)
            x_sorted = x[sort_idx]
            y_sorted = y_m[sort_idx]

            # 应用边界条件镜像（如果启用）
            if use_bc:
                x_fit, y_fit = self._apply_odd_symmetric_mirror(x_sorted, y_sorted, boundary_conditions)
            else:
                x_fit, y_fit = x_sorted, y_sorted

            # 创建三次样条，k=3 表示三次样条
            self.spline = UnivariateSpline(x_fit, y_fit, k=3, s=s)

            # 清除多项式相关对象
            self.poly = None
            self.poly_coeffs = None
            self.poly_second = None

            # 计算拟合值（使用原始数据点）
            y_fit_m = self.spline(x)

        elif algo_type == "spline5":
            # ===== 五次样条平滑 =====
            from scipy.interpolate import UnivariateSpline

            # 五次样条需要至少6个数据点
            if x.size < 6:
                raise ValueError("五次样条拟合需要至少6个数据点")

            # 计算平滑因子 s = N × σ²
            sigma_m = sigma_mm / 1000.0
            s = len(y_m) * (sigma_m ** 2)

            # 先对原始数据排序
            sort_idx = np.argsort(x)
            x_sorted = x[sort_idx]
            y_sorted = y_m[sort_idx]

            # 应用边界条件镜像（如果启用）
            if use_bc:
                x_fit, y_fit = self._apply_odd_symmetric_mirror(x_sorted, y_sorted, boundary_conditions)
            else:
                x_fit, y_fit = x_sorted, y_sorted

            # 创建五次样条，k=5 表示五次样条
            self.spline = UnivariateSpline(x_fit, y_fit, k=5, s=s)

            # 清除多项式相关对象
            self.poly = None
            self.poly_coeffs = None
            self.poly_second = None

            # 计算拟合值（使用原始数据点）
            y_fit_m = self.spline(x)

        else:
            # ===== 论文样条（毛朝辉2006）=====
            # 逐点误差控制的光顺三次样条
            if x.size < 4:
                raise ValueError("论文样条拟合需要至少4个数据点")

            # delta_m: 允许的最大逐点偏差 (m)
            delta_m = sigma_mm / 1000.0

            # 排序
            sort_idx = np.argsort(x)
            x_sorted = x[sort_idx]
            y_sorted = y_m[sort_idx]

            # 应用边界条件镜像（如果启用）
            if use_bc:
                x_fit, y_fit = self._apply_odd_symmetric_mirror(x_sorted, y_sorted, boundary_conditions)
            else:
                x_fit, y_fit = x_sorted, y_sorted

            # 求解论文样条
            y_corrected, M_full, h_arr = self._solve_mao_spline(x_fit, y_fit, delta_m)

            # 存储结果
            self._mao_x = x_fit
            self._mao_y_corrected = y_corrected
            self._mao_M = M_full
            self._mao_h = h_arr

            # 清除其他拟合对象
            self.poly = None
            self.poly_coeffs = None
            self.poly_second = None
            self.spline = None

            # 计算拟合值（使用原始数据点）
            y_fit_m = self._eval_mao_spline(x, deriv=0)

        # 保存原始数据用于统计计算
        self._x_data = x

        # 记录数据深度范围，用于生成绘图数据
        # 如果启用了边界条件，扩展范围到边界点
        x_min = float(x.min())
        x_max = float(x.max())
        if use_bc:
            if boundary_conditions.get('top_enabled'):
                x_min = min(x_min, boundary_conditions['top_depth'])
            if boundary_conditions.get('bottom_enabled'):
                x_max = max(x_max, boundary_conditions['bottom_depth'])
        self._x_range = (x_min, x_max)

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
        elif self.algo_type == "mao_spline":
            if self._mao_x is None:
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
        elif self.algo_type == "spline5":
            # 五次样条模式
            # 计算拟合位移值（米）
            y_fit_m = self.spline(x_dense)
            # 计算曲率（样条的二阶导数，1/m）
            curvature = self.spline.derivative(2)(x_dense)
            # 计算三阶导数
            third_deriv = self.spline.derivative(3)(x_dense)
            # 计算四阶导数
            fourth_deriv = self.spline.derivative(4)(x_dense)
        elif self.algo_type == "mao_spline":
            # 论文样条模式
            y_fit_m = self._eval_mao_spline(x_dense, deriv=0)
            curvature = self._eval_mao_spline(x_dense, deriv=2)
            third_deriv = self._eval_mao_spline(x_dense, deriv=3)
            # 三次样条四阶导数为0
            fourth_deriv = np.zeros_like(x_dense)

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
        elif self.algo_type == "spline5":
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
        elif self.algo_type == "mao_spline":
            # 论文样条模式
            if self._mao_x is None:
                raise RuntimeError("请先执行拟合")
            x_arr = np.array([x_query])
            y_m = float(self._eval_mao_spline(x_arr, deriv=0)[0])
            curvature = float(self._eval_mao_spline(x_arr, deriv=2)[0])
            third_deriv = float(self._eval_mao_spline(x_arr, deriv=3)[0])
            # 三次样条四阶导数为0
            fourth_deriv = 0.0

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

        if self.algo_type == "mao_spline":
            if self._mao_x is None:
                return ""
            return "论文光顺样条 (分段函数)"

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
        if self.algo_type in ("spline", "spline5", "mao_spline"):
            if self.algo_type == "mao_spline":
                if self._mao_x is None:
                    return ""
            else:
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

    def find_optimal_sigma(self, x_depths, y_disps_mm,
                           algo_type: str = "spline",
                           sigma_range: tuple = (0.001, 1.0),
                           n_candidates: int = 50,
                           boundary_conditions: dict = None) -> float:
        """
        使用 L-curve 法自动选择最优 σ

        在 log(残差) vs log(粗糙度) 空间中找 L 曲线拐角，
        在拟合精度和导数平滑度之间取得平衡。

        算法原理
        --------
        L-curve 是反问题中选择正则化参数的经典方法。对于每个候选 σ：

        1. 计算平滑因子 s = N × σ²
        2. 用 s 拟合样条曲线 f(x)
        3. 计算残差 ρ = Σ(yᵢ - f(xᵢ))²（仅在原始数据点上）
        4. 计算粗糙度 η = ∫f''(x)²dx（与弯矩平滑度直接相关）

        在 log(ρ) vs log(η) 空间中，曲线呈 L 形：
        - 左上角：过平滑，残差大但导数光滑
        - 右下角：过拟合，残差小但导数噪声大
        - 拐角处：最佳平衡点

        搜索策略
        --------
        - 使用对数尺度搜索，50 个候选值
        - 每个候选仅需 1 次样条拟合，计算复杂度 O(n_candidates)

        Args:
            x_depths: 深度数据数组，单位为米 (m)
            y_disps_mm: 位移数据数组，单位为毫米 (mm)
            algo_type (str): 算法类型
                - 'spline': 三次样条 (k=3)
                - 'spline5': 五次样条 (k=5)
            sigma_range (tuple): σ 搜索范围 (mm)，默认 (0.001, 1.0)
            n_candidates (int): 候选 σ 数量，默认 50
            boundary_conditions (dict): 边界条件设置，可选

        Returns:
            float: 最优 σ 值，单位为毫米 (mm)
        """
        x = np.asarray(x_depths, dtype=float)
        y_mm = np.asarray(y_disps_mm, dtype=float)

        # 排序
        sort_idx = np.argsort(x)
        x = x[sort_idx]
        y_mm = y_mm[sort_idx]
        y_m = y_mm / 1000.0

        n = len(x)

        # 检查是否需要应用边界条件
        use_bc = (boundary_conditions is not None and
                  (boundary_conditions.get('top_enabled') or
                   boundary_conditions.get('bottom_enabled')))

        if use_bc:
            x_fit, y_fit = self._apply_odd_symmetric_mirror(x, y_m, boundary_conditions)
        else:
            x_fit, y_fit = x, y_m

        # 对数尺度生成候选 σ
        sigmas = np.logspace(np.log10(sigma_range[0]),
                             np.log10(sigma_range[1]),
                             n_candidates)

        # 用于计算粗糙度的细网格（在原始数据域上）
        x_fine = np.linspace(x[0], x[-1], 500)

        residuals = np.full(n_candidates, np.nan)
        roughnesses = np.full(n_candidates, np.nan)

        if algo_type == "mao_spline":
            # 论文样条：对每个候选 delta 调用 _solve_mao_spline
            for i, delta_mm_val in enumerate(sigmas):
                delta_m = delta_mm_val / 1000.0
                try:
                    y_corr, M_full, h_arr = self._solve_mao_spline(x_fit, y_fit, delta_m)

                    # 临时存储用于求值
                    old_x, old_y, old_M, old_h = self._mao_x, self._mao_y_corrected, self._mao_M, self._mao_h
                    self._mao_x = x_fit
                    self._mao_y_corrected = y_corr
                    self._mao_M = M_full
                    self._mao_h = h_arr

                    # 残差：仅在原始数据点上计算
                    y_pred = self._eval_mao_spline(x, deriv=0)
                    rho = float(np.sum((y_m - y_pred) ** 2))

                    # 粗糙度：∫f''(x)²dx
                    d2_vals = self._eval_mao_spline(x_fine, deriv=2)
                    eta = float(np.trapz(d2_vals ** 2, x_fine))

                    residuals[i] = rho
                    roughnesses[i] = eta

                    # 恢复
                    self._mao_x, self._mao_y_corrected, self._mao_M, self._mao_h = old_x, old_y, old_M, old_h
                except Exception:
                    continue
        else:
            from scipy.interpolate import UnivariateSpline
            k = 3 if algo_type == "spline" else 5

            for i, sigma_mm_val in enumerate(sigmas):
                sigma_m = sigma_mm_val / 1000.0
                s = n * (sigma_m ** 2)

                try:
                    spline = UnivariateSpline(x_fit, y_fit, k=k, s=s)

                    # 残差：仅在原始数据点上计算
                    y_pred = spline(x)
                    rho = float(np.sum((y_m - y_pred) ** 2))

                    # 粗糙度：∫f''(x)²dx，在原始数据域上数值积分
                    spline_d2 = spline.derivative(n=2)
                    d2_vals = spline_d2(x_fine)
                    eta = float(np.trapz(d2_vals ** 2, x_fine))

                    residuals[i] = rho
                    roughnesses[i] = eta
                except Exception:
                    continue

        # 过滤无效值
        valid = np.isfinite(residuals) & np.isfinite(roughnesses)
        if valid.sum() < 3:
            # 数据不足以找拐角，返回中间值
            return float(sigmas[n_candidates // 2])

        valid_indices = np.where(valid)[0]
        valid_res = residuals[valid_indices]
        valid_rough = roughnesses[valid_indices]

        corner_local = self._find_l_curve_corner(valid_res, valid_rough)
        corner_idx = valid_indices[corner_local]

        return float(sigmas[corner_idx])

    def _find_l_curve_corner(self, residuals: np.ndarray,
                             roughnesses: np.ndarray) -> int:
        """
        在 log-log 空间中用 Menger 曲率找 L 曲线拐角

        Args:
            residuals: 残差数组 ρ（与 σ 从小到大对应）
            roughnesses: 粗糙度数组 η

        Returns:
            int: 拐角点的索引
        """
        eps = 1e-30
        log_rho = np.log10(residuals + eps)
        log_eta = np.log10(roughnesses + eps)

        n = len(log_rho)
        if n < 3:
            return n // 2

        best_curvature = -np.inf
        best_idx = n // 2  # fallback：中间索引

        for i in range(1, n - 1):
            # 三点：P1=(log_rho[i-1], log_eta[i-1]), P2=(log_rho[i], log_eta[i]), P3=(log_rho[i+1], log_eta[i+1])
            x1, y1 = log_rho[i - 1], log_eta[i - 1]
            x2, y2 = log_rho[i], log_eta[i]
            x3, y3 = log_rho[i + 1], log_eta[i + 1]

            # 向量 P1->P2 和 P1->P3
            v12x, v12y = x2 - x1, y2 - y1
            v13x, v13y = x3 - x1, y3 - y1

            # 有符号叉积（正值表示向右弯，即 L 曲线拐角方向）
            cross = v12x * v13y - v12y * v13x

            if cross <= 0:
                continue

            # Menger 曲率 = 2 * |面积| / (d12 * d23 * d13)
            area = 0.5 * abs(cross)
            d12 = np.sqrt(v12x ** 2 + v12y ** 2)
            d13 = np.sqrt(v13x ** 2 + v13y ** 2)
            v23x, v23y = x3 - x2, y3 - y2
            d23 = np.sqrt(v23x ** 2 + v23y ** 2)

            denom = d12 * d23 * d13
            if denom < 1e-30:
                continue

            curvature = 2.0 * area / denom

            if curvature > best_curvature:
                best_curvature = curvature
                best_idx = i

        return best_idx

