#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
qgis_common.py —— **QGIS 出图共用层**（预检 + 数据准备），纯标准库。

为什么把"能不能用 QGIS"和"怎么写 QGIS 脚本"分开
------------------------------------------------
* 本模块**在任何 Python 下都能 import**（只依赖标准库），所以 `city_map.py`
  可以在**没有装 QGIS 的机器上**先调用 `qgis_available()` 预检，
  再决定是走 QGIS 还是回退 Pillow 画法 —— 不必为了"探测"而去启动 QGIS。
* `prepare_qgis_layers()` 把 Carto 的 GeoJSON 转成**带真实 CRS 的 GeoPackage**。
  这一步是 QGIS 方案的**关键前提**，原因见下。

坐标口径（踩坑记录，必读）
--------------------------
Carto 新版导出的是 `GeoJSON/`，它有两个坑：
1. **坐标是归一化值**（×`GEOJSON_SCALE`=111006.1 才是米），文件里没有 CRS；
2. **GeoJSON 规范规定 CRS 一律是 WGS84**，因此 OGR/QGIS 读进来一律是 `EPSG:4326`，
   `.prj` 同目录也不认。
   ⇒ 后果：**QGIS 会把 14 km 宽的城市当成 0.13°（≈14 km 的千分之一）的点**，
   图面空白。本项目实测踩过这个坑。
3. 另有一条**只能靠 `setSubsetString` 兜住**的坑：GeoJSON 驱动**忽略 URI 里的 `crs=` 参数**，
   加了它图层直接 `isValid()==False`。

**解决办法**：把坐标加上一个固定平移（`LOCAL_SHIFT_X = 400000`）搬进 **EPSG:32631（UTM 31N）**
的真实米制区间（与该地图 GeoTIFF 同一坐标系），写成 **GeoPackage** ——
GeoPackage 自带 SRS 表，CRS 会被 QGIS 原样读到，不再依赖任何猜测。

