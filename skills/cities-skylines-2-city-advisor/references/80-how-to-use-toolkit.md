# 工具箱使用说明（HOW-TO-USE）

本 skill 附带两套工具，全部只用**标准库 + numpy + Pillow**，不需要 geopandas / rasterio / matplotlib，也不需要联网。

## 0.0 代码布局（`scripts/`）

```
scripts/
├─ city_report.py      ← 稳定 CLI：一键诊断报告（转发到 analysis/city_reports.py）
├─ export_report.py    ← ⭐ **稳定 CLI：Markdown 报告 → 合规 DOCX + XLSX**（见 §4；规范见 `110`）
├─ city_map.py         ← 稳定 CLI：出诊断图（转发到 analysis/city_map.py）
├─ carto_qgis_map.py   ← ⭐ **QGIS 出精确规划图**（先探测 QGIS；见 §3.1）
├─ city_svg_map.py     ← ⭐⭐ **不用 QGIS 也出制图级规划图**（读 Carto 官方 `.qml`；见 §3.1a）
├─ city_archive.py     ← ⭐ **成果归档**：只留人能看懂的，删掉过程产物（见 §3.3）
├─ city_docx_polish.py ← ⭐ **用 Univer 精细化 DOCX + 逐页视觉验证**（见 §3.4）
├─ carto_reader.py     ← 稳定接口：数据读取库（转发到 core/carto_reader.py）
├─ core/               ← 底层：数据读取、路网图、**地形与可建造性**、**路名几何**、**命名**、**交付格式**
│   ├─ carto_reader.py        读 Shapefile/GeoJSON/GeoTIFF、空间索引、存档元数据
│   ├─ network_graph.py       路网加权图 + Dijkstra（T5c 通勤可达性）
│   ├─ terrain.py             **可建造性分级 + GeoJSON↔UTM 坐标标定**（见 §2.5）
│   ├─ roads.py               ⭐ **路名几何：连通段拆分 + 沿线里程 s + 区间定位**（见 §3.0）
│   ├─ naming.py              ⭐ **地点命名：以"人能快速定位与理解"为准则**（见 §3.2）
│   ├─ deliverable_style.py   ⭐⭐ **交付格式的唯一实现**（字体/字号/缩进/列宽/颜色常量；
│   │                             规范原文 = `references/110-deliverable-format.md`）
│   ├─ qgis_common.py         QGIS 预检 / 环境变量 / GeoPackage 转换（见 §3.1）
│   └─ qml_style.py           ⭐⭐ **读 Carto 官方 `.qml` 样式**（纯标准库；见 §3.1a）
├─ analysis/           ← 分析与呈现（要改指标口径就看这里）
│   ├─ city_reports.py     全部分析函数 + 20 节报告生成
│   ├─ city_map.py         诊断图
│   └─ report_base.py      中英对照表、fmt、md_table（无分析逻辑）
└─ tools/              ← PDF 提取与 OCR 工具链（与城市分析无关）
    ├─ pdf_diagnose.py / pdf_text_extract.py / pdf_image_probe.py
    ├─ pdf_ocr_pipeline.py / ocr_books.py / run_extract_all.ps1
    └─ ocr_winrt.ps1 / pdf_render_winrt.ps1
```

> **为什么最外层还留三个 `.py`**：`SKILL.md`、本文件与外部脚本都按
> `scripts/city_report.py`、`from carto_reader import CartoData` 使用它们 ——
> **这是稳定契约**，所以最外层是薄转发层，实现都在子目录里。
> **读代码请直接读子目录那份**（最外层只有十几行）。

| 套件 | 位置 | 用途 |
|---|---|---|
| **Carto 城市分析** | `core/` + `analysis/` | 读 Carto 导出数据、**建路网图跑 Dijkstra**、出诊断报告、出诊断图 |
| **交付落文档** | `export_report.py` + `core/deliverable_style.py` | Markdown 报告 → **DOCX + XLSX**（默认交付形态），含格式合规自检 |
| **PDF 提取** | `tools/` | 判断 PDF 有无可用文本层、提取文本、对扫描件做渲染 + Windows OCR 批量识别 |

## 0. 环境

用 `load_workspace_dependencies` 返回的 Python 解释器（已带 numpy、Pillow）。
本机路径示例：`C:\Users\Devcl\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe`

- `--carto` 可省略（脚本会自动查找 `Carto_live` / `Carto` / `Carto_prev` 等目录）。
- 在 PowerShell 里跑中文输出时加 `-X utf8` 并设 `$env:PYTHONIOENCODING='utf-8'`，否则控制台可能因 GBK 编码报错。
- 调用 PowerShell 脚本要用 `powershell`（本机没有 `pwsh`）。

## 0.1 PDF 提取的四类情形（**先判类型，再选工具**）

判类型：`python -X utf8 scripts/tools/pdf_diagnose.py "<pdf>" --pages 5`
（看 `pages_total` 是否正常、`xobjects` 是什么编码、`ops:` 里有没有 `Tj/TJ`）

| 情形 | 判据 | 用什么 |
|---|---|---|
| ① 正常文本层 | 有 `Tj/TJ`，抽出来是可读中文 | `pdf_text_extract.py` |
| ② **文本层存在但不可用** | 能抽出字符，但全是乱码（CID 字体 ToUnicode 损坏） | **只能 OCR**（见 ③）；别浪费时间调文本层 |
| ③ 扫描件 + Pillow 可解码 | 每页一张 `DCTDecode`/`JPXDecode` 图 | `pdf_ocr_pipeline.py` 导出图片 → `ocr_winrt.ps1` |
| ④ **扫描件 + Pillow 解不了** | `JBIG2Decode` / `CCITTFaxDecode` | **`pdf_render_winrt.ps1`**（`Windows.Data.Pdf`）渲染 PNG → `ocr_winrt.ps1` |
| ⑤ 图片被加扰（DRM） | 渲染 62 页哈希全同、OCR 只得水印 | **放弃**，如实记录"不可读"（见 `references/52`） |

> **实测速度**：`pdf_render_winrt.ps1` 对 75 MB / 429 页的 JBIG2 文件约 **1.4 秒/页**；
> `ocr_winrt.ps1` 中文页在 **0.55–1.0 缩放**下识别率最好。
> **规模参考**：730 页的书全流程（渲染+OCR）约需 20–30 分钟。

## 0.2 `scripts/tools/pdf_text_extract.py` 已修的三处真实缺陷（**重要**）

这三处都曾导致"误判 PDF 不可读 / 整页空白 / 极慢"，已修复并验证：

1. **`bytes` 被当成操作符**（最隐蔽）。
   PDF 内容流里的十六进制字符串 `<033d1bb7…>` 与字面字符串 `(abc)` 都会被词法器解析成 `bytes`。
   旧代码写成 `isinstance(obj, (Name, str)) or isinstance(obj, bytes)` → 把字符串当操作符，
   于是字符串**永远进不了操作数栈**，`Tj` 取到空栈 → **整页文本为空**。
   PingFang / InDesign / Word 导出的 PDF 全用 hex 字符串，会被整体误判为"扫描件"。
   修法：**只有 `str`（关键字）才是操作符**。
2. **不查对象流（ObjStm）**。PDF 1.5+ 把大量对象压在对象流里；`get_object` 不查就会
   出现 `pages_total: 0`（本项目 TB 10099 就这样被误判过）。修法：按交叉引用流登记
   `objstm_of`，`get_object` 回退时查对象流。
3. **交叉引用流字典定位错误**。旧代码"在 `/Type /XRef` 之前往回找最近的 `<<`"——
   而 xref 流的键序不固定（`/Type` 可能很靠后），往回找会命中**别的对象**的字典而静默失败。
   修法：**从该流的对象头 `<num> <gen> obj` 开始解析**。
4. **性能**：`re.match(pat, data[pos:])` 每个 token 都复制剩余全部字节，内容流 0.3–1.1 MB 时
   退化成 O(n²)（实测慢约 **56 倍**）。修法：改用 `pat.match(data, pos)` 并预编译正则。

---

## 1. `scripts/core/carto_reader.py` —— Carto 数据读取库

被其他脚本 import，也可以直接交互式使用。

