#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""carto_reader_gj.py —— 读取 Carto 新版 GeoJSON 导出，并兼容旧版 Shapefile 导出的字段名。

为什么需要它
------------
2026-10-13 起 Carto 的导出布局变了：
    旧： <Carto>/Shapefile/*.shp + <Carto>/GeoTIFF/*.tif      属性表 GBK，坐标 EPSG:32631（米）
    新： <Carto>/GeoJSON/<城市名>_*.json + <Carto>/GeoTIFF/*.tif   属性 UTF-8，坐标为**归一化值**

新坐标没有 CRS，需要标定比例。实测：取 Network_Centerline 的 LineString 几何长度与
属性 `Length`（米）之比，1732 条样本中位 = **111006 m / 坐标单位**
（p25=110696，p75=111522，四分位区间很窄 → 线性关系成立）。
因此本模块把所有坐标乘以该比例，换算成"米"，从而与旧版分析脚本口径一致。

字段名适配：新导出的字段名与旧版不同，这里统一翻译成旧名，使既有脚本无需改动：
    Address_District -> Addr_dist      Address_Street -> Addr_strt
    Address_Number   -> Addr_nmbr      Zone           -> Zoning（建筑层的真实分区）
    Density          -> 额外保留（Low/Medium/High，比从中文名正则判断可靠）

用法与旧版完全一致：
    from carto_reader_gj import CartoDataGJ
    c = CartoDataGJ(r"...\\ModsData\\Carto")
    c.layer("buildings") / c.layer("roads") / c.layer("zoning") / c.layer("routes") ...
"""
import json
import math
import os
import struct

try:
    import numpy as np
except Exception:  # noqa: BLE001
    np = None

# ------------------------------------------------------------------ 常量
SCALE = 111006.1          # 米 / 坐标单位（由 Length 字段标定，见模块 docstring）
SHP_ENC = ("utf-8", "gbk", "latin-1")

LAYER_FILE = {
    "roads": "Network_Centerline",
    "road_boundary": "Network_Boundary",
    "zoning": "Zoning_Boundary",
    "buildings": "Building_Boundary",
    "routes": "Route_Centerline",
    "areas": "Area_Boundary",
    "pois": "POI_Location",
}

# 新字段名 -> 旧字段名（让既有脚本不用改）
RENAME = {
    "Address_District": "Addr_dist",
    "Address_Street": "Addr_strt",
    "Address_Number": "Addr_nmbr",
}

# 建筑层用真实分区字段覆盖旧的 Zoning
BUILDING_ZONE_FIELD = "Zone"


# ------------------------------------------------------------------ 几何
class Feature(object):
    """与旧版 carto_reader.Feature 同接口，坐标已换算为米。"""

    __slots__ = ("index", "geom_type", "parts", "bbox", "attrs", "centroid")

    def __init__(self, index, geom_type, parts, bbox, attrs):
        self.index = index
        self.geom_type = geom_type
        self.parts = parts
        self.bbox = bbox
        self.attrs = attrs
        self.centroid = None

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
            if pts:
                self.centroid = (sum(p[0] for p in pts) / len(pts),
                                 sum(p[1] for p in pts) / len(pts))
            else:
                self.centroid = (0.0, 0.0)
        elif self.parts:
            pts = self.parts[0] if isinstance(self.parts[0], list) else self.parts
            self.centroid = (pts[0][0], pts[0][1])
        else:
            self.centroid = (0.0, 0.0)
        return self.centroid

    def polygon_area(self):
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
        if self.geom_type != "line":
            return 0.0
        total = 0.0
        for part in self.parts:
            for i in range(1, len(part)):
                total += math.hypot(part[i][0] - part[i - 1][0], part[i][1] - part[i - 1][1])
        return total


def _scale_ring(ring, scale, ox, oy):
    return [((p[0] - ox) * scale, (p[1] - oy) * scale) for p in ring]


# ------------------------------------------------------------------ DBF/SHP（旧版，保留以兼容）


def _decode_text(b, encodings=SHP_ENC):
    for enc in encodings:
        try:
            return b.decode(enc).strip()
        except Exception:
            continue
    return b.decode("latin-1", "ignore").strip()


def read_dbf(path):
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
        fields.append((name, ftype, flen, d[i + 17]))
        i += 32
    records = []
    for r in range(nrec):
        off = hlen + r * rlen
        rec = d[off:off + rlen]
        if len(rec) < rlen or rec[:1] == b"*":
            continue
        vals = {}
        p = 1
        for name, ftype, flen, _fdec in fields:
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


def read_shp(shp_path):
    with open(shp_path, "rb") as f:
        d = f.read()
    if len(d) < 100:
        return []
    dbf = os.path.splitext(shp_path)[0] + ".dbf"
    _, recs = read_dbf(dbf) if os.path.exists(dbf) else ([], [])
    feats = []
    pos, idx, n = 100, 0, len(d)
    while pos + 8 <= n:
        rec_no, clen = struct.unpack(">II", d[pos:pos + 8])
        pos += 8
        end = pos + clen * 2
        if end > n:
            break
        body = d[pos:end]
        pos = end
        attrs = recs[idx] if idx < len(recs) else {}
        idx += 1
        if len(body) < 4:
            continue
        st = struct.unpack("<i", body[0:4])[0]
        base = st - 10 if st >= 11 else st
        if base == 1:
            x, y = struct.unpack("<dd", body[4:20])
            feats.append(Feature(rec_no, "point", [[(x, y)]], (x, y, x, y), attrs))
        elif base in (3, 5):
            nparts, npoints = struct.unpack("<ii", body[36:44])
            if nparts <= 0 or npoints <= 0:
                continue
            p = 44
            if len(body) < p + 4 * nparts + 16 * npoints:
                continue
            pidx = list(struct.unpack("<%di" % nparts, body[p:p + 4 * nparts]))
            p += 4 * nparts
            co = struct.unpack("<%dd" % (npoints * 2), body[p:p + 16 * npoints])
            pts = [(co[i * 2], co[i * 2 + 1]) for i in range(npoints)]
            parts = []
            for i, s0 in enumerate(pidx):
                s1 = pidx[i + 1] if i + 1 < len(pidx) else npoints
                if 0 <= s0 < s1 <= npoints:
                    parts.append(pts[s0:s1])
            if not parts:
                continue
            xs = [q[0] for q in pts]
            ys = [q[1] for q in pts]
            feats.append(Feature(rec_no, "polygon" if base == 5 else "line", parts,
                                 (min(xs), min(ys), max(xs), max(ys)), attrs))
    return feats


# ------------------------------------------------------------------ 栅格

class Raster(object):
    def __init__(self, path):
        from PIL import Image
        self.path = path
        im = Image.open(path)
        self.size = im.size
        self.mode = im.mode
        tags = im.tag_v2
        self.scale = tags.get(33550) or (1.0, 1.0, 1.0)
        self.tiepoint = tags.get(33922) or (0.0,) * 6
        try:
            self.array = np.array(im) if np is not None else None
        except Exception:
            self.array = None
        self.x0 = self.tiepoint[3]
        self.y0 = self.tiepoint[4]
        self.dx = self.scale[0]
        self.dy = self.scale[1]

    def bounds(self):
        w, h = self.size
        return (self.x0, self.y0 - h * self.dy, self.x0 + w * self.dx, self.y0)

    def xy_to_pixel(self, x, y):
        return (int((x - self.x0) / self.dx), int((self.y0 - y) / self.dy))

    def value_at(self, x, y):
        if self.array is None:
            return None
        col, row = self.xy_to_pixel(x, y)
        h, w = self.array.shape[:2]
        if 0 <= col < w and 0 <= row < h:
            return float(self.array[row, col])
        return None


# ------------------------------------------------------------------ 数据容器

class CartoDataGJ(object):
    """新版 GeoJSON 导出的统一入口，接口与旧版 CartoData 一致。"""

    def __init__(self, carto_dir, scale=SCALE):
        self.dir = carto_dir
        self.scale = scale
        self.gj_dir = os.path.join(carto_dir, "GeoJSON")
        self.shp_dir = os.path.join(carto_dir, "Shapefile")
        self.tif_dir = os.path.join(carto_dir, "GeoTIFF")
        self._cache = {}
        self._origin = None

    # --- 定位数据文件（自动识别 <城市名>_ 前缀） ---
    def _find(self, stem):
        for d in (self.gj_dir, self.shp_dir, self.dir):
            if not os.path.isdir(d):
                continue
            for fn in os.listdir(d):
                if stem in fn and fn.lower().endswith(".json"):
                    return os.path.join(d, fn)
        return None

    def _find_shp(self, stem):
        for d in (self.shp_dir, self.dir):
            if not os.path.isdir(d):
                continue
            for fn in os.listdir(d):
                if fn.startswith(stem) and fn.lower().endswith(".shp"):
                    return os.path.join(d, fn)
        return None

    @property
    def origin(self):
        """归一化坐标的平移原点：取路网 bbox 中心，使坐标恒为正且与旧版量级相近。"""
        if self._origin is None:
            feats = self.layer("roads")
            if feats:
                xs0 = min(f.bbox[0] for f in feats)
                ys0 = min(f.bbox[1] for f in feats)
                self._origin = (xs0, ys0)
            else:
                self._origin = (0.0, 0.0)
        return self._origin

    def _load_geojson(self, name, key):
        path = self._find(name)
        if not path:
            return None
        with open(path, encoding="utf-8-sig") as f:
            d = json.load(f)
        feats_raw = d.get("features") or []
        # 先算原始 bbox 求原点（与 origin 属性一致：用 roads 的 bbox 左下角）
        if self._origin is None:
            rp = self._find("Network_Centerline")
            ox = oy = 0.0
            if rp:
                with open(rp, encoding="utf-8-sig") as f:
                    rd = json.load(f)
                gx, gy = [], []
                for f_ in (rd.get("features") or []):
                    g = f_.get("geometry") or {}
                    cs = g.get("coordinates") or []
                    if g.get("type") == "LineString":
                        for p in cs:
                            gx.append(p[0]); gy.append(p[1])
                    elif g.get("type") == "MultiLineString":
                        for ln in cs:
                            for p in ln:
                                gx.append(p[0]); gy.append(p[1])
                if gx:
                    ox, oy = min(gx), min(gy)
            self._origin = (ox, oy)
        ox, oy = self._origin
        s = self.scale

        feats = []
        for i, f_ in enumerate(feats_raw):
            g = f_.get("geometry") or {}
            gt = g.get("type")
            cs = g.get("coordinates")
            if cs is None:
                continue
            props = dict(f_.get("properties") or {})
            # 字段名适配
            for new, old in RENAME.items():
                if new in props and old not in props:
                    props[old] = props[new]
            if key == "buildings":
                z = props.get(BUILDING_ZONE_FIELD)
                if z:
                    props["Zone"] = z
                    props["Zoning"] = z
                props.setdefault("Addr_dist", props.get("Address_District"))
            if key == "roads":
                props.setdefault("Name", props.get("Asset"))

            if gt == "Polygon":
                parts = [_scale_ring(ring, s, ox, oy) for ring in cs if len(ring) >= 3]
                gtype = "polygon"
            elif gt == "MultiPolygon":
                parts = [_scale_ring(ring, s, ox, oy) for poly in cs for ring in poly if len(ring) >= 3]
                gtype = "polygon"
            elif gt == "LineString":
                parts = [_scale_ring(cs, s, ox, oy)] if len(cs) >= 2 else []
                gtype = "line"
            elif gt == "MultiLineString":
                parts = [_scale_ring(ln, s, ox, oy) for ln in cs if len(ln) >= 2]
                gtype = "line"
            elif gt == "Point":
                pts = [((cs[0] - ox) * s, (cs[1] - oy) * s)]
                parts = [pts]
                gtype = "point"
            elif gt == "MultiPoint":
                parts = [[((p[0] - ox) * s, (p[1] - oy) * s) for p in cs]]
                gtype = "point"
            else:
                continue
            if not parts:
                continue
            allp = [p for part in parts for p in part]
            xs = [p[0] for p in allp]
            ys = [p[1] for p in allp]
            feats.append(Feature(i, gtype, parts,
                                 (min(xs), min(ys), max(xs), max(ys)), props))
        return feats

    def layer(self, key):
        if key in self._cache:
            return self._cache[key]
        name = LAYER_FILE.get(key, key)
        feats = self._load_geojson(name, key)
        if feats is None:                      # 回退到旧版 Shapefile
            shp = self._find_shp(name)
            feats = read_shp(shp) if shp and os.path.exists(shp) else []
        self._cache[key] = feats
        return feats

    def __getattr__(self, item):
        if item in LAYER_FILE:
            return self.layer(item)
        raise AttributeError(item)

    # --- 栅格 ---
    def raster(self, name):
        k = "_r_" + name
        if k not in self._cache:
            p = os.path.join(self.tif_dir, name + ".tif")
            self._cache[k] = Raster(p) if os.path.exists(p) else None
        return self._cache[k]

    @property
    def elevation(self):
        return self.raster("Elevation")

    @property
    def depth(self):
        return self.raster("Depth")

    # --- 派生 ---
    def districts(self):
        return [a for a in self.layer("areas") if a.get("Object") == "District"]

    def unlocked_tiles(self):
        return [a for a in self.layer("areas")
                if a.get("Object") == "MapTile" and a.get("Unlocked")]

    def city_bounds(self):
        feats = self.unlocked_tiles() or self.layer("buildings")
        if not feats:
            return None
        return (min(f.bbox[0] for f in feats), min(f.bbox[1] for f in feats),
                max(f.bbox[2] for f in feats), max(f.bbox[3] for f in feats))

    def built_bounds(self):
        feats = [f for f in self.unlocked_tiles()
                 if (f.get("Resident") or 0) > 0 or (f.get("Employee") or 0) > 0]
        if not feats:
            feats = self.layer("buildings")
        if not feats:
            return self.city_bounds()
        return (min(f.bbox[0] for f in feats), min(f.bbox[1] for f in feats),
                max(f.bbox[2] for f in feats), max(f.bbox[3] for f in feats))

    def total_population(self):
        return sum(f.get("Resident") or 0 for f in self.layer("buildings"))

    def total_jobs(self):
        return sum(f.get("Employee") or 0 for f in self.layer("buildings"))


class GridIndex(object):
    def __init__(self, points, cell=200.0):
        self.cell = float(cell)
        self.buckets = {}
        for x, y, payload in points:
            self.buckets.setdefault(self._key(x, y), []).append((x, y, payload))

    def _key(self, x, y):
        return (int(math.floor(x / self.cell)), int(math.floor(y / self.cell)))

    def within(self, x, y, radius):
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
    return GridIndex([(b.compute_centroid()[0], b.compute_centroid()[1], b)
                      for b in carto.layer("buildings")])


if __name__ == "__main__":
    import io
    import sys
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    root = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\Devcl\Desktop\CSL2\Carto_20261013"
    c = CartoDataGJ(root)
    print("数据目录:", root)
    print("原点(归一化):", c.origin, " 比例: %.1f m/单位" % c.scale)
    for k in LAYER_FILE:
        print("  %-14s %d 个要素" % (k, len(c.layer(k))))
    print("人口 %d / 岗位 %d" % (c.total_population(), c.total_jobs()))
    print("已解锁地块 %d" % len(c.unlocked_tiles()))
    b = c.layer("buildings")
    if b:
        print("建筑样例:", {kk: b[0].get(kk) for kk in
                            ("Name", "Addr_dist", "Zoning", "Density", "Resident",
                             "Employee", "Level")})
        print("建筑 bbox:", tuple(round(v) for v in c.built_bounds()))
