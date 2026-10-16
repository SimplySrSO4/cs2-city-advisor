# -*- coding: utf-8 -*-
"""report_base.py —— 报告生成的公共底座：中英对照表、格式化与 Markdown 表格。

被 `city_reports.py` 与 `city_map.py` 共用；**不含任何分析逻辑**，
所以改动这里不会影响任何指标口径。
"""

# ------------------------------------------------------------------ 中英对照（仅用于报告可读性）
TRANSPORT_CN = {
    "Bus": "公交", "Tram": "有轨电车", "Subway": "地铁", "Train": "铁路",
    "Ferry": "渡轮", "Ship": "货船", "Airplane": "航空", "Taxi": "出租车",
    "BusLine": "公交", "SubwayLine": "地铁",
}
ZONE_CN = {
    "Residential": "住宅", "Commercial": "商业", "Industrial": "工业",
    "Office": "办公", "Residential, Commercial": "商住混合", "Farmland": "农田",
    "Forestry": "林业", "Extractor": "采掘", "None": "无",
}


def fmt(x, nd=0):
    """数值格式化：`None` 一律输出 `—`（**不要输出 0** —— 0 与"没有数据"必须可区分）。"""
    if x is None:
        return "—"
    if isinstance(x, float):
        return ("%%.%df" % nd) % x
    return str(x)


def md_table(headers, rows):
    """把二维数据渲染成 Markdown 表格。"""
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)
