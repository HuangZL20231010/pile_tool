# ============================================
# 围护桩反分析工具 - 打包脚本 (PowerShell)
# ============================================

Write-Host "[1/4] 清理旧的构建文件..." -ForegroundColor Cyan
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "main.spec") { Remove-Item -Force "main.spec" }

Write-Host "[2/4] 开始打包..." -ForegroundColor Cyan
pyinstaller --clean --noconsole --onefile `
    --name "PileBackAnalysis" `
    --hidden-import=PyQt6.QtCore `
    --hidden-import=PyQt6.QtGui `
    --hidden-import=PyQt6.QtWidgets `
    --collect-data matplotlib `
    main.py

Write-Host "[3/4] 检查打包结果..." -ForegroundColor Cyan
if (Test-Path "dist\PileBackAnalysis.exe") {
    Write-Host "✓ 打包成功！" -ForegroundColor Green
    Write-Host ""
    Write-Host "生成文件: dist\PileBackAnalysis.exe"
    Get-Item "dist\PileBackAnalysis.exe" | Format-List Length, LastWriteTime
} else {
    Write-Host "✗ 打包失败！" -ForegroundColor Red
    exit 1
}

Write-Host "[4/4] 清理临时文件..." -ForegroundColor Cyan
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "main.spec") { Remove-Item -Force "main.spec" }

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "打包完成！可执行文件位于: dist\PileBackAnalysis.exe" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green

Read-Host "按回车键退出"
