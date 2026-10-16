# -*- coding: utf-8 -*-
"""deliverable_style.py —— **交付格式的唯一实现来源**。

规范原文：`references/110-deliverable-format.md`（normative）。
**任何字号 / 字体 / 缩进 / 颜色 / 列宽都只能写在这里**，
`analysis/` 与 `export_report.py` 一律 import 本模块，不得就地硬编码 ——
否则规范与实现会脱钩（见 `110` §12）。

依赖：python-docx（DOCX）、openpyxl（XLSX）、Pillow（读图尺寸）。
"""
from __future__ import annotations

import os

# ============================================================ 字体（110 §2）
CN_FONT = "微软雅黑"           # w:eastAsia
EN_FONT = "Calibri"           # w:ascii / w:hAnsi
MONO_FONT = "Consolas"        # w:cs（代码 / 路径 / 字段名）

# ============================================================ 颜色（110 §4）
C_H1 = "14366B"
C_H2 = "1B4B8C"
C_H3 = "215CA8"
C_SUBTITLE = "444C5A"
C_COVER_NOTE = "777E8A"
C_BODY = "000000"
C_QUOTE = "3A424E"
C_QUOTE_BAR = "C8D2E0"
C_CAPTION = "555B66"
C_TBL_BORDER = "BFC6D2"
C_TBL_HEADER = "1B4B8C"
C_FOOTER = "888E99"
C_XLSX_TITLE = "14366B"
C_XLSX_NOTE = "666E7C"

# ============================================================ 页面（110 §3）
PAGE = dict(page_w_cm=21.0, page_h_cm=29.7,
            top_cm=2.2, bottom_cm=2.0, side_cm=2.4,
            content_cm=16.2)          # 版心宽 = 21.0 − 2.4 − 2.4

IMG_MAX_W_CM = 16.2                   # 110 §6
IMG_MAX_H_CM = 20.5                   # 竖向图的高度上限（A4 版心高 25.5 cm，留题注位）

# ============================================================ 段落（110 §4）
# 键名即 `add_para()` 的 spec 名。indent 单位 pt：first=首行缩进，left=左缩进，
# hanging=悬挂缩进（与 left 同时给出时为"左 X + 悬挂 Y"）。
SPEC = {
    "cover_title": dict(size=30, bold=True, color=C_H1, line=1.0, before=0, after=4,
                        left=0, first=0, hanging=0, align="center"),
    "cover_sub": dict(size=14, bold=False, color=C_SUBTITLE, line=1.0, before=0, after=28,
                      left=0, first=0, hanging=0, align="center"),
    "cover_info": dict(size=11.5, bold=False, color=C_BODY, line=1.0, before=0, after=6,
                       left=0, first=0, hanging=0, align="center"),
    "cover_note": dict(size=9.5, bold=False, color=C_COVER_NOTE, line=1.0, before=0, after=0,
                       left=0, first=0, hanging=0, align="center"),

    "h1": dict(size=17, bold=True, color=C_H1, line=1.0, before=16, after=6,
               left=0, first=0, hanging=0, align="left", keep=("next", "lines")),
    "h2": dict(size=13.5, bold=True, color=C_H2, line=1.0, before=10, after=6,
               left=0, first=0, hanging=0, align="left", keep=("next", "lines")),
    "h3": dict(size=11.5, bold=True, color=C_H3, line=1.0, before=10, after=6,
               left=0, first=0, hanging=0, align="left", keep=("next", "lines")),

    # 正文：首行缩进 2 字符 = 21 pt（正文 10.5 pt）
    # `keep="widow"` 只开孤行控制：正文长段**不要** keepNext（会把整节挤到下一页）。
    "body": dict(size=10.5, bold=False, color=C_BODY, line=1.25, before=0, after=6,
                 left=0, first=21, hanging=0, align="justify", keep="widow"),
    "bullet1": dict(size=10.5, bold=False, color=C_BODY, line=1.25, before=0, after=3,
                    left=21, first=0, hanging=12, align="left"),
    "bullet2": dict(size=10.5, bold=False, color=C_BODY, line=1.25, before=0, after=3,
                    left=33, first=0, hanging=12, align="left"),
    "quote": dict(size=10, bold=False, color=C_QUOTE, line=1.2, before=0, after=6,
                  left=21, first=0, hanging=0, align="left", quote_bar=True),

    "caption": dict(size=9, bold=False, color=C_CAPTION, line=1.0, before=2, after=12,
                    left=0, first=0, hanging=0, align="center", keep="lines"),
    "tbl_caption": dict(size=10, bold=True, color=C_H2, line=1.0, before=6, after=2,
                        left=0, first=0, hanging=0, align="center", keep=("next", "lines")),
    "figure": dict(size=10.5, bold=False, color=C_BODY, line=1.0, before=6, after=2,
                   left=0, first=0, hanging=0, align="center", keep=("next", "lines")),
}

