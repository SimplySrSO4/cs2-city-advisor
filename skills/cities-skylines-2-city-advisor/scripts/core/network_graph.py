#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
network_graph.py —— 由 Carto 路网中心线构建可路由的图（T5c 通勤可达性代理的基础设施）

为什么需要它
------------
`references/46` 的 **T5c（通勤可达性代理，★★★）** 要求用**路网最短路**而不是欧氏距离来评估通勤风险：
1.6.0f1 起游戏按出行目的分设寻路距离上限，**找不到可行路线就直接辞职/搬离**，
所以"有没有一条可行路线、要绕多远"比"直线多近"更关键。
`carto_reader.py` 只有几何与属性，没有图结构 —— 本模块补这一层。

设计
----
* **节点**：道路中心线的端点/顶点，按容差（默认 25 m）吸附到网格节点 ——
  Carto 的路段是分段的，相邻段端点通常不严格重合，必须吸附。
* **边**：每段道路按其几何长度加权；**权重 = 长度 ÷ 速度**（秒），速度取该段的 `Limit`（km/h）。
  `Form == 'Tunnel'` 与 `Elevated` 不改变拓扑，只影响限速（已在 `Limit` 里）。
* **方向**：`Direction == 'Forward'` 视为单向（只建立正向边）；`Both` 双向。
  注意 CSL2 的高速常按方向各记一条中心线，所以单向段本身并不缺回程。
* **不区分车道容量**——这是**几何可达性**模型，不是交通仿真；拥堵无法从中得出（见 `70` §5 局限 2）。

用法
----
    from network_graph import RoadNetwork
    net = RoadNetwork(carto)
    dist, path = net.shortest_path(x0, y0, x1, y1)     # 返回米与节点序列
    m = net.distance_matrix(sources, targets)          # 多源多汇（笛卡尔积，逐个 Dijkstra）
