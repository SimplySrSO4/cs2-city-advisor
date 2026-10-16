#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
pdf_text_extract.py —— 无第三方依赖的 PDF 文本提取器（纯标准库）

用途
----
把 PDF 逐页提取为纯文本，落盘为 UTF-8 文本文件 + 逐页 JSON，供后续阅读/检索。
优先使用 pypdf / pdfminer（若环境里装了），否则退回内置的纯 Python 解析器。

纯 Python 解析器能力
--------------------
* 解析 xref table / xref stream，建立对象表（含对象流 ObjStm 展开）
* 对 FlateDecode（可带 PNG/TIFF 预测器）流做解压
* 递归解析页面资源里的字体，构建 ToUnicode CMap（bfchar / bfrange）
* 解码内容流中的 BT..ET 文本块：Tj / TJ / ' / " / Td / TD / T* / Tm / TL / Tf
* 对中文 CID 字体（Identity-H 等）用 ToUnicode 映射；无 ToUnicode 时按 Identity 猜测

局限
----
* 不处理加密 PDF、LZW/JPX 图片型扫描页（无文本层的扫描件只能得到 0 字符 —— 这正是
  "无法阅读"的判定依据）
* 不做版面重排，只按操作符顺序输出；表格/分栏会走形，但正文连贯性足以阅读

用法
----
    python pdf_text_extract.py <input.pdf> <outdir> [--max-pages N] [--start-page N]

输出
----
    <outdir>/<name>.txt          全文（含分页标记）
    <outdir>/<name>.pages.json   逐页文本 + 字符数统计
    <outdir>/<name>.report.txt   可读性判定报告
