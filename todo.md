这份文档是为您（开发者）准备的**技术设计文档（Technical Design Document, TDD）**。

它详细规划了代码架构、类设计、数据流向以及核心算法的实现方式。您可以直接参照这份文档在 IDE 中建立项目。

---

# 围护桩反分析工具 (PileBackAnalysis) - 开发文档

| 项目信息 | 内容 |
| :--- | :--- |
| **项目名称** | PileBackAnalysis (围护桩位移-弯矩反分析工具) |
| **应用类型** | Windows 桌面应用程序 (.exe) |
| **开发语言** | Python 3.10+ |
| **核心算法** | 最小二乘法多项式拟合 (Least Squares Polynomial Fitting) |
| **版本** | V1.2 (对应 PRD V1.2) |

---

## 1. 技术栈选型 (Tech Stack)

| 模块 | 库/工具 | 版本建议 | 选型理由 |
| :--- | :--- | :--- | :--- |
| **GUI 框架** | **PyQt6** | Latest | 现代化、原生控件丰富、文档齐全，比 Tkinter 美观。 |
| **数值计算** | **NumPy** | Latest | 处理矩阵运算、多项式拟合 (`polyfit`)、求导 (`polyder`) 的核心库。 |
| **数据处理** | **Pandas** | Latest | (可选) 用于后续扩展 Excel 导入导出功能。 |
| **图表绘制** | **Matplotlib** | Latest | 科学绘图标准库，通过 `FigureCanvasQTAgg` 嵌入 PyQt。 |
| **打包工具** | **PyInstaller** | Latest | 将 Python 脚本打包为独立的 `.exe` 文件。 |

---

## 2. 项目文件结构 (Project Structure)

建议采用 **MVC (Model-View-Controller)** 的分层思想，将界面与计算逻辑分离。

```text
PileBackAnalysis/
│
├── main.py                 # [入口] 程序启动文件
├── requirements.txt        # 依赖列表
├── README.md               # 说明文档
│
├── core/                   # [Model] 核心逻辑层
│   ├── __init__.py
│   ├── calculator.py       # 核心算法类：负责拟合、求导、弯矩计算
│   └── utils.py            # 工具函数：单位换算、数据校验
│
├── ui/                     # [View] 界面层
│   ├── __init__.py
│   ├── main_window.py      # 主窗口布局与交互逻辑
│   ├── plotting.py         # 封装 Matplotlib 的画布控件
│   └── components.py       # 自定义小组件 (如输入框组)
│
└── assets/                 # 资源文件
    └── icon.ico            # 软件图标
```

---

## 3. 核心类设计 (Class Design)

### 3.1 `core/calculator.py` - 核心计算引擎

这是整个软件的“大脑”，不包含任何 GUI 代码。

```python
class PileSolver:
    def __init__(self):
        self.poly_coeffs = None  # 拟合后的多项式系数 [an, ..., a0]
        self.E_kpa = 0.0         # 弹性模量 (kPa)
        self.I_m4 = 0.0          # 惯性矩 (m^4)
        self.fitting_stats = {}  # 存储 R2, RMSE

    def set_parameters(self, E_val, E_unit, section_type, dims):
        """
        设置材料与截面参数
        E_unit: 'MPa' or 'kPa'
        section_type: 'circle' or 'rect'
        dims: dict, e.g., {'D': 800} or {'b': 800, 'h': 1000}
        """
        # TODO: 实现单位换算逻辑 (MPa -> kPa, mm -> m)
        pass

    def fit_data(self, x_depths, y_disps_mm, degree=5):
        """
        执行拟合
        x_depths: list/array (m)
        y_disps_mm: list/array (mm)
        degree: int (拟合阶数)
        """
        # 1. 单位清洗: y_m = y_mm / 1000
        # 2. numpy.polyfit(x, y_m, degree) 得到系数
        # 3. 计算 R2 和 RMSE 并存储
        pass

    def get_results_arrays(self, num_points=100):
        """
        生成用于绘图的密集数组
        Returns:
            x_dense (m)
            y_fit_mm (mm)
            moment_knm (kN.m)
        """
        # 1. 生成密集 x 坐标: np.linspace(min, max, num)
        # 2. 计算 y_fit: np.polyval
        # 3. 计算 y'': np.polyder(coeffs, 2) -> np.polyval
        # 4. 计算 M = E * I * y''
        pass

    def query_single_point(self, x_query):
        """
        V1.2 新增功能：查询特定深度的值
        Returns: (y_second_deriv, moment_val)
        """
        pass
```

### 3.2 `ui/main_window.py` - 主界面控制器

负责组装界面元素，并连接信号与槽。