# ============================================================ 表格（110 §5）
TABLE = dict(font_pt=9.5, header_font_pt=9.5, header_bold=True,
             header_color="FFFFFF", header_fill=C_TBL_HEADER,
             border_pt=0.5, border_color=C_TBL_BORDER,
             cell_after_pt=1.0, cant_split=True, repeat_header=True,
             empty_marker="—",
             max_width_cm=PAGE["content_cm"])

# ============================================================ 页脚（110 §7）
FOOTER = dict(font_pt=8, color=C_FOOTER, align="center",
              template="{name}  ·  第 {page} 页")

# ============================================================ XLSX（110 §8）
XLSX = dict(title_pt=13, note_pt=9, header_pt=10.5, body_pt=10,
            header_fill=C_TBL_HEADER, header_color="FFFFFF",
            title_color=C_XLSX_TITLE, note_color=C_XLSX_NOTE,
            freeze=True, max_sheet_len=31, sheet_bad_chars=list('[]:*?/\\'),
            empty_marker="—")


# ============================================================ DOCX 应用层
def _rgb(hexstr):
    from docx.shared import RGBColor
    return RGBColor.from_string(hexstr)


def _set_run_font(run, size_pt, bold, color, mono=False):
    """**中西文分别设字体**（110 §2）—— 只设 run.font.name 中文会掉成宋体。"""
    from docx.oxml.ns import qn
    from docx.shared import Pt
    run.font.size = Pt(size_pt)
    run.bold = bool(bold)
    run.font.color.rgb = _rgb(color)
    run.font.name = EN_FONT
    rPr = run._element.get_or_add_rPr()
    rf = rPr.find(qn("w:rFonts"))
    if rf is None:
        rf = rPr.makeelement(qn("w:rFonts"), {})
        rPr.insert(0, rf)
    rf.set(qn("w:ascii"), MONO_FONT if mono else EN_FONT)
    rf.set(qn("w:hAnsi"), MONO_FONT if mono else EN_FONT)
    rf.set(qn("w:eastAsia"), CN_FONT)
    rf.set(qn("w:cs"), MONO_FONT)


def _apply_para_fmt(p, spec):
    from docx.shared import Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
    pf = p.paragraph_format
    pf.space_before = Pt(spec["before"])
    pf.space_after = Pt(spec["after"])
    pf.line_spacing = spec["line"]
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    # **值为 0 时不写 `w:ind`** —— 写了会产出 `w:firstLine="0"` 这类无意义属性，
    # 既污染 XML，也让"缩进必须是 420/240 twip"的校验没法用。
    left = spec.get("left", 0) or 0
    if left:
        pf.left_indent = Pt(left)
    hang = spec.get("hanging", 0) or 0
    first = spec.get("first", 0) or 0
    if hang:
        pf.first_line_indent = Pt(-hang)        # python-docx 会写成 w:hanging
    elif first:
        pf.first_line_indent = Pt(first)        # w:firstLine
    amap = {"center": WD_ALIGN_PARAGRAPH.CENTER,
            "left": WD_ALIGN_PARAGRAPH.LEFT,
            "right": WD_ALIGN_PARAGRAPH.RIGHT,
            "justify": WD_ALIGN_PARAGRAPH.JUSTIFY}
    p.alignment = amap.get(spec.get("align", "left"), WD_ALIGN_PARAGRAPH.LEFT)
    if spec.get("quote_bar"):
        _set_left_bar(p, left, C_QUOTE_BAR)
    if spec.get("keep"):
        _set_keep(p, spec["keep"])


