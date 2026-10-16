#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""text_lint.py —— 最终文档的**正文体检**（正文纯净 / 自包含 / 编号统一）。

只查三件事，都是"读者一眼就能看出不对劲"的硬伤：

| 组 | 查什么 | 为什么 |
|---|---|---|
| A 编写期注释 | `口径（… 修正）`、`上一版只列了 …`、`本轮新增`、`第 N 轮改动`、`修订记录` … | 读者要的是**结论**，不是"我改过什么"；修订痕迹会让文档读起来像草稿 |
| B skill 内部标签 | `SKILL.md`、`references/xx`、`铁律 N`、`见第 0.5 节的基础体检` 这类内部结构名 | **读者没读过 skill** —— 引用它等于让读者去翻一份他手上没有的资料 |
| C 编号混用 | 出现 `§`（尤其与「第 N 节」同时出现） | `§8` 与 `8` 混用会让交叉引用指向不明；**全文只允许一套编号** |
| D 来回指代 | `见上文`、`见前文`、`见某文件`、`如前所述` | 归档后只有一个文件夹，读者不该被要求来回翻 |

用法：
    python -X utf8 scripts/core/text_lint.py <文件…>          # .md / .txt / .docx
    python -X utf8 scripts/core/text_lint.py --dir <目录>       # 目录内所有 .md/.docx/.txt

退出码：**0 = 零命中（可交付）**；1 = 有命中（先改文档）；2 = 用法错误。

设计约束：**只用标准库**（`re` / `zipfile` / `os`），因此任何机器上都能跑。
"""
from __future__ import print_function

import io
import os
import re
import sys
import zipfile

# ---------------------------------------------------------------- 规则表
#: (组, 名称, 正则, 说明)。正则一律按**中文正文**写，避免误伤代码/公式。
RULES = [
    # ---- A 编写期注释 ----
    ("A", "修订注", r"口径（[^）]{0,40}修正", "把「我改过口径」写进了正文"),
    ("A", "修订注", r"（\s*(?:F|V|v)\d+\s*修正\s*）", "轮次编号式修订注"),
    ("A", "修订注", r"第\s*\d+\s*[轮版]\s*(?:修正|改动|修订|新增)", "轮次编号式修订注"),
    ("A", "修订注", r"上一版", "拿旧版本作对比是编写期信息，正文只留当前结论"),
    ("A", "修订注", r"上一轮|本轮(?:新增|改动|修订)", "轮次对比是编写期信息"),
    ("A", "修订注", r"修订记录|改动记录|变更记录|Changelog", "变更记录不进正文"),
    ("A", "残留待办", r"\bTODO\b|\bFIXME\b|待填|占位符", "正文里有待办/占位符"),
    # ---- B skill 内部标签 ----
    ("B", "skill 标签", r"SKILL\.md", "读者没有这份 skill 文件"),
    ("B", "skill 标签", r"references/", "引用 skill 内部资料文件名"),
    ("B", "skill 标签", r"铁律", "skill 内部条目名，读者看不懂"),
    ("B", "skill 标签", r"本\s*skill|本技能文件", "自指 skill 而非直接讲机制"),
    # ---- C 编号混用 ----
    ("C", "编号混用", r"§", "全文编号必须只有一套：标题用 N./N.M，交叉引用写「第 N 节」"),
    # ---- D 来回指代 ----
    ("D", "来回指代", r"见上文|见前文|如前所述|见某文件|见另文", "归档后只有一份文档，不该要求读者来回翻"),
]

_COMPILED = [(g, name, re.compile(pat), why) for g, name, pat, why in RULES]

#: 纯文本文件后缀（直接读）
TEXT_EXT = (".md", ".txt", ".markdown", ".csv")
#: 需要解包 xml 的文件后缀
ZIP_EXT = (".docx", ".xlsx", ".pptx")


def _docx_text(path):
    """从 OOXML（docx/xlsx/pptx）里抽出可见文本，够体检用（不追求版式还原）。

    ⚠️ 段落/换行标签先换成 `\\n`，这样报出来的**行号**才有意义（否则全文是一行）。
    """
    chunks = []
    try:
        with zipfile.ZipFile(path) as z:
            for nm in z.namelist():
                if not nm.endswith(".xml"):
                    continue
                if not (nm.startswith("word/") or nm.startswith("xl/") or nm.startswith("ppt/")):
                    continue
                raw = z.read(nm).decode("utf-8", "ignore")
                raw = re.sub(r"</w:p>|</a:p>|<w:br\s*/>|<w:tab\s*/>", "\n", raw)
                raw = re.sub(r"</c>|</row>", "\n", raw)
                raw = re.sub(r"<[^>]+>", "", raw)
                chunks.append(raw)
    except Exception as e:                       # noqa: BLE001
        raise RuntimeError("无法读取 %s：%s" % (path, e))
    text = "\n".join(chunks)
    text = re.sub(r"[ \t\u3000]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text


def read_text(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in ZIP_EXT:
        return _docx_text(path)
    with io.open(path, encoding="utf-8", errors="ignore") as f:
        return f.read()


def lint_text(text):
    """对一段文本做体检，返回命中列表（每条含 `group` / `name` / `why` / `hit` / `line`）。"""
    hits = []
    lines = text.splitlines() or [text]
    for g, name, rx, why in _COMPILED:
        for i, ln in enumerate(lines, 1):
            for m in rx.finditer(ln):
                hits.append({"group": g, "name": name, "why": why,
                             "hit": m.group(0), "line": i,
                             "context": ln.strip()[:160]})
    return hits


def lint_path(path):
    return lint_text(read_text(path))


def _collect(dirpath):
    out = []
    for root, _dirs, files in os.walk(dirpath):
        for fn in sorted(files):
            if fn.lower().endswith(TEXT_EXT + ZIP_EXT) and not fn.startswith("~$"):
                out.append(os.path.join(root, fn))
    return out


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    targets = []
    if argv and argv[0] == "--dir":
        if len(argv) < 2:
            print("用法：text_lint.py --dir <目录>")
            return 2
        targets = _collect(argv[1])
    else:
        targets = [a for a in argv if not a.startswith("--")]
    if not targets:
        print(__doc__)
        return 2

    total = 0
    for p in targets:
        if not os.path.isfile(p):
            print("⚠️ 跳过（不是文件）：%s" % p)
            continue
        try:
            hits = lint_path(p)
        except Exception as e:                    # noqa: BLE001
            print("⚠️ 跳过（读取失败）：%s —— %s" % (p, e))
            continue
        total += len(hits)
        rel = os.path.basename(p)
        if not hits:
            print("✅ %s —— 正文体检零命中" % rel)
            continue
        print("❌ %s —— 命中 %d 处：" % (rel, len(hits)))
        for h in hits:
            print("   [%s/%s] 第 %s 行　命中 `%s`　→ %s"
                  % (h["group"], h["name"], h["line"], h["hit"], h["why"]))
            print("        上下文：%s" % h["context"])
    print("")
    if total:
        print("❌ 正文体检未通过：共 %d 处命中 —— **先改文档，再交付/归档**。"
              "（规则见 SKILL.md「正文纯净」条）" % total)
        return 1
    print("✅ 正文体检通过：未发现编写期注释 / skill 内部标签 / 编号混用 / 来回指代。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
