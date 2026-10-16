#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
city_docx_polish.py —— **用 Univer 对已生成的 DOCX 做精细化 / 视觉验证**。

为什么需要它（本项目的实测结论）
--------------------------------
`export_report.py`（python-docx）是**规范实现**：它把 `references/110` 的每一项
（A4 / 边距 / 版心 16.2 cm / 中西文字体 / 字号 / 首行缩进 420 twip / 表格列宽与底纹 /
`w:cantSplit` / `w:tblHeader` / 页脚 `PAGE` 域）**确定性地写进 OOXML**，并用 `--check` 逐项自检。
**这一层不可替代** —— 它保证的是"数值完全符合规范"。

但它**看不见渲染结果**。实测 python-docx 直出的报告里：

| 缺口 | 后果 | 谁能补 |
|---|---|---|
| 没有 `w:keepNext` / `w:keepLines` | **标题孤在页尾**、图题与图分离、表题与表分离 | ✅ 现已直接写进 `deliverable_style`（不再依赖 Univer） |
| 无法逐页看渲染 | 换行难看、表格溢出、图被裁、章节开头空白 —— **只能靠人眼发现** | ⭐ **Univer Doc**（`univer_screenshot` 出逐页 PNG） |
| 表格表头行数模型 | 跨页时表头是否重复，只能读 OOXML 才知道 | ⭐ Univer（`getHeaderRowCount` / `setHeaderRowCount`） |

所以分工是：**python-docx 管"符合规范"，Univer 管"看起来对"** ——
两者都要，且**顺序固定：先落规范 DOCX → 再进 Univer 做精细化与视觉验证 → 再导出 → 再跑 `--check`**。

本脚本做什么
------------
它**不直接调 Univer**（Univer 只能通过 DSH 工具调用），而是：

1. 校验输入 DOCX 存在、并读出关键规格（页尺寸/边距/版心/字号/表格数/图数/域）；
2. 生成 **Univer 精细化脚本 `polish_doc.js`**（分页控制 + 表格表头 + 逐项断言）；
3. 生成 **`verify_doc.js`**（只读回读：页几何、页脚段、段落与样式、表格、图）；
4. 打印**可直接照抄的 DSH 工具调用序列**（`univer_new` → `univer_worktree` → `univer_import`
   → `univer_execute` → `univer_screenshot` → `univer_export` → `--check`）。

用法
----
```bash
<python> -X utf8 scripts/city_docx_polish.py \
    --docx "<报告目录>/<城市名>规划报告.docx" \
    --univer "<报告目录>/<城市名>报告.univer" \
    --js-dir "<报告目录>/_univer_js"
```

⚠️ **归档铁律（`SKILL.md` 铁律 13）**：`.univer` 与 `_univer_js/` 都是**过程产物**，
`city_archive.py` 会把它们清掉（`.univer` 已在删除名单外，因为它是容器 —— 见该脚本的 `PURGE_DIRS` / 扩展名规则）。
交付目录里**只留 .docx / .xlsx / 配图 / names.json**。
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import zipfile

#: 110 规范的关键数值（用于读回后比对；改规范请同步 `references/110` 与 deliverable_style）
SPEC = {
    "page_cm": (21.0, 29.7),
    "margin_cm": {"top": 2.2, "bottom": 2.0, "left": 2.4, "right": 2.4},
    "content_cm": 16.2,
    "font_cn": "微软雅黑",
    "font_en": "Calibri",
    "body_pt": 10.5,
    "h_pt": (17.0, 13.5, 11.5),
}

#: 需要做分页控制的段落特征（与 `deliverable_style.SPEC` 的 `keep` 一致）
HEADING_RE = r"^#{0,0}[一二三四五六七八九十百]+、"
CAPTION_RE = r"^图\s*\d+"