#: 分页控制（`references/110` §5.1）。Word 只在**分页时**读这三项，
#: 因此它们不改变任何已校验的字号/缩进/列宽数值 —— 加了以后 110 校验仍全 PASS。
KEEP_TOKENS = {
    "next": "w:keepNext",        # 与下一段同页（标题、图表题）
    "lines": "w:keepLines",      # 本段不跨页（短标题）
    "widow": "w:widowControl",   # 孤行控制（正文长段）
}


def _set_keep(p, tokens):
    """给段落写 `<w:keepNext>` / `<w:keepLines>` / `<w:widowControl>`。

    ⚠️ 用**直接格式**写在 `pPr` 上（不是命名样式）：
    Word 与 LibreOffice 都认直接格式，且不改动 `styles.xml` 里的基准样式 ——
    这样"基准样式 正文字号 = 10.5 pt / 中文 = 微软雅黑"这类校验不会被打扰。
    """
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    pPr = p._p.get_or_add_pPr()
    # `w:keepNext` 等属于 `w:pPr` 里 **`w:pBdr` 之前** 的兄弟元素；
    # python-docx 的 `get_or_add_pPr()` 已保证 pPr 存在，这里按 schema 顺序前插即可。
    for tok in (tokens if isinstance(tokens, (list, tuple)) else [tokens]):
        tag = KEEP_TOKENS.get(tok)
        if not tag or pPr.find(qn(tag)) is not None:
            continue
        el = OxmlElement(tag)
        if tok == "widow":
            el.set(qn("w:val"), "1")
        ins = pPr.find(qn("w:pBdr"))
        if ins is not None:
            ins.addprevious(el)
        else:
            pPr.insert(0, el)


def _set_left_bar(p, left_pt, color):
    """引用块的左侧竖线（110 §4）。"""
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    pPr = p._p.get_or_add_pPr()
    bdr = OxmlElement("w:pBdr")
    lft = OxmlElement("w:left")
    lft.set(qn("w:val"), "single")
    lft.set(qn("w:sz"), "6")        # 0.75 pt
    lft.set(qn("w:space"), "8")     # 与文字的间距（pt）
    lft.set(qn("w:color"), color)
    bdr.append(lft)
    pPr.append(bdr)