"""

import json
import os
import re
import sys
import zlib

# --------------------------------------------------------------------------------------
# 低层工具
# --------------------------------------------------------------------------------------

WS = b"\x00\t\n\x0c\r "
DELIM = b"()<>[]{}/%"

TOKEN_RE = re.compile(
    rb"""
    (?P<comment>%[^\r\n]*)
  | (?P<string>\((?:\\.|[^\\()]|\((?:\\.|[^\\()])*\))*\))
  | (?P<hex><[0-9A-Fa-f\s]*>)
  | (?P<dictopen><<)
  | (?P<dictclose>>>)
  | (?P<arrayopen>\[)
  | (?P<arrayclose>\])
  | (?P<name>/[^\x00\t\n\x0c\r ()<>\[\]{}/%]*)
  | (?P<number>[+-]?(?:\d+\.?\d*|\.\d+))
  | (?P<keyword>[A-Za-z][A-Za-z0-9*'"]*)
    """,
    re.VERBOSE | re.DOTALL,
)


class Name(str):
    __slots__ = ()


class Ref(object):
    __slots__ = ("num", "gen")

    def __init__(self, num, gen):
        self.num = num
        self.gen = gen

    def __repr__(self):
        return "Ref(%d,%d)" % (self.num, self.gen)

    def __eq__(self, other):
        return isinstance(other, Ref) and other.num == self.num

    def __hash__(self):
        return hash(self.num)


class Stream(object):
    def __init__(self, d, raw, doc):
        self.dict = d
        self.raw = raw
        self.doc = doc
        self._decoded = None

    def decoded(self):
        if self._decoded is not None:
            return self._decoded
        data = self.raw
        filt = self.dict.get("Filter")
        if filt is None:
            filt = []
        elif isinstance(filt, (Name, str)):
            filt = [filt]
        elif isinstance(filt, list):
            filt = filt
        else:
            filt = []
        parms = self.dict.get("DecodeParms") or self.dict.get("DP")
        if not isinstance(parms, list):
            parms = [parms] * len(filt)
        for i, f in enumerate(filt):
            f = str(f)
            p = parms[i] if i < len(parms) else None
            if f in ("FlateDecode", "Fl"):
                try:
                    data = zlib.decompress(data)
                except Exception:
                    try:
                        data = zlib.decompressobj().decompress(data)
                    except Exception:
                        data = b""
                predictor = 1
                colors = 1
                bpc = 8
                columns = 1
                if isinstance(p, dict):
                    predictor = int(p.get("Predictor", 1) or 1)
                    colors = int(p.get("Colors", 1) or 1)
                    bpc = int(p.get("BitsPerComponent", 8) or 8)
                    columns = int(p.get("Columns", 1) or 1)
                if predictor >= 10:
                    try:
                        data = _unpredict_png(data, colors, bpc, columns)
                    except Exception:
                        pass
                elif predictor == 2:
                    try:
                        data = _unpredict_tiff(data, colors, bpc, columns)
                    except Exception:
                        pass
            elif f in ("ASCIIHexDecode", "AHx"):
                hexs = re.sub(rb"[^0-9A-Fa-f]", b"", data.split(b">")[0])
                if len(hexs) % 2:
                    hexs += b"0"
                data = bytes.fromhex(hexs.decode("ascii", "ignore"))
            elif f in ("ASCII85Decode", "A85"):
                try:
                    data = _ascii85(data)
                except Exception:
                    data = b""
            elif f in ("LZWDecode", "LZW"):
                try:
                    data = _lzw(data)
                except Exception:
                    data = b""
            elif f in ("DCTDecode", "DCT", "JPXDecode", "CCITTFaxDecode", "CCF", "JBIG2Decode"):
                # 图片/扫描数据的原生压缩格式：保留原始字节，交给 Pillow 等解码器处理
                pass
            elif f in ("RunLengthDecode", "RL"):
                try:
                    data = _runlength(data)
                except Exception:
                    pass
            else:
                data = b""
        self._decoded = data
        return data


def _unpredict_png(data, colors, bpc, columns):
    bpp = max(1, (colors * bpc + 7) // 8)
    rowlen = (columns * colors * bpc + 7) // 8
    out = bytearray()
    prev = bytearray(rowlen)
    i = 0
    while i + 1 + rowlen <= len(data):
        ft = data[i]
        row = bytearray(data[i + 1:i + 1 + rowlen])
        i += 1 + rowlen
        if ft == 0:
            pass
        elif ft == 1:
            for j in range(bpp, rowlen):
                row[j] = (row[j] + row[j - bpp]) & 0xFF
        elif ft == 2:
            for j in range(rowlen):
                row[j] = (row[j] + prev[j]) & 0xFF
        elif ft == 3:
            for j in range(rowlen):
                a = row[j - bpp] if j >= bpp else 0
                row[j] = (row[j] + ((a + prev[j]) >> 1)) & 0xFF
        elif ft == 4:
            for j in range(rowlen):
                a = row[j - bpp] if j >= bpp else 0
                b = prev[j]
                c = prev[j - bpp] if j >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                row[j] = (row[j] + pr) & 0xFF
        out += row
        prev = row
    return bytes(out)


def _unpredict_tiff(data, colors, bpc, columns):
    if bpc != 8:
        return data
    rowlen = columns * colors
    out = bytearray()
    for i in range(0, len(data) - rowlen + 1, rowlen):
        row = bytearray(data[i:i + rowlen])
        for j in range(colors, rowlen):
            row[j] = (row[j] + row[j - colors]) & 0xFF
        out += row
    return bytes(out)


def _ascii85(data):
    data = data.strip()
    if data.startswith(b"<~"):
        data = data[2:]
    end = data.find(b"~>")
    if end >= 0:
        data = data[:end]
    out = bytearray()
    group = []
    for ch in data:
        c = chr(ch)
        if c in " \t\r\n\x0c\x00":
            continue
        if c == "z" and not group:
            out += b"\x00\x00\x00\x00"
            continue
        if c < "!" or c > "u":
            continue
        group.append(ord(c) - 33)
        if len(group) == 5:
            v = 0
            for g in group:
                v = v * 85 + g
            out += v.to_bytes(4, "big")
            group = []
    if group:
        n = len(group)
        group += [84] * (5 - n)
        v = 0
        for g in group:
            v = v * 85 + g
        out += v.to_bytes(4, "big")[:n - 1]
    return bytes(out)


def _runlength(data):
    out = bytearray()
    i = 0
    while i < len(data):
        l = data[i]
        i += 1
        if l == 128:
            break
        if l < 128:
            out += data[i:i + l + 1]
            i += l + 1
        else:
            if i < len(data):
                out += bytes([data[i]]) * (257 - l)
                i += 1
    return bytes(out)


def _lzw(data):
    out = bytearray()
    table = [bytes([i]) for i in range(256)] + [b"", b""]
    bitpos = 0
    codelen = 9
    prev = None
    total = len(data) * 8

    def read(n):
        nonlocal bitpos
        v = 0
        for _ in range(n):
            if bitpos >= total:
                return None
            byte = data[bitpos >> 3]
            bit = (byte >> (7 - (bitpos & 7))) & 1
            v = (v << 1) | bit
            bitpos += 1
        return v

    while True:
        code = read(codelen)
        if code is None:
            break
        if code == 256:
            table = [bytes([i]) for i in range(256)] + [b"", b""]
            codelen = 9
            prev = None
            continue
        if code == 257:
            break
        if prev is None:
            entry = table[code]
        else:
            if code < len(table):
                entry = table[code]
                table.append(prev + entry[:1])
            else:
                entry = prev + prev[:1]
                table.append(entry)
        out += entry
        prev = entry
        if len(table) + 1 >= (1 << codelen) and codelen < 12:
            codelen += 1
    return bytes(out)


class Lexer(object):
    """把 PDF 字节流切成对象。"""

    def __init__(self, data, doc=None):
        self.data = data
        self.pos = 0
        self.doc = doc

    def skip_ws(self):
        d, n = self.data, len(self.data)
        while self.pos < n:
            c = d[self.pos]
            if c in WS:
                self.pos += 1
            elif c == 0x25:  # %
                while self.pos < n and d[self.pos] not in b"\r\n":
                    self.pos += 1
            else:
                break

    # 预编译 + 用 `pat.match(d, pos)` 而不是 `re.match(pat, d[pos:])`：
    # 后者每 token 都复制剩余全部字节，内容流 0.3–1.1 MB 时退化成 O(n²)
    # （实测某 104 页 PDF 因此慢约 56 倍）。
    _NAME = re.compile(rb"/([^\x00\t\n\x0c\r ()<>\[\]{}/%]*)")
    _HEX = re.compile(rb"<([0-9A-Fa-f\s]*)>")
    _NUM = re.compile(rb"[+-]?(?:\d+\.\d*|\.\d+|\d+)")
    _KW = re.compile(rb"[A-Za-z][A-Za-z0-9*'\"]*")
    _REF = re.compile(rb"(\d+)\s+R(?![A-Za-z0-9])")

    def parse(self):
        self.skip_ws()
        d, n = self.data, len(self.data)
        if self.pos >= n:
            return None
        c = d[self.pos]
        if c == 0x2F:  # /
            m = Lexer._NAME.match(d, self.pos)
            tok = m.group(1) if m else b""
            self.pos = m.end() if m else self.pos + 1
            name = Name(_pdf_name_decode(tok))
            return self._maybe_ref(name)
        if c == 0x28:  # (
            return self._maybe_ref(self._string())
        if c == 0x3C:  # <
            if d[self.pos:self.pos + 2] == b"<<":
                self.pos += 2
                return self._dict()
            m = Lexer._HEX.match(d, self.pos)
            if not m:
                self.pos += 1
                return None
            hexs = re.sub(rb"\s", b"", m.group(1))
            self.pos = m.end()
            if len(hexs) % 2:
                hexs += b"0"
            try:
                raw = bytes.fromhex(hexs.decode("ascii"))
            except Exception:
                raw = b""
            return self._maybe_ref(raw)
        if c == 0x5B:  # [
            self.pos += 1
            arr = []
            while True:
                self.skip_ws()
                if self.pos >= n or d[self.pos] == 0x5D:
                    self.pos += 1
                    break
                before = self.pos
                v = self.parse()
                if self.pos == before:
                    self.pos += 1
                arr.append(v)
            return arr
        if c == 0x5D:
            self.pos += 1
            return None
        if c in b"+-.0123456789":
            m = Lexer._NUM.match(d, self.pos)
            if m:
                txt = m.group(0)
                self.pos = m.end()
                num = float(txt) if b"." in txt else int(txt)
                return self._maybe_ref(num)
        m = Lexer._KW.match(d, self.pos)
        if m:
            kw = m.group(0)
            self.pos = m.end()
            if kw == b"true":
                return True
            if kw == b"false":
                return False
            if kw == b"null":
                return None
            return kw.decode("latin-1")
        self.pos += 1
        return None

    def _maybe_ref(self, value):
        """数字 + 数字 + R → 间接引用。"""
        if not isinstance(value, int) or self.doc is None:
            return value
        save = self.pos
        self.skip_ws()
        d = self.data
        m = Lexer._REF.match(d, self.pos)
        if m:
            gen = int(m.group(1))
            self.pos = m.end()
            return Ref(value, gen)
        self.pos = save
        return value

    def _dict(self):
        obj = {}
        while True:
            self.skip_ws()
            d = self.data
            if self.pos >= len(d):
                break
            if d[self.pos:self.pos + 2] == b">>":
                self.pos += 2
                break
            before = self.pos
            k = self.parse()
            if self.pos == before:
                self.pos += 1
                continue
            if not isinstance(k, Name):
                continue
            v = self.parse()
            obj[str(k)] = v
        # 后面可能跟 stream
        save = self.pos
        self.skip_ws()
        if self.data[self.pos:self.pos + 6] == b"stream":
            self.pos += 6
            if self.data[self.pos:self.pos + 2] == b"\r\n":
                self.pos += 2
            elif self.data[self.pos:self.pos + 1] in (b"\n", b"\r"):
                self.pos += 1
            length = obj.get("Length")
            if isinstance(length, Ref) and self.doc is not None:
                length = self.doc.resolve(length)
            raw = None
            if isinstance(length, int) and length >= 0 and self.pos + length <= len(self.data):
                raw = self.data[self.pos:self.pos + length]
                after = self.pos + length
                m = re.compile(rb"\s*endstream").match(self.data, after)
                if not m:
                    raw = None  # 长度不可信，回退搜索
            if raw is None:
                idx = self.data.find(b"endstream", self.pos)
                if idx < 0:
                    idx = len(self.data)
                raw = self.data[self.pos:idx]
                raw = raw.rstrip(b"\r\n")
                after = idx
            else:
                after = self.pos + len(raw)
                m = re.compile(rb"\s*endstream").match(self.data, after)
                while self.data[after:after + 1] in (b"\r", b"\n"):
                    after += 1
                if self.data[after:after + 9] == b"endstream":
                    after += 9
            self.pos = after
            return Stream(obj, raw, self.doc)
        self.pos = save
        return obj

    def _string(self):
        """解析 (...) 字面字符串，处理转义与括号嵌套。"""
        d = self.data
        i = self.pos + 1
        depth = 1
        out = bytearray()
        n = len(d)
        while i < n:
            c = d[i]
            if c == 0x5C:  # backslash
                if i + 1 >= n:
                    break
                nx = d[i + 1]
                if nx in b"nrtbf":
                    out.append({0x6E: 10, 0x72: 13, 0x74: 9, 0x62: 8, 0x66: 12}[nx])
                    i += 2
                elif nx in b"()\\":
                    out.append(nx)
                    i += 2
                elif 0x30 <= nx <= 0x37:
                    j = i + 1
                    oct_digits = b""
                    while j < n and len(oct_digits) < 3 and 0x30 <= d[j] <= 0x37:
                        oct_digits += d[j:j + 1]
                        j += 1
                    out.append(int(oct_digits, 8) & 0xFF)
                    i = j
                elif nx in b"\r\n":
                    i += 2
                    if nx == 13 and i < n and d[i] == 10:
                        i += 1
                else:
                    out.append(nx)
                    i += 2
            elif c == 0x28:
                depth += 1
                out.append(c)
                i += 1
            elif c == 0x29:
                depth -= 1
                if depth == 0:
                    i += 1
                    break
                out.append(c)
                i += 1
            else:
                out.append(c)
                i += 1
        self.pos = i
        return bytes(out)


def _pdf_name_decode(tok):
    out = bytearray()
    i = 0
    while i < len(tok):
        c = tok[i]
        if c == 0x23 and i + 2 < len(tok):
            try:
                out.append(int(tok[i + 1:i + 3], 16))
                i += 3
                continue
            except Exception:
                pass
        out.append(c)
        i += 1
    return out.decode("latin-1")


# --------------------------------------------------------------------------------------
# 文档
# --------------------------------------------------------------------------------------

OBJ_RE = re.compile(rb"(?<![0-9])(\d{1,10})\s+(\d{1,5})\s+obj\b")


class PDFDoc(object):
    def __init__(self, data):
        self.data = data
        self.cache = {}
        self.offsets = {}
        self.trailer = {}
        self.objstm_of = {}       # 对象号 → 它所在的对象流(Stream)
        self._objstm_cache = {}
        self._scan_objects()
        self._read_xref()
        self._read_xref_streams()   # PDF 1.5+：交叉引用流 + 对象流

    # ---- 对象访问 ----
    def resolve(self, obj, depth=0):
        while isinstance(obj, Ref) and depth < 64:
            obj = self.get_object(obj.num)
            depth += 1
        return obj

    def get_object(self, num):
        if num in self.cache:
            return self.cache[num]
        val = None
        off = self.offsets.get(num)
        if off is not None:
            m = OBJ_RE.match(self.data, off)
            if m and int(m.group(1)) == num:
                lx = Lexer(self.data[m.end():], self)
                lx.pos = 0
                try:
                    val = lx.parse()
                except Exception:
                    val = None
        if val is None and num in self.objstm_of:
            # 在对象流（ObjStm）里
            stream = self.objstm_of[num]
            try:
                table = self.objstm_objects(stream)
                val = table.get(num)
            except Exception:
                val = None
        if val is None:
            # 回退：全文件搜索
            for m in OBJ_RE.finditer(self.data):
                if int(m.group(1)) == num:
                    lx = Lexer(self.data[m.end():], self)
                    try:
                        cand = lx.parse()
                    except Exception:
                        continue
                    if cand is not None:
                        val = cand
                        break
        if isinstance(val, Ref) and val.num == num:
            val = None
        self.cache[num] = val
        return val

    def _scan_objects(self):
        for m in OBJ_RE.finditer(self.data):
            num = int(m.group(1))
            self.offsets.setdefault(num, m.start())

    def _read_xref(self):
        """读取 trailer（取最后一个 trailer 字典或 xref stream 字典）。"""
        idx = self.data.rfind(b"trailer")
        if idx >= 0:
            lx = Lexer(self.data[idx + 7:], self)
            try:
                t = lx.parse()
                if isinstance(t, dict):
                    self.trailer = t
            except Exception:
                pass
        if "Root" not in self.trailer:
            for m in re.finditer(rb"trailer", self.data):
                lx = Lexer(self.data[m.end():], self)
                try:
                    t = lx.parse()
                except Exception:
                    continue
                if isinstance(t, dict) and "Root" in t:
                    self.trailer = t

    # ---- PDF 1.5+ 交叉引用流 / 对象流 ----
    def _read_xref_streams(self):
        """解析 /Type /XRef 交叉引用流：类型 1 = 未压缩对象(偏移)，类型 2 = 在对象流内。

        许多新版 PDF（含本项目的 TB 10099、城市规划原理第四版、MHT5002 等）
        **只有交叉引用流、没有经典 xref 表**，而且大量对象被压在对象流（ObjStm）里。
        不实现这一段就会"一页都找不到"（`pages_total: 0`）。

        定位方式：**必须从该交叉引用流的对象头 `<num> <gen> obj` 开始解析**。
        早期实现是"在 `/Type /XRef` 之前往回找最近的 `<<`"，但 xref 流的字典键序不固定，
        `/Type` 可能出现在很后面，往回找 `<<` 会命中**别的对象**的字典 → 静默解析失败。
        """
        seen_off = set()
        for m in re.finditer(rb"/Type\s*/XRef", self.data):
            # 往前找最近的 "<num> <gen> obj" 头（限定在合理距离内）
            hdr = None
            for hm in re.finditer(rb"(?<![0-9])(\d{1,10})\s+(\d{1,5})\s+obj\b",
                                  self.data[max(0, m.start() - 20000):m.start()]):
                hdr = hm
            if hdr is None:
                continue
            body_start = max(0, m.start() - 20000) + hdr.end()
            if body_start in seen_off:
                continue
            seen_off.add(body_start)
            lx = Lexer(self.data[body_start:], self)
            try:
                st = lx.parse()
            except Exception:
                continue
            if not isinstance(st, Stream):
                continue
            d = st.dict
            if "Root" in d and "Root" not in self.trailer:
                self.trailer = d
            try:
                w = [int(x) for x in (self.resolve(d.get("W")) or [])]
            except Exception:
                continue
            if len(w) < 3:
                continue
            size = d.get("Size")
            try:
                size = int(self.resolve(size) or 0)
            except Exception:
                size = 0
            index = self.resolve(d.get("Index"))
            if not isinstance(index, list) or not index:
                index = [0, size]
            try:
                index = [int(self.resolve(x) or 0) for x in index]
            except Exception:
                continue
            blob = st.decoded()
            rowlen = sum(w)
            if rowlen <= 0:
                continue
            pos = 0
            for k in range(0, len(index) - 1, 2):
                first, count = index[k], index[k + 1]
                for i in range(count):
                    if pos + rowlen > len(blob):
                        break
                    fields = []
                    off = pos
                    for width in w:
                        if width == 0:
                            fields.append(0)
                        else:
                            fields.append(int.from_bytes(blob[off:off + width], "big"))
                        off += width
                    pos += rowlen
                    ftype = fields[0] if w[0] > 0 else 1
                    num = first + i
                    if ftype == 1:
                        self.offsets.setdefault(num, fields[1])
                    elif ftype == 2:
                        # 在对象流 fields[1] 内，索引 fields[2]
                        host = self.get_object(fields[1])
                        if isinstance(host, Stream):
                            self.objstm_of[num] = host
        # 若 trailer 仍无 Root，从任意 XRef 流字典里补
        if "Root" not in self.trailer:
            for m in re.finditer(rb"/Root\s+(\d+)\s+\d+\s+R", self.data):
                self.trailer["Root"] = Ref(int(m.group(1)), 0)
                break

    # ---- 页面树 ----
    def catalog(self):
        root = self.trailer.get("Root")
        cat = self.resolve(root) if root is not None else None
        if not isinstance(cat, dict):
            # 回退：找 /Type /Catalog
            for num in list(self.offsets.keys()):
                o = self.get_object(num)
                if isinstance(o, dict) and str(o.get("Type")) == "Catalog":
                    cat = o
                    break
        return cat if isinstance(cat, dict) else {}

    def pages(self):
        cat = self.catalog()
        pages = []
        seen = set()

        def walk(node, depth=0):
            if depth > 64 or len(pages) > 6000:
                return
            node = self.resolve(node)
            if not isinstance(node, dict):
                return
            t = str(node.get("Type") or "")
            if t == "Page":
                pages.append(node)
                return
            kids = self.resolve(node.get("Kids"))
            if isinstance(kids, list):
                for k in kids:
                    walk(k, depth + 1)
            elif t == "" and "Contents" in node:
                pages.append(node)

        walk(cat.get("Pages"))
        if not pages:
            for num in sorted(self.offsets.keys()):
                o = self.get_object(num)
                if isinstance(o, dict) and str(o.get("Type")) == "Page":
                    if num not in seen:
                        seen.add(num)
                        pages.append(o)
        return pages

    def page_stream_data(self, page):
        contents = self.resolve(page.get("Contents"))
        chunks = []
        if isinstance(contents, Stream):
            chunks.append(contents.decoded())
        elif isinstance(contents, list):
            for c in contents:
                c = self.resolve(c)
                if isinstance(c, Stream):
                    chunks.append(c.decoded())
        return b"\n".join(chunks)

    def page_resources(self, page):
        res = self.resolve(page.get("Resources"))
        if isinstance(res, dict):
            return res
        return {}

    # ---- 对象流 ----
    def objstm_objects(self, stream):
        key = id(stream)
        if key in self._objstm_cache:
            return self._objstm_cache[key]
        out = {}
        try:
            data = stream.decoded()
            n = int(self.resolve(stream.dict.get("N")) or 0)
            first = int(self.resolve(stream.dict.get("First")) or 0)
            header = data[:first]
            nums = [int(x) for x in re.findall(rb"\d+", header)]
            pairs = list(zip(nums[0::2], nums[1::2]))[:n]
            for i, (onum, off) in enumerate(pairs):
                end = pairs[i + 1][1] if i + 1 < len(pairs) else len(data) - first
                seg = data[first + off:first + end]
                lx = Lexer(seg, self)
                try:
                    out[onum] = lx.parse()
                except Exception:
                    pass
        except Exception:
            pass
        self._objstm_cache[key] = out
        return out


# --------------------------------------------------------------------------------------
# 字体 / ToUnicode
# --------------------------------------------------------------------------------------

def _parse_tounicode(data):
    """解析 ToUnicode CMap，返回 {code:int -> str}。"""
    mapping = {}
    if not data:
        return mapping
    text = data.decode("latin-1", "ignore")
    # bfchar
    for block in re.findall(r"beginbfchar(.*?)endbfchar", text, re.S):
        for src, dst in re.findall(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]*)>", block):
            try:
                code = int(src, 16)
            except Exception:
                continue
            mapping[code] = _utf16_hex_to_str(dst)
    # bfrange
    for block in re.findall(r"beginbfrange(.*?)endbfrange", text, re.S):
        for m in re.finditer(
            r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*(<([0-9A-Fa-f]*)>|\[(.*?)\])", block, re.S
        ):
            lo = int(m.group(1), 16)
            hi = int(m.group(2), 16)
            if m.group(4) is not None:
                base = m.group(4)
                try:
                    basev = int(base, 16) if base else 0
                except Exception:
                    basev = 0
                width = len(base) if base else 4
                for i, code in enumerate(range(lo, min(hi, lo + 65535) + 1)):
                    try:
                        h = "%0*X" % (width, basev + i)
                    except Exception:
                        continue
                    mapping[code] = _utf16_hex_to_str(h)
            else:
                items = re.findall(r"<([0-9A-Fa-f]*)>", m.group(5) or "")
                for i, h in enumerate(items):
                    mapping[lo + i] = _utf16_hex_to_str(h)
    return mapping


def _utf16_hex_to_str(h):
    if not h:
        return ""
    if len(h) % 4 != 0 and len(h) % 2 == 0:
        # 可能是单字节
        try:
            return bytes.fromhex(h).decode("latin-1")
        except Exception:
            return ""
    try:
        raw = bytes.fromhex(h)
    except Exception:
        return ""
    try:
        return raw.decode("utf-16-be", "ignore")
    except Exception:
        return ""


class FontInfo(object):
    __slots__ = ("tounicode", "two_byte", "is_cid", "basefont", "diff")

    def __init__(self):
        self.tounicode = {}
        self.two_byte = False
        self.is_cid = False
        self.basefont = ""
        self.diff = {}


def _build_font(doc, fdict):
    fi = FontInfo()
    fd = doc.resolve(fdict)
    if not isinstance(fd, dict):
        return fi
    fi.basefont = str(fd.get("BaseFont") or "")
    subtype = str(fd.get("Subtype") or "")
    enc = str(fd.get("Encoding") or "")
    if "Identity" in enc or subtype in ("Type0",):
        fi.two_byte = True
    if subtype == "Type0":
        fi.is_cid = True
        desc = doc.resolve(fd.get("DescendantFonts"))
        if isinstance(desc, list) and desc:
            df = doc.resolve(desc[0])
            if isinstance(df, dict):
                if not fi.basefont:
                    fi.basefont = str(df.get("BaseFont") or "")
                cidinfo = doc.resolve(df.get("CIDSystemInfo"))
                if isinstance(cidinfo, dict):
                    reg = str(cidinfo.get("Registry") or "")
                    if reg and reg != "Adobe":
                        pass
    tu = doc.resolve(fd.get("ToUnicode"))
    if isinstance(tu, Stream):
        fi.tounicode = _parse_tounicode(tu.decoded())
    encd = doc.resolve(fd.get("Encoding"))
    if isinstance(encd, dict):
        diffs = doc.resolve(encd.get("Differences"))
        if isinstance(diffs, list):
            cur = 0
            for item in diffs:
                if isinstance(item, (int, float)):
                    cur = int(item)
                elif isinstance(item, (Name, str)):
                    fi.diff[cur] = str(item)
                    cur += 1
    return fi


GLYPH_HINTS = {
    "space": " ",
}


def _decode_show_bytes(raw, font):
    """按字体信息把字符串字节解码成文本。"""
    if not raw:
        return ""
    if font is None:
        # 无字体信息：尝试单字节 latin-1
        return raw.decode("latin-1", "ignore")
    out = []
    if font.two_byte:
        for i in range(0, len(raw) - 1, 2):
            code = (raw[i] << 8) | raw[i + 1]
            ch = font.tounicode.get(code)
            if ch is None:
                # 无 ToUnicode：Identity 编码猜测
                ch = _identity_guess(font, code)
            out.append(ch)
        if len(raw) % 2:
            code = raw[-1]
            out.append(font.tounicode.get(code) or _identity_guess(font, code))
    else:
        for b in raw:
            ch = font.tounicode.get(b)
            if ch is None and b in font.diff:
                ch = GLYPH_HINTS.get(font.diff[b], "")
            if ch is None:
                ch = bytes([b]).decode("latin-1")
            out.append(ch)
    return "".join(out)


def _identity_guess(font, code):
    """无 ToUnicode 时的兜底猜测。"""
    if 0x20 <= code < 0x7F:
        return chr(code)
    if font and "GBK" in font.basefont.upper() or (font and "GB-" in font.basefont.upper()):
        try:
            return bytes([code >> 8, code & 0xFF]).decode("gbk", "ignore")
        except Exception:
            return ""
    if code < 0x10000:
        return chr(code)
    return ""


# --------------------------------------------------------------------------------------
# 内容流 → 文本
# --------------------------------------------------------------------------------------

def extract_page_text(doc, page):
    data = doc.page_stream_data(page)
    if not data:
        return ""
    res = doc.page_resources(page)
    fonts_raw = doc.resolve(res.get("Font"))
    fonts = {}
    if isinstance(fonts_raw, dict):
        for k, v in fonts_raw.items():
            try:
                fonts[k] = _build_font(doc, v)
            except Exception:
                fonts[k] = FontInfo()

    lx = Lexer(data, doc)
    lx.pos = 0
    cur_font = None
    out = []
    stack = []
    tm = [1, 0, 0, 1, 0, 0]
    tlm = [1, 0, 0, 1, 0, 0]
    leading = 0.0
    font_size = 0.0
    char_space = 0.0
    word_space = 0.0
    hscale = 1.0
    last_y = None
    ops_count = 0
    while True:
        lx.skip_ws()
        if lx.pos >= len(data):
            break
        obj = lx.parse()
        ops_count += 1
        if ops_count > 4000000:
            break
        # 只有 str（关键字）才是操作符。**bytes 绝对不能当操作符**：
        # PDF 内容流里的十六进制字符串 <033d1bb7…> 与字面字符串 (abc) 都会被 Lexer
        # 解析成 bytes，若把它们当操作符，字符串就永远进不了操作数栈，
        # `Tj` 取到空栈 → 整页文本为空（PingFang / InDesign / Word 导出的 PDF 全是 hex 字符串，
        # 会被误判成"扫描件"）。本项目实测命中的文件见 references/52 与 58。
        if isinstance(obj, (Name, str)) and not isinstance(obj, bytes):
            op = str(obj)
            try:
                if op == "BT":
                    tm = [1, 0, 0, 1, 0, 0]
                    tlm = list(tm)
                elif op == "ET":
                    if out and not out[-1].endswith("\n"):
                        out.append("\n")
                elif op == "Tf":
                    if len(stack) >= 2:
                        fname, fsize = stack[-2], stack[-1]
                        cur_font = fonts.get(str(fname))
                        font_size = float(fsize) if isinstance(fsize, (int, float)) else 0.0
                elif op == "TL":
                    if stack and isinstance(stack[-1], (int, float)):
                        leading = float(stack[-1])
                elif op == "Tc":
                    if stack and isinstance(stack[-1], (int, float)):
                        char_space = float(stack[-1])
                elif op == "Tw":
                    if stack and isinstance(stack[-1], (int, float)):
                        word_space = float(stack[-1])
                elif op == "Tz":
                    if stack and isinstance(stack[-1], (int, float)):
                        hscale = float(stack[-1]) / 100.0
                elif op == "Td":
                    if len(stack) >= 2:
                        tx, ty = float(stack[-2]), float(stack[-1])
                        tlm = _mat_mul([1, 0, 0, 1, tx, ty], tlm)
                        tm = list(tlm)
                elif op == "TD":
                    if len(stack) >= 2:
                        tx, ty = float(stack[-2]), float(stack[-1])
                        leading = -ty
                        tlm = _mat_mul([1, 0, 0, 1, tx, ty], tlm)
                        tm = list(tlm)
                elif op == "Tm":
                    if len(stack) >= 6:
                        tlm = [float(x) for x in stack[-6:]]
                        tm = list(tlm)
                elif op == "T*":
                    tlm = _mat_mul([1, 0, 0, 1, 0, -leading], tlm)
                    tm = list(tlm)
                elif op == "'":
                    tlm = _mat_mul([1, 0, 0, 1, 0, -leading], tlm)
                    tm = list(tlm)
                    s = stack[-1] if stack else b""
                    _emit(out, _decode_show_bytes(_as_bytes(s), cur_font), tm, font_size, last_y)
                    last_y = tm[5]
                elif op == '"':
                    if len(stack) >= 3:
                        aw, ac = stack[-3], stack[-2]
                        try:
                            word_space = float(aw)
                            char_space = float(ac)
                        except Exception:
                            pass
                    tlm = _mat_mul([1, 0, 0, 1, 0, -leading], tlm)
                    tm = list(tlm)
                    s = stack[-1] if stack else b""
                    _emit(out, _decode_show_bytes(_as_bytes(s), cur_font), tm, font_size, last_y)
                    last_y = tm[5]
                elif op == "Tj":
                    s = stack[-1] if stack else b""
                    _emit(out, _decode_show_bytes(_as_bytes(s), cur_font), tm, font_size, last_y)
                    last_y = tm[5]
                elif op == "TJ":
                    arr = stack[-1] if stack else []
                    if isinstance(arr, list):
                        buf = []
                        for it in arr:
                            if isinstance(it, bytes):
                                buf.append(_decode_show_bytes(it, cur_font))
                            elif isinstance(it, (int, float)):
                                # 负值 = 加宽字距 → 可能是空格
                                if it <= -180:
                                    buf.append(" ")
                        _emit(out, "".join(buf), tm, font_size, last_y)
                        last_y = tm[5]
                elif op == "Do":
                    pass
            except Exception:
                pass
            stack = []
        else:
            stack.append(obj)
            if len(stack) > 64:
                del stack[:-32]
    text = "".join(out)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _emit(out, s, tm, font_size, last_y):
    if not s:
        return
    y = tm[5]
    if last_y is None:
        pass
    elif abs(y - last_y) > max(1.0, font_size * 0.35):
        if out and not out[-1].endswith("\n"):
            out.append("\n")
    out.append(s)


def _as_bytes(s):
    if isinstance(s, bytes):
        return s
    if isinstance(s, str):
        return s.encode("latin-1", "ignore")
    return b""


def _mat_mul(a, b):
    a0, a1, a2, a3, a4, a5 = a
    b0, b1, b2, b3, b4, b5 = b
    return [
        a0 * b0 + a1 * b2,
        a0 * b1 + a1 * b3,
        a2 * b0 + a3 * b2,
        a2 * b1 + a3 * b3,
        a4 * b0 + a5 * b2 + b4,
        a4 * b1 + a5 * b3 + b5,
    ]


# --------------------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------------------

def extract(pdf_path, outdir, max_pages=None, start_page=1, verbose=True):
    with open(pdf_path, "rb") as f:
        data = f.read()
    name = os.path.splitext(os.path.basename(pdf_path))[0]
    name = re.sub(r"[^\w\u4e00-\u9fff.\-]+", "_", name)[:80] or "document"
    doc = PDFDoc(data)
    pages = doc.pages()
    total = len(pages)
    os.makedirs(outdir, exist_ok=True)

    page_texts = []
    lo = max(1, start_page)
    hi = total if not max_pages else min(total, lo + max_pages - 1)
    for i in range(lo, hi + 1):
        try:
            t = extract_page_text(doc, pages[i - 1])
        except Exception as e:  # noqa: BLE001
            t = ""
            if verbose:
                sys.stderr.write("page %d failed: %r\n" % (i, e))
        page_texts.append({"page": i, "chars": len(t.strip()), "text": t})

    txt_path = os.path.join(outdir, name + ".txt")
    json_path = os.path.join(outdir, name + ".pages.json")
    rep_path = os.path.join(outdir, name + ".report.txt")

    with open(txt_path, "w", encoding="utf-8") as f:
        for p in page_texts:
            f.write("\n\n===== PAGE %d =====\n" % p["page"])
            f.write(p["text"].strip() + "\n")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "file": pdf_path,
                "pages_total": total,
                "pages_extracted": [p["page"] for p in page_texts],
                "page_char_counts": {str(p["page"]): p["chars"] for p in page_texts},
                "pages": page_texts,
            },
            f,
            ensure_ascii=False,
        )

    nz = [p for p in page_texts if p["chars"] > 0]
    chars = sum(p["chars"] for p in page_texts)
    mojibake = sum(1 for p in page_texts if _mojibake_ratio(p["text"]) > 0.3)
    han = sum(len(re.findall(r"[\u4e00-\u9fff]", p["text"])) for p in page_texts)
    report = [
        "file: %s" % pdf_path,
        "bytes: %d" % len(data),
        "pages_total: %d" % total,
        "pages_extracted: %d (%d..%d)" % (len(page_texts), lo, hi),
        "pages_with_text: %d" % len(nz),
        "total_chars: %d" % chars,
        "cjk_chars: %d" % han,
        "avg_chars_per_page: %.1f" % (chars / max(1, len(page_texts))),
        "pages_likely_mojibake: %d" % mojibake,
        "verdict: %s" % _verdict(len(nz), len(page_texts), chars, han, mojibake, bool(doc.catalog())),
        "",
        "outputs:",
        "  " + txt_path,
        "  " + json_path,
    ]
    with open(rep_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report) + "\n")
    if verbose:
        print("\n".join(report))
    return {
        "txt": txt_path,
        "json": json_path,
        "report": rep_path,
        "pages_total": total,
        "total_chars": chars,
    }


def _mojibake_ratio(text):
    if not text:
        return 0.0
    bad = len(re.findall(r"[\ufffd\u0000-\u0008\u000e-\u001f]", text))
    weird = len(re.findall(r"[\u00c0-\u00ff]{3,}", text))
    return (bad + weird) / max(1, len(text))


def _verdict(nz_pages, pages, chars, han, mojibake, has_catalog):
    if pages == 0:
        return "不可读：未找到任何页面对象（文件可能损坏或结构异常）"
    ratio = nz_pages / max(1, pages)
    if chars < 200:
        return "不可读：提取到 %d 字符，几乎无文本层（可能为扫描件/图片型 PDF）" % chars
    if ratio < 0.25:
        return "基本不可读：仅 %d/%d 页有文本" % (nz_pages, pages)
    if mojibake > pages * 0.3:
        return "部分可读：%d 页疑似乱码，编码映射不完整" % mojibake
    if han < chars * 0.05:
        return "可疑：中日韩字符占比过低（%.1f%%），中文原文可能未正确映射" % (100.0 * han / max(1, chars))
    return "可读：%d/%d 页有文本，共 %d 字符（中文 %d）" % (nz_pages, pages, chars, han)


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    pdf_path = argv[1]
    outdir = argv[2]
    max_pages = None
    start_page = 1
    i = 3
    while i < len(argv):
        if argv[i] == "--max-pages" and i + 1 < len(argv):
            max_pages = int(argv[i + 1])
            i += 2
        elif argv[i] == "--start-page" and i + 1 < len(argv):
            start_page = int(argv[i + 1])
            i += 2
        else:
            i += 1
    if not os.path.isfile(pdf_path):
        print("no such file: %s" % pdf_path)
        return 2
    extract(pdf_path, outdir, max_pages=max_pages, start_page=start_page)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
