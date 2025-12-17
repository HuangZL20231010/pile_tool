"""
围护桩反分析工具辅助函数库

提供单位换算、几何计算、数据解析等通用功能函数。
这些函数是核心计算的支撑，确保数据处理的准确性和一致性。
"""

from __future__ import annotations

import math
import re
from typing import Iterable, List, Tuple


def mm_to_m(value_mm: float) -> float:
    """
    将毫米转换为米

    Args:
        value_mm (float): 毫米数值

    Returns:
        float: 米数值

    Note:
        围护桩计算中经常需要在毫米和米之间转换，因为：
        - 用户界面通常使用毫米（更直观）
        - 物理公式需要米制单位（SI单位制）
    """
    return value_mm / 1000.0


def convert_E_to_kpa(E_val: float, unit: str) -> float:
    """
    将弹性模量转换为千帕单位

    Args:
        E_val (float): 弹性模量数值
        unit (str): 单位字符串，'MPa' 或 'kPa'

    Returns:
        float: 统一为千帕 (kPa) 的弹性模量值

    Raises:
        ValueError: 当单位不是 'MPa' 或 'kPa' 时抛出

    Note:
        - MPa = 兆帕 = 10^6 Pa
        - kPa = 千帕 = 10^3 Pa
        - 转换关系：1 MPa = 1000 kPa
    """
    # 标准化单位字符串为小写
    unit_norm = unit.lower()
    if unit_norm == "mpa":
        # 兆帕转换为千帕：乘以 1000
        return E_val * 1000.0
    if unit_norm == "kpa":
        # 已经是千帕，直接返回
        return E_val
    # 不支持的单位，抛出错误
    raise ValueError("E_unit must be 'MPa' or 'kPa'")


def inertia_circle(D_mm: float) -> float:
    """
    计算圆形截面的惯性矩

    公式：I = π * D^4 / 64

    Args:
        D_mm (float): 圆形截面直径，单位为毫米

    Returns:
        float: 惯性矩，单位为 m^4

    Note:
        - 这是针对圆形截面的标准惯性矩计算公式
        - 输入直径会自动转换为米
        - 惯性矩用于弯矩计算：M = E * I * y''
    """
    # 将直径从毫米转换为米
    D_m = mm_to_m(D_mm)
    # 计算圆形截面惯性矩
    return math.pi * (D_m**4) / 64.0


def inertia_rectangle(b_mm: float, h_mm: float) -> float:
    """
    计算矩形截面的惯性矩

    公式：I = b * h^3 / 12

    Args:
        b_mm (float): 矩形截面宽度，单位为毫米
        h_mm (float): 矩形截面高度，单位为毫米

    Returns:
        float: 惯性矩，单位为 m^4

    Note:
        - 这是针对矩形截面的标准惯性矩计算公式
        - 假设中性轴平行于宽度方向
        - 输入尺寸会自动转换为米
    """
    # 将宽度和高度从毫米转换为米
    b_m = mm_to_m(b_mm)
    h_m = mm_to_m(h_mm)
    # 计算矩形截面惯性矩
    return b_m * (h_m**3) / 12.0


def compute_inertia(section_type: str, dims: dict) -> float:
    """
    根据截面类型计算惯性矩

    Args:
        section_type (str): 截面类型，'circle' 为圆形，'rect' 为矩形
        dims (dict): 截面尺寸参数
            - 圆形: {'D': 直径值}，单位为毫米
            - 矩形: {'b': 宽度, 'h': 高度}，单位为毫米

    Returns:
        float: 惯性矩，单位为 m^4

    Raises:
        ValueError: 当截面类型不支持或尺寸参数无效时抛出

    Note:
        - 自动调用对应的惯性矩计算函数
        - 包含参数校验，确保尺寸大于0
        - 这是材料力学中的重要参数，用于弯矩计算
    """
    # 标准化截面类型字符串为小写
    stype = section_type.lower()

    if stype == "circle":
        # 圆形截面：从字典中获取直径参数
        D = float(dims.get("D", 0))
        if D <= 0:
            raise ValueError("Circle section requires D > 0 (mm)")
        return inertia_circle(D)

    if stype == "rect":
        # 矩形截面：从字典中获取宽度和高度参数
        b = float(dims.get("b", 0))
        h = float(dims.get("h", 0))
        if b <= 0 or h <= 0:
            raise ValueError("Rect section requires b > 0 and h > 0 (mm)")
        return inertia_rectangle(b, h)

    # 不支持的截面类型
    raise ValueError("section_type must be 'circle' or 'rect'")