def apply_page_and_styles(doc):
    """页面设置 + 基准样式（110 §3/§2）。"""
    from docx.shared import Pt, Cm
    from docx.oxml.ns import qn
    s = doc.sections[0]
    s.page_width, s.page_height = Cm(PAGE["page_w_cm"]), Cm(PAGE["page_h_cm"])
    s.top_margin, s.bottom_margin = Cm(PAGE["top_cm"]), Cm(PAGE["bottom_cm"])
    s.left_margin = s.right_margin = Cm(PAGE["side_cm"])

    normal = doc.styles["Normal"]
    normal.font.name = EN_FONT
    normal.font.size = Pt(SPEC["body"]["size"])
    rPr = normal.element.get_or_add_rPr()
    rf = rPr.find(qn("w:rFonts"))
    if rf is None:
        rf = rPr.makeelement(qn("w:rFonts"), {})
        rPr.insert(0, rf)
    rf.set(qn("w:ascii"), EN_FONT)
    rf.set(qn("w:hAnsi"), EN_FONT)
    rf.set(qn("w:eastAsia"), CN_FONT)
    rf.set(qn("w:cs"), MONO_FONT)
    normal.paragraph_format.space_after = Pt(SPEC["body"]["after"])
    normal.paragraph_format.line_spacing = SPEC["body"]["line"]

    for name, key in (("Heading 1", "h1"), ("Heading 2", "h2"), ("Heading 3", "h3")):
        st = doc.styles[name]
        sp = SPEC[key]
        st.font.name = EN_FONT
        st.font.size = Pt(sp["size"])
        st.font.bold = True
        st.font.color.rgb = _rgb(sp["color"])
        rPr = st.element.get_or_add_rPr()
        rf = rPr.find(qn("w:rFonts"))
        if rf is None:
            rf = rPr.makeelement(qn("w:rFonts"), {})
            rPr.insert(0, rf)
        rf.set(qn("w:ascii"), EN_FONT)
        rf.set(qn("w:hAnsi"), EN_FONT)
        rf.set(qn("w:eastAsia"), CN_FONT)
        st.paragraph_format.space_before = Pt(sp["before"])
        st.paragraph_format.space_after = Pt(sp["after"])
        st.paragraph_format.line_spacing = sp["line"]
        st.paragraph_format.first_line_indent = Pt(0)
        st.paragraph_format.left_indent = Pt(0)
    return doc


def add_para(doc, spec_name, text="", runs=None):
    """按 SPEC[spec_name] 落一个段落。

    `runs` 给出时用它做行内混排：`[(文本, {bold, mono}), …]`；
    否则整段用 `text`（含 `**粗体**` / `` `代码` `` 行内标记时自动解析）。
    """
    p = doc.add_paragraph()
    spec = SPEC[spec_name]
    if runs is None:
        runs = parse_inline(text)
    for t, opt in runs:
        if not t:
            continue
        r = p.add_run(t)
        _set_run_font(r, spec["size"], opt.get("bold", spec["bold"]),
                      spec["color"], mono=opt.get("mono", False))
    if not runs:
        r = p.add_run("")
        _set_run_font(r, spec["size"], spec["bold"], spec["color"])
    _apply_para_fmt(p, spec)
    return p


def parse_inline(text):
    """把 `**粗体**` 与 `` `代码` `` 解析成 runs（110 未规定行内样式，保持最小集）。

    **必须递归**：源稿里常见 `**…`代码`…**` 这种嵌套（先匹配到 `**…**`，
    里面的反引号若不递归解析就会原样漏进 Word）。
    """
    out = []
    _scan_inline(text, out, bold=False)
    return out


_INLINE_RE = None


def _scan_inline(text, out, bold):
    global _INLINE_RE
    if _INLINE_RE is None:
        import re as _re
        _INLINE_RE = _re.compile(r"(\*\*.+?\*\*|`[^`]+`)", _re.S)
    i = 0
    for m in _INLINE_RE.finditer(text):
        if m.start() > i:
            out.append((text[i:m.start()], {"bold": bold}))
        tok = m.group(0)
        if tok.startswith("**"):
            _scan_inline(tok[2:-2], out, True)          # 粗体里还能有代码
        else:
            out.append((tok[1:-1], {"bold": bold, "mono": True}))
        i = m.end()
    if i < len(text):
        out.append((text[i:], {"bold": bold}))


