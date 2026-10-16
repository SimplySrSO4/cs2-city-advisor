#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
roads.py —— **路名几何与"沿线区间"定位**（纯标准库）

为什么需要它（本项目实测踩过的坑）
----------------------------------
`Network_Boundary` / `Network_Centerline` 是**按路段（segment）导出的一条条折线**，
**同一条"路"会对应几十条独立要素**，它们在文件里的顺序**与地理位置无关**。

⚠️ **最危险的一个错误**：把所有同名路段首尾相接画成一条折线 —— 于是**互不相邻的路段被直线连起来**。
本项目第十轮实测：`繁荣路` 47 段 / 5.05 km，被这样画成一条横贯 5 km 的橙色斜带
（图上那几道平行长线就是这个 artifact），**"路在哪"在图上是错的**。

⚠️ **第二个错误**：用这些要素的**合并 bbox** 当"这条路的两端"。
bbox 会同时收录**别处的同名小段**，于是"繁荣路北端"被写成 y=12088（其实那是另一段的东北角），
而真正的北端路口在 (8208, 12088) 附近的另一条线段上 —— **一个坐标就足以让建议落到错误的位置**。

本模块给出的口径（**报告里描述"xx路沿线"必须用这一套**）
------------------------------------------------------
1. **连通段（run）**：把同名路段按"端点相接"聚成若干条**连续折线**（默认容差 `tol=60 m`，
   因为游戏里路口处路段可能断开十几米）。**只有同一个 run 内部的顺序才有意义。**
2. **参数 s（沿线里程）**：沿某个 run 从**南端/西端**（或指定的端点）累计的弧长，单位米。
   `s = 0` 是起点，`s = run.length` 是终点。
3. **沿线区间**：任何位置都写成 **`路名 s₁–s₂ m`**（如"繁荣路 s 4210–5045 m"），
   并且**同时给出该区间的端点地物**（哪个路口 / 哪条路的交点 / 哪个地块）。
   **不要写"把 xx 路延伸到某点"** —— 那条路并没有延伸到那里；要么是"在 s=a–b 区间内新增"，
   要么就是"地图上另一个位置的新建道路"，必须分开说（见 `SKILL.md` §0 铁律 9）。
4. **两端点**：`terminal()` 返回**几何上的真实端点**（该 run 的首/末顶点），
   不是 bbox 角点。报告里写"北端"时用它。