def inspect_docx(path):
    """读 OOXML，报出关键规格 —— 用来确认"进 Univer 之前就已经合规"。"""
    z = zipfile.ZipFile(path)
    doc = z.read("word/document.xml").decode("utf-8", "replace")
    foot = [n for n in z.namelist() if n.startswith("word/footer")]
    footer_txt = z.read(foot[0]).decode("utf-8", "replace") if foot else ""
    tw = re.search(r'<w:pgSz[^>]*w:w="(\d+)"[^>]*w:h="(\d+)"', doc)
    mg = re.search(r'<w:pgMar[^>]*w:top="(\d+)"[^>]*w:right="(\d+)"'
                   r'[^>]*w:bottom="(\d+)"[^>]*w:left="(\d+)"', doc)
    twip_cm = 566.929  # 1 cm = 566.929 twip
    info = {
        "page_cm": (round(int(tw.group(1)) / twip_cm, 2), round(int(tw.group(2)) / twip_cm, 2))
        if tw else None,
        "margin_cm": None,
        "content_cm": None,
        "eastAsia_runs": len(re.findall(r'w:eastAsia="', doc)),
        "keepNext": len(re.findall(r"<w:keepNext[ /]", doc)),
        "keepLines": len(re.findall(r"<w:keepLines[ /]", doc)),
        "widowControl": len(re.findall(r"<w:widowControl[ /]", doc)),
        "tblHeader": len(re.findall(r"<w:tblHeader[ /]", doc)),
        "cantSplit": len(re.findall(r"<w:cantSplit[ /]", doc)),
        "tables": len(re.findall(r"<w:tbl>", doc)),
        "images": len(re.findall(r"<w:drawing>", doc)),
        "footer_has_PAGE": "PAGE" in footer_txt,
        "first_line_420": len(re.findall(r'w:firstLine="420"', doc)),
    }
    if mg:
        t, r, b, l = (int(mg.group(i)) for i in (1, 2, 3, 4))
        info["margin_cm"] = {"top": round(t / twip_cm, 2), "right": round(r / twip_cm, 2),
                             "bottom": round(b / twip_cm, 2), "left": round(l / twip_cm, 2)}
        if tw:
            info["content_cm"] = round((int(tw.group(1)) - l - r) / twip_cm, 2)
    return info


def spec_check(info):
    """把读回值与 110 规范逐项比对，返回 `[(项, 通过, 实测)]`。"""
    rows = []
    rows.append(("页面 A4 21×29.7 cm", info["page_cm"] == SPEC["page_cm"], info["page_cm"]))
    m = info["margin_cm"] or {}
    rows.append(("页边距 2.2/2.0/2.4/2.4", 
                 (m.get("top"), m.get("bottom"), m.get("left"), m.get("right"))
                 == (2.2, 2.0, 2.4, 2.4), m))
    rows.append(("版心 16.2 cm", info["content_cm"] == SPEC["content_cm"], info["content_cm"]))
    rows.append(("每个 run 有 w:eastAsia", info["eastAsia_runs"] > 0, info["eastAsia_runs"]))
    rows.append(("正文首行缩进 420 twip", info["first_line_420"] > 0, info["first_line_420"]))
    rows.append(("页脚含 PAGE 域", info["footer_has_PAGE"], info["footer_has_PAGE"]))
    rows.append(("分页控制 keepNext", info["keepNext"] > 0, info["keepNext"]))
    rows.append(("分页控制 keepLines", info["keepLines"] > 0, info["keepLines"]))
    rows.append(("表行不跨页 cantSplit", info["cantSplit"] > 0, info["cantSplit"]))
    return rows


