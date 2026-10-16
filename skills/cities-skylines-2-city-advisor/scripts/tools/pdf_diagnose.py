#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""pdf_diagnose.py —— 诊断 PDF 是"扫描件（无文本层）"还是"提取器能力不足"。

用法: python pdf_diagnose.py <input.pdf> [--pages N]
输出: 每页 页面对象键 / Resources 里的 XObject 与 Font / 内容流字节数与操作符直方图。
"""
import os
import re
import sys
import zlib
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pdf_text_extract import PDFDoc, Stream  # noqa: E402


def describe_filters(s):
    f = s.dict.get("Filter")
    return f


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    path = argv[1]
    n = 5
    if "--pages" in argv:
        n = int(argv[argv.index("--pages") + 1])
    with open(path, "rb") as f:
        data = f.read()
    doc = PDFDoc(data)
    pages = doc.pages()
    print("pages_total:", len(pages))
    print("catalog keys:", sorted(doc.catalog().keys()))
    print("trailer keys:", sorted(doc.trailer.keys()))
    tally = Counter()
    for i, page in enumerate(pages[:n], 1):
        res = doc.page_resources(page)
        xo = doc.resolve(res.get("XObject")) or {}
        fonts = doc.resolve(res.get("Font")) or {}
        contents = doc.resolve(page.get("Contents"))
        raw_len = 0
        dec_len = 0
        filters = []
        if isinstance(contents, Stream):
            raw_len = len(contents.raw)
            dec_len = len(contents.decoded())
            filters = describe_filters(contents)
        elif isinstance(contents, list):
            for c in contents:
                c = doc.resolve(c)
                if isinstance(c, Stream):
                    raw_len += len(c.raw)
                    dec_len += len(c.decoded())
                    filters.append(describe_filters(c))
        stream = doc.page_stream_data(page)
        ops = Counter(re.findall(rb"(?<![A-Za-z0-9])(Tj|TJ|Tm|Td|TD|Tf|BT|ET|Do|re|cm|Tz|Tc|Tw|T\*)(?![A-Za-z0-9])", stream))
        img = []
        if isinstance(xo, dict):
            for k, v in xo.items():
                o = doc.resolve(v)
                if isinstance(o, Stream):
                    d = o.dict
                    img.append((str(k), str(d.get("Subtype")), str(d.get("Width")), str(d.get("Height")), str(describe_filters(o))))
        print("--- page %d" % i)
        print("   page keys:", sorted(page.keys()))
        print("   contents bytes raw=%d decoded=%d filters=%s" % (raw_len, dec_len, filters))
        print("   stream head:", stream[:80])
        print("   ops:", dict(ops))
        print("   fonts(%d):" % len(fonts), list(fonts.keys())[:8])
        print("   xobjects(%d):" % len(img), img[:6])
        tally.update(ops)
    print("=== tally over first %d pages: %s" % (min(n, len(pages)), dict(tally)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
