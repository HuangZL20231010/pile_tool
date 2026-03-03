"""
L-curve 优化模块

提供 L-curve 法自动选择最优平滑参数 σ 的功能，
在拟合精度和导数平滑度之间取得平衡。
"""

from __future__ import annotations

from typing import Callable

import numpy as np


def find_optimal_sigma(x: np.ndarray, y_mm: np.ndarray,
                       algo_type: str = "spline",
                       sigma_range: tuple = (0.001, 1.0),
                       n_candidates: int = 50,
                       bc: dict | None = None,
                       mirror_fn: Callable | None = None,
                       mao_bc_fn: Callable | None = None,
                       mao_solve_fn: Callable | None = None,
                       mao_eval_fn: Callable | None = None) -> float:
    """
    使用 L-curve 法自动选择最优 σ

    在 log(残差) vs log(粗糙度) 空间中找 L 曲线拐角，
    在拟合精度和导数平滑度之间取得平衡。

    Args:
        x: 深度数据数组 (m)，已排序
        y_mm: 位移数据数组 (mm)
        algo_type: 算法类型 ('spline', 'spline5', 'mao_spline')
        sigma_range: σ 搜索范围 (mm)
        n_candidates: 候选 σ 数量
        bc: 边界条件字典
        mirror_fn: 奇对称镜像函数 (x, y_m, bc) -> (x_aug, y_aug)
        mao_bc_fn: mao 边界条件函数 (x, y, bc) -> (x_aug, y_aug, locked)
        mao_solve_fn: mao 样条求解函数 (x, y, delta, locked) -> (y_corr, M, h)
        mao_eval_fn: mao 样条求值函数 (x_eval, mao_x, mao_y, mao_M, mao_h, deriv) -> values

    Returns:
        float: 最优 σ 值 (mm)
    """
    y_m = y_mm / 1000.0
    n = len(x)

    # 检查是否需要应用边界条件
    use_bc = (bc is not None and
              (bc.get('top_enabled') or bc.get('bottom_enabled')))

    # mao_spline 使用直接插入边界点方式，其他样条使用镜像法
    locked = set()
    if algo_type == "mao_spline":
        if use_bc and mao_bc_fn is not None:
            x_fit, y_fit, locked = mao_bc_fn(x, y_m, bc)
        else:
            x_fit, y_fit = x, y_m
    else:
        if use_bc and mirror_fn is not None:
            x_fit, y_fit = mirror_fn(x, y_m, bc)
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
        # 论文样条：对每个候选 delta 调用 solve_mao_spline
        for i, delta_mm_val in enumerate(sigmas):
            delta_m = delta_mm_val / 1000.0
            try:
                y_corr, M_full, h_arr = mao_solve_fn(
                    x_fit, y_fit, delta_m, locked_indices=locked)

                # 残差：仅在原始数据点上计算
                y_pred = mao_eval_fn(x, x_fit, y_corr, M_full, h_arr, deriv=0)
                rho = float(np.sum((y_m - y_pred) ** 2))

                # 粗糙度：∫f''(x)²dx
                d2_vals = mao_eval_fn(x_fine, x_fit, y_corr, M_full, h_arr, deriv=2)
                eta = float(np.trapz(d2_vals ** 2, x_fine))

                residuals[i] = rho
                roughnesses[i] = eta
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

    corner_local = find_l_curve_corner(valid_res, valid_rough)
    corner_idx = valid_indices[corner_local]

    return float(sigmas[corner_idx])


def find_l_curve_corner(residuals: np.ndarray,
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
