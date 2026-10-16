#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
pdf_ocr_pipeline.py —— 扫描版 PDF → 逐页图片 → （由 ocr_winrt.ps1 识别）→ 逐页文本

为什么需要它
------------
两本中文书都是**扫描件**：每页只有一张整页 JPEG（DCTDecode），没有文本层。
`pdf_text_extract.py` 会如实报出 0 字符 —— 这不是提取失败，而是原件本身没有文字层。
要读到内容只能 OCR。本脚本用 Pillow 把页面图片导出为 PNG，交给 Windows 内置
OCR 引擎（Windows.Media.Ocr，中文简体）识别，再把逐页文本合并成 txt/pages.json。

用法
----
    python pdf_ocr_pipeline.py <input.pdf> <workdir> [--pages 1-40] [--scale 1.0]
                               [--png/--jpg] [--keep-images] [--report-only]

流程
----
    阶段 1  python pdf_ocr_pipeline.py book.pdf work --pages 1-120
            → work/images/p0001.png ... 以及 work/pages.json（含每页图片路径）
    阶段 2  pwsh -File ocr_winrt.ps1 -ImageDir work/images -OutDir work/ocr
    阶段 3  python pdf_ocr_pipeline.py book.pdf work --assemble
            → work/<name>.txt（逐页全文） + work/<name>.report.txt（可读性判定）

说明
----
* Windows OCR 单次识别有尺寸上限，图片太大时会自动缩放；本脚本默认按原始像素导出，
  可用 --scale 调整（<1 缩小，可提速；>1 放大，对小字有帮助）。
* 若本机没有 OCR 语言包，ocr_winrt.ps1 会以退出码 3 + NO_OCR_ENGINE 报错，
  此时应如实报告"无法查看 PDF"，不要猜测内容。
