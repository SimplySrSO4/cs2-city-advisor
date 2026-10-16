#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
city_archive.py —— **成果归档**：只留人能看懂的，删掉过程产物。

⭐ 规则（`SKILL.md` 的「归档」条）
----------------------------
> 生成完毕最终输出文档后（无论 Word + Excel 还是 Markdown），
> **把所有文件归档到一个文件夹内；中间计算的程序、脚本、数据全部删除；
> 最终呈现必须简明且易于被人类理解。**

**保留（KEEP）** —— 只有人会打开的东西：

| 类别 | 例 |
|---|---|
| 最终文档 | `*.md` / `*.docx` / `*.xlsx` / `*.pdf` |
| 文档里引用的图 | `*.png` / `*.jpg` / `*.svg` |
| 人类可读的对照表 | `names.json`（地名别名表，人要看） |

**删除（PURGE）** —— 过程产物：

| 类别 | 例 | 为什么能删 |
|---|---|---|
| 全部脚本 | `scripts/`、`*.py`、`*.ps1` | 结论已写进文档；脚本可重跑 |
| 机器可读中间数据 | `city_metrics.json`、`structure*.json`、`*.csv` | **数字已抄进文档正文** |
| 诊断底稿 | `city_report.md` | 它的结论已整合进最终文档 |
| 出图中间件 | `qgis/`（GeoPackage + 转换用 GeoJSON） | 可重新 `--prepare` 生成 |
| Univer 过程件 | `<存档名>报告.univer`、`_univer_js/`、`_shots/` | DOCX 已导出；容器与 Facade JS 都是中间件（见 `references/80` §3.4） |
| 字体/缓存/临时 | `__pycache__`、`fonts/`、`*.tmp`、`*.log` | 纯过程垃圾 |

⚠️ **前提是"自包含"**：删掉 `city_report.md` / `city_metrics.json` 之后，
**最终文档里被引用的数字必须已经写在正文里**（表格或括注）。
本工具会在报告里找不到"数据来源"字样时给一条提醒（见 `check()`）。

⭐⭐ **归档前还会跑一次「正文体检」**（`core/text_lint.py`，规则见 `SKILL.md` 的「正文纯净」条）：
最终文档里**不得**出现编写期注释（`口径（… 修正）`、`上一版…`、`本轮新增`）、
skill 内部标签（`SKILL.md` / `references/xx` / `铁律 N`）、`§` 编号混用、来回指代。
**命中时 `--apply` 会中止**（确认无害可加 `--force`）。