```python
from carto_reader import CartoData, GridIndex, build_building_index

c = CartoData(r"C:\Users\Devcl\Desktop\CSL2\Carto")
c.roads        # 路网中心线（Feature 列表）
c.zoning       # 分区图斑
c.buildings    # 建筑（含 Resident / Employee）
c.routes       # 公交/轨道线路（含 Passenger / Vehicle / Stop / Length）
c.districts()  # 行政区
c.unlocked_tiles()   # 已解锁地块
c.total_population(), c.total_jobs()
c.elevation.value_at(x, y)      # 某点高程（米）
c.depth                        # 水深栅格

idx = build_building_index(c)          # 建筑空间索引
hits = idx.within(x, y, 600)           # 600 m 内的 [(距离, 建筑), ...]
```

要点（**先读 `references/70-carto-data-schema.md`**）：
- 几何是 **Z 型**（PolyLineZ/PolygonZ），字段文本是 **GBK**，坐标系 EPSG:32631。
- `Route.Length` 是**含往返的总长**，算站距必须除以 2。
- 单位是米，可直接算欧氏距离。

---

## 2. `scripts/city_report.py` —— 一键城市诊断报告

> ⚠️ **它产出的是 Markdown 中间稿，不是最终交付物。**
> 默认交付形态是 **DOCX + XLSX**，落文档用 **`scripts/export_report.py`**（见 §3.3）。
> 只有玩家**明确要求 markdown** 时，`city_report.md` 才是最终交付物。
> 加 `--maps <目录>` 出配图 —— 默认交付 DOCX，图要嵌进去。

```bash
# 最省事：什么都不用指定，脚本会自己找到游戏导出的 Carto 目录
<python> -X utf8 scripts/city_report.py --out city_report.md --json city_metrics.json

# 要看趋势/增量就再给上期与多期目录
# ⭐ 游戏内时间**自动读取，不需要输入任何时间**
<python> -X utf8 scripts/city_report.py \
         --carto "<Carto 导出目录>" --prev "<上一期导出>" \
         --trend "<第1期>,<第2期>" \
         --out city_report.md --json city_metrics.json
```

> ⭐⭐ **游戏内时间：自动读取存档，无需用户输入**
>
> `Passenger`（线路乘客数）、`Volume`（车流量）、拥堵程度等读数**随一天内的时段剧烈变化**。
> 「上次是早高峰、这次是凌晨」的差异会被误读成"公共交通客流下降" —— **那是错的**。
>
> * **脚本自动做这件事**：读 `<城市名>.SaveGameMetadata`（在 `.cok` ZIP 里）的
>   `simulationDate {year, month, hour, minute}`，再按
>   「人口合理性过滤 → 取时间最接近的存档 → 72h 窗口」匹配到本次导出，
>   **并把置信度（高/中/低）写进报告**。
> * 单期报告会在**开头**给出游戏内时间；`--prev` 时 **§20.0** 会判定
>   `可比 / 需谨慎 / 不可比 / 未知`，列出**还能比**与**不能比**的指标，
>   并**给出下次存档的时段建议**（如"上一期存于 08:12（早高峰）→ 下次请在 07:00–09:00 存档"）。
> * 判为 `不可比`／`未知` 时，**线路表会自动隐去「乘客变化」列**，只留配车数与线路增删。
> * `--at` / `--prev-at` **只用于纠错**（自动匹配明显不对时）；
>   `--no-auto-time` 可禁用自动读取（排查匹配问题用）。
> * **最佳实践：导出 Carto 后立刻保存一次游戏** —— 这样时间匹配几乎必然正确。
> * **纯时段无关的量任何时间都能比**：人口/岗位/职住比、建筑数与建筑等级、分区图斑、
>   路网与轨道里程、配车数、线位几何、站数、公司利润、地块解锁数、地形量、税基结构。
>
> 机制与匹配规则细节见 `references/70` §1.0.1b。

- `--carto` **可以省略**：脚本会用 `carto_reader.find_carto_dir()` 自动查找
  `Carto` / `Carto_live` / `Carto_prev` / `CartoData` 等常见目录名（先看当前目录，再逐级向上找），
  **最后退回游戏自身的导出目录**
  （`%USERPROFILE%\AppData\LocalLow\Colossal Order\Cities Skylines II\ModsData\Carto`）。
  → **所以通常不必把 Carto 导出复制到工作区**，直接跑即可。
- `--prev` 可选：给上一期导出目录，报告多出 §19 的两期增量。
- `--trend` 可选：给**多期目录（逗号分隔、按时间先后）**，报告多出 §14 趋势表。
  **这是判断"方向对不对"的唯一手段** —— 单期快照只能看现状。
  > 实测价值：本项目就是靠它发现"人口 +29% 而公交乘客 −6%"这个致命信号；
  > 只看单期快照完全看不出来。

输出 **20 个部分（§0–§19）**：
| 节 | 内容 |
|---|---|
| §0 | **数据自检**（数据为空 / 人口为 0 / 路网超出已解锁范围 / 高程栅格未覆盖…） |
| §1 | 城市规模、区级职住比（同时给出 District 与 Building 两种口径） |
| §2 | 用地与分区结构（**含图斑面积不可当用地面积的自动警告**、建筑密度层级分布） |
| §3 | 路网等级、限速分布、双向路幅口径提醒 |
| §4 | **公交线路效率表**（人·车、人·km、平均站距及口径、估算间隔、Usage/车）⚠️ **只含客运线路**（`RoutePassenger`）；货运铁路/货运航线单列 `cargo_routes`，归工业部分 |
| §5 | 轨道走廊重叠度（**自动判读**：同一走廊 / 部分重合 / 独立）⚠️ 只比较**客运**轨道线 |
| §6 | **车站腹地**（站点几何**靠等分线路猜**，跨线去重，标出"空站"）⚠️ 与 §15 不一致时以 §15 为准；**只统计客运站点，depot（含地铁总站）不是车站** |
| §7 | 就业中心（400 m 网格聚合） |
| §8 | 地形、**可建造性（§8.1）**、**真实税基与建筑等级（§8.2）**、**高程的规划用途（§8.3）** |
| §9 | **用地效率**：各分区"岗位/公顷""每个岗位占地"，岗位最密/最疏地块 |
| §10 | **风险代理指标**：区级职住比离散度、支路/主干比、低密度占比、空站占比 |
| §11 | **税基潜力**：密度权重与分区权重的**相对指数**、密度×分区对照、**本地劳动力自给率** |
| §12 | **开发强度**：各用途"建筑占地 ÷ 已划区面积"，找没盖起来的用途 |
| §13 | **住宅噪音暴露**：逐栋 Top15 + 片区热点（**隧道权重 0**） |
| §14 | **多期趋势**（`--trend`）：人口/岗位/税基指数/分区结构/逐线乘客的走向 |
| §15 | **真实站点覆盖率**：用 **POI 里的真实站点坐标**（`StopBus`/`StopSubway`/`StopPassengerTrain`）算 300/400/500/800 m 的人口与**岗位**覆盖 + 未覆盖热点 + 自动判读（覆盖是不是瓶颈） |
| §16 | **服务设施双口径覆盖**：**官方 `Service range`（上界，会被密度压缩）** vs **现实步行半径（下界）** + **压缩比** + "先调预算后盖楼"的动作建议 |
| §17 | **公交服务质量归因**：逐线的「公交专用道覆盖率 × 人/车」→ 该**加车**还是该**上专用道**（Ceder 式 12.1 的可观测代理） |
| §18 | **通勤可达性**：用 `Network_Centerline` 建加权图（权重 = 长度 ÷ 限速）跑 **Dijkstra**，算"住宅 → 最近就业中心"的**路网距离**（含 3/5/8/12 km 阈值曲线），**自动区分「形态病」与「总量病」** |
| §19 | **道路流量与拥堵治理**：`Volume ÷ Lane` 单车流量分位 → 拥堵热点区（800 m 聚类）+ **按道路等级给不同处方**（高速分流 / 匝道治交织 / 支路治路口） |
| §20 | **与上期对比**（`--prev`）：最近两期的增量 |

**§8 之下还有三个小节**：
| 小节 | 内容 |
|---|---|
| §8.1 | **可建造性分级**：水体 / 陡坡 / 缓坡 / 适宜建设区（`core/terrain.py`） |
| §8.2 | **真实税基与建筑等级**：新版 `Profit`/`Wage`/`Level` → 官方税收机制原样落地；**等级分布即税率实验的核心观测值** |
| **§8.2 之后 · 工业部分** | **工业部分 · 货运终端与产业链（辅助分析）**：**货运港口 / 货运铁路 / 货运航线不与客运数据一并分析** —— 本小节给出货运线路（`cargo_routes`）与**货运终端集疏运（T14）**；同一设施的多条 POI 记录已按 200 m 归并。**不得写进任何客运结论** |
| §8.3 | **高程的规划用途**：城市高差 / 主要台地 / **低洼处（排水方向）** / **制高点（地标选址）** / **平整土方量（相对量）** |

