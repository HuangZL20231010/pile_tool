#!/bin/bash
# ============================================
# PileBackAnalysis - Build Script (Mac)
# ============================================

echo "[1/4] Cleaning old build files..."
rm -rf build
rm -rf dist
rm -f main.spec

echo "[2/4] Building executable..."
pyinstaller --clean --noconsole --onefile \
    --name "PileBackAnalysis" \
    --hidden-import=PyQt6.QtCore \
    --hidden-import=PyQt6.QtGui \
    --hidden-import=PyQt6.QtWidgets \
    --collect-data matplotlib \
    main.py

echo "[3/4] Checking build result..."
if [ -f "dist/PileBackAnalysis" ]; then
    echo "SUCCESS: Build completed!"
    echo ""
    echo "Output file: dist/PileBackAnalysis"
    ls -lh "dist/PileBackAnalysis"
else
    echo "ERROR: Build failed!"
    exit 1
fi

echo "[4/4] Cleaning temporary files..."
rm -rf build
rm -f main.spec

echo ""
echo "============================================"
echo "Build finished! Output: dist/PileBackAnalysis"
echo "============================================"

