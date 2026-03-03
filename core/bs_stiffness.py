"""
Bs 迭代刚度计算模块

实现矩形截面钢筋混凝土短期刚度（Bs）的迭代计算，
用于根据曲率逐点求弯矩。
"""

from __future__ import annotations

import numpy as np


def precompute_bs_params(Ec_MPa: float, As_mm2: float, h0_mm: float,
                         ftk_MPa: float, b_mm: float, h_mm: float,
                         I_m4: float) -> dict:
    """
    预计算 Bs 迭代所需的常量参数

    Args:
        Ec_MPa: 混凝土弹性模量 (MPa)
        As_mm2: 钢筋面积 (mm²)
        h0_mm: 有效高度 (mm)
        ftk_MPa: 混凝土抗拉强度标准值 (MPa)
        b_mm: 截面宽度 (mm)（矩形截面或圆形等效）
        h_mm: 截面高度 (mm)（矩形截面或圆形等效）
        I_m4: 截面惯性矩 (m⁴)

    Returns:
        dict: 预计算参数字典
    """
    Es_MPa = 200000.0  # 钢筋弹性模量 (MPa)

    # 转换为 kPa / m 单位制
    Es_kPa = Es_MPa * 1000.0
    Ec_kPa = Ec_MPa * 1000.0
    ftk_kPa = ftk_MPa * 1000.0
    As_m2 = As_mm2 / 1e6
    h0_m = h0_mm / 1000.0
    b_m = b_mm / 1000.0
    h_m = h_mm / 1000.0

    # 预计算常量
    alpha_E = Es_kPa / Ec_kPa  # αE = Es/Ec
    rho = As_m2 / (b_m * h0_m)  # ρ = As/(b·h0)
    # αE·ρ/ζ = 0.2 + 6·αE·ρ （矩形截面 γf'=0）
    alpha_E_rho_over_zeta = 0.2 + 6.0 * alpha_E * rho
    # η = 1 - 0.4·√(αE·ρ)  (内力臂系数)
    eta = 1.0 - 0.4 * np.sqrt(alpha_E * rho)
    # Ate = 0.5·b·h, ρte = As/Ate (≥0.01)
    Ate = 0.5 * b_m * h_m
    rho_te = max(As_m2 / Ate, 0.01)
    # Bs0 = Ec · I_rect （初始刚度）
    Bs0 = Ec_kPa * I_m4

    return {
        'Es_kPa': Es_kPa,
        'As_m2': As_m2,
        'h0_m': h0_m,
        'ftk_kPa': ftk_kPa,
        'alpha_E_rho_over_zeta': alpha_E_rho_over_zeta,
        'eta': eta,
        'rho_te': rho_te,
        'Bs0': Bs0,
    }


def compute_bs_single(curvature: float, bs_params: dict) -> tuple[float, float]:
    """
    对单个曲率值迭代求 Bs 和弯矩 M

    使用短期刚度公式 Bs = Es·As·h0² / (ψ/η + αE·ρ/ζ) 逐步迭代，
    直到 Bs 收敛。

    Args:
        curvature: 曲率 φ (1/m)
        bs_params: 预计算参数字典

    Returns:
        (Bs, M): Bs 刚度 (kN·m²) 和弯矩 M (kN·m)
    """
    p = bs_params
    phi = abs(curvature)
    sign = 1.0 if curvature >= 0 else -1.0

    # 曲率接近零时直接返回
    if phi < 1e-15:
        return p['Bs0'], 0.0

    Es_kPa = p['Es_kPa']
    As_m2 = p['As_m2']
    h0_m = p['h0_m']
    ftk_kPa = p['ftk_kPa']
    aErho_zeta = p['alpha_E_rho_over_zeta']
    eta = p['eta']
    rho_te = p['rho_te']
    Bs = p['Bs0']

    for _ in range(50):
        M_abs = Bs * phi
        # σss = M / (0.87·h0·As)，单位 kPa
        sigma_ss = M_abs / (0.87 * h0_m * As_m2)
        if sigma_ss < 1e-15:
            break
        # ψ = 1.1 - 0.65·ftk/(ρte·σss), clamp [0.2, 1.0]
        psi = 1.1 - 0.65 * ftk_kPa / (rho_te * sigma_ss)
        psi = max(0.2, min(1.0, psi))
        # Bs_new = Es·As·h0² / (ψ/η + αE·ρ/ζ)
        Bs_new = Es_kPa * As_m2 * h0_m ** 2 / (psi / eta + aErho_zeta)
        # 收敛判断
        if abs(Bs_new - Bs) / max(Bs, 1e-30) < 1e-6:
            Bs = Bs_new
            break
        Bs = Bs_new

    M = sign * Bs * phi
    return Bs, M


def compute_bs_moment(curvature_array: np.ndarray, bs_params: dict) -> np.ndarray:
    """
    对曲率数组逐点迭代计算弯矩

    Args:
        curvature_array: 曲率数组 (1/m)
        bs_params: 预计算参数字典

    Returns:
        弯矩数组 (kN·m)
    """
    moment = np.empty_like(curvature_array)
    for i, phi in enumerate(curvature_array):
        _, m = compute_bs_single(float(phi), bs_params)
        moment[i] = m
    return moment