def parse_depth_disp(text: str) -> Tuple[List[float], List[float]]:
    """
    解析多行文本中的深度和位移数据

    从用户输入的文本中提取深度和位移数值，支持多种分隔符。
    会自动忽略非数值行和表头等无效内容。

    Args:
        text (str): 多行文本，每行包含深度和位移数据

    Returns:
        Tuple[List[float], List[float]]: (深度列表, 位移列表)
            - 深度单位为米 (m)
            - 位移单位为毫米 (mm)

    Note:
        - 支持的分隔符：逗号(,)、空格(\\s)、制表符(\\t)
        - 自动跳过空行和非数值行
        - 每行至少需要两个数值（深度在前，位移在后）
        - 适用于从Excel复制的数据粘贴输入
    """
    # 初始化结果列表
    depths: List[float] = []  # 深度数据列表
    disps: List[float] = []   # 位移数据列表

    # 逐行处理输入文本
    for raw in text.splitlines():
        # 去除行首尾空白字符
        line = raw.strip()
        # 跳过空行
        if not line:
            continue

        # 使用正则表达式分割行，支持逗号、空格、制表符
        tokens = re.split(r"[,\s]+", line)
        # 每行至少需要两个数值
        if len(tokens) < 2:
            continue

        # 尝试转换为数值
        try:
            x = float(tokens[0])  # 深度
            y = float(tokens[1])  # 位移
        except ValueError:
            # 转换失败，跳过该行（可能是表头或其他非数值内容）
            continue

        # 添加到结果列表
        depths.append(x)
        disps.append(y)

    return depths, disps


def clamp_degree(degree: int, min_deg: int = 3, max_deg: int = 9) -> int:
    """
    限制多项式拟合阶数在合理范围内

    防止阶数过低（拟合不足）或过高（过拟合或数值不稳定）。

    Args:
        degree (int): 用户指定的阶数
        min_deg (int): 最小允许阶数，默认 3
        max_deg (int): 最大允许阶数，默认 9

    Returns:
        int: 限制后的阶数

    Note:
        - 阶数范围基于经验值：3-9 阶通常能平衡拟合精度和稳定性
        - 阶数过高可能导致 NumPy 发出 RankWarning
        - 阶数过低可能无法捕捉位移曲线的特征
    """
    return max(min_deg, min(max_deg, int(degree)))


def format_polynomial(coeffs: Iterable[float], var: str = 'x', precision: int = 4) -> str:
    """
    将多项式系数数组格式化为可读的数学表达式

    Args:
        coeffs: 从高次到低次的系数数组 [an, an-1, ..., a1, a0]
        var: 变量名，默认 'x'
        precision: 小数精度，默认 4 位

    Returns:
        格式化的表达式字符串，如 "y = 0.5x³ - 2.3x² + 1.2x + 0.8"

    Example:
        >>> format_polynomial([0.5, -2.3, 1.2, 0.8])
        'y = 0.5x³ - 2.3x² + 1.2x + 0.8'
    """
    coeffs_list = list(coeffs)
    degree = len(coeffs_list) - 1
    terms = []

    # Unicode 上标字符映射（用于指数）
    superscript_map = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")

    for i, coeff in enumerate(coeffs_list):
        power = degree - i

        # 跳过系数接近 0 的项
        if abs(coeff) < 1e-10:
            continue

        # 判断是否使用科学计数法（系数很小或很大时）
        abs_coeff = abs(coeff)
        if abs_coeff < 0.01 or abs_coeff > 1000:
            # 使用科学计数法
            exp = int(f"{abs_coeff:.0e}".split('e')[1])
            mantissa = abs_coeff / (10 ** exp)

            # 格式化尾数部分
            mantissa_str = f"{mantissa:.{precision}f}".rstrip('0').rstrip('.')
            # 格式化指数部分（使用上标）
            exp_str = str(exp).translate(superscript_map)
            coeff_str = f"{mantissa_str}×10{exp_str}"
        else:
            # 使用普通格式
            coeff_str = f"{abs_coeff:.{precision}f}".rstrip('0').rstrip('.')

        # 构建项表达式
        if power == 0:
            # 常数项
            term = coeff_str
        elif power == 1:
            # 一次项
            if abs_coeff == 1.0:
                term = var
            else:
                term = f"{coeff_str}{var}"
        else:
            # 高次项，使用上标
            exponent = str(power).translate(superscript_map)
            if abs_coeff == 1.0:
                term = f"{var}{exponent}"
            else:
                term = f"{coeff_str}{var}{exponent}"

        # 添加符号
        if coeff < 0:
            terms.append(f"- {term}")
        else:
            terms.append(f"+ {term}" if terms else term)

    # 如果所有系数都接近 0
    if not terms:
        return "y = 0"

    # 连接所有项
    result = " ".join(terms)
    return f"y = {result}"

