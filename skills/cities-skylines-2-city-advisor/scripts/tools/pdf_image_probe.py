#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
pdf_image_probe.py —— 探查 PDF 页面里的图片流能不能被解码（用于判断"扫描件能否 OCR"）

背景
----
新版扫描 PDF 常用 **JBIG2Decode**（图像编码）而非 DCTDecode。Pillow **不支持 JBIG2**，
所以 python 侧无法直接解码，需要用系统/其他工具。本脚本负责：
  1. 取出页面的图片 XObject 原始字节；
  2. 按 Filter 判断能否解码（DCTDecode/JPXDecode → Pillow 可读；JBIG2Decode → 需外部解码器）；
  3. 把原始流导出到磁盘（`.jbig2` / `.jpg`），方便交给别的工具或人工检查。

用法:
    python pdf_image_probe.py <pdf> <outdir> [--pages 1-3]
"""

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pdf_text_extract import PDFDoc, Stream  # noqa: E402

#: Pillow 能直接打开的 Filter
PIL_OK = {"DCTDecode", "DCT", "JPXDecode", "CCITTFaxDecode", "CCF"}
NEEDS_HELP = {"JBIG2Decode"}


def page_images(doc, page):
    res = doc.page_resources(page)
    xo = doc.resolve(res.get("XObject")) or {}
    out = []
    if isinstance(xo, dict):
        for k, v in xo.items():
            o = doc.resolve(v)
            if isinstance(o, Stream) and str(o.dict.get("Subtype")) == "Image":
                out.append((str(k), o))
    return out


def probe(pdf, outdir, pages_spec=None):
    with open(pdf, "rb") as f:
        data = f.read()
    doc = PDFDoc(data)
    pages = doc.pages()
    total = len(pages)
    os.makedirs(outdir, exist_ok=True)
    want = []
    if pages_spec:
        for part in str(pages_spec).split(","):
            if "-" in part:
                a, b = part.split("-")
                want.extend(range(int(a), min(int(b), total) + 1))
            elif part.strip():
                want.append(int(part))
    else:
        want = list(range(1, min(total, 3) + 1))

    report = []
    for i in want:
        imgs = page_images(doc, pages[i - 1])
        if not imgs:
            report.append((i, "无图片对象", None, 0, None))
            continue
        name, st = imgs[0]
        filt = st.dict.get("Filter")
        raw = st.raw if isinstance(st.raw, bytes) else b""
        w, h = st.dict.get("Width"), st.dict.get("Height")
        status = "可解码(Pillow)" if str(filt) in PIL_OK else (
            "需外部解码器(JBIG2)" if str(filt) in NEEDS_HELP else "未知")
        ext = ".jbig2" if "JBIG2" in str(filt) else ".jpg"
        outp = os.path.join(outdir, "p%04d%s" % (i, ext))
        try:
            with open(outp, "wb") as f:
                f.write(raw)
        except Exception:
            outp = None
        report.append((i, status, filt, len(raw), (w, h), outp))
    return {"total": total, "report": report}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("outdir")
    ap.add_argument("--pages", default=None)
    a = ap.parse_args(argv)
    r = probe(a.pdf, a.outdir, a.pages)
    print("pages_total:", r["total"])
    for row in r["report"]:
        print("  page %s | %s | filter=%s | raw=%s B | size=%s | %s" %
              (row[0], row[1], row[2], row[3], row[4] if len(row) > 4 else None,
               row[5] if len(row) > 5 else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