用法
----
```python
from core import roads as R
g = R.road_geometry(carto, '繁荣路')          # 全部同名路段 + 连通段 + 参数化
print(g.summary())                            # 段数 / 总长 / 各 run 端点与里程
p = g.project(x, y)                           # 任意点 → (到路距离, run 序号, s)
[i for i in g.stations(carto) if i['in_interval']]   # 站点落在哪个沿线区间
```
"""

import math
from collections import defaultdict

#: 连通段容差（米）。游戏在路口处会把路段断开十几米，60 m 足够合并、又不会把两条平行路错并。
RUN_TOL = 60.0


def _parts_of(f):
    p = f.parts
    return p if p and isinstance(p[0], list) else [p]


def named_segments(carto, name, layer="roads"):
    """取某路名的全部路段要素。返回 `[(Feature, [顶点...]), ...]`。"""
    out = []
    for f in carto.layer(layer):
        if (f.attrs.get("Name") or "") == name:
            for part in _parts_of(f):
                if len(part) >= 2:
                    out.append((f, list(part)))
    return out


def _run_length(pts):
    return sum(math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
               for i in range(1, len(pts)))


def group_runs(segments, tol=RUN_TOL):
    """把路段按"端点相接"聚成**连续段（run）**。

    做法：以每条路段的两端点为节点，端点距离 ≤ `tol` 视作同一节点（并查集通路），
    再按"该路的走向轴"（端点协方差主轴）排序、串成折线。

    ⚠️ 排序轴必须是**整条路的走向主轴**，不能用 y 轴 —— 斜向道路按 y 排会串错。
    """
    segs = [list(s[1]) for s in segments if len(s[1]) >= 2]
    if not segs:
        return []
    # --- 端点聚类 ---
    pts = []
    for s in segs:
        pts.append(s[0])
        pts.append(s[-1])
    parent = list(range(len(pts)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    cell = max(1.0, tol)
    grid = defaultdict(list)
    for i, (x, y) in enumerate(pts):
        grid[(int(x // cell), int(y // cell))].append(i)
    for (cx, cy), idxs in grid.items():
        near = []
        for ddx in (-1, 0, 1):
            for ddy in (-1, 0, 1):
                near += grid.get((cx + ddx, cy + ddy), [])
        for i in idxs:
            xi, yi = pts[i]
            for j in near:
                if j <= i:
                    continue
                xj, yj = pts[j]
                if math.hypot(xi - xj, yi - yj) <= tol:
                    union(i, j)
    comp = defaultdict(list)                     # 端点 → 路段序号（按**端点簇**归组）
    for k in range(len(segs)):
        comp[find(2 * k)].append(k)
        comp[find(2 * k + 1)].append(k)
    # ⚠️ **必须按端点集群连通闭包**：只按单个端点归组会把"甲段终点≈乙段起点"
    # 这种跨簇相接拆成两个 run（实测会把一条直路切成十几段）。
    # 做法：把每个 run 当节点，两个 run 共享任一端点簇即合并。
    rparent = list(range(len(segs)))

    def rfind(a):
        while rparent[a] != a:
            rparent[a] = rparent[rparent[a]]
            a = rparent[a]
        return a

    owner = {}
    for k in range(len(segs)):
        for e in (2 * k, 2 * k + 1):
            r = find(e)
            if r in owner:
                ra, rb = rfind(owner[r]), rfind(k)
                if ra != rb:
                    rparent[rb] = ra
            else:
                owner[r] = k
    groups = defaultdict(list)
    for k in range(len(segs)):
        groups[rfind(k)].append(k)
    # --- 每组串成折线 ---
    runs = []
    for ids in groups.values():
        pool = [segs[i] for i in ids]
        # 走向主轴：所有顶点 PCA
        allp = [p for s in pool for p in s]
        mx = sum(p[0] for p in allp) / len(allp)
        my = sum(p[1] for p in allp) / len(allp)
        sxx = sum((p[0] - mx) ** 2 for p in allp)
        syy = sum((p[1] - my) ** 2 for p in allp)
        sxy = sum((p[0] - mx) * (p[1] - my) for p in allp)
        # 主轴方向（最大特征值）
        tr, det = sxx + syy, sxx * syy - sxy * sxy
        lam = tr / 2 + math.sqrt(max(0.0, tr * tr / 4 - det))
        if abs(sxy) > 1e-9:
            ax, ay = lam - syy, sxy
        else:
            ax, ay = (1.0, 0.0) if sxx >= syy else (0.0, 1.0)
        nrm = math.hypot(ax, ay) or 1.0
        ax, ay = ax / nrm, ay / nrm
        proj = lambda p: p[0] * ax + p[1] * ay          # noqa: E731
        chains = []
        left = list(pool)
        while left:
            cur = left.pop(0)
            chain = list(cur)
            grew = True
            while grew:
                grew = False
                for i, s in enumerate(left):
                    if math.hypot(chain[-1][0] - s[0][0], chain[-1][1] - s[0][1]) <= tol:
                        chain += s[1:]
                        left.pop(i)
                        grew = True
                        break
                    if math.hypot(chain[-1][0] - s[-1][0], chain[-1][1] - s[-1][1]) <= tol:
                        chain += list(reversed(s))[1:]
                        left.pop(i)
                        grew = True
                        break
                    if math.hypot(chain[0][0] - s[-1][0], chain[0][1] - s[-1][1]) <= tol:
                        chain = s[:-1] + chain
                        left.pop(i)
                        grew = True
                        break
                    if math.hypot(chain[0][0] - s[0][0], chain[0][1] - s[0][1]) <= tol:
                        chain = list(reversed(s))[:-1] + chain
                        left.pop(i)
                        grew = True
                        break
            chains.append(chain)
        for ch in chains:
            if proj(ch[0]) > proj(ch[-1]):
                ch = list(reversed(ch))
            runs.append(ch)
    runs.sort(key=lambda ch: -_run_length(ch))
    return runs


class RoadGeometry(object):
    """一条**同名路**的几何：路段、连通段、参数化、沿线区间。

    所有坐标都是**数据本身的本地米制**（与报告一致，未加渲染平移）。
    """

    def __init__(self, name, segments, runs):
        self.name = name
        self.segments = segments
        self.runs = runs
        self._cum = []
        for ch in runs:
            c = [0.0]
            for i in range(1, len(ch)):
                c.append(c[-1] + math.hypot(ch[i][0] - ch[i - 1][0], ch[i][1] - ch[i - 1][1]))
            self._cum.append(c)

    # --- 基本量 ---
    @property
    def total_length(self):
        return sum(c[-1] for c in self._cum if c)

    def run_length(self, k):
        return self._cum[k][-1]

    @property
    def n_segments(self):
        return sum(len(_parts_of(f)) for f, _p in self.segments)

    def categories(self):
        d = defaultdict(float)
        for f, p in self.segments:
            try:
                L = f.line_length()
            except Exception:                                   # noqa: BLE001
                L = _run_length(p)
            d[f.attrs.get("Category") or "?"] += L
        return dict(d)

    def terminal(self, k=0, which="end"):
        """连通段 `k` 的**真实端点**（`which='start'|'end'`）。返回 `(x, y, s)`。"""
        ch = self.runs[k]
        if which in ("end", "north", "east"):
            return (ch[-1][0], ch[-1][1], self._cum[k][-1])
        return (ch[0][0], ch[0][1], 0.0)

    # --- 参数化 ---
    def point_at(self, k, s):
        """连通段 `k` 上里程 `s` 处的点（`s` 会被夹到 `[0, L]`）。"""
        ch, cum = self.runs[k], self._cum[k]
        L = cum[-1]
        s = max(0.0, min(L, float(s)))
        for i in range(1, len(cum)):
            if cum[i] >= s:
                d = cum[i] - cum[i - 1]
                t = 0.0 if d <= 0 else (s - cum[i - 1]) / d
                return (ch[i - 1][0] + (ch[i][0] - ch[i - 1][0]) * t,
                        ch[i - 1][1] + (ch[i][1] - ch[i - 1][1]) * t)
        return ch[-1]

    def project(self, x, y, k=None):
        """点在路上的投影 → `(距离m, run序号, 里程s)`；`k` 给定时只在该 run 上投。"""
        best = (1e18, None, None)
        ks = range(len(self.runs)) if k is None else (k,)
        for kk in ks:
            ch = self.runs[kk]
            cum = self._cum[kk]
            for i in range(1, len(ch)):
                x1, y1 = ch[i - 1]
                x2, y2 = ch[i]
                dx, dy = x2 - x1, y2 - y1
                L2 = dx * dx + dy * dy
                t = 0.0 if L2 <= 0 else max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / L2))
                px, py = x1 + t * dx, y1 + t * dy
                d = math.hypot(x - px, y - py)
                if d < best[0]:
                    best = (d, kk, cum[i - 1] + t * math.hypot(dx, dy))
        return best

    def offset_of(self, x, y, k=None):
        """点在路上的里程 `s`（米）；返回 `None` 表示 >2 km 之外（不认为在这条路沿线）。"""
        d, _kk, s = self.project(x, y, k=k)
        return s if d <= 2000.0 else None

    def interval_label(self, s1, s2, k=0):
        """**标准写法**：`繁荣路 s 4210–5045 m（1.0 km）`。"""
        s1, s2 = sorted((float(s1), float(s2)))
        return "%s s %d–%d m（%.1f km）" % (self.name, round(s1), round(s2), (s2 - s1) / 1000.0)

    def window(self, s1, s2, k=0):
        """取出连通段 `k` 上 `s∈[s1,s2]` 的折线顶点（用于图上画区间括号）。"""
        ch, cum = self.runs[k], self._cum[k]
        s1, s2 = sorted((max(0.0, s1), min(cum[-1], s2)))
        pts = [self.point_at(k, s1)]
        for i in range(1, len(cum) - 1):
            if s1 < cum[i] < s2:
                pts.append(ch[i])
        pts.append(self.point_at(k, s2))
        return pts

    def stations(self, carto, radius=800.0, categories=("StopBus", "StopSubway", "StopPassengerTrain"),
                 merge=40.0, runs=None):
        """把 POI 站点投到本条路上，返回逐站的 `(名称, 类别, 到路距离, run, s)`（按 run、s 排序）。

        ⚠️ **必须去重**：`POI_Location` 里同一个车站会在几何两侧各记一条（相距 30–40 m），
        直接数会把站数算成两倍 —— 项目实测某地铁站被记 3 次（见 `references/70`）。
        `merge` 给出"视为同一个站"的距离阈值。

        ⚠️ **`runs` 必须按需限定**：同名路可能是**几个互不相连的连通段**
        （本项目实测 `繁荣路` = 4.86 km 主段 + 0.18 km 孤立小段，相距约 900 m）。
        不限定时，站会落到"离最近的那一段"上，把两个片区的站混成一张表。
        **做走廊分析时给 `runs=[0]`（或明确列出要分析的那几段）。**
        """
        raw = []
        ks = range(len(self.runs)) if runs is None else runs
        for p in carto.pois:
            cat = p.get("Category") or ""
            if cat not in categories:
                continue
            x, y = p.compute_centroid()
            best = (1e18, None, None)
            for kk in ks:
                d, _k, s = self.project(x, y, k=kk)
                if d < best[0]:
                    best = (d, kk, s)
            d, k, s = best
            if d <= radius:
                raw.append({"name": p.get("Name"), "cat": cat, "dist": d, "run": k, "s": s,
                            "x": x, "y": y})
        raw.sort(key=lambda r: (r["run"], r["s"], r["dist"]))
        out = []
        for r in raw:
            dup = None
            for o in out:
                if math.hypot(r["x"] - o["x"], r["y"] - o["y"]) <= merge:
                    dup = o
                    break
            if dup is None:
                out.append(r)
            else:
                # 同一站的多条记录：方式取"更高一级"的（铁路/地铁 > 公交），距离取更近的
                rank = {"StopBus": 0, "StopPassengerTrain": 1, "StopSubway": 2}
                if rank.get(r["cat"], 0) > rank.get(dup["cat"], 0):
                    dup["cat"] = r["cat"]
                dup["dist"] = min(dup["dist"], r["dist"])
                dup["s"] = min(dup["s"], r["s"])
        out.sort(key=lambda r: (r["run"], r["s"]))
        return out

    def summary(self):
        """给报告/控制台用的多行摘要（**不要直接把 bbox 当端点**）。"""
        L = []
        L.append("%s：%d 条路段 → %d 个连通段，总长 %.2f km" %
                 (self.name, self.n_segments, len(self.runs), self.total_length / 1000.0))
        for k, ch in enumerate(self.runs):
            a, b = ch[0], ch[-1]
            L.append("  连通段%d  %.2f km  %d 顶点  起点(%.0f,%.0f) → 终点(%.0f,%.0f)" %
                     (k, self._cum[k][-1] / 1000.0, len(ch), a[0], a[1], b[0], b[1]))
        cats = self.categories()
        L.append("  等级里程：%s" % ", ".join("%s %.2f km" % (k, v / 1000.0)
                                              for k, v in sorted(cats.items(), key=lambda t: -t[1])))
        return "\n".join(L)


def road_geometry(carto, name, layer="roads", tol=RUN_TOL):
    """一条同名路的完整几何（见 `RoadGeometry`）。`layer` 默认 `roads`（=Network_Centerline）。"""
    segs = named_segments(carto, name, layer=layer)
    runs = group_runs(segs, tol=tol)
    return RoadGeometry(name, segs, runs)


def lane_windows(road, carto, k=0, step=200.0, half=300.0, attrs=("Lane", "Limit", "Category")):
    """沿连通段 `k` 逐 `step` 米取一个横断面，统计 `half` 米内的**道路等级构成**。

    这是"沿线"分析的正确做法：**断面沿路走**，而不是按 bbox 或按区统计。
    返回 `[{s, cross: {等级: km}, lanes: 车道均值, limit: 限速均值}, ...]`。
    """
    out = []
    segs = [(f, p) for f, p in road.segments]
    L = road.run_length(k)
    s = 0.0
    while s <= L + 1e-6:
        x, y = road.point_at(k, s)
        cross = defaultdict(float)
        lanes, lims, n = 0.0, 0.0, 0
        for f, p in segs:
            d = _min_dist(x, y, p)
            if d <= half:
                cat = f.attrs.get("Category") or "?"
                try:
                    cl = f.line_length()
                except Exception:                              # noqa: BLE001
                    cl = _run_length(p)
                cross[cat] += cl / 1000.0
                if (f.attrs.get("Lane") or 0) > 0:
                    lanes += f.attrs.get("Lane")
                    lims += f.attrs.get("Limit") or 0
                    n += 1
        out.append({"s": s, "cross": dict(cross), "lanes": (lanes / n if n else 0),
                    "limit": (lims / n if n else 0)})
        s += step
    return out


def _min_dist(x, y, pts):
    best = 1e18
    for i in range(1, len(pts)):
        x1, y1 = pts[i - 1]
        x2, y2 = pts[i]
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 <= 0 else max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / L2))
        best = min(best, math.hypot(x - (x1 + t * dx), y - (y1 + t * dy)))
    return best
