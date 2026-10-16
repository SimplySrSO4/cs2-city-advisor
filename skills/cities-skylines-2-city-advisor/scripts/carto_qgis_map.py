#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
carto_qgis_map.py —— **用 QGIS 出精确规划图**（可选增强路径）

> ⭐ **没有 QGIS 时不必退回草图**：`scripts/city_svg_map.py` 读**同一套 Carto 官方
> `.qml` 样式**，在没有 QGIS 的机器上出同等精度的图（真实路幅 / 逐栋建筑 / 中文标注 /
> 图例比例尺），并自带精度自证。本脚本没有 QGIS 时会直接引导到那一条路（退出码 3）。

为什么要这条路径
----------------
`analysis/city_map.py`（Pillow）是**诊断草图**：它把地块画成 bbox、把同名道路画成折线，
够用但**不是地图**。本项目实测：`MapTile`/`Area_Boundary` 是**不规则多边形**（顶点 5–17 个），
用 bbox 画会把边界放错几十到几百米；而 Carto **自带官方 QGIS 样式**（`Styles/Street|Plan|Topo`），
用 QGIS 渲染可以得到：真实地块边界、真实建筑面积、路名、POI 中文标注、水域 ——
**并且是逐要素按官方规则渲染的，没有"自己猜图层"的成分**。

⚠️ **`--layers` 的方向**：`QgsMapSettings.setLayers()` 里**第一项画在最上面**。
默认顺序把 `Zoning_Boundary` 放在第一位，于是**分区图斑会盖住建筑**；
`Route_Centerline` 在最后，于是**公交线路被路面盖住**。
要看得见建筑与线路，把这两个往后 / 往前挪（见 `city_svg_map.py` 的两种推荐顺序；
两边语义一致，可直接照搬）。

本脚本做的事
------------
1. 读 `core/qgis_common.py` 转换好的 GeoPackage（**CRS 正确**，见该模块的踩坑记录）；
2. 按 `--style-set` 套用 Carto 官方 QML；
3. 支持**沿线区间标注**：给 `--interval 繁荣路:3690:4210` 就在图上画出该区间的高亮 + 里程括号；
4. 支持隐藏图层（默认隐藏 `Area_Boundary` —— 它的行政区块会盖住建筑）；
5. 出图带标题、图例、比例尺、指北针。

用法
----
```bash
# 第 0 步（一次）：把 Carto 数据转成 QGIS 能用的 GeoPackage
<python> scripts/carto_qgis_map.py --prepare --carto "<Carto目录>" --render-dir out/qgis

# 出图
"<QGIS>/apps/Python312/python.exe" scripts/carto_qgis_map.py \
    --render-dir out/qgis --out out/qgis/plan.png --size 2000 \
    --bounds 4300,8300,9700,13000 \
    --interval 繁荣路:3690:4210 --title "北渡区 · 繁荣路走廊"
```

⚠️ **必须用 QGIS 自带的 Python 运行**（`core/qgis_common.qgis_paths()['python']`），
并带上 `qgis_env()` 给的环境变量；用普通 Python 跑会在 `import qgis.core` 处失败。

