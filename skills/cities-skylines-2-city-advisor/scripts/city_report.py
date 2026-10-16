# -*- coding: utf-8 -*-
"""一键城市诊断报告（CLI 入口；实现见 `analysis/city_reports.py`）。

用法（与旧版完全一致，路径不变）：
    python -X utf8 scripts/city_report.py --carto <Carto导出目录> [--prev <上期>] [--out 报告.md]

为什么保留这一层：`SKILL.md` 与 `references/80`/`100` 都按这个路径给出命令，
**它是稳定契约**；实现被拆到 `analysis/` 下以便单独阅读与维护。
"""
import os
import runpy
import sys

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

if __name__ == "__main__":
    runpy.run_module("analysis.city_reports", run_name="__main__", alter_sys=True)
