#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
terrain.py —— **可建造性**分析（水体 / 陡坡 / 适宜建设区）+ GeoJSON→UTM 坐标标定。

为什么需要它
------------
`SKILL.md` 的**最高级别要求**：给出规划建议时必须避开**水体**与**坡度极大**的区域。
Carto 的 GeoTIFF 是 EPSG:32631 绝对坐标，而新版 GeoJSON 是归一化坐标 ——
两者必须先**标定**才能把地形与建筑对上。本模块解决这件事，并输出可建造性分级。

坐标标定（`solve_utm_offset`）
------------------------------
不依赖任何外部说明，纯数据自洽：
建筑自带 `Elevation`（米），栅格 `Elevation.tif` 是同一套地形 ——
搜索使两者**中位误差最小**的平移量即可。
实测：中位误差 **0.05 m**、平均 0.08 m、P90 0.21 m（≈ 数据本身的 0.1 m 量化精度），
且建筑处坡度中位 **0°** 而全图中位 8.1° —— 城市建在平地上，物理上自洽。

地形分级（`buildability`）
--------------------------
实测该地图是**台地式**设计：约 48% 面积坡度 < 0.5°，其后直接跳到 5° 以上
（0.5–5° 区间为空），台地高程集中在 280 / 400 / 353 / 449 m；
**水体为高程 0 的平坦区**。

