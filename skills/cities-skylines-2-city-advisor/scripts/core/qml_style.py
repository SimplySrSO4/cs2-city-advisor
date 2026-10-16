#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
qml_style.py —— 读 Carto 自带的**官方 QGIS 样式**（`.qml`），**纯标准库**。

为什么需要它
------------
`carto_qgis_map.py` 走 QGIS 时，样式由 `lyr.loadNamedStyle(qml)` 交给 QGIS 去解释。
**没有 QGIS 的机器上没有任何东西能解释这些 `.qml`** —— 于是"无 QGIS 只能出草图"。
但 `.qml` 本身就是 XML：**规则**（`filter` + 比例尺范围）+ **符号**
（`SimpleFill` / `SimpleLine` / `SimpleMarker` …），两者都能直接读出来。
把这两样读出来，**官方配色 / 线宽 / 分级规则就能在没有 QGIS 的机器上原样复现** ——
这是 `city_svg_map.py` 能称得上"制图级"而不是"自己猜图层"的关键。

支持范围（按本项目 `Styles/Street|Plan|Topo` 实测统计）
------------------------------------------------------
* `RuleRenderer`（路网 / 建筑 / 分区 / 线路 / POI 都用它）—— 含**嵌套规则**、
  `scalemindenom` / `scalemaxdenom`、`checkstate`（取消勾选的规则必须跳过）；
* `categorizedSymbol`（`Area_Boundary`）；
* `nullSymbol`（`Network_Centerline` —— **它只出标注、不画线**，必须识别，
  否则会凭空画出一堆路名线）；
* 符号层：`SimpleFill` / `SimpleLine` / `SimpleMarker` / `LinePatternFill`
  （后者近似为斜线填充）；`SvgMarker` / `FontMarker` 在零依赖下无法复现图形 →
  **退化为同色圆点**，并计入 `degraded`，调用方可在图上或报告里说明。

过滤器表达式
------------
QGIS 的 `filter` 是一小段表达式语言。本项目实测只会用到这一撮：

    "Category" ~ 'Highway'                     正则匹配（QGIS 的 ~ 是 re.search）
    "Zoning" = 'Residential'                   相等
    NOT ("Category" ~ 'Highway|Large')         取反
    (...) AND (...) / (...) OR (...)           与 / 或
    ELSE                                       兜底（恒真）

因此本模块用**递归下降**解析它们，而不是 eval —— `eval` 既危险又会在
`Park(?!ing)` 这类正则上出错。**解析失败的表达式绝不静默通过**：
它被记入 `unparsed`，并当作"该规则不生效"处理（宁可不画，不可画错）。

坐标 / 单位口径
---------------
`.qml` 里的线宽是 `MM`、字号是 `Point`、标注缓冲是 `MM` —— 都是**纸面单位**。
换算成像素需要"纸面 → 输出"的比例（见 `city_svg_map.py` 的 `--size` / `--canvas-w`）。
本模块只负责**原样读出数值与单位**，不做任何换算。

用法
----
```python
from core import qml_style as Q
st = Q.load(r'<Carto>/Styles/Street/Street-Network-Boundary.qml')
print(st.renderer, len(st.rules), len(st.symbols))
sym = st.symbol_for({'Category': 'Highway', 'Form': 'Normal'}, denom=45000)
for sl in sym.layers:                      # 按 pass 升序（先画的在前）
    print(sl.cls, sl.fill_rgba, sl.width_mm)
```
"""

import re
import xml.etree.ElementTree as ET
from collections import OrderedDict

#: QGIS 字号单位 → 纸面毫米。1 pt = 25.4/72 mm。
PT_PER_MM = 72.0 / 25.4


# ====================================================================== 颜色

def parse_color(value):
    """QGIS 颜色串 → `(r, g, b, a)`（0–255）。认不出返回 `None`。

    实测两种写法：
      * `"40,160,80,255,rgb:0.15,..."`（主流）
      * `"#ff0000"` / `"255,0,0"`（少数）
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.lower() in ("no", "none"):
        return None
    if s.startswith("#"):
        h = s[1:]
        try:
            if len(h) == 6:
                return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)
            if len(h) == 8:
                return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(h[6:8], 16))
        except ValueError:
            return None
        return None
    head = s.split(",rgb:")[0].split(",hsv:")[0]
    parts = [p.strip() for p in head.split(",") if p.strip() != ""]
    try:
        nums = [float(p) for p in parts[:4]]
    except ValueError:
        return None
    if len(nums) < 3:
        return None
    r, g, b = (int(round(min(255.0, max(0.0, n)))) for n in nums[:3])
    a = int(round(min(255.0, max(0.0, nums[3])))) if len(nums) > 3 else 255
    return (r, g, b, a)


