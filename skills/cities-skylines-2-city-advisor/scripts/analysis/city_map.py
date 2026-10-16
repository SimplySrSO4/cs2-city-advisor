#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
city_map.py —— 用 Pillow 把 Carto 数据画成诊断图（不依赖 matplotlib / QGIS）

出图内容（可分别开关）：
    1. 路网分级底图（高速 / 主干 / 支路 / 轨道，按限速与等级上色）
    2. 公共交通线路（线宽 ∝ 车辆数，颜色区分方式）
    3. 车站 600 m 腹地圆（半径可调）
    4. 人口 / 岗位密度格网（400 m）
    5. 分区用途着色（住宅/商业/工业/办公）
    6. 地形等高线（来自 Elevation.tif）

用法：
    python city_map.py --carto "<Carto 目录>" --out map.png
    python city_map.py --carto ... --out map.png --layers roads,transit,catchment,density

说明：坐标已投影（EPSG:32631，米），直接线性映射到像素即可；北向上。
"""

import argparse
import math
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(HERE)          # scripts/
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from core.carto_reader import (CartoData, GridIndex, find_carto_dir,  # noqa: E402
                               dissolve_to_rings)

# ------------------------------------------------------------------ 调色板
BG = (250, 249, 246)
#: 路网配色 —— **层级对比要拉开**，否则主次不分、看起来"干道画得不对"
C_HIGHWAY = (208, 96, 76)      # 高速：暗红，最粗
C_LARGE = (150, 145, 138)      # 大路：中深灰
C_MEDIUM = (108, 112, 120)     # 主干：偏冷灰，比大路更显眼（承载主要流量）
C_SMALL = (214, 210, 202)      # 支路：很浅，只作底纹
C_RAIL = (52, 52, 58)          # 铁路/轨道：近黑，中等粗
#: 各等级的绘制宽度（像素，会再乘 width_scale）
ROAD_WIDTH = {"Highway": 3.0, "Large": 2.4, "Medium": 2.0, "Small": 0.9}
RAIL_WIDTH = 1.8

#: 可建造性配色（水体 / 陡坡 / 缓坡 / 适宜）
BUILD_COLOR = {
    "水体": (150, 200, 235),
    "陡坡": (196, 132, 118),
    "缓坡": (238, 220, 170),
    "适宜": (206, 228, 196),
}
BUILD_LEGEND = (("适宜建设区", BUILD_COLOR["适宜"]), ("缓坡（需整地）", BUILD_COLOR["缓坡"]),
                ("陡坡（不建议）", BUILD_COLOR["陡坡"]), ("水体（禁止）", BUILD_COLOR["水体"]))

TRANSPORT_COLOR = {
    "Bus": (0, 197, 197),
    "Tram": (60, 140, 230),
    "Subway": (230, 90, 60),
    "Train": (231, 163, 29),
    "Ferry": (30, 130, 200),
    "Ship": (30, 130, 200),
    "Airplane": (140, 90, 200),
}

ZONE_COLOR = {
    "Residential": (60, 200, 80, 70),
    "Residential, Commercial": (60, 200, 80, 70),
    "Commercial": (60, 110, 240, 80),
    "Industrial": (220, 170, 40, 85),
    "Office": (150, 90, 220, 85),
    "Farmland": (200, 220, 140, 60),
    "Forestry": (120, 180, 120, 60),
    "Extractor": (170, 120, 60, 80),
}


def get_font(size):
    from PIL import ImageFont
    for name in ("msyh.ttc", "msyhbd.ttc", "simhei.ttf", "simsun.ttc", "arial.ttf"):
        for root in (r"C:\Windows\Fonts", "/usr/share/fonts", "/System/Library/Fonts"):
            p = os.path.join(root, name)
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size)
                except Exception:
                    continue
    # 找不到中文字体：退回默认字体（无法渲染中文），调用方会打英文告警
    return ImageFont.load_default()


def has_cjk_font():
    for name in ("msyh.ttc", "msyhbd.ttc", "simhei.ttf", "simsun.ttc"):
        for root in (r"C:\Windows\Fonts", "/usr/share/fonts", "/System/Library/Fonts"):
            if os.path.exists(os.path.join(root, name)):
                return True
    return False


class Mapper(object):
    """世界坐标(m) ↔ 像素。"""

    def __init__(self, bounds, width, height, pad=40):
        x0, y0, x1, y1 = bounds
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
        self.w = width - 2 * pad
        self.h = height - 2 * pad
        self.pad = pad
        spanx = max(1e-6, x1 - x0)
        spany = max(1e-6, y1 - y0)
        self.scale = min(self.w / spanx, self.h / spany)
        self.ox = pad + (self.w - spanx * self.scale) / 2.0
        self.oy = pad + (self.h - spany * self.scale) / 2.0

    def px(self, x, y):
        return (self.ox + (x - self.x0) * self.scale,
                self.oy + (self.y1 - y) * self.scale)

    def r_px(self, meters):
        return meters * self.scale

    def px_to_geo(self, px, py):
        """像素 → 世界坐标（`px` 的反函数）。"""
        return (self.x0 + (px - self.ox) / self.scale,
                self.y1 - (py - self.oy) / self.scale)


def layer_buildability(carto, draw, mapper, img):
    """画**简单地形图**：水体 / 陡坡 / 缓坡 / 适宜建设区（打底层）。

    返回 `(img, stats)`；无栅格或标定失败时原样返回 `(img, None)`。
    """
    try:
        import numpy as _np
        from PIL import Image
        from core import terrain as T
    except Exception:
        return img, None
    ox, oy, _q = T.solve_utm_offset(carto)
    if ox is None:
        return img, None
    build = T.buildability(carto, (ox, oy))
    if not build:
        return img, None

    W, H = img.size
    step = build["step"]
    # 目标像素网格 → 世界坐标（**GeoJSON 系**，与 mapper 一致）→ 加标定平移 → 栅格行列
    px = _np.arange(W)
    py = _np.arange(H)
    gx = mapper.x0 + (px - mapper.ox) / mapper.scale + ox
    gy = mapper.y1 - (py - mapper.oy) / mapper.scale + oy
    col = _np.floor((gx - build["x0"]) / step).astype(_np.int64)
    row = _np.floor((build["y0"] - gy) / step).astype(_np.int64)
    okc = (col >= 0) & (col < build["nx"])
    okr = (row >= 0) & (row < build["ny"])
    if not okc.any() or not okr.any():
        return img, build["stats"]
    # ⚠️ 必须用**联合**掩码：col 与 row 是两个独立的 1-D 序列，
    # 若各自过滤再交给 np.ix_，两者的长度会不一致、索引被错误配对。
    cc = _np.where(okc)[0]
    rr = _np.where(okr)[0]
    if not cc.size or not rr.size:
        return img, build["stats"]
    gcol = col[cc]
    grow = row[rr]
    sub = build["cls"][_np.ix_(grow, gcol)]     # object 数组，形状 (len(rr), len(cc))
    if os.environ.get("CSL2_TERRAIN_DEBUG"):
        import collections as _c
        print("[terrain-debug] W=%d H=%d nx=%d ny=%d" % (W, H, build["nx"], build["ny"]))
        print("[terrain-debug] gx %.0f..%.0f  gy %.0f..%.0f" % (gx.min(), gx.max(), gy.min(), gy.max()))
        print("[terrain-debug] col %d..%d (ok %d/%d)  row %d..%d (ok %d/%d)"
              % (col.min(), col.max(), okc.sum(), len(col), row.min(), row.max(), okr.sum(), len(row)))
        print("[terrain-debug] rr %d..%d n=%d   cc %d..%d n=%d"
              % (rr.min(), rr.max(), len(rr), cc.min(), cc.max(), len(cc)))
        print("[terrain-debug] sub.shape=%s 取值=%s"
              % (sub.shape, dict(_c.Counter(sub.ravel().tolist()))))

    # 逐类别用布尔掩码写回；world 用 (row, col) 的 open mesh 索引
    base = _np.asarray(img).copy()
    target = base[_np.ix_(rr, cc)]
    painted = 0
    for k, rgb in BUILD_COLOR.items():
        m = sub == k
        n = int(m.sum())
        if n:
            target[m] = rgb
            painted += n
    if not painted:
        return img, build["stats"]
    base[_np.ix_(rr, cc)] = target
    return Image.fromarray(base, "RGB"), build["stats"]


def draw_polyline(draw, mapper, pts, color, width):
    if len(pts) < 2:
        return
    seq = [mapper.px(x, y) for x, y in pts]
    draw.line(seq, fill=color, width=max(1, int(round(width))), joint="curve")


def draw_ring(draw, mapper, ring, color, width):
    """画**闭合多边形**（地块/分区图斑用）。`ring` 首尾不必重复。"""
    if len(ring) < 3:
        return
    seq = [mapper.px(x, y) for x, y in ring]
    draw.line(seq + [seq[0]], fill=color, width=max(1, int(round(width))), joint="curve")


def tile_rings(t):
    """地块要素 → 顶点环列表（**不要用 bbox**）。

    ⚠️ 本项目实测：`MapTile` 与 `Area_Boundary` 是**不规则多边形**（顶点 5–17 个、不在规则网格上），
    用 bbox 画会把边界放错几十到几百米。要精确出图请用本函数取真实环。
    """
    p = t.parts if t.parts and isinstance(t.parts[0], list) else [t.parts]
    return [ring for ring in p if len(ring) >= 3]


def tile_bbox(t):
    """地块 bbox —— **只用于筛选/居中，不得当作边界**。"""
    xs, ys = [], []
    for ring in tile_rings(t):
        xs += [q[0] for q in ring]
        ys += [q[1] for q in ring]
    return (min(xs), min(ys), max(xs), max(ys))


def named_road_runs(carto, name, tol=None):
    """**同名道路的连通段**（只按真实端点相接分组，绝不做"首尾相接画一条线"）。

    ⚠️ 为什么必须这样：一条路在 Carto 里是**几十条独立路段要素**，文件顺序与地理位置无关。
    把所有同名路段首尾相接画成一条折线，会**用直线把互不相邻的路段连起来** ——
    本项目第十轮实测 `繁荣路` 47 段因此被画成一条横贯全城的橙带（图上那几道平行长线）。
    完整口径见 `core/roads.py` 模块头注释。
    """
    try:
        from core import roads as _R
    except Exception:                                    # noqa: BLE001
        return []
    g = _R.road_geometry(carto, name, tol=tol) if tol else _R.road_geometry(carto, name)
    return g.runs


def layer_named_road(carto, draw, mapper, name, color=(255, 140, 0), width=4.0,
                     interval=None, run=0, label=True):
    """**画一条具名道路的连通段**（可选只画其中一个沿线区间）。

    `interval=(s1, s2)` 给定时只画该区间（`s` = 沿该路主连通段的里程，米），
    并在两端画里程标记 —— 这是"**xx路沿线 s₁–s₂ 区间**"这种表述的图上依据。
    """
    try:
        from core import roads as _R
    except Exception:                                    # noqa: BLE001
        return None
    g = _R.road_geometry(carto, name)
    if not g.runs:
        return None
    if interval:
        s1, s2 = interval
        pts = g.window(s1, s2, run)
        draw_polyline(draw, mapper, pts, color, width)
        for s in (s1, s2):
            x, y = g.point_at(run, s)
            px, py = mapper.px(x, y)
            r = max(3.0, width)
            draw.ellipse([px - r, py - r, px + r, py + r], fill=color, outline=(20, 20, 20))
            txt = "s=%.0f m" % s
            tw = draw.textlength(txt, font=get_font(11))
            draw.rectangle([px - tw / 2 - 3, py - 20, px + tw / 2 + 3, py - 4],
                           fill=(255, 255, 255), outline=color)
            draw.text((px - tw / 2, py - 19), txt, fill=(20, 20, 20), font=get_font(11))
    else:
        for ch in g.runs:
            draw_polyline(draw, mapper, ch, color, width)
    if label:
        mid = g.point_at(run, g.run_length(run) / 2)
        px, py = mapper.px(*mid)
        draw.text((px + 6, py - 14), name, fill=(180, 70, 0), font=get_font(13),
                  stroke_width=2, stroke_fill=(255, 255, 255))
    return g


class _CellShim(object):
    """把"网格格子列表"包装成 `dissolve_to_rings()` 能吃的对象（只需 `.parts`）。"""

    __slots__ = ("parts",)

    def __init__(self, cells, cell):
        self.parts = []
        for (ci, cj) in cells:
            x0, y0 = ci * cell, cj * cell
            self.parts.append([(x0, y0), (x0 + cell, y0),
                               (x0 + cell, y0 + cell), (x0, y0 + cell),
                               (x0, y0)])


def layer_unlocked_boundary(carto, draw, mapper, img, shade_locked=True):
    """⭐ **精确画出「已解锁区域」的边界**（打底层）。

    为什么专门做这一层：`MapTile` 是**不规则四边形**且**不在规则网格上**，
    逐个画出来就是一堆斜方块堆在一起 —— 既看不出范围也不好看。
    这里用 `dissolve_to_rings()` 把已解锁地块**合并成外轮廓**，得到**一条准确的边界线**。

    `shade_locked=True` 时把**未解锁区域压成浅灰**（先整体铺灰，再用背景色填出已解锁区），
    这样"能建的范围"一眼可见。

    返回 `(img, n_rings)`；无地块数据时原样返回 `(img, 0)`。
    """
    from PIL import Image, ImageDraw

    tiles = [a for a in carto.layer("areas") if a.get("Object") == "MapTile"]
    if not tiles:
        return img, 0
    unlocked = [t for t in tiles if t.get("Unlocked")]
    if not unlocked:
        return img, 0
    rings = dissolve_to_rings(unlocked)
    if not rings:
        return img, 0

    if shade_locked:
        img = img.copy()
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, img.size[0], img.size[1]], fill=(230, 228, 222))
        for r in rings:                       # 已解锁区恢复成背景色
            d.polygon([mapper.px(x, y) for x, y in r], fill=BG)
        draw = ImageDraw.Draw(img)
    return img, len(rings)


def draw_unlocked_outline(carto, draw, mapper, width=1.0):
    """把已解锁区域的**边界线**画在当前图层之上：白色描边 + 深色主线（压得住任何底色）。"""
    tiles = [a for a in carto.layer("areas") if a.get("Object") == "MapTile"]
    unlocked = [t for t in tiles if t.get("Unlocked")]
    if not unlocked:
        return 0
    rings = dissolve_to_rings(unlocked)
    for r in rings:
        seq = [mapper.px(x, y) for x, y in r]
        if len(seq) < 3:
            continue
        draw.line(seq, fill=(255, 255, 255),
                  width=max(2, int(round(3.5 * width))), joint="curve")
        draw.line(seq, fill=(38, 38, 46),
                  width=max(1, int(round(1.8 * width))), joint="curve")
    return len(rings)


def layer_clusters(carto, draw, mapper, font, clusters=None, cmap=None,
                   fills=True, labels=True):
    """**组团层**：按人口/岗位密集程度划分的组团 + 它的公交/轨道可达性。

    配色表达"关系缺口"（这是给公共交通建议时最关键的一张图）：
      * 绿 = 有**轨道**服务　蓝 = 只有地面公交　**红 = 没有任何线路直达**（优先补线）

    ⚠️ **分两步画**：`labels=False` 只画色块（垫在所有线网之下），
    最后再用 `labels=True, fills=False` 把**标签画在最上层** ——
    否则线路与站点文字会压掉组团名，图就没法读了。
    """
    try:
        from analysis.city_reports import ClusterMap
    except Exception:
        return None
    cm = cmap or ClusterMap(carto)
    gs = clusters if clusters is not None else cm.groups
    if not gs or cm.single:
        return None

    # 每个组团被多少条线路服务（含轨道）
    served = {i: {"lines": 0, "rail": 0} for i in range(len(gs))}
    for f in carto.layer("routes"):
        # ⚠️ 客运口径：货运铁路/货运航线不算"组团被公交服务"（见 SKILL.md §2 货运与产业链）
        if (f.get("Object") or "RoutePassenger") == "RouteCargo":
            continue
        is_rail = f.get("Transport") in ("Train", "Subway", "Tram")
        for k in cm.route_cluster_pairs(f):
            for i, g in enumerate(gs):
                if g.get("name") in k:
                    served[i]["lines"] += 1
                    if is_rail:
                        served[i]["rail"] += 1
                    break

    cell = gs[0].get("cell") or 150.0
    if fills:
        for i, g in enumerate(gs):
            sv = served[i]
            if sv["rail"]:
                fill, outline = (196, 232, 196), (46, 125, 50)
            elif sv["lines"]:
                fill, outline = (200, 226, 245), (25, 118, 210)
            else:
                fill, outline = (250, 205, 200), (198, 40, 40)
            # ⚠️ 不能逐格画矩形 —— 那样看起来是"一堆方块叠在一起"。
            # 用 `dissolve_to_rings()` 把这些格子**合并成一个外轮廓**，只画一圈边界。
            cells = g.get("_cells") or []
            if not cells:
                continue
            rings = dissolve_to_rings([_CellShim(cells, cell)])
            for r in rings:
                poly = [mapper.px(x, y) for x, y in r]
                if len(poly) < 3:
                    continue
                draw.polygon(poly, fill=fill, outline=outline)
    if labels:
        for i, g in enumerate(gs):
            sv = served[i]
            cx, cy = g["center"]
            px, py = mapper.px(cx, cy)
            l1 = (g.get("name") or "")[:16]
            l2 = "%s｜线路%d 轨道%d" % (g.get("type") or "", sv["lines"], sv["rail"])
            pad = 2
            for k, line in enumerate((l1, l2)):
                tw = draw.textlength(line, font=font)
                ty = py - font.size + k * (font.size + 2)
                # 白底文字框：保证压在彩色线网上也能读
                draw.rectangle([px - tw / 2 - pad, ty - pad,
                                px + tw / 2 + pad, ty + font.size + pad],
                               fill=(255, 255, 255), outline=(140, 140, 140))
                draw.text((px - tw / 2, ty), line, fill=(20, 20, 20), font=font)
    return served


def cluster_legend(served):
    """组团层的图例项。"""
    return [("组团：有轨道服务", (196, 232, 196)),
            ("组团：仅地面公交", (200, 226, 245)),
            ("组团：无直达线路（优先补线）", (250, 205, 200))]


#: 道路等级绘制顺序（低 → 高），干道最后画以压在顶层
_ROAD_RANK = {"Small": 0, "Medium": 1, "Large": 2, "Highway": 3}


def road_legend_items(carto, min_level=None):
    """图例：**只列出该 `min_level` 下真正会画出来的等级**。

    否则只画干道时图例还列着"支路"，读者会以为支路被漏画了 —— 图例必须与画面一致。
    """
    floor = _ROAD_RANK.get(min_level or "Small", 0)
    cats = {}
    for f in carto.layer("roads"):
        c = f.get("Category") or ""
        cats[c] = cats.get(c, 0.0) + f.line_length()
    has = lambda kw: any(kw in k for k in cats)          # noqa: E731
    items = []
    if has("Highway") and _ROAD_RANK["Highway"] >= floor:
        items.append(("高速 Highway", C_HIGHWAY))
    if has("Large") and _ROAD_RANK["Large"] >= floor:
        items.append(("大路 Large", C_LARGE))
    if has("Medium") and _ROAD_RANK["Medium"] >= floor:
        items.append(("主干道 Medium", C_MEDIUM))
    if has("Small") and floor <= 0:
        items.append(("支路 Small（底纹）", C_SMALL))
    if has("Train") or has("Subway"):
        items.append(("铁路 / 地铁", C_RAIL))
    return items


def layer_highlight_routes(carto, draw, mapper, names, width_scale=1.0):
    """**高亮给定线路**，其余线路淡化 —— 用于"这条线该怎么改"的单线配图。

    给公共交通建议配图时，一张图只讲一条线最有效：
    读者要能立刻看出**这条线服务哪些组团、走哪条干道、端点在哪**。
    """
    want = set(names or [])
    if not want:
        return
    for pass_dim in (True, False):
        for f in carto.layer("routes"):
            hit = f.get("Name") in want
            if hit == pass_dim:
                continue                      # 先画淡化的，再画高亮的（压在上层）
            mode = f.get("Transport") or "Bus"
            base = TRANSPORT_COLOR.get(mode, (120, 120, 120))
            color = base if hit else tuple(int(c + (245 - c) * 0.72) for c in base)
            w = (4.4 if hit else 1.6) * width_scale * (
                max(1.0, (f.get("Vehicle") or 1)) ** 0.35 if hit else 1.0)
            parts = f.parts if f.parts and isinstance(f.parts[0], list) else [f.parts]
            for part in parts:
                draw_polyline(draw, mapper, part, color, w)
            if hit:
                # 线名标签画在几何中点，带白底
                part = max(parts, key=len)
                if len(part) >= 2:
                    mx, my = part[len(part) // 2]
                    px, py = mapper.px(mx, my)
                    txt = str(f.get("Name"))[:16]
                    tw = draw.textlength(txt, font=get_font(13))
                    draw.rectangle([px - tw / 2 - 3, py - 16, px + tw / 2 + 3, py + 4],
                                   fill=(255, 255, 255), outline=base)
                    draw.text((px - tw / 2, py - 15), txt, fill=(20, 20, 20),
                              font=get_font(13))


def layer_roads(carto, draw, mapper, width_scale=1.0, clip=True, min_level=None):
    """画路网 + 铁路/轨道。

    **只画正确的几何**（这是"图上干道必须对"的前提）：
      * 几何取自 `Network_Centerline` 的**中心线**——已用「几何长度 ÷ 属性 `Length`」核验，
        各类别比值中位 ≈ **1.00**（见 `references/70`），所以位置与比例是准的；
      * 默认**裁剪到已解锁地块**（`clip=True`）：未解锁/地图外的路段不画，
        避免"图上画出城市之外的路"造成误读；
      * 不画 `Waterway`/`Pathway`（不是车行路网，混进来会干扰判读）。

    `min_level`：只画到某一等级及以上 —— `"Medium"` 表示画 高速+大路+主干（**不画支路**），
    用于"少而准"的交通/公交建议配图。`None` 表示全画。
    """
    _RANK = _ROAD_RANK
    floor = _RANK.get(min_level or "Small", 0)
    roads = carto.layer("roads")
    # 先画低等级（粗后画细，保证干道压在最上层）
    order = []
    for f in roads:
        cat = f.get("Category") or ""
        asset = f.get("Asset") or ""
        if "Waterway" in cat or "Pathway" in cat:
            continue
        if "Train" in cat or "Subway" in cat or "轨" in asset or "铁路" in asset or "火车" in asset:
            kind, color, w = "rail", C_RAIL, RAIL_WIDTH
        elif "Highway" in cat:
            kind, color, w = "Highway", C_HIGHWAY, ROAD_WIDTH["Highway"]
        elif "Large" in cat:
            kind, color, w = "Large", C_LARGE, ROAD_WIDTH["Large"]
        elif "Medium" in cat:
            kind, color, w = "Medium", C_MEDIUM, ROAD_WIDTH["Medium"]
        elif "Small" in cat:
            kind, color, w = "Small", C_SMALL, ROAD_WIDTH["Small"]
        else:
            continue
        if kind != "rail" and _RANK.get(kind, 0) < floor:
            continue
        order.append((_RANK.get(kind, 3) if kind != "rail" else 1, f, color, w))
    order.sort(key=lambda t: t[0])           # 低等级先画，干道后画（压在顶层）

    for _r, f, color, w in order:
        parts = carto.clipped_parts(f) if clip else (
            f.parts if f.parts and isinstance(f.parts[0], list) else [f.parts])
        for part in parts:
            draw_polyline(draw, mapper, part, color, w * width_scale)


def layer_zoning(carto, draw, mapper, img):
    from PIL import Image, ImageDraw
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for f in carto.layer("zoning"):
        c = ZONE_COLOR.get(f.get("Zoning") or "")
        if not c:
            continue
        for ring in f.parts:
            if len(ring) < 3:
                continue
            od.polygon([mapper.px(x, y) for x, y in ring], fill=c)
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


def layer_density(carto, draw, mapper, img, cell=400.0, which="both"):
    from PIL import Image, ImageDraw
    grid_pop = defaultdict(int)
    grid_job = defaultdict(int)
    for b in carto.layer("buildings"):
        cx, cy = b.compute_centroid()
        k = (int(cx // cell) * cell, int(cy // cell) * cell)
        grid_pop[k] += b.get("Resident") or 0
        grid_job[k] += b.get("Employee") or 0
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    maxp = max(list(grid_pop.values()) + [1])
    maxj = max(list(grid_job.values()) + [1])
    for k, v in grid_pop.items():
        if v <= 0:
            continue
        a = int(30 + 120 * (v / maxp) ** 0.6)
        x0, y0 = mapper.px(k[0], k[1] + cell)
        x1, y1 = mapper.px(k[0] + cell, k[1])
        od.rectangle([x0, y0, x1, y1], fill=(40, 120, 240, a) if which != "jobs" else None)
    for k, v in grid_job.items():
        if v <= 0:
            continue
        a = int(30 + 130 * (v / maxj) ** 0.6)
        x0, y0 = mapper.px(k[0], k[1] + cell)
        x1, y1 = mapper.px(k[0] + cell, k[1])
        if which == "jobs":
            od.rectangle([x0, y0, x1, y1], fill=(230, 100, 40, a))
        else:
            od.rectangle([x0, y0, x1, y1], outline=(230, 90, 40, min(255, a + 60)), width=1)
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


def layer_transit(carto, draw, mapper, font, show_catchment=True, only=None):
    """画公交/轨道线路。`only` 给一组线名时**只画这些线**（单线配图用）。"""
    routes = carto.layer("routes")
    if only:
        want = set(only)
        routes = [f for f in routes if f.get("Name") in want]
    for f in routes:
        t = f.get("Transport") or "Bus"
        color = TRANSPORT_COLOR.get(t, (200, 0, 200))
        veh = int(f.get("Vehicle") or 0)
        w = 1.8 + min(4.0, veh / 4.0)
        parts = f.parts if f.parts and isinstance(f.parts[0], list) else [f.parts]
        allpts = [p for part in parts for p in part]
        for part in parts:
            draw_polyline(draw, mapper, part, color, w)
        if show_catchment and len(allpts) >= 2:
            # 沿线路等分取站：闭合环线用一圈长度，普通线只铺单程（与 city_report.py 口径一致）
            cum = [0.0]
            for i in range(1, len(allpts)):
                cum.append(cum[-1] + math.hypot(allpts[i][0] - allpts[i - 1][0],
                                                allpts[i][1] - allpts[i - 1][1]))
            total = cum[-1]
            if total > 0:
                closed = math.hypot(allpts[0][0] - allpts[-1][0],
                                    allpts[0][1] - allpts[-1][1]) < 50
                span = total if closed else total / 2.0
                n = max(2, int(f.get("Stop") or 2))
                for k in range(n):
                    target = span * k / (n - 1)
                    for i in range(1, len(cum)):
                        if cum[i] >= target:
                            seg = cum[i] - cum[i - 1] or 1.0
                            r = (target - cum[i - 1]) / seg
                            sx = allpts[i - 1][0] + (allpts[i][0] - allpts[i - 1][0]) * r
                            sy = allpts[i - 1][1] + (allpts[i][1] - allpts[i - 1][1]) * r
                            px, py = mapper.px(sx, sy)
                            rr = mapper.r_px(600.0)
                            draw.ellipse([px - rr, py - rr, px + rr, py + rr],
                                         outline=color, width=1)
                            draw.ellipse([px - 3, py - 3, px + 3, py + 3], fill=color)
                            break
        # 线名标签（放在线路中点）
        if allpts:
            mx, my = allpts[len(allpts) // 2]
            px, py = mapper.px(mx, my)
            label = "%s %s (%d车/%d人)" % (f.get("Name"), t, veh, int(f.get("Passenger") or 0))
            draw.text((px + 5, py - 12), label, fill=color, font=font)


def layer_contours(carto, draw, mapper, step=10.0):
    el = carto.elevation
    if el is None or el.array is None:
        return
    import numpy as np
    a = np.asarray(el.array, dtype="float32")
    b = carto.city_bounds()
    if not b:
        return
    x0, y0, x1, y1 = b
    c0, r0 = el.xy_to_pixel(x0, y1)
    c1, r1 = el.xy_to_pixel(x1, y0)
    c0, c1 = sorted((max(0, c0), min(a.shape[1] - 1, c1)))
    r0, r1 = sorted((max(0, r0), min(a.shape[0] - 1, r1)))
    sub = a[r0:r1 + 1, c0:c1 + 1]
    if sub.size == 0:
        return
    lo, hi = float(np.nanmin(sub)), float(np.nanmax(sub))
    lvl = math.floor(lo / step) * step
    while lvl <= hi:
        mask = (sub >= lvl) & (sub < lvl + step * 0.12)
        ys, xs = np.nonzero(mask)
        for k in range(0, len(xs), 3):
            wx = el.x0 + (c0 + xs[k]) * el.dx
            wy = el.y0 - (r0 + ys[k]) * el.dy
            px, py = mapper.px(wx, wy)
            draw.point((px, py), fill=(200, 190, 170))
        lvl += step


def make_map(carto, out_path, layers, width=2200, height=2200, cell=400.0,
             highlight=None, title_note=None, named_road=None, road_interval=None):
    from PIL import Image, ImageDraw
    bounds = carto.built_bounds() or carto.city_bounds()
    if not bounds:
        raise SystemExit("无法确定城市范围（数据为空？）")
    # 留一点边距
    x0, y0, x1, y1 = bounds
    mx = (x1 - x0) * 0.05 + 100
    my = (y1 - y0) * 0.05 + 100
    bounds = (x0 - mx, y0 - my, x1 + mx, y1 + my)
    mapper = Mapper(bounds, width, height)
    img = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(img)
    font = get_font(max(13, width // 110))
    small = get_font(max(11, width // 150))

    _unlocked_rings = 0
    if "unlocked" in layers:
        # ⭐ 打底层：**精确的已解锁区域边界**（未解锁压成浅灰）。
        # 必须最先画，且本层返回**新的**图像对象 —— 必须接住并重建 draw。
        img, _unlocked_rings = layer_unlocked_boundary(carto, draw, mapper, img)
        draw = ImageDraw.Draw(img)
    if "terrain" in layers:
        # 注意：本层返回**新的**图像对象（逐像素改色），必须接住并重建 draw，
        # 否则地形图层不会出现在最终图上（曾因丢掉返回值导致整张图空白）。
        img, _bstats = layer_buildability(carto, draw, mapper, img)
        draw = ImageDraw.Draw(img)
    if "contours" in layers:
        layer_contours(carto, draw, mapper)
    if "zoning" in layers:
        img = layer_zoning(carto, draw, mapper, img)
        draw = ImageDraw.Draw(img)
    if "density" in layers:
        img = layer_density(carto, draw, mapper, img, cell=cell)
        draw = ImageDraw.Draw(img)
    _served = None
    _cmap = None
    if "clusters" in layers:
        # 第一遍：只画组团**色块**（垫在路网/线网之下，作为底图分区）
        try:
            from analysis.city_reports import ClusterMap as _CM
            _cmap = _CM(carto)
        except Exception:
            _cmap = None
        if _cmap is not None and not _cmap.single:
            layer_clusters(carto, draw, mapper, small, cmap=_cmap, fills=True, labels=False)
    if "roads" in layers:
        # 公交建议配图用 "arterial"：**只画高速/大路/主干 + 铁路地铁**，
        # 不画支路 —— 图更干净，且"主干道必须画对"这件事在图上可核验。
        layer_roads(carto, draw, mapper,
                    min_level=("Medium" if "arterial" in layers else None))
    if "named-road" in layers and named_road:
        # ⭐ 具名道路：**按连通段分段画**（绝不把同名路段首尾相接），
        # 可只画其中一个沿线区间 —— 这是"xx路沿线 s₁–s₂ 区间"的图上依据。
        layer_named_road(carto, draw, mapper, named_road,
                         interval=road_interval, width=4.0)
    if "transit" in layers or "catchment" in layers or highlight:
        layer_transit(carto, draw, mapper, small,
                      show_catchment=("catchment" in layers),
                      only=highlight)
    if highlight:
        # 高亮线画在所有内容之上，确保"这条线"是图上第一眼看到的东西
        layer_highlight_routes(carto, draw, mapper, highlight)
    if _cmap is not None and not _cmap.single:
        # 第二遍：**标签画在最上层**（白底文字框），否则会被线网压掉
        _served = layer_clusters(carto, draw, mapper, small, cmap=_cmap,
                                 fills=False, labels=True)
    if "unlocked" in layers and _unlocked_rings:
        # ⭐ 边界线**再画一遍在最上层**（白描边 + 深色主线）——
        # 否则会被地形/分区/路网盖住，就失去"划清范围"的意义了。
        draw_unlocked_outline(carto, draw, mapper,
                              width=1.0 if width >= 1200 else 0.7)

    # 图例 + 标题
    cjk_ok = has_cjk_font()
    title = "CSL2 城市诊断图" if cjk_ok else "CSL2 city diagnostic map (CJK font missing)"
    draw.text((mapper.pad, 8), title, fill=(20, 20, 20), font=font)
    pop = carto.total_population()
    jobs = carto.total_jobs()
    sub = ("人口 %s / 岗位 %s   |   图层：%s   |   网格 %d m" %
           (int(pop), int(jobs), ",".join(layers), int(cell))) if cjk_ok else \
          ("pop %s / jobs %s | layers: %s | grid %dm" %
           (int(pop), int(jobs), ",".join(layers), int(cell)))
    draw.text((mapper.pad, 8 + font.size + 4), sub, fill=(90, 90, 90), font=small)
    # 图例按"实际画了什么"生成，避免列出图上根本看不见的类别
    legend = road_legend_items(carto, min_level=("Medium" if "arterial" in layers else None))
    # 地形图例放在最前（它是打底层，读图顺序应先看地形再看路网）；组团图例更前
    terr_items = list(BUILD_LEGEND) if "terrain" in layers else []
    cl_items = cluster_legend(_served) if _served is not None else []
    used_modes = [t for t in TRANSPORT_COLOR if t in
                  set(f.get("Transport") for f in carto.layer("routes"))]
    if "unlocked" in layers and _unlocked_rings:
        legend = legend + [("已解锁区边界", (38, 38, 46))]
    # ⚠️ 行距必须用**真实步长**：原来按固定 12 px 估算高度，
    # 而实际每行是 `12 + small.size`（≈25 px）→ 11 项就会**跑出画布并互相压字**。
    step = 12 + small.size
    all_items = cl_items + terr_items + legend
    n_total = len(all_items) + len(used_modes)
    ly = height - mapper.pad - step * n_total
    for name, color in all_items:
        draw.rectangle([mapper.pad, ly, mapper.pad + 18, ly + 8], fill=color)
        draw.text((mapper.pad + 24, ly - 3), name, fill=(60, 60, 60), font=small)
        ly += step
    for t in used_modes:
        draw.rectangle([mapper.pad, ly, mapper.pad + 18, ly + 8], fill=TRANSPORT_COLOR[t])
        draw.text((mapper.pad + 24, ly - 3), "线路：" + t, fill=(60, 60, 60), font=small)
        ly += step

    img.save(out_path)
    return out_path


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--carto", default=None,
                    help="Carto 导出目录；不给则自动查找常见目录名")
    ap.add_argument("--out", default="city_map.png")
    ap.add_argument("--layers", default="roads,arterial",
                    help="图层（逗号分隔）。默认 **roads,arterial** —— "
                         "只画高速/大路/主干+铁路地铁，**不画支路**："
                         "辅助图不必画全部路网，但画出来的必须正确。"
                         "要看完整肌理再加 `roads`（去掉 arterial）。"
                         "可用：unlocked/terrain/arterial/clusters/roads/transit/catchment/density/zoning/contours"
                         "/named-road（配合 --named-road、--road-interval）")
    ap.add_argument("--size", type=int, default=2200)
    ap.add_argument("--cell", type=float, default=400.0)
    ap.add_argument("--highlight", default=None,
                    help="高亮指定线路（逗号分隔线名）——单线建议配图用。"
                         "会给该线单独出图，其余线路淡化")
    ap.add_argument("--named-road", default=None,
                    help="高亮一条**具名道路**（如 `繁荣路`）。"
                         "按**连通段**分段画，不会把同名路段错误连成一条线")
    ap.add_argument("--road-interval", default=None,
                    help="只画该路的某个**沿线区间**，格式 s1:s2（米，沿主连通段自起点起算）。"
                         "配合 --named-road 使用 —— 这是'xx路沿线 s₁–s₂ 区间'的图上依据")
    a = ap.parse_args(argv)
    layers = [s.strip() for s in a.layers.split(",") if s.strip()]
    hl = [s.strip() for s in (a.highlight or "").split(",") if s.strip()] or None
    interval = None
    if a.road_interval:
        try:
            s1, s2 = [float(v) for v in a.road_interval.replace(",", ":").split(":")[:2]]
            interval = (s1, s2)
        except ValueError:
            print("--road-interval 格式应为 s1:s2，收到 %r" % a.road_interval)
            return 2
    carto_dir = a.carto or find_carto_dir()
    if not carto_dir:
        print("找不到 Carto 导出目录，请用 --carto 指定。")
        return 2
    if not a.carto:
        print("自动识别到 Carto 目录：%s" % carto_dir)
    carto = CartoData(carto_dir)
    p = make_map(carto, a.out, layers, width=a.size, height=a.size, cell=a.cell,
                 highlight=hl, named_road=a.named_road, road_interval=interval)
    print("written:", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