**先看第 0 节**：它会明确报出问题。**第 0 节有警告时，不要把后面的数字当结论用。**

`--json` 含 MD 里省略的明细（`catchment.all`、`tax_potential.top_buildings`、
`noise_exposure.all`、`underdevelopment.by_zone`、`data_checks` 等）。

判读方法见 `SKILL.md` §2 速查卡。

> ⚠️ **报告里 §9–§13 都是"代理指标"**（游戏内没有税收/噪音/幸福度字段），每节都写了口径与局限。
> 引用时**必须把口径一起带上**，不要说成 ₡ 金额或游戏内数值。三个最常被误用的：
> ① **高速里程含双向路幅**（高速按方向各记一条中心线），比实际道路长度约翻一倍，§3 已打印按方向分列；
> ② **分区图斑面积不是用地面积**（图斑是 8 m × 8 m 固定栅格单元，且**含大量非建筑细节**），
>    只有图斑数与分区之间的相对比较有意义；
> ③ **税基指数是无量纲值**，只能同城纵向比，不能跨城比。

---

## 3. `scripts/city_map.py` —— 出诊断图（PNG）

```bash
<python> -X utf8 scripts/city_map.py --carto "<Carto 导出目录>" --out city_map.png \
         --layers roads,transit,catchment,density --size 1800
```
（`--carto` 同样可省略，会自动查找；连 `--carto` 都不给时会退回游戏自身的导出目录。）

可用图层：
| 图层 | 内容 |
|---|---|
| **`terrain`** ⭐ | **简单地形图（打底层）：水体 / 陡坡 / 缓坡 / 适宜建设区**。判据与坐标标定见 §2.5。**给建设建议前先看它** |
| **`arterial`** ⭐ | **修饰层：只画到主干及以上**（自动去掉支路）。**建议配图应当加它** —— 干道不被支路淹没，且"主干道画对没有"在图上可核验 |
| **`clusters`** ⭐ | **组团层（按人/岗密集程度划分）**，三色表示可达性：🟩有轨道／🟦仅公交／🟥**无直达（优先补线）**。标签带白底框、画在最上层 |
| `roads` | 路网分级：高速（暗红）/ 大路 / 主干 Medium（冷灰）/ 支路 Small（浅底纹）/ 铁路地铁（近黑）。**默认裁剪到已解锁地块** —— 非解锁区路网是**地图自带资源**，既不是玩家的成果也不是失误（`SKILL.md` 「路网口径」条） |
| `transit` | 公交与轨道线路（**线宽 ∝ 车辆数**，颜色区分方式）＋ 线名标签（车辆数/乘客数） |
| `catchment` | 沿线路按站数等分画 **600 m 腹地圆**，直观看覆盖与重叠 |
| `density` | 400 m 格网：人口（蓝底）与岗位（橙框） |
| `zoning` | 分区用途着色（住宅绿 / 商业蓝 / 工业黄 / 办公紫） |
| `contours` | 等高线（来自 Elevation.tif） |
| **`named-road`** ⭐ | **具名道路（按连通段逐段画）**，配合 `--named-road "繁荣路"`；加 `--road-interval s1:s2` 只画该**沿线区间**并标里程（「沿线定位」条 的图上依据，见 §3.0） |

> ⭐⭐ **`unlocked` 层：为什么值得单独做一层**
>
> 它画出**精确的「已解锁区域」边界**（未解锁区域压成浅灰）。
> Carto 的 `MapTile` 是**不规则四边形**且**不在规则网格上**（顶点数 5–17 不等），
> 逐个画出来就是"一堆斜方块堆在一起"，既看不出范围也不好看。
> 本层用 `dissolve_to_rings()`（`core/carto_reader.py`）把它们**合并成一条外轮廓**：
> 一组铺满区域的多边形，**内部边会被两个多边形各报一次、边界边只报一次**
> ⇒ 取 `count == 1` 的边即为准确边界，再首尾相接成闭环。
>
> **实测质量**（40 个已解锁地块）：**1 个闭环 / 52 个顶点 / 0 处自相交**，
> 环面积 ÷ 地块面积合计 = **1.0000**，**0/192** 个未解锁地块误落环内。
>
> **`--layers` 里加上 `unlocked`，或直接用 `--maps`（标准配图已全部带上它）。**

> **图例只列真正画出的等级**：只画干道时不会还挂着"支路"，避免读者以为支路被漏画了。
> 图例行距按**真实字号**计算（`12 + font.size`）—— 曾因按固定 12 px 估算高度，
> 项目一多就**跑出画布并互相压字**。

**推荐的三种组合**：

```bash
# ① 已解锁范围（看清"能规划到哪里"）
--layers unlocked,roads,arterial
# ② 干道网（给道路/拥堵建议配图）—— 也是默认值
--layers unlocked,roads,arterial
# ③ 组团公交可达性（给公共交通建议配图）★
--layers unlocked,clusters,roads,arterial,transit
# ④ 整体肌理（含支路，仅在需要看细部时用）
--layers terrain,unlocked,roads,transit
```

> **`--layers` 默认已是 `roads,arterial`** —— 只画高速/大路/主干 + 铁路地铁，**不画支路**。
> 辅助图不必画全部路网；但**画出来的必须正确**（核验方法见 `70` §1.0.2g 的四项自检）。

**逐线配图**（给"这条线该怎么改"的建议时用）：

```bash
<python> -X utf8 scripts/city_map.py --carto "<Carto 目录>" --out line11.png \
         --layers clusters,roads,arterial,transit --highlight "公交路线 11"
```
高亮该线、其余线路淡化 —— **一张图只讲一条线**，读者才能核验"它服务哪些组团、走哪条干道"。

> **建议与配图成对出现**：`city_report.py --maps <目录>` 一次性生成 4 张标准图
> （`map-terrain` / `map-arterial` / `map-transit_advice` / `map-overview`）
> **外加逐线配图 `line-<线名>.png`**，并在 §17（公交建议）与 §19（拥堵治理）自动引用。
> **给空间建议时必须同时给可核验的空间依据。**

典型用法：
* **`terrain,roads,transit`** —— 首选的"能不能建"底图（本 skill 的**最高级别约束**）；
* `roads,transit,catchment` —— 看线网问题；
* `roads,zoning,density` —— 看用地与岗位结构。

输出的 PNG 可以直接贴进报告或聊天里。

## 3.0 ⭐⭐ `core/roads.py` —— **路名几何与"沿线区间"定位**（**必读，本项目踩过大坑**）

`SKILL.md` 「沿线定位」条 要求"**说 xx 路沿线就必须给沿线区间**"。本模块是那件事的唯一正确做法。

### 两个必须避开的错误（都实际发生过）

| 错误做法 | 后果 | 实测证据 |
|---|---|---|
| 把所有同名路段**首尾相接**画成一条折线 | **用直线把互不相邻的路段连起来** —— 图上出现根本不存在的路段 | `繁荣路` 47 段被画成一条横贯 5 km 的橙色斜带（几道平行长线就是拼接 artifact） |
| 用同名路段的**合并 bbox** 当"这条路的两端" | 端点是**别处的同名小段**的角点，一个坐标就把建议说错片区 | 报告曾把"繁荣路南端"写成 y=8105（那其实是 900 m 外一条 0.18 km 小段的端点） |

### 正确口径

```python
from core import roads as R
g = R.road_geometry(carto, '繁荣路')
print(g.summary())                     # 段数 → 连通段数、各段端点与长度（**端点取真实几何端点**）
# 繁荣路：47 条路段 → 2 个连通段，总长 5.05 km
#   连通段0  4.86 km  662 顶点  起点(4550,8931) → 终点(8208,12088)
#   连通段1  0.18 km  4 顶点  起点(7095,8213) → 终点(7244,8105)

g.project(x, y)        # 任意点 → (到路距离, 连通段号, 沿线里程 s)
g.point_at(0, 4000)    # 主段 s=4000 m 处的点（画图/取断面用）
g.interval_label(3650, 4210)   # → '繁荣路 s 3650–4210 m（0.6 km）'  ← 报告里的标准写法
g.stations(carto, runs=[0])    # 站点投到路上 → 逐站里程（**已去重**、可限定连通段）
g.window(3650, 4210)           # 该区间的折线（图上高亮用）
R.lane_windows(g, carto, step=200)   # 沿线逐断面统计道路等级构成（"沿线"分析的正确做法）
```

