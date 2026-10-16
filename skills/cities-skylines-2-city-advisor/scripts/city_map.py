# -*- coding: utf-8 -*-
"""诊断图输出（CLI 入口；实现见 `analysis/city_map.py`）。

用法（与旧版完全一致）：
    python -X utf8 scripts/city_map.py --carto <Carto导出目录> --out city_map.png
"""
import os
import runpy
import sys

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

if __name__ == "__main__":
    runpy.run_module("analysis.city_map", run_name="__main__", alter_sys=True)