def contrast_text(rgba):
    """给一个填充色，返回在上面能看清的文字色（用于图例/标注）。"""
    if not rgba:
        return (20, 20, 20, 255)
    r, g, b = rgba[0], rgba[1], rgba[2]
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    return (25, 25, 25, 255) if lum > 150 else (250, 250, 250, 255)


# ====================================================================== 过滤器

class FilterError(Exception):
    """过滤器表达式无法解析。"""


_TOKEN = re.compile(r"""
    \s*(?:
        (?P<lparen>\()
      | (?P<rparen>\))
      | (?P<op><=|>=|<>|!=|=|~|<|>)
      | (?P<dstr>"[^"]*")
      | (?P<sstr>'(?:[^']|'')*')
      | (?P<word>[A-Za-z_][A-Za-z_0-9]*)
    )
""", re.VERBOSE)


def _tokenize(expr):
    out = []
    i = 0
    n = len(expr)
    while i < n:
        if expr[i].isspace():
            i += 1
            continue
        m = _TOKEN.match(expr, i)
        if not m or m.end() == i:
            raise FilterError("无法识别的字符 @%d: %r" % (i, expr[i:i + 24]))
        i = m.end()
        if m.group("lparen"):
            out.append(("(", "("))
        elif m.group("rparen"):
            out.append((")", ")"))
        elif m.group("op"):
            out.append(("op", m.group("op")))
        elif m.group("dstr"):
            out.append(("field", m.group("dstr")[1:-1]))
        elif m.group("sstr"):
            out.append(("str", m.group("sstr")[1:-1].replace("''", "'")))
        else:
            out.append(("word", m.group("word").upper()))
    return out


_OPS = {
    "=": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "<>": lambda a, b: a != b,
    "<": lambda a, b: _num(a) < _num(b),
    ">": lambda a, b: _num(a) > _num(b),
    "<=": lambda a, b: _num(a) <= _num(b),
    ">=": lambda a, b: _num(a) >= _num(b),
    #: QGIS 的 `~` 是**正则查找**（不是全匹配）：`'Park(?!ing)'` 靠的就是这一点。
    "~": lambda a, b: re.search(b, "" if a is None else str(a)) is not None,
}


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return float("nan")


class _Parser(object):
    """递归下降：or → and → unary → primary。"""

    def __init__(self, tokens):
        self.t = tokens
        self.i = 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else (None, None)

    def take(self):
        tok = self.peek()
        self.i += 1
        return tok

    def parse(self):
        node = self.or_expr()
        if self.i != len(self.t):
            raise FilterError("表达式尾部有多余记号：%r" % (self.t[self.i:],))
        return node

    def or_expr(self):
        node = self.and_expr()
        while self.peek() == ("word", "OR"):
            self.take()
            node = ("or", node, self.and_expr())
        return node

    def and_expr(self):
        node = self.unary()
        while self.peek() == ("word", "AND"):
            self.take()
            node = ("and", node, self.unary())
        return node

    def unary(self):
        if self.peek() == ("word", "NOT"):
            self.take()
            return ("not", self.unary())
        return self.primary()

    def primary(self):
        kind, val = self.peek()
        if kind == "(":
            self.take()
            node = self.or_expr()
            if self.take()[0] != ")":
                raise FilterError("括号没有闭合")
            return node
        if kind == "word" and val == "ELSE":
            self.take()
            return ("else",)
        if kind == "field":
            self.take()
            opk, op = self.take()
            if opk != "op":
                raise FilterError("字段 %r 后面不是比较运算符" % val)
            sk, sv = self.take()
            if sk not in ("str", "field", "word"):
                raise FilterError("运算符 %r 后面不是字面量" % op)
            return ("cmp", val, op, sv)
        raise FilterError("无法解析的记号：%r" % (self.peek(),))


