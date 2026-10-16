# -*- coding: utf-8 -*-
"""稳定接口：Carto 数据读取库（实现已移到 `core/carto_reader.py`）。

保留这一层的理由：`references/70`、`references/80` 与外部脚本都按
`from carto_reader import CartoData` 使用它 —— **这个导入路径是稳定契约**。
实现请直接看 `core/carto_reader.py`，本文件只做转发。
"""
import os as _os
import sys as _sys

_SCRIPTS_DIR = _os.path.dirname(_os.path.abspath(__file__))
if _SCRIPTS_DIR not in _sys.path:
    _sys.path.insert(0, _SCRIPTS_DIR)

from core.carto_reader import *          # noqa: F401,F403,E402
from core.carto_reader import (          # noqa: F401,E402
    CartoData, Feature, GridIndex, Raster,
    build_building_index, build_poi_index,
    find_carto_dir, find_game_carto_dir, find_save_dir,
    list_saves, read_save_metadata, read_dbf, read_shp,
    read_geojson, find_geojson, GEOJSON_SCALE,
)