要点：
* **连通段（run）**按"端点相接"聚合（`tol=60 m`：游戏在路口处常断开十几米）。
  **只有同一个 run 内部的顺序才有意义**；跨 run 不能连线，也不能合并统计。
* **里程 `s`** 是沿 run 从起点累计的弧长（米）。**区间必须落在 `0 ≤ s₁ < s₂ ≤ run 长度` 内** ——
  超出就说明目标位置**不在这条路沿线**，必须分开表述（见「沿线定位」条）。
* `stations()` **默认按 40 m 去重**：`POI_Location` 里同一车站会在几何两侧各记一条
  （实测某地铁站在 800 m 缓冲里被记 3 次，会把站数算成两倍）。
* `stations()` 要**按需给 `runs=[…]`**：不限定时站点会落到"离最近的那一段"上，
  **把两个片区的站混成一张表**（实测 `繁荣路` 主段沿线只有 2 个站，
  另外 14 个公交站其实在 900 m 外那条独立小段旁）。

### 图上的依据

```bash
# 草图路径
<python> scripts/city_map.py --out plan.png --layers terrain,roads,arterial,named-road \
         --named-road "繁荣路" --road-interval "3650:4210"
# QGIS 路径（见 §3.1）
"<QGIS>\apps\Python312\python.exe" scripts/carto_qgis_map.py --render-dir qgis --out plan.png \
         --bounds 5000,10500,9200,13400 --interval "繁荣路:3650:4210"
# ⭐ 无 QGIS 的制图级路径（见 §3.1a）—— 与上面 QGIS 那条的 `--interval` 口径完全一致
<python> -X utf8 scripts/city_svg_map.py --out plan.png --svg plan.svg \
         --bounds 5000,10500,9200,13400 --interval "繁荣路:3650:4210"
```
三条路径都会画出**该区间的高亮 + 两端里程标记**，读者可以在地图上直接核验。
（`city_map.py` 用 `--road-interval`，另两条用 `--interval` —— 参数名不同、口径相同。）

## 3.1 ⭐⭐ `scripts/carto_qgis_map.py` —— **用 QGIS 出精确规划图**（**先探测，再决定**）

> ⭐ **「环境」条：先假设 QGIS 不存在，探测一次，再决定要不要出图。**
> **有 QGIS** → 配图走这里（制图级），或走 §3.1a（同样制图级，见下表取舍）；
> **无 QGIS** → ⭐ **走 §3.1a 的 `city_svg_map.py`**（读同一套官方 `.qml`，**不再退回草图**）。

### 第 0 步：探测（必做，毫秒级，**不启动 QGIS**）

```bash
<python> -c "import sys; sys.path.insert(0,r'<skill>\scripts'); from core import qgis_common as Q; print('QGIS:', Q.qgis_available())"
```

`CSL2_QGIS_ROOT` 是**强制开关**：
| 值 | 行为 |
|---|---|
| 未设置 | 自动探测（已知安装位置 + 扫描 `Program Files\QGIS*`） |
| 有效路径 | **只用它** |
| `0` / `off` / `none` / 不存在的路径 | **判定没有 QGIS** —— 用它在这台机器上验证"无 QGIS 时的退化行为" |

`carto_qgis_map.py` 在**任何模式下**都先探测；没有 QGIS 时**不抛 traceback**，
打印去 §3.1a 的替代命令并返回**退出码 3**，便于脚本判定。

### 有 QGIS 时的用法

```bash
# 第 1 步（普通 Python）：把 Carto 转成 **CRS 正确**的 GeoPackage
<python> -X utf8 scripts/carto_qgis_map.py --prepare --render-dir <报告目录>/qgis

# 第 2 步（**必须用 QGIS 自带的 Python**）：出图
"<QGIS>\apps\Python312\python.exe" scripts/carto_qgis_map.py \
    --render-dir <报告目录>/qgis --out <报告目录>/plan.png --size 2000 \
    --bounds <x0>,<y0>,<x1>,<y1>            # 本地米制，与报告口径一致
    --title "…" --interval "繁荣路:3650:4210"
```

> ⚠️ **`--layers` 的方向**：`QgsMapSettings.setLayers()` 里**第一项画在最上面**。
> 默认顺序把 `Zoning_Boundary` 放第一位（**分区图斑盖住建筑**）、
> `Route_Centerline` 放最后一位（**公交线路被路面盖住**）。
> 要改就把这两项往前/往后挪 —— 与 `city_svg_map.py` **语义相同，顺序可直接照搬**。
> ⭐ 本项目实测过这个方向：`Zoning_Boundary,Building_Boundary` → 分区在上；
> 反过来 → 建筑在上。**别凭直觉猜。**

> ⚠️ **两条内部分支的纸面密度不同**：`--no-legend --no-scalebar` 且无 `--title` 时走
> "直接渲染"分支（输出恒为 `--size × --size`、QGIS 按 **96 dpi** 换算样式里的 mm/pt）；
> 否则走 `QgsPrintLayout` 分支（按 **300 dpi** 导出）。
> 同一套样式在两条分支上"线粗细 / 字号"看起来差约 2.5 倍 —— **是 QGIS 的行为，不是 bug**；
> 要可比就固定走版式分支（给 `--title`）。

### ⚠️ 四个必须知道的坑（都已在本模块里解决）

1. **GeoJSON 的 CRS 是"假的"**：`GeoJSON/` 坐标是归一化值（×111006.1 才是米）且**没有 CRS**，
   而 GeoJSON 规范规定 CRS 一律 WGS84 → **OGR/QGIS 一律按 `EPSG:4326` 读**，
   于是 **14 km 宽的城市被当成 0.13°（≈ 千分之一大小）的点，图面空白**。
   ⇒ 必须**把坐标平移进 EPSG:32631 的真实米制区间并写成 GeoPackage**（自带 SRS 表）。
   `qgis_common.prepare_qgis_layers()` 做的就是这件事。
2. **GeoJSON 驱动忽略 URI 里的 `crs=` 参数**，加上它图层直接 `isValid()==False`；`.prj` 同目录也不认。
   ⇒ 不要试图用 URI 覆盖 CRS。
3. **Qt 不再自带字体**：不设 `QT_QPA_FONTDIR` 时中文标注整片变豆腐块。
   `qgis_env()` 会自动把系统字体复制到临时目录并指过去。
4. **必须带上完整环境变量**（`PYTHONPATH` / `QGIS_PREFIX_PATH` / `PATH` 含 Qt5 bin / `PROJ_LIB` /
   `QT_QPA_PLATFORM=offscreen`）。**不要自己拼，用 `core/qgis_common.py` 的 `qgis_env()`。**
   * ⭐ **`PATH` 里必须有 `<QGIS>/apps/qgis-ltr/bin`**（`qgis_core.dll` 在那儿）。
     少这一项时 `import qgis.core` 报
     `ImportError: DLL load failed while importing _core: 找不到指定的模块` ——
     **错误信息完全不提 PATH**，能查很久。`qgis_env()` 现已自动带上（`paths['qgis_bin']`）。

### 图层与顺序

| 图层 | 官方 QML | 说明 |
|---|---|---|
| `Zoning_Boundary` | `*-Zoning-Boundary (By Zoning).qml` | 分区用途（**默认在最上** —— 会盖住建筑） |
| `Building_Boundary` | `*-Building-Boundary.qml` | **逐栋建筑轮廓** |
| `Network_Boundary` | `*-Network-Boundary.qml` | ⭐ **真实路幅**（含人行道、标线、水域）。**画路用它** |
| `Network_Centerline` | `*-Network-Centerline (Chinese).qml` | 渲染器是 **nullSymbol**（只出**路名标注**，不画线）—— 别指望它画路 |
| `POI_Location` | `*-POI-Location (Chinese).qml` | 站点/服务设施中文标注（外层的 `pointCluster` 会把邻近点聚合成气泡） |
| `Route_Centerline` | `*-Route-Centerline (By Transport).qml` | 公交/轨道线路（**默认在最下，会被路面盖住**） |
| `Area_Boundary` | `*-Area-Boundary (Chinese).qml` | 行政区块（**默认隐藏** —— 不透明色块会盖住建筑） |