def _eval(node, attrs):
    k = node[0]
    if k == "else":
        return True
    if k == "and":
        return _eval(node[1], attrs) and _eval(node[2], attrs)
    if k == "or":
        return _eval(node[1], attrs) or _eval(node[2], attrs)
    if k == "not":
        return not _eval(node[1], attrs)
    if k == "cmp":
        _k, field, op, lit = node
        return bool(_OPS[op](attrs.get(field), lit))
    raise FilterError("未知节点 %r" % (k,))


#: QGIS 表达式函数 → 本模块能算的等价写法。
#: `regexp_match("F", 'p')` 与 `"F" ~ 'p'` 完全等价，因此**先归一再解析**。
#: 其它函数（`$area` / `@zoom_level` / `length()` …）**不做近似** ——
#: 它们依赖几何或渲染上下文，猜错就会画出不该有的东西；这类规则进 `unparsed`。
_RE_NORMALIZE = (
    (re.compile(r"""regexp_match\s*\(\s*("[^"]*")\s*,\s*('(?:[^']|'')*')\s*\)"""), r"\1 ~ \2"),
)


def normalize_filter(expr):
    """把 QGIS 表达式里可**无损**改写的部分换成本模块的算子。"""
    s = str(expr)
    for pat, rep in _RE_NORMALIZE:
        s = pat.sub(rep, s)
    return s


def compile_filter(expr):
    """QGIS 过滤器表达式 → `callable(attrs) -> bool`。

    空表达式 / `None` → 恒真（QGIS 里空 filter 表示"全部"）。
    `ELSE` → 恒真。解析失败抛 `FilterError`（**调用方必须当成"不生效"**）。
    """
    if expr is None:
        return lambda _a: True
    s = str(expr).strip()
    if not s:
        return lambda _a: True
    if s.upper() == "ELSE":
        return lambda _a: True
    node = _Parser(_tokenize(normalize_filter(s))).parse()
    return lambda attrs: bool(_eval(node, attrs or {}))


# ====================================================================== 结构

class SymbolLayer(object):
    """一个符号层（`SimpleFill` / `SimpleLine` / ...）。

    `opts` 是**该层自己的** `<Option name= value=>` 键值对（不会混进
    `data_defined_properties` 里的同名项 —— 那是数据定义覆盖，本项目用不到）。
    """

    __slots__ = ("cls", "enabled", "pass_", "opts", "raw")

    def __init__(self, cls, enabled, pass_, opts, raw=None):
        self.cls = cls
        self.enabled = enabled
        self.pass_ = pass_
        self.opts = opts
        self.raw = raw or {}

    # --- 常用量的**规范化读取**（把 QGIS 的各种写法收成一种）---
    def _opt(self, *names, **kw):
        for n in names:
            if n in self.opts:
                return self.opts[n]
        return kw.get("default")

    @property
    def fill_rgba(self):
        return parse_color(self._opt("color", "fillColor", "fill"))

    @property
    def outline_rgba(self):
        if (self._opt("outline_style", default="solid") or "").lower() == "no":
            return None
        return parse_color(self._opt("outline_color"))

    @property
    def stroke_rgba(self):
        return parse_color(self._opt("line_color", "outline_color", "color"))

    @property
    def width_mm(self):
        """线宽（毫米）。QML 里 `outline_width`（面）/ `line_width`（线）都是 MM。"""
        for key in ("line_width", "outline_width"):
            if key in self.opts:
                try:
                    return float(self.opts[key])
                except (TypeError, ValueError):
                    return 0.0
        return 0.0

    @property
    def size_mm(self):
        try:
            return float(self._opt("size", default=2.0))
        except (TypeError, ValueError):
            return 2.0

    @property
    def line_style(self):
        return (self._opt("line_style", "outline_style", default="solid") or "solid").lower()

    @property
    def dash(self):
        """虚线：返回 `(实长mm, 空长mm)` 或 `None`（实线）。"""
        if self.line_style in ("dash", "dashed"):
            w = max(0.2, self.width_mm)
            return (w * 4.0, w * 3.0)
        if self.line_style in ("dot", "dotted"):
            w = max(0.2, self.width_mm)
            return (w * 0.6, w * 2.2)
        if self.line_style in ("dash dot", "dashdot"):
            w = max(0.2, self.width_mm)
            return (w * 3.0, w * 2.0)
        return None

    @property
    def offset_mm(self):
        try:
            parts = str(self._opt("offset", default="0,0")).split(",")
            return float(parts[0]), float(parts[1])
        except (TypeError, ValueError):
            return (0.0, 0.0)

    def __repr__(self):
        return "<SymbolLayer %s pass=%s fill=%s w=%.2fmm>" % (
            self.cls, self.pass_, self.fill_rgba, self.width_mm)


