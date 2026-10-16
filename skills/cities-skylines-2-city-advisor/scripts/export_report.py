# -*- coding: utf-8 -*-
"""export_report.py —— 把 Markdown 诊断稿落成**合规的 DOCX 报告 + XLSX 数据附录**。

规范：`references/110-deliverable-format.md`（normative）
实现：`scripts/core/deliverable_style.py`（唯一格式来源）
**本文件不含任何字号/颜色/缩进的字面量** —— 全部从 deliverable_style 取。

用法
----
落交付物（默认）::

    python -X utf8 scripts/export_report.py \
        --md city_report.md --json city_metrics.json --maps maps/ \
        --city "江东" --outdir .

只出一份 Markdown（**仅当玩家明确要求 markdown 时**）::

    python -X utf8 scripts/export_report.py --md city_report.md --md-only

格式合规校验（交付前必跑）::

    python -X utf8 scripts/export_report.py --check "江东规划报告.docx" "江东规划数据附录.xlsx"

退出码：0 成功 / 1 参数或读取错误 / 2 校验未通过。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata

_SCRIPTS = os.path.dirname(os.path.abspath(__file__))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from core import deliverable_style as S        # noqa: E402

TWIP_PER_PT = 20


# ====================================================================== 解析
class Block(dict):
    """`{"type": ..., ...}` —— 故意用 dict，便于 json 落盘与调试。"""


def parse_markdown(text):
    """把 city_report.py 产出的 Markdown 解析成块序列。

    只支持该脚本实际会产出的子集：`#/##/###/####` 标题、GFM 表格、
    `- ` 项目符号（含 2 空格缩进嵌套）、`1. ` 有序、`> ` 引用、`![alt](path)` 图片、
    以及普通段落。行内支持 `**粗体**` 与 `` `代码` ``（由 deliverable_style 解析）。
    """
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blocks, i, n = [], 0, len(lines)

    def flush_para(buf):
        if buf:
            blocks.append(Block(type="p", text=" ".join(x.strip() for x in buf)))
            buf.clear()

    para = []
    while i < n:
        raw = lines[i]
        line = raw.rstrip()
        stripped = line.strip()

        if not stripped:
            flush_para(para)
            i += 1
            continue

        # 图片：![alt](path)
        m = re.match(r"^!\[(?P<alt>[^\]]*)\]\((?P<path>[^)]+)\)\s*$", stripped)
        if m:
            flush_para(para)
            blocks.append(Block(type="image", alt=m.group("alt").strip(),
                                path=m.group("path").strip()))
            i += 1
            continue

        # 标题
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            flush_para(para)
            blocks.append(Block(type="h%d" % min(len(m.group(1)), 4),
                                text=m.group(2).strip()))
            i += 1
            continue

        # 表格：当前行以 | 开头，且下一行是分隔行
        if stripped.startswith("|") and i + 1 < n and re.match(
                r"^\|[\s:|-]+\|\s*$", lines[i + 1].strip()):
            flush_para(para)
            header = _split_row(stripped)
            body, j = [], i + 2
            while j < n and lines[j].strip().startswith("|"):
                body.append(_split_row(lines[j].strip()))
                j += 1
            width = len(header)
            body = [(r + [""] * width)[:width] for r in body]
            blocks.append(Block(type="table", header=header, rows=body))
            i = j
            continue

        # 引用（连续行各自成段 —— 源稿每条 `A("> …")` 都是独立提示）
        if stripped.startswith(">"):
            flush_para(para)
            blocks.append(Block(type="quote", text=stripped.lstrip(">").strip()))
            i += 1
            continue

        # 分隔线
        if re.match(r"^(-{3,}|\*{3,}|_{3,})$", stripped):
            flush_para(para)
            i += 1
            continue

        # 列表
        m = re.match(r"^(\s*)([-*+]|\d+\.)\s+(.*)$", line)
        if m:
            flush_para(para)
            indent = len(m.group(1).replace("\t", "  "))
            ordered = bool(re.match(r"^\d+\.$", m.group(2)))
            txt = m.group(3).strip()
            # 续行（缩进更深的非列表行）并入本条
            j = i + 1
            while j < n and lines[j].strip() and not re.match(
                    r"^\s*([-*+]|\d+\.)\s+", lines[j]) and not lines[j].strip().startswith(
                    ("|", ">", "#")):
                if len(lines[j]) - len(lines[j].lstrip()) > indent:
                    txt += " " + lines[j].strip()
                    j += 1
                else:
                    break
            blocks.append(Block(type="num" if ordered else "bullet",
                                level=2 if indent >= 2 else 1, text=txt))
            i = j
            continue

        para.append(line)
        i += 1

    flush_para(para)
    return blocks


def _split_row(line):
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def _short_title(s, limit=16):
    """把 `7. 就业中心（400 m 网格聚合，前 12）` 压成 `就业中心` —— 用于工作表名。"""
    s = re.sub(r"^\s*\d+(\.\d+)?[.、]?\s*", "", s or "").strip()
    for sep in ("——", "（", "(", "：", ":", "｜", "|"):
        if sep in s:
            s = s.split(sep)[0]
    return s.strip()[:limit] or "数据表"


def _plain(s):
    """去掉行内标记，用于目录 / 工作表名。"""
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"`([^`]+)`", r"\1", s)
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    return s.strip()


def _guess_widths(header, rows, max_cm):
    """按各列最长内容估算列宽，并夹到版心宽以内（110 §5）。"""
    ncol = len(header)
    if ncol == 0:
        return []
    def visual(s):
        return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in str(s))
    w = []
    for c in range(ncol):
        vals = [visual(header[c])] + [visual(r[c]) for r in rows[:200]]
        vals.sort()
        # 取 P85，避免单个超长单元格把整列撑爆
        w.append(max(4.0, vals[int(len(vals) * 0.85)] if vals else 4.0))
    tot = sum(w)
    scale = max_cm / tot if tot > max_cm else 1.0
    fallback = max_cm / ncol
    out = [max(1.6, x * scale) for x in w]
    if sum(out) > max_cm:                       # 夹一次，保证不溢出
        out = [fallback] * ncol
    return out


# ====================================================================== DOCX
def build_docx(blocks, docx_path, city, report_name, with_toc=True):
    from docx import Document

    doc = Document()
    S.apply_page_and_styles(doc)

    title = None
    for b in blocks:
        if b["type"] == "h1":
            title = _plain(b["text"])
            break
    cover_title = ("%s城市诊断与规划报告" % city) if city else (title or "城市诊断报告")

    # ---- 封面（110 §4）----
    for _ in range(4):
        S.add_para(doc, "cover_info", "")
    S.add_para(doc, "cover_title", cover_title)
    S.add_para(doc, "cover_sub", "——基于 Carto GIS 导出的定量诊断与规划建议")
    if title and title != cover_title:
        S.add_para(doc, "cover_info", title)
    S.add_para(doc, "cover_info", "数据源：Cities: Skylines II · Carto Mod 导出（GeoJSON / Shapefile + GeoTIFF）")
    S.add_para(doc, "cover_info", "生成方式：由 Carto 导出数据实算后落文档（不是人工估计）")
    S.add_para(doc, "cover_note", "本报告全部数值由脚本实算，不是估计值；请先读正文第 0 节的数据自检。")
    S.page_break(doc)

    # ---- 目录 ----
    if with_toc:
        heads = [_plain(b["text"]) for b in blocks if b["type"] == "h2"]
        if heads:
            S.add_toc_placeholder(doc, heads)
            S.page_break(doc)

    # ---- 正文 ----
    skipped_title = False
    n_img_ok = n_img_bad = 0
    for b in blocks:
        t = b["type"]
        if t == "h1" and not skipped_title:
            skipped_title = True          # 已在封面用过
            continue
        if t in ("h1", "h2", "h3", "h4"):
            S.add_para(doc, {"h1": "h1", "h2": "h2", "h3": "h3", "h4": "h3"}[t], b["text"])
        elif t == "p":
            S.add_para(doc, "body", b["text"])
        elif t == "quote":
            S.add_para(doc, "quote", b["text"])
        elif t == "bullet":
            S.add_para(doc, "bullet1" if b.get("level", 1) == 1 else "bullet2", "• " + b["text"])
        elif t == "num":
            S.add_para(doc, "bullet1" if b.get("level", 1) == 1 else "bullet2", b["text"])
        elif t == "image":
            if S.add_figure(doc, b["path"], b["alt"] or os.path.basename(b["path"])):
                n_img_ok += 1
            else:
                n_img_bad += 1
        elif t == "table":
            widths = _guess_widths(b["header"], b["rows"], S.TABLE["max_width_cm"])
            S.add_table(doc, b["header"], b["rows"], widths)

    S.add_footer(doc.sections[0], report_name)
    doc.save(docx_path)
    return dict(images_ok=n_img_ok, images_missing=n_img_bad)


# ====================================================================== XLSX
def _flatten_kpi(obj, prefix=""):
    """把 JSON 指标摊平成 (指标, 数值, 单位/说明) 行。"""
    rows = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.startswith("_") or k == "maps":
                continue
            name = ("%s.%s" % (prefix, k)) if prefix else str(k)
            if isinstance(v, (dict, list)):
                rows.extend(_flatten_kpi(v, name))
            else:
                rows.append((name, v, ""))
    elif isinstance(obj, list):
        for idx, v in enumerate(obj):
            name = "%s[%d]" % (prefix, idx)
            if isinstance(v, (dict, list)):
                rows.extend(_flatten_kpi(v, name))
            else:
                rows.append((name, v, ""))
    return rows


def build_xlsx(blocks, xlsx_path, city, metrics=None):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    x = S.XLSX
    thin = Side(style="thin", color=S.C_TBL_BORDER)
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    hdr_font = Font(name=S.CN_FONT, size=x["header_pt"], bold=True, color=x["header_color"])
    hdr_fill = PatternFill("solid", fgColor=x["header_fill"])
    title_font = Font(name=S.CN_FONT, size=x["title_pt"], bold=True, color=x["title_color"])
    note_font = Font(name=S.CN_FONT, size=x["note_pt"], italic=True, color=x["note_color"])
    body_font = Font(name=S.CN_FONT, size=x["body_pt"])

    wb = Workbook()
    wb.remove(wb.active)
    used = set()

    def make_sheet(name, title, headers, rows, note=None):
        ws = wb.create_sheet(S.safe_sheet_name(name, used))
        ws["A1"] = title
        ws["A1"].font = title_font
        r0 = 3
        if note:
            ws["A2"] = note
            ws["A2"].font = note_font
            r0 = 4
        for j, h in enumerate(headers, 1):
            c = ws.cell(row=r0, column=j, value=_cell(h))
            c.font = hdr_font
            c.fill = hdr_fill
            c.border = border
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        for i, row in enumerate(rows, r0 + 1):
            for j in range(len(headers)):
                v = _cell(row[j]) if j < len(row) else x["empty_marker"]
                c = ws.cell(row=i, column=j + 1, value=v)
                c.border = border
                c.font = body_font
                c.alignment = Alignment(horizontal="right" if isinstance(v, (int, float))
                                        else "left")
        # 列宽（110 §8：不使用默认宽度）
        for j in range(1, len(headers) + 1):
            widest = 0
            for i in range(r0, ws.max_row + 1):
                v = ws.cell(row=i, column=j).value
                s = "" if v is None else str(v)
                widest = max(widest, sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1
                                         for ch in s))
            ws.column_dimensions[get_column_letter(j)].width = min(46, max(9, widest + 3))
        if x["freeze"]:
            ws.freeze_panes = ws.cell(row=r0 + 1, column=1)
        return ws

    def _cell(v):
        if v is None or v == "":
            return x["empty_marker"]
        if isinstance(v, str):
            s = _plain(v)
            s = s.replace(",", "")
            if re.match(r"^-?\d+$", s):
                return int(s)
            if re.match(r"^-?\d+\.\d+$", s):
                return float(s)
            return s or x["empty_marker"]
        return v

    # ---- 1-概览 ----
    if metrics:
        rows = [(k, v, u) for k, v, u in _flatten_kpi(metrics)][:400]
        if rows:
            make_sheet("1-概览", "%s · 关键指标概览" % (city or "城市"),
                       ["指标", "数值", "说明"], rows,
                       note="由 city_report.py 的 --json 输出摊平；空值以 %s 表示。" % x["empty_marker"])

    # ---- 报告里每张数据表 → 一张工作表 ----
    cur_head, idx = None, 0
    for b in blocks:
        if b["type"] == "h2":
            cur_head = _short_title(_plain(b["text"]))
        elif b["type"] == "table":
            idx += 1
            nm = cur_head or "数据表"
            title = "%s（表 %d）" % (nm, idx)
            make_sheet("%d-%s" % (idx + (1 if metrics else 0), nm[:24]), title,
                       b["header"], b["rows"],
                       note="来源：Carto 导出实算；节次 %s。" % (cur_head or "—"))

    if not wb.sheetnames:                       # 兜底：至少给一张表
        make_sheet("1-概览", "%s · 数据附录" % (city or "城市"), ["说明"], [["报告未含数据表"]])
    wb.save(xlsx_path)
    return wb.sheetnames


# ====================================================================== 校验
def verify(docx_path=None, xlsx_path=None):
    """逐项比对本文件对应的规范（110 §10）。返回 (ok, [(项, 是否通过, 详情)])。"""
    checks = []

    def ck(item, ok, detail=""):
        checks.append((item, bool(ok), str(detail)))
        return ok

    if docx_path:
        from docx import Document
        from docx.oxml.ns import qn
        from docx.shared import Cm
        doc = Document(docx_path)
        sec = doc.sections[0]

        ck("页面 A4", abs(sec.page_width.cm - S.PAGE["page_w_cm"]) < 0.02
           and abs(sec.page_height.cm - S.PAGE["page_h_cm"]) < 0.02,
           "%.1f×%.1f cm" % (sec.page_width.cm, sec.page_height.cm))
        ck("页边距 上下左右 = 22/20/24/24 mm",
           abs(sec.top_margin.cm - S.PAGE["top_cm"]) < 0.02
           and abs(sec.bottom_margin.cm - S.PAGE["bottom_cm"]) < 0.02
           and abs(sec.left_margin.cm - S.PAGE["side_cm"]) < 0.02,
           "%.1f/%.1f/%.1f" % (sec.top_margin.cm, sec.bottom_margin.cm, sec.left_margin.cm))

        normal = doc.styles["Normal"]
        rf = normal.element.get_or_add_rPr().find(qn("w:rFonts"))
        ck("基准样式 中文 eastAsia = 微软雅黑",
           rf is not None and rf.get(qn("w:eastAsia")) == S.CN_FONT,
           rf.get(qn("w:eastAsia")) if rf is not None else "缺失")
        ck("基准样式 正文字号 10.5 pt",
           abs(normal.font.size.pt - S.SPEC["body"]["size"]) < 0.01,
           "%s pt" % (normal.font.size.pt if normal.font.size else "—"))

        want = {"Heading 1": S.SPEC["h1"], "Heading 2": S.SPEC["h2"], "Heading 3": S.SPEC["h3"]}
        bad = []
        for name, sp in want.items():
            st = doc.styles[name]
            if abs(st.font.size.pt - sp["size"]) > 0.01:
                bad.append("%s %s≠%s" % (name, st.font.size.pt, sp["size"]))
        ck("标题字号 17 / 13.5 / 11.5 pt", not bad, "; ".join(bad) or "OK")

        # 行内字体：每个 run 都必须带 eastAsia
        miss = 0
        total = 0
        for p in _iter_paragraphs(doc):
            for r in p.runs:
                total += 1
                e = r._element.find(qn("w:rPr"))
                f = e.find(qn("w:rFonts")) if e is not None else None
                if f is None or not f.get(qn("w:eastAsia")):
                    miss += 1
        ck("每个 run 都设了 w:eastAsia", miss == 0, "缺 %d / 共 %d 个 run" % (miss, total))

        # 缩进：正文首行 420 twip（21 pt），列表项悬挂 −240 twip（12 pt）
        bad_ind = []
        for p in doc.paragraphs:
            pPr = p._p.find(qn("w:pPr"))
            if pPr is None:
                continue
            ind = pPr.find(qn("w:ind"))
            if ind is None:
                continue
            fl, hg = ind.get(qn("w:firstLine")), ind.get(qn("w:hanging"))
            if fl is not None and int(fl) != 420:
                bad_ind.append("firstLine=%s" % fl)
            if hg is not None and int(hg) != 240:
                bad_ind.append("hanging=%s" % hg)
        ck("缩进 正文首行 420 twip / 列表悬挂 240 twip",
           not bad_ind, "异常值 %s" % (sorted(set(bad_ind)) if bad_ind else "无"))

        # 表格
        tb_bad = []
        for ti, t in enumerate(doc.tables):
            width = sum((c.width.cm if c.width else 0) for c in t.rows[0].cells)
            if width > S.TABLE["max_width_cm"] + 0.05:
                tb_bad.append("表%d 宽 %.1f cm" % (ti + 1, width))
            shd = t.rows[0].cells[0]._tc.get_or_add_tcPr().find(qn("w:shd"))
            if shd is None or shd.get(qn("w:fill")) != S.TABLE["header_fill"]:
                tb_bad.append("表%d 表头底纹" % (ti + 1))
            for r in t.rows[1:]:
                trPr = r._tr.find(qn("w:trPr"))
                if trPr is None or trPr.find(qn("w:cantSplit")) is None:
                    tb_bad.append("表%d 有行未禁止跨页" % (ti + 1))
                    break
        ck("表格 列宽≤16.2cm / 表头底纹 / 行不跨页", not tb_bad,
           "; ".join(tb_bad[:4]) or "共 %d 张表" % len(doc.tables))

        # 图宽度
        img_bad = []
        for shp in doc.inline_shapes:
            wcm = shp.width.cm
            if wcm > S.IMG_MAX_W_CM + 0.02:
                img_bad.append("%.1fcm" % wcm)
        ck("图片宽度 ≤ 16.2 cm", not img_bad, "超宽 %s" % (img_bad or "无"))

        # 页脚页码域
        ftr_xml = doc.sections[0].footer.paragraphs[0]._p.xml
        ck("页脚含 PAGE 域", "PAGE" in ftr_xml, "")

        # Markdown 残留：`**粗体**` / 反引号 必须已被解析掉（表格单元格最容易漏）
        residue = []
        for p in _iter_paragraphs(doc):
            if "**" in p.text or "`" in p.text:
                residue.append(p.text[:34])
        ck("无残留 Markdown 标记（** / `）", not residue,
           ("例：%s" % residue[0]) if residue else "干净")

    if xlsx_path:
        from openpyxl import load_workbook
        wb = load_workbook(xlsx_path)
        x = S.XLSX
        ck("工作表数 ≥1", len(wb.sheetnames) >= 1, ", ".join(wb.sheetnames[:6]))
        ck("工作表名 ≤31 字符且无非法字符",
           all(len(n) <= x["max_sheet_len"] and not any(c in n for c in x["sheet_bad_chars"])
               for n in wb.sheetnames), "")
        fills, fonts, freeze, numeric = [], [], [], 0
        for n in wb.sheetnames:
            ws = wb[n]
            hdr_row = 3
            for r in range(1, 6):
                c = ws.cell(row=r, column=1)
                if c.fill and c.fill.fgColor and c.fill.fgColor.rgb == "00" + x["header_fill"]:
                    hdr_row = r
                    break
            cells = [ws.cell(row=hdr_row, column=j) for j in range(1, min(ws.max_column, 8) + 1)]
            fills.append(all(c.fill and c.fill.fgColor and
                             str(c.fill.fgColor.rgb).endswith(x["header_fill"]) for c in cells))
            fonts.append(all(c.font and c.font.bold and _pt(c.font.size) is not None
                             and abs(_pt(c.font.size) - x["header_pt"]) < 0.01 for c in cells))
            freeze.append(ws.freeze_panes is not None)
            for row in ws.iter_rows(min_row=hdr_row + 1):
                numeric += sum(1 for c in row if isinstance(c.value, (int, float)))
        ck("每张表 表头底纹 #1B4B8C + 加粗 10.5pt", all(fills) and all(fonts),
           "底纹 %s / 字体 %s" % (all(fills), all(fonts)))
        ck("每张表 冻结表头行", all(freeze), "%d/%d" % (sum(freeze), len(freeze)))
        ck("数值为数字型（非字符串）", numeric > 0, "数字单元格 %d 个" % numeric)

    ok = all(c[1] for c in checks)
    return ok, checks


def _pt(size):
    """openpyxl 读回的字号有时是 float、有时是 Length(EMU) —— 统一成 pt。"""
    if size is None:
        return None
    return float(getattr(size, "pt", size))


def _iter_paragraphs(doc):
    for p in doc.paragraphs:
        yield p
    for t in doc.tables:
        for r in t.rows:
            for c in r.cells:
                for p in c.paragraphs:
                    yield p


# ====================================================================== CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description="Markdown 诊断稿 → 合规 DOCX + XLSX")
    ap.add_argument("--md", help="city_report.py 产出的 Markdown 报告")
    ap.add_argument("--json", dest="json_path", default=None, help="--json 输出的指标文件")
    ap.add_argument("--maps", default=None, help="配图目录（用于把图相对路径补成绝对路径）")
    ap.add_argument("--city", default=None, help="城市名（存档名），用于文件名与封面")
    ap.add_argument("--name", default=None, help="报告名（默认 <城市名>规划报告）")
    ap.add_argument("--outdir", default=".", help="输出目录")
    ap.add_argument("--toc", dest="toc", action="store_true", default=True)
    ap.add_argument("--no-toc", dest="toc", action="store_false")
    ap.add_argument("--md-only", action="store_true",
                    help="**仅当玩家明确要求 markdown 时使用**：只交付 .md，不产出 docx/xlsx")
    ap.add_argument("--check", nargs="+", metavar="FILE",
                    help="校验已生成的 docx/xlsx 是否符合 110 规范")
    a = ap.parse_args(argv)

    if a.check:
        docx = next((f for f in a.check if f.lower().endswith(".docx")), None)
        xlsx = next((f for f in a.check if f.lower().endswith(".xlsx")), None)
        ok, checks = verify(docx, xlsx)
        print("格式合规校验（references/110-deliverable-format.md）")
        for item, good, detail in checks:
            print("  [%s] %-38s %s" % ("PASS" if good else "FAIL", item, detail))
        print("\n%s" % ("PASS —— 交付物符合 110 规范" if ok else "FAIL —— 有项目不合规"))
        return 0 if ok else 2

    if not a.md:
        ap.error("需要 --md（或 --check）")
    if not os.path.isfile(a.md):
        print("找不到 Markdown：%s" % a.md, file=sys.stderr)
        return 1

    with open(a.md, "r", encoding="utf-8") as f:
        text = f.read()
    blocks = parse_markdown(text)

    city = a.city or ""
    if not city:                      # 从标题里猜一个城市名
        m = re.match(r"^#\s*([^\s（(]+)", text.strip().split("\n")[0] or "")
        city = m.group(1) if m else ""
    city = S.safe_filename(city, "city")
    report_name = a.name or ("%s规划报告" % city if city != "city" else "城市规划报告")

    if a.md_only:
        print("⚠️ --md-only：按 110 §1，仅交付 Markdown，未生成 docx/xlsx。")
        print("   严格来说这只在玩家明确要求 markdown 时才应使用。")
        print("Markdown：%s" % os.path.abspath(a.md))
        return 0

    os.makedirs(a.outdir, exist_ok=True)
    docx_path = os.path.join(a.outdir, "%s.docx" % report_name)
    xlsx_path = os.path.join(a.outdir, "%s数据附录.xlsx" % S.safe_filename(city, "city"))

    # 配图：把图里的相对路径按 --maps 补全（找不到的文件由 add_figure 降级说明）
    if a.maps:
        for b in blocks:
            if b["type"] == "image" and not os.path.isabs(b["path"]):
                cand = os.path.join(a.maps, os.path.basename(b["path"]))
                b["path"] = cand if os.path.isfile(cand) else b["path"]

    metrics = None
    if a.json_path and os.path.isfile(a.json_path):
        try:
            with open(a.json_path, "r", encoding="utf-8") as f:
                metrics = json.load(f)
        except Exception as e:                        # noqa: BLE001
            print("⚠️ 指标 JSON 读取失败，XLSX 概览页跳过：%s" % e, file=sys.stderr)

    info = build_docx(blocks, docx_path, city, report_name, with_toc=a.toc)
    sheets = build_xlsx(blocks, xlsx_path, city, metrics)

    ok, checks = verify(docx_path, xlsx_path)
    print("已生成：")
    print("  DOCX：%s" % os.path.abspath(docx_path))
    print("  XLSX：%s（%d 张工作表）" % (os.path.abspath(xlsx_path), len(sheets)))
    print("  配图：%d 张已嵌入 / %d 张缺失" % (info["images_ok"], info["images_missing"]))
    print("  表格：%d 张" % sum(1 for b in blocks if b["type"] == "table"))
    print("\n格式合规校验（references/110-deliverable-format.md）")
    for item, good, detail in checks:
        print("  [%s] %-38s %s" % ("PASS" if good else "FAIL", item, detail))
    if not ok:
        print("\n⚠️ 有项目不合规 —— 请改 scripts/core/deliverable_style.py 后重新生成，"
              "不要在 Word 里手改（下次生成会丢）。")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
