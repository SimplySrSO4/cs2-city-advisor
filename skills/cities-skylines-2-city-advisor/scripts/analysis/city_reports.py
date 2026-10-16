#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
city_report.py —— 基于 Carto 导出数据生成城市诊断报告（Markdown）

输入：Carto 导出目录（含 Shapefile/ 与 GeoTIFF/），或本文件所在仓库的 Carto 目录。
输出：一份可直接交给决策的 Markdown 诊断报告，含
      1. 城市规模与区级结构（人口/岗位/职住比）
      2. 用地与分区结构（各分区建筑面积、占比、密度层级）
      3. 路网结构与拥堵风险（按道路等级/车道/限速统计，高速占比）
      4. 公共交通线路效率表（人/车、人/公里、人均站数、处置建议）
      5. 轨道走廊重叠诊断（两条线是否跑在同一走廊）
      6. 车站腹地（站点周边 400/600/800 m 的人口与岗位）
      7. 就业中心识别（岗位密度热点）
      8. 地形与可建地（高程/坡度的粗略判断）

用法：
    python city_report.py --carto "C:\\Users\\Devcl\\Desktop\\CSL2\\Carto" --out report.md
    python city_report.py --carto ... --json metrics.json      # 机器可读结果
"""

import argparse
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(HERE)          # scripts/
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from core.carto_reader import (  # noqa: E402
    CartoData,
    GridIndex,
    build_building_index,
    build_poi_index,
    find_carto_dir,
)
from analysis.report_base import TRANSPORT_CN, ZONE_CN, fmt, md_table  # noqa: E402,F401

# ------------------------------------------------------------------ 中英对照（仅用于报告可读性）
# 公共底座（对照表 / fmt / md_table）在 report_base.py，见文件头 import


# ------------------------------------------------------------------ 1. 城市与区级
# ------------------------------------------------------------------ 0.5 基础体检（第 1 层）
#: 人口分布"失衡"判据：某组团人口密度超过全城中位这个倍数 → 视为过密
FOUND_OVERCONCENTRATION = 2.5
#: 岗位/劳动力 供需代理的合理带（`Employee ÷ Labor`）——**游戏内经验带，不是官方数值**
FOUND_JOB_SUPPLY_BAND = (0.90, 1.15)
#: 支路 : 主干 的目标比值。来源：`references/50` 书 p153/第 8 节 ——
#: 「可把**支路总长 ≈ 主干路总长的 2.5~4 倍**作为粗略的校验比」。
#: 用**比值**判定，避免依赖"建成区面积"这个在 Carto 里只能粗估的分母。
FOUND_BRANCH_TO_ARTERIAL = (2.5, 4.0)
#: 各等级路网密度的现实标准带（km/km²，`references/50` 书 p152-153 表）。
#: ⚠️ **这是现实标准，游戏内无对应机制**（`SKILL.md` 铁律 4），只作相对参考。
FOUND_ROAD_DENSITY_STD = {"Highway": (0.3, 0.5), "Arterial": (0.8, 1.4), "Branch": (3.0, 4.0)}
#: 公交线网密度的现实标准（km/km²，`references/50` 书 p156）：市中心 3~4、边缘 2~2.5
FOUND_TRANSIT_DENSITY_STD = (2.0, 4.0)
#: 人口达到这个量级却完全没有轨道 → 规模与方式不匹配（`references/30` 官方里程碑：地铁/电车在此前已解锁）
FOUND_RAIL_EXPECT_POP = 60000


def analyze_foundation(carto, city=None, roads=None, cmap=None, zoning=None):
    """**第 1 层「基础体检」** —— 回答"这座城市的基础打对了没有"。

    按 `SKILL.md` 核心目标的分层，本节必须在任何税收建议之前看。四项基础：

    ① **人口分布均衡** —— 各组团人口密度相对全城中位的偏离；识别"过密/过疏"。
       判据是**失衡**而不是"不均匀"（适度集中是效率来源）。
    ② **失业率** —— Carto **没有失业字段**（已核实全部图层）。
       这里给 `岗位 ↔ 劳动力` 的**供需代理** + 明确要求玩家补游戏内读数。
    ③ **公共交通与城市规模匹配** —— 线网密度、配车、有无轨道。
    ④ **路网分级** —— **支路:主干 比值**（比值口径，不依赖粗估面积）+ 各等级密度 + 单车道瓶颈段。

    ⚠️ 引用的密度带都是**现实标准**（`references/50`），游戏内无对应机制，
    只用于**相对**判断，不得当游戏数值。

    返回每项含 `status`（`达标`/`偏弱`/`不达标`/`未知`）、`detail` 与 `fix`。
    """
    import numpy as np
    out = {"items": [], "blocking": [], "n_blocking": 0}

    pop = (city or {}).get("population") or carto.total_population()
    jobs = (city or {}).get("jobs") or carto.total_jobs()
    out["population"] = pop
    out["jobs"] = jobs

    # 建成区面积：用"有建筑的 100 m 格"估计 —— 比 bbox 合理得多（bbox 含大片空地）
    cells = set()
    for b in carto.layer("buildings"):
        x, y = b.compute_centroid()
        cells.add((int(x // 100.0), int(y // 100.0)))
    developed_km2 = len(cells) * 0.01
    out["developed_km2"] = developed_km2

    # ---------- ① 人口分布均衡 ----------
    gs = list(getattr(cmap, "groups", None) or [])
    item = {"key": "distribution", "name": "人口分布均衡", "status": "未知", "detail": [], "fix": None}
    if gs:
        dens = [(g["res"] / g["area_km2"]) if g.get("area_km2") else 0.0 for g in gs]
        pos = [d for d in dens if d > 0]
        med = float(np.median(pos)) if pos else 0.0
        item["detail"].append("组团 %d 个；组团人口密度中位 **%s 人/km²**" % (len(gs), fmt(med, 0)))
        over = [g for g, d in zip(gs, dens) if med and d > med * FOUND_OVERCONCENTRATION]
        under = [g for g, d in zip(gs, dens) if med and 0 < d < med / 4.0 and g["res"] > 0]
        share = sorted((g["res"] / pop) for g in gs if pop) if pop else []
        top1 = share[-1] if share else 0.0
        item["detail"].append("人口最大组团占全城 **%.0f%%**" % (100 * top1))
        h = None
        if share and len(share) > 1:
            h = -sum(s * math.log(s) for s in share if s > 0) / math.log(len(share))
            item["detail"].append("分布均匀度（归一化熵）**%.2f**（1=完全均匀，0=全挤在一处）" % h)
        if over:
            item["status"] = "不达标"
            item["detail"].append("⚠️ **过密组团 %d 个**（密度 > 中位 %.1f 倍）：%s"
                                  % (len(over), FOUND_OVERCONCENTRATION,
                                     "、".join(g["name"] for g in over[:4])))
            item["fix"] = ("把新增住宅/岗位**导向过疏侧**（补路 + 补公交 + 补服务），"
                           "并在过密组团**停止继续加密**；**不要靠拆楼降密度**。")
        elif top1 > 0.6:
            item["status"] = "偏弱"
            item["detail"].append("人口高度集中在单一组团（%.0f%%）—— 抗风险能力弱，"
                                  "一条走廊出问题就影响大半城市" % (100 * top1))
            item["fix"] = "培育第二、第三组团：把下一批岗位与服务放到人口次集中处。"
        else:
            item["status"] = "达标"
            item["fix"] = "保持：新增开发继续按组团均衡分摊。"
        if under:
            item["detail"].append("过疏组团：%s" % "、".join(g["name"] for g in under[:4]))
        item["entropy"] = h
        item["top1_share"] = top1
        item["over"] = [g["name"] for g in over]
    else:
        item["detail"].append("未识别出组团 → 无法判断分布均衡")
        item["fix"] = "确认 Carto 导出含 `Building_Boundary` 的人口字段。"
    out["items"].append(item)

    # ---------- ② 失业率 ----------
    item = {"key": "unemployment", "name": "失业率", "status": "未知", "detail": [], "fix": None}
    labor = sum((f.get("Labor") or 0.0) for f in carto.layer("buildings"))
    if not labor:
        labor = sum((d.get("Labor") or 0) for d in carto.districts())
    emp = sum((f.get("Employee") or 0.0) for f in carto.layer("buildings"))
    supply = (emp / labor) if labor else None
    item.update({"labor": labor, "employee": emp, "supply_ratio": supply})
    lo, hi = FOUND_JOB_SUPPLY_BAND
    item["detail"].append("⚠️ **Carto 没有失业字段**（已核实全部图层字段）→ "
                          "**必须由玩家读游戏内 Unemployment 百分比**，代理不能替代。")
    if supply is None:
        item["detail"].append("连 `Labor`/`Employee` 都没有 → 无法给供需代理")
        item["fix"] = "问玩家：游戏内 Unemployment 百分比。"
    else:
        item["detail"].append("供需代理：岗位 ÷ 劳动力 = **%.3f**（%s 岗 / %s 人）"
                              % (supply, fmt(emp, 0), fmt(labor, 0)))
        item["detail"].append("⚠️ 这**不是失业率**：岗位不足时居民会**出城就业**"
                              "（游戏里不显示为失业，但**这些人不向本城缴税**）；"
                              "而学历不匹配造成的**结构性失业**在供需比里完全看不出来。")
        if supply < lo:
            item["status"] = "偏弱"
            item["detail"].append("岗位比劳动力少 **%.0f%%** → 缺口约 **%s 个岗位**，"
                                  "会有居民出城就业" % (100 * (1 - supply), fmt(labor - emp, 0)))
            item["fix"] = "补岗位用地（优先办公/商业这类高税基用途），**不是继续加住宅**。"
        elif supply > hi:
            item["status"] = "偏弱"
            item["detail"].append("岗位比劳动力多 **%.0f%%** → 企业招不满人，"
                                  "产出受损（公司利润因此下降）" % (100 * (supply - 1)))
            item["fix"] = "补住宅，并确保**学历结构**匹配岗位需求。"
        else:
            item["detail"].append("供需基本平衡（%.2f–%.2f 带内，**游戏内经验带，非官方数值**）" % (lo, hi))
        item["fix"] = ("**仍必须问玩家游戏内 Unemployment 百分比** —— "
                       "供需平衡也可能伴随结构性失业（学历不匹配）。"
                       + (" " + (item["fix"] or "") if item["fix"] else ""))
    out["items"].append(item)

    # ---------- ③ 公共交通与城市规模匹配 ----------
    # ⚠️ 口径限制：**只算客运线路**（`RoutePassenger`）。
    # 货运铁路 / 货运航线（`RouteCargo`）的 Passenger 恒为 0，混进来会把
    # 「线路数 / 线网 km / 方式构成」全部算歪；货运类数据只在工业部分做辅助分析。
    item = {"key": "transit", "name": "公共交通与城市规模匹配", "status": "未知", "detail": [], "fix": None}
    routes = passenger_routes(carto)
    veh = sum((f.get("Vehicle") or 0) for f in routes)
    # ⭐ 线网里程 = **逐线路长度相加**（唯一口径）。线路里有掉头 / 绕行 / 环线，
    # 任何"线网统计口径"的另一种合计都会与逐线明细对不上 —— 不一致时以逐线路相加为准。
    rlen = sum(route_length_km(f) for f in routes)
    _susp = [f for f in routes if not (f.get("Vehicle") or 0)]
    modes = Counter(f.get("Transport") for f in routes)
    rail = modes.get("Train", 0) + modes.get("Subway", 0) + modes.get("Tram", 0)
    tdens = (rlen / developed_km2) if developed_km2 else None
    item.update({"routes": len(routes), "vehicles": veh, "route_km": rlen,
                 "suspended_routes": len(_susp),
                 "rail_routes": rail, "density_km_per_km2": tdens, "modes": dict(modes)})
    item["detail"].append("线路 **%d** 条（轨道 %d；**其中停用 %d 条**）、在跑配车 **%s** 辆、"
                          "线网 **%s km**（**逐线路长度相加**，唯一口径）"
                          "（**只含客运线路；货运铁路/货运航线不并入本项**）"
                          % (len(routes), rail, len(_susp), fmt(veh, 0), fmt(rlen, 1)))
    item["detail"].append("人口 **%s**、建成区（有建筑的 100 m 格）**%s km²**"
                          % (fmt(pop, 0), fmt(developed_km2, 2)))
    if tdens:
        item["detail"].append("公交线网密度 %s km/km² —— ⚠️ **此数与现实标准（2–4 km/km²）"
                              "不可直接比较**：CSL2 的「米」与现实「米」不对应、"
                              "人口规模也不对应（现实规划教材对这一点有明确警告）。"
                              "**只用于同城纵向比较。**"
                              % fmt(tdens, 2))
    # 判定只用**结构性**判据（不依赖与现实单位可比）
    cov_pop = None
    try:
        cov = analyze_stop_coverage(carto)
        cov_pop = ((cov or {}).get("radii") or {}).get(500, {}).get("pop_share")
    except Exception:      # noqa: BLE001
        cov_pop = None
    item["stop_coverage_pop"] = cov_pop
    if cov_pop is not None:
        item["detail"].append("500 m 站点覆盖人口 **%.0f%%**（报告 第 15 节 同口径）" % (100 * cov_pop))
    if cov_pop is not None and cov_pop < 0.80:
        item["status"] = "不达标"
        item["detail"].append("⚠️ 站点覆盖人口不足 80% —— **公交网络没跟上建成区扩张**")
        item["fix"] = ("先把线路/站点补到**已建成但无覆盖**的片区（报告 第 15 节 有未覆盖热点），"
                       "再谈加密班次；**不要只在线网密集处重复布线**。")
    elif rail == 0 and pop >= FOUND_RAIL_EXPECT_POP:
        item["status"] = "偏弱"
        item["detail"].append("人口已达 %s 却**一条轨道都没有** —— 规模到了该上中运量的时候"
                              % fmt(pop, 0))
        item["fix"] = ("在**通勤主轴**（报告 第 1.1 节 的人口最集中组团 ↔ 岗位密度最高组团）"
                       "先上**一段**中运量，不要全网铺开。")
    else:
        item["status"] = "达标"
        item["fix"] = "维持：新增片区同步延伸线路，不要让覆盖掉队。"
    out["items"].append(item)

    # ---------- ④ 路网分级 ----------
    item = {"key": "roadhier", "name": "路网分级规划", "status": "未知", "detail": [], "fix": None}
    if roads and roads.get("total_km"):
        bycat = roads.get("by_category") or {}

        def _km(pred):
            return sum(v["km"] for k, v in bycat.items() if pred(k))

        hw = _km(lambda k: "Highway" in k)
        lg = _km(lambda k: "Large" in k)
        md = _km(lambda k: "Medium" in k)
        sm = _km(lambda k: "Small" in k)
        tot = roads["total_km"]
        arterial = lg + md
        # ⭐ 主判据用**比值**：无量纲、不受"游戏米 vs 现实米"的尺度问题影响
        ratio = (sm / arterial) if arterial else None
        hw_ratio = (hw / tot) if tot else 0.0
        item.update({"highway_km": hw, "arterial_km": arterial, "branch_km": sm,
                     "branch_to_arterial": ratio, "highway_share": hw_ratio})
        item["detail"].append("已解锁路网 **%s km**：高速 %s（%.0f%%）/ 大路 %s / 主干 %s / 支路 %s"
                              % (fmt(tot, 1), fmt(hw, 1), 100 * hw_ratio,
                                 fmt(lg, 1), fmt(md, 1), fmt(sm, 1)))
        rlo, rhi = FOUND_BRANCH_TO_ARTERIAL
        if ratio is not None:
            item["detail"].append("⭐ **支路 : 干路（大路+主干）= %.2f : 1**　"
                                  "现实规范的校验比 %s–%s : 1（现实标准，游戏内无对应机制）—— "
                                  "**这是比值口径，不受游戏/现实尺度差异影响，是本项的主判据**"
                                  % (ratio, fmt(rlo, 1), fmt(rhi, 1)))
        if developed_km2:
            item["detail"].append("（附）各等级密度：高速 %.2f、干路 %.2f、支路 %.2f km/km² —— "
                                  "⚠️ **与现实标准带不可直接比较**（游戏米≠现实米），"
                                  "**只作同城纵向比较用**，不参与判定"
                                  % (hw / developed_km2, arterial / developed_km2, sm / developed_km2))
        smoke = []
        if ratio is not None and ratio < rlo:
            smoke.append("**支路严重不足**（%.2f < %.1f）—— 末端分流全靠干道，"
                         "所有车被迫挤到主干上，这是拥堵的**结构性**原因" % (ratio, rlo))
        if ratio is not None and ratio > rhi:
            smoke.append("支路过多（%.2f > %.1f）—— 交叉口过密会反过来压低干道效率" % (ratio, rhi))
        if hw_ratio > 0.25:
            smoke.append("高速占**已解锁**路网 **%.0f%%** —— 偏高，"
                         "注意区分「玩家修的穿城段」与「已剔除的地图自带段」（见第 3 节）"
                         % (100 * hw_ratio))
        if not smoke:
            item["status"] = "达标"
            item["fix"] = "维持分级：新增片区**先铺支路网**，再按需接主干。"
        else:
            item["status"] = "不达标"
            for s in smoke:
                item["detail"].append("⚠️ " + s)
            item["fix"] = ("按**各等级功能**分别补：**支路成网**（末端分流）→ 主干只承担跨区 → "
                           "高速只服务城际与过境（**不穿城**）。**不是把某一等级无限加宽。**")
        # ⭐ 铁律 12：非解锁区路网是**地图自带**，与玩家的规划失误无关 ——
        # 这一项的所有判据都用「已解锁内」口径，必须把这件事写在明面上。
        _native = roads.get("highway_km_map_native") or 0.0
        _native_all = roads.get("total_km_map_native") or 0.0
        if _native > 0.05 or _native_all > 0.05:
            item["detail"].append(
                "ℹ️ **本项只统计「已解锁内」路网**：另有 **高速 %.1f km / 路网 %.1f km** "
                "位于**非解锁区**，属**地图自带资源**（玩家未建、不拥有），"
                "**已整体剔除，不参与等级结构判定**。"
                % (_native, _native_all))
    else:
        item["detail"].append("无路网数据")
        item["fix"] = "检查 Carto 导出是否含 `Network_Centerline`。"
    out["items"].append(item)

    for it in out["items"]:
        if it["status"] == "不达标":
            out["blocking"].append(it["name"])
    out["n_blocking"] = len(out["blocking"])
    out["gate_open"] = (out["n_blocking"] == 0)
    out["policy"] = ("**基础未全部达标 → 税收类建议一律降级为「暂缓」**，先修上面的项目。"
                     if out["n_blocking"] else
                     "四项基础未发现明显不达标 → 可以进入税收优化（第 2 层）。")
    return out


# ------------------------------------------------------------------ 1. 规模与职住比
def analyze_city(carto):
    districts = []
    for d in carto.districts():
        districts.append({
            "name": d.get("Name"),
            "residents": d.get("Resident") or 0,
            "employees": d.get("Employee") or 0,
            "area_m2": d.polygon_area(),
        })
    pop = sum(d["residents"] for d in districts)
    jobs = sum(d["employees"] for d in districts)
    if pop == 0 and jobs == 0:
        # 退回建筑统计（有些导出没有 District）
        pop = carto.total_population()
        jobs = carto.total_jobs()
    # 建筑逐栋汇总：与地块汇总不是同一口径，报告里两个都给出并标注来源
    bpop = carto.total_population()
    bjobs = carto.total_jobs()
    return {
        "districts": districts,
        "population": pop,
        "jobs": jobs,
        "job_housing_ratio": (jobs / pop) if pop else None,
        "building_totals": {"population": bpop, "jobs": bjobs},
        "bounds": carto.city_bounds(),
        "built_bounds": carto.built_bounds(),
        "unlocked_tiles": len(carto.unlocked_tiles()),
    }


# ------------------------------------------------------------------ 2. 用地结构
def analyze_zoning(carto):
    """用地/分区结构。

    重要：Carto 的 Zoning_Boundary 图斑**不是地块边界，而是 8 m×8 m 的栅格单元**
    （实测每图斑 area ≈ 64 m² 且高度一致）。因此"图斑面积合计"**约等于建成占地面积，
    不等于用地面积**，且会有系统性低估。报告里必须点明这一点，否则会被当成"用地结构"误用。
    """
    by_zone = defaultdict(lambda: {"area": 0.0, "count": 0, "areas": []})
    names = Counter()
    for f in carto.layer("zoning"):
        z = f.get("Zoning") or "None"
        a = f.polygon_area()
        by_zone[z]["area"] += a
        by_zone[z]["count"] += 1
        if len(by_zone[z]["areas"]) < 400:
            by_zone[z]["areas"].append(a)
        if f.get("Name"):
            names[(z, f.get("Name"))] += 1
    total = sum(v["area"] for v in by_zone.values()) or 1.0
    tile_like = _is_tile_like(by_zone)
    rows = []
    for z, v in sorted(by_zone.items(), key=lambda kv: -kv[1]["area"]):
        rows.append({
            "zoning": z,
            "zoning_cn": ZONE_CN.get(z, z),
            "area_km2": v["area"] / 1e6,
            "share": v["area"] / total,
            "count": v["count"],
        })
    # 建筑层面的用途统计（更能反映实际吸纳）
    bz = Counter()
    b_res = defaultdict(int)
    b_emp = defaultdict(int)
    density_names = Counter()
    for b in carto.layer("buildings"):
        z = b.get("Zoning") or "None"
        bz[z] += 1
        b_res[z] += b.get("Resident") or 0
        b_emp[z] += b.get("Employee") or 0
        nm = b.get("Name") or ""
        for key, label in (("高密度", "高密度"), ("中密度", "中密度"),
                           ("低密度", "低密度"), ("排屋", "排屋"), ("四合院", "低密度四合院")):
            if key in nm:
                density_names[label] += 1
                break
    return {"zones": rows, "total_area_km2": total / 1e6,
            "tile_like": tile_like,
            "building_zones": dict(bz), "building_residents": dict(b_res),
            "building_employees": dict(b_emp),
            "density_names": dict(density_names),
            "top_building_names": names.most_common(20)}


def _is_tile_like(by_zone, tol=0.02):
    """判断图斑面积是否高度一致（≈固定栅格单元）→ 面积不可当用地面积用。"""
    areas = []
    for v in by_zone.values():
        areas.extend(v["areas"])
    if len(areas) < 20:
        return False
    mean = sum(areas) / len(areas)
    if mean <= 0:
        return False
    var = sum((a - mean) ** 2 for a in areas) / len(areas)
    return (var ** 0.5) / mean < tol


# ------------------------------------------------------------------ 3. 路网
def analyze_roads(carto):
    roads = carto.layer("roads")
    by_cat = defaultdict(lambda: {"n": 0, "len": 0.0, "lanes": 0.0, "len_full": 0.0})
    by_dir = defaultdict(float)
    by_asset = Counter()
    by_limit = Counter()
    total_len = 0.0
    total_len_full = 0.0
    rail_len = rail_len_full = 0.0
    out_of_bounds = 0
    bb = carto.city_bounds()
    for r in roads:
        if r.get("Object") not in ("Road", "Track", None):
            continue
        L = r.line_length()                       # 已按"是否解锁"裁剪（见 apply_unlocked_clip）
        Lf = r.full_line_length()                 # 全长，用于对照
        total_len += L
        total_len_full += Lf
        cat = r.get("Category") or "?"
        if "Train" in cat or "Subway" in cat:
            rail_len += L
            rail_len_full += Lf
        by_cat[cat]["n"] += 1
        by_cat[cat]["len"] += L
        by_cat[cat]["len_full"] += Lf
        by_cat[cat]["lanes"] += r.get("Lane") or 0
        by_dir[r.get("Direction") or "?"] += L
        by_asset[r.get("Asset") or "?"] += 1
        by_limit[r.get("Limit")] += 1
        if bb and (r.bbox[1] < bb[1] or r.bbox[3] > bb[3]):
            out_of_bounds += 1
    # 建成区口径：只用有建筑的地块 bbox
    b = carto.built_bounds() or carto.city_bounds()
    built_area_km2 = None
    if b:
        built_area_km2 = (b[2] - b[0]) * (b[3] - b[1]) / 1e6
    highway_len = sum(v["len"] for k, v in by_cat.items() if "Highway" in k)
    highway_len_full = sum(v["len_full"] for k, v in by_cat.items() if "Highway" in k)
    # 高速在数据里几乎都是单向记录 → 双向路幅各占一条中心线
    hw_dir = {}
    for k, v in by_cat.items():
        if "Highway" in k:
            hw_dir[k] = v["len"]
    return {
        "segments": len(roads),
        "total_km": total_len / 1000.0,
        "total_km_full": total_len_full / 1000.0,
        "rail_km": rail_len / 1000.0,
        "rail_km_full": rail_len_full / 1000.0,
        "rail_share": (rail_len / total_len) if total_len else None,
        "clip_ratio": (total_len / total_len_full) if total_len_full else None,
        "clip_note": getattr(carto, "_clip_note", None),
        "by_category": {k: {"n": v["n"], "km": v["len"] / 1000.0,
                            "km_full": v["len_full"] / 1000.0,
                            "avg_lanes": (v["lanes"] / v["n"]) if v["n"] else 0}
                        for k, v in by_cat.items()},
        "by_direction_km": {k: v / 1000.0 for k, v in by_dir.items()},
        "by_asset": by_asset.most_common(30),
        "by_limit": by_limit.most_common(),
        "highway_km": highway_len / 1000.0,
        "highway_km_full": highway_len_full / 1000.0,
        # ⭐ 铁律 12：非解锁区路网 = **地图自带资源**（玩家没修、不拥有、无权规划）。
        # 单独把这个量算出来，让"已剔除多少"在报告里可见，而不是悄悄消失。
        "highway_km_map_native": (highway_len_full - highway_len) / 1000.0,
        "total_km_map_native": (total_len_full - total_len) / 1000.0,
        "highway_share": highway_len / total_len if total_len else None,
        "highway_share_full": (highway_len_full / total_len_full) if total_len_full else None,
        "road_density_km_per_km2": (total_len / 1000.0 / built_area_km2) if built_area_km2 else None,
        "built_area_km2": built_area_km2,
        "built_bounds": b,
        "segments_outside_city_bounds": out_of_bounds,
    }


# ---------------------------------------------------------------- 客运 / 货运 口径分界（唯一实现）
#: `Route_Centerline.Object` 的取值：`RoutePassenger` / `RouteCargo`。
#: ⚠️ **凡"客运"指标（线路效率、走廊重叠、车站腹地、站点覆盖、走廊归因、线网规模）
#: 一律只取 `RoutePassenger`**；`RouteCargo`（货运铁路 / 货运航线）不进任何客运口径 ——
#: 它们的 `Passenger` 恒为 0，混进来会把中位数与总量一起拉偏。
#: 货运类数据只在**工业部分**做辅助分析（见 `SKILL.md` 第 2 节「货运与产业链」与报告工业小节）。
CARGO_ROUTE_OBJECT = "RouteCargo"
PASSENGER_ROUTE_OBJECT = "RoutePassenger"

#: 客运站点类别白名单（POI_Location.Category 精确匹配）。
#: ⚠️ **用车库/车辆段当车站是错的**：`DepotSubway`（地铁总站）/`DepotBus`（公交总站）/
#: `DepotTrain` 是 depot（车辆段），只负责给线路提供车辆，**不是站点** ——
#: 实测它们的 `Category` 本来就不带 `Stop` 前缀，因此**永远不会**进入本白名单；
#: 这里用白名单（而不是 `startswith("Stop")`）是为了让"排除"成为显式行为，
#: 避免将来出现 `StopSubwayYard` 这类新类别时被 `startswith` 误收。
PASSENGER_STOP_CATS = ("StopBus", "StopSubway", "StopPassengerTrain")
#: 货运站点类别（**不得计入客运站点覆盖**）：货运铁路站点 / 货运码头。
CARGO_STOP_CATS = ("StopCargoTrain", "StopCargoShip", "StopCargoAirport")
#: 货运终端建筑（货运港口 / 货运铁路终端 / 机场货运）—— 归工业部分做集疏运辅助分析。
CARGO_TERMINAL_CATS = ("StopCargoTrain", "StopCargoShip", "BuildingCargoTrain", "BuildingCargoShip",
                       "BuildingCargoAirport", "StopCargoAirport")

#: ⭐ **单车容量（人/辆）—— 游戏内可信数值（玩家提供）**。
#: 用途：把「人/车」归一化成**跨交通方式可比**的效率 —— 地铁一辆车装得下 1080 人、公交只有 80 人，
#: 直接比"每辆车拉多少人"会让车大的方式永远排最后，结论会反过来。
#: ⚠️ 表里**没有的方式（有轨电车 / 单轨 / 渡轮 / 缆车…）不做容量归一** —— 留空并注明，不要猜。
VEHICLE_CAPACITY = {
    "Bus": 80,        # 公交
    "Subway": 1080,   # 地铁
    "Train": 840,     # 客运火车
}


def route_length_km(f):
    """单条线路的里程（km）—— **全报告唯一的线路里程口径**。

    * 优先用 Carto 的 `Length` 字段（游戏自己给的线路长度，含往返）；
    * 老版导出缺该字段时退回几何长度（`analyze_routes` 会为这种情况记一条告警）。

    ⭐ **线路总里程 = 逐线路调用本函数后相加**。线路里有**掉头 / 绕行 / 环线**，
    任何"线网统计口径"的另一种合计都会与逐线明细对不上 ——
    **两处数字不一致时以逐线路相加为准**，并且**不再保留另一套合计去核销差额**。
    """
    raw = f.get("Length")
    if raw:
        return raw / 1000.0
    return f.line_length() / 1000.0


def is_passenger_route(f):
    """这条线路算不算**客运**线路（`Route_Centerline.Object`）。

    * `Object == RouteCargo` → False（货运铁路 / 货运航线，归工业部分）；
    * `Object == RoutePassenger` → True；
    * `Object` 缺失（老版导出没有该字段）→ True，绝不误删客运线。
    """
    return (f.get("Object") or PASSENGER_ROUTE_OBJECT) != CARGO_ROUTE_OBJECT


def is_cargo_route(f):
    """这条线路是不是**货运**线路（只用于工业部分的辅助分析）。"""
    return not is_passenger_route(f)


def passenger_routes(carto):
    """`carto.layer("routes")` 里的**客运**线路（客运口径的唯一入口）。"""
    return [f for f in carto.layer("routes") if is_passenger_route(f)]


def cargo_routes(carto):
    """`carto.layer("routes")` 里的**货运**线路（工业部分辅助口径）。"""
    return [f for f in carto.layer("routes") if is_cargo_route(f)]


def passenger_stop_categories():
    """客运站点类别白名单（供站点覆盖 / 走廊逐站分析使用）。"""
    return PASSENGER_STOP_CATS


# ------------------------------------------------------------------ 4. 公交线路效率
def analyze_routes(carto, speed_kmh=20.0):
    """**客运**线路效率表。

    ⚠️ **口径限制**：只统计 `Object == RoutePassenger` 的线路。
    货运铁路 / 货运航线（`RouteCargo`）**不进本表** —— 它们的 `Passenger` 恒为 0，
    混进来会让「人/车」中位数、总乘客量、按方式汇总全部失真
    （实测某城 2 条货船线的 `Passenger=0` 会把中位数拉低）。
    货运类数据的用法见 `SKILL.md` 第 2 节「货运与产业链」（放在**工业部分**做辅助分析）。
    """
    routes = []
    warnings = []
    for f in carto.layer("routes"):
        if not is_passenger_route(f):
            continue
        raw_len = f.get("Length")
        if not raw_len:
            warnings.append("线路「%s」缺少 Length 字段，已回退用几何长度（口径可能不一致，注意双向重复）"
                            % f.get("Name"))
        # ⭐ 里程口径：**逐线路长度相加**（唯一口径，见 `route_length_km`）
        total_len_km = route_length_km(f)
        # Carto 的 Length 是线路总长（含往返）—— 站距必须用单程长度
        one_way_km = total_len_km / 2.0
        veh = f.get("Vehicle") or 0
        pax = f.get("Passenger") or 0
        stops = f.get("Stop") or 0
        usage = f.get("Usage")
        transport = f.get("Transport")
        # ⭐ 单车容量与归一化载客效率（游戏内可信容量；未知方式不做归一）
        cap = VEHICLE_CAPACITY.get(transport)
        fleet_cap = (veh * cap) if (cap and veh) else None
        # 站点几何：首尾点距离≈0 说明是环线/闭合几何
        pts = [p for part in (f.parts if f.parts and isinstance(f.parts[0], list) else [f.parts]) for p in part]
        closed = False
        geom_km = 0.0
        if len(pts) >= 2:
            geom_km = sum(math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
                          for i in range(1, len(pts))) / 1000.0
        if len(pts) >= 3:
            closed = math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 50
        # 站距：线路总长含往返时用单程；闭合环线本身就是一圈，直接用总长
        spacing_basis_km = total_len_km if closed else one_way_km
        usable_spacing = bool(stops and stops > 2)
        routes.append({
            "name": f.get("Name"),
            "transport": transport,
            "transport_cn": TRANSPORT_CN.get(transport, transport),
            "length_km": total_len_km,
            "one_way_km": one_way_km,
            "stops": stops,
            "vehicles": veh,
            "passengers": pax,
            "usage": usage,
            "usage_per_vehicle": (usage / veh) if (usage and veh) else None,
            "pax_per_vehicle": (pax / veh) if veh else None,
            # ⭐ 单车容量 / 车队总容量 / 归一化载客效率（跨方式唯一可比的效率口径）
            "capacity": cap,
            "fleet_capacity": fleet_cap,
            "load_efficiency": (pax / fleet_cap) if fleet_cap else None,
            "pax_per_km": (pax / total_len_km) if total_len_km else None,
            # ⭐ 配车 = 0 → **停用线路**：不做任何客流分析，只做线位分析
            "suspended": (veh == 0),
            # 站距：站数 >2 才有意义；闭合环线用一圈长度，普通线用单程长度
            "avg_stop_spacing_m": (spacing_basis_km * 1000.0 / (stops - 1)) if usable_spacing else None,
            "spacing_basis": ("环线一圈" if closed else "单程") if usable_spacing else "不可算",
            "is_loop": closed,
            "spacing_note": ("站数 ≤2，站距不可算" if (stops and not usable_spacing) else None),
            # 车队与间隔的关系：间隔(min) ≈ 往返时间 × 60 / 车辆数
            "approx_headway_min_at_20kmh": (2 * (one_way_km / speed_kmh) * 60.0 / veh) if veh else None,
            "centroid": f.compute_centroid(),
            "object": f.get("Object") or PASSENGER_ROUTE_OBJECT,
        })
    # 城市级汇总（**只含客运**；货运线路另算，不进本表的任何合计）
    # ⚠️ 停用线路（配车 = 0）**不进客流合计与效率排序**，只单独成表做线位分析。
    active = [r for r in routes if not r["suspended"]]
    suspended = [r for r in routes if r["suspended"]]
    by_t = defaultdict(lambda: {"routes": 0, "veh": 0, "pax": 0, "km": 0.0,
                                "active": 0, "suspended": 0})
    for r in routes:
        t = r["transport"] or "?"
        by_t[t]["routes"] += 1
        by_t[t]["veh"] += r["vehicles"]
        by_t[t]["pax"] += r["passengers"]
        by_t[t]["km"] += r["length_km"]
        by_t[t]["active" if not r["suspended"] else "suspended"] += 1
    cargo = [{"name": f.get("Name"), "transport": f.get("Transport"),
              "transport_cn": TRANSPORT_CN.get(f.get("Transport"), f.get("Transport")),
              "vehicles": f.get("Vehicle") or 0, "stops": f.get("Stop") or 0,
              "length_km": route_length_km(f)}
             for f in cargo_routes(carto)]
    return {"routes": routes, "by_transport": dict(by_t), "warnings": warnings,
            "active_routes": active, "suspended_routes": suspended,
            "total_passengers": sum(r["passengers"] for r in active),
            "total_vehicles": sum(r["vehicles"] for r in active),
            # ⭐ 线路总里程 = **逐线路长度相加**（唯一口径；停用线路的线位仍占里程，所以含它们）
            "total_length_km": sum(r["length_km"] for r in routes),
            "active_length_km": sum(r["length_km"] for r in active),
            # ⚠️ 货运线路**只在这里列出**，供工业部分做辅助分析；不进上面的任何合计。
            "cargo_routes": cargo,
            "scope_note": "本表只含 `RoutePassenger`（客运）线路；"
                          "`RouteCargo`（货运铁路/货运航线）已剔除，归工业部分辅助分析。"
                          "配车 = 0 的线路按**停用线路**处理：不做客流分析，只做线位分析。"}


# ------------------------------------------------------------------ 5. 走廊重叠
def analyze_overlap(routes, sample_m=100.0):
    """两两比较**客运**轨道/主干线路的空间重叠度：把每条线的顶点串重采样后算最近距离。

    ⚠️ **口径限制**：只比较 `RoutePassenger` 的轨道线路 —— 货运铁路 / 货运航线
    不参与"是否同一走廊、要不要合并"的判定（那要与工业布点一起看）。
    """
    def resample(route_feat, step):
        pts = [p for part in (route_feat.parts if isinstance(route_feat.parts[0], list) else [route_feat.parts])
               for p in part]
        if len(pts) < 2:
            return []
        out = [pts[0]]
        acc = 0.0
        for i in range(1, len(pts)):
            x0, y0 = pts[i - 1]
            x1, y1 = pts[i]
            seg = math.hypot(x1 - x0, y1 - y0)
            if seg <= 0:
                continue
            t = 0.0
            while acc + (seg - t) >= step:
                need = step - acc
                t += need
                r = t / seg
                out.append((x0 + (x1 - x0) * r, y0 + (y1 - y0) * r))
                acc = 0.0
            acc += seg - t
        return out

    # ⚠️ 只取**客运**轨道线（`RouteCargo` 的货运铁路/航线不进走廊重叠判定）
    rails = [f for f in routes if is_passenger_route(f)
             and f.get("Transport") in ("Subway", "Train", "Tram", "Monorail")]
    tracks = []
    for f in rails:
        pts = [p for part in (f.parts if f.parts and isinstance(f.parts[0], list) else [f.parts]) for p in part]
        tracks.append({"name": f.get("Name"), "transport": f.get("Transport"),
                       "pts": resample(f, sample_m)})
    pairs = []
    for i in range(len(tracks)):
        for j in range(i + 1, len(tracks)):
            a, b = tracks[i], tracks[j]
            if len(a["pts"]) < 2 or len(b["pts"]) < 2:
                continue
            idx = GridIndex([(p[0], p[1], k) for k, p in enumerate(b["pts"])], cell=200.0)
            dists = []
            for p in a["pts"]:
                hits = idx.within(p[0], p[1], 1200.0)
                dists.append(hits[0][0] if hits else float("inf"))
            finite = [d for d in dists if d != float("inf")]
            if not finite:
                continue
            pairs.append({
                "a": a["name"], "b": b["name"],
                "median_m": sorted(finite)[len(finite) // 2],
                "share_within_200m": sum(1 for d in finite if d <= 200) / len(dists),
                "share_within_400m": sum(1 for d in finite if d <= 400) / len(dists),
            })
    return pairs


# ------------------------------------------------------------------ 6/7. 腹地与就业中心
def _station_span(points):
    """返回 (cum, span, closed)：cum 为累计距离，span 为"应该铺开站点的长度"。

    线路几何既可能包含往返（去+回），也可能是闭合环线。判断依据：
    首尾点几乎重合 → 环线，全程即一圈；否则按往返处理，只铺前半段。
    """
    if len(points) < 2:
        return None, 0.0, False
    cum = [0.0]
    for i in range(1, len(points)):
        cum.append(cum[-1] + math.hypot(points[i][0] - points[i - 1][0],
                                        points[i][1] - points[i - 1][1]))
    total = cum[-1]
    if total <= 0:
        return None, 0.0, False
    closed = math.hypot(points[0][0] - points[-1][0], points[0][1] - points[-1][1]) < 50
    span = total if closed else total / 2.0
    return cum, span, closed


def analyze_catchment(carto, radius_list=(400, 600, 800), merge_m=150.0):
    """车站腹地：沿线路等分取站，统计站点周边人口/岗位，并**跨线路去重**（同一位置的站只算一次）。

    ⚠️ **两条口径限制**：
    ① **只取客运线路**（`RoutePassenger`）—— 货运铁路 / 货运航线没有客运腹地，
       混进来会产生"0 人腹地"的假空站；
    ② 本函数算的是**客运车站**腹地 —— **地铁总站（`DepotSubway`）等 depot 不是车站**，
       它只负责给线路提供车辆，不产生上下客，因此不进入任何站点/腹地口径。
    """
    bidx = build_building_index(carto)
    stations = []          # 全部站点坐标
    per_route = []
    for f in carto.layer("routes"):
        if not is_passenger_route(f):
            continue
        pts = [p for part in (f.parts if f.parts and isinstance(f.parts[0], list) else [f.parts]) for p in part]
        cum, span, closed = _station_span(pts)
        if not cum:
            continue
        n = max(2, int(f.get("Stop") or 2))
        st = []
        for k in range(n):
            target = span * k / (n - 1)
            for i in range(1, len(cum)):
                if cum[i] >= target:
                    seg = cum[i] - cum[i - 1]
                    r = (target - cum[i - 1]) / seg if seg else 0.0
                    st.append((pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * r,
                               pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * r))
                    break
        if st:
            per_route.append({"route": f.get("Name"), "transport": f.get("Transport"),
                              "is_loop": closed, "stations": st})
            stations.extend(st)
    # 去重：距离 < merge_m 的站点视为同一个换乘点
    unique = []
    for (x, y) in stations:
        for (ux, uy, _cnt) in unique:
            if math.hypot(x - ux, y - uy) < merge_m:
                break
        else:
            unique.append((x, y, 1))
    out = []
    for (x, y, _c) in unique:
        rec = {"x": x, "y": y}
        for R in radius_list:
            hits = bidx.within(x, y, R)
            rec["pop_%d" % R] = sum((b.get("Resident") or 0) for _, b in hits)
            rec["jobs_%d" % R] = sum((b.get("Employee") or 0) for _, b in hits)
        out.append(rec)
    return {"stations": out, "per_route": per_route,
            "raw_station_count": len(stations), "unique_station_count": len(unique)}


def identify_job_centers(carto, cell=400.0, top=12):
    """按 400 m 网格聚合岗位，找出就业中心。"""
    grid_jobs = defaultdict(int)
    grid_pop = defaultdict(int)
    for b in carto.layer("buildings"):
        cx, cy = b.compute_centroid()
        k = (int(cx // cell) * cell, int(cy // cell) * cell)
        grid_jobs[k] += b.get("Employee") or 0
        grid_pop[k] += b.get("Resident") or 0
    cells = []
    for k, v in grid_jobs.items():
        if v <= 0:
            continue
        cells.append({"x": k[0] + cell / 2, "y": k[1] + cell / 2, "jobs": v, "pop": grid_pop.get(k, 0)})
    cells.sort(key=lambda c: -c["jobs"])
    return cells[:top]


# ------------------------------------------------------------------ 8. 地形与可建造性
#: 方位词：CSL2 地图北为 +y（UTM 正向），故 x 增为东、y 增为北
_DIR8 = ("东", "东北", "北", "西北", "西", "西南", "南", "东南")


def bearing_cn(dx, dy):
    """把位移向量化为中文方位词（东/东北/北/…），用于**弱化绝对坐标**的表述。"""
    if dx == 0 and dy == 0:
        return "原地"
    ang = math.degrees(math.atan2(dy, dx)) % 360.0
    return _DIR8[int((ang + 22.5) % 360 // 45)]


class Locator(object):
    """把绝对坐标翻译成**相对城市的方位**（最高优先级要求：弱化绝对数字坐标）。

    以人口重心为原点，同时给出：
      * `dir_of(x, y)`  —— 方位词（东侧 / 西北侧 …）
      * `dist_of(x, y)` —— 距人口重心多少米
      * `near(x, y)`    —— 方位 + 距离，可直接写进建议
    绝对坐标只在**佐证**时附在括号里（用 `raw=True`）。
    """

    def __init__(self, cx, cy):
        self.cx, self.cy = float(cx), float(cy)

    def dir_of(self, x, y):
        return bearing_cn(x - self.cx, y - self.cy)

    def dist_of(self, x, y):
        return math.hypot(x - self.cx, y - self.cy)

    def near(self, x, y, raw=False):
        s = "%s侧 %.0f m" % (self.dir_of(x, y), self.dist_of(x, y))
        if raw:
            s += "（绝对坐标 %d, %d）" % (x, y)
        return s


def analyze_terrain(carto, build=None):
    """地形 + **可建造性**（水体 / 陡坡 / 适宜建设区）。

    ⚠️ 关键修正：Carto 的 GeoTIFF 是 EPSG:32631 绝对坐标，而新版 GeoJSON 是归一化坐标，
    **两者必须先标定**。旧实现直接拿 GeoJSON 坐标去比栅格 bbox，必然得出
    "栅格不覆盖城市"的错误结论。现在用 `core.terrain.solve_utm_offset()` 解出平移量
    （判据：建筑自带 Elevation 与栅格高程的中位误差最小，实测 0.05 m）。
    """
    import numpy as np
    from core import terrain as _T

    el = carto.elevation
    if el is None or el.array is None:
        return None
    a = np.asarray(el.array, dtype="float32")
    h, w = a.shape[:2]
    valid = a[np.isfinite(a)]
    if valid.size == 0:
        return None

    out = {
        "raster": el.size,
        "pixel_m": el.dx,
        "raster_bounds": el.bounds(),
        "min": float(valid.min()), "max": float(valid.max()),
        "mean": float(valid.mean()),
        "p2": float(np.percentile(valid, 2)), "p98": float(np.percentile(valid, 98)),
    }

    # 标定 GeoJSON → UTM，然后按**城市真实位置**取地形
    ox, oy, q = _T.solve_utm_offset(carto)
    out["utm_offset"] = (ox, oy)
    out["utm_calibration"] = q
    if ox is None:
        out["note"] = "无法标定 GeoJSON→UTM（栅格缺失或建筑 Elevation 不足），地形结论不可用"
        return out

    b = carto.city_bounds()
    if b:
        x0, y0, x1, y1 = b[0] + ox, b[1] + oy, b[2] + ox, b[3] + oy
        rb = el.bounds()
        # ⚠️ 只比较 bbox 会误报：城市 bbox 的**角点**可能恰好压到栅格边缘（甚至越界一点点），
        # 而实际建筑全都落在栅格内。所以主判据改成"**有多少建筑能取到高程值**"。
        blds = carto.layer("buildings")
        n_ok = n_tot = 0
        for f in blds:
            cx, cy = f.compute_centroid()
            n_tot += 1
            if el.value_at(cx + ox, cy + oy) is not None:
                n_ok += 1
        out["elev_coverage_ratio"] = (n_ok / n_tot) if n_tot else None
        out["elev_covered_buildings"] = (n_ok, n_tot)
        bbox_ok = not (x0 < rb[0] or x1 > rb[2] or y0 < rb[1] or y1 > rb[3])
        # 建筑覆盖率 ≥95% 即认为"覆盖城市"；bbox 越界只作附注
        out["raster_covers_city"] = bool(n_tot and n_ok / n_tot >= 0.95)
        out["bbox_within_raster"] = bbox_ok
        c0, r0 = el.xy_to_pixel(x0, y1)
        c1, r1 = el.xy_to_pixel(x1, y0)
        c0, c1 = sorted((min(max(0, c0), w - 1), min(max(0, c1), w - 1)))
        r0, r1 = sorted((min(max(0, r0), h - 1), min(max(0, r1), h - 1)))
        sub = a[r0:r1 + 1, c0:c1 + 1]
        sub = sub[np.isfinite(sub)]
        if sub.size:
            out["city_area_min"] = float(sub.min())
            out["city_area_max"] = float(sub.max())
            out["city_area_relief"] = float(sub.max() - sub.min())

    # 可建造性分级
    if build is None:
        build = _T.buildability(carto, (ox, oy))
    if build:
        out["buildability"] = build["stats"]
        out["buildability_grid"] = build
        # 建筑落点自检：城市建筑应几乎全在"适宜"
        blds = carto.layer("buildings")
        cnt = {}
        for f in blds:
            bx, by = f.compute_centroid()
            k = _T.classify_point(build, bx + ox, by + oy)
            cnt[k] = cnt.get(k, 0) + 1
        out["buildings_by_class"] = cnt
    return out


# ------------------------------------------------------------------ 8.5 用地效率（本轮核心）
TILE_M = 8.0            # CSL2 一格 = 8 m（官方吸附说明）；Carto 分区图斑亦为 8 m 网格单元
TILE_M2 = TILE_M * TILE_M


def analyze_land_efficiency(carto, zoning=None):
    """把"每单位土地能装下多少岗位/居民"算出来 —— 这是"效率用地 → 税收"的核心中间指标。

    重要口径说明（务必连同结论一起引用）：
    * Carto 的分区图斑是 **8 m × 8 m 的固定栅格单元**，所以「已建成图斑数 × 64 m²」
      是**建筑占地栅格量**，不是用地面积；它是唯一可比的"土地消耗"代理量。
    * 因此本节的"每公顷产出"= `该分区的岗位(或居民) ÷ (图斑数 × 64 m² / 10000)`，
      单位是 **岗位/公顷（按建成栅格计）**。**这是相对指标，用于分区之间横向比较**，
      不要当成现实意义的"就业密度"。
    * 游戏内**没有**"税收"字段，Carto 也不含税率/税基。所以本节只给"税基代理量"
      （岗位、居民、建筑等级），真实税收必须由玩家在游戏内读数。
    """
    if zoning is None:
        zoning = analyze_zoning(carto)
    zone_stats = {z["zoning"]: z for z in zoning["zones"]}
    b_emp = zoning["building_employees"]
    b_res = zoning["building_residents"]
    b_cnt = zoning["building_zones"]

    rows = []
    for z, st in zone_stats.items():
        tiles = st["count"]
        built_ha = tiles * TILE_M2 / 10000.0
        emp = b_emp.get(z, 0)
        res = b_res.get(z, 0)
        rows.append({
            "zoning": z,
            "zoning_cn": ZONE_CN.get(z, z),
            "tiles": tiles,
            "built_ha": built_ha,
            "jobs": emp,
            "residents": res,
            "buildings": b_cnt.get(z, 0),
            "jobs_per_ha": (emp / built_ha) if built_ha else None,
            "residents_per_ha": (res / built_ha) if built_ha else None,
            "jobs_per_building": (emp / b_cnt[z]) if b_cnt.get(z) else None,
        })
    rows.sort(key=lambda r: -(r["jobs_per_ha"] or 0))

    # 「每岗位占地」比较：越小越省地 —— 直接对应"用最少的地装最多的税基"
    land_per_job = []
    for r in rows:
        if r["jobs"] > 0:
            land_per_job.append({
                "zoning_cn": r["zoning_cn"],
                "m2_per_job": (r["built_ha"] * 10000.0 / r["jobs"]),
                "jobs": r["jobs"],
                "built_ha": r["built_ha"],
            })
    land_per_job.sort(key=lambda x: x["m2_per_job"])

    # 就业密度网格（400 m）——找出"最赚钱的地块"与"最浪费的地块"
    grid = defaultdict(lambda: {"jobs": 0, "res": 0, "tiles": 0})
    for b in carto.layer("buildings"):
        cx, cy = b.compute_centroid()
        k = (int(cx // 400.0) * 400, int(cy // 400.0) * 400)
        grid[k]["jobs"] += b.get("Employee") or 0
        grid[k]["res"] += b.get("Resident") or 0
    for f in carto.layer("zoning"):
        cx, cy = f.compute_centroid()
        k = (int(cx // 400.0) * 400, int(cy // 400.0) * 400)
        grid[k]["tiles"] += 1
    cells = []
    for (gx, gy), v in grid.items():
        ha = v["tiles"] * TILE_M2 / 10000.0
        if ha <= 0:
            continue
        cells.append({"x": gx + 200, "y": gy + 200, "jobs": v["jobs"], "res": v["res"],
                      "built_ha": ha,
                      "jobs_per_ha": v["jobs"] / ha,
                      "total_per_ha": (v["jobs"] + v["res"]) / ha})
    top_jobs = sorted(cells, key=lambda c: -c["jobs_per_ha"])[:10]
    low_jobs = sorted([c for c in cells if c["jobs"] > 0], key=lambda c: c["jobs_per_ha"])[:10]

    return {"zones": rows, "land_per_job": land_per_job,
            "top_job_density_cells": top_jobs, "low_job_density_cells": low_jobs,
            "tile_m": TILE_M, "note": "按建成栅格计（1 图斑 = 8 m × 8 m = 64 m²）"}


# ------------------------------------------------------------------ 8.6 幸福度/税收风险代理
def analyze_risk_proxies(carto, catchment=None, roads=None, zoning=None):
    """在**拿不到游戏内幸福度/税收数值**的前提下，用 Carto 可得字段构造风险代理指标。

    只做"能算的"：污染/噪声类字段 Carto 没有，因此这里只用**空间结构**代理：
      ① 职住错配（跨区通勤压力）② 站点腹地与线路效率的错配 ③ 路网层级失衡
      ④ 低密度大占地（税基薄）⑤ 未开发/低效地块
    每一项都要在报告里标明它是"代理指标，不是游戏内数值"。
    """
    out = {}
    # ① 区级职住比离散度：越大说明跨区通勤越严重（通勤长 → 幸福度降 + 道路压力升）
    districts = [d for d in carto.districts()]
    ratios = []
    for d in districts:
        r = d.get("Resident") or 0
        e = d.get("Employee") or 0
        if r > 0:
            ratios.append({"name": d.get("Name"), "ratio": e / r, "residents": r, "jobs": e})
    if ratios:
        vals = [x["ratio"] for x in ratios]
        mean = sum(vals) / len(vals)
        spread = max(vals) - min(vals)
        out["district_job_housing"] = ratios
        out["district_spread"] = spread
        out["district_mean"] = mean

    # ② 线路效率离散度：最低效线路就是最该动刀的地方
    if roads is None:
        roads = analyze_roads(carto)
    cats = roads["by_category"]
    small = sum(v["km"] for k, v in cats.items() if k.startswith("Small"))
    medium = sum(v["km"] for k, v in cats.items() if k.startswith("Medium") or k.startswith("Large"))
    high = sum(v["km"] for k, v in cats.items() if k.startswith("Highway"))
    out["road_mix"] = {"highway_km": high, "arterial_km": medium, "local_km": small}
    out["local_to_arterial"] = (small / medium) if medium else None

    # ③ 低密度占地：低密度建筑图斑占比越高，单位土地税基越薄
    if zoning is None:
        zoning = analyze_zoning(carto)
    dn = zoning.get("density_names") or {}
    total_b = sum(zoning.get("building_zones", {}).values()) or 1
    low = sum(v for k, v in dn.items() if "低密度" in k)
    out["low_density_share"] = low / total_b
    out["density_names"] = dn

    # ④ 线路效率
    if catchment is None:
        catchment = analyze_catchment(carto)
    st = catchment.get("stations", [])
    if st:
        weak = [s for s in st if (s["pop_400"] + s["jobs_400"]) < 200]
        out["weak_stations"] = len(weak)
        out["station_count"] = len(st)
        out["weak_station_share"] = len(weak) / len(st)
    return out



# ------------------------------------------------------------------ 8.7 真实站点覆盖（T18）
#: 官方 Service range（米），取自官方 Wiki `Service_buildings` 自动生成表（SVersion 1.6）。
#: 注意（C23）：这是**需求未饱和时的最大半径**，区内密度上升会被压缩 → 只作上界用。
OFFICIAL_SERVICE_RANGE = {
    "Small Post Office": 1000, "Post Office": 2000,
    "Small Elementary School": 1500, "Small Medical Clinic": 2500,
    "Medical Clinic": 5000, "Hospital": 7500, "Police Headquarters": 10000,
}
#: POI 的 Category → 现实标准半径（用于覆盖体检；取自 references/51、58、61）
COVERAGE_STANDARDS = {
    "StopBus": (300, 500),              # 公交站服务半径 300–500 m（51 p383），Ceder 站距 120–400 m
    "StopSubway": (600, 800),           # 轨道站 600–800 m（现实标准，非官方数值）
    "StopPassengerTrain": (800, 1200),
    "EducationElementary": (500, 500),  # 小学 500 m（51 p522）
    "EducationHigh": (1000, 1000),      # 中学 1000 m
    "EducationCollege": (1500, 2000),
    "Health": (1000, 2500),
    "Park": (500, 1000),                # 居住区公园 0.5–1.0 km（50 表 9-1）
    "Police": (1000, 1500), "Fire": (1000, 1500),
    "Post": (1000, 1000), "Waste": (1000, 1500), "MortuaryCrematorium": (1000, 1500),
}


def analyze_stop_coverage(carto, radii=(300, 400, 500, 800)):
    """T18：用 **POI 里的真实站点坐标** + 现实标准半径，算人口/岗位覆盖率与未覆盖点。

    为什么重要：此前 `city_report.py` 第 6 节 只能**沿线路几何等分猜站**（Carto 不导出站点几何），
    实测发现 `POI_Location` 里其实有**真实站点**（`StopBus`/`StopSubway`/`StopPassengerTrain`），
    本函数改用真实坐标 —— 这直接修正了 第 6 节 的系统性偏差。

    判读：覆盖率低 → 缺站；**覆盖率高但客流仍差 → 问题在服务质量（间隔/规律性），不在覆盖**
    （此时应看 第 4 节 人·车 与 第 15 节 归因，而不是继续加站）。

    ⚠️ **口径限制（两条，都是显式白名单，不靠前缀猜）**：
    ① **只数客运站点**：`PASSENGER_STOP_CATS = StopBus / StopSubway / StopPassengerTrain`。
       **地铁总站（`DepotSubway`）/ 公交总站（`DepotBus`）/ 火车总站（`DepotTrain`）
       是 depot（车辆段），只负责提供车辆，不是站点** → 不计入站点数与覆盖率
       （它们本来就不带 `Stop` 前缀，这里用白名单是为了把"排除"写成显式口径）；
    ② **货运站点不计入客运覆盖**：`StopCargoTrain` / `StopCargoShip`（货运铁路 / 货运码头 / 货运航线）
       属**工业部分的辅助分析**。此前用 `startswith("Stop")` 会把货运码头当成客运站算进覆盖率。
    """
    # 站点只取一次坐标（原写法对每个 POI 调了两次 compute_centroid）
    stop_pts = []
    for p in carto.layer("pois"):
        # ⭐ 白名单：只收客运站点（depot 与货运站点都不在名单内）
        if (p.get("Category") or "") in PASSENGER_STOP_CATS:
            x, y = p.compute_centroid()
            stop_pts.append((x, y, p))
    if not stop_pts:
        return None
    idx = GridIndex(stop_pts, cell=200.0)

    # 人口与岗位一次算好（原先在 4 个半径里各重扫一遍全表）
    cells = []
    for b in carto.layer("buildings"):
        pop = b.get("Resident") or 0
        jobs = b.get("Employee") or 0
        if pop or jobs:
            x, y = b.compute_centroid()
            cells.append((x, y, pop, jobs, b.get("Name")))
    total_pop = sum(c[2] for c in cells) or 1
    total_jobs = sum(c[3] for c in cells) or 1

    out = {"radii": {}, "stop_count": len(stop_pts),
           "by_kind": {}, "uncovered": [], "note":
           "站点坐标取自 POI_Location 的**客运站点白名单**（StopBus / StopSubway / StopPassengerTrain）；"
           "**depot（含地铁总站）与货运站点不计入**；半径是**现实标准**（非官方的 Service range）。"}
    for k, v in Counter(p.get("Category") for _x, _y, p in stop_pts).items():
        out["by_kind"][k] = v

    for R in radii:
        pop_cov = jobs_cov = 0
        for x, y, pop, jobs, _name in cells:
            if idx.within(x, y, R):
                pop_cov += pop
                jobs_cov += jobs
        out["radii"][R] = {"pop_covered": pop_cov, "pop_share": pop_cov / total_pop,
                           "jobs_covered": jobs_cov, "jobs_share": jobs_cov / total_jobs}

    # 找出"离最近站点最远"的住宅（未覆盖热点）；复用上面的 cells，避免第三次扫建筑
    worst = []
    for x, y, pop, _jobs, name in cells:
        if pop <= 0:
            continue
        hits = idx.within(x, y, 3000)
        d = hits[0][0] if hits else 9999
        worst.append({"name": name, "residents": pop, "dist": d, "x": x, "y": y})
    worst.sort(key=lambda r: -r["dist"])
    out["uncovered"] = worst[:15]
    out["worst_dist"] = worst[0]["dist"] if worst else None
    return out



#: 密度类型的税基权重（官方 Zoning 页：低密度"每人交更多税"，高密度人多人均少，低租金税收更低）
DENSITY_TAX_WEIGHT = {"低密度": 1.0, "中密度": 0.8, "高密度": 0.55, "低租金": 0.35}
#: 分区类型的岗位税基权重（办公利润 > 商业 > 工业，见 references/45）
ZONE_JOB_WEIGHT = {"Office": 1.6, "Commercial": 1.35, "Industrial": 1.0,
                   "Residential, Commercial": 1.2, "None": 0.8}

#: 官方住宅税起征点（`references/45`）。
#: ⚠️ **仅用于旧版导出**：新版 Carto 的 `Wage` 已改为"劳工平均**应税**收入"（起征点已在字段里扣掉），
#: 此时**不能再减一次**，否则会把起征点扣两遍、系统性低估税基。见 `WAGE_IS_TAXABLE`。
RESIDENTIAL_MIN_EARNINGS = 1400.0

#: 新版 Carto 的 `Wage` 字段语义 = 劳工平均**应税**收入（用户确认，2026-10-13 导出起）。
#: 判定方式：实测新导出 `Wage` 中位 500 / max 7116，旧口径为 1500 / 8157 —— 明显已扣过起征点，
#: 且非零取值集中在 1500 / 1000 / 2000 / 500 / 1250（旧口径则是 2500 / 2000 / 3000）。
#: 因此住宅税基 = `Σ Wage × Labor`，**不再套 max(0, Wage − 1400)**。
WAGE_IS_TAXABLE = True

#: 分区名归一化：新版 GeoJSON 的 `Zone` 会写出「Commercial High / Commercial Low」这类细分名，
#: 若不归一化，同一用途会被拆成多行（实测出现过 Commercial 198 栋 + Commercial High 1 栋）。
_ZONE_ALIAS = {
    "Commercial High": "Commercial", "Commercial Low": "Commercial",
    "Residential High": "Residential", "Residential Low": "Residential",
    "Residential Medium": "Residential", "Industrial High": "Industrial",
    "Industrial Low": "Industrial", "Office High": "Office", "Office Low": "Office",
    "": "未分区", "None": "未分区", "Unzoned": "未分区",
}


def _norm_zone(z):
    z = (z or "").strip()
    return _ZONE_ALIAS.get(z, z if z else "未分区")


#: 只有这三类分区里的建筑才**有公司利润**（商/工/办的税基就是利润）。
#: ⚠️ 住宅与未分区建筑的 `Profit` 恒为 0（它们不是公司）。若把它们算进"利润 ≤ 0 的建筑数"，
#: 会把**每一栋住宅**都当成"毫无余量的公司"（实测同一份导出：只算公司 111 栋 → 误算成 1681 栋）。
COMPANY_ZONE_KEYS = ("Commercial", "Industrial", "Office")


def is_company_zone(zoning):
    """该建筑是不是**公司**（商 / 工 / 办；混合用途如 `Residential, Commercial` 也算）。"""
    z = zoning or ""
    return any(k in z for k in COMPANY_ZONE_KEYS)


def _taxable_from_wage(w):
    """把建筑级 `Wage` 折算成"每个劳工的应税收入"。

    * `WAGE_IS_TAXABLE=True`（新版）：字段本身就是应税收入 → 直接用。
    * 否则（旧版）：字段是平均**总**收入 → 减去起征点 ₡1400，不足则不计税。
    """
    w = w or 0.0
    if WAGE_IS_TAXABLE:
        return max(0.0, w)
    return max(0.0, w - RESIDENTIAL_MIN_EARNINGS)


def analyze_real_tax_base(carto):
    """⭐ 用**新版 GeoJSON 的真字段**算税基 —— 不再依赖密度/分区权重那套代理。

    新版 Carto 的建筑层带有旧版没有的字段（见 `references/70` 第 1.0.2 节）：
      * `Level`  —— 建筑等级 L1–L5
      * `Profit` —— 公司利润（₡），**商/工/办的税基就是这个**
      * `Wage`   —— 工资（₡/月）
      * `Labor`  —— 该建筑提供的岗位数

    于是官方税收机制（`references/45`）可以**直接落地**：
      * 住宅应税额 = `max(0, 月薪 − ₡1400) × 岗位/人数`（起征点 ₡1400）
      * 商/工/办税基 = **公司利润合计**
    这比 第 11 节 的"人数 × 密度权重"代理准确得多 —— **本节可用时以本节为准**。

    返回 `None` 表示该导出没有这些字段（旧 Shapefile 版），调用方应退回 第 11 节 的代理口径。
    """
    blds = carto.layer("buildings")
    if not blds:
        return None
    have = [k for k in ("Level", "Profit", "Wage") if blds[0].get(k) is not None]
    if not have:
        return None

    by_zone = defaultdict(lambda: {"n": 0, "profit": 0.0, "labor": 0.0, "wage_sum": 0.0,
                                   "wage_n": 0, "res": 0.0, "emp": 0.0, "loss": 0,
                                   "loss_staffed": 0, "loss_vacant": 0,
                                   "levels": Counter()})
    tot_profit = tot_loss_bld = 0.0
    tot_loss_staffed = 0
    res_tax_base = 0.0
    #: ⭐ 商业"亏损/毫无余量"的店铺明细（判据：`Profit ≤ 0`；在营 vs 空置分开）
    com_loss = []
    for b in blds:
        z = _norm_zone(b.get("Zoning"))
        d = by_zone[z]
        d["n"] += 1
        lv = b.get("Level")
        d["levels"][int(lv) if lv is not None else -1] += 1
        pr = b.get("Profit") or 0.0
        emp = b.get("Employee") or 0.0
        d["profit"] += pr
        tot_profit += pr
        # ⭐ 判亏口径：`Profit <= 0`（**含等于 0**）。
        # 游戏里 `Profit` 永远不会为负（付不起 upkeep 的公司先降级、再废弃），
        # 所以 `<= 0` 实际就是"刚好付满、毫无余量"的临界档；用 `Profit < 0` 会得到 0 栋。
        # ⭐ 判亏口径：`Profit <= 0`（**含等于 0**），且**只对"公司"建筑**（商/工/办）。
        # 游戏里 `Profit` 永远不会为负（付不起 upkeep 的公司先降级、再废弃），
        # 所以 `<= 0` 实际就是"刚好付满、毫无余量"的临界档；用 `Profit < 0` 会得到 0 栋。
        # ⚠️ 住宅 / 未分区建筑的 `Profit` 恒为 0（它们不是公司）→ **必须排除**，否则整城住宅都会被算成"亏损公司"。
        if is_company_zone(b.get("Zoning")) and pr <= 0:
            d["loss"] += 1
            tot_loss_bld += 1
            if emp > 0:
                d["loss_staffed"] += 1
                tot_loss_staffed += 1
            else:
                d["loss_vacant"] += 1
            if "Commercial" in (b.get("Zoning") or ""):
                com_loss.append({"name": b.get("Name"), "asset": b.get("Asset"),
                                 "brand": b.get("Brand"), "product": b.get("Product"),
                                 "level": int(lv) if lv is not None else None,
                                 "employee": int(emp), "profit": pr,
                                 "district": b.get("Address_District"),
                                 "street": b.get("Address_Street"),
                                 "mixed_use": "Residential" in (b.get("Zoning") or ""),
                                 "staffed": emp > 0})
        lab = b.get("Labor") or 0.0
        d["labor"] += lab
        w = b.get("Wage")
        if w is not None and lab:
            d["wage_sum"] += w
            d["wage_n"] += 1
            # 住宅税基 = Σ (每劳工应税收入 × 该建筑劳工数)。
            # 新版 Wage 已是应税收入（起征点已在字段内），旧版才需要扣 ₡1400 —— 见 _taxable_from_wage。
            res_tax_base += _taxable_from_wage(w) * lab
        d["res"] += b.get("Resident") or 0.0
        d["emp"] += emp

    rows = []
    for z, d in by_zone.items():
        rows.append({
            "zoning": z, "buildings": d["n"], "profit": d["profit"],
            "profit_per_building": d["profit"] / d["n"] if d["n"] else None,
            "labor": d["labor"], "employees": d["emp"],
            "avg_wage": (d["wage_sum"] / d["wage_n"]) if d["wage_n"] else None,
            "loss_buildings": d["loss"],
            "loss_staffed": d["loss_staffed"], "loss_vacant": d["loss_vacant"],
            "levels": dict(d["levels"]),
        })
    rows.sort(key=lambda r: -r["profit"])

    # 全市等级分布
    lv_all = Counter()
    for b in blds:
        lv = b.get("Level")
        if lv is not None:
            lv_all[int(lv)] += 1

    com_loss.sort(key=lambda r: (r["employee"] == 0, -(r["employee"] or 0)))
    return {
        "fields_available": have,
        "total_profit": tot_profit,
        "loss_buildings": int(tot_loss_bld),
        "loss_staffed": int(tot_loss_staffed),
        "loss_vacant": int(tot_loss_bld) - int(tot_loss_staffed),
        # ⭐ 判亏口径随数据走：Carto 建筑层**没有**月收入 / 月成本字段，
        # 所以只能用 `Profit ≤ 0`；将来若导出这两列，再加一条"月收入 ≤ 月成本"。
        "loss_criterion": "`Profit ≤ 0`（含等于 0）；若能读到月收入与月成本，则加判「月收入 ≤ 月成本」",
        "loss_criterion_note": "Carto 建筑层不含月收入/月成本字段（已核实字段表），"
                              "本节只用 `Profit ≤ 0`。**不得**用 `Profit < 0` —— "
                              "游戏里付不起维护费的公司先降级、再废弃，不记负利润，用 `< 0` 会得到 0 栋。"
                              "⚠️ 本口径**只适用于公司建筑**（商业 / 工业 / 办公，含混合用途）："
                              "住宅与未分区建筑的 `Profit` 恒为 0，算进来会把整城住宅误当成「毫无余量的公司」。",
        "company_zones": list(COMPANY_ZONE_KEYS),
        "commercial_loss": com_loss,
        "residential_tax_base": res_tax_base,
        "by_zone": rows,
        "levels_all": dict(sorted(lv_all.items())),
        "wage_is_taxable": WAGE_IS_TAXABLE,
        "note": "税基为**代理量**：住宅部分 = Σ 应税工资 × 劳工数"
                + ("（`Wage` 字段已是应税收入，起征点 ₡1400 已含在字段内）"
                   if WAGE_IS_TAXABLE else "（由平均总收入减起征点 ₡1400 得出）")
                + "；商/工/办 = Σ 公司利润。**这是按官方税收机制算出的相对量，不是城市实际税收金额**"
                  "（实际税收还取决于税率与建筑等级，Carto 不含税率）。",
    }


def _density_class(name):
    n = name or ""
    if "低租金" in n or "廉租" in n:
        return "低租金"
    for k in ("高密度", "中密度", "低密度"):
        if k in n:
            return k
    if "四合院" in n or "排屋" in n or "独立" in n:
        return "低密度"
    return None


def analyze_service_coverage(carto):
    """C23 的**双口径**覆盖体检：官方 `Service range`（上界） vs 自圈现实半径（下界）。

    为什么必须双口径（`references/90` 第 5 节 / C23）：
    * 官方 `Service range` 单位是米（已结案，C20），但它是**需求未饱和时的最大半径**，
      区内人口密度上升会把它压缩 → **只能当上界**；
    * 自圈的现实标准半径（`references/51`/`58`）不受游戏机制影响 → **当下界**。
    两者一起报，玩家才能判断"是设施太少，还是密度把它压扁了"。

    数据来源：`POI_Location` 的**服务设施 POI**（不是建筑图层），配官方 range 表。
    跨城不可比：POI 的 Category 与官方建筑名不是一一对应，映射见下表，**未映射的类别不参与判定**。
    """
    #: POI Category → 官方 Service range（米）。取自官方 Wiki `Service_buildings`（SVersion 1.6，action=raw 已核）
    OFFICIAL = {
        "Post": 1000,                 # Small Post Office；Post Office 为 2000（建筑面板可区分）
        "EducationElementary": 1500,  # Small Elementary School
        "Health": 2500,               # Small Medical Clinic；Medical Clinic 5000 / Hospital 7500
        "Police": 10000,              # Police Headquarters
    }
    #: 自圈现实半径（下界），来自 references/51、58
    SELF = {"Post": 1000, "EducationElementary": 500, "Health": 1000, "Police": 1000}

    # ① POI 只按类别分桶一次（原先每个类别都全表扫一遍，且 compute_centroid 被调了两次）
    by_cat = defaultdict(list)
    for p in carto.layer("pois"):
        cat = p.get("Category")
        if cat in OFFICIAL:
            x, y = p.compute_centroid()
            by_cat[cat].append((x, y, p))

    # ② 人口建筑只取一次，且只对需要的类别做查询
    people = carto.populated_points()
    total = carto.total_population() or 1
    rows = []
    for cat, off_r in OFFICIAL.items():
        pts = by_cat.get(cat)
        if not pts:
            continue
        idx = GridIndex(pts, cell=200.0)
        self_r = SELF.get(cat, off_r)
        #: 本表所有类别的自圈半径都 ≤ 官方半径，故"命中自圈"必然"命中官方"
        assert self_r <= off_r, "自圈半径不应大于官方 range（%s）" % cat
        pop_off = pop_self = 0
        for x, y, pop in people:
            if idx.within(x, y, self_r):
                pop_self += pop
                pop_off += pop
            elif idx.within(x, y, off_r):
                pop_off += pop
        rows.append({
            "category": cat, "facilities": len(pts),
            "official_range_m": off_r, "self_range_m": self_r,
            "pop_covered_official": pop_off, "pop_share_official": pop_off / total,
            "pop_covered_self": pop_self, "pop_share_self": pop_self / total,
            "shrink_ratio": (pop_self / pop_off) if pop_off else None,
        })
    return {"rows": rows, "note":
            "官方 range = 上界（会被密度压缩）；自圈半径 = 下界（现实标准）。"
            "『压缩比』= 自圈覆盖 ÷ 官方覆盖，比值越低说明该服务越依赖它的大半径、"
            "在密集区越容易露洞。POI Category 与官方建筑名非一一对应，未映射类别不参与判定。"}


def analyze_tax_potential(carto, zoning=None):
    """税基潜力指数（T1）与逐栋开发强度（T2）。

    ⚠️ 这是**无量纲的相对指数**，不是 ₡。官方税基 = 住宅工资超 ₡1400 部分 / 公司利润，
    Carto 两者都没有，所以只能用"人数 × 密度权重"与"岗位 × 分区权重"做代理。
    **只用于同城内部排序（哪个地块/哪个区更值钱），不要跨城比较，也不要说成金额。**
    """
    if zoning is None:
        zoning = analyze_zoning(carto)
    rows = []
    cells = defaultdict(lambda: {"tax": 0.0, "res": 0, "jobs": 0, "n": 0})
    unknown_density = 0
    for b in carto.layer("buildings"):
        res = b.get("Resident") or 0
        emp = b.get("Employee") or 0
        z = b.get("Zoning") or "None"
        area = b.polygon_area()
        dc = _density_class(b.get("Name"))
        dw = DENSITY_TAX_WEIGHT.get(dc, 0.8)
        if dc is None and res > 0:
            unknown_density += 1
        job_w = ZONE_JOB_WEIGHT.get(z, 1.0)
        # 税基代理：住宅按 "人数 × 密度权重"；岗位按 "岗位数 × 分区权重"
        tax = res * dw + emp * job_w
        cx, cy = b.compute_centroid()
        k = (int(cx // 400.0) * 400, int(cy // 400.0) * 400)
        cells[k]["tax"] += tax
        cells[k]["res"] += res
        cells[k]["jobs"] += emp
        cells[k]["n"] += 1
        if area > 0:
            rows.append({
                "name": b.get("Name"), "zoning": z, "density": dc,
                "res": res, "emp": emp, "area_m2": area,
                "far_like": (res + emp) / area,     # 单位建筑占地的"人+岗"密度
                "tax_index": tax, "tax_per_m2": tax / area,
                "x": cx, "y": cy,
            })

    by_zone = defaultdict(lambda: {"tax": 0.0, "res": 0, "emp": 0, "area": 0.0, "n": 0})
    by_density = defaultdict(lambda: {"tax": 0.0, "res": 0, "emp": 0, "area": 0.0, "n": 0})
    # 密度 × 分区 交叉表：回答"同样一块地，住宅还是岗位更值钱"
    by_combo = defaultdict(lambda: {"tax": 0.0, "res": 0, "emp": 0, "area": 0.0, "n": 0})
    for r in rows:
        jobs_zone = r["zoning"] in ("Office", "Commercial", "Industrial")
        if jobs_zone:
            combo = "%s · %s" % (ZONE_CN.get(r["zoning"], r["zoning"]), "典型")
        else:
            combo = "住宅 · %s" % (r["density"] or "未标注")
        for bag, key in ((by_zone, ZONE_CN.get(r["zoning"], r["zoning"])),
                         (by_density, r["density"] or "未标注"),
                         (by_combo, combo)):
            bag[key]["tax"] += r["tax_index"]
            bag[key]["res"] += r["res"]
            bag[key]["emp"] += r["emp"]
            bag[key]["area"] += r["area_m2"]
            bag[key]["n"] += 1

    def pack(bag):
        out = []
        for k, v in bag.items():
            out.append({"key": k, "tax_index": v["tax"], "residents": v["res"], "jobs": v["emp"],
                        "built_m2": v["area"], "buildings": v["n"],
                        "tax_per_m2": (v["tax"] / v["area"]) if v["area"] else None,
                        "tax_per_building": (v["tax"] / v["n"]) if v["n"] else None,
                        "tax_per_resident": (v["tax"] / v["res"]) if v["res"] else None,
                        "tax_per_job": (v["tax"] / v["emp"]) if v["emp"] else None})
        out.sort(key=lambda x: -(x["tax_per_m2"] or 0))
        return out

    top_buildings = sorted(rows, key=lambda r: -r["tax_per_m2"])[:15]
    top_cells = sorted(({"x": k[0] + 200, "y": k[1] + 200, **v,
                         "tax_per_ha": v["tax"] / (v["n"] * TILE_M2 / 10000.0) if v["n"] else 0}
                        for k, v in cells.items()),
                       key=lambda c: -c["tax_per_ha"])[:10]

    # 本地劳动力自给率（T3）：本地岗位 vs 本地人口。>1 说明要靠城外通勤者（不纳税）
    pop = carto.total_population()
    jobs = carto.total_jobs()
    self_suff = (pop / jobs) if jobs else None

    return {"by_zone": pack(by_zone), "by_density": pack(by_density), "by_combo": pack(by_combo),
            "top_buildings": top_buildings, "top_cells": top_cells,
            "unknown_density_buildings": unknown_density,
            "labor_self_sufficiency": self_suff, "population": pop, "jobs": jobs,
            "total_tax_index": sum(r["tax_index"] for r in rows)}


def analyze_underdevelopment(carto, cell=400.0):
    """开发强度（T4 改良版）—— 分区图斑 vs 建筑占地，在**分区类型之间**比较。

    ⚠️ 为什么不做"空置图斑清单"（曾经试过，已废弃）：
    Carto 的分区图斑数量远多于建筑数量（本地实测 26,691 图斑 vs 1,754 栋建筑，
    平均每栋 15 个图斑），说明图斑里**混进了大量非建筑细节**（路面、地块、围栏、道具）。
    因此"某个图斑离建筑很远"绝大多数是假阳性，靠它列"闲置地清单"会严重误导。

    正确做法：**只在同一城市内部、按分区类型横向比较** `建筑占地 ÷ 已划区图斑面积`。
    比值明显偏低的那个分区，才是真正"划了区却没盖起来"的用途。
    分子用建筑多边形的 8 m 栅格占地下限（`Feature.developed_area()`），分母用图斑数 × 64 m²。
    """
    by_zone = defaultdict(lambda: {"tiles": 0, "built_m2": 0.0, "buildings": 0,
                                   "res": 0, "emp": 0})
    for f in carto.layer("zoning"):
        z = f.get("Zoning") or "None"
        by_zone[z]["tiles"] += 1
    for b in carto.layer("buildings"):
        z = b.get("Zoning") or "None"
        by_zone[z]["built_m2"] += b.developed_area()
        by_zone[z]["buildings"] += 1
        by_zone[z]["res"] += b.get("Resident") or 0
        by_zone[z]["emp"] += b.get("Employee") or 0
    rows = []
    for z, v in by_zone.items():
        zone_area = v["tiles"] * TILE_M2
        rows.append({
            "zoning": z, "zoning_cn": ZONE_CN.get(z, z),
            "zone_tiles": v["tiles"], "zone_m2": zone_area,
            "built_m2": v["built_m2"], "buildings": v["buildings"],
            "coverage": (v["built_m2"] / zone_area) if zone_area else None,
            "m2_per_building": (zone_area / v["buildings"]) if v["buildings"] else None,
            "residents": v["res"], "jobs": v["emp"],
        })
    rows.sort(key=lambda r: -(r["coverage"] or 0))
    return {"by_zone": rows,
            "total_zone_tiles": sum(v["tiles"] for v in by_zone.values()),
            "total_buildings": sum(v["buildings"] for v in by_zone.values()),
            "note": "分子=建筑多边形 8 m 栅格占地下限；分母=分区图斑数 × 64 m²。"
                    "图斑含非建筑细节，故比值绝对值偏小，**只看分区之间的相对高低**。"}


def analyze_noise_exposure(carto, max_dist=300.0, step=20.0):
    """住宅噪音暴露代理（T5）—— 幸福度因子之一是噪音污染，Carto 没有噪音字段，只能按道路推算。

    评分式（**纯代理，非游戏公式**）：
        score += 等级权重 × 车道数 × 限速 × exp(-距离/60)
    等级权重：高速 2.0 / 主干 1.0 / 支路 0.6；**隧道权重 0**（官方明文：隧道噪音被抑制）。
    输出是按暴露分排序的建筑，用于定位"住在高速边上"的片区。
    """
    import math as _m
    roads = []
    for f in carto.layer("roads"):
        if f.get("Object") not in ("Road", None):
            continue
        cat = f.get("Category") or ""
        if "Highway" in cat:
            w = 2.0
        elif cat.startswith("Medium") or cat.startswith("Large"):
            w = 1.0
        elif cat.startswith("Small"):
            w = 0.6
        else:
            continue
        if (f.get("Form") or "") == "Tunnel":
            w = 0.0
        lanes = f.get("Lane") or 2
        limit = f.get("Limit") or 40
        pts = [p for part in (f.parts if f.parts and isinstance(f.parts[0], list) else [f.parts]) for p in part]
        if pts and w > 0:
            roads.append((pts, w * lanes * limit))
    if not roads:
        return None
    idx = GridIndex([(p[0], p[1], (pts, strength)) for pts, strength in roads for p in pts[::2]],
                    cell=max(60.0, step * 3))
    out = []
    for b in carto.layer("buildings"):
        res = b.get("Resident") or 0
        if res <= 0:
            continue
        cx, cy = b.compute_centroid()
        score = 0.0
        for dist, (pts, strength) in idx.within(cx, cy, max_dist):
            score += strength * _m.exp(-dist / 60.0)
        if score > 0:
            out.append({"name": b.get("Name"), "residents": res, "score": score, "x": cx, "y": cy})
    out.sort(key=lambda r: -r["score"])
    return {"top": out[:15], "all": out, "count": len(out),
            "note": "代理评分 = Σ 等级权重 × 车道 × 限速 × exp(-距离/60)；隧道权重 0。非游戏公式。"}


def analyze_commute_access(carto, net=None, top_jobs=12, cell=400.0):
    """T5c：**路网**通勤可达性（不是欧氏距离）。

    依据 `references/46` T5c（★★★）：1.6.0f1 起寻路距离上限按出行目的分设，**找不到路线就辞职/搬离**，
    所以"要绕多远"比"直线多近"更关键。欧氏距离会低估绕行，必须走真实路网。

    ⚠️ **本函数必须与"岗位缺口"一起读**（这也是最容易误读的地方）：
    它算的是"住宅到**最近就业中心**"的路网距离。如果这个距离很短、而城市仍然缺岗位，
    那问题**不是城市形态（住得离岗位远），而是岗位总量不够** → 居民只能出城上班，
    而出城通勤者**不缴税**。两者是**不同**的病，处方也完全不同：
      * 形态病（距离远）→ 修路/迁移就业中心/加密站点；
      * 总量病（岗位少）→ **增加岗位用地（尤其办公）**。
    """
    if net is None:
        try:
            from core.network_graph import RoadNetwork, build_commute_inputs
        except Exception:
            return None
        net = RoadNetwork(carto)
        build_inputs = build_commute_inputs
    else:
        from core.network_graph import build_commute_inputs as build_inputs
    try:
        origins, dests = build_inputs(carto, cell=cell, top_jobs=top_jobs)
    except Exception:
        return None
    if not origins or not dests:
        return None
    prof = net.commute_profile(origins, dests)
    if not prof:
        return None
    # 岗位缺口（与形态无关的"总量病"判据）
    pop = carto.total_population()
    jobs = carto.total_jobs()
    prof["network"] = {"nodes": len(net.nodes), "edges": net.n_edges}
    prof["population"] = pop
    prof["jobs"] = jobs
    prof["jobs_per_capita"] = (jobs / pop) if pop else None
    return prof


def analyze_freight_access(carto, radius=1000.0, merge_m=200.0):
    """T14：货运终端（货运港口 / 货运铁路终端 / 机场货运）的**集疏运**检查。

    ⚠️ **范围**：本函数只服务**工业部分的辅助分析** —— 货运港口 / 货运铁路 / 货运航线的数据
    **不与客运数据一并分析**（`SKILL.md` 第 2 节「货运与产业链」；报告放在工业小节里）。

    依据 `references/46` T14 + 官方 `Transportation` 页：货运终端**必然产生大量卡车流**
    （"Due to large amounts of resources being transported to and from the terminal,
    it can generate a lot of truck traffic. Therefore it is crucial to prioritize the
    road connections to the terminal to avoid traffic jams."）。
    官方明确要求「优先保证终端与道路的连接」 → 本函数检查每个货运终端 `radius` 内有没有**高等级道路**。

    判据：终端 1 km 内若无 `Highway` / `Medium` / `Large` 级道路 → **大概率堵**（官方说"必须优先"）。

    ⚠️ **同一座设施在 POI 里会出现多条记录**（实测一个「货运港口」同时带
    `StopCargoShip` + `StopCargoTrain` + `BuildingCargoShip`… 数条，几何位置几乎重合）。
    若不按 `merge_m` 归并，会把 1 个终端报成 3–4 个 —— 于是"货运终端数"虚高，
    也会让"有几个终端缺道路接入"的判读失真。
    """
    pois = carto.layer("pois")
    raw = [p for p in pois if (p.get("Category") or "") in CARGO_TERMINAL_CATS]
    if not raw:
        return None
    # 按坐标归并：同一位置（< merge_m）多条记录 = 同一座终端
    terms = []
    for p in raw:
        x, y = p.compute_centroid()
        hit = None
        for t in terms:
            if math.hypot(x - t["x"], y - t["y"]) < merge_m:
                hit = t
                break
        if hit is None:
            terms.append({"name": p.get("Name"), "cats": {p.get("Category")},
                          "x": x, "y": y, "records": 1})
        else:
            hit["cats"].add(p.get("Category"))
            hit["records"] += 1
    # 高等级路段顶点
    major = []
    minor = []
    for f in carto.layer("roads"):
        cat = f.get("Category") or ""
        if "Highway" in cat or cat.startswith("Medium") or cat.startswith("Large"):
            bucket = major
        elif cat.startswith("Small"):
            bucket = minor
        else:
            continue
        for part in (f.parts if f.parts and isinstance(f.parts[0], list) else [f.parts]):
            for p in part:
                bucket.append((p[0], p[1], f.get("Name") or ""))
    major_idx = GridIndex(major, cell=200.0) if major else None
    minor_idx = GridIndex(minor, cell=200.0) if minor else None

    rows = []
    for t in terms:
        x, y = t["x"], t["y"]
        m = major_idx.within(x, y, radius) if major_idx else []
        s = minor_idx.within(x, y, radius) if minor_idx else []
        nearest_major = m[0][0] if m else None
        rows.append({
            "name": t["name"],
            # 归并后的类别串（一座港口可能同时是货船站 + 货运铁路站）
            "category": " + ".join(sorted(t["cats"])),
            "x": x, "y": y,
            "nearest_major_m": nearest_major,
            "major_within": len(m), "minor_within": len(s),
            "verdict": ("良好" if nearest_major is not None and nearest_major <= radius
                        else "**缺高等级道路接入 —— 大概率堵**"),
        })
    return {"rows": rows, "radius": radius,
            "note": "官方明确要求「优先保证货运终端的道路连接」；本检查只判几何邻近，不含容量。"
                    "同一设施的多条 POI 记录已按 %d m 归并。" % int(merge_m)}


def analyze_transit_service_quality(carto, routes=None, snap=40.0):
    """T17：候车时间的**两项分解**代理 —— 判断"客流差"该怪车不够，还是该怪车不规律。

    依据：Ceder《公共交通规划与运营》式 12.1 —— `E(候车) = E(H)/2 × (1 + C²)`，
    其中 `E(H)` 是平均发车间隔（← 加车可改），`C²` 是**发车间隔的变异系数平方**（← 规律性，专用道/调度可改）。
    `C²=0` → 候车 = 间隔的一半；`C²=1` → 候车 = 整个间隔。**只压 C² 就能把候车砍半，且不多花一辆车。**

    **诚实边界**：Carto **没有**逐车次到站时间，`C²` 算不出来。所以这里做两件能做的事：
      ① 沿线路几何采样，判断该线是否走在**带公交专用道的道路**上
         （Carto 的 `Network_Centerline.Category` 会带 `, Bus` 后缀 —— 这是可判的）；
      ② 结合已有的 `人/车` 与估算间隔，给出**可执行的归因**：

    | 有专用道 | 人/车 | 归因 | 动作 |
    |---|---|---|---|
    | 否 | 低 | 车不够 **且** 规律性差 | 先上专用道压 C²，再加车 |
    | 否 | 高 | 车不够为主 | 加车（优先线路车辆数） |
    | 是 | 低 | **C² 已被压过，问题在 E(H)** | 只加车；线位本身可能不对，查腹地 |
    | 是 | 高 | 运力确实不足 | 加车 + 考虑换大运力方式 |
    """
    if routes is None:
        routes = analyze_routes(carto)
    # 1) 建立"带公交道的路段"点集（**客运专用分析，货运线路已在下面被剔除**）
    bus_pts = []
    for f in carto.layer("roads"):
        cat = f.get("Category") or ""
        if "Bus" not in cat:
            continue
        for part in (f.parts if f.parts and isinstance(f.parts[0], list) else [f.parts]):
            for p in part:
                bus_pts.append((p[0], p[1], 1))
    bus_idx = GridIndex(bus_pts, cell=100.0) if bus_pts else None

    # 2) 线路级判定
    out = []
    # ⚠️ 中位数只由**在跑线路**决定：停用线路（配车 = 0）没有 人/车、也没有归一化效率，
    # 把它们算进来会把中位数拉低，进而把正常线路误判成"客流低"。
    pax_per_veh = [r["pax_per_vehicle"] for r in routes["routes"] if r["pax_per_vehicle"]]
    median = sorted(pax_per_veh)[len(pax_per_veh) // 2] if pax_per_veh else None
    load_eff = [r["load_efficiency"] for r in routes["routes"] if r.get("load_efficiency")]
    median_le = sorted(load_eff)[len(load_eff) // 2] if load_eff else None
    for f in carto.layer("routes"):
        # ⚠️ 客运口径：货运线路（`RouteCargo`，含理论上的**货运火车**）不进本归因表
        if not is_passenger_route(f):
            continue
        if f.get("Transport") not in ("Bus", "Tram"):
            continue
        pts = [p for part in (f.parts if f.parts and isinstance(f.parts[0], list) else [f.parts])
               for p in part]
        if len(pts) < 2:
            continue
        # 沿线等距采样，看有多少比例的点落在带公交道的路上
        total = 0.0
        cum = [0.0]
        for i in range(1, len(pts)):
            total += math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
            cum.append(total)
        hits = 0
        n = max(1, int(total / snap)) if total > 0 else 1
        for k in range(n + 1):
            target = total * k / n
            for i in range(1, len(cum)):
                if cum[i] >= target:
                    seg = cum[i] - cum[i - 1] or 1.0
                    r = (target - cum[i - 1]) / seg
                    x = pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * r
                    y = pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * r
                    if bus_idx is not None and bus_idx.within(x, y, 40.0):
                        hits += 1
                    break
        share = hits / (n + 1) if n >= 0 else 0.0
        rec = next((r for r in routes["routes"] if r["name"] == f.get("Name")), {})
        # ⭐ 停用线路（配车 = 0）**不做客流归因** —— 它根本没在跑，"客流低"是定义不是诊断。
        if not rec or rec.get("suspended"):
            continue
        ppv = rec.get("pax_per_vehicle")
        hw = rec.get("approx_headway_min_at_20kmh")
        # 归因
        low_ppv = (median is not None and ppv is not None and ppv < median * 0.7)
        has_lane = share >= 0.3
        if has_lane and low_ppv:
            verdict, action = "专用道已覆盖但客流低", "问题在 E(H) 或线位：先加车；仍不行就查腹地与走向"
        elif has_lane and not low_ppv:
            verdict, action = "专用道覆盖良好", "维护即可；客流到瓶颈再考虑换大运力方式"
        elif (not has_lane) and low_ppv:
            verdict, action = "无专用道 + 客流低", "**先上专用道压 C²（比加车便宜）**，再加车"
        else:
            verdict, action = "无专用道但客流尚可", "客流到瓶颈前补专用道，防间隔劣化"
        out.append({"name": f.get("Name"), "bus_lane_share": share,
                    "pax_per_vehicle": ppv, "headway_min": hw,
                    # ⭐ 归一化载客效率（跨方式可比）：乘客 ÷（车辆 × 单车容量）
                    "load_efficiency": rec.get("load_efficiency"),
                    "capacity": rec.get("capacity"),
                    "verdict": verdict, "action": action})
    return {"routes": out, "median_pax_per_vehicle": median,
            "median_load_efficiency": median_le,
            "note": "C²（间隔变异系数）Carto 无法直接算；这里用「是否走在带公交道的路上」做代理。"
                    "依据 Ceder 式 12.1：E(候车)=E(H)/2×(1+C²)。"
                    "效率比较以**归一化载客效率**为准（乘客 ÷（车辆 × 单车容量），"
                    "单车容量：公交 80 / 地铁 1080 / 客运火车 840 人），"
                    "「人/车」只在同一方式内部比较。"}


def analyze_lane_km(roads):
    """车道公里（T10）—— 比"里程"更接近通行能力口径；能同时修正"双向高速算两遍"的问题。"""
    out = defaultdict(float)
    for k, v in roads["by_category"].items():
        out[k] = v["km"] * (v["avg_lanes"] or 1)
    total = sum(out.values())
    return {"by_category": dict(out), "total_lane_km": total,
            "note": "车道公里 = 长度 × 平均车道数；比纯里程更接近通行能力口径"}


def analyze_elevation_planner(carto, build=None, offset=None, cell=400.0):
    """**高程的规划用途** —— 把高程从「背景数据」变成可执行的规划依据。

    四项输出，均给"对规划意味着什么"：
      1. **台地/坡向**：城市主要落在哪个高程带；高差决定平整土方量。
      2. **低洼点**：局部最低处 → **排水/污水要往哪走**（水往低处流，泵站要设在低处）。
      3. **制高点**：局部最高处 → 地标/公园/观景的选址依据。
      4. **建设平整代价**：按 `references/51` 的「容积率 = 密度 × 层数」同源逻辑，
         高差越大、平整成本越高 → 用**分区内高差**给出相对代价排序。

    只用 `Elevation` 栅格；`offset` 为 GeoJSON→UTM 平移量（见 `core/terrain.solve_utm_offset`）。
    """
    import numpy as np
    from core import terrain as _T

    r = carto.raster("Elevation")
    if r is None or r.array is None:
        return None
    EA = r.array.astype(np.float64)
    nod = EA == -32768
    if offset is None:
        ox, oy, _q = _T.solve_utm_offset(carto)
    else:
        ox, oy = offset
    if ox is None:
        return None

    # 城市范围（GeoJSON 系）
    b = carto.city_bounds()
    out = {"raster": r.size, "pixel_m": r.dx}

    # ① 按 400 m 网格聚合建筑的所在地面高程
    grids = defaultdict(lambda: {"n": 0, "elev": [], "res": 0.0, "jobs": 0.0,
                                 "cells": [], "step": r.dx})
    for f in carto.layer("buildings"):
        x, y = f.compute_centroid()
        e = f.get("Elevation")
        if e is None:
            continue
        k = (int(x // cell) * cell, int(y // cell) * cell)
        d = grids[k]
        d["n"] += 1
        d["elev"].append(float(e))
        d["res"] += f.get("Resident") or 0.0
        d["jobs"] += f.get("Employee") or 0.0
    if not grids:
        return None

    # 为每个网格采样栅格高程，用于算**土方量**（削峰填谷：以格内中位高程为设计标高）
    ny, nx = EA.shape

    def _grid_cells(gx, gy):
        c0 = int(np.floor((gx + ox - r.x0) / r.dx)); c1 = int(np.ceil((gx + cell + ox - r.x0) / r.dx))
        r0 = int(np.floor((r.y0 - (gy + cell + oy)) / r.dy)); r1 = int(np.ceil((r.y0 - (gy + oy)) / r.dy))
        c0, c1 = max(0, c0), min(nx, c1)
        r0, r1 = max(0, r0), min(ny, r1)
        if c1 <= c0 or r1 <= r0:
            return None
        sub = EA[r0:r1, c0:c1]
        sub = sub[sub != -32768]
        return sub if sub.size else None

    for k, d in grids.items():
        sub = _grid_cells(k[0], k[1])
        d["sub"] = sub

    all_e = [e for d in grids.values() for e in d["elev"]]
    out["city_elev_min"] = min(all_e)
    out["city_elev_max"] = max(all_e)
    out["city_relief"] = max(all_e) - min(all_e)
    out["city_elev_median"] = sorted(all_e)[len(all_e) // 2]

    # 台地：按 10 m 带统计，找城市主要落在哪个高程带
    bands = Counter()
    for e in all_e:
        bands[int(e // 10) * 10] += 1
    out["bands"] = dict(sorted(bands.items()))
    out["main_band"] = max(bands.items(), key=lambda kv: kv[1])[0]

    # ②③ 低洼点 / 制高点（在已有建筑的网格之间比较，保证是"城市范围内的地形"）
    cells = []
    for k, d in grids.items():
        sub = d.get("sub")
        relief = float(sub.max() - sub.min()) if sub is not None and sub.size else 0.0
        # 土方量：以格内中位高程为设计标高 → 超出的部分要挖、不足的部分要填，
        # 取两者中较大者作为"平整规模"的量级代理（单位按"m × 格"累积，不是真实 m³，
        # 因为栅格像素面积已知但这里只用相对量排序）。
        cut = fill = 0.0
        if sub is not None and sub.size:
            med = float(np.median(sub))
            cut = float(np.clip(sub - med, 0, None).sum())
            fill = float(np.clip(med - sub, 0, None).sum())
        cells.append({"x": k[0] + cell / 2, "y": k[1] + cell / 2,
                      "elev": sum(d["elev"]) / d["n"], "n": d["n"],
                      "res": d["res"], "jobs": d["jobs"],
                      "relief": relief, "cut": cut, "fill": fill,
                      "earthwork": max(cut, fill)})
    cells.sort(key=lambda c: c["elev"])
    out["n_cells"] = len(cells)
    out["n_buildings"] = len(all_e)
    out["lowest"] = cells[:6]
    out["highest"] = cells[-6:][::-1]
    # ④ 平整代价：网格内高差最大的地方 = 最需要平整/挡土
    out["steepest_cells"] = sorted(cells, key=lambda c: -c["relief"])[:8]
    out["earthwork_cells"] = sorted(cells, key=lambda c: -c["earthwork"])[:8]
    out["cell_m"] = cell
    return out



def analyze_traffic(carto, hot_quantile=0.90):
    """道路**流量与拥堵**诊断（新版 GeoJSON 的 `Network_Centerline.Volume`）。

    口径（重要）
    ------------
    * `Volume` = 该路段的**车流量**（游戏内实测存在，非官方公布的量纲说明）。
    * `Lane`   = 车道数。**实测 330 段 `Lane == 0`**（铁路/地铁/步道/部分水道）→ 一律排除，
      否则会把"没有车道"当成"极拥堵"。
    * **单车流量 `Volume ÷ Lane`** 是唯一可与路段长短无关地横向比较的量，
      也是"这条路吃不吃得消"的代理 —— **CSL2 官方从未公布道路通行能力（pcu/h）**
      （`references/00` C8，已 4 次确认），所以本函数**只用同城同等级路段的相对分位**判拥堵，
      **不给绝对通行能力阈值**。
    * `Volume × Length` = **车公里（veh·km）**，用来找"总负荷最重"的走廊（长路段即使不堵也累积负荷）。

    判读
    ----
    对每个 `Category` 单独取 `Volume/Lane` 的 `hot_quantile` 分位作为"该等级的拥堵线"，
    超过即为**拥堵候选段**。再用 `references/20`/`47` 的处方逻辑给动作：
    高速拥堵 → 别再加车道，改**分流/匝道/车道连接**；支路拥堵 → **瓶颈在路口**，加车道无用。

    非解锁区（**铁律 12**）
    ---------------------
    落在**未解锁地块**上的路段是**地图自带资源**，玩家既没修也不拥有 ——
    `line_length()` 对它们返回 **0**。这类段一律**排除**出本节全部统计
    （拥堵候选、单车道缺陷清单、各等级负荷），否则会把"地图作者修的路"当成玩家的缺陷。
    排除条数记在 `excluded_map_native` 里，报告里如实写出。
    """
    roads = carto.roads_with_flow()
    if not roads:
        return None

    # ⭐ 铁律 12：先剔除**非解锁区**（地图自带）的路段 —— 它们的裁剪后长度为 0
    roads_all = roads
    roads = [t for t in roads_all if t[4] > 0]
    excluded_map_native = len(roads_all) - len(roads)
    if not roads:
        return None

    by_cat = defaultdict(list)
    for f, vol, lane, lim, L in roads:
        by_cat[f.get("Category") or "?"].append(
            {"f": f, "vol": vol, "lane": lane, "limit": lim, "len": L,
             "vpl": vol / lane if lane else 0.0, "vk": vol * L / 1000.0,
             "name": f.get("Name"), "form": f.get("Form"),
             "oneway": (f.get("Direction") or "Both") == "Forward"})

    # 各等级的拥堵线（同城同等级的相对分位）
    thresholds = {}
    for c, segs in by_cat.items():
        v = sorted(s["vpl"] for s in segs)
        if v:
            thresholds[c] = v[min(len(v) - 1, int(len(v) * hot_quantile))]

    hot = []
    for c, segs in by_cat.items():
        th = thresholds.get(c)
        if not th:
            continue
        for s in segs:
            if s["vpl"] >= th and s["vpl"] > 0:
                s["cat"] = c
                s["threshold"] = th
                hot.append(s)
    hot.sort(key=lambda s: -s["vpl"])

    # 车道数缺口：**高速却只有 1 条车道** = 明确的缺陷段（双车道高速在 CSL2 里是常态，不算缺陷）。
    # 判据只锁 `lane <= 1`，避免把全部双车道高速都算进来（那会得出"681/700 段都不足"的废结论）。
    single = [s for c, segs in by_cat.items() for s in segs
              if "Highway" in c and s["lane"] <= 1]
    single.sort(key=lambda s: -s["vpl"])
    two = [s for c, segs in by_cat.items() for s in segs
           if "Highway" in c and s["lane"] == 2]
    lane_deficit = {
        "single_lane_segments": len(single),
        "single_lane_km": sum(s["len"] for s in single) / 1000.0,
        "two_lane_segments": len(two),
        "worst": single[:8],
        "min_lane": min((s["lane"] for s in single), default=None),
    }

    # 各等级的总体负荷
    cat_summary = []
    for c, segs in by_cat.items():
        km = sum(s["len"] for s in segs) / 1000.0
        vk = sum(s["vk"] for s in segs)
        cat_summary.append({
            "category": c, "segments": len(segs), "km": km, "veh_km": vk,
            "vpl_median": sorted(s["vpl"] for s in segs)[len(segs) // 2],
            "vpl_max": max(s["vpl"] for s in segs),
            "lanes_median": sorted(s["lane"] for s in segs)[len(segs) // 2],
            "share_of_veh_km": 0.0,
        })
    tot_vk = sum(x["veh_km"] for x in cat_summary) or 1.0
    for x in cat_summary:
        x["share_of_veh_km"] = x["veh_km"] / tot_vk
    cat_summary.sort(key=lambda x: -x["veh_km"])

    return {"categories": cat_summary, "hot": hot[:25],
            "hot_count": len(hot), "thresholds": thresholds,
            "lane_deficit": lane_deficit,
            "total_veh_km": tot_vk,
            "total_km": sum(x["km"] for x in cat_summary),
            "excluded_zero_lane": sum(1 for f in carto.layer("roads")
                                      if (f.get("Lane") or 0) <= 0),
            "excluded_map_native": excluded_map_native,
            "note": "单车流量 = Volume ÷ Lane；CSL2 **官方未公布道路通行能力**，"
                    "故只用同城同等级路段的相对分位判拥堵，不给绝对阈值。"
                    "**非解锁区（地图自带）路段已整体剔除**（铁律 12）。"}


# ------------------------------------------------------------------ 组团（按密集程度划分）
#: 组团识别用的网格边长（米）。150 m ≈ 一个街区量级：够细能分辨相邻住/职片区，
#: 又不至于把一个片区打碎成几十个小块。
CLUSTER_CELL = 150.0
#: 密度阈值取"有建筑格子"的哪个分位（越高 → 只保留最密的核，组团更少更聚焦）
CLUSTER_DENSITY_Q = 0.60
#: 组团最小规模（人+岗），低于此的碎块并入最近的组团
CLUSTER_MIN_MASS = 1500.0
#: 形态学闭运算半径（格），把相邻密块连成一个组团
CLUSTER_CLOSE_R = 2


def _label_components(mask):
    """8 邻域连通域标记（纯 Python，无 scipy）。返回 `(labels, count)`。"""
    import numpy as np
    h, w = mask.shape
    lab = np.zeros((h, w), dtype=np.int32)
    cur = 0
    for i in range(h):
        for j in range(w):
            if not mask[i, j] or lab[i, j]:
                continue
            cur += 1
            stack = [(i, j)]
            lab[i, j] = cur
            while stack:
                a, b = stack.pop()
                for da in (-1, 0, 1):
                    for db in (-1, 0, 1):
                        na, nb = a + da, b + db
                        if 0 <= na < h and 0 <= nb < w and mask[na, nb] and not lab[na, nb]:
                            lab[na, nb] = cur
                            stack.append((na, nb))
    return lab, cur


def _mass_center(g, cell):
    """组团质心：按格子中心平均（每格权重相同，mass 已在汇总时按格累计）。"""
    if not g["cells"]:
        return (0.0, 0.0)
    xs = [c[0] * cell + cell / 2 for c in g["cells"]]
    ys = [c[1] * cell + cell / 2 for c in g["cells"]]
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def identify_clusters(carto, cell=None, density_q=None, min_mass=None,
                      close_r=None, name_helper=None):
    """**按人口/岗位密集程度划分组团**（不是按行政区划）。

    ⚠️ 行政区划**只用于给组团命名与定位**（`name_helper`），**不参与划分**。

    步骤：
      1. 把建筑的人+岗聚到 `cell` 网格，得到密度面；
      2. 取密度分位 `density_q` 作**密集核**阈值（实测最密 30% 格子承载 75% 的人+岗）；
      3. 对核做**形态学闭运算**（膨胀 `close_r` 格再腐蚀）把相邻密块连成一片；
      4. 8 邻域连通域标记 → 每个连通域是一个组团；
      5. 规模 < `min_mass` 的碎块并入**最近**的组团。

    返回 `list[dict]`：`cells/res/jobs/mass/area_km2/center/dir/dist_km/type/name/cell/threshold`。
    """
    import numpy as np
    cell = float(cell or CLUSTER_CELL)
    q = CLUSTER_DENSITY_Q if density_q is None else float(density_q)
    min_mass = CLUSTER_MIN_MASS if min_mass is None else float(min_mass)
    close_r = CLUSTER_CLOSE_R if close_r is None else int(close_r)

    # ① 密度面
    acc = {}
    for b in carto.layer("buildings"):
        x, y = b.compute_centroid()
        k = (int(x // cell), int(y // cell))
        d = acc.get(k)
        if d is None:
            d = acc[k] = [0.0, 0.0]
        d[0] += b.get("Resident") or 0.0
        d[1] += b.get("Employee") or 0.0
    if not acc:
        return []
    ks = list(acc.keys())
    i0 = min(k[0] for k in ks); i1 = max(k[0] for k in ks)
    j0 = min(k[1] for k in ks); j1 = max(k[1] for k in ks)
    h, w = j1 - j0 + 1, i1 - i0 + 1
    dens = np.zeros((h, w), dtype=np.float32)
    rmap = np.zeros((h, w), dtype=np.float32)
    jmap = np.zeros((h, w), dtype=np.float32)
    for (i, j), (r, e) in acc.items():
        dens[j - j0, i - i0] = r + e
        rmap[j - j0, i - i0] = r
        jmap[j - j0, i - i0] = e

    # ② 密集核阈值（只统计有建筑的格子，否则大片 0 会把分位拉低）
    occ = dens[dens > 0]
    thr = float(np.percentile(occ, q * 100)) if occ.size else 0.0
    core = dens >= max(thr, 1.0)

    def _dilate(m, r):
        out = m.copy()
        for _ in range(r):
            p = np.pad(out, 1)
            out = (p[:-2, :-2] | p[:-2, 1:-1] | p[:-2, 2:] |
                   p[1:-1, :-2] | p[1:-1, 1:-1] | p[1:-1, 2:] |
                   p[2:, :-2] | p[2:, 1:-1] | p[2:, 2:])
        return out

    def _erode(m, r):
        out = m.copy()
        for _ in range(r):
            p = np.pad(out, 1, constant_values=True)
            out = (p[:-2, :-2] & p[:-2, 1:-1] & p[:-2, 2:] &
                   p[1:-1, :-2] & p[1:-1, 1:-1] & p[1:-1, 2:] &
                   p[2:, :-2] & p[2:, 1:-1] & p[2:, 2:])
        return out

    merged = _erode(_dilate(core, close_r), close_r) if close_r else core
    merged = merged & (dens > 0)          # 不许扩到没有建筑的格子

    # ③ 连通域 = 组团
    lab, n = _label_components(merged)
    groups = []
    for c in range(1, n + 1):
        sel = lab == c
        r = float(rmap[sel].sum()); e = float(jmap[sel].sum())
        if r + e <= 0:
            continue
        js, is_ = np.where(sel)
        groups.append({"res": r, "jobs": e, "mass": r + e,
                       "cells": [(int(i0 + i), int(j0 + j)) for i, j in zip(is_, js)]})
    if not groups:
        return []

    # ④ 小碎块并入最近的大组团
    big = [g for g in groups if g["mass"] >= min_mass]
    small = [g for g in groups if g["mass"] < min_mass]
    if not big:
        big, small = groups, []
    for g in small:
        gc = _mass_center(g, cell)
        tgt, bd = None, None
        for b in big:
            bc = _mass_center(b, cell)
            d = math.hypot(gc[0] - bc[0], gc[1] - bc[1])
            if bd is None or d < bd:
                tgt, bd = b, d
        if tgt is not None:
            tgt["res"] += g["res"]; tgt["jobs"] += g["jobs"]
            tgt["mass"] += g["mass"]; tgt["cells"] += g["cells"]

    # ⑤ 命名与属性
    pts = carto.populated_points()
    if pts:
        tw = sum(w for _x, _y, w in pts) or 1
        cx0 = sum(x * w for x, _y, w in pts) / tw
        cy0 = sum(y * w for _x, y, w in pts) / tw
    else:
        bb = carto.city_bounds() or (0, 0, 0, 0)
        cx0, cy0 = (bb[0] + bb[2]) / 2.0, (bb[1] + bb[3]) / 2.0

    out = []
    for g in big:
        cx, cy = _mass_center(g, cell)
        ratio = (g["jobs"] / g["res"]) if g["res"] else None
        if ratio is None or ratio > 1.5:
            gtype = "就业主导"
        elif ratio < 0.5:
            gtype = "居住主导"
        else:
            gtype = "职住混合"
        out.append({
            "name": name_helper(cx, cy) if name_helper else None,
            "res": g["res"], "jobs": g["jobs"], "mass": g["mass"],
            "job_res_ratio": ratio, "type": gtype,
            "area_km2": len(g["cells"]) * (cell * cell) / 1e6,
            "cells": len(g["cells"]),
            "_cells": g["cells"],
            "center": (cx, cy),
            "dir": bearing_cn(cx - cx0, cy - cy0),
            "dist_km": math.hypot(cx - cx0, cy - cy0) / 1000.0,
            "cell": cell, "threshold": thr,
        })
    out.sort(key=lambda g: -g["mass"])
    return out


# ------------------------------------------------------------------ 组团定位（行政区辅助）
class ClusterMap(object):
    """**组团**：按**人口/岗位密集程度**划分，行政 District **只用于命名与定位**。

    为什么这样定：行政边界是人为划的，与"人实际聚在哪"并不一致 ——
    同一个行政区可以既是全城最密的居住区、又只贡献很少岗位。
    规划语言应当基于**密度实际形成的团块**：
      * 点位 → `where(x, y)` 给出「<行政区>·<方位>组团」这类表述；
      * 线状设施 → `between(feature)` 给出「组团A ↔ 组团B」；
      * 每个组团带**职能标签**（就业主导 / 居住主导 / 职住混合）。

    命名规则：`<主导行政区>·<相对城市中心方位>组团` —— 行政区只提供"这是哪一片"的锚点；
    **方位基准是城市人口重心**，所以「中心组团」确实在中心。
    `self.single=True` 表示没识别出组团（数据不足），措辞降级为方位词。
    """

    def __init__(self, carto, **kw):
        self.single = True
        self.groups = []
        self.districts = []
        for a in carto.layer("areas"):
            if a.get("Object") != "District":
                continue
            nm = a.get("Name")
            if not nm:
                continue
            self.districts.append({"name": nm, "feat": a, "center": a.compute_centroid()})
        self._pts = carto.populated_points()
        self._cell = None
        try:
            self.groups = identify_clusters(carto, name_helper=None, **kw)
        except Exception:      # noqa: BLE001  识别失败就退回方位词
            self.groups = []
        if self.groups:
            self.single = False
            self._cell = self.groups[0].get("cell") or CLUSTER_CELL
            self._name_groups()
            self._index = self._build_index()

    # --- 命名：行政区 + 方位 ---
    def _district_of(self, x, y):
        """点落在哪个行政区（不在任何区内 → 最近的区）。行政区**只用于命名**。"""
        try:
            from core.carto_reader import _point_in_feature
        except Exception:
            _point_in_feature = None
        if _point_in_feature is not None:
            for d in self.districts:
                if _point_in_feature(x, y, d["feat"]):
                    return d["name"]
        best = None
        for d in self.districts:
            cx, cy = d["center"]
            dd = math.hypot(x - cx, y - cy)
            if best is None or dd < best[0]:
                best = (dd, d["name"])
        return best[1] if best else None

    def _name_groups(self):
        """给每个组团命名：`<主导行政区>·<相对城市中心的方位>组团`。

        方位**相对城市人口重心**（不是相对行政区中心）——
        这样"中心组团"就真在中心、"东北组团"就真在东北，与读者的空间直觉一致；
        行政区只提供"这是哪一片"的锚点（区分同名组团）。
        """
        # 城市人口重心（方位基准）
        pts = getattr(self, "_pts", None)
        if pts:
            tw = sum(w for _x, _y, w in pts) or 1
            ccx = sum(x * w for x, _y, w in pts) / tw
            ccy = sum(y * w for _x, y, w in pts) / tw
        else:
            ccx = sum(g["center"][0] * g["mass"] for g in self.groups) / (
                sum(g["mass"] for g in self.groups) or 1)
            ccy = sum(g["center"][1] * g["mass"] for g in self.groups) / (
                sum(g["mass"] for g in self.groups) or 1)

        # 主导行政区
        for g in self.groups:
            g["district"] = self._district_of(*g["center"])

        # 方位：离重心很近的直接叫「中心」
        med_r = sorted(math.hypot(g["center"][0] - ccx, g["center"][1] - ccy)
                       for g in self.groups)
        core_r = med_r[len(med_r) // 2] * 0.45 if med_r else 0.0
        used = defaultdict(int)
        for g in self.groups:
            cx, cy = g["center"]
            d = g.get("district") or "城区"
            dd = math.hypot(cx - ccx, cy - ccy)
            pos = "中心" if dd <= core_r else bearing_cn(cx - ccx, cy - ccy)
            base = "%s·%s组团" % (d, pos)
            used[base] += 1
            if used[base] > 1:
                base = "%s·%s组团%d" % (d, pos, used[base])
            g["name"] = base

    # --- 空间索引：格子 → 组团 ---
    def _build_index(self):
        cell = self._cell
        idx = {}
        for i, g in enumerate(self.groups):
            for c in g["_cells"] if "_cells" in g else []:
                idx[c] = i
        if idx:
            return idx
        # identify_clusters 只返回数量，未留存格子列表时按质心+半径归属
        return None

    def locate(self, x, y):
        """返回 `(组团 index 或 None, 是否落在该组团的密核内)`。"""
        if self.single:
            return None, False
        cell = self._cell or CLUSTER_CELL
        k = (int(x // cell), int(y // cell))
        if self._index:
            i = self._index.get(k)
            if i is not None:
                return i, True
        # 不在密核 → 取最近的组团（按质心）
        best = None
        for i, g in enumerate(self.groups):
            cx, cy = g["center"]
            dd = math.hypot(x - cx, y - cy)
            if best is None or dd < best[0]:
                best = (dd, i)
        return (best[1] if best else None), False

    def where(self, x, y, locator=None):
        """点位 → 组团表述。

        * 落在某组团的密核内 → 「**<行政区>·<方位>组团**」
        * 在组团外但离得近 → 「**<行政区>·<方位>组团**外西侧 0.4 km」
        * 识别不出组团 → 退回「相对人口重心 东侧 1.2 km」

        **一律不含绝对数字坐标。**
        """
        i, inside = self.locate(x, y)
        if self.single or i is None:
            return locator.near(x, y) if locator else "—"
        g = self.groups[i]
        name = g.get("name") or "组团%d" % (i + 1)
        if inside:
            return name
        cx, cy = g["center"]
        return "%s外%s侧 %.1f km" % (name, bearing_cn(x - cx, y - cy),
                                    math.hypot(x - cx, y - cy) / 1000.0)

    def group_label(self, i):
        """组团 i 的标签（名字 + 职能）。"""
        if self.single or i is None or i >= len(self.groups):
            return "—"
        g = self.groups[i]
        return "%s（%s）" % (g.get("name") or "组团%d" % (i + 1), g.get("type") or "")

    def between(self, feature, samples=24, snap_km=0.8):
        """线状设施跨越哪些组团 → 「组团A ↔ 组团B」。

        ⚠️ 用 `snap_km` **就近归属**：线路常跑在组团**之间的空隙**里（路网本身不落在
        密核上），若只认"点在密核内"，绝大多数线路会判不出归属（实测 15 对里只认出 1 对）。
        所以：落在密核内直接用；在核外则归给 `snap_km` 内最近的组团；超出就不计。
        """
        if self.single or not feature.parts:
            return None
        parts = feature.parts if isinstance(feature.parts[0], list) else [feature.parts]
        maxd = max(1.0, float(snap_km) * 1000.0)
        seq = []
        for part in parts:
            if len(part) < 2:
                continue
            total = sum(math.hypot(part[i][0] - part[i - 1][0], part[i][1] - part[i - 1][1])
                        for i in range(1, len(part)))
            if total <= 0:
                continue
            for k in range(samples + 1):
                t = total * k / samples
                acc = 0.0
                for i in range(1, len(part)):
                    seg = math.hypot(part[i][0] - part[i - 1][0], part[i][1] - part[i - 1][1])
                    if acc + seg >= t:
                        r = (t - acc) / seg if seg else 0.0
                        px = part[i - 1][0] + (part[i][0] - part[i - 1][0]) * r
                        py = part[i - 1][1] + (part[i][1] - part[i - 1][1]) * r
                        gi, ins = self.locate(px, py)
                        if gi is not None and not ins:
                            # 核外 → 只有够近才算（否则整条线会被远处的组团"认领"）
                            cx, cy = self.groups[gi]["center"]
                            if math.hypot(px - cx, py - cy) > maxd:
                                gi = None
                        if gi is not None:
                            nm = self.groups[gi].get("name")
                            if nm and (not seq or seq[-1] != nm):
                                seq.append(nm)
                        break
                    acc += seg
        if not seq:
            return None
        if len(seq) == 1:
            return "%s内" % seq[0]
        return " ↔ ".join(seq[:4])

    def route_cluster_pairs(self, feature, samples=24, snap_km=0.8):
        """一条线路**实际连通了哪些组团对**（无序去重）。

        ⚠️ 不能直接拿 `between()` 的字符串做字典键：环线/往返线会得到
        「A ↔ B ↔ A」这种序列，与「A ↔ B」不相等，导致**明明连通的组团对被判成无线路**
        （实测就是这个问题：15 对里只认出 1 对）。所以这里解析成**无序对集合**。
        """
        lab = self.between(feature, samples=samples, snap_km=snap_km)
        if not lab:
            return []
        names = [s.strip() for s in lab.split("↔") if s.strip()]
        names = [n[:-1] if n.endswith("内") else n for n in names]
        seen, uniq = set(), []
        for n in names:
            if n not in seen:
                seen.add(n)
                uniq.append(n)
        out = []
        for i, a in enumerate(uniq):
            for b in uniq[i + 1:]:
                out.append((a, b) if a <= b else (b, a))
        return out

    def relations(self, carto):
        """**组团之间的关系表** —— "用组团代替坐标"的核心产物。

        对每个组团对给出：中心距、双方职能与规模、**直达线路数、其中轨道数**。
        """
        if self.single:
            return []
        pair = defaultdict(lambda: {"lines": 0, "rail": 0, "names": []})
        for f in carto.layer("routes"):
            # ⚠️ 只算**客运**线路：货运铁路/货运航线不是"组团之间的通勤连通"，
            # 混进来会把"哪两个组团没有直达公交"的判读带偏（见 SKILL.md 第 2 节 货运与产业链）。
            if not is_passenger_route(f):
                continue
            is_rail = f.get("Transport") in ("Train", "Subway", "Tram")
            for k in self.route_cluster_pairs(f):
                pair[k]["lines"] += 1
                if is_rail:
                    pair[k]["rail"] += 1
                if len(pair[k]["names"]) < 4:
                    pair[k]["names"].append(f.get("Name"))
        rows = []
        for i, ga in enumerate(self.groups):
            for gb in self.groups[i + 1:]:
                na, nb = ga.get("name"), gb.get("name")
                if not na or not nb:
                    continue
                key = (na, nb) if na <= nb else (nb, na)
                tr = pair.get(key, {})
                ca, cb = ga["center"], gb["center"]
                rows.append({
                    "a": na, "b": nb,
                    "type_a": ga.get("type"), "type_b": gb.get("type"),
                    "dist_km": math.hypot(ca[0] - cb[0], ca[1] - cb[1]) / 1000.0,
                    "dir": bearing_cn(cb[0] - ca[0], cb[1] - ca[1]),
                    "mass_a": ga["mass"], "mass_b": gb["mass"],
                    "jobs_a": ga["jobs"], "res_a": ga["res"],
                    "jobs_b": gb["jobs"], "res_b": gb["res"],
                    "lines": tr.get("lines", 0), "rail": tr.get("rail", 0),
                    "line_names": tr.get("names", []),
                })
        rows.sort(key=lambda r: (-r["lines"], r["dist_km"]))
        return rows


def cluster_traffic_hotspots(traffic, cell=800.0, top=8):
    """把拥堵候选段按 800 m 网格聚成**热点区**，便于给"去哪治"的建议。

    返回 `list[{x, y, segments, veh_km, vpl_max, names, lanes, limits}]`，按车公里负荷排序。
    """
    if not traffic:
        return []
    agg = defaultdict(lambda: {"n": 0, "vk": 0.0, "vpl": 0.0, "names": Counter(),
                               "lanes": [], "limits": [], "cats": Counter()})
    for s in traffic["hot"]:
        x, y = s["f"].compute_centroid()
        k = (int(x // cell) * cell, int(y // cell) * cell)
        d = agg[k]
        d["n"] += 1
        d["vk"] += s["vk"]
        d["vpl"] = max(d["vpl"], s["vpl"])
        d["names"][s["name"] or "未命名"] += 1
        d["lanes"].append(s["lane"])
        d["limits"].append(s["limit"])
        d["cats"][s["cat"]] += 1
    out = []
    for (gx, gy), d in agg.items():
        out.append({
            "x": gx + cell / 2, "y": gy + cell / 2,
            "segments": d["n"], "veh_km": d["vk"], "vpl_max": d["vpl"],
            "names": [n for n, _ in d["names"].most_common(3)],
            "lane_median": sorted(d["lanes"])[len(d["lanes"]) // 2],
            "limit_median": sorted(d["limits"])[len(d["limits"]) // 2],
            "cat": d["cats"].most_common(1)[0][0],
        })
    out.sort(key=lambda r: -r["veh_km"])
    return out[:top]



def analyze_trend(dirs):
    """多期 Carto 导出 → 趋势表。回答「我的改动到底把税基推高了还是推低了」。

    单期快照只能看现状；有了多期才能判断**方向**。每期压成同构快照（人口、岗位、
    税基指数代理、分区图斑、路网、逐线乘客），按目录名排序输出成表。
    """
    snaps = []
    for d in dirs:
        try:
            c = CartoData(d)
        except Exception:
            continue
        z = analyze_zoning(c)
        try:
            tax = analyze_tax_potential(c, z)
        except Exception:
            tax = None
        routes = {}
        for f in c.layer("routes"):
            routes[f.get("Name")] = {"pax": f.get("Passenger") or 0,
                                     "veh": f.get("Vehicle") or 0,
                                     "object": f.get("Object") or PASSENGER_ROUTE_OBJECT}
        s = {
            "dir": os.path.basename(os.path.abspath(d)),
            "population": c.total_population(),
            "jobs": c.total_jobs(),
            "zoning_tiles": {r["zoning"]: r["count"] for r in z["zones"]},
            "zoning_total": sum(r["count"] for r in z["zones"]),
            "road_km": sum(f.line_length() for f in c.layer("roads")) / 1000.0,
            "tax_index": tax["total_tax_index"] if tax else None,
            "labor_self_sufficiency": tax["labor_self_sufficiency"] if tax else None,
            "routes": routes,
            # ⚠️ 「线路乘客合计」**只含客运**（`RoutePassenger`）—— 货运线路的 Passenger 恒为 0，
            # 不影响数值，但口径必须写明（见 SKILL.md 第 2 节 货运与产业链）。
            "route_pax_total": sum(v["pax"] for v in routes.values()
                                   if v.get("object") != CARGO_ROUTE_OBJECT),
        }
        s["job_housing"] = (s["jobs"] / s["population"]) if s["population"] else None
        snaps.append(s)
    return {"snapshots": snaps}


# ------------------------------------------------------------------ 游戏时间与时点可比性
#: 时段划分（按**小时**，CSL2 的一天）。`peak` 标记是否通勤峰。
GAME_TIME_BANDS = (
    (0, 5, "凌晨", False),
    (6, 9, "早高峰", True),
    (10, 15, "日间平峰", False),
    (16, 19, "晚高峰", True),
    (20, 23, "夜间", False),
)
#: ⭐ **商业热门时段**（小时，闭区间）= 日间平峰 10–15 时 ＋ 晚高峰 16–19 时。
#: 用途：商业盈亏有**潮汐性** —— 凌晨（0–5 时）存档大概率一片不赚钱，日间未必，
#: 所以**只有落在这个时段内的存档**才能用来判"商业是不是真的在亏"。
#: ⚠️ 这是**经验口径**（由上面两个时段拼成），游戏官方没有给过"营业高峰"的定义。
COMMERCIAL_PEAK_HOURS = (10, 19)
#: 每个指标对"时点"的敏感度。**强敏感 = 跨时段数值不可比**。
#: 这是本 skill 里 `Passenger` 类读数最重要的使用纪律。
METRIC_TIME_SENSITIVITY = {
    "strong": [
        "线路乘客数 `Passenger`", "站点/线路客流", "断面客流",
        "车流量 `Volume` 与单车流量", "拥堵程度",
        # ⭐ 商业顾客数与**商业/零售的公司利润**随营业时段变化（潮汐）——
        # 凌晨的"亏损"是时段现象，不是经营问题（工业/办公利润敏感度低得多，见 medium）。
        "商业顾客数", "商业（零售/餐饮/住宿）的公司利润与亏损店清单",
        "公交候车与在车人数", "步行与自行车流量",
    ],
    "medium": [
        "就业中心分布", "通勤距离分布", "服务设施负载", "垃圾/殡葬等服务压力",
        "工业 / 办公 / 农业的公司利润（敏感度低于商业）",
    ],
    "weak": [
        "人口 / 岗位 / 职住比", "建筑数与建筑等级", "分区图斑", "路网与轨道里程",
        "线路配车数 `Vehicle`、线位几何、站数", "地块解锁数",
        "可建造性与高程等地形量", "税基与税率结构",
    ],
}


def game_time_band(hour):
    """给小时 → `(时段名, 是否通勤峰)`；`hour` 为 None 时返回 `(None, None)`。"""
    if hour is None:
        return None, None
    for lo, hi, name, peak in GAME_TIME_BANDS:
        if lo <= hour <= hi:
            return name, peak
    return None, None


def _band_index(hour):
    """时段在 `GAME_TIME_BANDS` 里的序号，用于算"跨了几个时段"。"""
    if hour is None:
        return None
    for i, (lo, hi, _n, _p) in enumerate(GAME_TIME_BANDS):
        if lo <= hour <= hi:
            return i
    return None


def resolve_game_time(carto, saves=None, override=None):
    """定出**该次分析对应的游戏内时间**。

    **默认路径 = 自动读存档，无需用户输入。**
    规则见 `core.carto_reader.find_save_for_carto()`：人口合理性过滤 → 取时间最接近的存档 → 72h 窗口。
    `override`（CLI `--at`）只作为**纠错手段**保留：当自动匹配明显不对时用它覆盖。

    两者都拿不到时返回 `hour=None`，**报告必须如实说明并放弃客流类比较**。
    """
    import core.carto_reader as CR
    out = {"time": None, "hour": None, "minute": None, "band": None, "is_peak": None,
           "source": None, "confidence": None, "note": None, "save": None,
           "auto": False}
    if override:
        y = mo = h = mi = None
        if isinstance(override, str):
            m = re.match(r"\s*(\d{3,4})-(\d{1,2})(?:-(\d{1,2}))?\s+(\d{1,2}):(\d{2})", override)
            if m:
                y, mo = int(m.group(1)), int(m.group(2))
                h, mi = int(m.group(4)), int(m.group(5))
            else:
                m2 = re.match(r"\s*(\d{1,2}):(\d{2})", override)
                if m2:
                    h, mi = int(m2.group(1)), int(m2.group(2))
        elif isinstance(override, (tuple, list)):
            vals = list(override) + [None, None, None, None]
            y, mo, h, mi = vals[0], vals[1], vals[2], vals[3]
        if h is None:
            out["note"] = "`--at` 解析失败，请用 `2031-01-22 23:22` 或 `23:22` 格式"
            return out
        out.update({"hour": h, "minute": mi or 0,
                    "source": "用户手动指定（`--at`，纠错用）", "confidence": "高"})
        out["time"] = "%s %02d:%02d" % (("%s-%02d" % (y, mo)) if y is not None else "（仅时段）",
                                        h, mi or 0)
    else:
        # ⭐ 默认：自动从存档元数据读取（不需要用户输入任何时间）
        try:
            auto = CR.attach_game_time(carto, saves=saves)
        except Exception as e:      # noqa: BLE001
            auto = {"hour": None, "note": "自动读取存档时间失败：%s" % e}
        if auto.get("hour") is not None:
            out.update({"hour": auto["hour"], "minute": auto.get("minute"),
                        "save": auto.get("save"), "source": auto.get("source"),
                        "confidence": auto.get("confidence"), "auto": True})
            out["time"] = auto.get("time")
        else:
            out["note"] = auto.get("note") or "未能自动确定游戏内时间"
            return out
    band, peak = game_time_band(out["hour"])
    out.update({"band": band, "is_peak": peak})
    return out


def _circular_hour_gap(h1, h2):
    """两个小时之间的**环形**间隔（小时，24 h 制）。"""
    if h1 is None or h2 is None:
        return None
    d = abs(h1 - h2)
    return min(d, 24 - d)


def compare_game_time(prev_time, cur_time):
    """**跨期比较的第一道关**：先判两次导出的游戏内时间是否可比。

    ⚠️ **判据用"环形小时差"，不是时段序号差。** 时段序号会把「凌晨(0) → 早高峰(1)」
    误判成"相邻"，而这两者的客流是**数量级**差异 —— 正是最需要拦住的情况。
    另加一条硬规则：**一端在凌晨（0–5 时）、另一端在通勤峰 → 一律不可比**。

    返回 `verdict`（`可比`/`需谨慎`/`不可比`/`未知`）、`hour_gap`、
    `usable`（还能比的指标）、`blocked`（不能比的指标）、`recommend_save`（建议下次存档时段）。
    """
    ph, ch = (prev_time or {}).get("hour"), (cur_time or {}).get("hour")
    out = {"prev": prev_time, "cur": cur_time, "verdict": "未知", "hour_gap": None,
           "band_gap": None,
           "usable": list(METRIC_TIME_SENSITIVITY["weak"]),
           "blocked": [], "recommend_save": None, "reason": None,
           "prev_band": None, "cur_band": None}

    if ph is None or ch is None:
        out["verdict"] = "未知"
        out["blocked"] = (METRIC_TIME_SENSITIVITY["strong"]
                          + METRIC_TIME_SENSITIVITY["medium"])
        missing = [n for n, h in (("上一期", ph), ("本期", ch)) if h is None]
        out["reason"] = ("%s的游戏内时间未知 → **所有随时间变化的指标都不能比较**。"
                         % "、".join(missing))
        # 仍给出建议：**只说未知的那一侧**，不要把已知的一侧也说成未知
        if ph is not None and ch is None:
            lo, hi, name, peak = GAME_TIME_BANDS[_band_index(ph)]
            _wl, _wh = (("%02d:00" % (lo + 1), "%02d:00" % hi) if peak
                        else ("%02d:30" % lo, "%02d:30" % hi))
            out["recommend_save"] = {
                "window": "%s–%s" % (_wl, _wh), "band": name, "match_prev": True,
                "why": ("**本期时间读不到**（%s），但上一期是 **%s（%s）**。"
                        "请检查本期的 Carto 导出目录是否完整（要有 `GeoJSON/` 或 `Shapefile/`），"
                        "并确认**该导出对应的存档仍在 `Saves\\<SteamID>\\` 里**"
                        "（导出后立刻存档即可保证匹配）。"
                        "重取时请在 **%s 之间**存档，这样就能与上一期逐项对比。"
                        % (cur_time.get("note") or "原因见上",
                           (prev_time or {}).get("time") or "?", name,
                           "%s–%s" % (_wl, _wh)))}
        elif ph is None and ch is not None:
            out["recommend_save"] = {
                "window": None, "band": cur_time.get("band"), "match_prev": False,
                "why": ("**本期时间已自动读到（%s，%s）**，但上一期读不到。"
                        "本期这一份**可以正常用**；若要与其他期比较，"
                        "请让上一期的 Carto 导出目录保持完整、且其对应存档仍在存档目录里。"
                        % (cur_time.get("time"), cur_time.get("band")))}
        else:
            out["recommend_save"] = {
                "window": None, "band": None, "match_prev": False,
                "why": ("两期时间都读不到。请确认两期的 Carto 目录都完整"
                        "（含 `GeoJSON/` 或 `Shapefile/`），且导出后**没有删除对应存档**；"
                        "并**每次都挑同一个时段导出**（例如都用早高峰 07:00–09:00）。")}
        return out

    pb, pp = game_time_band(ph)
    cb, cp = game_time_band(ch)
    pi, ci = _band_index(ph), _band_index(ch)
    gap = _circular_hour_gap(ph, ch)
    out.update({"prev_band": pb, "cur_band": cb, "hour_gap": gap,
                "band_gap": abs(pi - ci)})
    night = (0, 5)
    prev_night = night[0] <= ph <= night[1]
    cur_night = night[0] <= ch <= night[1]

    # ① 同一时段 → 完全可比
    if pi == ci:
        out["verdict"] = "可比"
        out["usable"] = (METRIC_TIME_SENSITIVITY["weak"] + METRIC_TIME_SENSITIVITY["medium"]
                         + METRIC_TIME_SENSITIVITY["strong"])
        out["reason"] = ("两次都在**%s**（%02d 时 vs %02d 时）→ 同属一个时段，"
                         "**包括客流在内的指标都可以比较**。" % (pb, ph, ch))
    # ② 凌晨 ↔ 通勤峰 → 硬性不可比（客流数量级差异，最容易被误读成"客流下降"）
    elif (prev_night and cp) or (cur_night and pp):
        out["verdict"] = "不可比"
        out["usable"] = list(METRIC_TIME_SENSITIVITY["weak"])
        out["blocked"] = (METRIC_TIME_SENSITIVITY["strong"]
                          + METRIC_TIME_SENSITIVITY["medium"])
        out["reason"] = ("一次在**%s**、另一次在**%s**（相隔约 %.1f 小时）—— "
                         "**深夜与通勤峰的客流是数量级差异**，跨这两个时点比较客流"
                         "会把时点差读成趋势，**结论必然错误**。"
                         % (pb, cb, gap))
    # ③ 其余按环形小时差
    elif gap is not None and gap <= 3.0:
        out["verdict"] = "需谨慎"
        out["usable"] = METRIC_TIME_SENSITIVITY["weak"] + METRIC_TIME_SENSITIVITY["medium"]
        out["blocked"] = list(METRIC_TIME_SENSITIVITY["strong"])
        out["reason"] = ("两次在**相近时段**（%s → %s，相隔约 %.1f 小时）→ "
                         "客流/流量类指标仍有**系统性偏差**，只能作方向性参考，"
                         "不能当数值增减引用。" % (pb, cb, gap))
    else:
        out["verdict"] = "不可比"
        out["usable"] = list(METRIC_TIME_SENSITIVITY["weak"])
        out["blocked"] = (METRIC_TIME_SENSITIVITY["strong"]
                          + METRIC_TIME_SENSITIVITY["medium"])
        out["reason"] = ("两次相隔约 **%.1f 小时**（%s → %s）→ "
                         "**客流/流量类差异几乎全部由时点造成**；"
                         "任何基于它们的「上升/下降」结论**都是错的**。" % (gap, pb, cb))

    # —— 建议下次存档时间：回到上一次的时段内 ——
    if out["verdict"] != "可比":
        lo, hi, name, peak = GAME_TIME_BANDS[pi]
        if peak:
            # 峰内取整点窗口（避开峰边界的过渡时刻）
            w_lo, w_hi = "%02d:00" % (lo + 1), "%02d:00" % hi
        else:
            w_lo, w_hi = "%02d:30" % lo, "%02d:30" % hi
        out["recommend_save"] = {
            "window": "%s–%s" % (w_lo, w_hi), "band": name, "match_prev": True,
            "why": ("上一期存于 **%s**（%s）。要让**客流/流量类指标可比**，"
                    "**下一次请在 %s 之间存档** —— 与上一期同一时段，两次即可逐项对比。"
                    "（若只关心不随时段变的指标，如人口/岗位/建筑等级/配车数，"
                    "则任何时间存档都可以。）"
                    % ((prev_time or {}).get("time") or "?", name, "%s–%s" % (w_lo, w_hi)))}
    else:
        out["recommend_save"] = {"window": None, "band": pb, "match_prev": True,
                                 "why": ("两次已在同一时段（%s）；下次存档**保持同一时段**即可。" % pb)}
    return out


def analyze_delta(carto, prev, prev_time=None, cur_time=None):
    """把两次 Carto 导出做增量对比 —— 只有对比才能判断「这一步改动到底有没有用」。

    ⭐ **先挂上游戏内时间的可比性结论**（`game_time`），报告 第 20.0 节 会先读它。
    """
    def snap(c):
        rts = {}
        for f in c.layer("routes"):
            rts[f.get("Name")] = {"pax": f.get("Passenger") or 0, "veh": f.get("Vehicle") or 0,
                                  "stops": f.get("Stop") or 0, "transport": f.get("Transport"),
                                  # ⚠️ 客/货分界的唯一判据：`Route_Centerline.Object`
                                  "object": f.get("Object") or PASSENGER_ROUTE_OBJECT}
        z = {}
        for f in c.layer("zoning"):
            k = f.get("Zoning") or "None"
            z[k] = z.get(k, 0) + 1
        return {
            "population": c.total_population(), "jobs": c.total_jobs(),
            "tiles_unlocked": len(c.unlocked_tiles()),
            "districts": {d.get("Name"): {"res": d.get("Resident") or 0,
                                          "emp": d.get("Employee") or 0} for d in c.districts()},
            "routes": rts, "zoning_tiles": z,
            "road_km": sum(f.line_length() for f in c.layer("roads")) / 1000.0,
            "zoning_total": sum(z.values()),
        }

    cur, old = snap(carto), snap(prev)
    d = {"population": cur["population"] - old["population"],
         "jobs": cur["jobs"] - old["jobs"],
         "tiles_unlocked": cur["tiles_unlocked"] - old["tiles_unlocked"],
         "road_km": cur["road_km"] - old["road_km"],
         "zoning_total": cur["zoning_total"] - old["zoning_total"],
         "districts": [], "routes": []}
    for name in sorted(set(cur["districts"]) | set(old["districts"])):
        a = cur["districts"].get(name, {"res": 0, "emp": 0})
        b = old["districts"].get(name, {"res": 0, "emp": 0})
        d["districts"].append({"name": name, "res_delta": a["res"] - b["res"],
                               "emp_delta": a["emp"] - b["emp"],
                               "res_now": a["res"], "emp_now": a["emp"]})
    for name in sorted(set(cur["routes"]) | set(old["routes"])):
        a, b = cur["routes"].get(name), old["routes"].get(name)
        # ⚠️ 客/货分界：货运线路（`RouteCargo`）**只做配车/站数/里程对比，不参与乘客口径**。
        _obj = (a or b or {}).get("object") or PASSENGER_ROUTE_OBJECT
        _is_cargo = _obj == CARGO_ROUTE_OBJECT
        if a and b:
            d["routes"].append({"name": name, "transport": a["transport"], "status": "保留",
                                "object": _obj, "is_cargo": _is_cargo,
                                "pax_delta": a["pax"] - b["pax"], "pax_now": a["pax"],
                                "veh_delta": a["veh"] - b["veh"], "veh_now": a["veh"]})
        elif a:
            d["routes"].append({"name": name, "transport": a["transport"], "status": "新增",
                                "object": _obj, "is_cargo": _is_cargo,
                                "pax_delta": a["pax"], "pax_now": a["pax"],
                                "veh_delta": a["veh"], "veh_now": a["veh"]})
        else:
            d["routes"].append({"name": name, "transport": b["transport"], "status": "已删除",
                                "object": _obj, "is_cargo": _is_cargo,
                                "pax_delta": -b["pax"], "pax_now": 0,
                                "veh_delta": -b["veh"], "veh_now": 0})
    d["zoning_delta"] = {k: cur["zoning_tiles"].get(k, 0) - old["zoning_tiles"].get(k, 0)
                         for k in set(cur["zoning_tiles"]) | set(old["zoning_tiles"])}
    # ⭐⭐ 挂上游戏内时间的可比性（报告 第 20.0 节 会**先**读它，再读任何数值增量）
    d["game_time"] = compare_game_time(prev_time, cur_time)
    # 时点不可比时，把客流差从结论里剔除（保留在 JSON 里供人工核查，但报告不展示）
    if d["game_time"].get("verdict") in ("不可比", "未知"):
        for r in d["routes"]:
            r["pax_delta_unreliable"] = True
    return d


_STATUS_CN = {"达标": "✅ 达标", "偏弱": "⚠️ 偏弱", "不达标": "❌ 不达标", "未知": "❓ 未知"}


def _st_cn(item):
    """基础体检条目的状态中文标签。"""
    return _STATUS_CN.get((item or {}).get("status"), "❓ 未知")


def build_report(carto, out_md, out_json=None, prev=None, trend=None, maps_dir=None,
                 at=None, prev_at=None, auto_time=True):
    maps = {}
    if maps_dir:
        # 配图与建议成对出现：给出建议时同时给出**可核验的空间依据**。
        # 用元数据 + 干道 + 组团公交三张，避免"只有文字没有图"。
        try:
            import os as _os
            from analysis.city_map import make_map as _mk
            _os.makedirs(maps_dir, exist_ok=True)
            specs = [
                # ⭐ 每张图都带 `unlocked`：精确的已解锁区域边界（未解锁压成浅灰），
                # 让读者一眼看出"哪些范围是可规划/可比较的"。
                ("unlocked", "已解锁区域边界", ["unlocked", "roads", "arterial"]),
                ("terrain", "地形与干道", ["terrain", "unlocked", "roads", "arterial"]),
                ("arterial", "干道路网（不含支路）", ["unlocked", "roads", "arterial"]),
                ("transit_advice", "组团与公交可达性",
                 ["unlocked", "clusters", "roads", "arterial", "transit"]),
                ("overview", "综合（地形+路网+公交）",
                 ["terrain", "unlocked", "roads", "transit"]),
            ]
            for key, _label, layers in specs:
                p = _os.path.join(maps_dir, "map-%s.png" % key)
                _mk(carto, p, layers, width=1500, height=1500)
                maps[key] = p
            maps["_dir"] = maps_dir
        except Exception as _e:      # noqa: BLE001  配图失败不该让报告失败
            maps = {"_error": str(_e)}
    # ⚠️ **必须先裁剪到已解锁地块**：高速/铁路会伸到未解锁区域（实测高速仅 29.7% 在解锁内），
    # 不裁剪会把城际里程算成城内里程。`apply_unlocked_clip()` 会把裁剪值注入各要素，
    # 之后所有 `f.line_length()` / `z.polygon_area()` 调用点自动使用裁剪口径。
    carto.apply_unlocked_clip()
    # ⚠️ **上一期也必须裁剪**：否则 `--prev` 会拿"裁剪后的本期"去比"未裁剪的上一期"，
    # 把纯口径差当成里程增减（实测同一目录自比会显示 −91 km 的路网变化）。
    if prev is not None:
        prev.apply_unlocked_clip()
    city = analyze_city(carto)
    zoning = analyze_zoning(carto)
    roads = analyze_roads(carto)
    routes = analyze_routes(carto)
    overlap = analyze_overlap(passenger_routes(carto))
    catchment = analyze_catchment(carto)
    centers = identify_job_centers(carto)
    terrain = analyze_terrain(carto)
    eff = analyze_land_efficiency(carto, zoning)
    risk = analyze_risk_proxies(carto, catchment, roads, zoning)
    tax = analyze_tax_potential(carto, zoning)
    noise = analyze_noise_exposure(carto)
    underdev = analyze_underdevelopment(carto)
    lanekm = analyze_lane_km(roads)
    tsq = analyze_transit_service_quality(carto, routes)
    cov = analyze_stop_coverage(carto)
    svc = analyze_service_coverage(carto)
    commute = analyze_commute_access(carto)
    freight = analyze_freight_access(carto)
    rtb = analyze_real_tax_base(carto)
    traffic = analyze_traffic(carto)
    tclusters = cluster_traffic_hotspots(traffic)
    elev_plan = analyze_elevation_planner(carto)
    # 游戏内时间：跨期比较的第一道关（见 compare_game_time）
    # **默认自动从存档读取**（`auto_time=True`）；`--no-auto-time` 或 `--at` 可覆盖。
    try:
        _c_at = at if at else (None if auto_time else "__skip__")
        _p_at = prev_at if prev_at else (None if auto_time else "__skip__")

        def _resolve(c, ov):
            if ov == "__skip__":
                return {"hour": None, "note": "已用 `--no-auto-time` 禁用自动读取，"
                                              "且未用 `--at` 给出时间"}
            return resolve_game_time(c, override=ov)

        cur_time = _resolve(carto, _c_at)
        prev_time = _resolve(prev, _p_at) if prev is not None else None
    except Exception as _te:      # noqa: BLE001
        cur_time = prev_time = {"hour": None, "note": "时间解析失败：%s" % _te}
    delta = analyze_delta(carto, prev, prev_time=prev_time, cur_time=cur_time) \
        if prev is not None else None
    # 基础体检（第 1 层）——需要 roads 与组团，所以放在它们算完之后
    found = None

    # -------- 方位定位器：**弱化绝对坐标**，把位置表述成「东侧 1.2 km」这类方位词 --------
    # 原点取人口重心（无人口时退回城市 bbox 中心），这样方位与人的直觉一致。
    _pts = carto.populated_points()
    if _pts:
        _tw = sum(w for _x, _y, w in _pts) or 1
        loc = Locator(sum(x * w for x, _y, w in _pts) / _tw,
                      sum(y * w for _x, y, w in _pts) / _tw)
    else:
        _b = carto.city_bounds() or (0, 0, 0, 0)
        loc = Locator((_b[0] + _b[2]) / 2.0, (_b[1] + _b[3]) / 2.0)

    def LOC(x, y):
        """点位 → 位置表述。**优先用组团语言**（「<行政区>·<方位>组团」）；
        无 District 数据时才退回「相对人口重心的方位词」。两者都**不含绝对坐标**。"""
        return CWHERE(x, y)

    # -------- 可建造性查询（最高级别约束：水体/陡坡不得作为建议落点） --------
    _bgrid = (terrain or {}).get("buildability_grid")
    _b_off = (terrain or {}).get("utm_offset") or (0.0, 0.0)

    def BUILDABLE(x, y):
        """给一个**GeoJSON 坐标系**下的点做地形体检，返回 OK / 需整地 / 禁 / 无数据。

        ⚠️ 注意：调用方传的是 GeoJSON 坐标，而可建造性栅格在 UTM 系 —— 这里内部完成平移，
        调用方不必关心坐标系（`analyze_terrain` 已把标定平移量放在 `utm_offset`）。
        内部用 3×3 邻域取样，避免地图边缘的单像素 NoData 把整条建议打成未知。
        """
        if not _bgrid:
            return "无数据"
        try:
            from core import terrain as _T
            return _T.verdict_text(_bgrid, x + _b_off[0], y + _b_off[1])
        except Exception:
            return "无数据"

    # -------- 组团：把"绝对坐标"换成"组团 + 组团间关系"（报告全篇用它表述位置） --------
    cluster = ClusterMap(carto)
    CWHERE = (lambda x, y: cluster.where(x, y, loc))
    if cluster.single:
        CWHERE = (lambda x, y: LOC(x, y))

    # -------- 基础体检（第 1 层）：必须在任何税收表述之前算出来 --------
    try:
        found = analyze_foundation(carto, city=city, roads=roads, cmap=cluster)
    except Exception as _fe:      # noqa: BLE001  体检失败不该让报告失败
        found = {"items": [], "blocking": ["基础体检计算失败：%s" % _fe],
                 "n_blocking": 0, "gate_open": False,
                 "policy": "基础体检未能完成 → 税收建议同样降级为「暂缓」。"}

    # -------- 数据自检：数据不可用时必须告警，不能让"人口 0"的报告被当结论用 --------
    checks = []
    if not carto.layer("buildings"):
        checks.append("**未读到任何建筑数据（Building_Boundary 为空）** —— Carto 目录可能不对，"
                      "本报告所有数字都不可用。")
    if city["population"] == 0 and city["jobs"] == 0:
        checks.append("**人口与岗位都是 0** —— 城市可能尚未有人口，或导出目录/字段不匹配。")
    if not carto.layer("routes"):
        checks.append("未读到线路数据（Route_Centerline 为空）—— 公共交通章节不可用。")
    if not carto.layer("roads"):
        checks.append("未读到路网数据（Network_Centerline 为空）—— 路网章节不可用。")
    if roads["segments_outside_city_bounds"]:
        checks.append("有 %d 段道路的几何**伸出已解锁地块之外**（城际高速/铁路为主）—— "
                      "**本报告的里程与流量已裁剪到已解锁范围内**（见 第 3 节 两个口径），"
                      "但「按全域统计的分子 vs 按地块统计的分母」在其他指标上仍可能有口径差，"
                      "涉及里程/密度时请以 第 3 节 的「解锁内」列为准。"
                      % roads["segments_outside_city_bounds"])
    if terrain and terrain.get("raster_covers_city") is False:
        _r = terrain.get("elev_coverage_ratio")
        checks.append("高程栅格**未覆盖全部建筑**（仅 %.0f%% 能取到高程值）—— "
                      "地形统计只代表覆盖到的那部分。" % (100 * _r) if _r is not None
                      else "高程栅格未覆盖城市全域 —— 地形统计只代表覆盖到的那部分。")
    # 标定质量自检：解出的平移量**看起来**误差很小，也可能只是"落在同一级台地上"的伪解
    # （台地地形有大量等高区）。所以同时看 P90 与"1 m 内占比"，任一不达标就告警。
    _q = (terrain or {}).get("utm_calibration") or {}
    if _q:
        _p90 = _q.get("p90_m")
        _w1 = _q.get("within_1m")
        if (_p90 is not None and _p90 > 1.0) or (_w1 is not None and _w1 < 0.95):
            checks.append(
                "⚠️ **地形坐标标定质量差**（中位误差 %s m / P90 %s m / 1 m 内占比 %s）—— "
                "台地地形会产生等高伪解，这个平移量很可能是错的，"
                "**第 8 节/第 8.1 节/第 8.3 节 的地形与可建造性结论不可用**。"
                "核验方式：修 `core/terrain.py` 的 `solve_utm_offset()`（锚点必须用 MapTile bbox 中心，"
                "判优必须看 P90 而非中位数），不要靠调大搜索范围。"
                % (fmt(_q.get("median_m"), 3), fmt(_p90, 3),
                   ('%.3f' % _w1) if _w1 is not None else "—"))
    for w in routes.get("warnings", []):
        checks.append(w)

    L = []
    A = L.append

    # -------- 配图：**标准图片 Markdown**（图题在图下、图号连续） --------
    # 必须用 `![题](路径)` 而不是把文件名写进反引号：`export_report.py` 靠它把图
    # 嵌进 DOCX（见 `references/110-deliverable-format.md` 第 6 节）。
    # 同一 `key` 只出一次图，重复调用返回已有图号（供跨节引用同一张图）。
    _fig_no = [0]
    _fig_reg = {}

    def FIG(path, caption, note=None, key=None):
        if not path:
            return None
        if key and key in _fig_reg:
            return _fig_reg[key]
        _fig_no[0] += 1
        try:
            _rel = os.path.relpath(path, os.path.dirname(os.path.abspath(out_md)) or ".")
        except Exception:                       # noqa: BLE001
            _rel = os.path.basename(path)
        A("![图 %d  %s](%s)\n" % (_fig_no[0], caption, str(_rel).replace("\\", "/")))
        if note:
            A(note)
        if key:
            _fig_reg[key] = _fig_no[0]
        return _fig_no[0]

    A("# 城市诊断报告（Carto 导出数据实算）\n")
    b = city["bounds"]
    # 坐标参考系说明按**实际**栅格 bounds 生成（导出可能用不同投影：绝对 UTM 或以地图中心为原点）
    _fmt = {"geojson": "GeoJSON", "shapefile": "Shapefile"}.get(
        getattr(carto, "format", None), "矢量 + GeoTIFF")
    _rb = None
    for _nm in ("Elevation", "WorldElevation"):
        _r = carto.raster(_nm)
        if _r is not None:
            _rb = _r.bounds()
            break
    if _rb:
        _ax, _ay = abs(_rb[0]), abs(_rb[2])
        _crs = ("绝对投影米（如 EPSG:32631）" if _ax > 100000
                else "**以地图中心为原点的投影米**（不是绝对 UTM —— 因此本报告不做绝对坐标引用）")
        A("> 数据源：Carto 导出（%s + GeoTIFF）；栅格为 %s，单位米（1 格 = 8 m）。"
          % (_fmt, _crs))
    else:
        A("> 数据源：Carto 导出（%s + GeoTIFF）。坐标单位米（1 格 = 8 m）。" % _fmt)
    A("> **报告正文不出现绝对数字坐标**：位置一律以**人口重心**为原点的**方位词**表述"
      "（如「东侧 1.2 km」），并给出所属组团。需要绝对坐标请加 `--json`。")
    # ⭐ 游戏内时间：所有"客流/流量"类读数的解读前提
    if cur_time and cur_time.get("hour") is not None:
        _c = cur_time.get("confidence")
        A("> ⏰ **游戏内时间：%s（%s）** —— 来源：%s%s"
          % (cur_time.get("time"), cur_time.get("band"), cur_time.get("source") or "—",
             "" if _c in ("高", "中") else "　⚠️ **置信度低，请核对**"))
        A("> ⚠️ **本报告所有 `Passenger`（线路乘客数）与 `Volume`（车流量）读数都只对此时点成立**。"
          "客流随一天内的时段剧烈变化（早高峰 vs 凌晨可差**数量级**）→ "
          "跨期比较前先看 第 20.0 节 的时点可比性判定。")
    elif cur_time and cur_time.get("note"):
        A("> ⏰ **游戏内时间未知**：%s" % cur_time["note"])
        A("> ⚠️ 因此**本期客流/流量类读数无法与任何其它期比较** —— "
          "它们随时段变化，缺少时点就没有可比性。")
    A("> 所有数字均由脚本实算，不是估计值 —— 但请先读下面的数据自检。\n")
    if maps.get("overview"):
        FIG(maps["overview"], "城市总览（地形 + 路网 + 公交）", key="overview",
            note="> 📍 **读法**：先看它建立整体印象，再读下文各节；"
                 "每节的建议都配有对应的分项图。\n")

    A("## 0. 数据自检")
    if checks:
        for c in checks:
            A("- ⚠️ " + c)
    else:
        A("- ✅ 各项数据齐备，未见覆盖缺口。")
    A("")

    # ---------- 0.5 基础体检（第 1 层）—— 必须排在所有税收节之前 ----------
    if found:
        A("## 0.5 基础体检 —— **先过这一关，再谈税收**（第 1 层）")
        A("> 本诊断是**分层**的：**第 0 层**城市规模持续扩大 → "
          "**第 1 层**四项基础（人口分布均衡 / 失业率正常 / 公交与规模匹配 / 路网分级最优）→ "
          "**第 2 层**才是最大化税收。")
        A("> **基础未达标时，后面所有税收类建议一律降级为「暂缓」。**\n")
        A(md_table(["#", "基础", "判定"],
                   [["1", "人口分布均衡", "**%s**" % _st_cn(found["items"][0])],
                    ["2", "失业率在正常范围", "**%s**" % _st_cn(found["items"][1])],
                    ["3", "公共交通与城市规模匹配", "**%s**" % _st_cn(found["items"][2])],
                    ["4", "路网分级规划", "**%s**" % _st_cn(found["items"][3])]]))
        A("\n> **闸门结论**：%s" % found["policy"])
        if found["blocking"]:
            A("> 拖住的项目：**%s**" % "、".join(found["blocking"]))
        A("")
        for it in found["items"]:
            A("\n### 0.5.%d %s —— %s" % (found["items"].index(it) + 1,
                                          it["name"], _st_cn(it)))
            for d in it["detail"]:
                A("- " + d)
            if it.get("fix"):
                A("\n> **该怎么修**：%s" % it["fix"])
        A("\n> ⚠️ **失业率必须问玩家要游戏内读数** —— Carto 无此字段（已核实全部图层），"
          "上面的供需比只是代理，不能替代。")
        A("> 第 0 层（城市规模持续扩大）请看 第 1 节 与 第 19 节 的增速对比。")
        A("")

    A("## 1. 城市规模")
    A(md_table(["指标", "数值", "口径"],
               [["人口", fmt(city["population"]), "District 汇总（无 District 时退化为 Building 汇总）"],
                ["岗位", fmt(city["jobs"]), "同上"],
                ["职住比（岗位/人口）", fmt(city["job_housing_ratio"], 2), "同上"],
                ["已解锁地块", city["unlocked_tiles"], "MapTile Unlocked=1"],
                ["范围 bbox(m)", ("%.0f, %.0f → %.0f, %.0f" % b) if b else "—", "已解锁地块并集"]]))
    if city["building_totals"]:
        bt = city["building_totals"]
        A("\n> 另按建筑逐栋汇总：人口 %s / 岗位 %s（与上表可能有小差异，因为地块汇总与建筑汇总不是同一口径）。"
          % (fmt(bt.get("population")), fmt(bt.get("jobs"))))
    if city["districts"]:
        A("\n### 区级结构\n")
        rows = []
        for d in sorted(city["districts"], key=lambda x: -x["residents"]):
            rows.append([d["name"], fmt(d["residents"]), fmt(d["employees"]),
                         fmt((d["employees"] / d["residents"]) if d["residents"] else None, 2),
                         fmt(d["area_m2"] / 1e6, 2)])
        A(md_table(["区", "人口", "岗位", "职住比", "面积 km²"], rows))

    # ---------- 组团与组团间关系（"用组团代替坐标"的落地） ----------
    if not cluster.single:
        A("\n### 1.1 **组团**（按人口/岗位密集程度划分 —— 不是按行政区划）\n")
        A("> **划分依据**：把建筑的人+岗聚到 **%d m 网格**，取密度分位 **%.0f%%** 作密集核"
          "（阈值 **%s 人+岗/格**），再做形态学闭运算把相邻密块连成一片，"
          "8 邻域连通域即一个组团；规模 < %s 的碎块并入最近的组团。"
          % (CLUSTER_CELL, CLUSTER_DENSITY_Q * 100,
             fmt(cluster.groups[0].get("threshold"), 0), fmt(CLUSTER_MIN_MASS, 0)))
        A("> **行政区划只用于命名与定位**（`<主导行政区>·<相对城市中心方位>组团`），"
          "**不参与划分** —— 行政边界是人为划的，与人实际聚在哪并不一致。")
        A("> **方位基准是城市人口重心**：所以「中心组团」确实在中心、「东北组团」确实在东北。\n")
        A(md_table(["组团", "职能", "人口", "岗位", "职住比", "面积 km²", "密度 人+岗/km²", "方位"],
                   [[g["name"], g["type"], fmt(g["res"], 0), fmt(g["jobs"], 0),
                     fmt(g["job_res_ratio"], 2), fmt(g["area_km2"], 2),
                     fmt(g["mass"] / g["area_km2"] if g["area_km2"] else None, 0),
                     "%s %.1f km" % (g["dir"], g["dist_km"])]
                    for g in cluster.groups]))
        _emp = [g for g in cluster.groups if g["type"] == "就业主导"]
        _res = [g for g in cluster.groups if g["type"] == "居住主导"]
        _mix = [g for g in cluster.groups if g["type"] == "职住混合"]
        A("\n> **结构读数**：共 **%d 个组团** —— **就业主导 %d 个**、居住主导 %d 个、职住混合 %d 个。"
          % (len(cluster.groups), len(_emp), len(_res), len(_mix)))
        if _res and _emp:
            _big_res = max(_res, key=lambda g: g["res"])
            _big_emp = max(_emp, key=lambda g: g["jobs"])
            A("> 最大居住组团是 **%s**（%.0f 人，职住比 %s），最大就业组团是 **%s**（%.0f 岗）—— "
              "**这两者之间的关系就是全城通勤的主轴**。"
              % (_big_res["name"], _big_res["res"], fmt(_big_res["job_res_ratio"], 2),
                 _big_emp["name"], _big_emp["jobs"]))
        else:
            # 没有"就业主导"组团时，用"单位人口岗位最多"的组团代替，给出同样的主轴判断
            _g = sorted(cluster.groups, key=lambda g: -(g["job_res_ratio"] or 0))[0]
            _r = max(cluster.groups, key=lambda g: g["res"])
            A("> **通勤主轴**：全城人口最集中的是 **%s**（%.0f 人，职住比 %s），"
              "而岗位密度最高的是 **%s**（%.0f 岗、职住比 %s）—— "
              "**这两者之间的关系就是全城通勤的主轴**，也是公交最该强化的一对。"
              % (_r["name"], _r["res"], fmt(_r["job_res_ratio"], 2),
                 _g["name"], _g["jobs"], fmt(_g["job_res_ratio"], 2)))
        if not _emp:
            A("> ⚠️ **没有任何「就业主导」组团**（职住比 >1.5）—— 岗位分散在各组团内部、"
              "缺少集中的就业中心。这会同时抬高跨组团通勤比例与公交组织难度："
              "**公交难以用一条干线覆盖「多点到一点」，只能做网格化接驳**。")

        rel = cluster.relations(carto)
        if rel:
            A("\n**组团之间的关系**（按是否有公交/轨道连通排序；只列前 12 对）：\n")
            A(md_table(["组团对", "双方职能", "中心距 km", "直达线路数", "其中轨道", "线路名"],
                       [["**%s ↔ %s**" % (r["a"], r["b"]),
                         "%s ↔ %s" % (r["type_a"], r["type_b"]),
                         fmt(r["dist_km"], 1), r["lines"], r["rail"],
                         "、".join(str(n)[:10] for n in r["line_names"]) or "—"]
                        for r in rel[:12]]))
            _no = [r for r in rel if r["lines"] == 0 and r["dist_km"] <= 3.0]
            if _no:
                A("\n> ⚠️ **有 %d 对 3 km 以内的组团之间没有直达公交/轨道**（%s）—— "
                  "**近距离却无直达，是最该优先补的「组团间关系」缺口**"
                  "（距离近 → 补线的成本最低、见效最快）。"
                  % (len(_no), "、".join("%s↔%s" % (r["a"], r["b"]) for r in _no[:5])))
            _weak = [r for r in rel if r["lines"] > 0 and r["rail"] == 0 and r["dist_km"] > 3.0]
            if _weak:
                A("> ⚠️ **有 %d 对组团相距 >3 km 却只有地面公交**（%s）—— "
                  "长距离组团间的联系靠公交很难压住候车与行程时间，"
                  "远期若要强化这几对关系，应考虑轨道。"
                  % (len(_weak), "、".join("%s↔%s" % (r["a"], r["b"]) for r in _weak[:5])))

    A("\n## 2. 用地/分区结构")
    if zoning["tile_like"]:
        A("> ⚠️ **本表的面积数据不可当「用地面积」用**：Carto 的分区图斑是 8 m × 8 m（≈64 m²）的固定栅格单元，"
          "面积高度一致（已自动检测到）。图斑数反映「有多少个分区单元」，比面积更可靠。\n")
    A(md_table(["分区", "图斑面积合计 km²", "占比", "图斑数"],
               [[z["zoning_cn"], fmt(z["area_km2"], 3), "%.1f%%" % (z["share"] * 100), z["count"]]
                for z in zoning["zones"]]))
    A("\n> 图斑面积合计 %.3f km²（%s）" %
      (zoning["total_area_km2"],
       "**非用地面积**，仅反映已建成用途的栅格单元总量" if zoning["tile_like"] else "按图斑几何累加"))
    if zoning["density_names"]:
        A("\n**建筑密度层级分布**（按建筑名判定）：" +
          "、".join("%s %d 栋" % (k, v) for k, v in sorted(zoning["density_names"].items(), key=lambda kv: -kv[1])))
    if zoning["building_employees"]:
        A("\n### 建筑层面：岗位与人口按分区\n")
        rows = []
        for z, v in sorted(zoning["building_employees"].items(), key=lambda kv: -kv[1]):
            rows.append([z, fmt(zoning["building_residents"].get(z, 0)), fmt(v),
                         fmt(zoning["building_zones"].get(z, 0))])
        A(md_table(["分区", "居民", "岗位", "建筑数"], rows))

    A("\n## 3. 路网结构")
    _hw_r = (roads["highway_km"] / roads["highway_km_full"]) if roads.get("highway_km_full") else None
    _rl_r = (roads["rail_km"] / roads["rail_km_full"]) if roads.get("rail_km_full") else None
    A("> ✅ **口径（重要）**：本节里程**已裁剪到已解锁地块内** —— 高速与铁路的几何会伸出已解锁范围，"
      "按整张地图统计会**系统性高估城内里程**。实测：**高速只有 %.0f%% 落在解锁内**"
      "（%.1f → **%.1f km**），**铁路只有 %.0f%%**（%.1f → **%.1f km**）；"
      "而城内道路（Medium/Small/Large）**100%% 在解锁内**。\n"
      "> 下表「**解锁内 km**」是**规划口径**，「全长 km」仅供对照。\n"
      "> ⭐⭐ **非解锁区内的路网（含高速）一律认定为「地图自带资源」** —— "
      "玩家没修、不拥有、也无权在其上规划。**因此它不得作为「路网等级失衡」的证据**，"
      "**任何等级结构比较都必须先把这部分剔除**。"
      "把它算进城内占比会得出「高速严重过剩」的**假结论** —— 那是地图作者画的，不是玩家的规划失误。\n"
      % ((_hw_r or 0) * 100, roads.get("highway_km_full", 0), roads["highway_km"],
         (_rl_r or 0) * 100, roads.get("rail_km_full", 0), roads.get("rail_km", 0)))
    A(md_table(["道路等级 Category", "路段数", "**解锁内 km**", "全长 km（对照）", "平均车道"],
               [[k, v["n"], "**%s**" % fmt(v["km"], 2), fmt(v.get("km_full"), 2),
                 fmt(v["avg_lanes"], 1)]
                for k, v in sorted(roads["by_category"].items(), key=lambda kv: -kv[1]["km"])]
               + [["**合计**", roads["segments"], "**%s**" % fmt(roads["total_km"], 2),
                   fmt(roads.get("total_km_full"), 2), "—"]]))
    A("\n- 高速里程（**解锁内**）%.1f km，占已解锁路网 %.1f%%"
      % (roads["highway_km"], (roads["highway_share"] or 0) * 100))
    A("  - ⚠️ 口径提醒 ①：CSL2 的高速在数据里通常**按方向各记一条**（`Direction=Forward`），"
      "所以里程含**双向路幅**，比「实际道路长度」大约翻倍。按方向分列：%s"
      % "、".join("%s %.1f km" % (k, v) for k, v in
                  sorted(roads["by_direction_km"].items(), key=lambda kv: -kv[1])))
    if roads.get("highway_km_full"):
        A("  - ⭐⭐ 口径提醒 ②：**高速全长 %.1f km，其中只有 %.1f km 在已解锁地块内"
          "（%.0f%%）**；剩下的 **%.1f km 位于非解锁区，属「地图自带资源」** —— "
          "玩家没修、不拥有、也无权在其上规划。"
          "**本报告的一切等级结构判定都只用「解锁内」口径**；"
          "**非解锁区高速不得作为「路网等级失衡」的证据**，"
          "拿它去论证「城内高速过剩」「高速穿城」是**误判**（那是地图作者的安排，不是玩家的规划失误）。"
          % (roads["highway_km_full"], roads["highway_km"],
             100.0 * roads["highway_km"] / max(1e-9, roads["highway_km_full"]),
             roads.get("highway_km_map_native") or 0.0))
        A("  - 对照（**仅供看地图全貌，不进任何判据**）：若按整张地图算，"
          "高速占全路网 %.1f%% —— **这个数不要用在城内规划结论里**。"
          % ((roads.get("highway_share_full") or 0) * 100))
    if roads["road_density_km_per_km2"]:
        A("- 建成区路网密度 ≈ %.1f km/km²（分子为**已解锁内**路网长度 —— "
          "**非解锁区的地图自带路网已剔除**；分母为建成区 bbox %.1f km²，"
          "**属粗估**；现实标准参考 3–4 km/km²）"
          % (roads["road_density_km_per_km2"], roads["built_area_km2"]))
    A("\n### 限速分布\n")
    A(md_table(["限速 km/h", "路段数"], [[fmt(k), v] for k, v in roads["by_limit"]]))

    # ⚠️ 原「货运终端集疏运（T14）」小节**已从本节移走** ——
    # 货运港口 / 货运铁路 / 货运航线的数据**不与客运数据一并分析**，
    # 统一移到 **第 8.2 节 真实税基与建筑等级之后的「工业部分 · 货运终端与产业链」**。
    A("\n> ℹ️ **口径分界**：货运港口 / 货运铁路 / 货运航线的数据**不并入任何客运口径**"
      "（线路效率、走廊重叠、站点覆盖都不用它们）；"
      "它们连同货运终端（货运港口 / 货运铁路终端 / 机场货运）一起，"
      "在**工业部分**做辅助分析（见报告 第 8.2 节 之后的「工业部分 · 货运终端与产业链」小节）。\n")

    A("\n## 4. 公共交通线路效率")
    A("> ⚠️ **口径限制**：本表**只含客运线路**（`Object = RoutePassenger`）。"
      "**货运港口、货运铁路、货运航线的数据不并入本表** —— 它们的 `Passenger` 恒为 0，"
      "混进来会把「人/车」中位数、乘客合计与按方式汇总一起拉偏；"
      "货运类数据只在**工业部分**做辅助分析（见报告「工业部分 · 货运终端与产业链」小节）。\n")
    # ⭐ 线路总里程 = **逐线路长度相加**（唯一口径）
    A("> ⭐ **线路总里程 = 逐线路长度相加 = %s km**（在跑 %s km + 停用 %s km）。"
      "线路里有**掉头 / 绕行 / 环线**，任何另一种「线网统计口径」的合计都会与下面逐线明细对不上 —— "
      "**不一致时以本表逐线路相加为准**。"
      % (fmt(routes.get("total_length_km"), 2), fmt(routes.get("active_length_km"), 2),
         fmt((routes.get("total_length_km") or 0) - (routes.get("active_length_km") or 0), 2)))
    A("> ⭐ **跨方式比效率只看「归一化载客效率」** = 乘客数 ÷（车辆数 × 单车容量）："
      "单车容量按游戏内数值取 **公交 80 / 地铁 1080 / 客运火车 840 人**，"
      "其余方式没有可信容量 → 留「—」，不做归一。"
      "**「人/车」只在同一方式内部比** —— 直接拿它给不同方式排队，会让车大的方式永远垫底。\n")
    _act = [r for r in routes["routes"] if not r.get("suspended")]
    A(md_table(["线路", "方式", "长度 km", "站数", "车辆", "乘客", "单车容量", "归一化载客效率",
                "人/车", "人/km", "平均站距 m", "估算间隔 min"],
               [[r["name"], r["transport_cn"], fmt(r["length_km"], 2), r["stops"], r["vehicles"],
                 r["passengers"], (r["capacity"] if r["capacity"] else "—"),
                 fmt(r["load_efficiency"], 2),
                 fmt(r["pax_per_vehicle"], 1), fmt(r["pax_per_km"], 1),
                 fmt(r["avg_stop_spacing_m"], 0),
                 fmt(r["approx_headway_min_at_20kmh"], 1)]
                for r in sorted(_act, key=lambda r: -(r["load_efficiency"] or 0))]))
    A("\n> 归一化载客效率的含义：**每辆车一天承运了相当于「满载跑几趟」的量** —— 跨方式可比。")
    A("> 估算间隔按运营速度 20 km/h 反推：间隔 ≈ 2 × 单程时间 × 60 / 车辆数（未计停站时间）；"
      "只用于**线路之间横向比较**，绝对值受路况影响。")
    A("> 判断是否该加车请看游戏内 Line 面板的**使用率百分比**（逼近 100% 就加车）。")
    A("> 站距为「—」表示站数 ≤2，该指标无意义；标记「环线一圈」的线路按一圈长度算站距。\n")
    A(md_table(["方式", "线路数", "其中停用", "车辆", "乘客"],
               [[TRANSPORT_CN.get(k, k), v["routes"], v.get("suspended", 0), v["veh"], v["pax"]]
                for k, v in sorted(routes["by_transport"].items(), key=lambda kv: -kv[1]["pax"])]))
    # ---------- ⭐ 停用线路（配车 = 0）：不做客流分析，只做线位分析 ----------
    _susp = routes.get("suspended_routes") or []
    if _susp:
        A("\n### 4.1 停用线路（车辆数 = 0）—— **只做线位分析，不做客流分析**\n")
        A("> 这些线路**一辆车都没配**：它们的低客流是**定义**，不是诊断结论。"
          "**不要**把它们混进上面的效率排序里比较；要看的是**线位还有没有用**。\n")
        A(md_table(["线路", "方式", "长度 km", "站数", "环线", "线位端点（方位）"],
                   [[r["name"], r["transport_cn"], fmt(r["length_km"], 2), r["stops"],
                     "是" if r["is_loop"] else "否",
                     LOC(r["centroid"][0], r["centroid"][1]) if r.get("centroid") else "—"]
                    for r in sorted(_susp, key=lambda r: -r["length_km"])]))
        A("\n> 处方只有两条：**① 恢复配车**（线位仍覆盖空白片区时，按目标间隔给车："
          "`车辆数 ≈ 往返时间 ÷ 目标间隔`）；**② 撤线**（线位已被其它线路覆盖时，"
          "撤销可省下车辆与维护费，把车调给效率高的线）。")
        A("> 判断线位有没有价值，看它是否覆盖**已建成但无公交覆盖**的片区（见第 15 节 的未覆盖热点）。\n")
    _cg = routes.get("cargo_routes") or []
    if _cg:
        A("\n> ℹ️ **另有 %d 条货运线路（%s）未计入上表**（`RouteCargo`：货运铁路 / 货运航线）—— "
          "它们 **`Passenger` 恒为 0**，并入客运口径会拉偏「人/车」中位数与乘客合计；"
          "其车辆与线路数见报告「工业部分 · 货运终端与产业链」小节。"
          % (len(_cg), "、".join(sorted(set(c["transport_cn"] or c["transport"] for c in _cg)))))

    if overlap:
        A("\n## 5. 轨道走廊重叠诊断")
        A("> ⚠️ **口径限制**：只比较**客运轨道线**（`RoutePassenger`）。"
          "货运铁路 / 货运航线**不参与**「是否同一走廊、要不要合并」的判定 —— "
          "货运线的取舍要与工业布点和终端选址一起看。\n")
        A(md_table(["线路 A", "线路 B", "最近距离中位数 m", "A 的 200 m 内占比", "A 的 400 m 内占比", "自动判读"],
                   [[p["a"], p["b"], fmt(p["median_m"], 0),
                     "%.0f%%" % (p["share_within_200m"] * 100),
                     "%.0f%%" % (p["share_within_400m"] * 100),
                     _overlap_verdict(p)] for p in overlap]))
        A("\n> 判读阈值：A 的 400 m 内占比 ≥ 80% → 同一走廊；50–80% → 部分重合；< 50% → 基本独立。")
        A("> 同一走廊的两条线应**合并为一条高频线**（车辆数相加），而不是各跑一半运力。")

    A("\n## 6. 车站腹地（站点 %s m 内的人口 / 岗位）"
      % "/".join(str(r) for r in (400, 600, 800)))
    st = catchment["stations"]
    A("> ⚠️ **本节只统计客运车站**：① 站点来自**客运线路**（`RoutePassenger`），"
      "货运铁路 / 货运航线的站不算；② **地铁总站（`DepotSubway`）、公交总站（`DepotBus`）"
      "这类 depot 只负责提供车辆，不是车站**，不计入站点数与本表。")
    A("> ⚠️ **本节的站点位置是「沿线路几何等分 `Stop` 个点」猜出来的**（不是真实站点坐标）；"
      "**第 15 节 用的是 POI 里的真实站点坐标，两者不一致时以 第 15 节 为准**，本节只作腹地规模参照。"
      "跨线路 %d m 内的站点已合并去重：原始 %d 个 → 去重后 %d 个。"
      % (150, catchment["raw_station_count"], catchment["unique_station_count"]))
    if st:
        st_sorted = sorted(st, key=lambda s: -(s["pop_600"] + s["jobs_600"]))
        A(md_table(["#", "位置（组团）", "地形", "400 m 人口", "400 m 岗位",
                    "600 m 人口", "600 m 岗位", "800 m 人口", "800 m 岗位"],
                   [[i + 1, LOC(s["x"], s["y"]), BUILDABLE(s["x"], s["y"]),
                     s["pop_400"], s["jobs_400"], s["pop_600"], s["jobs_600"],
                     s["pop_800"], s["jobs_800"]]
                    for i, s in enumerate(st_sorted[:20])]))
        A("\n> **位置列读法**：以**人口重心**为原点给出方位与距离（绝对坐标不再出现在正文，"
          "仅在需要核对时用 `--json` 取）。**地形列**：OK=适宜建设区、需整地=缓坡、禁=水体或陡坡。")
        A("\n> 只列出腹地最大的前 20 个站点（按 600 m 内人口+岗位排序）。"
          "腹地小的站点说明**站没放在需求上，或周边尚未开发**。")
        low = [s for s in st if (s["pop_400"] + s["jobs_400"]) < 200]
        if low:
            A("> ⚠️ 有 **%d 个站点**在 400 m 内人口+岗位不足 200 —— 这些站基本是「空站」，"
              "优先考虑迁移站点或加密周边用地，而不是给线路加车。" % len(low))
    else:
        A("_（无可用站点数据）_")

    A("\n## 7. 就业中心（400 m 网格聚合，前 12）")
    A("> 位置用**组团 + 组团内方位**表述（不含绝对坐标）；地形列见 第 8 节 判据。\n")
    A(md_table(["位置（组团）", "地形", "岗位", "居民"],
               [[LOC(c["x"], c["y"]), BUILDABLE(c["x"], c["y"]), c["jobs"], c["pop"]]
                for c in centers]))
    _bad = [c for c in centers if BUILDABLE(c["x"], c["y"]) == "禁"]
    if _bad:
        A("\n> ⚠️ **有 %d 个就业中心落在水体/陡坡上**（%s）—— 这类中心不宜再作为扩展方向，"
          "建议改为在最近的适宜建设区侧向扩展。"
          % (len(_bad), "、".join(LOC(c["x"], c["y"]) for c in _bad)))

    if terrain:
        A("\n## 8. 地形与**可建造性**（水体 / 陡坡 / 适宜建设区）")
        A("> ⚠️⚠️ **本节是最高级别约束**：水体与陡坡**不得**作为规划建议的落点。"
          "下面所有「适宜建设区」的建议都需先过这一节。")
        if maps.get("terrain"):
            FIG(maps["terrain"], "地形与可建造性（地形 + 干道）", key="terrain",
                note="> 📍 **读法**：绿=适宜建设区、黄=缓坡（需整地）、红=陡坡（不建议）、"
                     "蓝=水体（禁止）。**本节任何结论都应能在这张图上找到对应色块。**")
        if terrain.get("utm_offset") and terrain["utm_offset"][0] is not None:
            q = terrain.get("utm_calibration") or {}
            A("> **坐标标定**：GeoTIFF 是 EPSG:32631 绝对坐标，新版 GeoJSON 是归一化坐标 —— "
              "本节用「建筑自带 `Elevation` vs 栅格高程」解出平移量 "
              "（中位误差 **%.2f m** / 平均 %.2f m，有效率 %.0f%%；该误差≈数据本身的 0.1 m 量化精度）。"
              % (q.get("median_m", 0), q.get("mean_m", 0), 100 * q.get("valid", 0)))
        rows = [
            ["高程范围 m（全栅格）", "%.2f – %.2f" % (terrain["min"], terrain["max"])],
            ["城市范围内高差 m", fmt(terrain.get("city_area_relief"), 2)],
            ["栅格", "%s @ %.1f m/px" % (terrain["raster"], terrain["pixel_m"])],
            ["栅格是否覆盖城市全域", "是" if terrain.get("raster_covers_city") else "**否**"],
        ]
        A(md_table(["指标", "数值"], rows))

        bs = terrain.get("buildability")
        if bs:
            A("\n### 8.1 可建造性分级（占**地图内**面积）\n")
            A(md_table(["类别", "判据", "占比", "可否给建设建议"],
                       [["**水体**", "高程 ≤ %.0f m 且坡度 < %.0f°" % (1.0, 1.0),
                         "%.2f%%" % bs["water_pct"], "❌ **禁止**"],
                        ["**陡坡**", "坡度 > %.0f°" % bs["steep_deg"],
                         "%.2f%%" % bs["steep_pct"], "❌ **不建议**"],
                        ["缓坡", "坡度 %.0f–%.0f°" % (bs["slope_deg"], bs["steep_deg"]),
                         "%.2f%%" % bs["slope_pct"], "⚠️ 需整地"],
                        ["**适宜建设区**", "坡度 ≤ %.0f° 且非水体" % bs["slope_deg"],
                         "%.2f%%" % bs["flat_pct"], "✅ 优先"]]))
            bc = terrain.get("buildings_by_class") or {}
            if bc:
                tot = sum(bc.values()) or 1
                A("\n> **自检**：现有 %d 栋建筑中，**%.1f%%** 落在适宜建设区、%.1f%% 在缓坡、"
                  "**%.1f%%** 在陡坡%s —— 城市与地形的匹配是合理的。"
                  % (tot, 100 * bc.get("适宜", 0) / tot, 100 * bc.get("缓坡", 0) / tot,
                     100 * bc.get("陡坡", 0) / tot,
                     ("（那 %d 栋建议核查是否为观景/装饰性建筑）" % bc["陡坡"]) if bc.get("陡坡") else ""))
            A("\n> **给出新建设建议时必须先查这一节**：水体与陡坡一律排除；"
              "缓坡需在建议里写明「需整地/代价更高」。工具：`core/terrain.py` 的 "
              "`classify_point(build, x, y)` / `is_buildable(build, x, y)`。")

    # ---------- 8.2 真实税基（用新版 GeoJSON 的 Level / Profit / Wage） ----------
    if rtb:
        A("\n### 8.2 ⭐ 真实税基与建筑等级（新版 GeoJSON 字段：`%s`）\n"
          % "` / `".join(rtb["fields_available"]))
        if found and not found.get("gate_open"):
            A("> 🚦 **门控提醒（第 2 层）**：第 0.5 节 基础体检**未全部达标**"
              "（拖住：%s）→ **本节的税收优化建议一律降级为「暂缓」**。"
              "先把基础修好，再来动税基结构。下面的数字仍可用于**诊断**，但不要据此提加税/换用途建议。\n"
              % "、".join(found.get("blocking") or ["（见 第 0.5 节）"]))
        A("> **口径升级**：第 11 节 的税基是「人数 × 密度权重」的**代理**；新版导出**直接带公司利润与工资**，"
          "于是官方税收机制可以原样落地 —— **住宅应税 = Σ 劳工应税收入 × 劳工数**，"
          "**商/工/办 = Σ 公司利润**。**本节可用时以本节为准。**\n")
        if rtb.get("wage_is_taxable"):
            A("> ℹ️ **`Wage` 字段口径**：新版导出里它已是**劳工平均应税收入**（起征点 ₡1400 已扣在字段内），"
              "所以本节**不再做 `max(0, 工资−1400)`** —— 否则会把起征点扣两遍、系统性低估税基。\n")
        A(md_table(["指标", "数值"],
                   [["公司利润合计（= 商/工/办税基）", "₡ %s" % fmt(rtb["total_profit"], 0)],
                    ["住宅应税基数（Σ 超 ₡1400 部分 × 岗位）", "₡ %s" % fmt(rtb["residential_tax_base"], 0)],
                    ["**利润 ≤ 0 的公司建筑数**（商/工/办）",
                     "%d 栋%s" % (rtb["loss_buildings"],
                      "　✅ 没有毫无余量的公司" if not rtb["loss_buildings"]
                      else "　⚠️ 有公司处于毫无余量状态，优先查它们")],
                    ["　├ 其中**在营**（有员工）", "%d 栋　← 要处理的是这一档" % rtb.get("loss_staffed", 0)],
                    ["　└ 其中**空置 / 停业**（无员工）", "%d 栋" % rtb.get("loss_vacant", 0)]]))
        A("\n> ⭐ **判亏口径**：%s。" % rtb.get("loss_criterion", "`Profit ≤ 0`"))
        A("> %s" % rtb.get("loss_criterion_note", ""))

        # ---------- ⭐ 商业「毫无余量」店铺 + **潮汐门控** ----------
        _com = rtb.get("commercial_loss") or []
        _com_staffed = [x for x in _com if x.get("staffed")]
        _com_vacant = [x for x in _com if not x.get("staffed")]
        _h = (cur_time or {}).get("hour")
        _peak_lo, _peak_hi = COMMERCIAL_PEAK_HOURS
        A("\n**商业店铺盈亏（判据：利润 ≤ 0）**\n")
        A("> 商业 **%d** 栋里，**利润 ≤ 0 的 %d 栋**：**在营却毫无余量 %d 栋**（有员工）、"
          "**空置 / 停业 %d 栋**（无员工）—— 前者才是要处理的。"
          % (sum(z["buildings"] for z in rtb["by_zone"] if "Commercial" in z["zoning"]),
             len(_com), len(_com_staffed), len(_com_vacant)))
        # ⭐ 潮汐：商业盈亏随营业时段变化 —— 凌晨的「亏损」不作证据
        if _h is None:
            A("> ⏰ **存档时点未知 → 本段结论不可用作证据**：商业盈亏**随营业时段变化**"
              "（凌晨 0–5 时大概率一片不赚钱，日间未必）。**需要白天（%d–%d 时）再导一次**，"
              "才能判「即使在热门时段仍然不赚钱」的店。" % (_peak_lo, _peak_hi))
        elif _peak_lo <= _h <= _peak_hi:
            A("> ⏰ **存档时点 %02d:%02d 落在商业热门时段（%d–%d 时）内** → 本段结论**可用**："
              "下面这批店是**即使在热门时段也不赚钱**的，应当优先处置。"
              % (_h, (cur_time or {}).get("minute") or 0, _peak_lo, _peak_hi))
        else:
            A("> ⛔ **存档时点 %02d:%02d 不在商业热门时段（%d–%d 时）内** → "
              "**本段不得用来下「商业在亏」的结论**（凌晨的亏损是时段现象，不是经营问题）。"
              "清单只作定位用；**结论降级为「需白天（%d–%d 时）复导一次再判」**。"
              % (_h, (cur_time or {}).get("minute") or 0, _peak_lo, _peak_hi, _peak_lo, _peak_hi))
        if _com_staffed:
            _top = _com_staffed[:12]
            A(md_table(["店铺（品牌 / 品类）", "等级", "员工", "利润 ₡", "所在区 · 街"],
                       [["%s / %s" % (x.get("brand") or "—", x.get("product") or "—"),
                         "L%s" % x.get("level") if x.get("level") is not None else "—",
                         x.get("employee"), fmt(x.get("profit"), 0),
                         "%s · %s" % (x.get("district") or "—", x.get("street") or "—")]
                        for x in _top]))
            A("> 处方：**分流**（在增量新区开新网点），**不是「救」或「拆」** —— "
              "拆店会同时损失岗位与税基；真正的病根通常是**末端配送距离太长 / 同品类过密 / 上游原料不在本地**。")
        else:
            A("> ✅ 当前口径下没有「在营却毫无余量」的商业店铺。")

        A("\n**建筑等级分布（全城）**：%s\n"
          % "　".join("L%d: **%d**" % (k, v) for k, v in sorted(rtb["levels_all"].items()) if k >= 0))
        A("> ℹ️ **等级分布正是「税率甜蜜点」实验要的核心观测值**——"
          "**以前只能用游戏内 `Building Level` 视图目视，现在可以直接算出来了。**"
          "做税率实验时用 `--prev` 对比这个分布的变化即可。\n")
        A(md_table(["分区", "栋数", "利润合计", "每栋利润", "平均工资", "岗位(Employee)", "居住劳动力(Labor)", "各等级栋数"],
                   [[z["zoning"], z["buildings"], fmt(z["profit"], 0),
                     fmt(z["profit_per_building"], 0), fmt(z["avg_wage"], 0),
                     fmt(z["employees"], 0), fmt(z["labor"], 0),
                     " ".join("L%d:%d" % (k, v) for k, v in sorted(z["levels"].items()) if k >= 0)]
                    for z in rtb["by_zone"]]))
        A("\n> **两列人力口径不同（别混用）**：`Employee` = 该建筑提供的**岗位数**"
          "（商/工/办，全域合计 %s）；`Labor` = 住在这里面、**在外工作的居民数**"
          "（住宅，全域合计 %s）。住宅应税基数用的是 `Labor`。"
          % (fmt(sum(z["employees"] for z in rtb["by_zone"]), 0),
             fmt(sum(z["labor"] for z in rtb["by_zone"]), 0)))
        _z = [z for z in rtb["by_zone"] if z["profit"] > 0]
        if _z:
            A("\n> **税基效率**：每栋利润最高的是 **%s**（₡ %s/栋），最低的是 **%s**（₡ %s/栋）—— "
              "**相差 %.1f 倍**。公司利润就是商/工/办的税基，所以「每栋利润」越高的用途，"
              "同样的建筑数量能贡献越多税收。"
              % (_z[0]["zoning"], fmt(_z[0]["profit_per_building"], 0),
                 _z[-1]["zoning"], fmt(_z[-1]["profit_per_building"], 0),
                 (_z[0]["profit_per_building"] / max(1.0, _z[-1]["profit_per_building"]))))
        A("\n> ⚠️ **口径限制**：这是**按官方机制算出的相对量，不是城市实际税收金额** —— "
          "实际税收还取决于**税率**与建筑等级，而 **Carto 不导出税率**。"
          "要验证税率影响，做一次受控实验（只动税率、跑 1–2 个游戏月），用这里的等级分布做前后对比。")

    # ---------- 工业部分：货运港口 / 货运铁路 / 货运航线（**辅助分析**，不与客运数据混算） ----------
    # ⚠️ 位置说明：货运数据的**归属是工业部分** —— 本站位紧跟在
    # **第 8.2 节 真实税基与建筑等级**（= 公司利润 = 商/工/办税基）之后，
    # 与客运章节（第 4 节/第 5 节/第 6 节/第 15 节）**完全分开**，且**不参与 第 0.5 节 基础体检的任何一项**。
    if freight or routes.get("cargo_routes"):
        A("\n### 工业部分 · 货运终端与产业链（辅助分析 —— **口径独立于客运**）\n")
        A("> ⚠️⚠️ **范围限制**：**货运港口、货运铁路、货运航线不并入客运数据一起分析**。"
          "本小节的数字来自 `RouteCargo`（货运线路）与货运终端 POI"
          "（`StopCargoTrain` / `StopCargoShip` / 货运港口等），"
          "**它们的 `Passenger` 恒为 0，进客运口径只会把中位数与总量拉偏**。")
        A("> 用途只有一个：**辅助判断工业/商业的运输条件**（公司利润 = 商/工/办的税基）。"
          "判据与处方："
          "① 货运终端**不开货运线也能当配送中心**；② 终端必然产生大量卡车 → 先保道路连接；"
          "③ 出口走铁路/港口比卡车拖到外部连接更便宜更快；④ **缩短产业上下游的实际路网距离 = 直接涨税**。\n")
        if routes.get("cargo_routes"):
            A(md_table(["货运线路", "方式", "车辆", "终端/站数", "长度 km"],
                       [[c["name"], c["transport_cn"], c["vehicles"], c["stops"],
                         fmt(c["length_km"], 2)] for c in routes["cargo_routes"]]))
        else:
            A("_（本城没有货运线路。⚠️ 这不等于货运条件差 —— 官方明确："
              "**货运终端即使不开货运线也能当配送中心**，只要建了终端就能给周边公司加取货点。）_")
        if freight and freight["rows"]:
            A("\n**货运终端集疏运检查（T14）** —— 官方 `Transportation` 页：货运终端**必然产生大量卡车流**，"
              "「优先保证终端的道路连接」是硬要求。判据：终端 %.0f m 内有没有**高等级道路**"
              "（`Highway` / `Medium` / `Large`），只有支路 → 大概率堵。"
              "⚠️ 同一座设施的多条 POI 记录已按距离归并。\n" % freight["radius"])
            A(md_table(["终端", "类型", "最近高等级路 m", "判读"],
                       [[x["name"], x["category"],
                         fmt(x["nearest_major_m"], 0) if x["nearest_major_m"] is not None else "**无**",
                         x["verdict"]] for x in freight["rows"]]))
            bad = [x for x in freight["rows"] if x["nearest_major_m"] is None]
            if bad:
                A("\n> ⚠️ **有 %d 个货运终端 1 km 内没有高等级道路** —— 官方说这种情况必须优先整改，"
                  "否则货卡会挤爆周边小路。**动作**：加一条主干道直连，或把终端迁到主干道旁。"
                  % len(bad))
            else:
                A("\n> ✅ 所有货运终端 1 km 内都有高等级道路接入，集疏运条件合格。"
                  "（本检查**只判几何邻近，不含容量** —— 终端吞吐量超了照样会堵。）")
        A("\n> ⛔ **不得把这些数字写进客运结论**：本节的车数/站数**不是**客运运力，"
          "站数**不是**客运站点，也不参与 第 4 节 线路效率、第 5 节 走廊重叠、第 6 节/第 15 节 站点覆盖与 第 0.5 节 基础体检。")
        A("> ⛔ 反过来也成立：**不得用客运数据（乘客数 / 配车数 / 站距）为货运与工业布局辩护或否定** ——"
          "货运要看的是上表的**终端类型、线路配车、运输方式与终端到路网的距离**。")

    # ---------- 8.3 高程的规划用途 ----------
    if elev_plan:
        ep = elev_plan
        A("\n### 8.3 高程的规划用途（高差 / 低洼 / 制高 / 平整代价）\n")
        A("> 高程不只是背景数据 —— **它直接决定土方量、排水方向与地标选址**。"
          "下表全部来自 `Elevation` 栅格（%.1f m/px），位置用方位词表述。\n" % ep["pixel_m"])
        A(md_table(["指标", "数值"],
                   [["城市建筑所在高程范围", "%.1f – %.1f m" % (ep["city_elev_min"], ep["city_elev_max"])],
                    ["**城市高差**", "**%.1f m**" % ep["city_relief"]],
                    ["城市主要台地（10 m 带）", "**%.0f m 一带**（%d 栋）"
                     % (ep["main_band"], ep["bands"].get(ep["main_band"], 0))],
                    ["主要台地栋数占比", "%.0f%%（%d / %d 栋）"
                     % (100.0 * ep["bands"].get(ep["main_band"], 0) / max(1, ep["n_buildings"]),
                        ep["bands"].get(ep["main_band"], 0), ep["n_buildings"])],
                    ["有建筑的 %d m 网格数" % ep["cell_m"], "%d 个（共 %d 栋）"
                     % (ep["n_cells"], ep["n_buildings"])]]))
        A("\n**局部最低处（排水/泵站应设在这些方向）**\n")
        A(md_table(["位置（组团）", "地面高程 m", "居民", "岗位"],
                   [[LOC(c["x"], c["y"]), fmt(c["elev"], 1), fmt(c["res"], 0), fmt(c["jobs"], 0)]
                    for c in ep["lowest"][:5]]))
        A("\n**局部最高处（地标 / 公园 / 观景选址）**\n")
        A(md_table(["位置（组团）", "地面高程 m", "居民", "岗位", "地形"],
                   [[LOC(c["x"], c["y"]), fmt(c["elev"], 1), fmt(c["res"], 0), fmt(c["jobs"], 0),
                     BUILDABLE(c["x"], c["y"])] for c in ep["highest"][:5]]))
        st = ep.get("earthwork_cells") or []
        if st and st[0]["earthwork"] > 0:
            A("\n**平整土方量最大处（%d m 网格；以格内中位高程为设计标高，挖填取大者）**\n" % ep["cell_m"])
            A(md_table(["位置（组团）", "土方量(相对)", "网格内高差 m", "平均高程 m", "建筑数", "地形"],
                       [[LOC(c["x"], c["y"]), fmt(c["earthwork"], 0), fmt(c["relief"], 2),
                         fmt(c["elev"], 1), c["n"], BUILDABLE(c["x"], c["y"])]
                        for c in st[:5]]))
            A("\n> **动作**：这些网格若要新建，**先整地或做挡土**（土方量随高差上升，是隐性成本）；"
              "能避开就避开 —— 与 第 8.1 节「优先适宜建设区」是同一条原则。"
              "**注意土方量是相对量**（栅格米×格累积），只用于**网格之间排序**，不是真实 m³。")
        else:
            A("\n> ✅ 各 %d m 网格内部起伏很小 —— **城市建在平整台地上，不需要额外土方**，"
              "这是本地形最有利的一点。" % ep["cell_m"])
        A("\n> **排水方向**：污水/雨水应顺着高程往**最低处**汇集（上表第一张），"
          "泵站与污水处理厂设在低洼侧比设在高处省能耗；**不要把排污设施放在制高点**。")
        A("> **制高点用法**：上表第二张的空旷高处（居民 0、岗位 0）适合做**地标 / 公园 / 观景台** —— "
          "既提升幸福度（官方幸福度因子含休闲与景观），又不与居住用地争地。")

    # ---------- 9. 用地效率（本轮核心） ----------
    A("\n## 9. 用地效率（每单位土地装下多少税基）")
    A("> **口径**：按 %d m × %d m = %d m² 的建成栅格计（Carto 分区图斑即 8 m 栅格单元）。"
      "「每公顷产出」= 该分区的岗位/居民 ÷ 建成栅格公顷数，**是分区之间的横向比较指标**，"
      "不等于现实意义的就业密度。" % (eff["tile_m"], eff["tile_m"], eff["tile_m"] ** 2))
    A("> ⚠️ 游戏内**没有**税收字段，Carto 也不含税率/税基。本节给的是**税基代理量**（岗位、居民），"
      "真实税收必须由玩家在游戏内读；官方没有给过「最优税率」，只给了「低税率升级快 / 高税率钱多」这一条权衡。\n")
    A(md_table(["分区", "建成栅格 ha", "建筑数", "岗位", "居民", "岗位/公顷", "居民/公顷", "岗位/栋"],
               [[z["zoning_cn"], fmt(z["built_ha"], 2), z["buildings"], z["jobs"], z["residents"],
                 fmt(z["jobs_per_ha"], 1), fmt(z["residents_per_ha"], 1),
                 fmt(z["jobs_per_building"], 1)]
                for z in eff["zones"]]))
    if eff["land_per_job"]:
        A("\n### 每个岗位占多少地（越小越省地 → 同样的地能装更多税基）\n")
        A(md_table(["分区", "每个岗位占地 m²", "岗位数", "建成 ha"],
                   [[x["zoning_cn"], fmt(x["m2_per_job"], 1), x["jobs"], fmt(x["built_ha"], 2)]
                    for x in eff["land_per_job"]]))
        best, worst = eff["land_per_job"][0], eff["land_per_job"][-1]
        if worst["m2_per_job"] > 2 * best["m2_per_job"]:
            A("\n> **结构性提示**：%s 每个岗位要 %.0f m²，而 %s 只要 %.0f m² —— "
              "**相差 %.1f 倍**。在土地有限、目标是最大化税收时，"
              "把增量土地优先给每公顷岗位更多的用途，比扩大占地大的用途更划算。"
              % (worst["zoning_cn"], worst["m2_per_job"], best["zoning_cn"],
                 best["m2_per_job"], worst["m2_per_job"] / max(1e-9, best["m2_per_job"])))
    if eff["top_job_density_cells"]:
        A("\n### 岗位最密集的地块（400 m 网格，前 10）—— 这些是「税基最厚」的地方\n")
        A(md_table(["位置（组团）", "地形", "岗位", "居民", "建成 ha", "岗位/公顷"],
                   [[LOC(c["x"], c["y"]), BUILDABLE(c["x"], c["y"]), fmt(c["jobs"]),
                     fmt(c["res"]), fmt(c["built_ha"], 2), fmt(c["jobs_per_ha"], 1)]
                    for c in eff["top_job_density_cells"]]))
    if eff["low_job_density_cells"]:
        A("\n### 岗位最稀疏但已有开发的地块（前 10）—— 内填/升级的优先候选\n")
        A(md_table(["位置（组团）", "地形", "岗位", "居民", "建成 ha", "岗位/公顷"],
                   [[LOC(c["x"], c["y"]), BUILDABLE(c["x"], c["y"]), fmt(c["jobs"]), fmt(c["res"]),
                     fmt(c["built_ha"], 2), fmt(c["jobs_per_ha"], 1)]
                    for c in eff["low_job_density_cells"]]))

    # ---------- 风险代理 ----------
    A("\n## 10. 风险代理指标（幸福度与税收的先行信号）")
    A("> Carto **没有**污染/噪声/幸福度/税率字段，所以这里只用**空间结构**做代理。"
      "代理指标只能用于排序与定位问题，**不能当作游戏内数值引用**。\n")
    rrows = []
    if risk.get("district_job_housing"):
        v = risk["district_job_housing"]
        rrows.append(["区级职住比离散度", "%.2f（均值 %.2f）" % (risk["district_spread"], risk["district_mean"]),
                      "越大 = 跨区通勤越重 → 通勤时间升、幸福度降、干道压力升"])
        for x in sorted(v, key=lambda t: t["ratio"]):
            rrows.append(["  · " + str(x["name"]),
                          "职住比 %.2f（%s 人 / %s 岗）" % (x["ratio"], fmt(x["residents"]), fmt(x["jobs"])),
                          "远低于均值说明是「睡城」，居民被迫外出就业" if x["ratio"] < risk["district_mean"] * 0.6 else ""])
    rm = risk.get("road_mix") or {}
    if rm:
        rrows.append(["支路/主干长度比", fmt(risk.get("local_to_arterial"), 2),
                      "偏低 = 只有主干道、缺支路网 → 过境车挤社区路。现实标准支路总长远多于干路"])
    if risk.get("density_names"):
        rrows.append(["低密度建筑占比", "%.0f%%（低密度 %d 栋 / 共 %d 栋）"
                      % (risk["low_density_share"] * 100,
                         sum(v for k, v in risk["density_names"].items() if "低密度" in k),
                         sum(risk["density_names"].values())),
                      "占比高 = 单位土地税基薄，服务与道路成本却被摊到更大的面积上"])
    if risk.get("station_count"):
        rrows.append(["空站占比", "%d/%d（%.0f%%）" % (risk["weak_stations"], risk["station_count"],
                                                   risk["weak_station_share"] * 100),
                      "400 m 内人口+岗位 < 200 的站点：站没放在需求上，或周边没开发"])
    A(md_table(["代理指标", "实测值", "为什么与税收/幸福度有关"], rrows) if rrows
      else "_（数据不足，未生成代理指标）_")

    # ---------- 税基潜力 ----------
    A("\n## 11. 税基潜力（按官方税收机制的代理指数）")
    if found and not found.get("gate_open"):
        A("> 🚦 **门控提醒（第 2 层）**：第 0.5 节 基础体检**未全部达标**（拖住：%s）"
          "→ **本节结论暂不用于给出加税/换用途建议**，先修基础。"
          "本表仍可用于**理解税基结构**。\n"
          % "、".join(found.get("blocking") or ["（见 第 0.5 节）"]))
    A("> ⚠️ **这是无量纲相对指数，不是金额。** 官方税基是「住宅工资超 ₡1400/月的部分」与「公司利润」，"
      "Carto 两者都没有 → 这里用 `住宅 = 人数 × 密度权重`（低密度 1.0 / 中 0.8 / 高 0.55 / 低租金 0.35）"
      "与 `岗位 = 岗位数 × 分区权重`（办公 1.6 / 商业 1.35 / 工业 1.0）做代理。")
    A("> **只能用于同城内部排序**（哪块地更值钱），不要跨城比、不要说成 ₡。机制见第 8.2 节 的税基说明。")
    A("> ⚠️⚠️ **必读：本表的「每 m² 指数」是「建筑占地面积」口径，不是「用地面积」口径** ——")
    A("> 它回答「同一栋楼的哪种用途更值钱」，**不能回答「同一片地该给哪个用途」**。")
    A("> 要回答后者，必须用 **第 9 节 的「岗位/公顷」**（那才是按已划区图斑算的用地口径）。")
    A("> **两个口径的结论可能相反**，所以：")
    A("> **任何「把某用途改成另一用途」的建议，必须同时给出 第 9 节 的用地口径数字，否则不要提。**\n")
    A(md_table(["分区", "税基指数", "建筑数", "居民", "岗位", "每 m² 建筑指数（建筑口径）", "每栋指数"],
               [[r["key"], fmt(r["tax_index"], 0), r["buildings"], fmt(r["residents"]),
                 fmt(r["jobs"]), fmt(r["tax_per_m2"], 3), fmt(r["tax_per_building"], 1)]
                for r in tax["by_zone"]]))
    # 把 第 9 节 的用地口径并列出来，避免"只拿税基指数就下用地结论"这个高频误用
    if eff and eff.get("zones"):
        A("\n**并列：第 9 节 的用地口径（每公顷，按已划区图斑）** —— 与上表口径不同，做用地决策看这张：\n")
        A(md_table(["分区", "岗位/公顷（用地口径）", "税基指数/公顷（用地口径）"],
                   [[z["zoning_cn"], fmt(z["jobs_per_ha"], 1),
                     fmt((z["jobs_per_ha"] or 0) *
                         (ZONE_JOB_WEIGHT.get(z["zoning"], 1.0) if z["jobs"] else
                          DENSITY_TAX_WEIGHT.get("中密度", 0.8)), 0)]
                    for z in eff["zones"]]))
        A("\n> **读法**：如果两个用途的「每公顷」量级接近（常见），**就不要建议互换用途** —— "
          "换用途会损失原有岗位、且收益不明确。**优先做「内填」**（第 12 节：把开发强度低的那类补到与高的一类同级），"
          "因为内填**不减少任何现存岗位**。")
    if tax["by_density"]:
        A("\n### 按密度层级（官方：低密度人均纳税更多、高密度人均少）\n")
        A(md_table(["密度层级", "税基指数", "建筑数", "居民", "每 m² 建筑指数", "每居民指数"],
                   [[r["key"], fmt(r["tax_index"], 0), r["buildings"], fmt(r["residents"]),
                     fmt(r["tax_per_m2"], 3), fmt(r["tax_per_resident"], 3)]
                    for r in tax["by_density"]]))
    if tax["by_combo"]:
        A("\n### 住宅 vs 岗位：同样一块地哪个更值钱（密度 × 分区）\n")
        A(md_table(["类型", "税基指数", "建筑数", "居民", "岗位", "每 m² 建筑指数"],
                   [[r["key"], fmt(r["tax_index"], 0), r["buildings"], fmt(r["residents"]),
                     fmt(r["jobs"]), fmt(r["tax_per_m2"], 3)] for r in tax["by_combo"]]))
        res_rows = [r for r in tax["by_combo"] if r["key"].startswith("住宅 ·")
                    and r["tax_per_m2"] is not None]
        job_rows = [r for r in tax["by_combo"] if not r["key"].startswith("住宅 ·")
                    and r["tax_per_m2"] is not None]
        if res_rows and job_rows:
            best_res = max(res_rows, key=lambda r: r["tax_per_m2"])
            best_job = max(job_rows, key=lambda r: r["tax_per_m2"])
            A("\n> **对照**：住宅里最划算的是「%s」（%.3f 指数/m² 建筑），"
              "岗位用地里最划算的是「%s」（%.3f）。"
              "在土地受限时，增量应优先给指数更高的一侧。"
              % (best_res["key"], best_res["tax_per_m2"], best_job["key"], best_job["tax_per_m2"]))
    A("\n- 全城税基指数合计：**%s**（只用于与自身历史比）" % fmt(tax["total_tax_index"], 0))
    if tax["labor_self_sufficiency"]:
        ss = tax["labor_self_sufficiency"]
        A("- **本地劳动力自给率**（人口 ÷ 岗位）= **%.2f**" % ss)
        if ss < 1.0:
            A("  - ⚠️ 小于 1 → 岗位多于本地人口，必然依赖**城外通勤者，而他们完全不缴税**"
              "（住城内、去城外上班的居民也不缴税）。这类岗位对税收的贡献远低于账面。")
        elif ss > 2.0:
            A("  - ⚠️ 大于 2 → 岗位远少于人口，居民被迫外出就业（同样不缴税），"
              "且通勤压力大 → 幸福度与地价都受损。")
    if tax["unknown_density_buildings"]:
        A("- 有 %d 栋住宅从名称里判不出密度层级，已按中密度（0.8）计入。" % tax["unknown_density_buildings"])
    if tax["top_buildings"]:
        A("\n### 单位占地税基最高的建筑（前 15）—— 这就是「值得复制」的样本\n")
        A(md_table(["建筑名", "分区", "密度", "居民", "岗位", "占地 m²", "指数/m²"],
                   [[r["name"], ZONE_CN.get(r["zoning"], r["zoning"]), r["density"] or "—",
                     r["res"], r["emp"], fmt(r["area_m2"], 0), fmt(r["tax_per_m2"], 3)]
                    for r in tax["top_buildings"]]))

    # ---------- 开发强度 ----------
    if underdev and underdev["by_zone"]:
        A("\n## 12. 开发强度（划了区的用途里，哪些没盖起来）")
        A("> ⚠️ **只在同城内部、按分区类型横向比较，不要看绝对数。** %s\n" % underdev["note"])
        A("> 参考量级：全城 %s 个分区图斑对应 %s 栋建筑（平均每栋 %.1f 个图斑），"
          "说明图斑里含大量非建筑细节 —— 所以「覆盖率」整体偏低是正常的。\n"
          % (fmt(underdev["total_zone_tiles"]), fmt(underdev["total_buildings"]),
             underdev["total_zone_tiles"] / max(1, underdev["total_buildings"])))
        A(md_table(["分区", "图斑数", "已划区 m²", "建筑占地 m²", "建筑数", "占地覆盖率", "每栋摊到的划区 m²"],
                   [[r["zoning_cn"], fmt(r["zone_tiles"], 0), fmt(r["zone_m2"], 0),
                     fmt(r["built_m2"], 0), r["buildings"],
                     "%.0f%%" % (r["coverage"] * 100) if r["coverage"] is not None else "—",
                     fmt(r["m2_per_building"], 0)] for r in underdev["by_zone"]]))
        low = underdev["by_zone"][-1] if underdev["by_zone"] else None
        if low and low["coverage"] is not None:
            A("\n> **读法**：覆盖率最低的是「%s」（%.0f%%）。"
              "它意味着同样面积的划区只盖出了很少的建筑占地 —— 在土地受限时，"
              "这类用途要么提高强度（升级/加密），要么把地让给单位占地税基更高的用途。"
              % (low["zoning_cn"], low["coverage"] * 100))

    # ---------- 噪音暴露 ----------
    if noise and noise["top"]:
        A("\n## 13. 住宅噪音暴露最高的建筑（幸福度风险）")
        A("> %s\n" % noise["note"])
        A("> 官方幸福度因子含**噪音污染**；**隧道内的道路噪音被完全抑制**（权重 0）。\n")
        A(md_table(["建筑名", "居民", "暴露分", "位置（组团）"],
                   [[r["name"], r["residents"], fmt(r["score"], 1), LOC(r["x"], r["y"])]
                    for r in noise["top"]]))
        tot = sum(r["residents"] for r in noise["top"])
        A("\n> 这 15 栋合计 %s 位居民。若他们抱怨噪音，优先考虑**给这段路加隔音/改隧道、"
          "或在路与住宅之间留缓冲带**，而不是把整片住宅拆掉 —— 隧道内噪音被完全抑制，是最有效的单点手段。"
          % fmt(tot))
        # 按 400 m 网格找出"受影响居民最多"的片区，比逐栋更有可操作性
        agg = defaultdict(lambda: {"res": 0, "score": 0.0, "n": 0})
        for r in noise["all"]:
            k = (int(r["x"] // 400.0) * 400, int(r["y"] // 400.0) * 400)
            agg[k]["res"] += r["residents"]
            agg[k]["score"] += r["score"] * r["residents"]
            agg[k]["n"] += 1
        spots = sorted(({"x": k[0] + 200, "y": k[1] + 200, "res": v["res"], "n": v["n"],
                         "score": v["score"] / v["res"] if v["res"] else 0}
                        for k, v in agg.items()), key=lambda s: -s["score"])[:10]
        A("\n### 噪音最集中的片区（400 m 网格，按人均暴露分排序）\n")
        A(md_table(["位置（组团）", "受影响居民", "建筑数", "人均暴露分"],
                   [[LOC(s["x"], s["y"]), fmt(s["res"]), s["n"], fmt(s["score"], 1)]
                    for s in spots]))
        A("\n> **行动**：这些网格是「降噪收益最大」的地方 —— 隔音屏障、限速下调、"
          "把这段路改隧道，或把临街住宅逐步置换为商业/办公（它们对噪音不敏感）。")

    # ---------- 多期趋势 ----------
    if trend:
        A("\n## 14. 多期趋势（这才是判断「改动是否有效」的依据）")
        A("> 单期快照只能看现状；**只有多期才能看出方向**。下表按 `--trend` 给出的顺序排列。\n")
        snaps = trend["snapshots"]
        A(md_table(["期（目录名）", "人口", "岗位", "职住比", "分区图斑", "路网 km",
                    "税基指数", "劳动力自给率", "线路乘客合计"],
                   [[s["dir"], fmt(s["population"]), fmt(s["jobs"]), fmt(s["job_housing"], 2),
                     fmt(s["zoning_total"]), fmt(s["road_km"], 1), fmt(s["tax_index"], 0),
                     fmt(s["labor_self_sufficiency"], 2), fmt(s["route_pax_total"])]
                    for s in snaps]))
        # 分区结构变化
        keys = set()
        for s in snaps:
            keys |= set(s["zoning_tiles"])
        if keys:
            A("\n### 分区图斑变化（用地结构在往哪个方向走）\n")
            A(md_table(["分区"] + [s["dir"] for s in snaps],
                       [[ZONE_CN.get(k, k)] + [fmt(s["zoning_tiles"].get(k, 0)) for s in snaps]
                        for k in sorted(keys, key=lambda k: -max(s["zoning_tiles"].get(k, 0) for s in snaps))]))
            first, last = snaps[0], snaps[-1]
            tot_f = sum(first["zoning_tiles"].values()) or 1
            tot_l = sum(last["zoning_tiles"].values()) or 1
            shifts = []
            for k in keys:
                sf = first["zoning_tiles"].get(k, 0) / tot_f
                sl = last["zoning_tiles"].get(k, 0) / tot_l
                if abs(sl - sf) > 0.003:
                    shifts.append((ZONE_CN.get(k, k), sf, sl, sl - sf))
            if shifts:
                A("\n**结构位移**（首期 → 末期占比）：" +
                  "；".join("%s %.1f%%→%.1f%%（%+.1f pt）" % (n, a * 100, b * 100, d * 100)
                           for n, a, b, d in sorted(shifts, key=lambda t: -abs(t[3]))))
        # 逐线乘客趋势（⚠️ 只列**客运**线路；货运线路的 Passenger 恒为 0，不参与乘客趋势）
        rkeys = set()
        for s in snaps:
            rkeys |= set(k for k, v in s["routes"].items()
                         if (v.get("object") or PASSENGER_ROUTE_OBJECT) != CARGO_ROUTE_OBJECT)
        if rkeys:
            A("\n### 逐线乘客趋势（**只含客运线路**）\n")
            A("> ⚠️ **口径限制**：货运铁路 / 货运航线（`RouteCargo`）**不进本表** —— "
              "它们的 `Passenger` 恒为 0，只会稀释判断。\n")
            rows = []
            for k in sorted(rkeys):
                row = [k]
                for s in snaps:
                    r = s["routes"].get(k)
                    row.append("—" if not r else "%s(%s车)" % (fmt(r["pax"]), fmt(r["veh"])))
                rows.append(row)
            A(md_table(["线路"] + [s["dir"] for s in snaps], rows))
            A("\n> 判读：**乘客连续下降的线路要立刻查原因**（间隔变长？走廊被抢？站点被迁？）；"
              "**新增线路若乘客长期远低于同城中位数，说明需求判断错了**。")

    # ---------- 真实站点覆盖 ----------
    if cov:
        A("\n## 15. 真实站点覆盖率（用 POI 里的真实站点坐标算）")
        A("> ⚠️ **口径限制（与 第 6 节 同一套白名单）**：本节的站点**只取客运站点**"
          "（`StopBus` / `StopSubway` / `StopPassengerTrain`）。"
          "**地铁总站 / 公交总站 / 火车总站是 depot（车辆段），只提供车辆、不是车站** → 不计入站点数；"
          "**货运铁路站（`StopCargoTrain`）与货运码头（`StopCargoShip`）也不计入客运覆盖**"
          "（它们归工业部分的辅助分析）。")
        A("> **口径修正**：第 6 节 的站点位置是「沿线路几何等分 `Stop` 个点」**猜出来的**；"
          "本节改用 `POI_Location` 里的**真实站点对象**（`StopBus` / `StopSubway` / `StopPassengerTrain`），"
          "实测本城有 **%d** 个真实站点。**两者不一致时以本节为准。**" % cov["stop_count"])
        A("> ⚠️ 半径用的是**现实标准**，**不是**游戏的 `Service range`"
          "（那个单位是米，但它是「需求未饱和时的最大半径」，密度上升会把它压缩）。\n")
        A("| 半径 | 人口覆盖 | 岗位覆盖 |")
        A("|---|---|---|")
        for R, v in cov["radii"].items():
            A("| %d m | %.1f%% | **%.1f%%** |" % (R, v["pop_share"] * 100, v["jobs_share"] * 100))
        A("\n**站点构成**：" + "、".join("%s %d" % (k.replace("Stop", ""), v)
                                       for k, v in sorted(cov["by_kind"].items(), key=lambda kv: -kv[1])))
        if cov["uncovered"]:
            A("\n### 离站点最远的住宅（未覆盖热点，前 10）\n")
            A(md_table(["建筑", "居民", "到最近站点 m", "位置（组团）", "地形"],
                       [[u["name"], u["residents"], fmt(u["dist"], 0), LOC(u["x"], u["y"]),
                         BUILDABLE(u["x"], u["y"])]
                        for u in cov["uncovered"][:10]]))
        # 关键判读：覆盖率 vs 客流 —— 覆盖率已高但客流差，说明问题在服务质量
        r500 = cov["radii"].get(500)
        if r500 and r500["pop_share"] >= 0.95:
            A("\n> ✅ **关键判读**：500 m 人口覆盖已达 **%.1f%%** —— **覆盖不是瓶颈**。"
              "此时再「加站」几乎没有收益；要把客流做上去，只能动**服务质量**"
              "（看 第 4 节 的人·车、第 16 节 的加车/专用道归因）。" % (r500["pop_share"] * 100))
        if r500 and r500["jobs_share"] < r500["pop_share"] - 0.05:
            A("> ⚠️ **但岗位覆盖（%.1f%%）明显低于人口覆盖（%.1f%%）** —— 就业中心周边的公交可达性不足。"
              "把线路/站点往**岗位密集区**（用 第 9 节 的岗位密度地块表定位）延伸，"
              "比继续加密住宅区更值钱 —— 因为**公司利润才是商/工/办的税基**。"
              % (r500["jobs_share"] * 100, r500["pop_share"] * 100))

    # ---------- 服务设施双口径覆盖 ----------
    if svc and svc["rows"]:
        A("\n## 16. 服务设施双口径覆盖（官方 Service range 上界 vs 现实步行半径下界）")
        A("> **为什么要双口径**：官方 `Service range` **单位是米**（C20 已结案），"
          "但它是**需求未饱和时的最大半径** —— 区内密度上升会把它压缩（C23）；"
          "而现实标准半径不受游戏机制影响。"
          "**两者一起看，才能判断是「设施太少」还是「密度把它压扁了」。**\n")
        A(md_table(["设施类别", "数量", "官方 range m", "自圈步行半径 m",
                    "官方半径下人口覆盖", "步行半径下人口覆盖", "压缩比"],
                   [[r["category"], r["facilities"], r["official_range_m"], r["self_range_m"],
                     "%.1f%%" % (r["pop_share_official"] * 100),
                     "**%.1f%%**" % (r["pop_share_self"] * 100),
                     fmt(r["shrink_ratio"], 2)]
                    for r in svc["rows"]]))
        A("\n> **压缩比 = 步行半径覆盖 ÷ 官方半径覆盖**。比值越低，说明该服务**越依赖它的大半径**，"
          "在密集区越容易露洞。")
        weak = [r for r in svc["rows"] if r["pop_share_self"] < 0.8]
        if weak:
            A("> ⚠️ **需要补的**：" + "、".join("%s（步行半径下只覆盖 %.0f%%）"
                                            % (r["category"], r["pop_share_self"] * 100)
                                            for r in sorted(weak, key=lambda r: r["pop_share_self"])))
            A("> **动作**：优先用**服务预算滑块**（官方明文会改变覆盖半径）试一下，"
              "确认不是预算不足造成的覆盖缩水，再决定建新设施 —— "
              "**先调预算、后盖楼，是最便宜的顺序**。")
        A("\n> ⚠️ 口径限制：POI 的 `Category` 与官方建筑名**不是一一对应**（例如 `Health` 可能是小诊所也可能是医院，"
          "官方 range 分别是 2500 / 5000 / 7500）→ 本表用**最低档**保守估计，**未映射的类别不参与判定**。")

    # ---------- 公交服务质量归因 ----------
    if tsq and tsq["routes"]:
        A("\n## 17. 公交服务质量归因（该加车，还是该上专用道）")
        if maps.get("transit_advice"):
            FIG(maps["transit_advice"], "组团划分与公交/轨道可达性", key="transit_advice",
                note="> 📍 **读法**：绿=有轨道服务、蓝=仅地面公交、**红=无任何直达线路**。"
                     "下面给某条线加车或改线之前，先在这张图上看它服务的是哪个组团、"
                     "该组团是不是红的（缺口）。")
        A("> 依据：**Ceder《公共交通规划与运营》式 12.1** —— `E(候车) = E(H)/2 × (1 + C²)`，"
          "`C²` 是**发车间隔的变异系数平方**（车来得规不规律）。`C²=0` 时候车 = 间隔的一半，"
          "`C²=1` 时候车 = 整个间隔 → **只把车开规律，候车就能砍半，且不多花一辆车。**")
        A("> ⚠️ Carto **没有逐车次到站时间，`C²` 算不出来**。本节的代理是「这条线有多少比例走在"
          "**带公交专用道的道路**上」（Carto 的 `Category` 带 `, Bus` 后缀即可判）。"
          "**代理只能用于归因排序，不能当游戏内数值引用。**\n")
        A("| 线路 | 专用道覆盖率 | 人/车（全城中位 %s）| 估算间隔 min | 归因 | 建议动作 |"
          % fmt(tsq["median_pax_per_vehicle"], 1))
        A("|---|---|---|---|---|---|")
        for x in tsq["routes"]:
            A("| %s | %.0f%% | %s | %s | %s | %s |" % (
                x["name"], x["bus_lane_share"] * 100,
                fmt(x["pax_per_vehicle"], 1), fmt(x["headway_min"], 1),
                x["verdict"], x["action"]))
        A("\n> **判读要点**：**「无专用道 + 客流低」的线路，先上专用道比先加车便宜** ——"
          "现实数据里公交专用道的收益主要来自**降低间隔方差（减串车）**，而不是提车速"
          "（苏黎世信号优先+AVL 只让车速 +1.9 km/h）。")

        # ---- 逐线配图：给出"改哪条线"的建议，就必须给出那条线的图 ----
        _need = [x for x in tsq["routes"]
                 if x.get("action") and ("加车" in x["action"] or "专用道" in x["action"]
                                         or "改" in x["action"] or "拆" in x["action"])]
        if maps.get("_dir") and _need:
            A("\n### 17.1 逐线配图（每条要动的线路一张图）\n")
            A("> **为什么一张图只讲一条线**：读者要能立刻看出这条线**服务哪些组团、"
              "走哪条干道、端点在哪**。把 12 条线画在一张图上，改线决策根本没法核验。"
              "图中**高亮的是该线**，其余线路淡化；底图为干道网（不含支路）。\n")
            try:
                from analysis.city_map import make_map as _mk
                _lim = 6
                for x in _need[:_lim]:
                    _safe = "".join(ch for ch in str(x["name"]) if ch.isalnum() or ch in "_-")
                    _p = os.path.join(maps["_dir"], "line-%s.png" % (_safe or "line"))
                    _mk(carto, _p, ["clusters", "roads", "arterial", "transit"],
                        width=1200, height=1200, highlight=[x["name"]])
                    FIG(_p, "线路 %s 走向与服务组团" % x["name"])
                    A("- **%s** —— %s｜动作：%s（见上方配图）"
                      % (x["name"], x["verdict"], x["action"]))
                if len(_need) > _lim:
                    A("- （其余 %d 条按同样方法出图：`city_map.py --highlight \"线名\"`）"
                      % (len(_need) - _lim))
            except Exception as _e:      # noqa: BLE001
                A("- ⚠️ 逐线配图生成失败：%s" % _e)

    # ---------- 通勤可达性（路网） ----------
    if commute:
        A("\n## 18. 通勤可达性（**路网距离**，不是直线距离）")
        A("> **机制（1.6.0f1 起）**：寻路距离上限**按出行目的分设**（工作 / 上学 / 购物 / 休闲各有合理范围），"
          "**找不到可行路线就辞职/搬离** → 「要绕多远」比「直线多近」更关键。"
          "本节用 `Network_Centerline` 建加权图（权重 = 长度 ÷ 限速）跑 Dijkstra，"
          "起点 = 前 %d 个就业中心（400 m 网格），终点 = 每个有居民的 400 m 网格。" % 12)
        A("> ⚠️ **必须和「岗位缺口」一起读**（最容易误读的地方）：本节量的是"
          "「住宅 → **最近**就业中心」的路网距离。**距离短 ≠ 不缺岗位** —— "
          "**形态病**（住得离岗位远）要修路/迁中心；**总量病**（岗位总是不够）要**加岗位用地**。"
          "两者处方完全不同。\n")
        A("| 指标 | 实测 |")
        A("|---|---|")
        A("| 路网规模 | %d 节点 / %d 边 |" % (commute["network"]["nodes"], commute["network"]["edges"]))
        A("| 到最近就业中心的**中位**路网距离 | **%s m** |" % fmt(commute["median_road_m"], 0))
        A("| 最远住宅聚类 | %s m |" % fmt(commute["max_road_m"], 0))
        A("| 吸附不到路网的居民占比 | %.1f%% |" % (commute["unreachable_share"] * 100))
        A("| **岗位 / 人口** | **%s** |" % fmt(commute["jobs_per_capita"], 2))
        A("\n**按阈值的敏感性分析**（官方**未公布**四类出行的距离上限 → 只作敏感性，不是判定线）：\n")
        A(md_table(["超过该距离的居民占比", "阈值"],
                   [["%.1f%%" % v["share_over"] * 100 if False else "%.1f%%" % (v["share_over"] * 100),
                     "%d km" % T] for T, v in sorted(commute["bands"].items())]))
        # 自动判读：形态 vs 总量
        med = commute["median_road_m"]
        jpc = commute["jobs_per_capita"]
        far = commute["bands"].get(12, {}).get("share_over", 0)
        if med is not None and med < 3000 and far <= 0.10 and jpc is not None and jpc < 0.5:
            A("\n> ✅ **判读：这是「总量病」，不是「形态病」。** 到最近就业中心的中位路网距离只有 **%s m**、"
              "超过 12 km 的居民 **%.1f%%** —— **城市形态没有问题**；但**岗位/人口只有 %s**，"
              "说明居民不是「住得远」，而是**本地没那么多岗位可做**，只能出城上班。"
              "而**出城通勤者不缴税** → 这才是税收上不去的根因。"
              % (fmt(med, 0), far * 100, fmt(jpc, 2)))
            A("> **处方：不要再整治通勤（划不来），要把增量土地给「能装岗位」的用途** —— "
              "办公每岗位占地最少且税基等级最高（看 第 9 节 / 第 11 节），工业次之。")
        elif far > 0.10:
            A("\n> ⚠️ **判读：存在「形态病」** —— 有 **%.1f%%** 的居民到最近就业中心超过 12 km，"
              "在 1.6.0f1 之后属高危（可能出现辞职/搬离）。"
              "**处方**：在这些片区附近增设就业用地，或改善路网联通（看 第 3 节 路网等级与 第 5 节 走廊）。"
              % (far * 100))

    # ---------- 20. 道路流量与拥堵治理 ----------
    if traffic:
        t = traffic
        A("\n## 19. 道路流量与**拥堵治理**（新版 GeoJSON 的 `Volume`）")
        if maps.get("arterial"):
            _n_art = FIG(maps["arterial"], "干道网（不含支路）", key="arterial")
            _n_tr = FIG(maps.get("transit_advice"), "组团划分与公交/轨道可达性",
                        key="transit_advice")
            _refs = "、".join("图 %d" % n for n in (_n_art, _n_tr) if n)
            if _refs:
                A("> 📍 **配套图**：%s。本节给出的「哪条路该分流/该补车道」"
                  "都能在这些图上定位核验。" % _refs)
        A("> **口径**：`Volume` = 路段车流量；**单车流量 = `Volume ÷ Lane`**，"
          "是唯一与路段长短无关、可横向比较的负荷量。"
          "**CSL2 官方从未公布道路通行能力（pcu/h）**（多次核查确认）→ "
          "本节**只用同城同等级路段的相对分位判拥堵，不给绝对阈值**。"
          "已排除 **%d 段 `Lane=0`**（铁路/地铁/步道/水道），否则会把「没车道」当成「极拥堵」。\n"
          % t["excluded_zero_lane"])
        if t.get("excluded_map_native"):
            A("> ⭐ 另已整体剔除 **%d 段位于非解锁区的路段**（**地图自带资源**，"
              "玩家未建、不拥有）—— 它们的拥堵与车道数**不是本城的问题**，"
              "**不得**作为本城路网缺陷或等级失衡的证据。\n" % t["excluded_map_native"])
        A(md_table(["道路等级", "段数", "里程 km", "**车公里**", "**负荷占比**", "单车道中位", "单车道峰值", "车道中位"],
                   [[c["category"], c["segments"], fmt(c["km"], 1), fmt(c["veh_km"], 0),
                     "**%.1f%%**" % (100 * c["share_of_veh_km"]), fmt(c["vpl_median"], 1),
                     fmt(c["vpl_max"], 1), fmt(c["lanes_median"], 0)]
                    for c in t["categories"] if c["veh_km"] > 0]))
        _top = t["categories"][0]
        A("\n> **关键读数**：**%s 承担了 %.1f%% 的车公里负荷**（%.1f km，占路网 %.0f%%），"
          "而单车道中位只有 %.1f —— %s。"
          % (_top["category"], 100 * _top["share_of_veh_km"], _top["km"],
             100 * _top["km"] / max(1e-9, t["total_km"]), _top["vpl_median"],
             "说明**它是全城的主承载体**，治理顺序应从它开始"
             if "Highway" in _top["category"] else "它是主要负荷来源"))
        if _top["km"] / max(1e-9, t["total_km"]) > 0.4 and "Highway" in _top["category"]:
            A("> ⚠️ **高速里程占比 %.0f%% 但仍在承载主要流量** —— 与 第 3 节 的「高速过多」看似矛盾，"
              "实际含义是：**它同时是「最长的路」和「最忙的路」，所以任何高速上的瓶颈都会被放大**。"
              "官方 Traffic 页的原则仍然成立：**高速解决城际，不解决城内** → "
              "动作是**给高速分流（补主干/支路），而不是继续加宽高速**。"
              % (100 * _top["km"] / max(1e-9, t["total_km"])))

        if tclusters:
            A("\n### 20.1 拥堵热点区（800 m 网格聚类，按车公里负荷排序）\n")
            A(md_table(["位置（组团）", "地形", "路段数", "车公里", "单车峰值", "车道中位", "限速中位", "主要路段"],
                       [[LOC(c["x"], c["y"]), BUILDABLE(c["x"], c["y"]), c["segments"],
                         fmt(c["veh_km"], 0), fmt(c["vpl_max"], 1), fmt(c["lane_median"], 0),
                         fmt(c["limit_median"], 0), "、".join(str(n)[:12] for n in c["names"])]
                        for c in tclusters]))
            A("\n### 20.2 拥堵最重的单段（前 12）\n")
            A(md_table(["路段名", "等级", "车道", "限速", "流量", "**单车道流量**", "位置（组团）", "地形"],
                       [[str(s["name"])[:20], s["cat"], fmt(s["lane"], 0), fmt(s["limit"], 0),
                         fmt(s["vol"], 0), "**%s**" % fmt(s["vpl"], 1),
                         LOC(*s["f"].compute_centroid()), BUILDABLE(*s["f"].compute_centroid())]
                        for s in t["hot"][:12]]))
            # ---- 车道数缺口：高速却只有 1–2 车道，本身就是瓶颈 ----
            ld = t.get("lane_deficit") or {}
            if ld.get("single_lane_segments"):
                A("\n### 20.3 ⚠️ 结构性发现：**只有 1 条车道的高速段**\n")
                A("> 判据：**高速公路却只有 1 条车道** —— 这不是「流量大」，而是**供给本身有缺陷**，"
                  "与「该不该加宽高速」是两回事："
                  "官方 Traffic 页说「高速解决城际、不解决城内」，针对的是**给城内通勤再修新高速**；"
                  "**而把既有高速上的单车道瓶颈补到 2 条，属于修正明显缺陷，不是扩张。**\n"
                  "> （注：CSL2 里**双车道高速是常态**，全城 %d 段，**不算缺陷** —— 所以判据只锁 1 车道。）\n"
                  % ld.get("two_lane_segments", 0))
                A("实测全城有 **%d 段高速只有 1 条车道**，合计 **%.1f km**。其中最忙的：\n"
                  % (ld["single_lane_segments"], ld["single_lane_km"]))
                A(md_table(["路段名", "车道", "限速", "流量", "单车道流量", "位置（组团）", "地形"],
                           [[str(s["name"])[:20], fmt(s["lane"], 0), fmt(s["limit"], 0),
                             fmt(s["vol"], 0), "**%s**" % fmt(s["vpl"], 1),
                             LOC(*s["f"].compute_centroid()), BUILDABLE(*s["f"].compute_centroid())]
                            for s in ld["worst"][:6]]))
                _w = ld["worst"][0]
                A("\n> **动作**：① 把这 %d 段（%.1f km）补到 **2 车道** —— 工程量最小、"
                  "产能直接翻倍；② 同时检查这些段的**车道连接**有没有强制并线或错误转向"
                  "（用官方车道连接工具，**无需 Mod**）；③ 补完仍饱和**再考虑分流**"
                  "（补平行主干道），**不要继续加宽**。"
                  % (ld["single_lane_segments"], ld["single_lane_km"]))

            A("\n### 20.4 处方（按等级给不同动作 —— 加车道不是万能的）\n")
            A("| 症状 | 该做什么 | 不该做什么 | 依据 |")
            A("|---|---|---|---|")
            A("| **高速段单车道流量接近本等级峰值** | **给高速分流**：补平行的主干/支路，"
              "把城内短途出行从高速上摘下来 | ❌ 别再加宽高速 —— 高速解决城际，不解决城内 | 官方 Traffic 页 |")
            A("| **匝道/立交附近成串拥堵** | **分离交织、拉开匝道间距、用车道连接工具限制转向** | "
              "❌ 别指望「匝道再加一条车道翻倍」 —— 双车道匝道只有单车道产能的 1.6–1.8 倍 | 立交设计规范（现实标准） |")
            A("| **支路单车道流量偏高** | **瓶颈在路口**：减少接入点、合并路口、用单行做成对环路；"
              "先用官方**禁左/禁直/禁右标志**（无需 Mod） | ❌ 支路加车道几乎白加（支路单车道产能只有快速路的 0.55–0.65 倍） | 城市道路设计规范（现实标准）+ 实操手册 |")
            A("| **某走廊整体饱和** | 把**公交专用道 + 高频班次**做起来，把长距离通勤从路上摘走 | "
              "❌ 别同时上新线分流（拆分干线会把两条线的间隔都拉长） | 公共交通运营（现实标准） |")
            A("| **货运终端周边堵** | 补终端周边的**支路**、必要时迁终端到主干道旁 | "
              "❌ 别只在高速上做文章 —— 官方明确要求「优先保证终端与道路的连接」 | 官方 `Transportation` |")
            A("\n> **判据优先级（照这个顺序下结论，别跳步）**："
              "① 先看本节 第 20.1 节 热点是否落在**高速**上 → 若是，分流优先；"
              "② 再看热点是否集中在**匝道/立交** → 若是，改交织与转向；"
              "③ 若热点在**支路** → 治路口，不治路宽；"
              "④ 最后才考虑「这条走廊要不要上公交」（配合 第 17 节 的候车间隔归因）。")
            A("\n> ⚠️ **不要做的事**：**不要为了「降低单车流量」而拆路**。"
              "流量是需求的结果，拆路会把车赶到更窄的路上。**要改的是供给结构（分流/分级/治路口），"
              "不是把容量拿掉。**")

    # ---------- 与上期对比 ----------
    if delta:
        A("\n## 20. 与上期对比（只看最近两期的增量）")
        A("> 要看更多期的方向，用 `--trend`（见上一节）。\n")

        # ⭐⭐ **第一道关：游戏内时间可比性** —— 必须排在所有数值增量之前。
        # 理由：`Passenger` / `Volume` 这类读数随一天内的时段剧烈变化，
        # 「早高峰 vs 凌晨」的差异会被误读成"客流下降"。所以先判能不能比，再比。
        gt = delta.get("game_time") or {}
        if gt:
            _v = gt.get("verdict")
            _icon = {"可比": "✅", "需谨慎": "⚠️", "不可比": "⛔", "未知": "❓"}.get(_v, "❓")
            A("\n### 20.0 ⏰ **先判时点可比性**（游戏内时间）\n")
            A("> **为什么先看这个**：`Passenger`（线路乘客数）、`Volume`（车流量）等读数"
              "**随一天内的时段剧烈变化**。若两次存档分别落在「早高峰」与「凌晨」，"
              "客流差异**几乎全部由时点造成** —— 把它读成「公共交通客流下降」是**错的**。"
              "所以本节**先比时间，再比数值**。\n")
            A(md_table(["项", "上一期", "本期"], [
                ["游戏内时间", (gt.get("prev") or {}).get("time") or "**未知**",
                 (gt.get("cur") or {}).get("time") or "**未知**"],
                ["时段", (gt.get("prev_band") or "—"),
                 (gt.get("cur_band") or "—")],
                ["时间来源", (gt.get("prev") or {}).get("source") or "—",
                 (gt.get("cur") or {}).get("source") or "—"],
            ]))
            A("\n> %s **结论：%s** —— %s" % (_icon, _v, gt.get("reason") or ""))
            if gt.get("usable"):
                A("> - ✅ **可以直接比较**（不随时段变）：%s" % "、".join(gt["usable"]))
            if gt.get("blocked"):
                A("> - ⛔ **本次不可比较**（随时段变）：%s" % "、".join(gt["blocked"]))
            _rec = gt.get("recommend_save") or {}
            if _rec.get("why"):
                A("> - 📅 **下次存档建议**：%s" % _rec["why"])
            if _v in ("不可比", "未知"):
                A("\n> ⛔ **因此：本期任何「客流/流量上升或下降」的结论都不成立**，"
                  "请按上面的存档建议重取一期后再比较。以下增量表**只保留不随时段变的指标**。")
            A("")

        A(md_table(["指标", "变化量"], [
            ["人口", ("%+d" % delta["population"])],
            ["岗位", ("%+d" % delta["jobs"])],
            ["已解锁地块", ("%+d" % delta["tiles_unlocked"])],
            ["路网长度 km", ("%+.1f" % delta["road_km"])],
            ["分区图斑总数", ("%+d" % delta["zoning_total"])],
        ]))
        if delta["zoning_delta"]:
            A("\n**分区变化**：" + "、".join("%s %+d 图斑" % (ZONE_CN.get(k, k), v)
                                          for k, v in sorted(delta["zoning_delta"].items(), key=lambda kv: -abs(kv[1]))
                                          if v != 0) or "（无变化）")
        if delta["districts"]:
            A("\n" + md_table(["区", "人口变化", "岗位变化", "现人口", "现岗位"],
                              [[d["name"], "%+d" % d["res_delta"], "%+d" % d["emp_delta"],
                                fmt(d["res_now"]), fmt(d["emp_now"])] for d in delta["districts"]]))
        if delta["routes"]:
            # ⚠️ 客/货分界（`Route_Centerline.Object`）：**货运线路（RouteCargo）单独成表**，
            # 不进客运对比 —— 它的 Passenger 恒为 0，混在客运表里会让"乘客下降"的判读失真。
            _pax_rows = [r for r in delta["routes"] if not r.get("is_cargo")]
            _cargo_rows = [r for r in delta["routes"] if r.get("is_cargo")]
            # ⚠️ 乘客变化列**只在时点可比时才给**。不可比时把该列拆出去，
            # 只留"不随时段变"的配车/增删，避免读者把时段差当成客流趋势。
            _gtv = (gt or {}).get("verdict")
            if _pax_rows:
                if _gtv in ("不可比", "未知"):
                    A("\n**客运线路变化（⚠️ 已隐去「乘客变化」列）**\n")
                    A("> ⛔ 两次存档的**游戏内时点不可比**（见 第 20.0 节），"
                      "`Passenger` 的差值反映的是**时点差异而不是客流趋势**，因此不予列出。"
                      "下表只保留**不随时段变**的量（配车数与线路增删）；"
                      "**要看客流趋势，请按 第 20.0 节 的存档建议重新取一期**。\n")
                    A(md_table(["线路", "方式", "状态", "车辆变化", "现车辆"],
                               [[r["name"], TRANSPORT_CN.get(r["transport"], r["transport"]),
                                 r["status"], "%+d" % r["veh_delta"], fmt(r["veh_now"])]
                                for r in sorted(_pax_rows, key=lambda r: -abs(r["veh_delta"]))]))
                else:
                    A("")
                    A(md_table(["线路", "方式", "状态", "乘客变化", "现乘客", "车辆变化", "现车辆"],
                               [[r["name"], TRANSPORT_CN.get(r["transport"], r["transport"]), r["status"],
                                 "%+d" % r["pax_delta"], fmt(r["pax_now"]),
                                 "%+d" % r["veh_delta"], fmt(r["veh_now"])]
                                for r in sorted(_pax_rows, key=lambda r: -abs(r["pax_delta"]))]))
                    A("\n> 判读：**两次时点可比（%s）**，乘客变化可用。"
                      "**乘客下降的线路要立刻查原因**（间隔变长？走廊被抢？站点被迁？）；"
                      "**新增线路若乘客远低于同城中位数，说明需求判断错了**。"
                      % ((gt or {}).get("verdict") or "—"))
            if _cargo_rows:
                A("\n**货运线路变化（口径独立 —— 只看配车与线路增删，不看乘客）**\n")
                A("> ⚠️ 货运铁路 / 货运航线（`RouteCargo`）**不与客运数据一并分析**；"
                  "本表只反映「运力有没有加」，其取舍要与**工业布点**一起判断"
                  "（货运线路不与客运数据混算）。\n")
                A(md_table(["货运线路", "方式", "状态", "车辆变化", "现车辆"],
                           [[r["name"], TRANSPORT_CN.get(r["transport"], r["transport"]),
                             r["status"], "%+d" % r["veh_delta"], fmt(r["veh_now"])]
                            for r in sorted(_cargo_rows, key=lambda r: -abs(r["veh_delta"]))]))

    md = "\n".join(L) + "\n"
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(md)
    if out_json:
        payload = {"data_checks": checks, "city": city, "zoning": zoning, "roads": roads,
                   "transit": routes, "overlap": overlap, "catchment": catchment,
                   "terrain": terrain, "job_centers": centers,
                   "land_efficiency": eff, "risk_proxies": risk, "delta_vs_prev": delta,
                   "tax_potential": tax, "noise_exposure": noise,
                   "transit_service_quality": tsq, "stop_coverage": cov,
                   "underdevelopment": underdev, "lane_km": lanekm,
                   "trend": trend}
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1, default=str)
    return {"md": out_md, "json": out_json, "checks": checks,
            "land_efficiency": eff, "risk_proxies": risk, "delta": delta,
            "tax_potential": tax, "maps": maps}


def _overlap_verdict(p):
    share = p["share_within_400m"]
    if share >= 0.8:
        return "**同一走廊** → 合并 + 车辆数相加"
    if share >= 0.5:
        return "部分重合 → 检查是否在抢同一批乘客"
    return "基本独立（无需处理）"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--carto", default=None,
                    help="Carto 导出目录（含 Shapefile/ 与 GeoTIFF/）；不给则自动查找常见目录名")
    ap.add_argument("--prev", default=None,
                    help="可选：上一期 Carto 导出目录，用于输出「与上期对比」的增量")
    ap.add_argument("--at", default=None,
                    help="可选·**仅用于纠错**：本期导出的游戏内时间，如 `2031-01-22 23:22`。"
                         "**通常不需要给** —— 脚本会自动从存档元数据（`*.SaveGameMetadata` 的 "
                         "`simulationDate`）读取。只有在自动匹配明显不对时才用它覆盖。")
    ap.add_argument("--prev-at", default=None,
                    help="可选·**仅用于纠错**：上一期导出的游戏内时间（格式同 `--at`）。通常不需要给。")
    ap.add_argument("--no-auto-time", action="store_true",
                    help="禁用自动读取存档时间（用于排查匹配问题）。")
    ap.add_argument("--trend", default=None,
                    help="可选：多期目录（逗号分隔，按时间先后给），输出趋势表")
    ap.add_argument("--out", default="city_report.md")
    ap.add_argument("--json", default=None)
    ap.add_argument("--maps", default=None,
                    help="可选：输出配图目录。给了就自动生成 4 张图（地形/干道/组团公交/综合），"
                         "并在「公共交通建议」相关小节里引用它们 —— "
                         "建议与配图应当成对出现，否则读者无法核验建议的空间依据。")
    a = ap.parse_args(argv)
    carto_dir = a.carto or find_carto_dir()
    if not carto_dir:
        print("找不到 Carto 导出目录。请用 --carto 显式指定（目录里应有 Shapefile/ 子目录）。")
        return 2
    if not a.carto:
        print("自动识别到 Carto 目录：%s" % carto_dir)
    carto = CartoData(carto_dir)
    prev = CartoData(a.prev) if a.prev else None
    trend = None
    if a.trend:
        dirs = [s.strip() for s in a.trend.split(",") if s.strip()]
        t = analyze_trend(dirs)
        if len(t["snapshots"]) >= 2:
            trend = t
    res = build_report(carto, a.out, a.json, prev=prev, trend=trend,
                       maps_dir=a.maps, at=a.at, prev_at=a.prev_at,
                       auto_time=(not a.no_auto_time))
    print("written:", res["md"], ("and " + res["json"]) if res["json"] else "")
    _gt = (res.get("delta") or {}).get("game_time")
    if _gt:
        print("游戏时间可比性：%s" % _gt.get("verdict"))
        _p, _c = (_gt.get("prev") or {}), (_gt.get("cur") or {})
        print("  上一期 %s（%s） / 本期 %s（%s）"
              % (_p.get("time") or "未知", _p.get("source") or "—",
                 _c.get("time") or "未知", _c.get("source") or "—"))
        if (_gt.get("recommend_save") or {}).get("why"):
            print("  建议下次存档：%s" % _gt["recommend_save"]["why"])
    if res.get("maps"):
        print("配图：")
        for k, v in res["maps"].items():
            print("  - %-22s %s" % (k, v))
    if res.get("checks"):
        print("\n数据自检有 %d 条告警（详见报告 第 0 节）：" % len(res["checks"]))
        for c in res["checks"]:
            print("  - " + c.replace("**", ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
