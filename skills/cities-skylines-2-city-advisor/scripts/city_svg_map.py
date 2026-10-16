#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
city_svg_map.py —— **不用 QGIS 也能出制图级规划图**（读 Carto 官方 `.qml` 样式）

它解决什么问题
--------------
`SKILL.md` 铁律 11 原来只有两条路：

| 有 QGIS | `carto_qgis_map.py` | 制图级 |
| 无 QGIS | `city_map.py`（Pillow） | 工程草图，且**尽量少出图** |

原因是：官方样式的解释权只有 QGIS 有 —— `.qml` 没人读，就只能"自己猜图层"。
本脚本把 `.qml` 读出来（`core/qml_style.py`），于是**第三条路**成立：

    无 QGIS → 官方配色 / 官方线宽 / 官方分级规则 + 真实路幅 / 逐栋建筑 / 中文标注

**精度不来自 QGIS，来自数据。** QGIS 提供的是"制图加工"（样式解释、标注引擎、
版面），而几何真值一直在 Carto 导出里。把加工这一层自己实现，就不需要 QGIS 了。

与 QGIS 路径的关系
------------------
* **同一套输入**：`Carto/GeoJSON` + `Carto/Styles/<套名>/*.qml`；
* **同一套 CLI**：`--bounds`（本地米制）/ `--size` / `--title` / `--style-set` /
  `--layers` / `--hide` / `--interval` / `--no-legend` / `--no-scalebar`；
* **同一套图层顺序**：`--layers` **第一项在最上面**（与 `carto_qgis_map.py` 的
  `QgsMapSettings.setLayers()` 语义一致 —— 实测：把 `Zoning_Boundary` 放第一位时
  分区图斑会盖住建筑，放第二位则相反）。所以默认顺序里 `Zoning_Boundary` 在最上、
  `Route_Centerline` 在最下（会被路面盖住）。**想让分区当"底色"、想看见公交线路，
  就把它们往后 / 往前挪**（见下方"推荐的两种顺序"）；
* **同一套比例尺口径**：`scalemindenom` / `scalemaxdenom` 按本图比例尺分母过滤，
  因此 1:50000 下不会冒出只在 1:30000 以内显示的步行道 —— 与 QGIS 所见一致。

与 QGIS 路径的**已知差异**（不隐瞒）
-----------------------------------
| 项 | QGIS | 本脚本 |
|---|---|---|
| 标注摆放 | 沿曲线（curved） | 沿切向的**直排旋转**文字（`placement=3` 的近似；不会沿弧弯） |
| POI 图标 | `SvgMarker` / `FontMarker` 图形 | **同色圆点**（零依赖无法复现图形）——计入 `degraded` |
| 面状图案 | `LinePatternFill` 原生图案 | 近似为**斜线填充** |
| 行政区 | 官方样式 | 默认同样隐藏 |
| 版面 | `QgsPrintLayout`（图例会溢出页面） | 自绘：图例**不覆盖地图**、条目按"实际画出来的"反推 |
| 字体 | `Microsoft JhengHei UI`（繁体字体渲染简体字） | 映射到 `Microsoft YaHei`（简体字形正确） |

**这些差异都不影响几何位置**：图上任何一个点、任何一条路幅边界的位置与 QGIS
逐要素一致（同一坐标系、同一投影、同一要素）。差异只在"字怎么摆、图标长什么样"。

精度如何自证
------------
`--check` 会打印一组**可核验的数字**（不是"看起来对"）：

* `bounds_roundtrip_max_err_m` —— 世界→像素→世界 的往返误差（应 ≈ 0）；
* `pavement_width` —— 抽样路面多边形的 `面积 ÷ 长度` 与属性 `Width` 的相对误差
  （证明画的是**真实路幅**，不是固定线宽）；
* `scalebar` —— 比例尺分段长度 ÷ 米数 与图面比例是否一致；
* `labels` —— 各层标注"放上去 / 因避让丢弃"的条数；
* `rules_unparsed` / `degraded` —— 样式里**没能复现**的部分（必须为 0 或已被说明）。

用法
----
```bash
# 无 QGIS 也能跑（本脚本**从不探测、也从不启动 QGIS**）
python -X utf8 scripts/city_svg_map.py \
    --carto "<Carto导出目录>" --out plan.png --size 2000 \
    --bounds 1150,4900,10150,14000 \
    --title "北渡区 · 繁荣路走廊" --interval "繁荣路:3650:4210"

# 同时出矢量图（排版/放大用；零依赖手写 SVG）
python -X utf8 scripts/city_svg_map.py --out plan.png --svg plan.svg --size 3000

# 出图并打印精度自证
python -X utf8 scripts/city_svg_map.py --out plan.png --check
```