class Symbol(object):
    """一个符号：若干符号层，按 `pass` **升序**即为绘制顺序（先画的在下）。"""

    __slots__ = ("name", "type", "alpha", "layers", "degraded")

    def __init__(self, name, type_, alpha, layers, degraded=()):
        self.name = name
        self.type = type_
        self.alpha = alpha
        self.layers = layers
        self.degraded = tuple(degraded)

    def by_pass(self):
        return sorted(self.layers, key=lambda l: l.pass_)

    def __repr__(self):
        return "<Symbol %s %s layers=%d%s>" % (
            self.name, self.type, len(self.layers),
            (" degraded=%s" % (self.degraded,)) if self.degraded else "")


class Rule(object):
    """一条渲染规则。`group` 是它在嵌套结构里的父规则标签（用于图例分组）。"""

    __slots__ = ("label", "filter", "symbol", "smin", "smax", "enabled",
                 "group", "matcher", "error")

    def __init__(self, label, filter_expr, symbol, smin, smax, enabled, group,
                 matcher=None, error=None):
        self.label = label
        self.filter = filter_expr
        self.symbol = symbol
        self.smin = smin
        self.smax = smax
        self.enabled = enabled
        self.group = group
        self.matcher = matcher
        self.error = error

    def matches_scale(self, denom):
        if denom is None:
            return True
        if self.smin and denom < self.smin:
            return False
        if self.smax and denom > self.smax:
            return False
        return True

    def matches(self, attrs, denom=None):
        if not self.enabled or self.matcher is None:
            return False
        if not self.matches_scale(denom):
            return False
        return self.matcher(attrs)

    def __repr__(self):
        return "<Rule %r filter=%r sym=%s scale=[%s,%s]>" % (
            self.label, self.filter, self.symbol, self.smin, self.smax)


class Category(object):
    __slots__ = ("value", "label", "symbol", "render")

    def __init__(self, value, label, symbol, render=True):
        self.value = value
        self.label = label
        self.symbol = symbol
        self.render = render


class TextStyle(object):
    __slots__ = ("size_pt", "color", "family", "bold", "italic", "field",
                 "is_expression", "opacity")

    def __init__(self, size_pt, color, family, bold, italic, field,
                 is_expression, opacity=1.0):
        self.size_pt = size_pt
        self.color = color
        self.family = family
        self.bold = bold
        self.italic = italic
        self.field = field
        self.is_expression = is_expression
        self.opacity = opacity


class BufferStyle(object):
    __slots__ = ("draw", "size_mm", "color", "opacity")

    def __init__(self, draw, size_mm, color, opacity=1.0):
        self.draw = draw
        self.size_mm = size_mm
        self.color = color
        self.opacity = opacity


class LabelRule(object):
    """标注规则：一条 filter + 文字样式 + 比例尺范围 + 摆放方式。"""

    __slots__ = ("filter", "smin", "smax", "text", "buffer", "placement",
                 "dist_mm", "priority", "repeat_mm", "matcher", "error", "description")

    def __init__(self, filter_expr, smin, smax, text, buffer, placement,
                 dist_mm, priority, repeat_mm, matcher, error, description=""):
        self.filter = filter_expr
        self.smin = smin
        self.smax = smax
        self.text = text
        self.buffer = buffer
        self.placement = placement
        self.dist_mm = dist_mm
        self.priority = priority
        self.repeat_mm = repeat_mm
        self.matcher = matcher
        self.error = error
        self.description = description

    def matches(self, attrs, denom=None):
        if self.matcher is None:
            return False
        if denom is not None:
            if self.smin and denom < self.smin:
                return False
            if self.smax and denom > self.smax:
                return False
        return self.matcher(attrs)

    def __repr__(self):
        return "<LabelRule %r place=%s size=%.1fpt scale=[%s,%s]>" % (
            self.description or self.filter, self.placement,
            self.text.size_pt if self.text else -1, self.smin, self.smax)