**出图内容**：标题 + 图例（按当前地图范围过滤）+ 比例尺（米制）+ 指北针可选，
通过 `QgsPrintLayout` 输出（`--no-legend` / `--no-scalebar` 可关）。

> ⚠️ 图例条目多时**会溢出页面**（实测 `Network_Boundary` 一层就有 25 条规则）——
> QGIS 版图例框是固定 `58×95 mm`。§3.1a 的实现改成"按实际画出来的条目 + 自动缩放字号"，
> 不会溢出。

### 与另两条路径的分工

| | `analysis/city_map.py`（Pillow 草图） | `carto_qgis_map.py`（QGIS） | `city_svg_map.py`（§3.1a，零依赖） |
|---|---|---|---|
| 依赖 | numpy + Pillow | **需要本机 QGIS** | Pillow（numpy 都不需要） |
| 速度 | 秒级 | 准备 ~5 s + 渲染 10–60 s | **20–30 s**（1600–2400 px） |
| 样式 | **自己写的**配色 | 官方 `.qml`（QGIS 解释） | 官方 `.qml`（**自己解释**） |
| 精度 | 工程草图 | 制图级 | **制图级（同一套要素与配色）** |
| 无 QGIS 时 | 少出图 | 不可用 | ⭐ **首选** |

## 3.1a ⭐⭐ `scripts/city_svg_map.py` + `core/qml_style.py` —— **没有 QGIS 也出制图级图**

> **为什么可能有这条路径**：`.qml` 不是 QGIS 的私有格式，它就是 XML
> （规则 `filter` + 符号 `SimpleFill` / `SimpleLine` / `SimpleMarker`）。
> 把这两样读出来，**官方配色 / 官方线宽 / 官方分级规则就能在没有 QGIS 的机器上原样复现**。
> **精度不来自 QGIS，来自数据**；QGIS 提供的是"制图加工"这一层，而这一层能自己实现。

### 用法

```bash
# 出图（可同时出 PNG + SVG）；本脚本**从不探测、也从不启动 QGIS**
python -X utf8 scripts/city_svg_map.py \
    --carto "<Carto导出目录>" --out plan.png --svg plan.svg --size 2000 \
    --bounds <x0>,<y0>,<x1>,<y1> \
    --title "…" --interval "繁荣路:3650:4210" \
    --check --report plan.check.json
```

CLI 与 `carto_qgis_map.py` **刻意保持一致**：`--bounds`（本地米制）/ `--size` /
`--title` / `--style-set` / `--layers` / `--hide` / `--interval` / `--interval-run` /
`--no-legend` / `--no-scalebar`。多出来的：

| 参数 | 作用 |
|---|---|
| `--svg <文件>` | 额外出一份**真矢量** SVG（手写，零依赖），排版/放大用 |
| `--canvas-w <mm>` | **纸面宽度**。`.qml` 里的 mm/pt 是**纸面尺寸**，靠它换算像素（默认 210 mm） |
| `--size-h` | 输出高度（默认与宽度相同 → 方图） |
| `--north` | 画指北针（默认不画） |
| `--no-labels` | 不画路名 / POI 标注 |
| `--check` / `--report` | ⭐ **打印 / 写出精度自证数字**（见下） |

### 推荐的两种图层顺序（**第一项在最上面**，与 QGIS 路径同义）

```bash
# ① 与 carto_qgis_map.py 默认逐项一致（分区盖住建筑；公交线路被路面盖住）
--layers Zoning_Boundary,Building_Boundary,Network_Boundary,Network_Centerline,\
POI_Location,Route_Centerline,Area_Boundary

# ② 诊断推荐：线路 → 站点 → 路名 → 路网 → 分区 → 建筑
--layers Route_Centerline,POI_Location,Network_Centerline,Network_Boundary,\
Zoning_Boundary,Building_Boundary,Area_Boundary
```

### `--check`：**图不能自证，数字可以**

| 输出项 | 它证明什么 |
|---|---|
| `bounds_roundtrip_max_err_m` | 世界 → 像素 → 世界往返误差（应为 0） |
| `pavement_width` | 抽样路面多边形 `面积 ÷ 中心线长度` vs 属性 `Width` 的相对误差 —— **证明画的是真实路幅面**，不是"按等级给固定线宽" |
| `scalebar` | 比例尺分段像素 ÷ 米数 与图面 `m/px` 是否一致 |
| `layers[].drawn / culled` | 各层真正画了多少、因视口外剔除多少 |
| `labels[].placed / dropped` | 标注放上多少、因避让丢弃多少 |
| `rules_unparsed` | ⚠️ **样式里没能解析的规则**（这些规则不会生效）——必须为 0 或已被说明 |
| `degraded` | ⚠️ 无法复现的符号层（`SvgMarker`/`FontMarker` → 同色圆点近似） |

本项目实测（江东，`Styles/Street`，1:60,000）：

```
世界→像素→世界 最大往返误差：0 m
真实路幅校验：1760 段 —— 中位相对误差 2.479%，P90 11.905%
比例尺校验：1100 m = 208.4 px → 5.278150 m/px（应为 5.278150）
```

> ⚠️ **路面多边形的面积 ÷ 长度**要过滤掉 `长度 < 3×路宽` 的碎段
> （路口过渡/圆角/斜交会让这个比值失真）；`--check` 会把过滤掉多少条一并报出来。

### 与 QGIS 渲染的一致性（本项目实测，**逐像素**）

同一范围、**同一纸面密度**（本脚本 `--canvas-w 529.17` ≡ QGIS 直接渲染分支的 96 dpi）
下对比两边的纯色像素数：

| 配色 | QGIS | `city_svg_map.py` | 比值 |
|---|---|---|---|
| 分区（5 类合计） | 72,505 | 90,674 | 1.25 |
| 建筑灰 | 97,111 | 86,929 | 0.90 |
| 高速深绿 | 1,402 | 1,428 | **1.02** |
| 高速浅绿 | 10,984 | 10,960 | **1.00** |
| 水路浅蓝 | 185,580 | 179,541 | 0.97 |
| 偏蓝（公交线路） | 6,508 | 5,999 | 0.92 |
| 道路掩码重合度 | — | — | **0.83**（残差 `dx=0, dy=0`） |

**结论：几何位置逐像素对齐（残差 0），配色与官方样式一致**；
剩下 3–17% 的差异来自描边抗锯齿与"1 mm 等于多少像素"的声明不同（见下）。

### ⚠️ 五个必须知道的差异（**都不影响任何坐标**）

1. **mm / pt 是纸面尺寸**：`.qml` 里线宽 `MM`、字号 `Point`。本脚本按 `--canvas-w`
   声明换算（默认 2000 px / 210 mm = **242 dpi**）；QGIS 直接渲染分支按 **96 dpi**。
   所以看起来"粗细/字号"差约 2.5 倍 —— **两者都忠实于样式文件**，只是"一毫米等于多少像素"
   这个声明不同。**要 QGIS 那种清爽感就调大 `--canvas-w`（或减小 `--size`）。**
2. **标注是"沿切向的直排旋转"**，不是 QGIS 的 `placement=3` 沿弧弯曲。位置与角度对，
   **弧线不会跟着弯**。路名走的是 `core/roads.group_runs()` 的**连通段**口径
   （与报告里"沿线里程"同一套），所以单段很短的路也能拿到标注。
3. **POI 图标退化为同色圆点**：官方样式用 `SvgMarker` / `FontMarker`（46 + 11 个），
   零依赖下无法复现图形；`--check` 的 `degraded` 会如实列出。
4. **不实现 `pointCluster`**：QGIS 会把 3 mm 内的邻近点聚合成气泡，本脚本**每个点都画**。
   做"站点腹地"这类诊断时这反而更有用，但**点数与 QGIS 图不同**。
5. **面状图案 `LinePatternFill` 近似为斜线填充**；`Area_Boundary` 与 QGIS 路径一样默认隐藏。

### 已知未支持（会进 `rules_unparsed`，**不会静默出错**）
依赖几何或渲染上下文的 QGIS 表达式：`$area`、`@zoom_level`、`length()` 等。
实测只有 `Styles/Topo` 的建筑层用到（1 条规则），`Street` / `Plan` 两套**全部解析通过**。
`regexp_match("F", 'p')` 已按等价形式归一到 `"F" ~ 'p'`。