推荐的两种图层顺序（`--layers` **第一项在最上面**）
--------------------------------------------------
```bash
# ① 与 carto_qgis_map.py 的默认完全一致（分区在最上；公交线路在最下，会被路面盖住）
--layers Zoning_Boundary,Building_Boundary,Network_Boundary,Network_Centerline,\
POI_Location,Route_Centerline,Area_Boundary

# ② 诊断推荐：线路 → 站点 → 路名 → 路网 → 分区 → 建筑
#    （把公交/轨道和路网压在最上层，分区与建筑当底图；路名标注本来就最后画）
--layers Route_Centerline,POI_Location,Network_Centerline,Network_Boundary,\
Zoning_Boundary,Building_Boundary,Area_Boundary
```
顺序 ① 是"与 QGIS 路径逐像素对齐"，顺序 ② 是"信息都看得见"。
**两者都只是画序，不影响任何坐标。**
"""

import argparse
import json
import math
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

try:                                     # Pillow 是唯一第三方依赖（numpy 都不需要）
    from PIL import Image as _Image, ImageDraw as _ImageDraw, ImageFont as _ImageFont
except ImportError:                      # pragma: no cover
    _Image = _ImageDraw = _ImageFont = None

from core import qgis_common as QC          # noqa: E402  （只用样式命名）
from core import qml_style as QS            # noqa: E402

#: 点 → 毫米。`.qml` 的 `fontSizeUnit="Point"` 是**纸面点**，1 pt = 25.4/72 mm。
#: ⚠️ 别写成 72/25.4（那是"每毫米多少点"）—— 曾因此把所有文字放大 8 倍。
PT_TO_MM = 25.4 / 72.0

#: 图层键 → 图例里的中文名（与 `carto_qgis_map.py` 的 `LAYER_LABELS` **保持一致**）
LAYER_LABELS = {
    "Zoning_Boundary": "分区用途",
    "Building_Boundary": "建筑",
    "Network_Boundary": "道路（真实路幅）",
    "Network_Centerline": "路名标注",
    "POI_Location": "站点与设施",
    "Route_Centerline": "公交 / 轨道线路",
    "Area_Boundary": "行政区",
}

#: `carto_reader` 的图层键（`CartoData.LAYERS` 的键）
READER_KEY = {
    "Zoning_Boundary": "zoning",
    "Building_Boundary": "buildings",
    "Network_Boundary": "road_boundary",
    "Network_Centerline": "roads",
    "POI_Location": "pois",
    "Route_Centerline": "routes",
    "Area_Boundary": "areas",
}

#: QGIS 字体族 → Windows 字体文件（粗体/常规）。查不到就用默认。
_FONT_MAP = (
    (("jhenghei", "yahei", "msyh", "heiti", "simhei"), ("msyh.ttc", "msyhbd.ttc")),
    (("simsun", "song", "nsimsun"), ("simsun.ttc", "simsun.ttc")),
    (("arial", "helvetica", "sans"), ("arial.ttf", "arialbd.ttf")),
    (("times", "serif"), ("times.ttf", "timesbd.ttf")),
)


# ====================================================================== 画布

class Projector(object):
    """本地米制 → 像素。

    ⚠️ 与 `city_map.py` 的 `Mapper` 有一处**有意的不同**：这里把请求范围
    **按画框长宽比扩张**（QGIS `zoomToExtent` 就是这么做的），因此
    ① 图面不留信箱边；② 比例尺分母只有一个值，标注的比例尺过滤才可判定。
    """

    def __init__(self, bounds, frame, px_per_mm):
        x0, y0, x1, y1 = bounds
        fx, fy, fw, fh = frame
        bw = max(1e-6, x1 - x0)
        bh = max(1e-6, y1 - y0)
        # 扩张到画框长宽比
        if bw / bh < fw / fh:
            need = bh * fw / fh
            cx = (x0 + x1) / 2.0
            x0, x1 = cx - need / 2.0, cx + need / 2.0
        else:
            need = bw * fh / fw
            cy = (y0 + y1) / 2.0
            y0, y1 = cy - need / 2.0, cy + need / 2.0
        self.bounds = (x0, y0, x1, y1)
        self.frame = frame
        self.fx, self.fy, self.fw, self.fh = frame
        self.scale = fw / (x1 - x0)                 # px / m
        self.px_per_mm = px_per_mm

    def px(self, x, y):
        return (self.fx + (x - self.bounds[0]) * self.scale,
                self.fy + (self.bounds[3] - y) * self.scale)

    def px_many(self, pts):
        fx, fy = self.fx, self.fy
        x0, y1, s = self.bounds[0], self.bounds[3], self.scale
        return [(fx + (x - x0) * s, fy + (y1 - y) * s) for x, y in pts]

    def inv(self, px, py):
        return (self.bounds[0] + (px - self.fx) / self.scale,
                self.bounds[3] - (py - self.fy) / self.scale)

    def mm(self, v):
        return v * self.px_per_mm

    def pt(self, v):
        return v * PT_TO_MM * self.px_per_mm

    def denom(self):
        """本图比例尺分母（= 每毫米多少米 × 1000）。"""
        mm_width = self.fw / self.px_per_mm
        return (self.bounds[2] - self.bounds[0]) / mm_width * 1000.0


class Fonts(object):
    """字体缓存 + QGIS 字体族映射。两个画布共用，保证**量出来的尺寸一致**。"""

    def __init__(self, bold_default=True):
        self._cache = {}
        self.bold_default = bold_default
        self.dir = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")

    def _file(self, family, bold):
        fam = (family or "").lower()
        for keys, (reg, boldf) in _FONT_MAP:
            if any(k in fam for k in keys):
                want = boldf if bold else reg
                if want and os.path.exists(os.path.join(self.dir, want)):
                    return os.path.join(self.dir, want)
                if reg and os.path.exists(os.path.join(self.dir, reg)):
                    return os.path.join(self.dir, reg)
        # QGIS 默认字体在本机不存在（例如 Microsoft JhengHei UI 渲染简体字会缺字），
        # 统一退回 Microsoft YaHei：**简体字形正确**，这是有意的改进。
        for cand in (("msyhbd.ttc" if bold else "msyh.ttc"), "msyh.ttc", "simhei.ttf",
                     "arial.ttf"):
            p = os.path.join(self.dir, cand)
            if os.path.exists(p):
                return p
        return None

    def get(self, family, size_px, bold=False):
        size = max(5, int(round(size_px)))
        key = (family or "", size, bool(bold))
        f = self._cache.get(key)
        if f is None:
            path = self._file(family, bold)
            try:
                f = _ImageFont.truetype(path, size) if path else _ImageFont.load_default()
            except (OSError, ValueError):
                f = _ImageFont.load_default()
            self._cache[key] = f
        return f

    def measure(self, s, family, size_px, bold=False):
        """返回 `(宽, 高, 左偏移, 上偏移)`（像素）。"""
        if not s:
            return (0.0, 0.0, 0.0, 0.0)
        f = self.get(family, size_px, bold)
        try:
            x0, y0, x1, y1 = f.getbbox(s)
        except (AttributeError, TypeError):
            x0, y0, x1, y1 = 0, 0, len(s) * size_px * 0.6, size_px
        return (x1 - x0, y1 - y0, x0, y0)


class RasterCanvas(object):
    """Pillow 后端。所有坐标都是像素、浮点。"""

    def __init__(self, width, height, bg, fonts):
        self.w = int(width)
        self.h = int(height)
        self.img = _Image.new("RGBA", (self.w, self.h), tuple(bg) + (255,))
        self.fonts = fonts
        self.stats = defaultdict(int)
        self._base = self.img
        self._clip = None

    # --- 图廓裁剪：地图内容必须止于内图廓（否则会压到版面上的文字）---
    def begin_clip(self, rect):
        self._clip = tuple(int(round(v)) for v in rect)
        self._layer = _Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        self.img = self._layer

    def end_clip(self):
        if self._clip is None:
            return
        x0, y0, x1, y1 = self._clip
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(self.w, x1), min(self.h, y1)
        self.img = self._base
        if x1 > x0 and y1 > y0:
            region = self._layer.crop((x0, y0, x1, y1))
            self.img.paste(region, (x0, y0), region)
        self._layer = None
        self._clip = None

    # --- 面 ---
    def polygon(self, rings, fill=None, outline=None, width_px=0.0, hatch=None):
        rings = [r for r in rings if len(r) >= 3]
        if not rings:
            return
        if fill and fill[3] > 0:
            if len(rings) == 1:
                _ImageDraw.Draw(self.img).polygon(rings[0], fill=fill)
            else:
                m = _Image.new("L", (self.w, self.h), 0)
                md = _ImageDraw.Draw(m)
                md.polygon(rings[0], fill=255)
                for hole in rings[1:]:
                    md.polygon(hole, fill=0)
                self.img.paste(fill, (0, 0), m)
        if hatch:
            self._hatch(rings, hatch)
        if outline and outline[3] > 0 and width_px > 0:
            d = _ImageDraw.Draw(self.img)
            wpx = max(1, int(round(width_px)))
            for r in rings:
                d.line(list(r) + [r[0]], fill=outline, width=wpx, joint="curve")

    def _hatch(self, rings, spec):
        color, spacing_px, width_px, angle = spec
        if color[3] <= 0 or spacing_px <= 1:
            return
        m = _Image.new("L", (self.w, self.h), 0)
        md = _ImageDraw.Draw(m)
        md.polygon(rings[0], fill=255)
        for hole in rings[1:]:
            md.polygon(hole, fill=0)
        layer = _Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        ld = _ImageDraw.Draw(layer)
        ca = math.cos(math.radians(angle))
        sa = math.sin(math.radians(angle))
        nx, ny = -sa, ca                     # 垂直于斜线方向
        cx, cy = self.w / 2.0, self.h / 2.0
        diag = math.hypot(self.w, self.h)
        n = int(diag / spacing_px) + 2
        wpx = max(1, int(round(width_px)))
        for i in range(-n, n + 1):
            off = i * spacing_px
            x1, y1 = cx + nx * off - ca * diag, cy + ny * off - sa * diag
            x2, y2 = cx + nx * off + ca * diag, cy + ny * off + sa * diag
            ld.line([(x1, y1), (x2, y2)], fill=color, width=wpx)
        layer.putalpha(_Image.eval(layer.getchannel("A"), lambda v: v))
        layer = _Image.composite(layer, _Image.new("RGBA", layer.size, (0, 0, 0, 0)), m)
        self.img.alpha_composite(layer)

    # --- 线 ---
    def line(self, pts, color, width_px, dash=None):
        if color is None or color[3] <= 0 or len(pts) < 2:
            return
        d = _ImageDraw.Draw(self.img)
        wpx = max(1, int(round(width_px)))
        if dash:
            for seg in _dash_polyline(pts, dash[0], dash[1]):
                d.line(seg, fill=color, width=wpx, joint="curve")
            return
        d.line(list(pts), fill=color, width=wpx, joint="curve")

    # --- 点 / 矩形 ---
    def circle(self, x, y, r, fill=None, outline=None, width_px=0.0):
        d = _ImageDraw.Draw(self.img)
        box = [x - r, y - r, x + r, y + r]
        wpx = max(1, int(round(width_px))) if (outline and width_px > 0) else 0
        d.ellipse(box, fill=fill, outline=outline if wpx else None, width=wpx)

    def rect(self, x0, y0, x1, y1, fill=None, outline=None, width_px=1.0):
        d = _ImageDraw.Draw(self.img)
        wpx = max(1, int(round(width_px))) if outline else 0
        d.rectangle([min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)],
                    fill=fill, outline=outline if wpx else None, width=wpx)

    # --- 文字 ---
    def text(self, x, y, s, size_px, color, family="", bold=False, anchor="mm",
             angle=0.0, buffer_color=None, buffer_px=0.0):
        if not s:
            return None
        w, h, ox, oy = self.fonts.measure(s, family, size_px, bold)
        pad = int(math.ceil(buffer_px)) + 2
        tw, th = int(math.ceil(w)) + 2 * pad, int(math.ceil(h)) + 2 * pad
        if tw <= 0 or th <= 0:
            return None
        tmp = _Image.new("RGBA", (tw, th), (0, 0, 0, 0))
        td = _ImageDraw.Draw(tmp)
        td.text((pad - ox, pad - oy), s, font=self.fonts.get(family, size_px, bold),
                fill=color,
                stroke_width=int(round(buffer_px)) if (buffer_color and buffer_px > 0) else 0,
                stroke_fill=buffer_color if (buffer_color and buffer_px > 0) else None)
        if abs(angle) > 0.01:
            tmp = tmp.rotate(angle, expand=True, resample=_Image.BICUBIC)
        ax, ay = _anchor_offset(anchor, tmp.width, tmp.height)
        bx, by = int(round(x - ax)), int(round(y - ay))
        self.img.alpha_composite(tmp, (bx, by))
        return (bx, by, bx + tmp.width, by + tmp.height)

    def save(self, path, bg=None):
        out = self.img
        if bg is not None:
            base = _Image.new("RGB", out.size, tuple(bg)[:3])
            base.paste(out, (0, 0), out)
            out = base
        elif out.mode == "RGBA":
            out = out.convert("RGB")
        ext = os.path.splitext(path)[1].lower()
        if ext in (".jpg", ".jpeg"):
            out.convert("RGB").save(path, quality=92)
        else:
            out.save(path)
        return out.size


def _anchor_offset(anchor, w, h):
    ax = {"l": 0.0, "m": w / 2.0, "r": float(w)}.get(anchor[0], w / 2.0)
    ay = {"t": 0.0, "m": h / 2.0, "b": float(h)}.get(anchor[1], h / 2.0)
    return ax, ay


def _dash_polyline(pts, on_px, off_px):
    """把折线切成虚线段（返回 `[[(x,y),...], ...]`）。"""
    out = []
    cur = []
    on = True
    remain = on_px
    for i in range(1, len(pts)):
        x1, y1 = pts[i - 1]
        x2, y2 = pts[i]
        seg = math.hypot(x2 - x1, y2 - y1)
        if seg <= 0:
            continue
        t = 0.0
        while t < seg - 1e-9:
            step = min(remain, seg - t)
            t2 = t + step
            a = (x1 + (x2 - x1) * t / seg, y1 + (y2 - y1) * t / seg)
            b = (x1 + (x2 - x1) * t2 / seg, y1 + (y2 - y1) * t2 / seg)
            if on:
                if not cur:
                    cur = [a]
                cur.append(b)
            else:
                if len(cur) > 1:
                    out.append(cur)
                cur = []
            remain -= step
            t = t2
            if remain <= 1e-9:
                on = not on
                remain = on_px if on else off_px
    if len(cur) > 1:
        out.append(cur)
    return out


class SvgCanvas(object):
    """手写 SVG 后端（零依赖）。产出的是**真矢量**，放大不糊、可直接进排版。"""

    def __init__(self, width, height, bg, fonts):
        self.w = float(width)
        self.h = float(height)
        self.bg = tuple(bg)[:3]
        self.fonts = fonts
        self.parts = []
        self.defs = []
        self._pat = {}
        self._clip = None
        self._clip_paths = []
        self.stats = defaultdict(int)

    # --- 图廓裁剪（矢量版用 clipPath，语义与位图版一致）---
    def begin_clip(self, rect):
        self._clip = tuple(round(float(v), 2) for v in rect)
        pid = "mapclip%d" % (len(self._clip_paths) + 1)
        self._clip_paths.append(pid)
        x0, y0, x1, y1 = self._clip
        self.defs.append('<clipPath id="%s"><rect x="%.2f" y="%.2f" width="%.2f" '
                         'height="%.2f"/></clipPath>' % (pid, x0, y0, x1 - x0, y1 - y0))
        self.parts.append('<g clip-path="url(#%s)">' % pid)

    def end_clip(self):
        if self._clip is None:
            return
        self.parts.append("</g>")
        self._clip = None

    # --- 工具 ---
    @staticmethod
    def _c(rgba):
        if rgba is None:
            return "none"
        r, g, b = rgba[0], rgba[1], rgba[2]
        a = rgba[3] / 255.0 if len(rgba) > 3 else 1.0
        if a >= 0.999:
            return "#%02x%02x%02x" % (r, g, b)
        return "rgba(%d,%d,%d,%.3f)" % (r, g, b, a)

    @staticmethod
    def _d(rings):
        out = []
        for r in rings:
            if len(r) < 3:
                continue
            out.append("M" + " L".join("%.2f %.2f" % (p[0], p[1]) for p in r) + " Z")
        return " ".join(out)

    def _hatch_pattern(self, color, spacing_px, width_px, angle):
        key = (color, round(spacing_px, 2), round(width_px, 2), round(angle, 1))
        pid = self._pat.get(key)
        if pid:
            return pid
        pid = "h%d" % (len(self._pat) + 1)
        self._pat[key] = pid
        size = max(4.0, spacing_px)
        self.defs.append(
            '<pattern id="%s" patternUnits="userSpaceOnUse" width="%.2f" height="%.2f" '
            'patternTransform="rotate(%.1f)">'
            '<line x1="0" y1="0" x2="0" y2="%.2f" stroke="%s" stroke-width="%.2f"/></pattern>'
            % (pid, size, size, angle, size, self._c(color), max(0.3, width_px)))
        return pid

    # --- 面 ---
    def polygon(self, rings, fill=None, outline=None, width_px=0.0, hatch=None):
        rings = [r for r in rings if len(r) >= 3]
        if not rings:
            return
        d = self._d(rings)
        if not d:
            return
        paints = []
        if hatch:
            paints.append('fill="url(#%s)"' % self._hatch_pattern(*hatch))
        elif fill and fill[3] > 0:
            paints.append('fill="%s"' % self._c(fill))
        else:
            paints.append('fill="none"')
        if outline and outline[3] > 0 and width_px > 0:
            paints.append('stroke="%s" stroke-width="%.2f" stroke-linejoin="round"'
                          % (self._c(outline), width_px))
        else:
            paints.append('stroke="none"')
        self.parts.append('<path d="%s" fill-rule="evenodd" %s/>' % (d, " ".join(paints)))

    # --- 线 ---
    def line(self, pts, color, width_px, dash=None):
        if color is None or color[3] <= 0 or len(pts) < 2:
            return
        d = "M" + " L".join("%.2f %.2f" % (p[0], p[1]) for p in pts)
        extra = ""
        if dash:
            extra = ' stroke-dasharray="%.2f %.2f"' % (dash[0], dash[1])
        self.parts.append(
            '<path d="%s" fill="none" stroke="%s" stroke-width="%.2f" '
            'stroke-linejoin="round" stroke-linecap="round"%s/>'
            % (d, self._c(color), max(0.3, width_px), extra))

    # --- 点 / 矩形 ---
    def circle(self, x, y, r, fill=None, outline=None, width_px=0.0):
        self.parts.append('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="%s" stroke="%s" '
                          'stroke-width="%.2f"/>'
                          % (x, y, r, self._c(fill), self._c(outline), max(0.0, width_px)))

    def rect(self, x0, y0, x1, y1, fill=None, outline=None, width_px=1.0):
        x, y = min(x0, x1), min(y0, y1)
        w, h = abs(x1 - x0), abs(y1 - y0)
        self.parts.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" '
                          'fill="%s" stroke="%s" stroke-width="%.2f"/>'
                          % (x, y, w, h, self._c(fill), self._c(outline), max(0.0, width_px)))

    # --- 文字 ---
    def text(self, x, y, s, size_px, color, family="", bold=False, anchor="mm",
             angle=0.0, buffer_color=None, buffer_px=0.0):
        if not s:
            return None
        esc = (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
        ax = {"l": "start", "m": "middle", "r": "end"}.get(anchor[0], "middle")
        base = {"t": "hanging", "m": "central", "b": "text-after-edge"}.get(anchor[1], "central")
        stroke = ""
        if buffer_color and buffer_px > 0:
            stroke = (' stroke="%s" stroke-width="%.2f" paint-order="stroke" '
                      'stroke-linejoin="round"' % (self._c(buffer_color), buffer_px * 2))
        tr = (' transform="rotate(%.2f %.2f %.2f)"' % (angle, x, y)) if abs(angle) > 0.01 else ""
        self.parts.append(
            '<text x="%.2f" y="%.2f" font-size="%.2f" font-family="%s" '
            'font-weight="%s" fill="%s" text-anchor="%s" dominant-baseline="%s"%s%s>%s</text>'
            % (x, y, max(1.0, size_px),
               (family or "sans-serif").replace('"', ""),
               "bold" if bold else "normal", self._c(color), ax, base, stroke, tr, esc))
        w, h, _ox, _oy = self.fonts.measure(s, family, size_px, bold)
        return (x - w / 2.0, y - h / 2.0, x + w / 2.0, y + h / 2.0)

    def save(self, path, bg=None):
        head = ('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<svg xmlns="http://www.w3.org/2000/svg" width="%.0f" height="%.0f" '
                'viewBox="0 0 %.0f %.0f">\n' % (self.w, self.h, self.w, self.h))
        body = ['<rect x="0" y="0" width="%.0f" height="%.0f" fill="#%02x%02x%02x"/>'
                % (self.w, self.h, self.bg[0], self.bg[1], self.bg[2])]
        defs = ("<defs>%s</defs>" % "".join(self.defs)) if self.defs else ""
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(head + defs + "\n" + "\n".join(body + self.parts) + "\n</svg>\n")
        return (int(self.w), int(self.h))


class LabelPlacer(object):
    """标注避让（QGIS `overlapHandling=PreventOverlap` 的贪心近似）。

    网格索引：只与前若干个格子里的框比较，避免 O(n²)。
    `region` 限定可放置范围（= 内图廓）：越界的框直接拒掉，
    否则标注会被图廓裁成半个字。
    """

    def __init__(self, width, height, cell=64.0, margin=1.0, region=None):
        self.w = width
        self.h = height
        self.cell = cell
        self.margin = margin
        self.region = region or (0.0, 0.0, float(width), float(height))
        self.boxes = []
        self.grid = defaultdict(list)

    def _keys(self, box):
        x0, y0, x1, y1 = box
        for cx in range(int(x0 // self.cell), int(x1 // self.cell) + 1):
            for cy in range(int(y0 // self.cell), int(y1 // self.cell) + 1):
                yield (cx, cy)

    def hits(self, box):
        for k in self._keys(box):
            for i in self.grid.get(k, ()):
                b = self.boxes[i]
                if box[0] < b[2] and b[0] < box[2] and box[1] < b[3] and b[1] < box[3]:
                    return True
        return False

    def add(self, box):
        m = self.margin
        box = (box[0] - m, box[1] - m, box[2] + m, box[3] + m)
        i = len(self.boxes)
        self.boxes.append(box)
        for k in self._keys(box):
            self.grid[k].append(i)

    def try_add(self, box):
        """放得下 → 登记并返回 True；被占 / 越出内图廓 → False。"""
        rx0, ry0, rx1, ry1 = self.region
        if (box[0] < rx0 or box[1] < ry0 or box[2] > rx1 or box[3] > ry1
                or box[0] < 0 or box[1] < 0 or box[2] > self.w or box[3] > self.h):
            return False
        if self.hits(box):
            return False
        self.add(box)
        return True


# ====================================================================== 渲染

class Renderer(object):
    def __init__(self, cart, style_dir, args, canvas, proj, layout=None):
        self.cart = cart
        self.style_dir = style_dir
        self.args = args
        self.cv = canvas
        self.pj = proj
        self.layout = layout or {}
        self.styles = {}
        self.used = defaultdict(int)       # id(rule|category) → 命中要素数（图例据此反推）
        self._rule_cache = {}              # (图层, 属性快照) → rule（省掉重复的正则匹配）
        self.stats = {
            "layers": {},
            "rules_unparsed": [],
            "degraded": [],
            "labels": {},
        }
        self.placer = LabelPlacer(
            canvas.w, canvas.h,
            region=_frame_region(self.layout.get("map_frame"), canvas.w, canvas.h))
        self.view = proj.bounds
        # ⚠️ **先占住版面家具的位置**：图例/比例尺/指北针是最后画的，
        # 若不预留，标注会被它们压住（实测比例尺刻度与 POI 名叠在一起）。
        self._reserve_furniture()

    def _reserve_furniture(self):
        mf = self.layout.get("map_frame")
        if not mf:
            return
        if not self.args.no_scalebar:
            g = self._scalebar_geom(mf)
            self.placer.add((g["x"] - 4, g["y"] - g["label_h"] - 4,
                             g["x"] + g["total_px"] + 4, g["y"] + g["bar_h"] + 4))
        if self.args.north:
            mx, my, mw, _mh = mf
            cx, cy, r = mx + mw - 26, my + 26, 12.0
            self.placer.add((cx - r - 6, cy - r - 6, cx + r + 6, cy + r + 16))
        if self.args.title:
            self.placer.add((0, 0, self.cv.w, self.layout.get("title_cy", 0) * 2))

    # --- 样式 ---
    def style(self, key):
        if key not in self.styles:
            st = QS.load_layer(self.style_dir, self.args.style_set, key)
            self.styles[key] = st
            if st is not None:
                for f, e in st.unparsed:
                    self.stats["rules_unparsed"].append({"layer": key, "filter": f, "error": e})
                for d in sorted(st.degraded):
                    self.stats["degraded"].append({"layer": key, "symbol_layer": d})
        return self.styles[key]

    def resolve(self, key, attrs):
        """属性 → `(rule, symbol)`。带记忆化：分区层有 3.5 万个要素，逐要素跑正则太浪费。"""
        st = self.style(key)
        if st is None:
            return (None, None)
        if st.renderer == "categorizedSymbol":
            cat = st.category_for(attrs)
            return (cat, st.symbols.get(cat.symbol) if cat is not None else None)
        denom = self.pj.denom()
        ck = (key, denom, tuple(sorted((str(k), str(v)) for k, v in attrs.items())))
        hit = self._rule_cache.get(ck)
        if hit is None:
            rule = st.rule_for(attrs, denom)
            hit = (rule, st.symbols.get(rule.symbol) if rule is not None else None)
            self._rule_cache[ck] = hit
        return hit

    def mark(self, layer_key, rule, sym):
        """登记"这条规则真的画到了东西" —— 图例据此反推，不用猜、也不抄样式文件。"""
        if rule is None or sym is None:
            return
        self.used[id(rule)] += 1

    def legend_items(self, key):
        """该层**本次真正画出来**的图例条目：`[(标签, kind, rgba, width_mm)]`，按文件顺序。"""
        st = self.styles.get(key)
        if st is None:
            return []
        seq = st.categories if st.renderer == "categorizedSymbol" else st.rules
        out = []
        for rule in seq:
            if not self.used.get(id(rule)):
                continue
            kind, col, w = QS.primary_style(st.symbols.get(getattr(rule, "symbol", None)))
            if col is None:
                continue
            label = getattr(rule, "label", None) or getattr(rule, "value", "") \
                or getattr(rule, "group", "")
            if not label:
                continue
            out.append((label, kind, col, w))
        return out

    # --- 通用：按 QML 规则画一层面 ---
    def _draw_polygon_layer(self, key, feats):
        st = self.style(key)
        n_drawn = 0
        n_cull = 0
        if st is None:
            self.stats["layers"][key] = {"drawn": 0, "no_style": True}
            return 0
        vx0, vy0, vx1, vy1 = self.view
        for f in feats:
            bb = f.bbox
            if bb[2] < vx0 or bb[0] > vx1 or bb[3] < vy0 or bb[1] > vy1:
                n_cull += 1
                continue
            rule, sym = self.resolve(key, f.attrs)
            if sym is None:
                continue
            rings = f.parts if f.parts and isinstance(f.parts[0], list) else [f.parts]
            pxy = [self.pj.px_many(r) for r in rings]
            for sl in sym.by_pass():
                if not sl.enabled:
                    continue
                if sl.cls == "SimpleFill":
                    self.cv.polygon(pxy, fill=sl.fill_rgba, outline=sl.outline_rgba,
                                    width_px=self.pj.mm(sl.width_mm))
                elif sl.cls == "LinePatternFill":
                    col = QS.parse_color(sl.opts.get("color")) or sl.fill_rgba
                    self.cv.polygon(
                        pxy, fill=None,
                        hatch=(col, max(2.0, self.pj.mm(_num(sl.opts.get("distance"), 2.0))),
                               max(0.6, self.pj.mm(sl.width_mm)),
                               _num(sl.opts.get("angle"), 45.0)))
                elif sl.cls == "SimpleLine":
                    col = sl.stroke_rgba
                    if col is None:
                        continue
                    dash = sl.dash
                    dash_px = (self.pj.mm(dash[0]), self.pj.mm(dash[1])) if dash else None
                    wpx = max(0.4, self.pj.mm(sl.width_mm))
                    for r in pxy:
                        self.cv.line(list(r) + [r[0]], col, wpx, dash_px)
            self.mark(key, rule, sym)
            n_drawn += 1
        self.stats["layers"][key] = {"drawn": n_drawn, "culled": n_cull}
        return n_drawn

    # --- 分区（底色）---
    def layer_zoning(self):
        return self._draw_polygon_layer("Zoning_Boundary", self.cart.layer("zoning"))

    # --- 建筑 ---
    def layer_buildings(self):
        return self._draw_polygon_layer("Building_Boundary", self.cart.layer("buildings"))

    # --- 真实路幅（含水域：Waterway 也是这一层的一个分类）---
    def layer_road_boundary(self):
        return self._draw_polygon_layer("Network_Boundary", self.cart.layer("road_boundary"))

    # --- 行政区 ---
    def layer_area(self):
        return self._draw_polygon_layer("Area_Boundary", self.cart.layer("areas"))

    # --- 公交 / 轨道线路（SimpleLine，带白色外晕）---
    def layer_routes(self):
        n = 0
        if self.style("Route_Centerline") is None:
            return 0
        for f in self.cart.layer("routes"):
            if not _bbox_in(f.bbox, self.view):
                continue
            rule, sym = self.resolve("Route_Centerline", f.attrs)
            if sym is None:
                continue
            parts = f.parts if f.parts and isinstance(f.parts[0], list) else [f.parts]
            pxy = [self.pj.px_many(p) for p in parts if len(p) >= 2]
            for sl in sym.by_pass():
                if not sl.enabled or sl.cls != "SimpleLine":
                    continue
                col = sl.stroke_rgba
                if col is None:
                    continue
                dash = sl.dash
                dash_px = (self.pj.mm(dash[0]), self.pj.mm(dash[1])) if dash else None
                wpx = max(0.6, self.pj.mm(sl.width_mm))
                for p in pxy:
                    self.cv.line(p, col, wpx, dash_px)
            self.mark("Route_Centerline", rule, sym)
            n += 1
        self.stats["layers"]["Route_Centerline"] = {"drawn": n}
        return n

    # --- POI 圆点（SvgMarker / FontMarker 无法复现 → 同色圆点）---
    def layer_pois(self):
        n = 0
        if self.style("POI_Location") is None:
            return 0
        fallback = 0
        for f in self.cart.layer("pois"):
            if not _bbox_in(f.bbox, self.view):
                continue
            rule, sym = self.resolve("POI_Location", f.attrs)
            if sym is None:
                continue
            x, y = f.compute_centroid()
            px, py = self.pj.px(x, y)
            drew = False
            for sl in sym.by_pass():
                if not sl.enabled:
                    continue
                if sl.cls == "SimpleMarker":
                    col = sl.fill_rgba
                    r = max(1.2, self.pj.mm(sl.size_mm) / 2.0)
                    self.cv.circle(px, py, r, fill=col, outline=sl.outline_rgba,
                                   width_px=self.pj.mm(sl.width_mm))
                    drew = True
                elif sl.cls == "SimpleFill":
                    col = sl.fill_rgba
                    if col is not None:
                        self.cv.circle(px, py, 2.2, fill=col)
                        drew = True
            if not drew:
                # SvgMarker / FontMarker：取它的 fill / color 当圆点色
                col = None
                for sl in sym.by_pass():
                    col = QS.parse_color(sl.opts.get("fill") or sl.opts.get("color"))
                    if col is not None and col[3] > 0:
                        break
                col = col or (120, 120, 120, 255)
                self.cv.circle(px, py, 2.4, fill=col, outline=(60, 60, 60, 180), width_px=0.6)
                fallback += 1
            self.mark("POI_Location", rule, sym)
            n += 1
        self.stats["layers"]["POI_Location"] = {"drawn": n, "approx_marker": fallback}
        return n

    # --- 标注 ---
    def layer_labels(self, poi=True, roads=True):
        """路名 + POI 名。**在所有几何之后画**，因此标注永远在最上层。"""
        if self.args.no_labels:
            return
        denom = self.pj.denom()
        jobs = []
        if roads:
            jobs += self._road_label_jobs(denom)
        if poi:
            jobs += self._poi_label_jobs(denom)
        # 优先级大的先放（QGIS 里 priority 越大越优先）
        jobs.sort(key=lambda j: -j[0])
        placed = defaultdict(int)
        dropped = defaultdict(int)
        for prio, kind, name, anchor, lr in jobs:
            box = self._place_label(kind, name, anchor, lr)
            if box is None:
                dropped[kind] += 1
            else:
                placed[kind] += 1
        self.stats["labels"]["roads"] = {"placed": placed["roads"], "dropped": dropped["roads"]}
        self.stats["labels"]["poi"] = {"placed": placed["poi"], "dropped": dropped["poi"]}

    def _poi_label_jobs(self, denom):
        """POI 标注候选：`(优先级, "poi", 名字, 像素坐标, 规则)`。"""
        st = self.style("POI_Location")
        out = []
        if st is None or not st.labels:
            return out
        for f in self.cart.layer("pois"):
            if not _bbox_in(f.bbox, self.view):
                continue
            name = f.attrs.get("Name")
            if not name:
                continue
            lr = st.label_rule_for(f.attrs, denom)
            if lr is None or lr.text is None:
                continue
            out.append((lr.priority or 5.0, "poi", name, self.pj.px(*f.compute_centroid()), lr))
        return out

    def _road_label_jobs(self, denom):
        """路名标注候选：**先按路名把路段串成连通段**，再在可见折线上均匀布点。

        ⚠️ 为什么要串：`Network_Centerline` 是**按路段**导出的，一条路几十段，
        单段往往短于一个路名（本项目实测 1:60000 下 480 条候选全部因"放不下"被丢）。
        用 `core/roads.group_runs` 串成连通段之后，长路才拿得到标注 ——
        这也正是报告里"沿线里程"用的同一套口径，图与表因此对得上。
        """
        st = self.style("Network_Centerline")
        out = []
        if st is None or not st.labels:
            return out
        groups = defaultdict(list)
        for f in self.cart.layer("roads"):
            if not _bbox_in(f.bbox, self.view):
                continue
            name = f.attrs.get("Name")
            if not name:
                continue
            lr = st.label_rule_for(f.attrs, denom)
            if lr is None or lr.text is None:
                continue
            parts = f.parts if f.parts and isinstance(f.parts[0], list) else [f.parts]
            groups[(name, id(lr))].append((f, [list(p) for p in parts if len(p) >= 2], lr))
        from core import roads as R
        for (name, _k), items in groups.items():
            lr = items[0][2]
            ts = lr.text
            size_px = self.pj.pt(ts.size_pt)
            w, _h, _ox, _oy = self.cv.fonts.measure(name, ts.family, size_px, ts.bold)
            if w <= 0:
                continue
            segs = [(f, pts[0]) for f, pts, _lr in items if pts]
            try:
                runs = R.group_runs(segs)
            except Exception:                                 # noqa: BLE001
                runs = [pts for _f, pts, _lr in items if pts]
            for run in runs:
                for piece in _visible_pieces(run, self.view):
                    q = self.pj.px_many(piece)
                    Lpx = _plen(q)
                    if Lpx < w + 8:
                        continue
                    # 沿可见段均匀放 1–3 个（间距不小于 300 m）
                    spacing_m = max(300.0, 3.0 * w / max(1e-9, self.pj.scale))
                    n = max(1, min(3, int(Lpx // max(1.0, spacing_m * self.pj.scale)) + 1))
                    for i in range(n):
                        d = Lpx * (i + 0.5) / n
                        mid, ang = _point_angle_at(q, d)
                        out.append((lr.priority or 5.0, "roads", name, (mid, _upright(ang)), lr))
        return out

    def _place_label(self, kind, name, anchor, lr):
        ts = lr.text
        size_px = self.pj.pt(ts.size_pt)
        bold = ts.bold
        buf_px = self.pj.mm(lr.buffer.size_mm) if (lr.buffer and lr.buffer.draw) else 0.0
        buf_col = lr.buffer.color if lr.buffer else None
        w, h, _ox, _oy = self.cv.fonts.measure(name, ts.family, size_px, bold)
        pad = buf_px + 1.0
        if kind == "poi":
            px, py = anchor
            # 右侧优先，其次右下 / 左 / 上（QGIS placement=6 是"围绕点"）
            for dx, dy, anc in ((10.0, 0.0, "lm"), (10.0, 12.0, "lm"),
                                (-10.0, 0.0, "rm"), (0.0, -12.0, "mb"), (0.0, 12.0, "mt")):
                left = px + dx - (w if anc[0] == "r" else w / 2.0)
                right = px + dx + (w if anc[0] == "l" else w / 2.0)
                box = (left - pad, py + dy - h / 2 - pad, right + pad, py + dy + h / 2 + pad)
                if self.placer.try_add(box):
                    self.cv.text(px + dx, py + dy, name, size_px, ts.color,
                                 family=ts.family, bold=bold, anchor=anc,
                                 buffer_color=buf_col, buffer_px=buf_px)
                    return box
            return None
        # 路名：沿折线的给定位置 + 切向旋转
        (mx, my), ang = anchor
        box = (mx - w / 2 - pad, my - h / 2 - pad, mx + w / 2 + pad, my + h / 2 + pad)
        if not self.placer.try_add(box):
            return None
        self.cv.text(mx, my, name, size_px, ts.color, family=ts.family,
                     bold=bold, anchor="mm", angle=ang,
                     buffer_color=buf_col, buffer_px=buf_px)
        return box

    # --- 沿线区间高亮（与 QGIS 路径同一套 `core/roads` 口径）---
    def layer_interval(self):
        if not self.args.interval:
            return
        from core import roads as R
        for spec in self.args.interval:
            try:
                nm, s1, s2 = spec.split(":")
                s1, s2 = float(s1), float(s2)
            except ValueError:
                sys.stderr.write("--interval 格式应为 路名:s1:s2，收到 %r\n" % spec)
                continue
            g = R.road_geometry(self.cart, nm)
            if not g.runs:
                sys.stderr.write("找不到路名 %s\n" % nm)
                continue
            run = min(self.args.interval_run, len(g.runs) - 1)
            pts = self.pj.px_many(g.window(s1, s2, run))
            self.cv.line(pts, (255, 80, 0, 255), max(2.0, self.pj.mm(1.2)))
            size_px = self.pj.pt(9.0)
            for s in (s1, s2):
                x, y = g.point_at(run, s)
                px, py = self.pj.px(x, y)
                self.cv.circle(px, py, max(2.5, self.pj.mm(1.1)), fill=(255, 80, 0, 255),
                               outline=(0, 0, 0, 255), width_px=0.8)
                label = "%s s=%.0f m" % (nm, s)
                w, h, _ox, _oy = self.cv.fonts.measure(label, "", size_px, False)
                box = (px + 6, py - h - 6, px + 6 + w + 4, py - 4)
                if self.placer.try_add(box):
                    self.cv.text(px + 8, py - 6, label, size_px, (20, 20, 20, 255),
                                 anchor="lb", buffer_color=(255, 255, 255, 255),
                                 buffer_px=max(1.0, self.pj.mm(0.5)))
            self.stats["layers"]["interval"] = {
                "drawn": 1, "road": nm, "run": run, "s1": s1, "s2": s2,
                "run_length": g.run_length(run),
                "endpoints": [tuple(round(v, 1) for v in g.point_at(run, s)) for s in (s1, s2)]}

    # --- 版面：标题 / 图例 / 比例尺 / 指北针 / 图框 ---
    def furniture(self, layout):
        a = self.args
        cv = self.cv
        mf = layout["map_frame"]
        if a.title:
            cv.text(10, layout["title_cy"], a.title, self.pj.pt(13.0), (20, 20, 20, 255),
                    bold=True, anchor="lm")
        cv.rect(mf[0], mf[1], mf[0] + mf[2], mf[1] + mf[3], fill=None,
                outline=(90, 90, 90, 255), width_px=1.2)
        if not a.no_legend:
            self._legend(layout["legend_frame"])
        if not a.no_scalebar:
            self._scalebar(mf)
        if a.north:
            self._north(mf)
        cv.text(cv.w - 8, cv.h - 4,
                "Carto 官方样式 · 无 QGIS 渲染（city_svg_map.py） 1:%s" % _fmt_denom(self.pj.denom()),
                self.pj.pt(6.0), (130, 130, 130, 255), anchor="rb")

    def _legend(self, frame):
        """图例：**只列真的画出来的**规则（按本次命中统计反推），自上而下与图序一致。"""
        x0, y0, w, h = frame
        cv = self.cv
        cv.rect(x0, y0, x0 + w, y0 + h, fill=(255, 255, 255, 235),
                outline=(150, 150, 150, 255), width_px=1.0)
        head_h = self.pj.pt(12.0) * 1.7
        cv.text(x0 + 8, y0 + head_h * 0.62, "图例", self.pj.pt(11.0), (20, 20, 20, 255),
                bold=True, anchor="lm")
        order = list(self.args.layers)          # 第一项在最上 → 图例也从上往下排
        blocks = []
        for key in order:
            items = self.legend_items(key)
            if not items:
                continue
            blocks.append((LAYER_LABELS.get(key, key), items))
        if not blocks:
            return
        # 先量总高，再决定字号（放不下就缩，绝不溢出 —— QGIS 那版图例会溢出页面）
        for scale in (1.0, 0.9, 0.8, 0.72, 0.64, 0.56):
            fs = self.pj.pt(9.0) * scale
            hfs = self.pj.pt(9.5) * scale
            row = fs * 1.62
            need = 0.0
            for _title, items in blocks:
                need += hfs * 1.85 + len(items) * row + fs * 0.55
            if y0 + head_h + need <= y0 + h - 6:
                break
        yy = y0 + head_h + 2
        cv.line([(x0 + 6, yy - 3), (x0 + w - 6, yy - 3)], (120, 120, 120, 255), 0.8)
        sw = min(20.0, w * 0.14)
        for title, items in blocks:
            cv.text(x0 + 8, yy + hfs * 0.55, title, hfs, (25, 25, 25, 255), bold=True, anchor="lm")
            yy += hfs * 1.85
            for label, kind, col, wid in items:
                self._swatch(x0 + 12, yy, sw, fs * 0.92, kind, col, wid)
                cv.text(x0 + 12 + sw + 7, yy + fs * 0.5, label, fs, (45, 45, 45, 255),
                        anchor="lm")
                yy += row
            yy += fs * 0.55

    def _swatch(self, x, y, w, h, kind, col, wid):
        cv = self.cv
        if kind == "line":
            cv.line([(x, y + h / 2), (x + w, y + h / 2)], col, max(1.5, h * 0.34))
        elif kind == "marker":
            cv.circle(x + w / 2, y + h / 2, max(1.6, h * 0.30), fill=col,
                      outline=(70, 70, 70, 200), width_px=0.6)
        else:
            cv.rect(x, y, x + w, y + h, fill=col,
                    outline=(120, 120, 120, 160) if col[3] < 250 else None, width_px=0.6)

    def _scalebar_geom(self, mf):
        """比例尺的版面几何（单框、2 段、米制；与 QGIS 版同口径）。

        分段长度 = `max(100, round((视野宽/8)/100)*100)` 米 —— 与
        `carto_qgis_map.py` 的 `unitsPerSegment` 算法一致，所以两条路径的读数可比。
        """
        mx, my, mw, mh = mf
        view_w = self.pj.bounds[2] - self.pj.bounds[0]
        seg_m = max(100.0, round((view_w / 8.0) / 100.0) * 100.0)
        seg_px = seg_m * self.pj.scale
        total_px = seg_px * 2
        bar_h = max(6.0, self.pj.mm(3.0))
        fs = self.pj.pt(8.5)
        x1 = mx + mw - 14 - total_px
        y1 = my + mh - 16 - bar_h
        return {"x": x1, "y": y1, "seg_px": seg_px, "total_px": total_px,
                "bar_h": bar_h, "seg_m": seg_m, "fs": fs, "label_h": fs * 1.6}

    def _scalebar(self, mf):
        """白左黑右的单框比例尺 + 三个刻度（0 / 中 / 尾）。"""
        cv = self.cv
        g = self._scalebar_geom(mf)
        x1, y1, seg_px = g["x"], g["y"], g["seg_px"]
        total_px, bar_h, seg_m, fs = g["total_px"], g["bar_h"], g["seg_m"], g["fs"]
        cv.rect(x1, y1, x1 + seg_px, y1 + bar_h, fill=(0, 0, 0, 255),
                outline=(40, 40, 40, 255), width_px=1.0)
        cv.rect(x1 + seg_px, y1, x1 + total_px, y1 + bar_h, fill=(255, 255, 255, 255),
                outline=(40, 40, 40, 255), width_px=1.0)
        for i, v in enumerate((0.0, seg_m, seg_m * 2)):
            tx = x1 + seg_px * i
            lab = ("%d" % v) if i < 2 else ("%d m" % v)
            cv.text(tx, y1 - fs * 0.72, lab, fs, (25, 25, 25, 255),
                    anchor=("lm" if i == 0 else "mm" if i == 1 else "rm"),
                    buffer_color=(255, 255, 255, 255), buffer_px=max(0.8, self.pj.mm(0.35)))
        self.stats["scalebar"] = {"segment_m": seg_m, "segment_px": seg_px,
                                  "px_per_m": self.pj.scale}

    def _north(self, mf):
        cv = self.cv
        mx, my, mw, _mh = mf
        cx, cy = mx + mw - 26, my + 26
        r = 12.0
        cv.line([(cx, cy + r), (cx, cy - r)], (40, 40, 40, 255), 1.4)
        cv.polygon([[(cx, cy - r - 1), (cx - 4.5, cy - r + 8), (cx + 4.5, cy - r + 8)]],
                   fill=(40, 40, 40, 255))
        cv.text(cx, cy + r + self.pj.pt(7.0) * 0.6, "N", self.pj.pt(8.0), (40, 40, 40, 255),
                bold=True, anchor="mt")


# ====================================================================== 版面

def compute_layout(canvas_w, canvas_h, px_per_mm, args):
    """算版面：标题带 + 图例栏 + 地图框。图例**不覆盖地图**。"""
    margin = px_per_mm * 4.0
    title_h = px_per_mm * 11.0 if args.title else margin
    left = margin
    legend_w = 0.0
    if not args.no_legend:
        legend_w = min(canvas_w * 0.34, max(px_per_mm * 46.0, canvas_w * 0.24))
        left = margin + legend_w + margin * 0.6
    top = title_h + margin * 0.4
    bottom = margin
    right = margin
    mf = (left, top, max(40.0, canvas_w - left - right), max(40.0, canvas_h - top - bottom))
    legend_frame = (margin, top, legend_w, mf[3]) if legend_w > 0 else (0, 0, 0, 0)
    return {"map_frame": mf, "legend_frame": legend_frame,
            "title_cy": title_h * 0.5, "px_per_mm": px_per_mm}


def _fmt_denom(d):
    if d >= 10000:
        return "{:,.0f}".format(round(d / 1000.0) * 1000)
    return "{:,.0f}".format(round(d / 100.0) * 100)


# ====================================================================== 小工具

def _frame_region(mf, w, h):
    """内图廓矩形（标注只能放在它里面）。没有版面信息时退回整幅画布。"""
    if not mf:
        return (0.0, 0.0, float(w), float(h))
    return (mf[0], mf[1], mf[0] + mf[2], mf[1] + mf[3])


def _num(v, default):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _bbox_in(bb, view):
    return not (bb[2] < view[0] or bb[0] > view[2] or bb[3] < view[1] or bb[1] > view[3])


def _plen(pts):
    return sum(math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
               for i in range(1, len(pts)))


def _point_angle_at(pts, d):
    """折线上距起点 `d`（像素）处的点与该处切向角（度，SVG 顺时针为正）。"""
    acc = 0.0
    for i in range(1, len(pts)):
        seg = math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
        if acc + seg >= d and seg > 0:
            t = (d - acc) / seg
            x = pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * t
            y = pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * t
            return (x, y), math.degrees(math.atan2(pts[i][1] - pts[i - 1][1],
                                                   pts[i][0] - pts[i - 1][0]))
        acc += seg
    return pts[len(pts) // 2], 0.0


def _visible_pieces(pts, view):
    """折线**完全落在画面内**的连续片段（宁短不长：边界上的一小截不参与布点）。"""
    x0, y0, x1, y1 = view
    out = []
    cur = []
    for p in pts:
        if x0 <= p[0] <= x1 and y0 <= p[1] <= y1:
            cur.append(p)
        else:
            if len(cur) >= 2:
                out.append(cur)
            cur = []
    if len(cur) >= 2:
        out.append(cur)
    return out


def _upright(ang):
    """让文字不倒过来：把角度收进 (-90, 90]。"""
    while ang > 90.0:
        ang -= 180.0
    while ang <= -90.0:
        ang += 180.0
    return ang


# ====================================================================== 精度自证

def run_checks(cart, args, proj, renderer, cv, layout=None):
    """返回一组**可核验的数字**（`--check`）。图不能自己证明自己对，数字可以。"""
    out = {"style_set": args.style_set, "denom": round(proj.denom(), 1),
           "view_bounds_local_m": [round(v, 2) for v in proj.bounds],
           "px_per_mm": round(proj.px_per_mm, 4),
           "px_per_m": round(proj.scale, 6),
           "output_px": [cv.w, cv.h]}
    if layout:
        # 把画框写出来：复核的人可以据此在图上精确取景，而不是靠肉眼找
        mf = layout["map_frame"]
        out["map_frame_px"] = [round(v, 2) for v in mf]
        out["legend_frame_px"] = [round(v, 2) for v in layout["legend_frame"]]
        reg = _frame_region(mf, cv.w, cv.h)
        out["map_clip_px"] = [round(v, 2) for v in reg]
        # ⚠️ 回归护栏：版面给的是 `(x, y, w, h)`，裁剪要 `(x0, y0, x1, y1)`。
        # 两者一旦不一致，地图右/下缘会被凭空切掉一大块（**曾真的发生过**），
        # 而所有"数字"仍然看着正常 —— 所以必须显式比对。
        out["frame_clip_match"] = bool(
            abs((mf[0] + mf[2]) - reg[2]) < 0.01 and abs((mf[1] + mf[3]) - reg[3]) < 0.01)
    # 1) 世界 → 像素 → 世界 往返
    worst = 0.0
    for k in range(24):
        t = k / 23.0
        x = proj.bounds[0] + t * (proj.bounds[2] - proj.bounds[0])
        y = proj.bounds[1] + (1 - t) * (proj.bounds[3] - proj.bounds[1])
        px, py = proj.px(x, y)
        bx, by = proj.inv(px, py)
        worst = max(worst, math.hypot(bx - x, by - y))
    out["bounds_roundtrip_max_err_m"] = round(worst, 9)
    # 2) 真实路幅：多边形「面积 ÷ 中心线长度」应等于属性 Width
    #    —— 这一条直接证明画的是**真实路幅面**，而不是"按等级给一个固定线宽"。
    #    过滤掉 L < 3W 的碎段：那种段上"面积÷长度"不是一个有意义的宽度
    #    （路口过渡、圆角、斜交都会让它偏大）。过滤掉多少条也要报出来。
    rows = []
    skipped_short = 0
    for f in cart.layer("road_boundary"):
        w = f.attrs.get("Width")
        L = f.attrs.get("Length")
        a = f.polygon_area()
        if not w or w <= 0 or not L or L <= 0 or a <= 0:
            continue
        if L < 3.0 * w:
            skipped_short += 1
            continue
        rows.append((abs(a / L - w) / w, f.attrs.get("Category"), w, a / L))
    if rows:
        errs = sorted(r[0] for r in rows)
        rows.sort(key=lambda r: -r[0])
        out["pavement_width"] = {
            "n": len(rows),
            "skipped_too_short": skipped_short,
            "median_rel_err": round(errs[len(errs) // 2], 5),
            "p90_rel_err": round(errs[int(len(errs) * 0.9)], 5),
            "worst": {"category": rows[0][1], "attr_width_m": rows[0][2],
                      "geom_width_m": round(rows[0][3], 3),
                      "rel_err": round(rows[0][0], 5)},
        }
    out["layers"] = renderer.stats["layers"]
    out["labels"] = renderer.stats["labels"]
    out["rules_unparsed"] = renderer.stats["rules_unparsed"]
    out["degraded"] = renderer.stats["degraded"]
    out["scalebar"] = renderer.stats.get("scalebar")
    if renderer.stats.get("scalebar"):
        sb = renderer.stats["scalebar"]
        out["scalebar"]["check_m_per_px"] = round(sb["segment_m"] / sb["segment_px"], 9)
        out["scalebar"]["expect_m_per_px"] = round(1.0 / proj.scale, 9)
    return out


# ====================================================================== CLI

def build_parser():
    ap = argparse.ArgumentParser(
        description="不用 QGIS 出制图级规划图（读 Carto 官方 .qml 样式）")
    ap.add_argument("--carto", default=None, help="Carto 导出目录（默认自动查找）")
    ap.add_argument("--out", default="plan.png", help="输出位图（.png/.jpg）")
    ap.add_argument("--svg", default=None, help="额外输出矢量图（.svg）")
    ap.add_argument("--size", type=int, default=2000, help="输出宽度（像素）")
    ap.add_argument("--size-h", type=int, default=None, help="输出高度（默认按画框比例）")
    ap.add_argument("--canvas-w", type=float, default=210.0,
                    help="版面宽度（毫米）—— QML 里的 mm/pt 尺寸按它换算像素")
    ap.add_argument("--bounds", default=None,
                    help="出图范围（**本地米制**，报告口径）：x0,y0,x1,y1；按画框比例扩张")
    ap.add_argument("--title", default=None)
    ap.add_argument("--style-set", default="Street", choices=list(QC.STYLE_SETS))
    ap.add_argument("--styles", default=None, help="Carto Styles 目录（默认从 --carto 推断）")
    ap.add_argument("--layers", default="Zoning_Boundary,Building_Boundary,Network_Boundary,"
                                       "Network_Centerline,POI_Location,Route_Centerline,"
                                       "Area_Boundary",
                    help="图层顺序 = **第一项在最上面**（与 carto_qgis_map.py 一致）")
    ap.add_argument("--hide", default="Area_Boundary", help="隐藏的图层（逗号分隔）")
    ap.add_argument("--interval", action="append", default=None,
                    help="沿线区间高亮，格式 路名:s1:s2（可重复）")
    ap.add_argument("--interval-run", type=int, default=0, help="第几个连通段（默认 0=最长）")
    ap.add_argument("--no-legend", action="store_true")
    ap.add_argument("--no-scalebar", action="store_true")
    ap.add_argument("--no-labels", action="store_true", help="不画路名 / POI 标注")
    ap.add_argument("--north", action="store_true", help="画指北针（默认不画）")
    ap.add_argument("--bg", default="252,251,248", help="背景色 r,g,b")
    ap.add_argument("--check", action="store_true", help="打印精度自证数字")
    ap.add_argument("--report", default=None, help="把自证数字写成 JSON")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.layers = [s.strip() for s in args.layers.split(",") if s.strip()]
    args.hide = set(s.strip() for s in (args.hide or "").split(",") if s.strip())
    args.bg = tuple(int(v) for v in args.bg.split(","))

    if args.carto is None:
        from core.carto_reader import find_carto_dir
        args.carto = find_carto_dir()
    if not args.carto:
        raise SystemExit("找不到 Carto 导出目录，请用 --carto 指定。")
    if args.styles is None:
        args.styles = os.path.join(args.carto, "Styles")
    if not os.path.isdir(args.styles):
        sys.stderr.write("⚠️ 没找到 Styles 目录（%s）——将退回内置保守配色，"
                         "图能出，但**不是官方样式**。\n" % args.styles)

    from core.carto_reader import CartoData
    cart = CartoData(args.carto)

    # 出图范围：给了就用（按画框比例扩张）；没给就用**可见图层**的并集（与 QGIS 路径同口径）
    if args.bounds:
        bounds = tuple(float(v) for v in args.bounds.split(","))
        if len(bounds) != 4:
            raise SystemExit("--bounds 需要 x0,y0,x1,y1")
    else:
        bounds = _union_bounds(cart, args)
        print("未给 --bounds → 用可见图层范围 %s" % (tuple(round(v) for v in bounds),))

    # 先用 1:1 的纸面比例算版面，得到画框后再算投影
    px_per_mm = args.size / float(args.canvas_w)
    height = args.size_h or args.size
    layout = compute_layout(args.size, height, px_per_mm, args)
    proj = Projector(bounds, layout["map_frame"], px_per_mm)

    fonts = Fonts()
    cv = RasterCanvas(args.size, height, args.bg, fonts)
    r = Renderer(cart, args.styles, args, cv, proj, layout)

    # ⚠️ 版面里是 `(x, y, w, h)`，裁剪接口要的是 `(x0, y0, x1, y1)` —— **必须转换**。
    # 直接传会把宽高当右下角，地图右缘与下缘被凭空切掉一大块。
    clip_rect = _frame_region(layout["map_frame"], cv.w, cv.h)
    cv.begin_clip(clip_rect)
    draw_all(r, args)
    cv.end_clip()
    r.furniture(layout)

    checks = run_checks(cart, args, proj, r, cv, layout) if (args.check or args.report) else None
    size = cv.save(args.out, bg=args.bg)
    print("written: %s  %dx%d px  1:%s" % (args.out, size[0], size[1], _fmt_denom(proj.denom())))
    if args.svg:
        sv = SvgCanvas(args.size, height, args.bg, fonts)
        r2 = Renderer(cart, args.styles, args, sv, proj, layout)
        sv.begin_clip(clip_rect)
        draw_all(r2, args)
        sv.end_clip()
        r2.furniture(layout)
        sv.save(args.svg)
        print("written: %s  (矢量)" % args.svg)
    if checks is not None:
        _print_checks(checks)
        if args.report:
            with open(args.report, "w", encoding="utf-8") as fh:
                json.dump(checks, fh, ensure_ascii=False, indent=2)
            print("written: %s" % args.report)
    return 0


def draw_all(r, args):
    """画几何，最后统一画标注。

    ⚠️ **`--layers` 是"从上到下"**（第一项画在最上面），与 `carto_qgis_map.py` 的
    `QgsMapSettings.setLayers()` 一致 —— 所以这里要**倒着遍历**（先画最下面的）。
    本项目实测确认过这个方向：`Zoning_Boundary,Building_Boundary` 得到"分区盖住建筑"，
    反过来则是"建筑盖住分区"。
    """
    dispatch = {
        "Zoning_Boundary": r.layer_zoning,
        "Building_Boundary": r.layer_buildings,
        "Network_Boundary": r.layer_road_boundary,
        "Route_Centerline": r.layer_routes,
        "POI_Location": r.layer_pois,
        "Area_Boundary": r.layer_area,
    }
    for key in reversed(args.layers):
        if key in args.hide:
            continue
        fn = dispatch.get(key)
        if fn is not None:
            fn()
    r.layer_interval()
    if "Network_Centerline" not in args.hide:
        r.layer_labels(poi=("POI_Location" not in args.hide),
                       roads=("Network_Centerline" in args.layers))


def _union_bounds(cart, args):
    xs, ys = [], []
    for key in args.layers:
        if key in args.hide:
            continue
        rk = READER_KEY.get(key)
        if not rk:
            continue
        for f in cart.layer(rk):
            xs.append(f.bbox[0])
            ys.append(f.bbox[1])
            xs.append(f.bbox[2])
            ys.append(f.bbox[3])
    if not xs:
        return (0.0, 0.0, 1000.0, 1000.0)
    return (min(xs), min(ys), max(xs), max(ys))


def _print_checks(c):
    L = []
    L.append("── 出图自证（图不能自证，数字可以） ──")
    L.append("  样式套 %s   比例尺 1:%s   输出 %dx%d px   %.4f px/mm"
             % (c["style_set"], _fmt_denom(c["denom"]), c["output_px"][0],
                c["output_px"][1], c["px_per_mm"]))
    L.append("  出图范围（本地米制）%s" % (c["view_bounds_local_m"],))
    L.append("  世界→像素→世界 最大往返误差：%.3g m" % c["bounds_roundtrip_max_err_m"])
    if c.get("map_frame_px"):
        L.append("  内图廓 %s px%s" % (
            c["map_frame_px"],
            "" if c.get("frame_clip_match", True) else "  ⚠️⚠️ 与裁剪区不一致 —— 图会被切掉一块！"))
    pw = c.get("pavement_width")
    if pw:
        L.append("  真实路幅校验：%d 段，面积÷长度 vs 属性 Width —— 中位相对误差 %.3f%%，"
                 "P90 %.3f%%" % (pw["n"], pw["median_rel_err"] * 100, pw["p90_rel_err"] * 100))
        w = pw["worst"]
        L.append("     最差：%s 属性 %.1f m / 几何 %.1f m（%.2f%%）"
                 % (w["category"], w["attr_width_m"], w["geom_width_m"], w["rel_err"] * 100))
    sb = c.get("scalebar")
    if sb:
        L.append("  比例尺校验：%.0f m = %.1f px → %.6f m/px（应为 %.6f）"
                 % (sb["segment_m"], sb["segment_px"], sb["check_m_per_px"],
                    sb["expect_m_per_px"]))
    for k, v in sorted((c.get("layers") or {}).items()):
        L.append("  图层 %-20s 画 %d 个%s" % (
            k, v.get("drawn", 0),
            ("（视口外剔除 %d）" % v["culled"]) if v.get("culled") else ""))
    lab = c.get("labels") or {}
    for k in ("roads", "poi"):
        if k in lab:
            L.append("  标注 %-6s 放上 %d / 因避让丢弃 %d"
                     % (k, lab[k]["placed"], lab[k]["dropped"]))
    if c.get("rules_unparsed"):
        L.append("  ⚠️ 未能解析的样式规则 %d 条（这些规则不会生效）："
                 % len(c["rules_unparsed"]))
        for u in c["rules_unparsed"][:3]:
            L.append("     [%s] %s" % (u["layer"], u["filter"]))
    if c.get("degraded"):
        d = defaultdict(list)
        for u in c["degraded"]:
            d[u["layer"]].append(u["symbol_layer"])
        for k, v in d.items():
            L.append("  ⚠️ %s 有无法复现的符号层（已用同色圆点近似）：%s" % (k, ", ".join(sorted(set(v)))))
    sys.stdout.write("\n".join(L) + "\n")


try:                                     # Pillow 是唯一第三方依赖
    from PIL import Image as _Image, ImageDraw as _ImageDraw, ImageFont as _ImageFont
except ImportError:                      # pragma: no cover
    _Image = _ImageDraw = _ImageFont = None


if __name__ == "__main__":
    if _Image is None:
        sys.stderr.write("需要 Pillow：pip install pillow\n")
        sys.exit(2)
    sys.exit(main())
