"""
围护桩反分析工具文件导入模块

提供从CSV和Excel文件导入数据的功能。
支持自动检测表头并提取深度和位移数据。
"""

from __future__ import annotations

from typing import List, Tuple
import pandas as pd
from pathlib import Path


def detect_header_row(df: pd.DataFrame) -> bool:
    """
    检测DataFrame的第一行是否为表头

    通过尝试将第一行的数据转换为浮点数来判断是否为表头。
    如果任何单元格无法转换为浮点数，则认为该行是表头。

    Args:
        df (pd.DataFrame): 待检测的DataFrame

    Returns:
        bool: 如果第一行包含非数值数据（表头），返回True；否则返回False

    Note:
        - 表头通常包含文字描述，如 "depth", "displacement", "深度", "位移" 等
        - 纯数值行会被识别为数据行
        - 混合行（部分文字部分数值）也会被识别为表头
    """
    if df.empty or len(df) == 0:
        return False

    # 获取第一行数据
    first_row = df.iloc[0]

    # 尝试将第一行的每个单元格转换为浮点数
    for cell in first_row:
        try:
            float(cell)
        except (ValueError, TypeError):
            # 无法转换为浮点数，说明是非数值数据（表头）
            return True

    # 所有单元格都能转换为浮点数，说明是数据行
    return False


def load_data_from_file(filepath: str) -> Tuple[List[float], List[float]]:
    """
    从CSV或Excel文件加载深度和位移数据

    自动检测文件类型，读取前两列作为深度和位移数据。
    支持自动检测并跳过表头行。

    Args:
        filepath (str): 文件路径，支持 .csv 和 .xlsx 格式

    Returns:
        Tuple[List[float], List[float]]: (深度列表, 位移列表)
            - 深度单位为米 (m)
            - 位移单位为毫米 (mm)

    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 文件格式错误、数据不足或无法解析
        Exception: 其他读取错误

    Note:
        - 仅使用前两列数据，其他列将被忽略
        - 返回格式与 utils.parse_depth_disp() 相同，便于统一处理
        - 对于Excel文件，默认读取第一个工作表
    """
    # 检查文件是否存在
    file_path = Path(filepath)
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {filepath}")

    # 根据文件扩展名确定文件类型
    file_ext = file_path.suffix.lower()

    try:
        # 读取文件到DataFrame（不预设表头）
        if file_ext == '.csv':
            # 读取CSV文件
            df = pd.read_csv(filepath, header=None, encoding='utf-8')
        elif file_ext in ['.xlsx', '.xls']:
            # 读取Excel文件（第一个工作表）
            df = pd.read_excel(filepath, sheet_name=0, header=None)
        else:
            raise ValueError(f"不支持的文件格式: {file_ext}。仅支持 .csv 和 .xlsx 文件")

        # 检查文件是否为空
        if df.empty or len(df) == 0:
            raise ValueError("文件为空，没有数据")

        # 检测并跳过表头
        if detect_header_row(df):
            # 第一行是表头，跳过
            df = df.iloc[1:]

        # 再次检查是否还有数据
        if df.empty or len(df) == 0:
            raise ValueError("跳过表头后没有数据")

        # 检查列数
        if df.shape[1] < 2:
            raise ValueError(f"数据列数不足。需要至少2列（深度、位移），但文件只有 {df.shape[1]} 列")

        # 提取前两列
        df_data = df.iloc[:, :2]

        # 转换为浮点数列表
        depths: List[float] = []
        disps: List[float] = []

        for idx, row in df_data.iterrows():
            try:
                depth = float(row.iloc[0])
                disp = float(row.iloc[1])
                depths.append(depth)
                disps.append(disp)
            except (ValueError, TypeError) as e:
                # 跳过无法转换的行，但记录警告
                print(f"[警告] 第 {idx + 1} 行数据无法转换为数值，已跳过: {e}")
                continue

        # 检查是否有有效数据
        if len(depths) == 0 or len(disps) == 0:
            raise ValueError("文件中没有有效的数值数据")

        return depths, disps

    except pd.errors.EmptyDataError:
        raise ValueError("文件为空或格式错误")
    except pd.errors.ParserError as e:
        raise ValueError(f"文件解析错误: {str(e)}")
    except PermissionError:
        raise PermissionError(f"无法访问文件（权限不足或文件被占用）: {filepath}")
    except Exception as e:
        # 捕获其他未预期的错误
        raise Exception(f"读取文件时发生错误: {str(e)}")