def primary_style(sym):
    """符号的代表样式 → `(kind, rgba, width_mm)`；无法判断返回 `(None, None, 0)`。

    `kind` 是 `"fill"` / `"line"` / `"marker"` —— 图例要用不同的样例图形，
    所以不能只给一个颜色。
    """
    if sym is None:
        return (None, None, 0.0)
    best = None
    for sl in sym.by_pass():                      # 最上层优先（画在图例最上方的那个色）
        if not sl.enabled:
            continue
        c = sl.fill_rgba
        if c is not None and c[3] > 0:
            best = ("fill", c, sl.width_mm)
    if best is None:
        for sl in sym.by_pass():
            if not sl.enabled:
                continue
            c = sl.stroke_rgba
            if c is not None and c[3] > 0:
                best = ("line", c, max(sl.width_mm, 0.3))
    if best is None:
        for sl in sym.by_pass():
            if not sl.enabled:
                continue
            c = parse_color(sl.opts.get("fill") or sl.opts.get("color"))
            if c is not None and c[3] > 0:
                best = ("marker", c, sl.size_mm)
    return best if best else (None, None, 0.0)


def _primary_color(sym):
    """符号在图例里的代表色（`primary_style` 的便捷包装）。"""
    return primary_style(sym)[1]


class QmlLayer(object):
    """一个 `.qml` 的解释结果。"""

    def __init__(self, path):
        self.path = path
        self.name = None
        self.renderer = ""
        self.rules = []
        self.categories = []
        self.symbols = OrderedDict()
        self.labels = []
        self.labels_enabled = False
        self.unparsed = []            # [(filter_expr, err)] —— **必须能被调用方看到**
        self.degraded = set()         # 无法复现的符号层类别
        self.cat_field = None         # categorizedSymbol 用的字段（QGIS 写在 renderer 的 attr 上）

    # --- 查询 ---
    def symbol_for(self, attrs, denom=None):
        """按规则**自上而下**取第一条命中的符号；没有命中返回 `None`。

        QGIS 的 RuleRenderer 就是"第一条命中即用"（除非 `enableorderby`）。
        """
        for r in self.rules:
            if r.matches(attrs, denom):
                return self.symbols.get(r.symbol)
        return None

    def rule_for(self, attrs, denom=None):
        for r in self.rules:
            if r.matches(attrs, denom):
                return r
        return None

    def category_for(self, attrs):
        """categorizedSymbol：按 `cat_field` 取分类（`render="false"` 的分类被跳过）。"""
        if not self.cat_field:
            return None
        val = str(attrs.get(self.cat_field, ""))
        for c in self.categories:
            if c.value == val and c.render:
                return c
        return None

    def category_symbol_for(self, attrs):
        c = self.category_for(attrs)
        return self.symbols.get(c.symbol) if c is not None else None

    def label_rule_for(self, attrs, denom=None):
        for lr in self.labels:
            if lr.matches(attrs, denom):
                return lr
        return None

    def legend_entries(self):
        """图例条目：`[(分组, 标签, kind, rgba, width_mm)]`，顺序与文件一致（自下而上）。

        * 取消勾选的规则、以及**过滤器解析失败**的规则都不进图例 ——
          图例必须与"真正画出来的东西"一致，否则图例本身就成了假证据。
        * `categorizedSymbol` 用分类标签。
        * ⚠️ 这里给的是"**样式文件里有什么**"；`city_svg_map.py` 还会按
          "**本次到底画出来了哪些**"再过滤一遍（图例由画出来的要素反推）。
        """
        out = []
        if self.renderer == "categorizedSymbol":
            for c in self.categories:
                if not c.render:
                    continue
                kind, col, w = primary_style(self.symbols.get(c.symbol))
                if col is not None:
                    out.append(("", c.label, kind, col, w))
            return out
        for r in self.rules:
            if not r.enabled or r.symbol is None or r.error:
                continue
            kind, col, w = primary_style(self.symbols.get(r.symbol))
            if col is None:
                continue
            label = r.label or (r.group or "")
            if not label:
                continue
            out.append((r.group or "", label, kind, col, w))
        return out

    def __repr__(self):
        return "<QmlLayer %s renderer=%s rules=%d symbols=%d labels=%d>" % (
            self.name, self.renderer, len(self.rules), len(self.symbols), len(self.labels))


