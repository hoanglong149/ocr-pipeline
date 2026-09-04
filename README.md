# OCR Pipeline — Apple Vision + anydoc

Pipeline OCR/convert tài liệu chạy local trên macOS — không cloud, không API key, miễn phí.

## Thành phần

| Tool | Chức năng | Công nghệ |
|------|-----------|-----------|
| `ocr-vision.swift` | OCR 1 ảnh (PNG/JPG/TIFF) | Apple Vision framework (local) |
| `ocr-vision-bin` | Binary đã compile (nhanh hơn swift script) | `swiftc -O` |
| `ocr-scan` | OCR PDF scan/ảnh, tự split trang | Apple Vision + sips |
| `anydoc-convert` | Convert DOCX/XLSX/PPT/PDF(text) → Markdown | firecrawl-anydoc (Rust) |
| `hybrid_v2.py` | Hybrid OCR: document mode + GLM-OCR | Apple Vision + Ollama GLM-OCR |

## Cài đặt

```bash
git clone <repo-url> && cd ocr-pipeline
./setup.sh
```

Setup sẽ:
1. Cài `@firecrawl/anydoc` (npm global) — convert tài liệu văn phòng
2. Tạo Python venv `~/venvs/anydoc` (py3.12) — binding anydoc + pillow
3. Compile `ocr-vision-bin` — binary OCR nhanh
4. Install wrapper scripts vào `/usr/local/bin/`

## Cách dùng

### OCR scan (tiếng Trung mặc định)
```bash
ocr-scan book-scan.pdf zh-Hans out.md   # PDF tự split từng trang
ocr-scan page.png vi-VN                 # tiếng Việt
ocr-scan image.jpg en-US                # tiếng Anh
```

### Convert tài liệu văn phòng
```bash
anydoc-convert bao-gia.docx             # → bao-gia.md
anydoc-convert spec.xlsx -o spec.md     # ghi đích chỉ định
```

### OCR 1 ảnh trực tiếp (swift)
```bash
swift /usr/local/bin/ocr-vision.swift image.png zh-Hans
# hoặc binary đã compile:
/usr/local/bin/ocr-vision-bin image.png zh-Hans
```

## Ngôn ngữ hỗ trợ

- `zh-Hans` — tiếng Trung giản thể (mặc định)
- `zh-Hant` — tiếng Trung phồn thể
- `vi-VN` — tiếng Việt
- `en-US` — tiếng Anh

## Benchmark (Mac mini i3-8100B, 4 cores)

| Scenario | Tốc độ |
|----------|--------|
| Ảnh nhỏ (3 dòng) | ~1.0s |
| Trang A4 đầy text (40 dòng TQ) | ~3.6s |
| PDF 5 trang | ~5.4s |
| CPU khi chạy | ~103% (1 core), nhẹ |
| 2 OCR song song | ~138% tổng, vẫn ổn |

## Độ chính xác

| Loại nội dung | Độ chính xác |
|---|---|
| Số liệu/bảng BOQ | ~100% (kể cả ảnh nghiêng, mờ) |
| Chữ Latinh/tiếng Anh | Rất tốt |
| Ký tự Hán đơn giản | Tốt |
| Ký tự Hán phức tạp + mờ | Trung bình (cần check lại) |
| Công thức toán/LaTeX | ❌ Không hỗ trợ (plain text) |

## Hybrid OCR v2 (Document Mode + GLM-OCR)

Kết hợp Apple Vision document mode (structured text) + GLM-OCR (table/formula) qua Ollama.

### Yêu cầu
- macOS 26+ (cho `RecognizeDocumentsRequest`)
- Ollama với model `glm-ocr:latest`
- `~/bin/mac-ocr-dev` (build từ source)

### Cách dùng
```bash
# Test 5 trang
python3 bin/hybrid_v2.py <pdf> <output_dir> 0 5

# Chạy full book
python3 bin/hybrid_v2.py <pdf> <output_dir>
```

### Workflow
1. mac-ocr document → structured text (Neural Engine, ~1s/trang)
2. Detect trang cần GLM-OCR (formula, table patterns)
3. GLM-OCR → table + formula (~20s/trang)
4. Merge → markdown

## Lưu ý

- **Không OCR được PDF scan** bằng anydoc — dùng `ocr-scan` cho scan
- **Không tính formula Excel** — anydoc chỉ lấy text; dùng openpyxl nếu cần giá trị
- **Không LaTeX** — Apple Vision xuất plain text; sách toán cần Qwen legacy hoặc GLM-OCR
- **File scan mờ** → check lại ký tự Hán, số liệu vẫn tin được

## Tham khảo

- [firecrawl/anydoc](https://github.com/firecrawl/anydoc) — Rust doc→Markdown converter
- [riddleling/iOS-OCR-Server](https://github.com/riddleling/iOS-OCR-Server) — cùng engine Vision trên iPhone (không cần dùng nếu có Mac)

## License

MIT
