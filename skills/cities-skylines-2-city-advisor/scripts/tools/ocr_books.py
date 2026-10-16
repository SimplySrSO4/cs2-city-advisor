#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ocr_books.py —— 两本扫描版图书的批量 OCR 驱动（导出图片 → Windows OCR → 规整 → 合并）

背景：`城市规划原理 第3版`.pdf 与 `城市快速公共汽车交通系统`.pdf 都是**扫描件**
（每页一张整页 JPEG，无文本层），必须 OCR 才能阅读。见 README-EXTRACTION.md。

用法（在 C:\\Users\\Devcl\\Desktop\\CSL2 下运行）
    python ocr_books.py --book brt   --work skill-extract/brt   [--pages 1-211]
    python ocr_books.py --book plan  --work skill-extract/plan  [--pages 1-305]
    python ocr_books.py --assemble-only --work skill-extract/brt

流程（每本书）
    1. 导出页面图片（Pillow，DCTDecode 原图 → JPEG，默认 0.55 缩放；实测 0.55 的
       中文识别率优于 1.0，因为 Windows OCR 对小字更稳）
    2. 调用 ocr_winrt.ps1 做识别（可 -Workers N 并行进程，按页段切分）
    3. 规整文本：去掉中日韩字符之间的多余空格、修掉常见 OCR 噪声
    4. 合并为 <name>.txt / <name>.pages.json / <name>.report.txt
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))      # scripts/tools/
SCRIPTS = os.path.dirname(HERE)                        # scripts/
for _p in (HERE, SCRIPTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import pdf_ocr_pipeline as pipe  # noqa: E402

#: 工作区根：scripts/tools/ → scripts/ → skill 目录 → 工作区
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
PS1 = os.path.join(HERE, "ocr_winrt.ps1")
PY = sys.executable

CJK = r"\u3000-\u303f\u4e00-\u9fff\uff00-\uffef"


def find_books(root=None):
    """在工作区里找那两本已知的书。**会同时搜索工作区根与 `参考资料/`**（PDF 位置变动过）。"""
    root = root or ROOT
    out = {}
    for d in (root, os.path.join(root, "参考资料")):
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if not f.lower().endswith(".pdf"):
                continue
            p = os.path.join(d, f)
            if "快速公共汽车" in f and "brt" not in out:
                out["brt"] = p
            elif "城市规划原理" in f and "第3版" in f and "plan" not in out:
                out["plan"] = p
    return out


# ----------------------------------------------------------------------------- 文本规整
NOISE_FIXES = [
    (r"[ \t]+", " "),
]


def normalize_ocr(text):
    """规整 Windows OCR 的中文输出。"""
    if not text:
        return ""
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    for raw_line in t.split("\n"):
        line = raw_line.strip()
        if not line:
            lines.append("")
            continue
        # 去掉中日韩字符之间的空格（Windows OCR 会把每个汉字当成一个词）
        line = re.sub(r"(?<=[%s])\s+(?=[%s])" % (CJK, CJK), "", line)
        # 汉字与拉丁/数字之间保留一个空格，但去掉多余
        line = re.sub(r"(?<=[%s])\s+(?=[0-9A-Za-z(])" % CJK, " ", line)
        line = re.sub(r"(?<=[0-9A-Za-z)])\s+(?=[%s])" % CJK, " ", line)
        line = re.sub(r"\s{2,}", " ", line)
        lines.append(line.strip())
    t = "\n".join(lines)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


# ----------------------------------------------------------------------------- 阶段
def export_images(pdf, work, pages_spec, scale, jpg=True):
    imgdir = os.path.join(work, "images")
    os.makedirs(imgdir, exist_ok=True)
    from pdf_text_extract import PDFDoc
    with open(pdf, "rb") as f:
        data = f.read()
    doc = PDFDoc(data)
    pages = doc.pages()
    total = len(pages)
    want = pipe.parse_pages(pages_spec, total)
    t0 = time.time()
    meta = []
    for n, i in enumerate(want, 1):
        dest_png = os.path.join(imgdir, "p%04d.png" % i)
        dest_jpg = os.path.join(imgdir, "p%04d.jpg" % i)
        if os.path.exists(dest_png) or os.path.exists(dest_jpg):
            meta.append({"page": i, "image": dest_png if os.path.exists(dest_png) else dest_jpg})
            continue
        try:
            r = pipe.render_page_image(doc, pages[i - 1], imgdir, i, scale=scale, fmt="jpg" if jpg else "png")
        except Exception as e:  # noqa: BLE001
            sys.stderr.write("page %d export failed: %r\n" % (i, e))
            r = None
        meta.append({"page": i, "image": r[0] if r else None, "w": r[1] if r else None, "h": r[2] if r else None})
        if n % 25 == 0:
            print("  exported %d/%d (%.1fs)" % (n, len(want), time.time() - t0), flush=True)
    with open(os.path.join(work, "pages.json"), "w", encoding="utf-8") as f:
        json.dump({"file": pdf, "pages_total": total, "pages": meta}, f, ensure_ascii=False)
    print("export done: %d images in %.1fs -> %s" % (len(meta), time.time() - t0, imgdir), flush=True)


def run_ocr(work, lang, workers=1):
    imgdir = os.path.join(work, "images")
    ocrdir = os.path.join(work, "ocr")
    os.makedirs(ocrdir, exist_ok=True)
    images = sorted(f for f in os.listdir(imgdir) if f.lower().endswith((".jpg", ".png")))
    if not images:
        print("no images to OCR")
        return
    if workers <= 1:
        cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", PS1,
               "-ImageDir", imgdir, "-OutDir", ocrdir, "-Lang", lang]
        print("ocr: one process, %d images" % len(images), flush=True)
        subprocess.run(cmd, check=False)
        return
    # 并行：按文件名排序后均分成 workers 段，每段用临时目录 + 前缀过滤
    chunks = [[] for _ in range(workers)]
    for i, name in enumerate(images):
        chunks[i % workers].append(name)
    procs = []
    for w, chunk in enumerate(chunks):
        sub = os.path.join(work, "images_w%d" % w)
        os.makedirs(sub, exist_ok=True)
        for name in chunk:
            dst = os.path.join(sub, name)
            if not os.path.exists(dst):
                try:
                    os.link(os.path.join(imgdir, name), dst)
                except Exception:
                    import shutil
                    shutil.copy2(os.path.join(imgdir, name), dst)
        cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", PS1,
               "-ImageDir", sub, "-OutDir", ocrdir, "-Lang", lang]
        print("ocr worker %d: %d images" % (w, len(chunk)), flush=True)
        procs.append(subprocess.Popen(cmd))
    for p in procs:
        p.wait()