| 类别 | 判据 | 含义 |
|---|---|---|
| `WATER` | 高程 ≤ 0 且坡度 < 1° | 水体，**不可建造** |
| `STEEP` | 坡度 > `steep_deg`（默认 25°） | 陡坡，**强烈不建议建造** |
| `SLOPE` | 坡度 > `slope_deg`（默认 10°） | 有明显坡度，建造需整地 |
| `FLAT` | 其余 | 适宜建设区 |
| `OUTSIDE` | 地图边界外 | 未解锁/地图外 |
"""

import numpy as np

#: 可建造性类别
WATER, STEEP, SLOPE, FLAT, OUTSIDE = "水体", "陡坡", "缓坡", "适宜", "地图外"

#: 实测该地图水体为高程 0；给 1 m 容差
WATER_MAX_ELEV = 1.0
#: 水体判定的坡度上限（真水面是平的）
WATER_MAX_SLOPE = 1.0


def tile_extent(carto):
    """全部 MapTile（含未解锁）在 **GeoJSON 米制**下的 bbox `(xmin, ymin, xmax, ymax)`。

    这张 bbox 与 `Elevation.tif` 覆盖的是**同一块地图**，因此它的中心就是标定的锚点 ——
    比"靠高程中位数搜索"稳健得多（台地地形有大量等高的伪极小值，见 `_score_offset`）。
    """
    xs, ys = [], []
    for t in carto.layer("areas"):
        if t.get("Object") != "MapTile":
            continue
        parts = t.parts if t.parts and isinstance(t.parts[0], list) else [t.parts]
        for part in parts:
            for x, y in part:
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


def _score_offset(sx, sy, se, EA, x0, y0, dx, dy, ox, oy, nodata=-32768.0):
    """给定平移量，返回建筑高程 vs 栅格高程的误差分布（全部样本必须落在栅格内）。"""
    h, w = EA.shape
    col = np.floor((sx + ox - x0) / dx).astype(np.int64)
    row = np.floor((y0 - (sy + oy)) / dy).astype(np.int64)
    ok = (col >= 0) & (col < w) & (row >= 0) & (row < h)
    if not ok.all():
        return None
    ev = EA[row, col]
    v = ev != nodata
    if v.sum() < len(sx) * 0.8:
        return None
    err = np.abs(ev[v] - se[v])
    return {"median_m": float(np.median(err)), "mean_m": float(err.mean()),
            "p90_m": float(np.percentile(err, 90)),
            "within_1m": float((err < 1.0).mean()),
            "valid": float(v.mean())}


def solve_utm_offset(carto, sample=150, coarse=50.0, span=2000.0, refine=(10.0, 2.0, 0.5), seed=5):
    """用「建筑 Elevation vs 栅格 Elevation」解出 GeoJSON → 栅格坐标的平移量。

    返回 `(ox, oy, quality)`；`quality` 含中位/平均/P90 误差、`within_1m` 与有效率。
    解不出（样本不足或栅格缺失）返回 `(None, None, None)`。

    ⚠️ **三处必须这样做，否则会解出错误的平移量**（本项目实测踩过）：
    1. **候选范围不能从栅格左上角起算**：本地栅格是"以地图中心为原点"的
       （`x0=-7168, y0=+7168`），而 `x0 - sx.min()` 这种写法会把搜索窗推到离真值
       超过 3 km 的地方，粗搜步长下**只剩伪极小值**。
       正确做法：用 **MapTile bbox 中心**对齐**栅格 bbox 中心**当锚点（两者覆盖同一块地图），
       再在锚点 ±`span` 内搜索。
    2. **判优不能只看中位数**：本图是**台地地形**（大量像素等高），
       错误平移也会让大部分建筑落在某个台地上、中位误差很小。
       必须同时看 **P90** 与 **`within_1m` 比例**。
    3. **不能把高程转成整数**（早期的 `astype(np.int64)`）：那会把 0.1 m 的量化精度
       放大成 1 m 的系统误差，使"中位误差 0.05 m"这类自检结论失真。

    ⚡ **结果按 `carto` 缓存**：本函数实测 ~10 s（粗搜要评成千上万个候选平移量），
    而 `analyze_terrain()` / `analyze_elevation_planner()` / `buildability()` 都要用同一个平移量。
    不缓存会把报告时间直接翻倍。
    """
    if not hasattr(carto, "_terrain_cache") or carto._terrain_cache is None:
        try:
            carto._terrain_cache = {}
        except Exception:      # noqa: BLE001
            pass
    _c = getattr(carto, "_terrain_cache", None)
    _ck = "_utm_offset_%s_%s_%s" % (sample, coarse, span)
    if _c is not None and _ck in _c:
        return _c[_ck]

    bl = carto.layer("buildings")
    pts = [(f.compute_centroid()[0], f.compute_centroid()[1], f.get("Elevation"))
           for f in bl]
    pts = [(x, y, float(e)) for x, y, e in pts if e is not None]
    if len(pts) < 20:
        return None, None, None
    P = np.array(pts)
    bx, by, be = P[:, 0], P[:, 1], P[:, 2]

    r = carto.raster("Elevation")
    if r is None or r.array is None:
        return None, None, None
    EA = r.array.astype(np.float64)
    x0, y0, dx, dy = r.x0, r.y0, r.dx, r.dy
    h, w = EA.shape

    rng = np.random.default_rng(seed)
    if len(P) > sample:
        idx = rng.choice(len(P), size=sample, replace=False)
    else:
        idx = np.arange(len(P))
    sx, sy, se = bx[idx], by[idx], be[idx]

    def evaluate(ox, oy):
        return _score_offset(sx, sy, se, EA, x0, y0, dx, dy, ox, oy)

    # --- 锚点：MapTile bbox 中心 → 栅格 bbox 中心 ---
    te = tile_extent(carto)
    if te is None:
        return None, None, None
    gx0, gy0, gx1, gy1 = (x0, y0 - h * dy, x0 + w * dx, y0)
    a_ox = (gx0 + gx1) / 2.0 - (te[0] + te[2]) / 2.0
    a_oy = (gy0 + gy1) / 2.0 - (te[1] + te[3]) / 2.0

    # --- 粗搜（以锚点为中心，按 P90 判优）---
    best = None
    for ox in np.arange(a_ox - span, a_ox + span + 1e-9, coarse):
        for oy in np.arange(a_oy - span, a_oy + span + 1e-9, coarse):
            s = evaluate(ox, oy)
            if s and (best is None or (s["p90_m"], s["median_m"]) < (best[0]["p90_m"], best[0]["median_m"])):
                best = (s, ox, oy)
    if best is None:
        return None, None, None
    b_ox, b_oy = best[1], best[2]

    # --- 逐级细搜 ---
    for st in refine:
        c = None
        for ox in np.arange(b_ox - st * 4, b_ox + st * 4 + 1e-9, st):
            for oy in np.arange(b_oy - st * 4, b_oy + st * 4 + 1e-9, st):
                s = evaluate(ox, oy)
                if s and (c is None or (s["p90_m"], s["median_m"]) < (c[0]["p90_m"], c[0]["median_m"])):
                    c = (s, ox, oy)
        if c:
            b_ox, b_oy = c[1], c[2]

    q = evaluate(b_ox, b_oy)
    if _c is not None:
        _c[_ck] = (b_ox, b_oy, q)
    return b_ox, b_oy, q


def map_extent(carto, offset=None):
    """返回地图（MapTile 范围）在**栅格坐标**下的 bbox `(xmin, ymin, xmax, ymax)`。

    `offset` 为 None 时自动调用 `solve_utm_offset()`（不传 offset 会得到未平移的地块范围，
    与栅格对不上）。解不出平移量时退回未平移范围。
    """
    if offset is None:
        ox, oy, _q = solve_utm_offset(carto)
        offset = (ox or 0.0, oy or 0.0)
    tiles = [a for a in carto.layer("areas") if a.get("Object") == "MapTile"]
    if not tiles:
        return None
    xs, ys = [], []
    for t in tiles:
        parts = t.parts if t.parts and isinstance(t.parts[0], list) else [t.parts]
        for part in parts:
            for x, y in part:
                xs.append(x)
                ys.append(y)
    ox = offset[0] if offset else 0.0
    oy = offset[1] if offset else 0.0
    return (min(xs) + ox, min(ys) + oy, max(xs) + ox, max(ys) + oy)


def buildability(carto, offset=None, steep_deg=25.0, slope_deg=10.0, step=7.0):
    """输出可建造性栅格。**结果缓存到 `carto` 上 —— 重复调用不会重算。**

    ⚡ 性能说明：本函数要对 ~4000² 栅格求梯度并逐像元分级，**实测单次 ~10 s**。
    而 `analyze_terrain()` 与 `analyze_elevation_planner()` 都要用它 →
    若不缓存，报告时间会被翻倍。缓存键含阈值参数，改阈值会重算。

    返回 dict：
      * `x0/y0/step/nx/ny` —— 栅格地理参考（UTM 米）
      * `cls` —— `numpy` 字符串数组，取值见 `WATER/STEEP/SLOPE/FLAT/OUTSIDE`
      * `elev` / `slope` —— 对应的高程与坡度
      * `stats` —— 各类别像素占比；`inside_*` 为**地图内**占比

    用法：给一个 UTM 坐标 → `classify_point(build, x, y)` 取类别，从而在给建议前先排除水体与陡坡。
    """
    ck = "_terrain_buildability_%s_%s_%s" % (steep_deg, slope_deg, step)
    cache = getattr(carto, "_terrain_cache", None)
    if cache is None:
        cache = {}
        try:
            carto._terrain_cache = cache
        except Exception:      # noqa: BLE001  (carto 可能不允许加属性)
            cache = None
    if cache is not None and ck in cache:
        return cache[ck]

    e = carto.raster("Elevation")
    if e is None or e.array is None:
        return None
    # ⚡ float32 足够：地形分级只需 ~0.1° 精度，float64 会多花一倍内存与时间
    EA = e.array.astype(np.float32)
    gy, gx = np.gradient(EA, e.dy, e.dx)
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    h, w = EA.shape

    ext = map_extent(carto, offset)
    inside = np.zeros((h, w), dtype=bool)
    if ext:
        xmin, ymin, xmax, ymax = ext
        c0 = int(np.floor((xmin - e.x0) / e.dx)); c1 = int(np.ceil((xmax - e.x0) / e.dx))
        r0 = int(np.floor((e.y0 - ymax) / e.dy)); r1 = int(np.ceil((e.y0 - ymin) / e.dy))
        c0, c1 = max(0, c0), min(w, c1)
        r0, r1 = max(0, r0), min(h, r1)
        inside[r0:r1, c0:c1] = True

    nodata = EA == -32768
    cls = np.full((h, w), OUTSIDE, dtype=object)
    water = inside & (~nodata) & (EA <= WATER_MAX_ELEV) & (slope < WATER_MAX_SLOPE)
    steep = inside & (~nodata) & (slope > steep_deg)
    slope_m = inside & (~nodata) & (slope > slope_deg) & (~steep)
    flat = inside & (~nodata) & (~water) & (~steep) & (~slope_m)
    cls[water] = WATER
    cls[steep] = STEEP
    cls[slope_m] = SLOPE
    cls[flat] = FLAT

    n_in = int(inside.sum()) or 1
    stats = {
        "water": int(water.sum()), "steep": int(steep.sum()),
        "slope": int(slope_m.sum()), "flat": int(flat.sum()),
        "inside": int(inside.sum()),
        "water_pct": 100.0 * water.sum() / n_in,
        "steep_pct": 100.0 * steep.sum() / n_in,
        "slope_pct": 100.0 * slope_m.sum() / n_in,
        "flat_pct": 100.0 * flat.sum() / n_in,
        "steep_deg": steep_deg, "slope_deg": slope_deg,
    }
    out = {"x0": e.x0, "y0": e.y0, "step": e.dx, "nx": w, "ny": h,
           "cls": cls, "elev": EA, "slope": slope, "inside": inside, "stats": stats,
           "extent": ext}
    if cache is not None:
        cache[ck] = out
    return out


def classify_point(build, x, y, neighborhood=1):
    """查某 UTM 坐标的可建造性类别；越界/无数据返回 None。

    `neighborhood`：**在 (2n+1)² 邻域里取"最好"的类别**（默认 3×3）。
    为什么需要它：栅格在**地图边界/水体边缘**会有零星 NoData 或"地图外"像素，
    单点取样会让整条建议落到 `None`（报告里显示 `?`）。
    取邻域最优可以避免这种单像素抖动 —— 这也是"这个点位能不能建"的合理问法。
    """
    if not build:
        return None
    col = int(np.floor((x - build["x0"]) / build["step"]))
    row = int(np.floor((build["y0"] - y) / build["step"]))
    nx, ny, cls = build["nx"], build["ny"], build["cls"]
    n = max(0, int(neighborhood))
    #: 优先级：越靠前越"适合建设"，邻域里取最靠前的
    order = (FLAT, SLOPE, STEEP, WATER)
    for want in order:
        for dr in range(-n, n + 1):
            for dc in range(-n, n + 1):
                r, c = row + dr, col + dc
                if 0 <= c < nx and 0 <= r < ny and cls[r, c] == want:
                    return want
    return None


def is_buildable(build, x, y):
    """是否属于"可给出建设建议"的区域（适宜/缓坡为真；水体/陡坡/地图外/无数据为假）。"""
    c = classify_point(build, x, y, neighborhood=3)
    return c in (FLAT, SLOPE)


def verdict_text(build, x, y):
    """给人看的简短判语，用于报告表格。

    * `OK`     —— 适宜建设区，可直接给建议
    * `需整地`  —— 缓坡，可给但须写明代价
    * `禁`     —— 水体 / 陡坡，**不得给建设建议**
    * `无数据`  —— 地形栅格在此处无值（地图边缘/NoData）。**同样不建议在此新建**，
      因为"无法确认能建"不等于"能建"；但要在措辞上与"明确禁止"区分开。
    """
    c = classify_point(build, x, y, neighborhood=3)
    if c is None:
        return "无数据"
    return {FLAT: "OK", SLOPE: "需整地", STEEP: "禁", WATER: "禁"}.get(c, "无数据")