⚠️ **`--no-legend --no-scalebar` + 无 `--title` 会走"直接渲染"分支**（不看 `--canvas-w`，
输出恒为 `--size × --size`，且 QGIS 按 96 dpi 换算样式里的 mm/pt），
**与版式分支的纸面密度不同**，同样的样式在这两条分支上"粗细/字号"看起来不一样 ——
这是 QGIS 的行为，不是 bug；要可比就固定走版式分支（给 `--title`）。
"""

import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from core import qgis_common as QC          # noqa: E402

EPSG = "EPSG:32631"

#: 图层在**图例里显示的名字**（默认英文图层名对读者没有意义）
LAYER_LABELS = {
    "Zoning_Boundary": "分区用途",
    "Building_Boundary": "建筑",
    "Network_Boundary": "道路（真实路幅）",
    "Network_Centerline": "路名标注",
    "POI_Location": "站点与设施",
    "Route_Centerline": "公交 / 轨道线路",
    "Area_Boundary": "行政区",
}


def _local_road_geometry(carto_dir, name, layer="roads"):
    """在**普通 Python** 下算好道路连通段与区间（不依赖 QGIS）。"""
    from core.carto_reader import CartoData
    from core import roads as R
    c = CartoData(carto_dir)
    return R.road_geometry(c, name, layer=layer)


# ------------------------------------------------------------------ 渲染端

def render(args, paths):
    from qgis.core import (QgsApplication, QgsVectorLayer, QgsCoordinateReferenceSystem,
                           QgsMapSettings, QgsMapRendererSequentialJob, QgsRectangle,
                           QgsProject, QgsPrintLayout, QgsLayoutItemMap, QgsLayoutItemLabel,
                           QgsLayoutItemLegend, QgsLayoutItemScaleBar, QgsLayoutPoint,
                           QgsLayoutSize, QgsUnitTypes, QgsLayoutExporter, QgsFeature,
                           QgsLegendStyle,
                           QgsGeometry, QgsPointXY, QgsFields, QgsField, QgsLineSymbol,
                           QgsSingleSymbolRenderer, QgsMarkerSymbol, QgsPalLayerSettings,
                           QgsTextFormat, QgsTextBufferSettings, QgsVectorLayerSimpleLabeling)
    from qgis.PyQt.QtCore import QSize, QVariant
    from qgis.PyQt.QtGui import QColor, QFont

    QgsApplication.setPrefixPath(paths["prefix"], True)
    app = QgsApplication([], False)
    app.initQgis()

    legend_on = not args.no_legend
    sb_on = not args.no_scalebar

    layers = []
    for name in args.layers:
        p = os.path.join(args.render_dir, name + ".gpkg")
        if not os.path.exists(p):
            sys.stderr.write("缺少图层 %s（先跑 --prepare）\n" % p)
            continue
        lyr = QgsVectorLayer("%s|layername=%s" % (p, name), name, "ogr")
        if not lyr.isValid():
            sys.stderr.write("图层不可用：%s\n" % name)
            continue
        # 图例里用中文名（图层名本身不变，便于排查）
        lyr.setName(LAYER_LABELS.get(name, name))
        # 官方 QML
        tpl = QC.STYLE_FILES.get(name)
        if tpl and args.styles:
            qml = os.path.join(args.styles, args.style_set, tpl % args.style_set)
            if os.path.exists(qml):
                lyr.loadNamedStyle(qml)
        # 行政区块默认不画（会盖住建筑）；要用就得从 --hide 里去掉
        if name in args.hide:
            continue
        layers.append(lyr)
    if not layers:
        raise SystemExit("没有任何可用图层。")

    ext = None
    if args.bounds:
        x0, y0, x1, y1 = [float(v) for v in args.bounds.split(",")]
        x0, x1 = QC.local_to_utm(x0, 0)[0], QC.local_to_utm(x1, 0)[0]
        ext = QgsRectangle(x0, y0, x1, y1)
    else:
        ext = layers[0].extent()
        for l in layers[1:]:
            ext.combineExtentWith(l.extent())

    # --- 沿线区间高亮（可选）---
    extra = []
    for spec in (args.interval or []):
        try:
            nm, s1, s2 = spec.split(":")
            s1, s2 = float(s1), float(s2)
        except ValueError:
            sys.stderr.write("--interval 格式应为 路名:s1:s2，收到 %r\n" % spec)
            continue
        g = _local_road_geometry(args.carto, nm)
        if not g.runs:
            sys.stderr.write("找不到路名 %s\n" % nm)
            continue
        pts = g.window(s1, s2, args.interval_run)
        pts = [QC.local_to_utm(x, y) for x, y in pts]
        mem = QgsVectorLayer("LineString?crs=%s" % EPSG, "高亮 " + nm, "memory")
        dp = mem.dataProvider()
        f = QgsFeature()
        f.setGeometry(QgsGeometry.fromPolylineXY([QgsPointXY(x, y) for x, y in pts]))
        dp.addFeature(f)
        sym = QgsLineSymbol.createSimple({"line_color": "255,80,0,255", "line_width": "1.2"})
        mem.setRenderer(QgsSingleSymbolRenderer(sym))
        extra.append(mem)        # 端点符号 + 里程标注
        mk = QgsVectorLayer("Point?crs=%s" % EPSG, "里程 " + nm, "memory")
        dp2 = mk.dataProvider()
        flds = QgsFields()
        flds.append(QgsField("txt", QVariant.String))
        dp2.addAttributes(flds)
        mk.updateFields()
        for s in (s1, s2):
            x, y = g.point_at(args.interval_run, s)
            f = QgsFeature(mk.fields())
            f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(*QC.local_to_utm(x, y))))
            f.setAttribute("txt", "%s s=%.0f m" % (nm, s))
            dp2.addFeature(f)
        mk.setRenderer(QgsSingleSymbolRenderer(
            QgsMarkerSymbol.createSimple({"name": "circle", "color": "255,80,0,255",
                                          "size": "2.2", "outline_color": "0,0,0,255"})))
        lab = QgsPalLayerSettings()
        lab.fieldName = "txt"
        lab.enabled = True
        tf = QgsTextFormat()
        tf.setSize(9)
        tf.setColor(QColor(20, 20, 20))
        tf.setFont(QFont("Microsoft YaHei"))
        buf = QgsTextBufferSettings()
        buf.setEnabled(True)
        buf.setSize(1.0)
        buf.setColor(QColor(255, 255, 255))
        tf.setBuffer(buf)
        lab.setFormat(tf)
        mk.setLabeling(QgsVectorLayerSimpleLabeling(lab))
        mk.setLabelsEnabled(True)
        extra.append(mk)

    all_layers = layers + extra
    ms = QgsMapSettings()
    ms.setDestinationCrs(QgsCoordinateReferenceSystem(EPSG))
    ms.setLayers(all_layers)
    ms.setExtent(ext)
    ms.setOutputSize(QSize(args.size, args.size))
    ms.setBackgroundColor(QColor(*args.bg))
    ms.setFlag(QgsMapSettings.Antialiasing, True)
    ms.setFlag(QgsMapSettings.DrawLabeling, True)

    if not (legend_on or sb_on or args.title):
        job = QgsMapRendererSequentialJob(ms)
        job.start()
        job.waitForFinished()
        img = job.renderedImage()
        img.save(args.out)
        print("written:", args.out)
        return

    # --- 带版式的出图（标题 / 图例 / 比例尺）---
    proj = QgsProject.instance()
    proj.setCrs(QgsCoordinateReferenceSystem(EPSG))
    for l in all_layers:
        # ⚠️ 必须**加入项目图层树**（`addMapLayer` 第二个参数默认为 True）：
        # 若传 False，`QgsLayoutItemLegend` 拿不到图层树模型，图例会只剩一个标题框。
        proj.addMapLayer(l)

    # 画布尺寸：不给 --canvas-h 时**按出图范围的长宽比自动定**，
    # 否则方形页面会把宽图压出大片空白。
    aw, ah = ext.width(), ext.height()
    ratio = (aw / ah) if (aw > 0 and ah > 0) else 1.0
    pw, ph = args.canvas_w, args.canvas_h
    if args.canvas_h is None:
        if ratio >= 1.0:
            pw, ph = args.canvas_w, max(60.0, args.canvas_w / ratio)
        else:
            pw, ph = max(60.0, args.canvas_w * ratio), args.canvas_w
    print("画布 %.0f × %.0f mm（出图范围 %.0f × %.0f m，长宽比 %.2f）" % (pw, ph, aw, ah, ratio))
    lay = QgsPrintLayout(proj)
    lay.initializeDefaults()
    pc = lay.pageCollection()
    pc.page(0).setPageSize(QgsLayoutSize(pw, ph, QgsUnitTypes.LayoutMillimeters))
    mi = QgsLayoutItemMap(lay)
    lay.addLayoutItem(mi)
    top = 14.0 if args.title else 4.0
    mi.setRect(4.0, top, pw - 8.0, ph - top - 4.0)
    mi.setExtent(ext)
    mi.setCrs(QgsCoordinateReferenceSystem(EPSG))
    mi.setLayers(all_layers)
    mi.setFrameEnabled(True)
    mi.zoomToExtent(ext)
    if args.title:
        t = QgsLayoutItemLabel(lay)
        lay.addLayoutItem(t)
        t.setText(args.title)
        t.setFont(QFont("Microsoft YaHei", 13))
        t.attemptMove(QgsLayoutPoint(5, 4, QgsUnitTypes.LayoutMillimeters))
        t.attemptResize(QgsLayoutSize(pw - 10, 9, QgsUnitTypes.LayoutMillimeters))
    if legend_on:
        lg = QgsLayoutItemLegend(lay)
        lay.addLayoutItem(lg)
        lg.setTitle("图例")
        lg.setLinkedMap(mi)
        lg.setLegendFilterByMapEnabled(True)
        lg.setBackgroundEnabled(True)
        lg.setAutoUpdateModel(True)
        lg.setColumnCount(1)
        lg.setStyleFont(QgsLegendStyle.Title, QFont("Microsoft YaHei", 10))
        lg.setStyleFont(QgsLegendStyle.SymbolLabel, QFont("Microsoft YaHei", 8))
        lg.attemptMove(QgsLayoutPoint(6, top + 4, QgsUnitTypes.LayoutMillimeters))
        lg.attemptResize(QgsLayoutSize(58, 95, QgsUnitTypes.LayoutMillimeters))
        lg.updateLegend()
    if sb_on:
        sb = QgsLayoutItemScaleBar(lay)
        lay.addLayoutItem(sb)
        sb.setStyle("Single Box")
        sb.setLinkedMap(mi)
        sb.setUnits(QgsUnitTypes.DistanceMeters)
        sb.setUnitLabel("m")
        sb.setNumberOfSegments(2)
        sb.setUnitsPerSegment(max(100.0, round((ext.width() / 8.0) / 100.0) * 100.0))
        # ⚠️ 放在**地图框内部**的右下角：放到页面右下会跑出图幅（曾实测被裁掉一半）
        mr = mi.rect()
        sb.attemptResize(QgsLayoutSize(60, 10, QgsUnitTypes.LayoutMillimeters))
        sb.attemptMove(QgsLayoutPoint(mr.right() - 66, mr.bottom() - 16,
                                      QgsUnitTypes.LayoutMillimeters))
    out_png = args.out if args.out.lower().endswith(".png") else args.out + ".png"
    exp = QgsLayoutExporter(lay)
    st = exp.exportToImage(out_png, QgsLayoutExporter.ImageExportSettings())
    print("written:", out_png, "status", st)


def main(argv=None):
    ap = argparse.ArgumentParser(description="用 QGIS + Carto 官方样式出精确规划图")
    ap.add_argument("--prepare", action="store_true",
                    help="把 Carto 数据转成 QGIS 可用的 GeoPackage（先跑这一步）")
    ap.add_argument("--carto", default=None, help="Carto 导出目录（默认自动查找）")
    ap.add_argument("--render-dir", default="qgis", help="GeoPackage 存放目录")
    ap.add_argument("--out", default="qgis_map.png")
    ap.add_argument("--size", type=int, default=2000)
    ap.add_argument("--bounds", default=None,
                    help="出图范围（**本地米制**，即报告口径）：x0,y0,x1,y1")
    ap.add_argument("--title", default=None)
    ap.add_argument("--style-set", default="Street", choices=list(QC.STYLE_SETS))
    ap.add_argument("--styles", default=None, help="Carto Styles 目录（默认从 --carto / 游戏目录推断）")
    ap.add_argument("--layers", default="Zoning_Boundary,Building_Boundary,Network_Boundary,"
                                       "Network_Centerline,POI_Location,Route_Centerline,Area_Boundary")
    ap.add_argument("--hide", default="Area_Boundary",
                    help="默认隐藏的图层（行政区块会盖住建筑）")
    ap.add_argument("--interval", action="append", default=None,
                    help="沿线区间高亮，格式 路名:s1:s2（可重复）。s 是沿该路主连通段的里程（米）")
    ap.add_argument("--interval-run", type=int, default=0, help="区间取第几个连通段（默认 0 = 最长）")
    ap.add_argument("--no-legend", action="store_true")
    ap.add_argument("--no-scalebar", action="store_true")
    ap.add_argument("--canvas-w", type=float, default=210.0)
    ap.add_argument("--canvas-h", type=float, default=None,
                    help="版面高度（mm）。不给则按 --bounds 的长宽比自动定")
    ap.add_argument("--bg", default="252,251,248",
                    help="背景色 r,g,b")
    a = ap.parse_args(argv)
    a.layers = [s.strip() for s in a.layers.split(",") if s.strip()]
    a.hide = set(s.strip() for s in (a.hide or "").split(",") if s.strip())
    a.bg = tuple(int(v) for v in a.bg.split(","))

    # ⭐ **先假设 QGIS 不存在，再探测**（`SKILL.md` 铁律 11）。
    # 一条统一的提示语：无论哪一步发现没有 QGIS，都告诉用户**退回哪条路**，
    # 而不是抛一个被截断的 traceback。
    paths = QC.qgis_paths()
    if paths is None:
        sys.stderr.write(
            "未检测到可用的 QGIS（可用 CSL2_QGIS_ROOT 指定根目录，或设为 0 强制关闭）。\n"
            "→ 本脚本跳过。**配图改走无 QGIS 的制图级路径**（读同一套官方 .qml 样式）：\n"
            "    <python> -X utf8 scripts/city_svg_map.py \\\n"
            "        --out <图>.png --svg <图>.svg --size 2000 \\\n"
            "        --bounds <x0>,<y0>,<x1>,<y1> [--title \"…\"] [--interval 路名:s1:s2] [--check]\n"
            "  它用同一套 Carto 官方样式出**真实路幅 / 逐栋建筑 / 中文标注 / 图例比例尺**，\n"
            "  并且 `--check` 会打印精度自证数字（往返误差、真实路幅校验、比例尺校验）。\n"
            "  只有在需要**目录树/复杂标注引擎**等本脚本独有能力时才值得装 QGIS。\n"
            "  （简易草图另可用：scripts/city_map.py --layers terrain,roads,arterial）\n")
        return 3
    if a.carto is None:
        from core.carto_reader import find_carto_dir
        a.carto = find_carto_dir()
    if not a.carto:
        raise SystemExit("找不到 Carto 导出目录，请用 --carto 指定。")
    if a.styles is None:
        a.styles = os.path.join(a.carto, "Styles")

    if a.prepare:
        from core.carto_reader import CartoData
        c = CartoData(a.carto)
        print("准备 QGIS 图层 →", a.render_dir)
        QC.prepare_qgis_layers(c, a.render_dir, paths=paths)
        print("完成。现在用 QGIS 自带 Python 出图：")
        print("  %s %s --render-dir %s --out %s" %
              (paths["python"], os.path.abspath(__file__), a.render_dir, a.out))
        return 0
    render(a, paths)
    return 0


if __name__ == "__main__":
    sys.exit(main())