## 3.2 ⭐⭐ `core/naming.py` —— **地点命名**（准则：**人能快速定位与理解**）

> ⭐ **唯一准则（`SKILL.md` 「命名」条）**：**一切命名规则都应当以「能被人类快速定位和理解」为准则。**
> 下面的所有细则都从这一句推出；**细则冲突时回到这一句裁决**。

### 四条可判定的检验（`audit_names()` 逐条实现）

| # | 检验 | 判定 | 实现 |
|---|---|---|---|
| ① | **好懂** | 主名是人话（`北端预留区`），不是流水号或里程串 | `check_name()` |
| ② | **简短** | 主名 ≤ **16 字**，超了起别名 | `check_name()` + `NAME_MAX_CHARS` |
| ③ | **唯一** | 一名一地、一地一名 | `audit_names()` 重名检测 |
| ④ | **可核验** | 括号里的依据落在**游戏里看得见的实物**上（路名+里程 / 地标+方位距离 / 地块号） | `check_basis()` |

### 为什么需要它（数据现实）

Carto 里**只有三类是真正的地名**，其余都是机器标识：

| 字段 | 实测内容 | 能当主名吗 |
|---|---|---|
| `MapTile.Name` | **232 个全是纯数字**（`Map Tile 1227156`） | ❌ **流水号**，游戏地图上不显示 |
| `Zoning_Boundary.Name` | 只有 20 种**分区类目**（"欧洲中密度住宅""工业设施"） | ❌ 不是地名，但是很好的"这一带是什么"描述 |
| `Area_Boundary` 里 `District` | **4 个区名**：新岸区 / 北渡区 / 新湖区 / 月湖区 | ✅ |
| `Network_*.Name` | **路名**（繁荣路 / 北渡大道 / 羊城路…） | ✅ **最强**（配合沿线里程可精确定位） |
| `POI_Location.Name` | **设施名**（火车站 / 地铁总站 / 广播电视塔 / 消防站（城市）…） | ✅ |

⇒ **流水号不是"禁止出现"，而是"当不了主名"**（检验 ① 过不了）；它作括号里的精确定位附注完全正当。

### 用法

```python
from core import naming as N

ALIASES = {'1227156': '北端预留区', '1227158': '北端产业预留区'}   # 主名（人记得住）
nm = N.NameIndex(carto, aliases=ALIASES)
nm.tile_entry('1227156', corridor='繁荣路')
# → label : '北渡区·北端预留区（到繁荣路北端路口 545 m；地块号 1227156）'
#   short : '北端预留区'                       ← 图上标签 / 正文首次出现用它
#   basis : '到繁荣路北端路口 545 m；地块号 1227156'   ← 括号里的依据
#   where / km2 / zoning / buildings / cx / cy / bbox / name_check
nm.short_label(x, y)                    # 最短可读标签（画图用）
nm.describe(x, y, roads=['繁荣路'])      # 一句话定位（短名 + 依据）
nm.describe(x, y, brief=True)           # 只要短名（正文重复提及时）
nm.zone_mix(x, y, radius=400)           # → '高密度办公楼 43% / 中式高密度住宅 27% / …'
nm.audit_names(list(ALIASES))           # ⭐ 交付前跑一次：四条检验 + 重名 + 缺别名
N.check_name('北端预留区')               # ① 好懂 ② 简短
N.check_basis('到繁荣路北端路口 545 m')   # ④ 可核验
```

> ⭐ **`corridor=<本轮主轴路名>` 值得用**：读者要定位的是"它和本轮讨论的主轴什么关系"，
> 而不是"它离哪条不相干的路最近"。实测某地块最近的路恰是与方案无关的一条，
> 真正让人一眼找到的是"**到繁荣路北端路口 545 m**"。
> 判据是**显著性**：只有"到走廊端点"不比"到任意具名路"更远（留 10% 容差）才采用该写法。

**别名表建议存成报告目录下的 `names.json`**（`{"aliases": {"1227156": "北端预留区", …}}`）——
这样出图脚本与报告共用一份，且**同一地点跨期同名**。

### 标准和反例

| | 写法 |
|---|---|
| ✅ | `北端预留区（羊城路主段 s≈570 m 西北 746 m；地块号 1227156）` |
| ❌ | `地块 1227156` —— 流水号当主名，游戏里看不到这个词 |
| ❌ | `羊城路主段 s≈570 m 西北 746 m` —— 依据当主名，22 字，读者要逐字解码 |

### 命名顺序（依据从哪来，按可核验性排序）

| 序 | 条件 | 依据写法 |
|---|---|---|
| ① | 贴着强地标 ≤200 m | `消防站（城市）西北 299 m` |
| ② | 地块离具名路 ≤200 m | `羊城路主段 s≈446 m 沿线 184 m` |
| ③ | 强地标 ≤500 m | `地铁总站西南 220 m` |
| ④ | 具名路 ≤600 m | `繁荣路主段 s≈4314 m 沿线 58 m` |
| ⑤ | 边界最近的路（兜底） | `羊城路主段 s≈570 m 西北 746 m` |
| ⑥ | 任意地标 / 行政区 + 方位 | `北渡区北部` |
| ⑦ | **地块号** | 只作括号附注 |

### 五条实测踩坑

1. **别一律用"最近的强地标"**：北部 7 块地会被**全部**叫成"消防站（城市）北 1 170 m" —— **无法区分**（检验 ③ 失败）。
   必须"近处地标优先、稍远就改用路 + 里程"。
2. **别用 `bbox` 求"地块离路多远"**：地块是不规则/狭长多边形。实测某地块
   **中心**离最近具名路 970 m，而**边界**只隔 184 m —— 命名要问"它靠哪条路"，所以按**边界**算。
3. **两个距离不能混**：`地块边界 ↔ 道路红线` 与 `道路端点 ↔ 地块边界` 是两个数
   （实测同一块地 **1 123 m vs 545 m**，差一倍）。写依据时**必须说明是哪一个**。
4. **自动发现路名时要过滤 `Object`**：`Network_Centerline` 里还有**地铁轨道 / 火车轨道 / 航道**，
   它们也有 `Name`，不过滤会冒出"地铁轨道主段 s≈1395 m 沿线 102 m"这种不存在的路。
5. **求"点到地块边界"的距离必须逐边取垂足，不能只比顶点**：实测某地块离路口 121 m 的最近点
   **落在一条边的中段**，按每 4 个顶点抽样会量成 **543 m（差 4 倍）**，于是"显著性判据"误判、
   依据退回到一条不相干的路。
6. **依据必须与主名用同一个参照物**：一度出现"主名指 A 路、依据写 B 路" ——
   因为主名按**边界**最近的路选、依据却取了按**中心**最近的路。两者不是一回事。

## 2.5 `core/terrain.py` —— **可建造性**与坐标标定（最高级别约束）

`SKILL.md` 第 0 节「最高优先级」条：**水体与陡坡不得作为任何建设建议的落点**。本模块提供判据。

```python
from core import terrain as T
ox, oy, q = T.solve_utm_offset(carto)          # GeoJSON → EPSG:32631 平移量（中位误差 0.05 m）
b = T.buildability(carto, (ox, oy))            # 分级栅格
T.classify_point(b, utm_x, utm_y)              # → 水体/陡坡/缓坡/适宜/None
T.is_buildable(b, utm_x, utm_y)                # → True/False（水体与陡坡为 False）
```

| 类别 | 判据 | 建议 |
|---|---|---|
| **水体** | 高程 ≤ 1 m 且坡度 < 1° | ❌ **禁止** |
| **陡坡** | 坡度 > 25° | ❌ **不建议** |
| 缓坡 | 坡度 10–25° | ⚠️ 可建，但写明"需整地、代价更高" |
| **适宜建设区** | 坡度 ≤ 10° 且非水体 | ✅ 优先 |

> **⚠️ 调用方传的是 GeoJSON 坐标、栅格是 UTM 坐标** —— `city_report.py` 内部已统一处理
> （`BUILDABLE()` 会自动加平移量）。自己写脚本时**别忘了这一平移**，否则会得到一片 `?`。
>
> **标定为什么可信**：中位误差 0.05 m ≈ 数据 0.1 m 量化精度；且标定后**建筑处坡度中位 0°**、
> 而全图地形中位 8.1° —— 城市建在平地上，物理自洽。
> **踩坑记录**：早期实现把 `ModelTiepoint` 的 X/Y 直接当左上角（应为 `x0 = X − i·sx`、
> `y0 = Y + j·sy`），导致栅格整体偏移 21504 m；且坐标→像素必须用 `floor` 而非 `int()`。