def add_table(doc, headers, rows, widths_cm=None, first_col_left=True):
    """按 110 §5 落一张表。`widths_cm` 合计会被夹到 16.2 cm 以内。"""
    from docx.shared import Cm, Pt
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_ALIGN_VERTICAL
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    ncol = len(headers)
    t = doc.add_table(rows=1, cols=ncol)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False

    if not widths_cm:
        widths_cm = [TABLE["max_width_cm"] / ncol] * ncol
    total = sum(widths_cm)
    if total > TABLE["max_width_cm"]:
        widths_cm = [w * TABLE["max_width_cm"] / total for w in widths_cm]

    tblPr = t._tbl.tblPr
    lay = OxmlElement("w:tblLayout")
    lay.set(qn("w:type"), "fixed")
    tblPr.append(lay)
    tw = OxmlElement("w:tblW")
    tw.set(qn("w:type"), "dxa")
    tw.set(qn("w:w"), str(int(sum(widths_cm) * 567)))
    tblPr.append(tw)
    _set_table_borders(tblPr)

    def _fill(cell, value, header=False, idx=0):
        # ⚠️ `cell.text = ""` 会**留下一个没有 rPr 的空 run**（中文会掉成宋体），
        # 必须先把它删干净再写自己的 run。
        p = cell.paragraphs[0]
        for r in list(p.runs):
            r._element.getparent().remove(r._element)
        raw = TABLE["empty_marker"] if value is None or value == "" else str(value)
        # 单元格里也会有 `**粗体**` / `` `代码` `` —— 必须解析，
        # 否则会在 Word 里原样显示成 `**解锁内 km**`。
        for t, opt in (parse_inline(raw) or [(raw, {})]):
            if t == "":
                continue
            r = p.add_run(t)
            _set_run_font(r, TABLE["header_font_pt"] if header else TABLE["font_pt"],
                          header or opt.get("bold", False),
                          TABLE["header_color"] if header else C_BODY,
                          mono=opt.get("mono", False))
        if not p.runs:                      # 全空单元格也要留一个带字体的 run
            r = p.add_run("")
            _set_run_font(r, TABLE["header_font_pt"] if header else TABLE["font_pt"],
                          header, TABLE["header_color"] if header else C_BODY)
        p.paragraph_format.space_after = Pt(TABLE["cell_after_pt"])
        p.paragraph_format.space_before = Pt(0)
        # ⚠️ 不要写 `first_line_indent = Pt(0)`：那会产出 `w:firstLine="0"`，
        # 让"缩进只能是 420/240 twip"的校验失效。单元格本来就不缩进，不写即可。
        if header:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif idx == 0 and first_col_left:
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        else:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        if header:
            sh = OxmlElement("w:shd")
            sh.set(qn("w:val"), "clear")
            sh.set(qn("w:fill"), TABLE["header_fill"])
            cell._tc.get_or_add_tcPr().append(sh)

    for i, h in enumerate(headers):
        _fill(t.rows[0].cells[i], h, header=True)
    if TABLE["repeat_header"]:
        trPr = t.rows[0]._tr.get_or_add_trPr()
        th = OxmlElement("w:tblHeader")
        trPr.append(th)

    for row in rows:
        tr = t.add_row()
        if TABLE["cant_split"]:
            tr._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        for i in range(ncol):
            _fill(tr.cells[i], row[i] if i < len(row) else "", idx=i)

    for r in t.rows:
        for i, w in enumerate(widths_cm):
            r.cells[i].width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def _set_table_borders(tblPr):
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    b = OxmlElement("w:tblBorders")
    sz = str(int(TABLE["border_pt"] * 8))       # eighths of a point
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement("w:" + edge)
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), sz)
        e.set(qn("w:space"), "0")
        e.set(qn("w:color"), TABLE["border_color"])
        b.append(e)
    tblPr.append(b)