def assemble(work, pdf, name):
    src = os.path.join(work, "pages.json")
    meta = json.load(open(src, encoding="utf-8")) if os.path.exists(src) else {"pages": []}
    ocrdir = os.path.join(work, "ocr")
    records = []
    for m in meta.get("pages", []):
        page = m["page"]
        raw = ""
        for cand in ("p%04d.txt" % page, "p%04d.txt" % page):
            tf = os.path.join(ocrdir, cand)
            if os.path.exists(tf):
                raw = open(tf, encoding="utf-8", errors="replace").read()
                break
        text = normalize_ocr(raw)
        records.append({"page": page, "raw_chars": len(raw.strip()), "chars": len(text), "text": text})
    txt = os.path.join(work, name + ".txt")
    js = os.path.join(work, name + ".pages.json")
    rep = os.path.join(work, name + ".report.txt")
    with open(txt, "w", encoding="utf-8") as f:
        for r in records:
            f.write("\n\n===== PAGE %d =====\n" % r["page"])
            f.write(r["text"] + "\n")
    with open(js, "w", encoding="utf-8") as f:
        json.dump({"file": pdf, "method": "windows-ocr + normalize", "pages": records}, f, ensure_ascii=False)
    chars = sum(r["chars"] for r in records)
    han = sum(len(re.findall(r"[\u4e00-\u9fff]", r["text"])) for r in records)
    nz = [r for r in records if r["chars"] > 0]
    low = [r["page"] for r in records if 0 < r["chars"] < 80]
    empty = [r["page"] for r in records if r["chars"] == 0]
    lines = [
        "file: %s" % pdf,
        "method: 扫描件 → Pillow 导出图片 → Windows.Media.Ocr(zh-Hans-CN) → 规整",
        "pages: %d, pages_with_text: %d" % (len(records), len(nz)),
        "total_chars: %d, cjk_chars: %d, avg_chars_per_page: %.1f" % (chars, han, chars / max(1, len(records))),
        "empty_pages(first 40): %s" % empty[:40],
        "low_text_pages(first 40): %s" % low[:40],
        "verdict: %s" % ("可读" if chars > 2000 and len(nz) > len(records) * 0.6 else "部分可读/不可读"),
        "outputs: %s , %s" % (txt, js),
    ]
    with open(rep, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines), flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", choices=["brt", "plan"])
    ap.add_argument("--work", required=True)
    ap.add_argument("--pages", default="")
    ap.add_argument("--scale", type=float, default=0.55)
    ap.add_argument("--lang", default="zh-Hans-CN")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--stage", default="all", choices=["all", "export", "ocr", "assemble"])
    ap.add_argument("--name", default="")
    a = ap.parse_args(argv)

    work = os.path.abspath(a.work)
    os.makedirs(work, exist_ok=True)
    books = find_books()
    pdf = books.get(a.book or "", "")
    if a.stage in ("all", "export") and not pdf:
        print("cannot locate PDF for book=%s; found=%s" % (a.book, books))
        return 2
    name = a.name or (os.path.splitext(os.path.basename(pdf))[0][:60] if pdf else os.path.basename(work))

    if a.stage in ("all", "export"):
        print("== export images (%s) scale=%.2f" % (os.path.basename(pdf), a.scale), flush=True)
        export_images(pdf, work, a.pages, a.scale)
    if a.stage in ("all", "ocr"):
        print("== ocr", flush=True)
        run_ocr(work, a.lang, a.workers)
    if a.stage in ("all", "assemble"):
        print("== assemble", flush=True)
        meta_file = os.path.join(work, "pages.json")
        if not pdf and os.path.exists(meta_file):
            pdf = json.load(open(meta_file, encoding="utf-8")).get("file", "")
        assemble(work, pdf, name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
