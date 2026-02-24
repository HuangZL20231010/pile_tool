# CLAUDE.md - 项目指南

## 项目概述

围护桩反分析工具 (PileBackAnalysis) - 基于测斜仪位移数据反算围护桩内力的 PyQt6 桌面应用程序。

## 快速开始

### 环境设置
```bash
# 创建虚拟环境
conda create -n pile_tool python=3.10
conda activate pile_tool

# 安装依赖
pip install -r requirements.txt
```

### 运行程序
```bash
conda activate pile_tool
python main.py
```

### 打包发布
```bash
conda activate pile_tool
pyinstaller --noconsole --onefile --name PileBackAnalysis main.py
```

## 项目结构

```
pile_tool/
├── main.py              # 程序入口
├── requirements.txt     # 依赖列表
├── PRD.md               # 产品需求文档
├── README.md            # 用户文档
├── CLAUDE.md            # 本文件
├── core/                # 核心计算模块
│   ├── __init__.py
│   ├── calculator.py    # PileSolver 类 - 拟合与力学计算
│   ├── utils.py         # 工具函数（单位转换、数据解析）
│   └── file_importer.py # CSV/Excel 文件导入
└── ui/                  # 用户界面模块
    ├── __init__.py
    ├── main_window.py   # MainWindow 主窗口
    ├── components.py    # UI 组件（输入框、滑块、按钮等）
    └── plotting.py      # Matplotlib 绑图画布
```

## 核心架构

### 计算引擎 (core/calculator.py)

`PileSolver` 类是核心计算引擎，负责：
- 多项式拟合 (3-9 阶)
- 三次/五次样条平滑插值
- 力学计算：M = E·I·y''，Q = E·I·y'''，p = E·I·y''''
- L-curve 法自动选择最优平滑参数
- 边界条件处理（奇对称镜像法）

关键方法：
- `set_parameters()` - 设置材料和截面参数
- `fit_data()` - 执行拟合（多项式/样条），支持 `boundary_conditions` 参数
- `get_results_arrays()` - 生成绘图数据
- `query_single_point()` - 单点查询
- `find_optimal_sigma()` - L-curve 法自动参数选择
- `_find_l_curve_corner()` - L 曲线拐角识别（Menger 曲率法）
- `_apply_odd_symmetric_mirror()` - 奇对称镜像数据增强（边界条件实现）

### UI 框架 (ui/)

基于 PyQt6 的现代卡片式 UI：
- `MainWindow` - 主窗口，左右分栏布局（左侧面板支持滚动）
- `DataInputGroup` - 数据输入（文本框/文件导入/边界条件设置）
- `ParamsGroup` - 材料和截面参数
- `FitControlGroup` - 算法选择和参数控制（σ 范围动态调整）
- `QueryGroup` - 单点查询
- `StatsBar` - 统计信息栏
- `PlotCanvas` - Matplotlib 四图联动画布

### 信号槽连接

```python
# 计算按钮
fit_group.calc_button.clicked -> on_calculate_clicked()

# 查询按钮
query_group.query_clicked -> on_query_clicked()

# 自动选择 σ
fit_group.auto_sigma_requested -> on_auto_sigma_clicked()

# 数据变化时更新 σ 滑块范围
data_group.data_changed -> on_data_changed()

# 算法切换时更新 σ 滑块范围
fit_group.algo_changed -> _on_algo_type_changed()
```

## 关键算法

### 平滑因子公式
```
s = N × σ²
```
- N: 数据点数量
- σ: 测斜仪预估误差 (mm)

### L-curve 法自动选择最优 σ

在 log(残差) vs log(粗糙度) 空间中找 L 曲线拐角，平衡拟合精度与导数光滑性：
1. 对数尺度生成 50 个候选 σ 值
2. 对每个 σ：拟合样条，计算残差 ρ = Σ(yᵢ−f(xᵢ))² 和粗糙度 η = ∫f''(x)²dx
3. 在 log-log 空间用 Menger 曲率找 L 曲线拐角
4. 拐角对应的 σ 即为最优值（残差与粗糙度的最佳平衡点）

### σ 参数范围
σ 滑块范围根据数据点数量动态调整：
- 点数 ≤ 40：最大 2.5mm
- 点数 > 40 且 ≤ 60：最大 4mm
- 点数 > 60：最大 8mm

### 边界条件（奇对称镜像法）
用于强制样条曲线满足物理边界条件：
- 约束效果：y(x₀) = 指定位移，y''(x₀) = 0（弯矩为零）
- 实现原理：将数据点 (xᵢ, yᵢ) 关于边界点 (x₀, y₀) 镜像为 (2x₀-xᵢ, 2y₀-yᵢ)
- 边界条件字典格式：
```python
boundary_conditions = {
    'top_enabled': bool,
    'top_depth': float,     # 桩顶深度 (m)
    'top_disp': float,      # 桩顶位移 (mm)
    'bottom_enabled': bool,
    'bottom_depth': float,  # 桩底深度 (m)
    'bottom_disp': float,   # 桩底位移 (mm)
}
```

## 单位约定

| 物理量 | 输入单位 | 内部计算单位 | 输出单位 |
|--------|----------|--------------|----------|
| 深度 | m | m | m |
| 位移 | mm | m | mm |
| 弹性模量 E | MPa/kPa | kPa | - |
| 截面尺寸 | mm | m | - |
| 弯矩 M | - | - | kN·m |
| 剪力 Q | - | - | kN |
| 土压力 p | - | - | kPa |

## 代码风格

- Python 3.10+
- 类型注解 (typing)
- 中文注释和文档字符串
- 模块化设计，核心计算与 UI 分离

## 常见开发任务

### 添加新的拟合算法
1. 在 `calculator.py` 的 `fit_data()` 中添加新分支
2. 在 `components.py` 的 `FitControlGroup` 中添加 RadioButton
3. 更新 `get_algo_type()` 返回值

### 修改 UI 样式
主题颜色定义在 `main_window.py` 的 `_apply_theme()` 方法中。

### 添加新的统计指标
1. 在 `calculator.py` 的 `fitting_stats` 字典中添加
2. 在 `components.py` 的 `StatsBar.update_stats()` 中添加显示

## 注意事项

- 土压力曲线由四阶导数计算，数值可能不稳定
- 五次样条需要至少 6 个数据点
- L-curve 自动选择 σ 仅需 50 次拟合，速度快
- 绘图坐标系：Y 轴深度向下为正（岩土工程习惯）
- 边界条件仅对样条拟合有效，多项式拟合不支持
- 左侧面板使用 QScrollArea 包装，支持滚动查看
