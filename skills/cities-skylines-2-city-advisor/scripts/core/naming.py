#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
naming.py —— **地点的命名与指代**

⭐ 唯一准则（`SKILL.md` 铁律 10）
--------------------------------
> **一切命名规则都应当以「能被人类快速定位和理解」为准则。**

这条准则不是审美偏好，它有**四条可判定的检验**（本模块全部实现，见 `audit_names()`）：

| # | 检验 | 判定标准 | 为什么 |
|---|---|---|---|
| ① | **好懂** | 主名必须是**人话**：`北端预留区`、`暮色路东工业区`、`消防站西地块` | 名字是给人看的，不是给数据库看的 |
| ② | **简短** | 主名 **≤ `NAME_MAX_CHARS`（16）字**；超过就该起别名 | 名字太长就退化成坐标，失去"快速"的意义 |
| ③ | **唯一** | 同一份报告里**一名一地、一地一名** | 否则读者要反复回查，越读越慢 |
| ④ | **可核验** | 括号里的**依据**必须落在**游戏里看得见的实物**上（路名 + 里程 / 地标 + 方位距离） | 快速定位的前提是能验证，不是靠信任 |

**排序原则**：**短名在前，依据在后** —— `北端预留区（繁荣路主段北端西北 545 m；地块号 1227156）`。
读者第一眼看到的是人话，需要核验时再看括号。

数据现实（决定了能做到哪一步）
--------------------------------
`MapTile` 的 `Name` 只是**地块流水号**（实测 232 个全是纯数字），
`Zoning_Boundary` 的 `Name` 只是**分区类目**（"欧洲中密度住宅""工业设施"…），
真正的地名只有三类：**4 个行政区名**、**路名**（`Network_*.Name`）、**设施名**（`POI_Location.Name`）。

⇒ **流水号不是"禁止使用"，而是"当不了主名"**（检验 ①）：游戏地图上不显示，玩家看了没反应。
它作**括号里的精确定位附注**是合适的 —— 那是它的正当用途。

别名（`aliases`）：让短名稳定下来的机制
----------------------------------------
自动生成的名字天然偏长（`羊城路主段 s≈570 m 西北 746 m`，22 字）。要落实检验 ②，
就给它起一个**人记得住的名字**，并把自动名降为括号里的依据：

```python
ALIASES = {'1227156': '北端预留区', '1227158': '北端产业预留区'}
nm = N.NameIndex(carto, aliases=ALIASES)
nm.tile_entry('1227156')
# → label : '北渡区·北端预留区（羊城路主段 s≈570 m 西北 746 m；地块号 1227156）'
#   short : '北端预留区'                       ← 图上标签 / 正文首次出现用它
#   basis : '羊城路主段 s≈570 m 西北 746 m；地块号 1227156'   ← 括号里的依据
```