> 实测已知的读图注意事项（不是 bug，是数据/工具特性）：
> - **站点腹地圆在密集走廊会大幅重叠**，看起来"糊成一片"。这是真实覆盖情况；要看清单个站点请改用
>   `city_report.py` §6 的站点腹地**表格**（有具体人口/岗位数字）。
> - **`contours` 常常只画得出城市南缘**（栅格覆盖限制）。**但 `terrain` 层已修正坐标标定**，
>   实测本地 `Elevation.tif`（14.3 km）**是覆盖城市的**；若 `terrain` 层空白，先查
>   `solve_utm_offset()` 是否返回 `None`（说明栅格缺失或建筑缺 `Elevation`）。
> - 图例只列出**图上实际存在**的类别；`Small` 支路在数据量少时几乎不可见，别据此断言"支路缺失"——
>   用 `city_report.py` §3 的长度比来判断。
> - `--size` 越大线条越细、标签相对越小；默认 2200 在多数屏幕上够用。

> Carto 的 `Styles/*.qml` 是配套 QGIS 样式。用
> `scripts/carto_qgis_map.py` 可**直接出制图级规划图**（真实路幅/路名/建筑轮廓/中文标注）
> —— 见 **§3.1**；**没有 QGIS 的机器**用 `scripts/city_svg_map.py` 出**同一套官方样式**的
> 制图级图 —— 见 **§3.1a**（本项目实测几何逐像素对齐、配色比值 0.9–1.0）。
> Pillow 脚本（`city_map.py`）的价值是**离线、快、可批量**，适合自查。

---

## 3.3 ⭐⭐ `scripts/export_report.py` —— **Markdown 报告 → 合规 DOCX + XLSX**（默认交付形态）

> **规范原文**：`references/110-deliverable-format.md`（**normative**）
> **格式常量**：`core/deliverable_style.py`（**唯一实现**，改格式只改这一处）
> 本脚本**不含任何字号/颜色/缩进字面量** —— 全部从 `deliverable_style` 取，避免规范与实现脱钩。

**为什么需要它**：`city_report.py` 产出的是 **Markdown 中间稿**（内容对，但没有版式）。
默认交付物是 **DOCX 报告 + XLSX 数据附录**，所以必须再走一步落文档。

```bash
# ① 实算 → Markdown（+ 指标 JSON + 配图）
<python> -X utf8 scripts/city_report.py --carto "<Carto 目录>" --maps maps/ \
    --out city_report.md --json city_metrics.json

# ② 落交付物：DOCX + XLSX（生成末尾自动打印格式合规校验）
<python> -X utf8 scripts/export_report.py --md city_report.md --json city_metrics.json \
    --maps maps/ --city "<存档名>" --outdir .

# ③ 事后单独复查（或核查别人给的文档）
<python> -X utf8 scripts/export_report.py --check "<存档名>规划报告.docx" "<存档名>规划数据附录.xlsx"
```

| 参数 | 说明 |
| --- | --- |
| `--md` | `city_report.py` 产出的 Markdown（**必需**）|
| `--json` | 指标 JSON → 生成 XLSX 的 `1-概览` 工作表（摊平全部指标）|
| `--maps` | 配图目录；把 Markdown 里的**相对路径**补成可嵌入的绝对路径 |
| `--city` | 存档名 → 决定文件名与封面标题（Windows 非法字符自动替换）|
| `--name` | 覆盖报告名（默认 `<城市名>规划报告`）|
| `--outdir` | 输出目录（默认当前目录）|
| `--no-toc` | 不生成目录页（默认生成：封面 → 目录 → 正文）|
| `--md-only` | **仅在玩家明确要求 Markdown 时使用**：只确认 `.md`，不落 docx/xlsx |
| `--check` | 只做格式合规校验，返回码 **0=PASS / 2=FAIL** |

**产出**

| 文件 | 内容 |
| --- | --- |
| `<存档名>规划报告.docx` | 封面 + 目录 + 正文；报告里每张表落成规范表，每个 `![题](图)` 落成图（题在图下）|
| `<存档名>数据附录.xlsx` | `1-概览`（来自 `--json`）+ 报告里**每张数据表一张工作表**，命名 `序号-节名` |

> ⚠️ **XLSX 的工作表数是"报告里有多少张表"**（本项目实测 47 张表 → 48 个工作表）。
> 这不是 bug：规范要求"每个数据表一张表"，便于逐表核对。
>
> ⚠️ **`--check` 必须在交付前跑并且全 PASS**。它逐项比对：
> 页面与页边距、基准样式的中文字体与字号、标题字号、**每个 run 是否都带 `w:eastAsia`**
> （防中文掉宋体）、**正文首行缩进 420 twip / 列表悬挂 240 twip**、表格列宽 ≤16.2 cm 与表头底纹、
> 行不跨页、图宽 ≤16.2 cm、页脚 `PAGE` 域、**无残留 Markdown 标记**、
> 工作表名与冻结、数值是否为数字型。
>
> **失败时改 `core/deliverable_style.py` 后重新生成，不要手工在 Word 里改** —— 下次生成就丢。

**两条依赖**：`python-docx` + `openpyxl`（捆绑运行时已含）。
`city_report.py` / `city_map.py` 只要 numpy + Pillow，**落文档这一步才需要它们**。

**已踩过的三个坑（都已在实现里解决，改代码时别退回去）**
1. **`cell.text = ""` 会留下一个没有 `rPr` 的空 run** → 中文掉成宋体。
   必须先把 `cell.paragraphs[0].runs` 删干净再写自己的 run（footer 同理）。
2. **只设 `run.font.name` 不够** —— 必须同时写 `w:ascii` / `w:hAnsi` / `w:eastAsia`。
3. **行内标记是嵌套的**：源稿里有 `**……\`字段名\`……**`。
   行内解析器必须**递归**，否则反引号会原样漏进 Word（表格单元格尤其容易漏）。

## 3.3 ⭐⭐ `scripts/city_archive.py` —— **成果归档**（「归档」条：只留人能看懂的）

> ⭐ **规则**：最终输出文档写完后（无论 **Word + Excel** 还是 Markdown），
> **把所有文件归档到一个文件夹内；中间计算的程序、脚本、数据全部删除；
> 最终呈现一定为简明且易于被人类理解。**

**保留 / 删除的界线只有一个问题：人会不会直接打开它？**

| 保留 | 删除（过程产物） |
|---|---|
| 最终文档 `*.md` / `*.docx` / `*.xlsx` / `*.pdf` | 全部脚本 `scripts/`、`*.py`、`*.ps1` |
| 文档引用的图 `*.png` / `*.jpg` / `*.svg` | 机器可读中间数据 `city_metrics.json`、`structure*.json`、`*.csv` |
| 人类可读对照表 `names.json` | 诊断底稿 `city_report.md`、`structure7.md`（结论已进最终文档） |
| | 出图中间件 `qgis/`（GeoPackage + 转换用 GeoJSON，可秒级重建） |
| | 缓存/临时 `__pycache__`、`*.log`、`*.tmp`、字体目录 |

```bash
<python> -X utf8 scripts/city_archive.py --dir <报告目录>            # 只检查（默认，不删任何东西）
<python> -X utf8 scripts/city_archive.py --dir <报告目录> --apply    # 执行归档
```

**它做四件事**：
1. 把目录内容分成**保留 / 删除 / 需人工确认**三类打印出来（让人先过一眼再删）；
2. **没有最终文档时拒绝执行**（退出码 2）—— 避免"把成果删没了"；
3. 检查最终文档里有没有「数据源 / 口径声明」字样 —— 这是**自包含提醒**：
   删掉 `city_report.md` 之后，被引用的数字必须已经写在正文里。
4. **附加执行一次「正文体检」**（`scripts/core/text_lint.py`，随 `--dir` 自动调用）：
   查正文里的 **skill 内部标签**（`铁律` / `SKILL.md` / `references/`）、**节号符号 `§`**、
   以及**修订注**（`本轮新增` / `上一版` / `第 N 轮`…）。
   **命中即先改文档、再归档**：**归档默认中止**，要硬归档得显式加 `--force`。
   规范条款见 `references/110-deliverable-format.md` 第 13 节。