def add_figure(doc, image_path, caption):
    """按 110 §6 落一张图 + 图题（**题在图下**）。找不到文件时不中断。"""
    from docx.shared import Cm, Pt
    ok = image_path and os.path.isfile(image_path)
    if ok:
        try:
            from PIL import Image
            with Image.open(image_path) as im:
                pw, ph = im.size
            w = min(IMG_MAX_W_CM, PAGE["content_cm"])
            h = w * ph / float(pw)
            if h > IMG_MAX_H_CM:
                h = IMG_MAX_H_CM
                w = h * pw / float(ph)
            p = doc.add_paragraph()
            _apply_para_fmt(p, SPEC["figure"])
            r = p.add_run()
            # 图片 run 也要带字体属性 —— 否则"每个 run 都有 w:eastAsia"的校验会挂，
            # 而且用户往图上补字时会掉成宋体。
            _set_run_font(r, SPEC["figure"]["size"], False, C_BODY)
            r.add_picture(image_path, width=Cm(w), height=Cm(h))
        except Exception as e:                      # noqa: BLE001
            p = doc.add_paragraph()
            r = p.add_run("［图缺失：%s（%s）］" % (os.path.basename(image_path), e))
            _set_run_font(r, SPEC["caption"]["size"], False, C_CAPTION)
            _apply_para_fmt(p, SPEC["caption"])
            return False
    else:
        p = doc.add_paragraph()
        r = p.add_run("［图缺失：%s］" % (os.path.basename(image_path or "未给出") ))
        _set_run_font(r, SPEC["caption"]["size"], False, C_CAPTION)
        _apply_para_fmt(p, SPEC["caption"])
    add_para(doc, "caption", caption)
    return ok


def add_footer(section, report_name):
    """页脚：`<报告名>  ·  第 N 页`（110 §7），页码用 PAGE 域。"""
    from docx.shared import Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    p = section.footer.paragraphs[0]
    # `p.text = ""` 会**留下一个没有 rPr 的空 run** —— 先清干净
    for r in list(p.runs):
        r._element.getparent().remove(r._element)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    head = FOOTER["template"].split("{page}")[0].format(name=report_name)
    tail = FOOTER["template"].split("{page}")[1]
    r1 = p.add_run(head)
    _set_run_font(r1, FOOTER["font_pt"], False, FOOTER["color"])
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    rr = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    rf = OxmlElement("w:rFonts")
    rf.set(qn("w:ascii"), EN_FONT)
    rf.set(qn("w:hAnsi"), EN_FONT)
    rf.set(qn("w:eastAsia"), CN_FONT)
    rf.set(qn("w:cs"), MONO_FONT)
    rPr.append(rf)
    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), str(int(FOOTER["font_pt"] * 2)))
    rPr.append(sz)
    col = OxmlElement("w:color")
    col.set(qn("w:val"), FOOTER["color"])
    rPr.append(col)
    rr.append(rPr)
    fld.append(rr)
    p._p.append(fld)
    if tail:
        r2 = p.add_run(tail)
        _set_run_font(r2, FOOTER["font_pt"], False, FOOTER["color"])
    p.paragraph_format.space_after = Pt(0)


def add_toc_placeholder(doc, titles):
    """目录（110 未强制分页，这里给可点击的静态目录）。"""
    add_para(doc, "h1", "目录")
    for t in titles:
        add_para(doc, "bullet1", t)


def page_break(doc):
    from docx.enum.text import WD_BREAK
    from docx.shared import Pt
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run()
    _set_run_font(r, SPEC["body"]["size"], False, C_BODY)
    r.add_break(WD_BREAK.PAGE)


def safe_filename(name, fallback="city"):
    """Windows 非法字符替换（110 §9）。"""
    bad = '\\/:*?"<>|'
    out = "".join("_" if ch in bad else ch for ch in (name or "")).strip()
    return out or fallback


def safe_sheet_name(name, used=None):
    """Excel 工作表名：≤31 字符、去非法字符、去重（110 §8）。"""
    s = "".join("_" if ch in XLSX["sheet_bad_chars"] else ch for ch in (name or "Sheet"))
    s = s[:XLSX["max_sheet_len"]].strip() or "Sheet"
    if used is not None:
        base, k = s, 2
        while s in used:
            suffix = "(%d)" % k
            s = base[:XLSX["max_sheet_len"] - len(suffix)] + suffix
            k += 1
        used.add(s)
    return s