```python
class MainWindow(QMainWindow):
    def __init__(self):
        # 初始化 UI 布局
        # 初始化 PileSolver 实例
        self.solver = PileSolver()
        
    def setup_ui(self):
        # 左侧：InputPanel (QGroupBox)
        # 右侧：OutputPanel (TabWidget: 图表页, 数据页)
        # 底部：StatusPanel (R2, RMSE 显示)
        pass

    def on_calculate_clicked(self):
        # 1. 获取输入控件的值
        # 2. 校验数据 (try-except)
        # 3. 调用 self.solver.set_parameters()
        # 4. 调用 self.solver.fit_data()
        # 5. 调用 self.update_plots() 和 self.update_stats()
        pass
```

---

## 4. 关键算法实现细节 (Implementation Details)

### 4.1 单位统一 (非常重要)
在 `core/utils.py` 或 `calculator.py` 内部强制执行：
*   **输入**：$Y_{input}$ (mm), $E_{input}$ (MPa/kPa), $D/b/h$ (mm)
*   **计算内核**：全部转为 **kN** 和 **m**。
    *   $Y_{calc} = Y_{input} / 1000$
    *   $E_{calc} = E_{input} \times 1000$ (若输入为 MPa)
    *   $I_{calc} = \text{Calculate based on } (D/1000)$
*   **输出**：
    *   弯矩 $M$ 直接输出 ($kN \cdot m$)
    *   绘图位移需转回 mm: $Y_{plot} = Y_{fit} \times 1000$

### 4.2 拟合与求导 (NumPy API)
```python
import numpy as np

# 1. 拟合 (得到系数向量 p)
# p[0]是最高次项系数, p[-1]是常数项
coeffs = np.polyfit(x, y, deg)

# 2. 生成多项式对象 (方便后续计算)
poly_y = np.poly1d(coeffs)

# 3. 求二阶导数多项式
poly_y_prime2 = np.polyder(poly_y, 2)

# 4. 计算某一点的值
y_val = poly_y(x_val)          # 位移 (m)
curvature = poly_y_prime2(x_val) # 曲率 (1/m)
moment = E * I * curvature     # 弯矩 (kN.m)
```

### 4.3 评价指标计算
```python
# RMSE
rmse = np.sqrt(np.mean((y_measured - y_fitted)**2)) * 1000 # 结果转为 mm

# R-Squared
ss_res = np.sum((y_measured - y_fitted)**2)
ss_tot = np.sum((y_measured - np.mean(y_measured))**2)
r2 = 1 - (ss_res / ss_tot)
```

---

## 5. UI 布局草图 (Layout Plan)

使用 `QHBoxLayout` 将窗口分为左右两部分：

*   **左侧面板 (固定宽度 300px)**
    *   **数据输入区**：多行文本框 (TextEdit)，支持 Excel 粘贴。
    *   **参数设置区**：
        *   $E$ 值输入 + 单位下拉框。
        *   截面类型 (Radio Button: 圆形/矩形) + 对应尺寸输入框。
    *   **拟合控制区**：
        *   阶数滑块 (Slider): 3~9。
        *   “开始计算”按钮 (大号)。
    *   **查询工具 (V1.2)**：
        *   输入深度 $x$ -> 显示 $M$。

*   **右侧面板 (自适应拉伸)**
    *   **Matplotlib 画布**：
        *   子图1：深度-位移对比图。
        *   子图2：深度-弯矩分布图。
    *   **统计信息栏 (底部)**：
        *   显示 $R^2$, RMSE, 最大弯矩值。

---

## 6. 开发步骤清单 (Checklist)

1.  **环境搭建**：
    *   [ ] `conda create -n pile_tool python=3.10`
    *   [ ] `pip install numpy PyQt6 matplotlib`
2.  **核心逻辑开发**：
    *   [ ] 编写 `calculator.py`，实现 `fit_data` 和 `get_results`。
    *   [ ] 编写单元测试，用手算数据验证 $M=EIy''$ 是否准确。
3.  **UI 骨架搭建**：
    *   [ ] 编写 `main_window.py`，画出左右布局。
    *   [ ] 嵌入 Matplotlib 空白图表。
4.  **逻辑对接**：
    *   [ ] 将按钮点击事件连接到计算函数。
    *   [ ] 实现图表刷新逻辑。
5.  **V1.2 功能追加**：
    *   [ ] 添加“任意深度查询”的小面板。
6.  **打包发布**：
    *   [ ] `pyinstaller --noconsole --onefile main.py`
    *   [ ] 在另一台电脑上测试 `.exe`。

---

## 7. 常见坑点预警

1.  **坐标轴方向**：
    *   Matplotlib 默认 Y 轴向上为正。
    *   岩土工程习惯：**Y 轴（深度）向下为正**。
    *   *解决*：使用 `ax.invert_yaxis()`。
2.  **输入数据清洗**：
    *   用户从 Excel 粘贴过来可能带有表头（如“深度”、“位移”中文）。
    *   *解决*：在解析文本时，使用 `try-float` 转换，忽略非数字行。
3.  **多项式震荡**：
    *   当阶数 $n > 7$ 时，NumPy 可能会报 `RankWarning`（条件数差）。
    *   *解决*：在 UI 上限制最高阶数为 9，并捕获 Warning 提示用户“阶数过高可能失真”。