# ====================================================================== 解析

def _bool(v, default=False):
    if v is None:
        return default
    return str(v).strip().lower() in ("1", "true", "yes")


def _float(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _layer_options(layer_el):
    """取 `<layer>` 下**直接** `<Option name= value=>` 键值对。"""
    opts = OrderedDict()
    opt_map = layer_el.find("Option")
    if opt_map is None:
        return opts
    for o in list(opt_map):
        if o.tag != "Option":
            continue
        n = o.get("name")
        v = o.get("value")
        if n is not None and v is not None:
            opts[n] = v
    return opts


def _parse_symbol(sym_el):
    layers = []
    degraded = []
    for le in sym_el.findall("layer"):
        cls = le.get("class") or ""
        enabled = _bool(le.get("enabled"), True)
        pass_ = int(_float(le.get("pass"), 0))
        if cls in ("SvgMarker", "FontMarker", "RasterFill", "PointPatternFill",
                   "RandomMarker", "GeometryGenerator", "EllipseMarker", "AnimatedMarker"):
            degraded.append(cls)
        layers.append(SymbolLayer(cls, enabled, pass_, _layer_options(le)))
    return Symbol(sym_el.get("name") or "",
                  sym_el.get("type") or "",
                  _float(sym_el.get("alpha"), 1.0),
                  layers, degraded)


def _scale_min(el):
    """QGIS 写的是 `scalemindenom`；个别版本写 `scalindenom`。两个都认。

    ⚠️ 这个属性名曾把"比例尺范围"整段读丢（规则会变成"任何比例尺都显示"）——
    表现是图上出现本不该出现的支路名。**不要改回只认一个拼写。**
    """
    v = el.get("scalemindenom")
    if v is None:
        v = el.get("scalindenom")
    return _float(v, 0.0)


def _parse_rules(container, out, unparsed, group=""):
    """递归收集规则（保持文档顺序）。

    ⚠️ 分组规则的**子 `<rule>` 是父 `<rule>` 的直接子元素**（外面没有 `<rules>` 包一层）
    —— 实测 `Network_Boundary` 就是这种结构，按 `<rules>` 找会把 26 条规则全部读丢。
    返回 `group` 的标签。
    """
    if container is None:
        return group
    for r in container.findall("rule"):
        label = r.get("label") or ""
        flt = r.get("filter")
        sym = r.get("symbol")
        smin = _scale_min(r)
        smax = _float(r.get("scalemaxdenom"), 0.0)
        enabled = (r.get("checkstate") is None) or _bool(r.get("checkstate"), True)
        matcher = None
        err = None
        if sym is not None:
            try:
                matcher = compile_filter(flt)
            except FilterError as e:
                matcher = None
                err = str(e)
                unparsed.append((flt, err))
        if sym is not None:
            out.append(Rule(label, flt, sym, smin, smax, enabled, group, matcher, err))
        # 子规则（分组）——直接嵌在 `<rule>` 里
        kids = r.findall("rule")
        if kids:
            _parse_rules(r, out, unparsed, group=(label or group))
    return group


def _parse_labeling(root, out_labels, unparsed):
    """解析 `<labeling>`：rule-based 或 simple。返回 (是否启用, 标签字段)。"""
    lab = root.find("labeling")
    if lab is None:
        return False, None
    enabled = _bool(lab.get("enabled"), True)
    field = None
    rules = []
    rbc = lab.find("rules")
    if rbc is not None:
        for r in rbc.findall("rule"):
            rules.append((r.get("filter"), _scale_min(r),
                          _float(r.get("scalemaxdenom"), 0.0),
                          r.get("description") or "", r.find("settings")))
    else:
        rules.append((None, None, None, "", lab.find("settings")))
    for flt, smin, smax, desc, st in rules:
        if st is None:
            continue
        ts = st.find("text-style")
        if ts is None:
            continue
        fld = ts.get("fieldName")
        if fld and field is None and not _bool(ts.get("isExpression"), False):
            field = fld
        text = TextStyle(
            size_pt=_float(ts.get("fontSize"), 10.0),
            color=parse_color(ts.get("textColor")) or (30, 30, 30, 255),
            family=ts.get("fontFamily") or "",
            bold=_float(ts.get("fontWeight"), 50.0) >= 75 or _bool(ts.get("forcedBold"), False),
            italic=_bool(ts.get("fontItalic"), False),
            field=fld,
            is_expression=_bool(ts.get("isExpression"), False),
            opacity=_float(ts.get("textOpacity"), 1.0),
        )
        buf_el = st.find("text-buffer")
        buf = None
        if buf_el is not None:
            buf = BufferStyle(_bool(buf_el.get("bufferDraw"), False),
                              _float(buf_el.get("bufferSize"), 0.0),
                              parse_color(buf_el.get("bufferColor")) or (255, 255, 255, 255),
                              _float(buf_el.get("bufferOpacity"), 1.0))
        pl_el = st.find("placement")
        placement = dist = prio = repeat = None
        if pl_el is not None:
            placement = pl_el.get("placement")
            dist = _float(pl_el.get("dist"), 0.0)
            prio = _float(pl_el.get("priority"), 5.0)
            repeat = _float(pl_el.get("repeatDistance"), 0.0)
        matcher = None
        err = None
        try:
            matcher = compile_filter(flt)
        except FilterError as e:
            err = str(e)
            unparsed.append((flt, err))
            matcher = None
        out_labels.append(LabelRule(
            flt, _float(smin, 0.0), _float(smax, 0.0), text, buf, placement,
            dist, prio, repeat, matcher, err, desc))
    return enabled, field


def load(path):
    """解析一个 `.qml`。文件不存在 / XML 不合法 → `None`（**不抛异常**）。"""
    if not path or not path.lower().endswith(".qml"):
        return None
    import os
    if not os.path.exists(path):
        return None
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return None
    st = QmlLayer(path)
    st.name = os.path.splitext(os.path.basename(path))[0]
    st.labels_enabled = _bool(root.get("labelsEnabled"), False)

    rend = root.find("renderer-v2")
    # `POI_Location` 是 **`pointCluster` 套 `RuleRenderer`**（两层 `renderer-v2`）——
    # 只看第一层会得到"0 规则 0 符号"。取**最内层带 symbols 的那一个**。
    inner = None
    for cand in root.iter("renderer-v2"):
        if cand.find("symbols") is not None:
            inner = cand
    if inner is not None:
        rend = inner
    if rend is not None:
        st.renderer = (rend.get("type") or "").strip()
        st.cat_field = rend.get("attr")
        _parse_rules(rend.find("rules"), st.rules, st.unparsed)
        syms = rend.find("symbols")
        if syms is not None:
            for se in syms.findall("symbol"):
                s = _parse_symbol(se)
                st.symbols[s.name] = s
                st.degraded.update(s.degraded)
        cats = rend.find("categories")
        if cats is not None:
            for ce in cats.findall("category"):
                st.categories.append(Category(
                    ce.get("value") or "",
                    ce.get("label") or ce.get("value") or "",
                    ce.get("symbol"),
                    _bool(ce.get("render"), True)))
    _parse_labeling(root, st.labels, st.unparsed)
    return st


def style_path(styles_dir, style_set, layer_key):
    """拼出某层的官方 `.qml` 路径（与 `qgis_common.STYLE_FILES` 同一套命名）。"""
    import os
    from . import qgis_common as QC
    tpl = QC.STYLE_FILES.get(layer_key)
    if not tpl or not styles_dir:
        return None
    return os.path.join(styles_dir, style_set, tpl % style_set)


def load_layer(styles_dir, style_set, layer_key):
    """直接按图层键取官方样式。返回 `QmlLayer` 或 `None`。"""
    return load(style_path(styles_dir, style_set, layer_key))