用法
----
```python
from core import naming as N
nm = N.NameIndex(carto, aliases={'1227156': '北端预留区'})
nm.tile_entry('1227156')      # 见上（label / short / basis / where / km2 / zoning / buildings）
nm.short_label(x, y)          # 最短可读标签（画图用）
nm.describe(x, y, roads=['繁荣路'])       # 一句话定位（短名 + 依据）
nm.describe(x, y, brief=True)            # 只要短名，不要依据
nm.zone_mix(x, y)             # 分区构成 → '欧洲中密度住宅 45% / 低密度商业 25%'
nm.audit_names(['1227156', …])# ⭐ 整份报告的命名体检（四条检验）
N.check_name('北端预留区')     # 单个名字：① 好懂 ② 简短
N.check_basis('繁荣路主段 s≈570 m 西北 746 m')   # 依据：④ 可核验
```
"""

import math

#: 主名长度上限（字符）。超过它就该起别名了 —— 见准则检验 ②
NAME_MAX_CHARS = 16

#: 依据里必须出现的"游戏内实物"词（用于检验 ④ 可核验）
BASIS_TERMS = ("路", "街", "道", "站", "s≈", "s ", "里程", "地块号", "公园", "广场", "桥")

#: 不作为"地标"的 POI 类别（它们是线性/面状背景，不是可指认的点）
NON_LANDMARK = {
    "TrafficLight", "UtilityPylon", "StopBus", "StopSubway", "StopPassengerTrain",
    "PowerLine", "WaterPipe", "SewagePipe",
}

#: 玩家/游戏生成的**专有**设施名（这些才是好锚点）—— 按"指认力"从强到弱
LANDMARK_CATS = {
    "StopSubway", "StopPassengerTrain",
    "Park", "Post", "Communication", "Fire", "Health", "Police", "School",
    "TrainStation", "SubwayStation", "BusStation", "CargoTrainTerminal",
    "CargoHarbor", "Harbor", "Airport", "University", "College",
}

#: 强锚点类别（**唯一性强、玩家一眼能在地图上找到**）→ 优先用于命名
STRONG_LANDMARK = {
    "StopSubway", "StopPassengerTrain", "TrainStation", "SubwayStation", "BusStation",
    "CargoTrainTerminal", "CargoHarbor", "Harbor", "Airport", "University", "College",
    "Communication", "Fire", "Health", "Police", "School", "Post", "Park",
}

#: 分区类目 → 规划用途（用于"这一带是什么"）
ZONE_GROUP = {
    "Residential": "住宅",
    "Residential, Commercial": "住商混合",
    "Commercial": "商业",
    "Industrial": "工业",
    "Office": "办公",
    "Farmland": "农田",
    "Forestry": "林业",
    "Extractor": "采掘",
}


def check_name(name):
    """**主名自检**：能不能让人"快速理解"（铁律 10 检验 ① 好懂、② 简短）。

    返回 `{'ok': bool, 'issues': [...], 'len': n}`。
    检验 ③ 唯一（一名一地、一地一名）与 ④ 可核验（依据落在游戏实物上，见 `check_basis()`）
    是**整份报告层面**的，由 `audit_names()` 汇总。
    """
    issues = []
    if not name or not str(name).strip():
        return {"ok": False, "issues": ["空名字"], "len": 0}
    n = str(name).strip()
    if len(n) > NAME_MAX_CHARS:
        issues.append("太长（%d 字 > %d）：应起一个短名，把依据放进括号" % (len(n), NAME_MAX_CHARS))
    if n.replace(" ", "").isdigit():
        issues.append("是纯编号：游戏地图上不显示，人看了无法定位")
    elif n.upper().startswith("MAP TILE"):
        issues.append("是地块流水号：当不了主名（游戏里看不到这个词）")
    elif "地块号" in n:
        issues.append("主名里带「地块号」：编号应退到括号里当依据")
    return {"ok": not issues, "issues": issues, "len": len(n)}


def check_basis(basis):
    """**依据自检**：括号里的东西能不能让人"快速定位"（铁律 10 检验 ④ 可核验）。

    依据必须落在**游戏里看得见的实物**上：路名 + 里程 / 地标 + 方位距离 / 地块号。
    """
    issues = []
    b = str(basis or "").strip()
    if not b:
        return {"ok": False, "issues": ["没有给依据（括号为空）：读者无法核验"], "len": 0}
    if not any(t in b for t in BASIS_TERMS):
        issues.append("依据里没有可核验的实物（路名/里程/地标/地块号）：%r" % b)
    if not any(ch.isdigit() for ch in b):
        issues.append("依据里没有距离或里程数字：无法定位")
    return {"ok": not issues, "issues": issues, "len": len(b)}


def _bbox(rings):
    xs, ys = [], []
    for r in rings:
        xs += [p[0] for p in r]
        ys += [p[1] for p in r]
    return min(xs), min(ys), max(xs), max(ys)


def _rings(f):
    p = f.parts if f.parts and isinstance(f.parts[0], list) else [f.parts]
    return [r for r in p if len(r) >= 3]


def _centroid(rings):
    r = max(rings, key=len)
    x = sum(p[0] for p in r) / float(len(r))
    y = sum(p[1] for p in r) / float(len(r))
    return x, y


class NameIndex(object):
    """把坐标翻译成**可读地名**：行政区 → 最近路名与沿线里程 → 最近地标 → 分区构成。"""

    def __init__(self, carto, road_layer="roads", aliases=None):
        from . import roads as R                      # 延迟 import，避免循环
        self.carto = carto
        self._roads = R
        #: 人工短名表 `{地块号: 短名}`。**"简短"这条检验靠它落地** ——
        #: 自动生成的名字天然偏长，别名让短名稳定，自动名降为括号里的依据。
        self.aliases = dict(aliases or {})
        # --- 行政区（带多边形，不用 bbox 归属）---
        self.districts = []
        for f in carto.layer("areas"):
            if f.get("Object") != "District":
                continue
            rings = _rings(f)
            if not rings:
                continue
            self.districts.append({"name": f.get("Name"), "rings": rings,
                                   "bbox": _bbox(rings)})
        # --- 地标 POI ---
        self.landmarks = []
        for p in carto.pois:
            cat = p.get("Category") or ""
            if cat in NON_LANDMARK:
                continue
            nm = p.get("Name") or ""
            if not nm or nm.isdigit():
                continue
            x, y = p.compute_centroid()
            self.landmarks.append({"name": nm, "cat": cat, "x": x, "y": y})
        # --- 具名道路缓存（只建用得到的）---
        self._road_cache = {}
        self.road_layer = road_layer

    # ---------------------------------------------------------------- 行政区
    def district_at(self, x, y):
        """点落在哪个行政区（**多边形包含判定**，不是 bbox）。返回 `None` 表示不在任何区内。"""
        for d in self.districts:
            for r in d["rings"]:
                if _point_in_ring(x, y, r):
                    return d["name"]
        return None

    def district_near(self, x, y, max_dist=3000.0):
        """最近行政区（点在外时用），返回 `(名称, 距离)`。"""
        best = (None, 1e18)
        for d in self.districts:
            x0, y0, x1, y1 = d["bbox"]
            dx = max(x0 - x, 0.0, x - x1)
            dy = max(y0 - y, 0.0, y - y1)
            dist = math.hypot(dx, dy)
            if dist < best[1]:
                best = (d["name"], dist)
        return best if best[1] <= max_dist else (best[0], best[1])

    # ---------------------------------------------------------------- 道路
    def road(self, name):
        if name not in self._road_cache:
            self._road_cache[name] = self._roads.road_geometry(
                self.carto, name, layer=self.road_layer)
        return self._road_cache[name]

    def _all_named_roads(self, min_segments=3):
        """全部**像样的具名道路**（路段数 ≥ `min_segments`）。

        ⚠️ 必须同时过滤 **`Object`**：`Network_Centerline` 里装的不只是车行路 ——
        还有**地铁轨道 / 火车轨道 / 航道 / 步道**（实测这些也有路名，且会给最短路分析添乱）。
        只在调用方没给 `roads` 时兜底用；它要把每条路的连通段都算一遍，**比给名单慢**。
        """
        if getattr(self, "_roads_all", None) is None:
            cnt = {}
            for f in self.carto.layer(self.road_layer):
                nm = f.attrs.get("Name") or ""
                obj = f.attrs.get("Object") or ""
                cat = f.attrs.get("Category") or ""
                if not nm or obj != "Road":
                    continue
                if any(k in cat for k in ("Waterway", "Pathway", "Train", "Subway")):
                    continue
                cnt[nm] = cnt.get(nm, 0) + 1
            self._roads_all = sorted(n for n, c in cnt.items() if c >= min_segments)
        return self._roads_all

    def nearest_road(self, x, y, names=None, max_dist=1500.0):
        """最近具名道路 → `(路名, 沿线里程 s, 连通段号, 距离)`。

        `names` 给定时只在这些路里找（省时间）；否则扫描全部具名路段。
        """
        best = (None, None, None, 1e18)
        if names:
            for nm in names:
                g = self.road(nm)
                if not g.runs:
                    continue
                d, k, s = g.project(x, y)
                if d < best[3]:
                    best = (nm, s, k, d)
            return best if best[3] <= max_dist else (None, None, None, best[3])
        for f in self.carto.layer(self.road_layer):
            nm = f.attrs.get("Name") or ""
            if not nm:
                continue
            for part in (f.parts if f.parts and isinstance(f.parts[0], list) else [f.parts]):
                d, s = _proj_polyline(x, y, part)
                if d < best[3]:
                    best = (nm, s, None, d)
        return best if best[3] <= max_dist else (None, None, None, best[3])

    def road_axis(self, x, y, roads=None):
        """在一组道路里找**带里程**的最近者（`s` 只有在 `core/roads` 口径下才有意义）。

        返回 `(路名, 连通段号, 里程 s, 距离)`；找不到返回 `(None, None, None, 距离)`。
        `roads=None` 表示扫全部像样的具名道路（**慢**，仅兜底用）。
        """
        best = (None, None, None, 1e18)
        for nm in (roads if roads is not None else self._all_named_roads()):
            g = self.road(nm)
            if not g.runs:
                continue
            d, k, s = g.project(x, y)
            if d < best[3]:
                best = (nm, k, s, d)
        return best

    def _nearest_roads(self, x, y, top=2):
        """最近的 `top` 条具名道路（按距离）→ `[(路名, 连通段号, 里程 s, 距离), …]`。"""
        out = []
        for nm in self._all_named_roads():
            g = self.road(nm)
            if not g.runs:
                continue
            d, k, s = g.project(x, y)
            out.append((d, nm, k, s))
        out.sort()
        return [(nm, k, s, d) for (d, nm, k, s) in out[:max(1, top)]]

    def _nearest_road_by_boundary(self, rings, names, step=4):
        """**按多边形边界**取最近的具名路 → `(路名, 连通段号, 里程 s, 距离)`。

        为什么不用中心：地块常是狭长形，中心离最近的边界路可能上千米，
        而地块其实就贴着某条路（实测某地块中心 970 m、边界仅 184 m）。
        """
        pts = []
        for r in rings:
            pts += list(r)[::max(1, step)]
        best = (None, None, None, 1e18)
        for nm in names:
            g = self.road(nm)
            if not g.runs:
                continue
            for (px, py) in pts:
                d, k, s = g.project(px, py)
                if d < best[3]:
                    best = (nm, k, s, d)
        return best

    def _corridor_basis(self, corridor, rings, cx, cy, max_dist=600.0, prefer_within=1.1,
                        nearest=None):
        """地块到**本轮走廊路端点**的关系 → `'到繁荣路北端路口 121 m'`；不适用则返回 `None`。

        为什么值得优先用它：读者要定位的是"它和本轮讨论的主轴是什么关系"，
        而不是"它离哪条不相干的路最近"（实测某地块最近的路恰是与方案无关的一条，
        真正让人一眼找到的仍是"离繁荣路北端路口 121 m"）。

        `nearest` 给"到任意具名路的最近距离"时可作**显著性判据**：
        只有当"到走廊端点"不比它差太多（≤ `prefer_within` 倍）才采用 ——
        否则会拿一条远在天边的走廊去描述一块紧贴别的路的地。

        ⚠️ 采样必须**取全部顶点**（含环的所有点）：实测按每 4 点抽样会漏掉真正的最近点，
        把 121 m 量成 543 m（差 4 倍）。
        """
        g = self.road(corridor)
        if not g.runs:
            return None
        # ⚠️ 必须**逐边取垂足**求最近距离，不能只比顶点：
        # 实测某地块离路口 121 m 的最近点落在一条边的中段，按每 4 个顶点抽样会量成 543 m（差 4 倍）。
        best = (None, 1e18)
        for k in range(len(g.runs)):
            for which, zh in (("end", "北端"), ("start", "南端")):
                ex, ey, _s = g.terminal(k, which)
                for r in rings:
                    n = len(r)
                    for i in range(n):
                        ax, ay = r[i]
                        bx, by = r[(i + 1) % n]
                        dx, dy = bx - ax, by - ay
                        L2 = dx * dx + dy * dy
                        t = 0.0 if L2 <= 0 else max(
                            0.0, min(1.0, ((ex - ax) * dx + (ey - ay) * dy) / L2))
                        d = math.hypot(ex - (ax + t * dx), ey - (ay + t * dy))
                        if d < best[1]:
                            best = (zh, d)
        if not best[0] or best[1] > max_dist:
            return None
        # 显著性判据：**"到走廊端点"必须不比"到任意具名路"更远**（留 10% 容差）。
        # 否则会拿一条远在天边的走廊去描述一块紧贴别的路的地。
        if nearest is not None and best[1] > nearest * prefer_within:
            return None
        return "到%s%s路口 %.0f m" % (corridor, best[0], best[1])
    # ---------------------------------------------------------------- 地标
    def nearest_landmark(self, x, y, max_dist=2000.0, prefer=None, strong_only=False):
        """最近地标 → `{'name','cat','dist','x','y'}`。

        `prefer` 给类别集合时只在其中找；`strong_only=True` 时只考虑 `STRONG_LANDMARK`
        （**命名时应当用强锚点** —— 一个 `SolarPowerStation` 当路标远不如"地铁总站"好认）。
        """
        best = None
        for lm in self.landmarks:
            if prefer and lm["cat"] not in prefer:
                continue
            if strong_only and lm["cat"] not in STRONG_LANDMARK:
                continue
            d = math.hypot(lm["x"] - x, lm["y"] - y)
            if best is None or d < best["dist"]:
                best = {"name": lm["name"], "cat": lm["cat"], "dist": d,
                        "x": lm["x"], "y": lm["y"]}
        return best if best and best["dist"] <= max_dist else None

    @staticmethod
    def _dir8(dx, dy):
        """八方位（**报告里禁止裸坐标，方位词是允许的**）。"""
        if abs(dx) < 1e-9 and abs(dy) < 1e-9:
            return ""
        return ["东", "东北", "北", "西北", "西", "西南", "南", "东南"][
            int(((math.degrees(math.atan2(dy, dx)) + 22.5) % 360) // 45)]

    def short_label(self, x, y, roads=None, max_dist=2500.0):
        """给一个点起一个**短的、可当地名用的中文标签**（铁律 10 检验 ②：≤ 12 字最佳）。

        命名优先级（**唯一性 + 可核验性**，实测调过 6 版）：
        ① `<路名>沿线 s=… m 一带`（位置可精确定位在图上）→
        ② `<强地标> + 方位 + 距离`（玩家一眼能找到）→
        ③ `<行政区> + <八方位>`（最后兜底）。
        """
        if roads:
            nm, k, s, d = self.road_axis(x, y, roads=roads)
            if nm and d <= 400:
                return "%s%s s=%.0f m 一带" % (nm, "主段" if k == 0 else "连通段%d" % k, s)
        lm = self.nearest_landmark(x, y, max_dist=max_dist, strong_only=True)
        if lm:
            return "%s%s %.0f m" % (lm["name"], self._dir8(x - lm["x"], y - lm["y"]),
                                    lm["dist"])
        dn = self.district_at(x, y) or self.district_near(x, y)[0] or ""
        return "%s%s" % (dn, self._dir8(x, y))

    # ---------------------------------------------------------------- 组合
    def describe(self, x, y, roads=None, with_tile=None, brief=False):
        """把一个坐标说成一句人话（**这是报告里该用的写法**）。

        `brief=True` 只给短标签（正文里反复提到同一地点时用）；
        默认"**短标签 + 依据（括号）**" —— 这是铁律 10 的"短名在前、依据在后"。

        例：`北渡区 · 繁荣路主段 s 4820 m 一带（距 繁荣路主段 里程点 133 m；最近地标 火车站 1 060 m）`
        """
        parts = []
        dn = self.district_at(x, y)
        if not dn:
            dn, dd = self.district_near(x, y)
            if dn and dd < 1200:
                parts.append("%s（区界外 %.0f m）" % (dn, dd))
        if dn and not parts:
            parts.append(dn)
        loc = self.short_label(x, y, roads=roads, max_dist=600)
        if loc:
            parts.append(loc)
        if brief:
            return " · ".join(parts) if parts else "（无法定位到任何命名地物）"
        basis = self._basis_of(x, y, roads=roads)
        if basis:
            parts.append("（%s）" % basis)
        if with_tile:
            parts.append("地块号 %s" % with_tile)
        return " · ".join(parts) if parts else "（无法定位到任何命名地物）"

    def _basis_of(self, x, y, roads=None):
        """定位依据（进括号）：到路的距离 + 最近强地标。**距离为 0 的不写**（写了也不增加信息）。"""
        out = []
        if roads:
            nm, k, s, d = self.road_axis(x, y, roads=roads)
            if nm and d >= 10:
                out.append("距%s%s %.0f m" % (nm, "主段" if k == 0 else "连通段%d" % k, d))
        lms = self.nearest_landmark(x, y, max_dist=600, strong_only=True)
        if lms:
            out.append("最近地标 %s %.0f m" % (lms["name"], lms["dist"]))
        return "；".join(out)

    def zone_mix(self, x, y, radius=400.0, top=4):
        """以点为中心 `radius` 内的**分区构成**（按图斑数）→ `'欧洲中密度住宅 45%'` 这类。"""
        cnt = {}
        tot = 0
        for z in self.carto.zoning:
            zx, zy = z.compute_centroid()
            if math.hypot(zx - x, zy - y) > radius:
                continue
            nm = z.attrs.get("Name") or z.attrs.get("Zoning") or "?"
            cnt[nm] = cnt.get(nm, 0) + 1
            tot += 1
        if not tot:
            return "（%.0f m 内无分区图斑）" % radius
        items = sorted(cnt.items(), key=lambda t: -t[1])[:top]
        return " / ".join("%s %.0f%%" % (k, 100.0 * v / tot) for k, v in items)

    # ---------------------------------------------------------------- 地块
    def readable_name(self, tile_id):
        """只要一个**可读地名**（不含"（地块号 …）"后缀），适合画在图上当地名标签。

        失败返回 `None`。
        """
        e = self.tile_entry(tile_id)
        if not e:
            return None
        return e["short"]

    def tile_entry(self, tile_id, roads=None, landmark_max=2500.0, corridor=None):
        """给一个地块号，返回**可读名称 + 定位依据 + 现状**。

        `corridor` 给一条"本轮走廊路"（如 `'繁荣路'`）时，若该地块紧邻这条路的**端点**
        （≤300 m），依据优先写"**到 <路>北端/南端路口 N m**" —— 这比"最近的路"更好懂，
        因为它把地块挂在本轮讨论的主轴上（实测：某地块最近的路是一条不相关的路，
        但真正让读者定位的是"离繁荣路北端路口 121 m"）。

        返回 dict：`label`（**标准写法：短名在前、依据在后**）
        / `short`（主名）/ `basis`（括号里的依据）/ `where` / `km2` / `zoning` / `buildings` /
        `district` / `tile_id` / `name_check`（四条检验里的 ①②）。
        """
        tid = str(tile_id).replace("Map Tile ", "")
        f = None
        for t in self.carto.layer("areas"):
            if t.get("Object") == "MapTile" and (t.get("Name") or "").endswith(tid):
                f = t
                break
        if f is None:
            return None
        rings = _rings(f)
        x0, y0, x1, y1 = _bbox(rings)
        cx, cy = _centroid(rings)
        a2 = 0.0
        for r in rings:
            acc = 0.0
            n = len(r)
            for i in range(n):
                ax, ay = r[i]
                bx, by = r[(i + 1) % n]
                acc += ax * by - bx * ay
            a2 += abs(acc) / 2.0
        nz = nb = 0
        for z in self.carto.zoning:
            zx, zy = z.compute_centroid()
            if x0 <= zx <= x1 and y0 <= zy <= y1:
                nz += 1
        for b in self.carto.buildings:
            bx, by = b.compute_centroid()
            if x0 <= bx <= x1 and y0 <= by <= y1:
                nb += 1
        dn = self.district_at(cx, cy) or self.district_near(cx, cy)[0] or ""
        # 定位短语（可长，写进"它在哪"那一句）
        where = []
        nm = k = s = None
        d = 1e18
        if roads:
            nm, k, s, d = self.road_axis(cx, cy, roads=roads)
            if nm:
                where.append("%s%s s≈%.0f m %s %.0f m" % (
                    nm, "主段" if k == 0 else "连通段%d" % k, s,
                    "沿线" if d <= 600 else "外侧", d))
        else:
            nm, k, s, dd = self.road_axis(cx, cy, roads=self._all_named_roads())
            if nm:
                d = dd
                where.append("%s%s s≈%.0f m %s %.0f m" % (
                    nm, "主段" if k == 0 else "连通段%d" % k, s,
                    "沿线" if d <= 600 else "外侧", d))
        # 加"沿哪条路"的补充锚点：从**地块中心**看最近的两条具名路。
        # ⚠️ 用中心距离而不是边界距离 —— 边界最近点可能只是一角擦到，对读者没有指认意义。
        extra = self._nearest_roads(cx, cy, top=2)
        for (rn, rk, rs, rd) in extra:
            if rn == nm:
                continue
            where.append("最近道路 %s%s s≈%.0f m（%.0f m）" % (
                rn, "主段" if rk == 0 else "连通段%d" % rk, rs, rd))
        if nm is None and extra:
            nm, k, s, d = extra[0]
        # ⚠️ **标签用"边界最近的路"**：地块是狭长/不规则多边形，中心可能离最近的边界路很远
        # （实测某地块中心离最近具名路 970 m，而它的边界只隔 184 m）。
        # 命名要回答"它靠哪条路"，所以按**边界**取。
        bn, bk, bs, bd = self._nearest_road_by_boundary(rings, self._all_named_roads())
        lm = self.nearest_landmark(cx, cy, max_dist=landmark_max)
        if lm:
            where.append("最近地标 %s %.0f m" % (lm["name"], lm["dist"]))
        lm_strong = self.nearest_landmark(cx, cy, max_dist=landmark_max, strong_only=True)
        # 标签选择的核心权衡：**可核验性 > 唯一性 > 距离近**。
        # 实测教训：全用"最近的强地标"会把北部 7 块地全叫成"消防站（城市）北 1 170 m" —— 无法区分；
        # 而"某路 s≈… m 沿线 … m"既能区分、又能在地图上按里程核验。
        # 顺序：① 贴着大地标（≤200 m）→ 地标 + 方位 + 距离（最好认）；
        #       ② 紧邻具名路（≤200 m）→ 路 + 里程；
        #       ③ 强地标 ≤500 m → 地标 + 方位 + 距离；
        #       ④ 较近的路（≤600 m）→ 路 + 里程；
        #       ⑤ 边界最近的路（兜底）；⑥ 任意地标；⑦ 行政区 + 方位。
        lm_near = lm_strong and lm_strong["dist"] <= 200      # 贴着一个大地标：最好认
        lm_ok = lm_strong and lm_strong["dist"] <= 500

        def _road_phrase(rn, rk, rs, rd):
            """把"哪条路 + 里程"说成人话：**近才算"沿线"，远必须写成方位 + 距离**。

            ⚠️ 实测教训：地块离路 746 m 时若还写"沿线 746 m"，读者会以为是紧邻关系。
            """
            head = "%s%s s≈%.0f m" % (rn, "主段" if rk == 0 else "连通段%d" % rk, rs)
            if rd <= 400:
                return "%s 沿线 %.0f m" % (head, rd)
            rx, ry = self.road(rn).point_at(rk, rs)
            return "%s %s %.0f m" % (head, self._dir8(cx - rx, cy - ry), rd)

        if lm_near:
            core = "%s%s %.0f m" % (lm_strong["name"],
                                    self._dir8(cx - lm_strong["x"], cy - lm_strong["y"]),
                                    lm_strong["dist"])
        elif bn and bd <= 200:
            core = _road_phrase(bn, bk, bs, bd)
        elif lm_ok:
            core = "%s%s %.0f m" % (lm_strong["name"],
                                    self._dir8(cx - lm_strong["x"], cy - lm_strong["y"]),
                                    lm_strong["dist"])
        elif bn and bd <= 600:
            core = _road_phrase(bn, bk, bs, bd)
        elif nm and d <= 600:
            core = _road_phrase(nm, k, s, d)
        elif bn:
            core = _road_phrase(bn, bk, bs, bd)
        elif lm_strong:
            core = "%s%s %.0f m" % (lm_strong["name"],
                                    self._dir8(cx - lm_strong["x"], cy - lm_strong["y"]),
                                    lm_strong["dist"])
        elif lm:
            core = "%s%s %.0f m" % (lm["name"],
                                    self._dir8(cx - lm["x"], cy - lm["y"]), lm["dist"])
        else:
            core = "%s%s" % (dn, self._dir8(cx, cy))
        if bn and bd <= 200 and bn not in core:
            where.append("紧邻道路 %s" % _road_phrase(bn, bk, bs, bd))
        # ⭐ **短名在前，依据在后**（铁律 10 的落地）：
        #   有别名 → 主张用别名（人记得住），自动生成的名字降为括号里的**依据**；
        #   没别名 → 自动名当主名，地块号仍进括号。
        #
        # ⚠️ 依据必须**与 `core` 用同一个参照物**：`where[0]` 是"按地块中心最近的路"，
        #    而命名用的是"按边界最近的路"—— 两者可能不是同一条路（实测出现过
        #    主名指羊城路、依据却写银滩路）。所以依据直接用 `core` 本身。
        alias = self.aliases.get(tid)
        # 走廊优先：紧邻本轮走廊路的**端点**时，依据改成"到 <路><端>路口 N m"
        corridor_basis = self._corridor_basis(corridor, rings, cx, cy, nearest=bd) \
            if corridor else None
        if alias:
            short = alias
            basis = "%s；地块号 %s" % (corridor_basis or core, tid)
        else:
            short = core
            basis = "地块号 %s" % tid
        label = "%s·%s（%s）" % (dn, short, basis)
        chk = check_name(short)
        return {"tile_id": tid, "label": label, "short": short, "basis": basis,
                "where": " · ".join(where), "district": dn,
                "name_check": chk,
                "km2": a2 / 1e6, "zoning": nz, "buildings": nb,
                "cx": cx, "cy": cy, "bbox": (x0, y0, x1, y1)}

    def audit_names(self, tile_ids, aliases=None):
        """**整份报告层面的命名体检**（铁律 10 的四条检验）。

        ① 好懂 + ② 简短 → `check_name()`；
        ③ 唯一 → 短名**不得重复**（重名会让读者把两处混为一处）；
        ④ 可核验 → `check_basis()`，依据必须落在游戏里看得见的实物上。

        返回 `{'ok': bool, 'rows': [...], 'problems': [...]}`。
        """
        al = aliases if aliases is not None else self.aliases
        rows, problems = [], []
        seen = {}
        for tid in tile_ids:
            e = self.tile_entry(str(tid))
            if not e:
                problems.append("地块号 %s 找不到" % tid)
                continue
            nm = al.get(str(tid)) or e["short"]
            chk = check_name(nm)
            bchk = check_basis(e["basis"])
            rows.append({"tile_id": str(tid), "name": nm, "alias": bool(al.get(str(tid))),
                         "basis": e["basis"], "len": chk["len"],
                         "issues": chk["issues"] + bchk["issues"]})
            if nm in seen:
                problems.append("**重名**：%s 同时指 %s 与 %s —— 读者会把两处混为一处"
                                % (nm, seen[nm], tid))
            seen[nm] = str(tid)
            if not al.get(str(tid)) and chk["len"] > NAME_MAX_CHARS:
                problems.append("地块号 %s 没有别名，自动名 %d 字（>%d）→ 建议起一个短名"
                                % (tid, chk["len"], NAME_MAX_CHARS))
            for it in chk["issues"] + bchk["issues"]:
                problems.append("地块号 %s 的名字「%s」：%s" % (tid, nm, it))
        return {"ok": not problems, "rows": rows, "problems": problems}


def _point_in_ring(x, y, ring):
    """射线法（含边界视为在内）。"""
    inside = False
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xin = x1 + (y - y1) * (x2 - x1) / ((y2 - y1) or 1e-9)
            if x < xin:
                inside = not inside
    return inside


def _proj_polyline(x, y, pts):
    """点到折线的最近距离与该处累计弧长。"""
    best_d, best_s = 1e18, 0.0
    cum = 0.0
    for i in range(1, len(pts)):
        x1, y1 = pts[i - 1]
        x2, y2 = pts[i]
        dx, dy = x2 - x1, y2 - y1
        seg = math.hypot(dx, dy)
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 <= 0 else max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / L2))
        d = math.hypot(x - (x1 + t * dx), y - (y1 + t * dy))
        if d < best_d:
            best_d, best_s = d, cum + t * seg
        cum += seg
    return best_d, best_s
