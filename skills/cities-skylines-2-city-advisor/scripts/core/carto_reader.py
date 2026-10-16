#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
carto_reader.py —— 读取 Carto Mod 导出的城市数据（Shapefile / GeoJSON + GeoTIFF），
                 不依赖 geopandas / rasterio / shapely，只用标准库 + numpy + Pillow。

为什么自己写
------------
本机 Python 环境没有 geopandas / rasterio / shapely，且沙箱里 pip 不可用。
Carto 导出的数据量很小（几千个要素、4096² 栅格），用纯 Python 解析 DBF/SHP
完全够用，也便于在别的机器上复现。

支持的输入（Carto 导出目录）——**两种布局都支持，自动识别**
-----------------------------------------------------------
    新版（2026-10 起）：
        <Carto>/GeoJSON/<城市名>_<图层名>.json     矢量要素（UTF-8，坐标为归一化值）
        <Carto>/GeoTIFF/*.tif                      高程 / 水深栅格
    旧版：
        <Carto>/Shapefile/*.shp|.dbf|.shx         矢量要素（属性表 GBK，坐标 EPSG:32631）
        <Carto>/GeoTIFF/*.tif                      高程 / 水深栅格

⚠️ **新版 GeoJSON 没有 CRS，坐标是归一化值**，必须乘以 `GEOJSON_SCALE` 换算成米；
该值由「Network_Centerline 的几何长度 ÷ 属性 `Length`（米）」标定，
实测 1732 条样本中位 = **111006 m / 坐标单位**（四分位 110696–111522，线性成立）。
换算后坐标的**相对几何关系与旧版一致**，因此所有基于欧氏距离的分析口径不变。
另：新字段名（Address_District / Address_Street / Address_Number）会翻译成旧名
（Addr_dist / Addr_strt / Addr_nmbr），建筑层的 `Zone` 会补成 `Zoning`，
**使既有分析脚本无需改动**。

用法
----
    from carto_reader import CartoData
    c = CartoData(r"C:\\...\\Carto")
    c.roads            # list[Feature]  路网中心线（含 Lane / Limit / Category）
    c.zoning           # 分区多边形
    c.buildings        # 建筑多边形（含 Resident / Employee）
    c.routes           # 公交/轨道线路（含 Passenger / Vehicle / Stop / Length）
    c.areas            # 行政区 + 地图格子
    c.pois             # POI
    c.elevation        # numpy 2D 数组 (m)
    c.depth            # numpy 2D 数组 (m)

坐标系统：EPSG:32631（UTM 31N），单位米。CSL2 城市坐标即此平面坐标，
可直接做欧氏距离计算（城区尺度下误差可忽略）。
"""

import math
import os
import struct
import time

try:
    import numpy as np
except Exception:  # noqa: BLE001
    np = None

# ----------------------------------------------------------------------------- GeoJSON（新版导出）

#: 新版 GeoJSON 的坐标 → 米 换算系数（见模块 docstring 的标定说明）。
GEOJSON_SCALE = 111006.1

#: 新字段名 → 旧字段名（让既有脚本不用改）
_GJ_RENAME = {
    "Address_District": "Addr_dist",
    "Address_Street": "Addr_strt",
    "Address_Number": "Addr_nmbr",
}

#: 新版建筑层的 `Zone` 是**细分的资产分区名**（如「欧洲高密度住宅」「高密度办公楼」），
#: 而分析脚本（§2/§9/§11/§12）按**英文主类**（Residential / Office / ...）分组。
#: 这里做一次映射，把主类写回 `Zoning`，细节名保留在 `ZoneName`。
#: 顺序有意义：先匹配更具体的模式（如"商住"要在"商业/住宅"之前判）。
_GJ_ZONE_RULES = (
    (r"商住|混合型住宅", "Residential, Commercial"),
    (r"办公|写字楼", "Office"),
    (r"工业|采矿|农业区|采石|林业|石油", "Industrial"),
    (r"商业|商店|零售", "Commercial"),
    (r"住宅|公寓|廉租|四合院", "Residential"),
)

#: 新版分区图斑的 `Density` 字段（Low/Medium/High/Generic）→ 中文密度词，
#: 使报告里按「低/中/高密度」做的判定对**规划图斑**也成立（旧版只能从 Name 正则猜）。
_GJ_DENSITY_CN = {"Low": "低密度", "Medium": "中密度", "High": "高密度"}


def _gj_zone_category(name):
    """把细分分区名归到英文主类；认不出返回 None。"""
    import re as _re
    if not name:
        return None
    for pat, cat in _GJ_ZONE_RULES:
        if _re.search(pat, name):
            return cat
    return None


def _gj_flatten(geom):
    """把 GeoJSON geometry 拆成 (几何类型, [环/线, ...])；坐标此时仍是归一化值。"""
    if not isinstance(geom, dict):
        return None, None
    gt = geom.get("type")
    cs = geom.get("coordinates")
    if cs is None:
        return None, None
    if gt == "Polygon":
        return "polygon", [r for r in cs if len(r) >= 3]
    if gt == "MultiPolygon":
        return "polygon", [r for poly in cs for r in poly if len(r) >= 3]
    if gt == "LineString":
        return "line", [cs] if len(cs) >= 2 else []
    if gt == "MultiLineString":
        return "line", [ln for ln in cs if len(ln) >= 2]
    if gt == "Point":
        return "point", [[cs]]
    if gt == "MultiPoint":
        return "point", [[p for p in cs]]
    return None, None


def read_geojson(path, layer_key=None, scale=None, origin=None):
    """读 Carto 新版 GeoJSON 导出，返回 list[Feature]（坐标已换算为米）。

    path     : GeoJSON 文件路径
    layer_key: 图层键（buildings / roads / ...），用于做字段适配
    scale    : 米/坐标单位；None → 用 GEOJSON_SCALE
    origin   : (ox, oy) 平移原点（归一化坐标）；None → 用本文件路网 bbox 左下角
    """
    import json
    with open(path, encoding="utf-8-sig") as f:
        d = json.load(f)
    raw = d.get("features") or d.get("Features") or []
    s = float(scale) if scale else GEOJSON_SCALE

    if origin is None:
        gx, gy = [], []
        for f_ in raw:
            _gt, parts = _gj_flatten(f_.get("geometry") or {})
            if not parts:
                continue
            for part in parts:
                for p in part:
                    gx.append(p[0])
                    gy.append(p[1])
        origin = (min(gx), min(gy)) if gx else (0.0, 0.0)
    ox, oy = origin

    feats = []
    for i, f_ in enumerate(raw):
        gt, parts = _gj_flatten(f_.get("geometry") or {})
        if not parts:
            continue
        props = dict(f_.get("properties") or {})
        for new, old in _GJ_RENAME.items():
            if new in props and old not in props:
                props[old] = props[new]
        if layer_key == "buildings":
            z = props.get("Zone")
            if z:
                props["ZoneName"] = z          # 保留细分的资产分区名
                cat = _gj_zone_category(z)
                if cat:
                    # 建筑层的 Zone 才是真实分区；旧脚本读 Zoning
                    props["Zoning"] = cat
                else:
                    props["Zoning"] = z
                props["Zone"] = props["Zoning"]
            props.setdefault("Addr_dist", props.get("Address_District"))
        if layer_key == "zoning":
            # 图斑的 Zoning 已是英文主类；把 Density 翻成中文密度词，
            # 让"低/中/高密度"判定对规划图斑也成立
            d = props.get("Density")
            if d:
                props["DensityCN"] = _GJ_DENSITY_CN.get(d, d)
        if layer_key == "roads" and not props.get("Name"):
            props["Name"] = props.get("Asset")

        scaled = [[((p[0] - ox) * s, (p[1] - oy) * s) for p in part] for part in parts]
        allp = [p for part in scaled for p in part]
        xs = [p[0] for p in allp]
        ys = [p[1] for p in allp]
        feats.append(Feature(i, gt, scaled,
                             (min(xs), min(ys), max(xs), max(ys)), props))
    return feats


def find_geojson(carto_dir, stem):
    """在 <Carto>/GeoJSON（或 <Carto> 本身，或子目录）里找文件名含 stem 的 .json。

    新版 Carto 的文件名带城市名前缀（如 `江东_Network_Centerline.json`），
    所以用"包含 stem"而不是"等于 stem"来匹配。返回路径或 None。
    """
    cands = []
    for d in (os.path.join(carto_dir, "GeoJSON"), carto_dir):
        if os.path.isdir(d):
            try:
                for fn in os.listdir(d):
                    if fn.lower().endswith(".json") and stem in fn:
                        cands.append(os.path.join(d, fn))
            except OSError:
                pass
    if not cands:
        # 再扫一层子目录
        try:
            for entry in os.listdir(carto_dir):
                sub = os.path.join(carto_dir, entry)
                if os.path.isdir(sub):
                    for fn in os.listdir(sub):
                        if fn.lower().endswith(".json") and stem in fn:
                            cands.append(os.path.join(sub, fn))
        except OSError:
            pass
    if not cands:
        return None
    # 同类多个时取最大的（最完整）
    cands.sort(key=lambda p: -os.path.getsize(p))
    return cands[0]


# ----------------------------------------------------------------------------- DBF


def _decode_text(b, encodings=("utf-8", "gbk", "latin-1")):
    for enc in encodings:
        try:
            return b.decode(enc).strip()
        except Exception:
            continue
    return b.decode("latin-1", "ignore").strip()


def read_dbf(path):
    """读 DBF，返回 (fields, records)。fields=[(name,type,len,dec)]，records=list[dict]。"""
    with open(path, "rb") as f:
        d = f.read()
    if len(d) < 32:
        return [], []
    nrec, hlen, rlen = struct.unpack("<IHH", d[4:12])
    fields = []
    i = 32
    while i < len(d) and d[i] != 0x0D:
        name = d[i:i + 11].split(b"\x00")[0].decode("latin-1").strip()
        ftype = chr(d[i + 11])
        flen = d[i + 16]
        fdec = d[i + 17]
        fields.append((name, ftype, flen, fdec))
        i += 32
    records = []
    for r in range(nrec):
        off = hlen + r * rlen
        rec = d[off:off + rlen]
        if len(rec) < rlen or rec[:1] == b"*":
            continue
        vals = {}
        p = 1
        for name, ftype, flen, fdec in fields:
            raw = rec[p:p + flen]
            p += flen
            if ftype in ("N", "F"):
                s = raw.decode("latin-1").strip()
                try:
                    vals[name] = float(s) if s else None
                except ValueError:
                    vals[name] = None
            elif ftype == "L":
                vals[name] = raw.strip() in (b"T", b"t", b"Y", b"y")
            else:
                vals[name] = _decode_text(raw)
        records.append(vals)
    return fields, records


# ----------------------------------------------------------------------------- SHP


class Feature(object):
    """一个矢量要素：几何 + 属性。"""

    __slots__ = ("index", "geom_type", "parts", "bbox", "attrs", "centroid",
                 "clip_len", "clip_area")

    def __init__(self, index, geom_type, parts, bbox, attrs):
        self.index = index
        self.geom_type = geom_type  # 'polygon' | 'line' | 'point'
        self.parts = parts          # polygon: list[list[(x,y)]]；line: [(x,y)] 列表；point: [(x,y)]
        self.bbox = bbox            # (xmin, ymin, xmax, ymax)
        self.attrs = attrs
        self.centroid = None
        #: 由 `CartoData` 注入的"已解锁范围内长度/面积"覆写；None 表示用全长。
        #: 这样**所有既有 `line_length()` / `polygon_area()` 调用点自动获得裁剪口径**，
        #: 不必逐个改分析函数（也避免漏改）。
        self.clip_len = None
        self.clip_area = None

    # --- 便捷属性 ---
    def get(self, key, default=None):
        return self.attrs.get(key, default)

    def __getitem__(self, key):
        return self.attrs[key]

    def __repr__(self):
        return "<Feature %s %s %r>" % (self.geom_type, self.attrs.get("Name", ""), self.bbox)

    def compute_centroid(self):
        if self.centroid is not None:
            return self.centroid
        if self.geom_type == "polygon" and self.parts:
            ring = max(self.parts, key=len)
            a = cx = cy = 0.0
            n = len(ring)
            for i in range(n):
                x0, y0 = ring[i]
                x1, y1 = ring[(i + 1) % n]
                cross = x0 * y1 - x1 * y0
                a += cross
                cx += (x0 + x1) * cross
                cy += (y0 + y1) * cross
            if abs(a) > 1e-9:
                self.centroid = (cx / (3 * a), cy / (3 * a))
                return self.centroid
            xs = [p[0] for p in ring]
            ys = [p[1] for p in ring]
            self.centroid = (sum(xs) / len(xs), sum(ys) / len(ys))
        elif self.geom_type == "line" and self.parts:
            pts = [p for part in self.parts for p in part]
            if not pts:
                self.centroid = (0.0, 0.0)
            else:
                self.centroid = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
        elif self.parts:
            pts = self.parts[0] if isinstance(self.parts[0], list) else self.parts
            self.centroid = (pts[0][0], pts[0][1])
        else:
            self.centroid = (0.0, 0.0)
        return self.centroid

    def polygon_area(self):
        """多边形面积（m²），取最大环。**若已注入裁剪值，返回已解锁范围内的面积。**"""
        if self.clip_area is not None:
            return self.clip_area
        return self.full_polygon_area()

    def full_polygon_area(self):
        """未裁剪的多边形面积（m²）。"""
        if self.geom_type != "polygon" or not self.parts:
            return 0.0
        total = 0.0
        for ring in self.parts:
            a = 0.0
            n = len(ring)
            for i in range(n):
                x0, y0 = ring[i]
                x1, y1 = ring[(i + 1) % n]
                a += x0 * y1 - x1 * y0
            total += abs(a) / 2.0
        return total

    def line_length(self):
        """折线长度（m）。**若已注入裁剪值，返回已解锁范围内的长度。**"""
        if self.clip_len is not None:
            return self.clip_len
        return self.full_line_length()

    def full_line_length(self):
        """未裁剪的折线长度（m）。"""
        if self.geom_type != "line":
            return 0.0
        total = 0.0
        for part in self.parts:
            for i in range(1, len(part)):
                total += math.hypot(part[i][0] - part[i - 1][0], part[i][1] - part[i - 1][1])
        return total

    def developed_area(self, cell=8.0):
        """该建筑的**实际占地**（m²，按 CSL2 的 8 m 开发栅格近似）。

        `polygon_area()` 往往也是栅格对齐的（实测建筑面积多为 64 的倍数），
        所以这里直接数"覆盖了哪些 8 m 格子 × 64 m²"，得到与分区图斑同口径的占地下限。
        """
        cells = set()
        for ring in self.parts:
            if len(ring) < 3:
                for x, y in ring:
                    cells.add((int(x // cell), int(y // cell)))
                continue
            xs = [p[0] for p in ring]
            ys = [p[1] for p in ring]
            i0, i1 = int(min(xs) // cell), int(max(xs) // cell)
            j0, j1 = int(min(ys) // cell), int(max(ys) // cell)
            if (i1 - i0 + 1) * (j1 - j0 + 1) > 4_000_000:
                continue
            for i in range(i0, i1 + 1):
                cx = (i + 0.5) * cell
                for j in range(j0, j1 + 1):
                    cy = (j + 0.5) * cell
                    if _point_in_ring(cx, cy, ring):
                        cells.add((i, j))
        return len(cells) * cell * cell


def _point_in_ring(x, y, ring):
    """射线法判断点是否在多边形内。"""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > y) != (yj > y):
            xint = (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi
            if x < xint:
                inside = not inside
        j = i
    return inside


def read_shp(shp_path, dbf_path=None):
    """读 Shapefile（支持 Polygon / PolyLine / Point / MultiPoint）。"""
    with open(shp_path, "rb") as f:
        d = f.read()
    if len(d) < 100:
        return []
    # 文件头 bbox
    _, recs = (None, None)
    if dbf_path and os.path.exists(dbf_path):
        _, recs = read_dbf(dbf_path)
    else:
        guess = os.path.splitext(shp_path)[0] + ".dbf"
        if os.path.exists(guess):
            _, recs = read_dbf(guess)
    feats = []
    pos = 100
    idx = 0
    n = len(d)
    while pos + 8 <= n:
        rec_no, content_len = struct.unpack(">II", d[pos:pos + 8])
        pos += 8
        end = pos + content_len * 2
        if end > n:
            break
        body = d[pos:end]
        pos = end
        attrs = recs[idx] if recs and idx < len(recs) else {}
        idx += 1
        if len(body) < 4:
            continue
        stype = struct.unpack("<i", body[0:4])[0]
        f = _parse_shape(stype, body, attrs)
        if f is not None:
            f.index = rec_no
            feats.append(f)
    return feats


def _parse_shape(stype, body, attrs):
    """解析单个 shape 记录。

    注意：Carto 导出的是 **Z 型几何**（PolyLineZ=13 / PolygonZ=15 / PointZ=11 …），
    其布局为 [BBox(4d)][NumParts][NumPoints][Parts][Points(XY)]，之后才是 Z 值数组。
    因此只取 XY 时，偏移量与对应的 2D 版本完全一致（type = stype - 10 即 2D 版本号）。
    """
    if stype == 0:
        return None
    base = stype - 10 if stype >= 11 else stype   # Z/M 型 → 2D 型
    if base == 1:  # Point
        x, y = struct.unpack("<dd", body[4:20])
        return Feature(0, "point", [[(x, y)]], (x, y, x, y), attrs)
    if base in (3, 5):  # PolyLine / Polygon
        nparts, npoints = struct.unpack("<ii", body[36:44])
        if nparts <= 0 or npoints <= 0:
            return None
        p = 44
        need = 4 * nparts + 16 * npoints
        if len(body) < p + need:
            return None
        part_idx = list(struct.unpack("<%di" % nparts, body[p:p + 4 * nparts]))
        p += 4 * nparts
        coords = struct.unpack("<%dd" % (npoints * 2), body[p:p + 16 * npoints])
        pts = [(coords[i * 2], coords[i * 2 + 1]) for i in range(npoints)]
        parts = []
        for i, start in enumerate(part_idx):
            stop = part_idx[i + 1] if i + 1 < len(part_idx) else npoints
            if 0 <= start < stop <= npoints:
                parts.append(pts[start:stop])
        if not parts:
            return None
        xs = [q[0] for q in pts]
        ys = [q[1] for q in pts]
        gt = "polygon" if base == 5 else "line"
        return Feature(0, gt, parts, (min(xs), min(ys), max(xs), max(ys)), attrs)
    if base == 8:  # MultiPoint
        npoints = struct.unpack("<i", body[36:40])[0]
        if npoints <= 0 or len(body) < 40 + 16 * npoints:
            return None
        coords = struct.unpack("<%dd" % (npoints * 2), body[40:40 + 16 * npoints])
        pts = [(coords[i * 2], coords[i * 2 + 1]) for i in range(npoints)]
        xs = [q[0] for q in pts]
        ys = [q[1] for q in pts]
        return Feature(0, "point", [pts], (min(xs), min(ys), max(xs), max(ys)), attrs)
    return None


# ----------------------------------------------------------------------------- GeoTIFF


class Raster(object):
    """极简 GeoTIFF：只取第一波段 + 地理参考（origin / pixel size）。"""

    def __init__(self, path):
        from PIL import Image

        self.path = path
        im = Image.open(path)
        self.size = im.size  # (w, h)
        self.mode = im.mode
        tags = im.tag_v2
        self.scale = tags.get(33550) or (1.0, 1.0, 1.0)   # ModelPixelScale
        self.tiepoint = tags.get(33922) or (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)  # ModelTiepoint
        try:
            arr = np.array(im) if np is not None else None
        except Exception:
            arr = None
        self.array = arr
        # 地理参考。**必须按 ModelTiepoint 的定义换算**：
        #   tiepoint = (i, j, 0, X, Y, 0) 表示"像素 (i, j) 的中心对应地理坐标 (X, Y)"，
        #   ModelPixelScale = (sx, sy, sz)。于是像素 (row, col) 的地理坐标为
        #       X = X_tie + (col - i) * sx
        #       Y = Y_tie - (row - j) * sy
        #   反解出栅格左上角（col=0, row=0）：
        #       x0 = X_tie - i * sx
        #       y0 = Y_tie + j * sy        ← 注意是 **加**
        #   ⚠️ 早期版本误把 tiepoint 的 X/Y 直接当左上角、且 y0 用减号，
        #      导致所有栅格整体偏移（实测本地栅格偏 21504 m、世界栅格偏 86016 m），
        #      使"建筑高程 vs 栅格高程"永远对不上。此处按规范修正。
        tpx, tpy = self.tiepoint[0], self.tiepoint[1]
        self.x0 = self.tiepoint[3] - tpx * self.scale[0]
        self.y0 = self.tiepoint[4] + tpy * self.scale[1]
        self.dx = self.scale[0]
        self.dy = self.scale[1]

    def bounds(self):
        """(xmin, ymin, xmax, ymax)，单位与栅格 CRS 一致（Carto 为 EPSG:32631 米）。"""
        w, h = self.size
        return (self.x0, self.y0 - h * self.dy, self.x0 + w * self.dx, self.y0)

    def xy_to_pixel(self, x, y):
        """地理坐标 → 像素 (col, row)。用 `floor`（`int()` 对负值会向零截断，是错的）。"""
        col = int(math.floor((x - self.x0) / self.dx))
        row = int(math.floor((self.y0 - y) / self.dy))
        return (col, row)

    def value_at(self, x, y):
        if self.array is None:
            return None
        col, row = self.xy_to_pixel(x, y)
        h, w = self.array.shape[:2]
        if 0 <= col < w and 0 <= row < h:
            return float(self.array[row, col])
        return None

    def sample_grid(self, xmin, ymin, xmax, ymax, step):
        """在指定范围内按 step(m) 采样，返回 (xs, ys, values 2D)。"""
        if self.array is None:
            return [], [], []
        cols = int((xmax - xmin) / step) + 1
        rows = int((ymax - ymin) / step) + 1
        xs = [xmin + i * step for i in range(cols)]
        ys = [ymax - j * step for j in range(rows)]
        out = []
        for yy in ys:
            line = []
            for xx in xs:
                line.append(self.value_at(xx, yy))
            out.append(line)
        return xs, ys, out


# ----------------------------------------------------------------------------- 数据容器

#: 导出目录的常见命名（Carto Mod 的导出目录名会随玩家习惯变化）
DEFAULT_DIR_NAMES = ("Carto_live", "Carto", "Carto_prev", "CartoData", "ModsData",
                     "Carto Export", "CartoExport")

#: 游戏内 Carto 的**默认导出位置**（Unity 游戏的 persistentDataPath）。
#: 一般情况下 Carto 会直接把 Shapefile/ GeoTIFF/ 写到这里，
#: 所以**不必手动复制**到别处 —— 让脚本直接读它即可。
GAME_CARTO_HINTS = (
    os.path.join(os.path.expanduser("~"), "AppData", "LocalLow", "Colossal Order",
                 "Cities Skylines II", "ModsData", "Carto"),
    os.path.join(os.path.expanduser("~"), "Library", "Application Support",
                 "Colossal Order", "Cities Skylines II", "ModsData", "Carto"),   # macOS
    os.path.join(os.path.expanduser("~"), ".config", "unity3d", "Colossal Order",
                 "Cities Skylines II", "ModsData", "Carto"),                     # Linux
)


def _is_carto_dir(p):
    """判断 p 是否是一个 Carto 导出目录（新版 GeoJSON 或旧版 Shapefile 均可）。"""
    if not p or not os.path.isdir(p):
        return False
    if os.path.isdir(os.path.join(p, "Shapefile")):
        return True
    if os.path.isdir(os.path.join(p, "GeoJSON")):
        return True
    # 两种子目录都没有时，只要目录里直接躺着图层文件也算
    try:
        for fn in os.listdir(p):
            if fn.lower().endswith((".shp", ".json")) and (
                    "Network_Centerline" in fn or "Building_Boundary" in fn):
                return True
    except OSError:
        pass
    return False


def find_game_carto_dir():
    """找**游戏自己写出**的 Carto 目录（默认位于 LocalLow\\Colossal Order\\...\\ModsData\\Carto）。

    用途：免去"Carto 导出 → 手动复制到工作区"这一步。找到多个候选时，
    返回**修改时间最新**的那个（即最近一次导出的）。
    新版 GeoJSON 布局与旧版 Shapefile 布局都识别。
    """
    ok = []
    for p in GAME_CARTO_HINTS:
        if not _is_carto_dir(p):
            continue
        try:
            newest = 0.0
            for d in ("GeoJSON", "Shapefile", "GeoTIFF"):
                sub = os.path.join(p, d)
                if os.path.isdir(sub):
                    for f in os.listdir(sub):
                        newest = max(newest, os.path.getmtime(os.path.join(sub, f)))
        except Exception:  # noqa: BLE001
            newest = 0.0
        ok.append((newest, p))
    if not ok:
        return None
    ok.sort(reverse=True)
    return ok[0][1]


def find_carto_dir(start=None, names=DEFAULT_DIR_NAMES, include_game_dir=True):
    """从 start（默认当前工作目录）附近找 Carto 导出目录。

    查找顺序：
      1. `start` 自身或其子目录（按 `names`）；
      2. 从 `start` 逐级向上；
      3. **游戏默认导出目录**（`find_game_carto_dir()`）—— 免去手动复制。

    返回第一个像 Carto 导出的候选路径（含 `GeoJSON/` 或 `Shapefile/`）；找不到返回 None。
    """
    start = os.path.abspath(start or os.getcwd())

    def ok(p):
        return _is_carto_dir(p)

    if ok(start):
        return start
    for n in names:
        p = os.path.join(start, n)
        if ok(p):
            return p
    cur = start
    for _ in range(6):
        parent = os.path.dirname(cur)
        if not parent or parent == cur:
            break
        cur = parent
        if ok(cur):
            return cur
        for n in names:
            p = os.path.join(cur, n)
            if ok(p):
                return p
        try:
            for entry in sorted(os.listdir(cur)):
                if entry.startswith("."):
                    continue
                p = os.path.join(cur, entry)
                if ok(p):
                    return p
        except OSError:
            pass
    # 最后才退回"游戏默认导出目录"，避免抢在工作区数据之前被选中
    if include_game_dir:
        g = find_game_carto_dir()
        if ok(g):
            return g
    return None


# ----------------------------------------------------------------------------- 存档（Saves）

#: CSL2 存档目录（Unity persistentDataPath/Saves/<SteamID>/*.cok）
GAME_SAVE_ROOTS = (
    os.path.join(os.path.expanduser("~"), "AppData", "LocalLow", "Colossal Order",
                 "Cities Skylines II", "Saves"),
    os.path.join(os.path.expanduser("~"), "Library", "Application Support",
                 "Colossal Order", "Cities Skylines II", "Saves"),
    os.path.join(os.path.expanduser("~"), ".config", "unity3d", "Colossal Order",
                 "Cities Skylines II", "Saves"),
)


def find_save_dir():
    """返回最近的 CSL2 存档目录（Saves\\<SteamID>），找不到返回 None。"""
    for root in GAME_SAVE_ROOTS:
        if not os.path.isdir(root):
            continue
        subs = [os.path.join(root, d) for d in os.listdir(root)
                if os.path.isdir(os.path.join(root, d))]
        if subs:
            subs.sort(key=lambda p: os.path.getmtime(p), reverse=True)
            return subs[0]
        return root
    return None


def read_save_metadata(cok_path):
    """读 `.cok` 存档的元数据（**它是 ZIP，元数据是纯 JSON**）。

    能拿到：城市名 / 人口 / 资金 / 游戏内日期 / 主题 / 地图名 / 启用的 Mod 列表。
    ⚠️ **拿不到**税率、建筑等级、公司利润、地价 —— 这些在 `*.SaveGameData` 里，
    是**未压缩的二进制 ECS 序列化数据**（实测其中只有系统/组件**名**是可读字符串，
    没有可搜索的"值"）→ 需要反序列化才能读，成本很高。详见 `references/70`。
    """
    import json
    import zipfile
    with zipfile.ZipFile(cok_path) as z:
        name = next((n for n in z.namelist() if n.endswith(".SaveGameMetadata")), None)
        if name is None:
            return None
        meta = json.loads(z.read(name).decode("utf-8-sig"))
    sd = meta.get("simulationDate") or {}
    return {
        "file": cok_path,
        "filename": os.path.basename(cok_path),
        "city": meta.get("cityName"),
        "population": meta.get("population"),
        "money": meta.get("money"),
        "xp": meta.get("xp"),
        "year": sd.get("year"), "month": sd.get("month"),
        "day": sd.get("day"), "hour": sd.get("hour"), "minute": sd.get("minute"),
        "theme": meta.get("theme"), "map": meta.get("mapName"),
        "mods": meta.get("modsEnabled") or [],
        "mtime": os.path.getmtime(cok_path),
    }


def save_game_clock(meta):
    """把存档元数据里的游戏内时间格式化成 `"2031-01-22 23:22"`（缺字段时用 `??`）。"""
    if not meta:
        return None
    y, mo = meta.get("year"), meta.get("month")
    d, h, mi = meta.get("day"), meta.get("hour"), meta.get("minute")
    if y is None and h is None:
        return None
    parts = "%s-%s" % (y if y is not None else "????",
                       "%02d" % mo if mo is not None else "??")
    if d is not None:
        parts += "-%02d" % d
    parts += " %s:%s" % ("%02d" % h if h is not None else "??",
                         "%02d" % mi if mi is not None else "00")
    return parts


def carto_export_time(carto_dir):
    """Carto 导出的**实际数据时间**：取 `GeoJSON/*.json` 与 `GeoTIFF/*.tif` 里**最新的 mtime**。

    ⚠️ **不要用目录 mtime**：`ModsData\\Carto\\` 这个目录的 mtime 会被
    **任何子项写入**（例如 `Styles/*.qml` 是另一时刻生成的样式文件）顶掉，
    实测因此把导出时间误判到 10 小时之后。**数据文件的 mtime 才是导出的时刻。**
    """
    newest = None
    for sub, pats in (("GeoJSON", (".json",)), ("GeoTIFF", (".tif", ".tiff"))):
        d = os.path.join(carto_dir, sub)
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if not f.lower().endswith(pats):
                continue
            try:
                m = os.path.getmtime(os.path.join(d, f))
            except OSError:
                continue
            if newest is None or m > newest:
                newest = m
    if newest is None:                      # 退回 Shapefile（旧版导出）
        d = os.path.join(carto_dir, "Shapefile")
        if os.path.isdir(d):
            for f in os.listdir(d):
                if f.lower().endswith((".shp", ".dbf", ".shx")):
                    try:
                        m = os.path.getmtime(os.path.join(d, f))
                    except OSError:
                        continue
                    if newest is None or m > newest:
                        newest = m
    return newest


def find_save_for_carto(carto, saves=None, window_hours=72.0, pop_lo=0.5, pop_hi=2.0):
    """把一份 Carto 导出对应到某个存档，从而**自动拿到它的游戏内时间**（默认路径，无需用户输入）。

    ⚠️ **现实约束（实测）**：Carto 的导出是**按需触发**的，与"保存游戏"**不耦合** ——
    实测某次导出（`2026-10-14 00:23`）前后最近的存档分别在 `10-10 22:28` 与 `10-14 13:07`，
    **导出时刻根本没有对应存档**。而且 Carto 的 GeoJSON **文件名不含城市名**。
    所以只能**推断**，规则如下（按优先级）：

      1. **人口合理性过滤**：`Carto 建筑人口 ÷ 存档 population` 必须落在 `[pop_lo, pop_hi]`。
         这一步用来排除"同机器上的其它城市"（实测其它城市的比值可到 0.42 / 2.6 / 4.3）。
         > ⚠️ 两者**口径不同**（存档含无家可归者等，且**导出与存档的时刻不同、城市还在长**），
         > 所以比值不会正好 1.0，实测同一座城可达 ~0.84。
      2. **取时间最接近的**：在通过 ① 的候选里，选 `|存档 mtime − 导出 mtime|` 最小的
         （**不分前后** —— 用户可能"先导出后保存"，也可能"先保存后导出"）。
      3. **窗口限制**：时间差 > `window_hours` 视为无效（默认 72 h）。

    返回 `(meta, why)`。`meta` 为 `None` 时 `why` 说明原因。
    `meta["_match"]` 带诊断信息（时间差 / 人口比值 / 置信度），**报告必须把它显示出来**，
    这样推断错了用户能一眼看出。
    """
    saves = saves if saves is not None else list_saves()
    if not saves:
        return None, "读不到任何存档（存档目录缺失或没有 .cok）"

    try:
        ref = carto_export_time(getattr(carto, "dir", None))
    except Exception:      # noqa: BLE001
        ref = None
    if ref is None:
        return None, ("**该目录里没有可读的数据文件**（`GeoJSON/*.json`、`GeoTIFF/*.tif`、"
                      "`Shapefile/*.shp` 都没有）→ 目录可能是空的或路径不对，"
                      "因此**无法推断导出时间**")

    try:
        pop = carto.total_population()
    except Exception:      # noqa: BLE001
        pop = None

    cands = []
    for m in saves:
        p = m.get("population")
        ratio = (pop / float(p)) if (pop and p) else None
        if ratio is not None and not (pop_lo <= ratio <= pop_hi):
            continue                       # ① 人口不合理 → 判为"别的城市"
        dt = abs(m["mtime"] - ref) / 3600.0
        if dt > window_hours:
            continue                       # ③ 超出时间窗口
        cands.append((dt, ratio, m))

    if not cands:
        return None, ("没有既满足人口合理、又在 %.0f 小时内的存档（导出时间 %s；"
                      "Carto 建筑人口合计 %s）。**请让玩家在导出画面前后保存一次，"
                      "或用 `--at` 显式给出时间。**"
                      % (window_hours,
                         time.strftime("%Y-%m-%d %H:%M", time.localtime(ref)), pop))

    cands.sort(key=lambda t: t[0])          # ② 时间最接近
    dt, ratio, best = cands[0]
    conf = "高" if dt <= 2 else ("中" if dt <= 24 else "低")
    best = dict(best)
    best["_match"] = {
        "hours_from_export": dt,
        "pop_ratio": ratio,
        "confidence": conf,
        "n_candidates": len(cands),
        "export_mtime": ref,
    }
    why = ("自动匹配：**%s**（游戏内 %s）｜导出与存档相差 %.1f 小时、人口比值 %s、"
           "置信度 **%s**%s"
           % (best.get("filename"), save_game_clock(best), dt,
              ("%.2f" % ratio) if ratio is not None else "—", conf,
              "" if conf != "低" else "（差得较远，建议**导出后立刻存档**以提高准确度）"))
    return best, why


def attach_game_time(carto, override=None, saves=None, window_hours=72.0):
    """**默认路径**：不给 `override` 时自动从存档推断游戏内时间。

    返回 `dict(time, hour, minute, band, is_peak, source, confidence, save, note)`。
    `high_confidence` 为真表示"推断可靠或用户显式给出"。
    """
    import time as _t
    out = {"time": None, "hour": None, "minute": None, "band": None,
           "is_peak": None, "source": None, "confidence": None,
           "note": None, "save": None, "high_confidence": False}
    if override:
        return out                      # 调用方自己解析（见 analysis.resolve_game_time）
    meta, why = find_save_for_carto(carto, saves=saves, window_hours=window_hours)
    if not meta:
        out["note"] = why
        return out
    m = meta.get("_match") or {}
    out.update({"hour": meta.get("hour"), "minute": meta.get("minute"), "save": meta,
                "source": "自动读取存档元数据（%s）" % why,
                "confidence": m.get("confidence"),
                "high_confidence": m.get("confidence") in ("高", "中")})
    out["time"] = save_game_clock(meta)
    return out


def list_saves(save_dir=None, limit=None):
    """列出存档及其元数据，按文件时间倒序。"""
    d = save_dir or find_save_dir()
    if not d or not os.path.isdir(d):
        return []
    out = []
    for f in os.listdir(d):
        if not f.lower().endswith(".cok"):
            continue
        try:
            m = read_save_metadata(os.path.join(d, f))
        except Exception:
            m = None
        if m:
            out.append(m)
    out.sort(key=lambda m: -m["mtime"])
    return out[:limit] if limit else out


class CartoData(object):
    """Carto 导出目录的统一入口，按需读取并缓存。"""
    LAYERS = {
        "roads": "Network_Centerline",
        "road_boundary": "Network_Boundary",
        "zoning": "Zoning_Boundary",
        "buildings": "Building_Boundary",
        "routes": "Route_Centerline",
        "areas": "Area_Boundary",
        "pois": "POI_Location",
    }

    def __init__(self, carto_dir):
        self.dir = carto_dir
        self.shp_dir = os.path.join(carto_dir, "Shapefile")
        self.gj_dir = os.path.join(carto_dir, "GeoJSON")
        self.tif_dir = os.path.join(carto_dir, "GeoTIFF")
        self._cache = {}
        self._gj_origin = None
        #: 实际使用的格式："geojson" / "shapefile" / "empty"，供报告自检提示
        self.format = None

    def _origin(self):
        """GeoJSON 归一化坐标的平移原点：取路网 bbox 左下角（用未缩放的原始值）。"""
        if self._gj_origin is None:
            p = find_geojson(self.dir, "Network_Centerline")
            ox = oy = 0.0
            if p:
                import json
                try:
                    with open(p, encoding="utf-8-sig") as f:
                        d = json.load(f)
                    gx, gy = [], []
                    for f_ in (d.get("features") or []):
                        _gt, parts = _gj_flatten(f_.get("geometry") or {})
                        for part in (parts or []):
                            for q in part:
                                gx.append(q[0])
                                gy.append(q[1])
                    if gx:
                        ox, oy = min(gx), min(gy)
                except Exception:  # noqa: BLE001
                    pass
            self._gj_origin = (ox, oy)
        return self._gj_origin

    def layer(self, key):
        if key in self._cache:
            return self._cache[key]
        name = self.LAYERS.get(key, key)
        feats = None
        # 优先新版 GeoJSON（带城市名前缀，用"包含"匹配）
        gj = find_geojson(self.dir, name)
        if gj:
            try:
                feats = read_geojson(gj, layer_key=key, origin=self._origin())
                if feats:
                    self.format = "geojson"
            except Exception:  # noqa: BLE001
                feats = None
        # 回退旧版 Shapefile
        if not feats:
            shp = os.path.join(self.shp_dir, name + ".shp")
            if os.path.exists(shp):
                feats = read_shp(shp)
                if feats:
                    self.format = "shapefile"
        self._cache[key] = feats or []
        return self._cache[key]

    def data_format(self):
        """返回实际数据格式，供报告 §0 数据自检显示。"""
        if self.format is None:
            self.layer("roads")
        return self.format or "empty"

    def __getattr__(self, item):
        if item in CartoData.LAYERS:
            return self.layer(item)
        raise AttributeError(item)

    # --- 栅格 ---
    def raster_path(self, name):
        """找栅格文件：新版 Carto 会带城市名前缀（`<城名>_Elevation.tif`），旧版没有。

        因此先试 `<name>.tif`，再试 `<任意前缀>_<name>.tif`。找不到返回 None。
        """
        exact = os.path.join(self.tif_dir, name + ".tif")
        if os.path.exists(exact):
            return exact
        if os.path.isdir(self.tif_dir):
            suffix = "_" + name + ".tif"
            for fn in sorted(os.listdir(self.tif_dir)):
                if fn.endswith(suffix):
                    return os.path.join(self.tif_dir, fn)
        return None

    def raster(self, name):
        key = "_raster_" + name
        if key not in self._cache:
            p = self.raster_path(name)
            self._cache[key] = Raster(p) if p else None
        return self._cache[key]

    @property
    def elevation(self):
        return self.raster("Elevation")

    @property
    def depth(self):
        return self.raster("Depth")

    @property
    def world_elevation(self):
        return self.raster("WorldElevation")

    # --- 派生 ---
    def districts(self):
        return [a for a in self.layer("areas") if a.get("Object") == "District"]

    def unlocked_tiles(self):
        return [a for a in self.layer("areas") if a.get("Object") == "MapTile" and a.get("Unlocked")]

    def city_bounds(self):
        """已解锁地块的并集 bbox；无地块数据时退回建筑范围。"""
        feats = self.unlocked_tiles() or self.layer("buildings")
        if not feats:
            return None
        xs0 = min(f.bbox[0] for f in feats)
        ys0 = min(f.bbox[1] for f in feats)
        xs1 = max(f.bbox[2] for f in feats)
        ys1 = max(f.bbox[3] for f in feats)
        return (xs0, ys0, xs1, ys1)

    def built_bounds(self):
        """有建筑的地块并集 bbox —— 更接近真实建成区（用于算路网密度）。"""
        feats = [f for f in self.unlocked_tiles()
                 if (f.get("Resident") or 0) > 0 or (f.get("Employee") or 0) > 0]
        if not feats:
            feats = self.layer("buildings")
        if not feats:
            return self.city_bounds()
        return (min(f.bbox[0] for f in feats), min(f.bbox[1] for f in feats),
                max(f.bbox[2] for f in feats), max(f.bbox[3] for f in feats))

    # --- 派生（带缓存：这些量在报告里被反复引用，重扫 1754 栋建筑是纯浪费） ---
    def _sum_attr(self, attr):
        key = "_sum_" + attr
        if key not in self._cache:
            self._cache[key] = sum(f.get(attr) or 0 for f in self.layer("buildings"))
        return self._cache[key]

    def total_population(self):
        """居民合计（已落地居民口径）。**注意与存档元数据的人口口径不同**，见 `references/70`。"""
        return self._sum_attr("Resident")

    def total_jobs(self):
        """岗位合计。"""
        return self._sum_attr("Employee")

    def populated_points(self):
        """有居民的建筑的 `(x, y, 居民数)` 列表 —— **一次算好，供各覆盖分析复用**。

        覆盖率类分析（站点覆盖 / 服务设施覆盖）都要"遍历人口建筑"，
        每次现算会重复调用 `compute_centroid` 并重建列表；这里统一缓存。
        """
        key = "_populated_points"
        if key not in self._cache:
            out = []
            for b in self.layer("buildings"):
                pop = b.get("Resident") or 0
                if pop > 0:
                    x, y = b.compute_centroid()
                    out.append((x, y, pop))
            self._cache[key] = out
        return self._cache[key]

    def unlocked_tiles(self):
        """**已解锁**的地图地块（`Object == 'MapTile'` 且 `Unlocked` 为真）。实测 37/232。"""
        key = "_unlocked_tiles"
        if key not in self._cache:
            self._cache[key] = [a for a in self.layer("areas")
                                if a.get("Object") == "MapTile" and a.get("Unlocked")]
        return self._cache[key]

    def unlocked_bounds(self):
        """已解锁范围的 bbox `(xmin, ymin, xmax, ymax)`（GeoJSON 坐标系）。"""
        t = self.unlocked_tiles()
        if not t:
            return None
        xs, ys = [], []
        for f in t:
            parts = f.parts if f.parts and isinstance(f.parts[0], list) else [f.parts]
            for part in parts:
                for x, y in part:
                    xs.append(x)
                    ys.append(y)
        return (min(xs), min(ys), max(xs), max(ys)) if xs else None

    def clipped_length(self, feature, unlocked_only=True):
        """要素落在**已解锁地块内**的长度（米）；`unlocked_only=False` 时返回全长。"""
        if not unlocked_only:
            return feature.full_line_length()
        self.apply_unlocked_clip()
        return feature.line_length()

    def apply_unlocked_clip(self):
        """把「已解锁范围内」的长度/面积**注入到各要素**（幂等，只做一次）。

        为什么这样做：分析函数里到处都在调 `f.line_length()` / `z.polygon_area()`。
        与其逐个改成 `carto.clipped_length(f)`（容易漏改、且以后新增分析又会忘），
        不如**在数据层注入一次**，让所有既有调用点自动获得正确口径。
        原始全长仍可用 `f.full_line_length()` / `f.full_polygon_area()` 取。
        """
        key = "_clip_applied"
        if self._cache.get(key):
            return self
        tiles = self.unlocked_tiles()
        if not tiles:
            self._cache[key] = True          # 无解锁信息 → 保持全长口径
            self._clip_note = "无 MapTile 解锁信息，里程按全长统计"
            return self
        idx = RegionIndex(tiles)
        for layer_key in ("roads", "road_boundary", "zoning"):
            for f in self.layer(layer_key):
                bb = f.bbox
                cand = idx.candidates(bb)
                if not cand:
                    # 完全在解锁范围外 → 长度/面积记 0
                    if f.geom_type == "line":
                        f.clip_len = 0.0
                    elif f.geom_type == "polygon":
                        f.clip_area = 0.0
                    continue
                if f.geom_type == "line":
                    f.clip_len = clip_length_to_features(f, tiles, index=idx)
                elif f.geom_type == "polygon":
                    # ⚡ 快速通道：分区图斑是 8 m 小格（实测 3 万多个），逐个做边求交很慢。
                    # 若该图斑的 bbox **完全落在某一个候选地块内部**（不与任何地块边相交），
                    # 它要么整体在内、要么整体在外 —— 直接判定，跳过昂贵的裁剪。
                    f.clip_area = _polygon_area_fast(f, tiles, cand)
        self._cache[key] = True
        self._clip_note = "里程/面积已裁剪到已解锁地块内（原始全长见 full_* 方法）"
        return self

    def clipped_parts(self, feature, unlocked_only=True):
        """折线**裁剪后**的几何（供绘制）：`list[list[(x,y)]]`。

        未解锁/地图外的部分会被切掉 —— 避免图上"画出城市之外的路"。
        `unlocked_only=False` 时返回原几何。
        """
        if not unlocked_only:
            return feature.parts
        key = "_clip_parts"
        cache = self._cache.get(key)
        if cache is None:
            cache = {}
            self._cache[key] = cache
        fid = id(feature)
        if fid not in cache:
            tiles = self.unlocked_tiles()
            if not tiles:
                cache[fid] = feature.parts
            else:
                if "_clip_region_index" not in self._cache:
                    self._cache["_clip_region_index"] = RegionIndex(tiles)
                cache[fid] = clip_line_parts_to_features(
                    feature, tiles, index=self._cache["_clip_region_index"])
        return cache[fid]

    def roads_with_flow(self):
        """有**机动车流量**的路段：`list[(Feature, volume, lane, limit, length_m)]`。

        新版 GeoJSON 的 `Network_Centerline` 带 `Volume`（该段车流量）与 `Lane`（车道数）。
        实测 **330 段 `Lane == 0`**（铁路 / 地铁 / 步道 / 部分水道）—— 它们没有机动车流量，
        必须排除，否则会把"没车道"误算成"极拥堵"。见 `references/70` §1.0.2。
        """
        key = "_roads_with_flow"
        if key not in self._cache:
            out = []
            for f in self.layer("roads"):
                lane = f.get("Lane") or 0
                if lane <= 0:
                    continue
                out.append((f, f.get("Volume") or 0.0, float(lane),
                            f.get("Limit") or 0.0, f.line_length()))
            self._cache[key] = out
        return self._cache[key]


# ----------------------------------------------------------------------------- 已解锁地块裁剪

def _point_in_ring(x, y, ring):
    """射线法：点是否在多边形环内（含边界的容差处理由调用方负责）。"""
    inside = False
    n = len(ring)
    if n < 3:
        return False
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-30) + xi):
            inside = not inside
        j = i
    return inside


def _point_in_feature(x, y, feat):
    """点是否在要素内：取面积最大的环作为外环，其余视为洞（Carto 的图斑极少有洞，够用）。"""
    parts = feat.parts
    if not parts:
        return False
    if not isinstance(parts[0], list):        # 退化：当成单环
        parts = [parts]
    if not _point_in_ring(x, y, max(parts, key=len)):
        return False
    for ring in parts:
        if ring is max(parts, key=len):
            continue
        if _point_in_ring(x, y, ring):
            return False                          # 落在洞里
    return True


def clip_length_to_features(feature, regions, tol=1e-6, index=None):
    """**把一条折线裁剪到若干多边形区域内**，返回区域内的长度（米）。

    为什么需要：高速/铁路的几何会伸到**未解锁地块之外**（实测高速仅 29.7% 落在已解锁地块内），
    按整个地图统计里程会**系统性高估**。规划建议只应针对已解锁范围。

    算法：对每个线段求它与区域边的交点 → 按参数 t 排序 → 逐子段取中点判定所属 →
    累加落在区域内的子段长度。**是精确裁剪，不是按比例估算。**

    `index` 为可选的 `RegionIndex`：只与该线段包围盒相交的区域求交，避免全量两两比较。
    """
    if feature.geom_type != "line" or not feature.parts:
        return 0.0
    if not regions:
        return 0.0
    inner = feature.parts if isinstance(feature.parts[0], list) else [feature.parts]
    # 先用包围盒快速排除：完全落在区域外的折线直接返回 0
    if index is not None:
        regions = index.candidates(feature.bbox) or []
        if not regions:
            return 0.0

    rings = []
    for r in regions:
        parts = r.parts
        if not parts:
            continue
        if not isinstance(parts[0], list):
            parts = [parts]
        rings.append(parts)

    total = 0.0
    for part in inner:
        for i in range(1, len(part)):
            x0, y0 = part[i - 1]
            x1, y1 = part[i]
            dx, dy = x1 - x0, y1 - y0
            seg_len = math.hypot(dx, dy)
            if seg_len <= tol:
                continue
            ts = [0.0, 1.0]
            for parts in rings:
                for ring in parts:
                    n = len(ring)
                    for k in range(n):
                        ax, ay = ring[k]
                        bx, by = ring[(k + 1) % n]
                        ex, ey = bx - ax, by - ay
                        den = dx * ey - dy * ex
                        if abs(den) < 1e-12:
                            continue                      # 平行
                        t = ((ax - x0) * ey - (ay - y0) * ex) / den
                        u = ((ax - x0) * dy - (ay - y0) * dx) / den
                        if -1e-9 <= t <= 1 + 1e-9 and -1e-9 <= u <= 1 + 1e-9:
                            ts.append(min(1.0, max(0.0, t)))
            ts = sorted(set(round(t, 9) for t in ts))
            for a, b in zip(ts, ts[1:]):
                if b - a <= 1e-9:
                    continue
                tm = (a + b) / 2.0
                mx, my = x0 + dx * tm, y0 + dy * tm
                for parts in rings:
                    hit = False
                    for ring in parts:
                        if _point_in_ring(mx, my, ring):
                            hit = True
                            break
                    if hit:
                        total += seg_len * (b - a)
                        break
    return total


def clip_polygon_area_to_features(feature, regions, index=None):
    """多边形落在若干区域**内**的面积（m²）—— 用于把分区图斑面积裁剪到已解锁范围。

    做法：把外环的每条边按与区域边的交点切成子段，取子段中点判定是否在区域内，
    对落在区域内的子段做**闭合的鞋带累加**（把子段端点连回起点形成扇形），
    得到的就是该环在区域内的面积。**对凸/凹多边形都成立**（扇形分解不依赖凸性）。
    """
    if feature.geom_type != "polygon" or not feature.parts:
        return 0.0
    parts = feature.parts if isinstance(feature.parts[0], list) else [feature.parts]
    outer = max(parts, key=len)
    if len(outer) < 3:
        return 0.0
    if index is not None:
        regions = index.candidates(feature.bbox) or []
        if not regions:
            return 0.0
    rings = []
    for r in regions:
        rp = r.parts
        if not rp:
            continue
        if not isinstance(rp[0], list):
            rp = [rp]
        rings.append(rp)

    def inside(x, y):
        for rp in rings:
            for ring in rp:
                if _point_in_ring(x, y, ring):
                    return True
        return False

    # 以环的第一个顶点为扇形中心（它在不在区域内都会在累加中被自然抵消）
    ox, oy = outer[0]
    sub_points = [(ox, oy)]
    n = len(outer)
    for i in range(n):
        x0, y0 = outer[i]
        x1, y1 = outer[(i + 1) % n]
        dx, dy = x1 - x0, y1 - y0
        ts = [0.0, 1.0]
        for rp in rings:
            for ring in rp:
                m = len(ring)
                for k in range(m):
                    ax, ay = ring[k]
                    bx, by = ring[(k + 1) % m]
                    ex, ey = bx - ax, by - ay
                    den = dx * ey - dy * ex
                    if abs(den) < 1e-12:
                        continue
                    t = ((ax - x0) * ey - (ay - y0) * ex) / den
                    u = ((ax - x0) * dy - (ay - y0) * dx) / den
                    if -1e-9 <= t <= 1 + 1e-9 and -1e-9 <= u <= 1 + 1e-9:
                        ts.append(min(1.0, max(0.0, t)))
        ts = sorted(set(round(t, 9) for t in ts))
        for a, b in zip(ts, ts[1:]):
            if b - a <= 1e-9:
                continue
            tm = (a + b) / 2.0
            mx, my = x0 + dx * tm, y0 + dy * tm
            if inside(mx, my):
                sub_points.append((x0 + dx * a, y0 + dy * a))
                sub_points.append((x0 + dx * b, y0 + dy * b))
    if len(sub_points) < 3:
        return 0.0
    # 鞋带公式（含闭合边：末点连回首点）
    a2 = 0.0
    for i in range(len(sub_points)):
        x0, y0 = sub_points[i]
        x1, y1 = sub_points[(i + 1) % len(sub_points)]
        a2 += x0 * y1 - x1 * y0
    return abs(a2) / 2.0


def _polygon_area_fast(feature, tiles, candidates):
    """裁剪多边形面积的**快速通道**：能整体判定就不做边求交。

    判据：若存在一个候选地块**完全包含该多边形的 bbox**，则该多边形整体在该地块内 → 直接返回原面积。
    否则才走逐边裁剪（`clip_polygon_area_to_features`）。
    实测分区图斑是 8 m 小格，绝大多数都能走快速通道，整体耗时从数十秒降到亚秒级。
    """
    bb = feature.bbox
    for t in candidates:
        tb = t.bbox
        if tb[0] <= bb[0] and tb[1] <= bb[1] and tb[2] >= bb[2] and tb[3] >= bb[3]:
            # bbox 被完全包住 —— 再确认多边形确实落在该地块内（取一个内部点验证）
            parts = feature.parts if isinstance(feature.parts[0], list) else [feature.parts]
            outer = max(parts, key=len)
            cx = sum(p[0] for p in outer) / len(outer)
            cy = sum(p[1] for p in outer) / len(outer)
            tparts = t.parts if t.parts and isinstance(t.parts[0], list) else [t.parts]
            if any(_point_in_ring(cx, cy, ring) for ring in tparts):
                return feature.full_polygon_area()
    return clip_polygon_area_to_features(feature, tiles)


def clip_line_parts_to_features(feature, regions, index=None):
    """返回折线**落在区域内**的那些子段：`list[list[(x,y)]]`。

    与 `clip_length_to_features()` 同一套求交逻辑，区别是这里**返回几何**而不是长度 ——
    供绘制使用：未解锁/地图外的路段不该画进图里，否则会"画出城市之外的路"。
    """
    if feature.geom_type != "line" or not feature.parts:
        return []
    if not regions:
        return []
    sel = regions
    if index is not None:
        sel = index.candidates(feature.bbox) or []
        if not sel:
            return []
    rings = []
    for r in sel:
        parts = r.parts
        if not parts:
            continue
        if not isinstance(parts[0], list):
            parts = [parts]
        rings.append(parts)

    out = []
    inner = feature.parts if isinstance(feature.parts[0], list) else [feature.parts]
    for part in inner:
        for i in range(1, len(part)):
            x0, y0 = part[i - 1]
            x1, y1 = part[i]
            dx, dy = x1 - x0, y1 - y0
            seg_len = math.hypot(dx, dy)
            if seg_len <= 1e-9:
                continue
            ts = [0.0, 1.0]
            for parts in rings:
                for ring in parts:
                    n = len(ring)
                    for k in range(n):
                        ax, ay = ring[k]
                        bx, by = ring[(k + 1) % n]
                        ex, ey = bx - ax, by - ay
                        den = dx * ey - dy * ex
                        if abs(den) < 1e-12:
                            continue
                        t = ((ax - x0) * ey - (ay - y0) * ex) / den
                        u = ((ax - x0) * dy - (ay - y0) * dx) / den
                        if -1e-9 <= t <= 1 + 1e-9 and -1e-9 <= u <= 1 + 1e-9:
                            ts.append(min(1.0, max(0.0, t)))
            ts = sorted(set(round(t, 9) for t in ts))
            for a, b in zip(ts, ts[1:]):
                if b - a <= 1e-9:
                    continue
                tm = (a + b) / 2.0
                mx, my = x0 + dx * tm, y0 + dy * tm
                for parts in rings:
                    if any(_point_in_ring(mx, my, ring) for ring in parts):
                        out.append([(x0 + dx * a, y0 + dy * a), (x0 + dx * b, y0 + dy * b)])
                        break
    return out


def dissolve_to_rings(features, prec=2):
    """把若干多边形**合并**成外轮廓（返回闭环列表）。

    用途：画"已解锁区域"的**精确边界**，而不是把每个地块各画一遍
    （那样看起来是一堆方块/斜块堆在一起）。

    原理：一组铺满区域的多边形，其**内部边**会被两个多边形各报一次，
    **边界边只出现一次** ⇒ `count == 1` 的边就是外轮廓；再把它们首尾相接成闭环。

    ⚠️ 实测 Carto 的 `MapTile` 是**不规则四边形**（不是正方形、也不在规则网格上，
    顶点数 5–17 不等），但它们**共用顶点且坐标精确相等** ——
    实测 0/1/2 位小数三种精度下结果完全一致（39 个已解锁地块 → 49 条唯一边）。
    因此直接按坐标元组比较即可，不需要容差。

    `prec`：顶点取整小数位（默认 2），仅用于抵御浮点噪声。
    """
    from collections import Counter, defaultdict
    cnt = Counter()
    for f in features:
        parts = f.parts if f.parts and isinstance(f.parts[0], list) else [f.parts]
        for ring in parts:
            pts = [(round(x, prec), round(y, prec)) for x, y in ring]
            if len(pts) > 1 and pts[0] == pts[-1]:
                pts = pts[:-1]                      # 去掉闭合重复点
            n = len(pts)
            if n < 3:
                continue
            for i in range(n):
                a, b = pts[i], pts[(i + 1) % n]
                cnt[(a, b) if a <= b else (b, a)] += 1
    boundary = [e for e, c in cnt.items() if c == 1]
    if not boundary:
        return []
    # 用"未使用的边集合"驱动，**每条边只消费一次** ⇒ 不可能无限循环
    adj = defaultdict(list)
    for a, b in boundary:
        adj[a].append(b)
        adj[b].append(a)
    unused = set(boundary)
    rings = []
    while unused:
        a, b = next(iter(unused))
        unused.discard((a, b))
        ring = [a, b]
        cur = b
        while True:
            nxt = None
            for v in adj.get(cur, ()):
                if v == cur:
                    continue
                e = (cur, v) if cur <= v else (v, cur)
                if e in unused:
                    nxt = v
                    unused.discard(e)
                    break
            if nxt is None:
                break
            ring.append(nxt)
            cur = nxt
            if cur == ring[0]:
                break
        if len(ring) >= 4:
            rings.append(ring)
    return rings


class RegionIndex(object):
    """把区域（地块）按包围盒放进粗网格，用于"这条线可能穿过哪些地块"的快速筛选。"""

    def __init__(self, regions, cell=1000.0, bbox_of=None):
        self.cell = float(cell)
        self.buckets = {}
        self.regions = list(regions)
        for r in self.regions:
            bb = bbox_of(r) if bbox_of else r.bbox
            for k in self._keys(bb):
                self.buckets.setdefault(k, []).append((r, bb))

    def _keys(self, bb):
        x0, y0, x1, y1 = bb
        c = self.cell
        for ix in range(int(math.floor(x0 / c)), int(math.floor(x1 / c)) + 1):
            for iy in range(int(math.floor(y0 / c)), int(math.floor(y1 / c)) + 1):
                yield (ix, iy)

    def candidates(self, bb):
        """与给定 bbox 相交的区域（去重，按出现顺序稳定）。"""
        x0, y0, x1, y1 = bb
        seen = {}
        for k in self._keys(bb):
            for r, rbb in self.buckets.get(k, ()):
                if id(r) in seen:
                    continue
                if rbb[0] <= x1 and rbb[2] >= x0 and rbb[1] <= y1 and rbb[3] >= y0:
                    seen[id(r)] = r
        return list(seen.values())





class GridIndex(object):
    """把一组点放进网格，用于快速"半径内要素"查询。"""

    def __init__(self, points, cell=200.0):
        self.cell = float(cell)
        self.buckets = {}
        self.points = points  # list[(x, y, payload)]
        for x, y, payload in points:
            self.buckets.setdefault(self._key(x, y), []).append((x, y, payload))

    def _key(self, x, y):
        return (int(math.floor(x / self.cell)), int(math.floor(y / self.cell)))

    def within(self, x, y, radius):
        """返回半径内 (dist, payload)，按距离升序。"""
        r = float(radius)
        span = int(math.ceil(r / self.cell))
        cx, cy = self._key(x, y)
        out = []
        for i in range(cx - span, cx + span + 1):
            for j in range(cy - span, cy + span + 1):
                for px, py, payload in self.buckets.get((i, j), ()):
                    dist = math.hypot(px - x, py - y)
                    if dist <= r:
                        out.append((dist, payload))
        out.sort(key=lambda t: t[0])
        return out


def build_building_index(carto):
    pts = []
    for b in carto.layer("buildings"):
        cx, cy = b.compute_centroid()
        pts.append((cx, cy, b))
    return GridIndex(pts)


def build_poi_index(carto):
    pts = []
    for p in carto.layer("pois"):
        cx, cy = p.compute_centroid()
        pts.append((cx, cy, p))
    return GridIndex(pts)


def route_stop_points(carto, route_feature):
    """线路的车站几何点（Route 图层的线要素端点／顶点）。"""
    f = route_feature
    if f.geom_type == "line":
        pts = [p for part in f.parts for p in part]
        if len(pts) < 2:
            return []
        return pts
    return [f.compute_centroid()]


def nearest_distance(index, x, y, radius=5000.0):
    hits = index.within(x, y, radius)
    return hits[0][0] if hits else None