POLISH_JS = r"""// polish_doc.js —— Univer 精细化：分页控制 + 表格表头 + 断言
// 由 scripts/city_docx_polish.py 生成；用法见该脚本打印的工具序列。
if (!doc.isTraditional()) throw new Error("Traditional Doc required (import with docType: traditional)");
const B = api.Enum.BooleanNumber;
const paras = doc.getParagraphs();

// ① 标题类段落：与下一段同页（否则标题会孤在页尾）
const headings = paras.filter((p) => /%HEADING_RE%/.test(String(p.getText()).trim()));
let headingOk = 0;
for (const p of headings) {
  if (p.setStyle({ keepNext: B.TRUE, keepLines: B.TRUE })) headingOk++;
}

// ② 图题：不跨页，且与图同页
const captions = paras.filter((p) => /%CAPTION_RE%/.test(String(p.getText()).trim()));
let captionOk = 0;
for (const p of captions) {
  if (p.setStyle({ keepLines: B.TRUE, keepNext: B.TRUE })) captionOk++;
}

// ③ 表格：首行为表头行 → 跨页时自动重复
const tables = doc.getTables();
const tableRes = tables.map((t) => {
  const before = t.getHeaderRowCount();
  const set = t.setHeaderRowCount(1);
  return { before, set, after: t.getHeaderRowCount() };
});

// ④ 断言：任何一项没落地就抛错，避免"以为改了其实没改"
if (headingOk !== headings.length) throw new Error(`heading keepNext 未全部生效 ${headingOk}/${headings.length}`);
if (captionOk !== captions.length) throw new Error(`caption keepLines 未全部生效 ${captionOk}/${captions.length}`);
if (tableRes.some((r) => r.after < 1)) throw new Error("存在表头行数仍为 0 的表格");

return {
  headings: headings.length, headingOk,
  captions: captions.length, captionOk,
  tables: tableRes,
  keepNextNow: doc.getParagraphs().filter((p) => {
    const i = p.getInfo ? p.getInfo() : {};
    return i.paragraph && i.paragraph.keepNext === B.TRUE;
  }).length,
};
"""

VERIFY_JS = r"""// verify_doc.js —— 只读回读（不产生修订）
const PX_CM = 96 / 2.54;
const secs = doc.getSections();
return {
  flavor: doc.getDocumentFlavor(),
  isTraditional: doc.isTraditional(),
  paragraphs: doc.getParagraphs().length,
  tables: doc.getTables().length,
  images: doc.getImages().length,
  sections: secs.map((s) => {
    const d = s.describe();
    const c = d.config || {};
    const ps = c.pageSize || null;
    return {
      sectionType: d.sectionType,
      pageCm: ps ? [+(ps.width / PX_CM).toFixed(2), +(ps.height / PX_CM).toFixed(2)] : null,
      marginCm: {
        top: +(c.marginTop / PX_CM).toFixed(2), bottom: +(c.marginBottom / PX_CM).toFixed(2),
        left: +(c.marginLeft / PX_CM).toFixed(2), right: +(c.marginRight / PX_CM).toFixed(2),
      },
      contentCm: ps ? +(((ps.width - c.marginLeft - c.marginRight) / PX_CM).toFixed(2)) : null,
      footerSegments: Object.entries(d.headerFooter || {})
        .filter(([k, v]) => k.toLowerCase().includes("footer") && v && v.segmentId)
        .map(([k, v]) => ({ slot: k, segmentId: v.segmentId,
                            text: doc.getParagraphs(v.segmentId).map((p) => String(p.getText())) })),
    };
  }),
  tableHeaderRows: doc.getTables().map((t) => t.getHeaderRowCount()),
};
"""