用法
----
```bash
# 只检查（不删任何东西）——默认行为
<python> -X utf8 scripts/city_archive.py --dir <报告目录>

# 真正执行归档（先看一遍 check 输出再执行）
<python> -X utf8 scripts/city_archive.py --dir <报告目录> --apply
```
"""

import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import text_lint  # noqa: E402

#: 保留的扩展名（人类会直接打开的东西）
KEEP_EXT = {".md", ".docx", ".xlsx", ".xls", ".pdf", ".png", ".jpg", ".jpeg", ".svg", ".txt"}

#: 即使扩展名在上面，也属于过程产物的文件名（精确匹配）
#: ⚠️ 这里是**维护者清单**：`structure7.md` 这类"以 Markdown 写的中间分析"名字上像成果、
#: 实质是过程底稿（结论已整合进最终报告）—— 只能靠名单区分，别指望靠扩展名猜。
PURGE_NAMES = {
    "city_metrics.json", "city_report.md", "city_report.json",
    "metrics.json", "report_raw.md", "structure7.md", "structure7.json",
}

#: 一律删除的目录名
PURGE_DIRS = {"scripts", "__pycache__", "qgis", "fonts", ".ipynb_checkpoints", "cache", "tmp",
              # dsh-univer-office 的过程文件：容器与生成的 Facade JS（见 `references/80` §3.4）
              "_univer_js", "_shots", "checks"}

#: 保留的"人类可读对照表"（即便它是 .json）
KEEP_JSON = {"names.json", "数据说明.json"}

#: 需要提醒作者补一句"数据来源/自包含说明"的关键词
SELF_CONTAINED_HINTS = ("数据源", "数据来源", "口径声明", "本报告自包含", "Carto")


def classify(path, root):
    """返回 `('keep'|'purge', 原因)`。"""
    rel = os.path.relpath(path, root)
    parts = rel.replace("\\", "/").split("/")
    name = parts[-1]
    ext = os.path.splitext(name)[1].lower()
    # Office 打开文档时留下的锁文件（`~$xxx.docx`）—— 纯临时，先于扩展名判定
    if name.startswith("~$"):
        return "purge", "Office 临时锁文件（关掉 Word 后会自己消失）"
    # 目录级
    for d in parts[:-1]:
        if d in PURGE_DIRS:
            return "purge", "位于过程目录 %s/" % d
    if name in PURGE_NAMES:
        return "purge", "过程产物（结论已进最终文档）"
    if ext in (".py", ".pyc", ".ps1", ".bat", ".sh", ".ipynb"):
        return "purge", "脚本/程序"
    if ext in (".json", ".csv", ".geojson", ".gpkg", ".tif", ".shp", ".dbf", ".prj", ".cpg",
               # `.univer` 是 Univer 容器（docx 精细化用的中间件），**不是交付物**
               ".univer"):
        if name in KEEP_JSON:
            return "keep", "人类可读对照表"
        return "purge", "机器可读中间数据（数字应已抄进正文）"
    if ext in (".log", ".tmp", ".bak", ".lock"):
        return "purge", "临时/日志"
    if ext in KEEP_EXT:
        return "keep", "最终文档或配图"
    if ext == "":
        return "purge", "无扩展名（多为缓存）"
    return "kept?", "未识别的类型 —— 请人工确认"


def scan(root):
    keeps, purges, unknown = [], [], []
    for dirpath, dirnames, filenames in os.walk(root):
        for d in list(dirnames):
            if d in PURGE_DIRS:
                purges.append((os.path.join(dirpath, d) + os.sep, "过程目录 %s/" % d))
                dirnames.remove(d)
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            kind, why = classify(p, root)
            (keeps if kind == "keep" else purges if kind == "purge" else unknown).append((p, why))
    return keeps, purges, unknown


def check(root):
    """归档前检查：有没有**最终**文档？文档里有没有"自包含"说明？**正文体检过不过**？

    ⚠️ "最终文档"要**先过 `classify`** —— `city_report.md` 虽然也是 `.md`，
    但它是过程产物（结论已整合进最终文档），不能算作成果。

    返回 `(docs, imgs, notes, lint_hits)`；`lint_hits` 是 `core.text_lint` 的命中列表。
    """
    docs, process_docs = [], []
    for n in sorted(os.listdir(root)):
        p = os.path.join(root, n)
        if not os.path.isfile(p):
            continue
        if n.startswith("~$"):
            continue
        if not n.lower().endswith((".md", ".docx", ".pdf")):
            continue
        kind, _why = classify(p, root)
        (docs if kind == "keep" else process_docs).append(n)
    notes = []
    if process_docs:
        notes.append("ℹ️ 目录里的 %s 是**过程底稿**（`.md` 写的中间分析，结论已进最终文档）→ 归档时删除"
                     % "、".join(process_docs))
    if not docs:
        notes.append("⚠️ 目录里没有任何**最终**文档（.md/.docx/.pdf）—— 先写文档再归档")
    imgs = [p for p in os.listdir(root) if p.lower().endswith((".png", ".jpg", ".jpeg", ".svg"))]
    body = ""
    for d in docs:
        if d.lower().endswith(".md"):
            try:
                with open(os.path.join(root, d), encoding="utf-8") as fh:
                    body += fh.read()
            except OSError:
                pass
    if docs and body and not any(h in body for h in SELF_CONTAINED_HINTS):
        notes.append("⚠️ 最终文档里没找到「数据源 / 口径声明」字样 —— "
                     "删掉 city_report.md 与 city_metrics.json 后要保证文档**自包含**："
                     "被引用的数字必须已写在正文里")
    if not imgs:
        notes.append("ℹ️ 没有配图（「环境」条：无 QGIS 也能用 `scripts/city_svg_map.py` 出制图级配图，"
                     "不必因为没装 QGIS 就不出图 —— 只有连 Carto 导出都没有时才正常）")
    # ⭐ 正文体检：最终文档不得含编写期注释 / skill 内部标签 / § 编号混用 / 来回指代
    lint_hits = []
    for d in docs:
        if d.lower().endswith(".pdf"):
            continue
        try:
            for h in text_lint.lint_path(os.path.join(root, d)):
                h["file"] = d
                lint_hits.append(h)
        except Exception as e:                                   # noqa: BLE001
            notes.append("⚠️ 正文体检跳过 %s：%s" % (d, e))
    return docs, imgs, notes, lint_hits


def main(argv=None):
    ap = argparse.ArgumentParser(description="成果归档：只留人能看懂的，删掉过程产物")
    ap.add_argument("--dir", required=True, help="报告目录（归档目标）")
    ap.add_argument("--apply", action="store_true",
                    help="真正执行删除。**不给只做检查**（推荐先看一遍）")
    ap.add_argument("--force", action="store_true",
                    help="正文体检有命中时仍强行归档（默认中止，避免把带修订注/§ 的文档当成成品）")
    a = ap.parse_args(argv)
    root = os.path.abspath(a.dir)
    if not os.path.isdir(root):
        raise SystemExit("目录不存在：%s" % root)

    docs, imgs, notes, lint_hits = check(root)
    keeps, purges, unknown = scan(root)

    print("归档目标：%s" % root)
    print("最终文档：%s" % (", ".join(docs) if docs else "（无）"))
    print("配图    ：%d 张" % len(imgs))
    for n in notes:
        print("  " + n)
    print()
    # ⭐ 正文体检（规则见 `SKILL.md` 的「正文纯净」条）
    if lint_hits:
        print("== ❌ 正文体检：命中 %d 处（交付前必须清零）==" % len(lint_hits))
        for h in lint_hits:
            print("  ❌ %s 第 %s 行　[%s] 命中 `%s` —— %s"
                  % (h.get("file"), h.get("line"), h.get("name"), h.get("hit"), h.get("why")))
            print("      %s" % h.get("context"))
        print("  → 改法：**直接改成正确表述**，不要留修订痕迹；"
              "skill 内部标签（`SKILL.md` / `references/xx` / 铁律）换成把机制讲清楚；"
              "`§N` 一律写成「第 N 节」。")
    elif docs:
        print("== ✅ 正文体检：最终文档零命中 ==")
    print()
    print("== 保留（%d 项）==" % len(keeps))
    for p, why in sorted(keeps):
        print("  ✅ %-46s %s" % (os.path.relpath(p, root), why))
    print()
    print("== 删除（%d 项）==" % len(purges))
    for p, why in sorted(purges):
        print("  🗑  %-46s %s" % (os.path.relpath(p, root), why))
    if unknown:
        print()
        print("== 需要人工确认（%d 项）==" % len(unknown))
        for p, why in sorted(unknown):
            print("  ❓ %-46s %s" % (os.path.relpath(p, root), why))

    if not a.apply:
        print()
        print("（这是检查模式，没有删除任何东西。确认后加 --apply 执行。）")
        return 0

    if not docs:
        print()
        print("已中止：没有最终文档，不允许归档（避免把成果删没了）。")
        return 2
    if lint_hits and not a.force:
        print()
        print("已中止：正文体检有 %d 处命中（见上）—— **先改文档，再归档**。" % len(lint_hits))
        print("若确认这些命中无害（例如正文确实在解释某段历史），加 --force 跳过本检查。")
        return 3
    for p, _why in purges:
        try:
            if p.endswith(os.sep) and os.path.isdir(p):
                shutil.rmtree(p)
            elif os.path.isfile(p):
                os.remove(p)
        except OSError as exc:                                   # noqa: BLE001
            print("  !! 删除失败 %s：%s" % (p, exc))
    # 清掉可能变空的子目录
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        if dirpath != root and not os.listdir(dirpath):
            try:
                os.rmdir(dirpath)
            except OSError:
                pass
    print()
    print("归档完成。剩余 %d 项：" % len(os.listdir(root)))
    for n in sorted(os.listdir(root)):
        print("  %s" % n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
