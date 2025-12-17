@echo off
REM ============================================
REM PileBackAnalysis - Optimized Build Script
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
    --collect-data matplotlib ^
    --exclude-module tkinter ^
    --exclude-module PIL ^
    --exclude-module IPython ^
    --exclude-module jupyter ^
    --exclude-module notebook ^
    --exclude-module scipy ^
    main.py

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