def main(argv=None):
    ap = argparse.ArgumentParser(description="用 Univer 对已生成的 DOCX 做精细化 / 视觉验证")
    ap.add_argument("--docx", required=True, help="已由 export_report.py 生成的 DOCX")
    ap.add_argument("--univer", default=None, help="目标 .univer 路径（默认与 docx 同目录同名）")
    ap.add_argument("--js-dir", default=None, help="存放生成的 Facade JS 的目录")
    a = ap.parse_args(argv)

    docx = os.path.abspath(a.docx)
    if not os.path.exists(docx):
        raise SystemExit("找不到 DOCX：%s（先用 export_report.py 落文档）" % docx)
    base = os.path.splitext(docx)[0]
    univer = os.path.abspath(a.univer or (base + ".univer"))
    js_dir = os.path.abspath(a.js_dir or os.path.join(os.path.dirname(docx), "_univer_js"))
    os.makedirs(js_dir, exist_ok=True)

    info = inspect_docx(docx)
    print("输入 DOCX：%s" % docx)
    print("\n== 进 Univer 之前的规范自检（应由 export_report.py 保证）==")
    for name, ok, got in spec_check(info):
        print("  %s %-26s %s" % ("[OK]" if ok else "[!!]", name, got))
    print("  表格 %d 张 / 图 %d 张 / eastAsia %d 处"
          % (info["tables"], info["images"], info["eastAsia_runs"]))

    head_re = HEADING_RE
    cap_re = CAPTION_RE
    p_js = os.path.join(js_dir, "polish_doc.js")
    v_js = os.path.join(js_dir, "verify_doc.js")
    with open(p_js, "w", encoding="utf-8") as fh:
        fh.write(POLISH_JS.replace("%HEADING_RE%", head_re).replace("%CAPTION_RE%", cap_re))
    with open(v_js, "w", encoding="utf-8") as fh:
        fh.write(VERIFY_JS)
    print("\n已生成：\n  %s\n  %s" % (p_js, v_js))

    rel_docx = os.path.relpath(docx, os.getcwd()).replace("\\", "/")
    rel_univer = os.path.relpath(univer, os.getcwd()).replace("\\", "/")
    rel_p = os.path.relpath(p_js, os.getcwd()).replace("\\", "/")
    rel_v = os.path.relpath(v_js, os.getcwd()).replace("\\", "/")
    print("""
== 接下来按这个顺序调 DSH 工具（Univer 只能经工具调用，不能由本脚本直接调）==

1) univer_new            file="{u}"
2) univer_worktree       action="create", file="{u}", name="docx polish"
   → 记下返回的 worktreeId
3) univer_import         file="{u}", worktreeId=<WT>, name="<报告名>",
                         source="{d}", docType="traditional"      # traditional 才保页面设置
   → 记下返回的 unitId
4) univer_execute        file="{u}", worktreeId=<WT>, unitId=<U>, codeFile="{p}"
   → 期望 committed=true，且 headings/captions 全部生效、tables 表头行数=1
5) univer_screenshot     file="{u}", worktreeId=<WT>, unitId=<U>, output="<目录>/_shots"
   → ⭐ **逐页看图**：检查标题有没有孤在页尾、图题与图是否同页、表格有没有溢出版心、
      有没有半页空白；发现问题改 Markdown 或 references/110，然后重跑第 5 步（export_report.py）
6) univer_execute        file="{u}", worktreeId=<WT>, unitId=<U>, codeFile="{v}"   # 只读回读
   → 核对 pageCm / marginCm / contentCm = 21×29.7 / 2.2,2.0,2.4,2.4 / 16.2
7) univer_export         file="{u}", worktreeId=<WT>, unitId=<U>,
                         output="<报告目录>/<城市名>规划报告.docx"       # 覆盖为最终版
8) 交付前复检（**必跑**）：
   <python> -X utf8 scripts/export_report.py --check "<城市名>规划报告.docx" "<城市名>规划数据附录.xlsx"

⚠️ 已知限制（实测，别浪费时间找替代方案）：
  · Univer 的**渲染器不显示 PAGE 域的数字**（页脚显示成"第  页"）——
    这是渲染限制，**域本身完好**（`--check` 的"页脚含 PAGE 域"仍 PASS），
    不要为了"让截图里有页码"去写死页码。
  · `FDocumentImage.getInfo()` 不回读宽高 → 图宽请以 `--check` 的"图片宽度 ≤16.2 cm"为准。
  · 表格表头行数：python-docx 已写 `w:tblHeader`，Univer 再 `setHeaderRowCount(1)` 是**幂等**的。
""" .format(u=rel_univer, d=rel_docx, p=rel_p, v=rel_v))
    print("归档提醒（铁律 13）：.univer 与 _univer_js/ 都属过程产物，"
          "归档时由 city_archive.py 清理；交付目录只留 docx / xlsx / 配图 / names.json。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