"""

import argparse
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pdf_text_extract import PDFDoc, Stream, Lexer  # noqa: E402


def safe_name(path, limit=60):
    base = os.path.splitext(os.path.basename(path))[0]
    base = re.sub(r"[^\w\u4e00-\u9fff.\-]+", "_", base)
    return base[:limit] or "document"


def collect_page_images(doc, page):
    """返回该页的图片流列表 [(name, Stream)]，按绘制顺序。"""
    res = doc.page_resources(page)
    xo = doc.resolve(res.get("XObject")) or {}
    out = []
    if isinstance(xo, dict):
        for k, v in xo.items():
            o = doc.resolve(v)
            if isinstance(o, Stream) and str(o.dict.get("Subtype")) == "Image":
                out.append((str(k), o))
    return out


def render_page_image(doc, page, outdir, idx, scale=1.0, fmt="png", dpi_hint=None):
    """把页面上最大的图片导出为独立图片文件；返回 (路径, 宽, 高) 或 None。"""
    try:
        from PIL import Image
    except Exception as e:  # noqa: BLE001
        raise RuntimeError("需要 Pillow：%r" % e)
    import io

    imgs = collect_page_images(doc, page)
    if not imgs:
        return None
    # 取像素面积最大的那张（整页扫描图）
    def area(item):
        d = item[1].dict
        try:
            return int(d.get("Width") or 0) * int(d.get("Height") or 0)
        except Exception:
            return 0

    imgs.sort(key=area, reverse=True)
    _, stream = imgs[0]
    raw = stream.decoded()
    if not raw:
        return None
    try:
        im = Image.open(io.BytesIO(raw))
        im.load()
    except Exception:
        return None
    if scale and abs(scale - 1.0) > 1e-6:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)
    if im.mode not in ("L", "RGB"):
        im = im.convert("RGB")
    ext = "png" if fmt == "png" else "jpg"
    path = os.path.join(outdir, "p%04d.%s" % (idx, ext))
    if ext == "png":
        im.save(path, "PNG", optimize=False)
    else:
        im.convert("RGB").save(path, "JPEG", quality=88)
    return (path, im.width, im.height)


def parse_pages(spec, total):
    if not spec:
        return list(range(1, total + 1))
    out = []
    for part in str(spec).split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            a = int(a) if a.strip() else 1
            b = int(b) if b.strip() else total
        else:
            a = b = int(part)
        out.extend(range(max(1, a), min(total, b) + 1))
    seen, uniq = set(), []
    for p in out:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return uniq


def stage_images(pdf_path, workdir, pages_spec, scale, fmt, verbose=True):
    with open(pdf_path, "rb") as f:
        data = f.read()
    doc = PDFDoc(data)
    pages = doc.pages()
    total = len(pages)
    imgdir = os.path.join(workdir, "images")
    os.makedirs(imgdir, exist_ok=True)
    want = parse_pages(pages_spec, total)
    meta = []
    for i in want:
        try:
            r = render_page_image(doc, pages[i - 1], imgdir, i, scale=scale, fmt=fmt)
        except Exception as e:  # noqa: BLE001
            r = None
            if verbose:
                sys.stderr.write("page %d image failed: %r\n" % (i, e))
        meta.append({"page": i, "image": r[0] if r else None,
                     "w": r[1] if r else None, "h": r[2] if r else None})
    with open(os.path.join(workdir, "pages.json"), "w", encoding="utf-8") as f:
        json.dump({"file": pdf_path, "pages_total": total, "pages": meta}, f, ensure_ascii=False)
    n_ok = sum(1 for m in meta if m["image"])
    if verbose:
        print("pages_total=%d, exported=%d/%d images -> %s" % (total, n_ok, len(meta), imgdir))
    return {"imgdir": imgdir, "exported": n_ok, "total": total}


def stage_assemble(pdf_path, workdir, verbose=True):
    name = safe_name(pdf_path)
    src = os.path.join(workdir, "pages.json")
    meta = json.load(open(src, encoding="utf-8")) if os.path.exists(src) else {"pages": []}
    ocrdir = os.path.join(workdir, "ocr")
    records = []
    for m in meta.get("pages", []):
        page = m["page"]
        tf = os.path.join(ocrdir, "p%04d.txt" % page)
        text = ""
        if os.path.exists(tf):
            text = open(tf, encoding="utf-8", errors="replace").read()
        records.append({"page": page, "chars": len(text.strip()), "text": text})
    txt_path = os.path.join(workdir, name + ".txt")
    json_path = os.path.join(workdir, name + ".pages.json")
    rep_path = os.path.join(workdir, name + ".report.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write("\n\n===== PAGE %d =====\n" % r["page"])
            f.write(r["text"].strip() + "\n")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"file": pdf_path, "source": "windows-ocr", "pages": records}, f, ensure_ascii=False)
    chars = sum(r["chars"] for r in records)
    han = sum(len(re.findall(r"[\u4e00-\u9fff]", r["text"])) for r in records)
    nz = [r for r in records if r["chars"] > 0]
    avg = chars / max(1, len(records))
    verdict = "可读" if (chars > 200 and len(nz) > len(records) * 0.5) else "不可读/部分可读"
    lines = [
        "file: %s" % pdf_path,
        "method: windows-ocr (scanned pages, no text layer)",
        "pages: %d, pages_with_text: %d" % (len(records), len(nz)),
        "total_chars: %d, cjk_chars: %d, avg_chars_per_page: %.1f" % (chars, han, avg),
        "verdict: %s" % verdict,
        "outputs: %s , %s" % (txt_path, json_path),
    ]
    with open(rep_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    if verbose:
        print("\n".join(lines))
    return {"txt": txt_path, "json": json_path, "report": rep_path}


def main(argv=None):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("pdf")
    ap.add_argument("workdir")
    ap.add_argument("--pages", default="")
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--jpg", action="store_true", help="导出为 JPEG 而非 PNG")
    ap.add_argument("--assemble", action="store_true", help="合并 OCR 结果（阶段 3）")
    ap.add_argument("--report-only", action="store_true")
    a = ap.parse_args(argv)
    os.makedirs(a.workdir, exist_ok=True)
    if a.assemble:
        stage_assemble(a.pdf, a.workdir)
        return 0
    if a.report_only:
        with open(a.pdf, "rb") as f:
            data = f.read()
        doc = PDFDoc(data)
        print("pages:", len(doc.pages()))
        return 0
    stage_images(a.pdf, a.workdir, a.pages, a.scale, "jpg" if a.jpg else "png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