⚠️ 这个平移**只影响图层在 QGIS 里的绝对坐标**，不影响任何距离与形状（纯平移）。
`local_to_utm()` / `utm_to_local()` 负责两个口径之间的换算 ——
**报告与建议里的坐标一律用"本地米制"（即以地图最小角为原点的口径），只有渲染时才加平移。**
"""

import os
import shutil
import subprocess
import sys

#: 本地米制 → UTM 31N 的固定平移（东向）。只用于渲染，不影响形状与距离。
LOCAL_SHIFT_X = 400000.0

#: Carto 图层 → (GeoPackage 图层名, 几何类型)
LAYERS = (
    ("Network_Boundary", "Polygon"),
    ("Network_Centerline", "LineString"),
    ("Building_Boundary", "Polygon"),
    ("POI_Location", "Point"),
    ("Route_Centerline", "LineString"),
    ("Area_Boundary", "Polygon"),
    ("Zoning_Boundary", "Polygon"),
)

#: 官方 QML 样式（Carto 自带 `Styles/` 下三套）。本 skill 默认用 Street 套。
STYLE_SETS = ("Street", "Plan", "Topo")

STYLE_FILES = {
    "Network_Boundary": "%s-Network-Boundary.qml",
    "Network_Centerline": "%s-Network-Centerline (Chinese).qml",
    "Building_Boundary": "%s-Building-Boundary.qml",
    "POI_Location": "%s-POI-Location (Chinese).qml",
    "Route_Centerline": "%s-Route-Centerline (By Transport).qml",
    "Area_Boundary": "%s-Area-Boundary (Chinese).qml",
    "Zoning_Boundary": "%s-Zoning-Boundary (By Zoning).qml",
}

#: Windows 上 QGIS 的常见安装位置（也允许用环境变量 `CSL2_QGIS_ROOT` 指定）
QGIS_HINTS = (
    r"C:\Program Files\QGIS 3.44.15",
    r"C:\Program Files\QGIS 3.44.14",
    r"C:\Program Files\QGIS 3.40.0",
    r"C:\Program Files\QGIS 3.34.0",
    r"C:\OSGeo4W",
    "/usr",
    "/Applications/QGIS.app/Contents/MacOS",
)


#: 显式关闭 QGIS 路径的值（`SKILL.md` 铁律 11 要求"先假设不存在再探测"，
#: 这两个值同时也是**测试"没有 QGIS 时"行为**的开关）
QGIS_OFF = ("0", "off", "none", "no", "false", "")


def _qgis_root(hint=None):
    """返回可用的 QGIS 根目录，找不到返回 `None`。

    **探测顺序（`SKILL.md` 铁律 11）**：`CSL2_QGIS_ROOT` → 显式 `hint` → 已知安装位置 → 扫描。

    ⚠️ `CSL2_QGIS_ROOT` **是强制开关**，不是"提示"：
    设成一个有效路径 → 只用它；设成 `0` / `off` / `none` → **直接判定没有 QGIS**
    （用于在装了 QGIS 的机器上验证"无 QGIS 时的退化行为"）；
    设成一个不存在的路径 → 也判定没有（避免"我以为关掉了、其实自动探测又找到了"）。
    """
    env = os.environ.get("CSL2_QGIS_ROOT")
    if env is not None:
        if env.strip().lower() in QGIS_OFF:
            return None
        return env if _probe_root(env) else None
    cands = [hint] if hint else []
    cands += list(QGIS_HINTS)
    if os.name == "nt":
        # 扫描 Program Files 下的 QGIS x.y.z
        for base in (os.environ.get("ProgramFiles", r"C:\Program Files"),
                     os.environ.get("ProgramW6432", r"C:\Program Files")):
            if not base or not os.path.isdir(base):
                continue
            try:
                for n in sorted(os.listdir(base)):
                    if n.upper().startswith("QGIS"):
                        cands.append(os.path.join(base, n))
            except OSError:
                pass
    seen = set()
    for c in cands:
        if not c or c in seen:
            continue
        seen.add(c)
        if _probe_root(c):
            return c
    return None


def _probe_root(c):
    """该目录是不是一个可用的 QGIS 根目录（有 PyQGIS 绑定）。"""
    for probe in (os.path.join(c, "apps", "qgis-ltr", "python"),
                  os.path.join(c, "apps", "qgis", "python"),
                  os.path.join(c, "share", "qgis", "python")):
        if os.path.isdir(probe):
            return True
    return False


def qgis_paths(hint=None):
    """返回 QGIS 出图所需的路径字典；不可用时返回 None。

    键：`root` / `python` / `pyqgis`（PYTHONPATH 前缀）/ `prefix`（QGIS_PREFIX_PATH）
    / `bin` / `qt_bin` / `proj` / `gdal` / `ogr2ogr`
    """
    root = _qgis_root(hint)
    if not root:
        return None
    apps = os.path.join(root, "apps")
    pyqgis = prefix = None
    for name in ("qgis-ltr", "qgis"):
        p = os.path.join(apps, name, "python")
        if os.path.isdir(p):
            pyqgis = p
            prefix = os.path.join(apps, name)
            break
    if pyqgis is None and os.path.isdir(os.path.join(root, "share", "qgis", "python")):
        pyqgis = os.path.join(root, "share", "qgis", "python")
        prefix = os.path.join(root, "share", "qgis")
    if pyqgis is None:
        return None
    if os.name == "nt":
        py = os.path.join(apps, "Python312", "python.exe")
        if not os.path.exists(py):
            py = os.path.join(apps, "Python39", "python.exe")
        binp = os.path.join(root, "bin")
        qtb = os.path.join(apps, "Qt5", "bin")
        proj = os.path.join(root, "share", "proj")
        gdal = os.path.join(apps, "gdal", "share", "gdal")
    else:
        py = os.path.join(binp := os.path.join(root, "bin"), "python3")
        binp = os.path.join(root, "bin")
        qtb = None
        proj = os.path.join(root, "share", "proj")
        gdal = os.path.join(root, "share", "gdal")
    if not os.path.exists(py):
        return None
    return {
        "root": root, "python": py, "pyqgis": pyqgis, "prefix": prefix,
        #: ⚠️ **必须进 PATH**：`qgis_core.dll` 等都在 `<prefix>/bin` 下。少这一项时
        #: `import qgis.core` 会报 `ImportError: DLL load failed while importing _core`，
        #: 而错误信息完全不提 PATH —— 本项目实测踩过（`qgis_env()` 已自动带上）。
        "qgis_bin": os.path.join(prefix, "bin"),
        "bin": binp, "qt_bin": qtb, "proj": proj, "gdal": gdal,
        "ogr2ogr": os.path.join(binp, "ogr2ogr.exe" if os.name == "nt" else "ogr2ogr"),
    }


def qgis_available(hint=None):
    """QGIS 是否可用于出图（只看文件是否存在，不启动 QGIS）。"""
    return qgis_paths(hint) is not None


def qgis_env(paths, extra=None):
    """构造运行 QGIS Python 所需的环境变量（**不改动当前进程**，返回副本）。"""
    env = dict(os.environ)
    parts = [paths["pyqgis"]]
    if paths.get("qt_bin"):
        parts.append(paths["qt_bin"])
    if paths.get("bin"):
        parts.append(paths["bin"])
    env["PYTHONPATH"] = os.pathsep.join(parts + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
    env["QGIS_PREFIX_PATH"] = paths["prefix"]
    env["PATH"] = os.pathsep.join(
        [p for p in (paths.get("qgis_bin"), paths.get("bin"), paths.get("qt_bin")) if p]
        + [env.get("PATH", "")])
    env["PROJ_LIB"] = paths["proj"]
    env["GDAL_DATA"] = paths["gdal"]
    env["QT_QPA_PLATFORM"] = "offscreen"
    # ⚠️ Qt 不再自带字体；不指一个中文字体目录，中文标注会整片变成豆腐块。
    fd = _font_dir()
    if fd:
        env["QT_QPA_FONTDIR"] = fd
    if extra:
        env.update(extra)
    return env


_FONT_CACHE = [None]


def _font_dir():
    """准备一个含中文字体的目录（供 `QT_QPA_FONTDIR`）。找不到字体返回 None。"""
    if _FONT_CACHE[0] is not None:
        return _FONT_CACHE[0] or None
    if os.name != "nt":
        _FONT_CACHE[0] = ""
        return None
    src = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
    want = ("msyh.ttc", "msyhbd.ttc", "simhei.ttf", "simsun.ttc", "arial.ttf", "times.ttf")
    tmp = os.path.join(os.environ.get("TEMP", "/tmp"), "csl2_qgis_fonts")
    try:
        os.makedirs(tmp, exist_ok=True)
        for f in want:
            p = os.path.join(src, f)
            d = os.path.join(tmp, f)
            if os.path.exists(p) and not os.path.exists(d):
                shutil.copyfile(p, d)
    except OSError:
        _FONT_CACHE[0] = ""
        return None
    ok = any(os.path.exists(os.path.join(tmp, f)) for f in want)
    _FONT_CACHE[0] = tmp if ok else ""
    return tmp if ok else None


# ------------------------------------------------------------------ 坐标换算

def local_to_utm(x, y):
    """本地米制 → 渲染用 UTM 米（仅东向平移）。"""
    return (x + LOCAL_SHIFT_X, y)


def utm_to_local(x, y):
    """渲染用 UTM 米 → 本地米制。"""
    return (x - LOCAL_SHIFT_X, y)


def bounds_local_to_utm(b):
    """`(x0, y0, x1, y1)` 本地范围 → 渲染范围。"""
    x0, y0, x1, y1 = b
    return (x0 + LOCAL_SHIFT_X, y0, x1 + LOCAL_SHIFT_X, y1)


# ------------------------------------------------------------------ 数据准备

_PRJ = ('PROJCS["WGS 84 / UTM zone 31N",GEOGCS["WGS 84",DATUM["WGS_1984",'
        'SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],'
        'AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],'
        'UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],'
        'AUTHORITY["EPSG","4326"]],PROJECTION["Transverse_Mercator"],'
        'PARAMETER["latitude_of_origin",0],PARAMETER["central_meridian",3],'
        'PARAMETER["scale_factor",0.9996],PARAMETER["false_easting",500000],'
        'PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],'
        'AXIS["Easting",EAST],AXIS["Northing",NORTH],AUTHORITY["EPSG","32631"]]')


def _write_geojson_utm(carto, layer_key, path):
    """把某层写成"本地米制 + 平移"的 GeoJSON（带同名 `.prj`）。返回要素数。"""
    import json
    feats = carto.layer(layer_key)
    out = []
    for f in feats:
        parts = f.parts if f.parts and isinstance(f.parts[0], list) else [f.parts]
        if f.geom_type == "polygon":
            geom = {"type": "Polygon",
                    "coordinates": [[[round(p[0] + LOCAL_SHIFT_X, 2), round(p[1], 2)] for p in ring]
                                    for ring in parts]}
        elif f.geom_type == "line":
            if len(parts) > 1:
                geom = {"type": "MultiLineString",
                        "coordinates": [[[round(p[0] + LOCAL_SHIFT_X, 2), round(p[1], 2)] for p in part]
                                        for part in parts]}
            else:
                geom = {"type": "LineString",
                        "coordinates": [[round(p[0] + LOCAL_SHIFT_X, 2), round(p[1], 2)]
                                        for p in parts[0]]}
        else:
            flat = [p for part in parts for p in part]
            geom = {"type": "Point",
                    "coordinates": [round(flat[0][0] + LOCAL_SHIFT_X, 2), round(flat[0][1], 2)]}
        out.append({"type": "Feature", "properties": dict(f.attrs), "geometry": geom})
    txt = json.dumps({"type": "FeatureCollection", "name": layer_key, "features": out},
                     ensure_ascii=False, separators=(",", ":"))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(txt)
    with open(path[:-5] + ".prj", "w", encoding="utf-8") as fh:
        fh.write(_PRJ)
    return len(out)


def prepare_qgis_layers(carto, out_dir, layers=None, paths=None, quiet=False):
    """把 Carto 数据转成 QGIS 可直接读、**CRS 正确**的 GeoPackage。

    返回 `{图层名: gpkg 路径}`；失败抛 `RuntimeError`。
    `out_dir` 建议放在报告目录下（例如 `<报告目录>/qgis/`）。
    """
    paths = paths or qgis_paths()
    if not paths:
        raise RuntimeError("未找到 QGIS 安装；请设置环境变量 CSL2_QGIS_ROOT 指向 QGIS 根目录。")
    ogr = paths["ogr2ogr"]
    if not os.path.exists(ogr):
        raise RuntimeError("找不到 ogr2ogr：%s" % ogr)
    os.makedirs(out_dir, exist_ok=True)
    want = list(layers or [k for k, _ in LAYERS])
    gpkg = {}
    for key, _gt in LAYERS:
        if key not in want:
            continue
        src = os.path.join(out_dir, key + ".json")
        n = _write_geojson_utm(carto, key, src)
        dst = os.path.join(out_dir, key + ".gpkg")
        if os.path.exists(dst):
            os.remove(dst)
        cmd = [ogr, "-f", "GPKG", "-a_srs", "EPSG:32631", "-nln", key, dst, src]
        env = qgis_env(paths)
        pr = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if pr.returncode != 0 or not os.path.exists(dst):
            raise RuntimeError("ogr2ogr 失败（%s）：%s" % (key, pr.stdout.decode("utf-8", "replace")[:400]))
        gpkg[key] = dst
        if not quiet:
            print("  [qgis] %-20s %5d 要素 → %s" % (key, n, os.path.basename(dst)))
    return gpkg