### 顺序固定：**先导出交付物 → 再归档**

```bash
# ① 导出（DOCX + XLSX 直接写进归档目录）
python -X utf8 scripts/export_report.py --md city_report.md --json city_metrics.json \
       --maps maps/ --city "<存档名>" --outdir <报告目录>
# ② 归档（清掉 md 底稿 / json / maps / scripts / qgis）
python -X utf8 scripts/city_archive.py --dir <报告目录> --apply
```

**归档后目录里只该剩**：最终文档 + 配图 + `names.json`。

### ⚠️ 前提：自包含（做不到就不许删）

> **只给玩家这一个文件夹，他能不能看懂全部结论、并核对我引用的每个数？**

* 能 → 放心删；
* 不能 → **先补文档**（把数字写进正文），再归档。

### "简明易懂"不只是删文件

删完之后还要**通读一遍文档**，确认：
① 结论在开头（不是埋在第十节）；② 每个数字都带口径；
③ 地名与图上的标注一致（「命名」条）；④ 没有"见上文 / 见某文件"这类需要来回翻的指代。
**归档的目标是让玩家一次读完就懂。**

---

## 3.4 ⭐⭐ `scripts/city_docx_polish.py` —— **用 Univer 精细化 DOCX**（dsh-univer-office 插件）

> ⭐ **分工**：**python-docx（`export_report.py`）管"符合规范"；Univer（univer-doc）管"看起来对"。**
> 两者都要，顺序固定：**落规范 DOCX → Univer 精细化 + 逐页视觉验证 → 导出 → 再跑 `--check`**。

### 为什么不能只留一边（实测数据）

拿一份按 110 规范直出的探针 DOCX 做三态对比：

| 指标（OOXML 实测） | python-docx 直出 | 经 Univer 往返 | **Univer 加精细化后** |
|---|---|---|---|
| 页面 / 边距 / 版心 | ✅ 21×29.7 / 2.2,2.0,2.4,2.4 / **16.2 cm** | ✅ **完全保真** | ✅ 保持 |
| `w:eastAsia`（中文不掉宋体） | 39 | 35 | 35 |
| 首行缩进 420 twip | ✅ | ✅ | ✅ |
| 页脚 `PAGE` 域 | ✅ | ✅ **域存活** | ✅ |
| **`w:keepNext`**（标题不孤在页尾） | **0** | 0 | **5** |
| **`w:keepLines`**（图题不跨页） | **0** | 0 | **6** |
| 表头跨页重复 `w:tblHeader` | 1 | 1 | 1 |
| `--check` 110 合规 | **PASS** | **PASS** | **PASS** |

**两条结论**：
1. **往返是安全的**：页面几何（21×29.7 cm、边距、版心 16.2 cm）**逐位保真**，
   页脚的 `PAGE` 域也活着（Univer 模型里是 `第 \x1f\x1e 页` 的控制符）。
   ⇒ **Univer 可以安全地作为"最后一道精修 + 导出"**；
2. **加分项是真的**：`keepNext` / `keepLines` 原本**一个都没有** ——
   标题会孤在页尾、图题会与图分离。**现已直接写进 `deliverable_style`（确定性修复），
   不再依赖 Univer**；Univer 的价值落在那张**逐页截图**上。

### 用法

```bash
# ① 生成 Facade JS 并打印工具调用序列
<python> -X utf8 scripts/city_docx_polish.py \
    --docx "<报告目录>/<城市名>规划报告.docx" \
    --univer "<报告目录>/<城市名>报告.univer" --js-dir "<报告目录>/_univer_js"
```
它先在**纯 Python 侧**把 110 的关键项读回来比对（页面/边距/版心/`eastAsia`/缩进/域/分页控制），
再生成 `polish_doc.js` 与 `verify_doc.js`，并打印 `univer_new → univer_worktree → univer_import
→ univer_execute → univer_screenshot → univer_export → --check` 的完整参数。

### 工具调用要点（照做，别省）

| 步 | 工具 | 要点 |
|---|---|---|
| 1 | `univer_new` | 建 `.univer` 容器（不覆盖已有文件） |
| 2 | `univer_worktree` | `action:"create"` 开草稿工作树；**所有写入都必须带 `worktreeId`** |
| 3 | `univer_import` | **`docType:"traditional"`** —— 只有 traditional 才保 A4 页面设置；`modern` 会把页面几何改写成固定版式且**不可恢复** |
| 4 | `univer_execute` | 跑 `polish_doc.js`：标题 `keepNext`、图题 `keepLines`、表格 `setHeaderRowCount(1)`，并**逐项断言**（没生效就抛错） |
| 5 | `univer_screenshot` | ⭐ **逐页 PNG，必须真的看图**：标题孤行、图题与图分离、表格溢出版心、半页空白 —— **这些只有看图才知道** |
| 6 | `univer_execute` | 跑 `verify_doc.js`（只读，不产生修订）：核对 `pageCm / marginCm / contentCm` = 21×29.7 / 2.2,2.0,2.4,2.4 / **16.2** |
| 7 | `univer_export` | 覆盖为最终 DOCX（用**已验证的 worktree 作用域**） |
| 8 | `export_report.py --check` | **交付前必跑**：Univer 导出的件仍须 110 全 PASS |

### 三个实测限制（别浪费时间找替代方案）

1. **Univer 的渲染器不显示 `PAGE` 域的数字** —— 截图里页脚是"第  页"。
   这是**渲染限制，域本身完好**（`--check` 的"页脚含 PAGE 域"仍 PASS）。
   **不要为了"让截图有页码"去写死页码**（那会让域丢失，反而违规）。
2. **`FDocumentImage.getInfo()` 不回读宽高** → 图宽请以 `--check` 的"图片宽度 ≤16.2 cm"为准。
3. **表格表头行数是幂等的**：python-docx 已写 `w:tblHeader`，Univer 再 `setHeaderRowCount(1)`
   不会重复计数（但**不要**用它替代 python-docx 的写法 —— 规范实现仍只有一处）。

> ⚠️ **文件是过程产物**：`.univer` 与 `_univer_js/` **不进交付目录**，
> 由 `city_archive.py` 清理（「归档」条）。交付目录只留 `docx` / `xlsx` / 配图 / `names.json`。

---

## 4. PDF 提取工具链（两本中文书写在 `extract/` 里，一般不需要重跑）

| 脚本 | 作用 |
|---|---|
| `scripts/tools/pdf_diagnose.py` | 判断 PDF 是"扫描件（无文本层）"还是"提取器能力不足"。**先跑它** |
| `scripts/tools/pdf_text_extract.py` | 纯标准库 PDF 文本提取（处理 FlateDecode、ToUnicode CMap、对象流、Z 型…）。扫描件会如实返回 0 字符 |
| `scripts/tools/pdf_ocr_pipeline.py` | 扫描件 → Pillow 导出页面图片（可缩放） |
| `scripts/tools/ocr_winrt.ps1` | 用 **Windows 内置 OCR**（Windows.Media.Ocr）识别中文，无需安装任何东西 |
| `scripts/tools/ocr_books.py` / `scripts/tools/run_extract_all.ps1` | 上面几步的批量驱动 |

**两个关键坑（都已在脚本里解决）**
1. 扫描件没有文本层 —— 这不是提取失败，是原件如此。用 `pdf_diagnose.py` 确认：
   每页 `/Resources` 只有一个 `/XObject /Im0`、`/Subtype /Image`、`/Filter /DCTDecode`，且 `/Font` 数量为 0。
2. 在受限/沙箱进程里，WinRT 的 `StorageFile.GetFileFromPathAsync` 会抛
   `UnauthorizedAccessException`。**必须改成把字节读入 `InMemoryRandomAccessStream`**（`ocr_winrt.ps1` 已这么做）。
   另外：Windows OCR 对中文扫描页在 **0.55 缩放**下识别率优于原尺寸。

调用方式（注意用 `powershell`，不要用 `pwsh`）：
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/tools/ocr_winrt.ps1 `
    -ImageDir <图片目录> -OutDir <输出目录> -Lang zh-Hans-CN
```
若系统没有 OCR 语言包，脚本以退出码 3 + `NO_OCR_ENGINE` 失败 ——
此时应**如实报告"无法查看 PDF"**，不要靠书名猜测内容。
