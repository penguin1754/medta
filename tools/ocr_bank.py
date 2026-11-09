# -*- coding: utf-8 -*-
"""题库 PDF -> 逐页 OCR 文本（可断点续跑）。

用法：python tools/ocr_bank.py <pdf> [--dpi 200]
产物：knowledge/_ocr/pages.jsonl  每行 {"page": n, "lines": [...]}
"""
import json
import os
import sys
import time
from pathlib import Path

import pymupdf
from rapidocr_onnxruntime import RapidOCR

OUT_DIR = Path(__file__).resolve().parent.parent / "knowledge" / "_ocr"

def main():
    # 中文路径经 Start-Process 传参会被转成 GBK，改用环境变量传更稳
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        pdf = Path(sys.argv[1])
    else:
        pdf = Path(os.environ["MEDTA_BANK_PDF"])
    dpi = 200
    if "--dpi" in sys.argv:
        dpi = int(sys.argv[sys.argv.index("--dpi") + 1])
    out_name = "pages.jsonl"
    if "--out" in sys.argv:
        out_name = sys.argv[sys.argv.index("--out") + 1]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT = OUT_DIR / out_name

    done = set()
    if OUT.exists():
        for line in OUT.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                done.add(json.loads(line)["page"])
            except Exception:
                pass
    print("already done: %d pages" % len(done), flush=True)

    doc = pymupdf.open(pdf)
    total = doc.page_count
    ocr = RapidOCR()
    t_all = time.time()
    with OUT.open("a", encoding="utf-8") as f:
        for i in range(total):
            pno = i + 1
            if pno in done:
                continue
            t0 = time.time()
            img = doc[i].get_pixmap(dpi=dpi).tobytes("png")
            res, _ = ocr(img)
            lines = [str(item[1]) for item in (res or [])]
            f.write(json.dumps({"page": pno, "lines": lines}, ensure_ascii=False) + "\n")
            f.flush()
            print("page %d/%d  lines=%d  %.1fs" % (pno, total, len(lines), time.time() - t0), flush=True)
    print("done in %.1fs" % (time.time() - t_all), flush=True)

if __name__ == "__main__":
    main()