"""

import heapq
import math
import os
import sys
from collections import defaultdict

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # scripts/
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

try:
    from core.carto_reader import GridIndex
except Exception:  # 允许单独拷贝使用
    GridIndex = None


class RoadNetwork(object):
    """由 `Network_Centerline` 构建的加权无向/有向图。"""

    def __init__(self, carto, snap_tol=25.0, default_speed=40.0, cell=100.0):
        self.snap_tol = float(snap_tol)
        self.default_speed = float(default_speed)
        self.cell = float(cell)
        self.nodes = []          # [(x, y)]
        self.adj = defaultdict(list)   # node_idx -> [(nbr_idx, seconds, meters)]
        self._snap_index = None
        self._build(carto)

    # ---------------------------------------------------------------- 构建
    def _build(self, carto):
        key_to_node = {}

        def node_of(x, y):
            k = (int(round(x / self.snap_tol)), int(round(y / self.snap_tol)))
            idx = key_to_node.get(k)
            if idx is None:
                idx = len(self.nodes)
                self.nodes.append((x, y))
                key_to_node[k] = idx
            return idx

        n_seg = n_edge = 0
        for f in carto.layer("roads"):
            if f.get("Object") not in ("Road", None):
                continue
            limit = f.get("Limit") or self.default_speed
            speed = float(limit) if limit and limit > 0 else self.default_speed
            one_way = (f.get("Direction") or "Both") == "Forward"
            parts = f.parts if f.parts and isinstance(f.parts[0], list) else [f.parts]
            for part in parts:
                if len(part) < 2:
                    continue
                n_seg += 1
                for i in range(1, len(part)):
                    (x0, y0), (x1, y1) = part[i - 1], part[i]
                    L = math.hypot(x1 - x0, y1 - y0)
                    if L <= 0.01:
                        continue
                    a, b = node_of(x0, y0), node_of(x1, y1)
                    if a == b:
                        continue
                    sec = L / (speed * 1000.0 / 3600.0)
                    self.adj[a].append((b, sec, L))
                    if not one_way:
                        self.adj[b].append((a, sec, L))
                    n_edge += 1
        self.n_segments = n_seg
        self.n_edges = n_edge
        self.snap_index = GridIndex([(x, y, i) for i, (x, y) in enumerate(self.nodes)],
                                    cell=max(50.0, self.cell))

    # ---------------------------------------------------------------- 查询
    @property
    def snap_index(self):
        return self._snap_index

    @snap_index.setter
    def snap_index(self, v):
        self._snap_index = v

    def nearest_node(self, x, y, radius=400.0):
        hits = self._snap_index.within(x, y, radius) if self._snap_index else []
        return hits[0][1] if hits else None

    def _dijkstra(self, src_idx, max_seconds=None):
        """单源最短路：返回 {node_idx: (seconds, meters)}。"""
        dist = {src_idx: (0.0, 0.0)}
        pq = [(0.0, src_idx)]
        adj = self.adj
        while pq:
            d, u = heapq.heappop(pq)
            cur = dist.get(u)
            if cur is None or d > cur[0] + 1e-9:
                continue
            if max_seconds is not None and d > max_seconds:
                continue
            for v, sec, m in adj.get(u, ()):  # noqa: E501
                nd = d + sec
                if max_seconds is not None and nd > max_seconds:
                    continue
                old = dist.get(v)
                if old is None or nd < old[0] - 1e-9:
                    dist[v] = (nd, cur[1] + m)
                    heapq.heappush(pq, (nd, v))
        return dist

    def shortest_path(self, x0, y0, x1, y1, search_radius=600.0):
        """返回 (米, 秒) 或 (None, None)——两点任一吸附不到路网就算不可达。"""
        a = self.nearest_node(x0, y0, search_radius)
        b = self.nearest_node(x1, y1, search_radius)
        if a is None or b is None:
            return None, None
        dist = self._dijkstra(a)
        hit = dist.get(b)
        return (hit[1], hit[0]) if hit else (None, None)

    def commute_profile(self, origins, dests, thresholds_km=(3, 5, 8, 12),
                        origin_weight=None, search_radius=600.0):
        """多源（就业中心）→ 多汇（住宅聚类）的**路网距离**画像。

        `origins` / `dests`: [(x, y)] 或 [(x, y, weight)]
        返回每个目标点的**到最近源点的路网米数**，以及按阈值分档的人口占比。
        只对每个源点跑一次 Dijkstra（源点通常只有 5–15 个），复杂度可控。
        """
        def unpack(seq):
            out = []
            for it in seq:
                if len(it) >= 3:
                    out.append((float(it[0]), float(it[1]), float(it[2])))
                else:
                    out.append((float(it[0]), float(it[1]), 1.0))
            return out

        srcs = unpack(origins)
        dsts = unpack(dests)

        # 每个源点一次 Dijkstra，得到"该源点到图内所有节点的米数"
        maps = []
        for (sx, sy, _w) in srcs:
            a = self.nearest_node(sx, sy, search_radius)
            if a is None:
                continue
            d = self._dijkstra(a)
            maps.append({k: v[1] for k, v in d.items()})
        if not maps:
            return None

        rows = []
        for (dx, dy, dw) in dsts:
            b = self.nearest_node(dx, dy, search_radius)
            best = None
            if b is not None:
                for m in maps:
                    v = m.get(b)
                    if v is not None and (best is None or v < best):
                        best = v
            rows.append({"x": dx, "y": dy, "weight": dw, "road_m": best,
                         "unreachable": best is None})

        total_w = sum(r["weight"] for r in rows) or 1.0
        bands = {}
        for T in thresholds_km:
            lim = T * 1000.0
            w = sum(r["weight"] for r in rows
                    if r["road_m"] is None or r["road_m"] > lim)
            bands[T] = {"weight_over": w, "share_over": w / total_w}
        reach = [r["road_m"] for r in rows if r["road_m"] is not None]
        return {"rows": rows, "bands": bands,
                "unreachable_weight": sum(r["weight"] for r in rows if r["unreachable"]),
                "unreachable_share": sum(r["weight"] for r in rows if r["unreachable"]) / total_w,
                "median_road_m": (sorted(reach)[len(reach) // 2] if reach else None),
                "max_road_m": (max(reach) if reach else None),
                "note": "路网距离（沿道路）。官方**未公布**四类出行的距离上限 → 多阈值只作敏感性分析，"
                        "不是「超了就一定搬走」的判定线。"}


def build_commute_inputs(carto, cell=400.0, top_jobs=12):
    """从 Carto 数据准备 T5c 的输入：就业中心（源）与住宅聚类（汇）。

    * 就业中心：400 m 网格聚合 `Employee`，取前 `top_jobs` 个格心（与 `city_report.py` §7 同口径）。
    * 住宅聚类：同样按 400 m 网格聚合 `Resident`，**每个格子作为一个汇点**，权重 = 该格居民数。
      这样输出就是"每片住宅到最近就业中心的路网距离"，可直接算人口加权占比。
    """
    grid_jobs = defaultdict(int)
    grid_pop = defaultdict(int)
    for b in carto.layer("buildings"):
        cx, cy = b.compute_centroid()
        k = (int(cx // cell) * cell, int(cy // cell) * cell)
        grid_jobs[k] += b.get("Employee") or 0
        grid_pop[k] += b.get("Resident") or 0
    centers = sorted(grid_jobs.items(), key=lambda kv: -kv[1])[:top_jobs]
    origins = [(k[0] + cell / 2, k[1] + cell / 2, v) for k, v in centers if v > 0]
    dests = [(k[0] + cell / 2, k[1] + cell / 2, v) for k, v in grid_pop.items() if v > 0]
    return origins, dests
