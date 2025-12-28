@echo off
setlocal enabledelayedexpansion
REM ============================================
REM PileBackAnalysis - Optimized Build Script
REM ============================================
REM
REM 项目依赖分析：
REM   - PyQt6: QtWidgets, QtCore, QtGui
REM   - NumPy: 基础数组和多项式操作
REM   - SciPy: 仅 scipy.interpolate.UnivariateSpline
REM   - Pandas: read_csv, read_excel
REM   - Matplotlib: Figure, FigureCanvasQTAgg
REM   - mplcursors: cursor
REM   - PIL: matplotlib 间接依赖
REM
REM 不能排除的模块（已验证会报错）：
REM   - PIL/pillow: matplotlib.colors 需要
REM   - ssl: secrets 模块需要，numpy.random 依赖
REM   - xml: pandas 读取 Excel 需要
REM   - scipy.*: interpolate 依赖链太复杂，几乎需要整个 scipy
REM ============================================

echo [1/5] Cleaning old build files...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist main.spec del main.spec

echo [2/5] Building optimized executable...
pyinstaller --clean --noconsole --onefile ^
    --name "PileBackAnalysis" ^
    --hidden-import=PyQt6.QtCore ^
    --hidden-import=PyQt6.QtGui ^
    --hidden-import=PyQt6.QtWidgets ^
    --hidden-import=scipy.interpolate ^
    --collect-data matplotlib ^
    --exclude-module tkinter ^
    --exclude-module IPython ^
    --exclude-module jupyter ^
    --exclude-module notebook ^
    --exclude-module pytest ^
    --exclude-module setuptools ^
    --exclude-module pandas.tests ^
    --exclude-module matplotlib.tests ^
    main.py

REM ============================================
REM 排除模块说明：
REM
REM [确定排除 - 开发/测试工具]
REM   tkinter      - 使用 PyQt6，不需要 Tk
REM   IPython      - 交互式开发环境
REM   jupyter      - Jupyter 笔记本
REM   notebook     - Jupyter 笔记本
REM   pytest       - 测试框架
REM   setuptools   - 打包工具
REM
REM [确定排除 - 测试模块]
REM   pandas.tests       - Pandas 测试
REM   matplotlib.tests   - Matplotlib 测试
REM
REM [不能排除 - scipy.interpolate 依赖链太复杂]
REM   scipy 几乎所有子模块都被 interpolate 间接依赖
REM   包括: spatial, special, linalg, fft, constants, optimize 等
REM ============================================

echo [3/5] Checking build result...
if exist "dist\PileBackAnalysis.exe" (
    echo SUCCESS: Build completed!
    echo.
    echo Output file: dist\PileBackAnalysis.exe
    dir "dist\PileBackAnalysis.exe"
) else (
    echo ERROR: Build failed!
    exit /b 1
)

echo [4/5] Calculating file size...
for %%F in ("dist\PileBackAnalysis.exe") do (
    set size=%%~zF
    set /a sizeMB=!size! / 1048576
    echo File size: !sizeMB! MB
)

echo [5/5] Cleaning temporary files...
rmdir /s /q build
del main.spec

echo.
echo ============================================
echo Build finished! Output: dist\PileBackAnalysis.exe
echo ============================================
pause
