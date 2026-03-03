"""
论文光顺样条算法（毛朝辉2006）

提供逐点误差控制的三次样条拟合功能，包括：
- 边界条件准备（插入边界点并标记锁定）
- 五对角矩阵方程组求解（逐点权因子迭代）
- 分段三次样条求值（支持 0-3 阶导数）
"""

from __future__ import annotations

from typing import Tuple

import numpy as np


def prepare_mao_bc(x_sorted: np.ndarray, y_sorted: np.ndarray,
                   bc: dict) -> Tuple[np.ndarray, np.ndarray, set]:
    """
    为 mao_spline 准备边界条件：将边界点插入数据并标记为锁定

    与镜像法不同，此方法仅插入边界点本身（不生成虚构镜像数据），
    并返回锁定索引集合，使 solve_mao_spline 在迭代时跳过这些点。

    Args:
        x_sorted: 已排序的深度数组 (m)
        y_sorted: 对应的位移数组 (m)
        bc: 边界条件字典

    Returns:
        (x_aug, y_aug, locked): 增强后的数据和被锁定的索引集合
    """
    x_list = list(x_sorted)
    y_list = list(y_sorted)

    # 桩顶边界点：插入到头部
    if bc.get('top_enabled'):
        top_depth = bc['top_depth']
        top_disp_m = bc['top_disp'] / 1000.0
        x_list.insert(0, top_depth)
        y_list.insert(0, top_disp_m)

    # 桩底边界点：追加到尾部
    if bc.get('bottom_enabled'):
        bottom_depth = bc['bottom_depth']
        bottom_disp_m = bc['bottom_disp'] / 1000.0
        x_list.append(bottom_depth)
        y_list.append(bottom_disp_m)

    x_aug = np.array(x_list)
    y_aug = np.array(y_list)

    # 排序并去重
    sort_idx = np.argsort(x_aug)
    x_aug = x_aug[sort_idx]
    y_aug = y_aug[sort_idx]
    unique_mask = np.diff(x_aug, prepend=-np.inf) > 1e-10
    x_aug = x_aug[unique_mask]
    y_aug = y_aug[unique_mask]

    # 找出边界点在排序后数组中的索引
    locked = set()
    if bc.get('top_enabled'):
        idx = int(np.argmin(np.abs(x_aug - bc['top_depth'])))
        locked.add(idx)
    if bc.get('bottom_enabled'):
        idx = int(np.argmin(np.abs(x_aug - bc['bottom_depth'])))
        locked.add(idx)

    return x_aug, y_aug, locked


def solve_mao_spline(x: np.ndarray, y_m: np.ndarray,
                     delta_m: float,
                     locked_indices: set | None = None) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    论文光顺三次样条算法（毛朝辉2006，公式3.15-3.21）

    使用逐点权因子 ρ_i 和五对角矩阵方程组，通过直接迭代
    ρ_i^(k+1) = δ/|D_i^(k)| 使得逐点偏差 |ρ_i·D_i| ≤ δ。

    Args:
        x: 深度数组 (m)，已排序，N 个点
        y_m: 位移数组 (m)
        delta_m: 允许的最大逐点偏差 δ (m)
        locked_indices: 被锁定的点索引集合（边界点），这些点 ρ=0 不参与光顺修正

    Returns:
        (y_corrected, M, h):
            y_corrected: 光顺后的位移值 (m)
            M: 各节点的二阶导数 (1/m)
            h: 间距数组
    """
    from scipy.linalg import solve_banded

    if locked_indices is None:
        locked_indices = set()

    N = len(x)
    h = np.diff(x)  # h[i] = x[i+1] - x[i], 长度 N-1

    # 右端向量 g（不依赖 ρ），内部节点 i=1,...,N-2
    g = np.zeros(N - 2)
    for i in range(1, N - 1):
        g[i - 1] = (y_m[i + 1] - y_m[i]) / h[i] - (y_m[i] - y_m[i - 1]) / h[i - 1]

    # 初始化逐点权因子 ρ_i, i=0,...,N-1
    rho = np.ones(N)
    # 锁定点 ρ=0，位移不被修正
    for idx in locked_indices:
        rho[idx] = 0.0

    # ρ 上限：防止 |D_i| 极小时 ρ 爆炸导致矩阵奇异
    h_min = np.min(h)
    rho_max = 1.0 / (h_min * delta_m + 1e-30)

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

        # 求解 M 内部节点；若矩阵奇异则添加正则化重试
        try:
            M_inner = solve_banded((2, 2), ab, g)
        except np.linalg.LinAlgError:
            reg = max(1e-10, 1e-8 * np.max(np.abs(ab[2, :])))
            ab[2, :] += reg
            try:
                M_inner = solve_banded((2, 2), ab, g)
            except np.linalg.LinAlgError:
                raise ValueError(
                    f"论文样条求解失败：δ={delta_m*1000:.3f}mm 导致矩阵奇异，"
                    "请尝试略微调大或调小误差限"
                )

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

        # 更新 ρ_i（公式 3.21），跳过锁定的边界点
        for i in range(N):
            if i in locked_indices:
                rho[i] = 0.0
                continue
            abs_Di = abs(D[i])
            if abs_Di > 1e-15:
                rho[i] = min(delta_m / abs_Di, rho_max)
            else:
                rho[i] = 0.0

    # 计算光顺后位移（公式 3.18）
    y_corrected = y_m - rho * D

    return y_corrected, M_full, h


def eval_mao_spline(x_eval: np.ndarray, mao_x: np.ndarray,
                    mao_y: np.ndarray, mao_M: np.ndarray,
                    mao_h: np.ndarray, deriv: int = 0) -> np.ndarray:
    """
    用论文样条数据在任意点求值

    三次样条分段公式：
    S(x) = Mi(x_{i+1}-x)^3/(6hi) + M_{i+1}(x-xi)^3/(6hi)
           + (yi - Mi*hi^2/6)(x_{i+1}-x)/hi
           + (y_{i+1} - M_{i+1}*hi^2/6)(x-xi)/hi

    Args:
        x_eval: 求值点数组
        mao_x: 节点 x 坐标
        mao_y: 光顺后的节点 y 值
        mao_M: 节点二阶导数
        mao_h: 间距数组
        deriv: 导数阶数 (0,1,2,3)

    Returns:
        对应阶导数的值数组
    """
    x = mao_x
    y = mao_y
    M = mao_M
    h = mao_h

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
    dx_left = x_eval - x[idx]       # x - xi

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
        # S''(x) = Mi(x_{i+1}-x)/hi + M_{i+1}(x-xi)/hi
        result = Mi * dx_right / hi + Mi1 * dx_left / hi
    elif deriv == 3:
        # S'''(x) = (M_{i+1} - Mi) / hi
        result = (Mi1 - Mi) / hi
    else:
        result = np.zeros_like(x_eval)

    return result
