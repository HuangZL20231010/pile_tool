---
name: pile-tool-plan
overview: 按设计文档实现围护桩反分析工具，UI 用科技风格主题，分步完成核心计算、UI、联调与打包。
todos:
  - id: env-setup
    content: 创建虚拟环境并安装依赖
    status: completed
  - id: core-logic
    content: 实现 PileSolver 与单位换算工具
    status: completed
    dependencies:
      - env-setup
  - id: ui-components
    content: 搭建输入/查询组件与绘图封装
    status: completed
    dependencies:
      - core-logic
  - id: main-window
    content: 组装主界面并联调计算与绘图
    status: completed
    dependencies:
      - ui-components
  - id: testing
    content: 用示例数据验证拟合与查询
    status: completed
    dependencies:
      - main-window
  - id: packaging
    content: 配置并生成 PyInstaller exe
    status: completed
    dependencies:
      - testing
---

# PileBackAnalysis 实施计划

## 范围

- 按 `todo.md` 设计文档落地桌面应用（PyQt6），科技风格主题；功能含拟合、弯矩计算、R2/RMSE 显示、任意深度查询、Matplotlib 绘图，最终打包为单文件 exe。

## 方案

1) 环境与依赖

- 建立虚拟环境（Python 3.10），安装 numpy、PyQt6、matplotlib（如需 pandas 预留导入导出支持）。

2) 核心计算层 `core/`

- 在 `core/calculator.py` 实现 PileSolver：参数设置、单位统一（mm→m，MPa→kPa，截面惯性矩计算）、多项式拟合、R2/RMSE 计算、二阶导与弯矩生成、单点查询。
- 在 `core/utils.py` 封装单位换算、截面属性计算、数据清洗（忽略非数字行）。

3) 界面层 `ui/`

- `ui/components.py`：输入面板、参数/截面选择、阶数滑块、查询小面板等可复用控件。
- `ui/plotting.py`：Matplotlib 画布封装，提供位移/弯矩双子图，支持 y 轴反转。
- `ui/main_window.py`：搭建左右布局，连接事件：读取输入→校验→调用 solver→刷新图表与统计→支持查询功能。
- 应用科技风格配色（深色/霓虹点缀），统一字号/间距，必要时使用 Qt palette/style sheet。

4) 应用入口

- `main.py` 初始化 QApplication、加载主窗体与图标，设置默认主题。

5) 联调与验证

- 用示例数据跑通拟合、弯矩、查询，检查单位一致性和异常处理（阶数过高提示）。

6) 打包

- 更新 `requirements.txt`，使用 PyInstaller 生成无控制台的单文件 exe，验证启动与绘图。

## 交付物

- 源码结构与 `requirements.txt`、`README.md` 简述用法。
- 可运行 exe（或打包脚本/命令）。

## 实施顺序

1. 环境与依赖
2. 核心计算实现
3. UI 组件与主题
4. 主窗体联调
5. 功能验证与示例数据
6. 打包与说明