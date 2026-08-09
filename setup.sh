#!/bin/bash
# setup.sh — cài đặt OCR pipeline (Apple Vision + anydoc) trên macOS
# Chạy sau khi clone repo: ./setup.sh
# Kết quả: cài anydoc CLI + Python venv + compile ocr-vision binary + wrapper scripts

set -e
echo "=== OCR Pipeline Setup ==="

# 1. anydoc CLI (npm global)
echo "[1/5] Cài anydoc CLI (npm)..."
if command -v anydoc &>/dev/null; then
  echo "  ✓ anydoc đã có"
else
  npm install -g @firecrawl/anydoc
  echo "  ✓ cài xong"
fi

# 2. Python venv
echo "[2/5] Tạo Python venv (~/venvs/anydoc)..."
mkdir -p ~/venvs
if [ ! -x ~/venvs/anydoc/bin/python ]; then
  # Tìm python >= 3.10
  PY=""
  for p in python3.13 python3.12 python3.11 python3.10; do
    if command -v $p &>/dev/null; then PY=$p; break; fi
  done
  [ -z "$PY" ] && PY=python3
  $PY -m venv ~/venvs/anydoc
  ~/venvs/anydoc/bin/pip install -q firecrawl-anydoc pillow
  echo "  ✓ venv tạo xong (python: $PY)"
else
  echo "  ✓ venv đã có"
fi

# 3. Compile ocr-vision binary
echo "[3/5] Compile ocr-vision (Apple Vision OCR)..."
swiftc -O bin/ocr-vision.swift -o /usr/local/bin/ocr-vision-bin
echo "  ✓ /usr/local/bin/ocr-vision-bin"

# 4. Cài wrapper scripts
echo "[4/5] Cài wrapper scripts..."
install -m 755 bin/ocr-vision.swift /usr/local/bin/ocr-vision.swift
install -m 755 bin/ocr-scan /usr/local/bin/ocr-scan
install -m 755 bin/anydoc-convert /usr/local/bin/anydoc-convert
echo "  ✓ ocr-scan, ocr-vision.swift, anydoc-convert"

# 5. Verify
echo "[5/5] Verify..."
anydoc --version 2>/dev/null && echo "  ✓ anydoc CLI OK" || echo "  ⚠ anydoc CLI chưa verify"
~/venvs/anydoc/bin/python -c "import anydoc; print('  ✓ anydoc Python OK')"
ls -la /usr/local/bin/ocr-vision-bin && echo "  ✓ ocr-vision-bin OK"

echo ""
echo "=== HOÀN TẤT ==="
echo "Dùng: ocr-scan <file> [zh-Hans|vi-VN|en-US] [out.md]"
echo "      anydoc-convert <file.docx/xlsx/pdf>"
