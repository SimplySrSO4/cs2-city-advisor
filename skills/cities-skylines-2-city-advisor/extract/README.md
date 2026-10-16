# extract/ —— 两本中文书的提取产物（核查原始出处用）

## 为什么是 OCR

目录下两本 PDF **都是扫描件**：每页只有一张整页 JPEG（`/Subtype /Image` + `/Filter /DCTDecode`，
`/Font` 数量为 0），**没有文本层**。任何文本提取器都会读到 0 字符 —— 这不是工具缺陷，是原件如此。
证据与复现命令见 `../references/50-book-urban-planning-principles.md` 的「证据（可复现）」一节。

因此走的是：**Pillow 导出页面图片 → Windows 内置 OCR（Windows.Media.Ocr，zh-Hans-CN）→ 去冗余空格 → 逐页文本**。
工具见 `../scripts/tools/pdf_ocr_pipeline.py`、`../scripts/tools/ocr_winrt.ps1`、`../scripts/tools/ocr_books.py`。
（`scripts/` 的完整布局见 `../references/80-how-to-use-toolkit.md` §0.0）

## 目录内容

```
extract/
├─ URBAN-PLANNING-full.clean.txt   《城市规划原理》第3版 全书合并文本（含 ===== PAGE n =====）
├─ URBAN-PLANNING-full.raw.txt     同上，未清洗版（保留 OCR 原始输出）
├─ URBAN-PLANNING-full.stats.json  逐页字符数统计
├─ BRT-full.clean.txt              《城市快速公共汽车交通系统》全书合并文本
├─ BRT-full.raw.txt / *.stats.json 同上
├─ facts-UP.txt                    《城市规划原理》数值/事实条目（每条带 pdf 页码 + 印刷页码）
├─ facts-BRT.txt                   《BRT》数值/事实条目（同上）
├─ chapters/                       按章节切片的文本（UP-*.txt / BRT-*.txt）
├─ ocr/UP/p0001.txt …              逐页 OCR 文本（文件名 = PDF 页序号）
├─ ocr/BRT/p0001.txt …
├─ tb10099/                        《铁路线路及站场》提取产物
└─ img/UP/*.jpg, img/BRT/*.jpg     逐页页面图片（核对 OCR 错字时看它）
```

> 本目录**只放书籍提取产物**。
> **不含任何地图的样例输出**（报告 / 指标 JSON / 配图）—— 样例数值容易被误当结论，
> 且任何一座城的数字对另一座城都不适用。报告与配图请**现场生成**：
>
> ```bash
> python -X utf8 ../scripts/city_report.py --carto "<Carto导出目录>" --out city_report.md --maps maps/
> python -X utf8 ../scripts/city_map.py    --carto "<Carto导出目录>" --out city_map.png
> ```
>
> skill 目录内同样**不含** Carto 原始数据（体积大且随时会变）；要分析请让玩家导出自己的 Carto 数据。

## 可读性指标

| 书 | 页数 | 有文本页 | 清洗后字符 | CJK 字符 | 均值 | 页码换算 |
|---|---|---|---|---|---|---|
| 城市规划原理（第3版） | 305 | 304 | 338,911 | 293,625 | 1114.8 字符/页 | **印刷页 = PDF 页 − 8** |
| 城市快速公共汽车交通系统 | 211 | 210 | 104,509 | 74,689 | 497.7 字符/页 | **印刷页 = PDF 页 − 9** |

页码换算由目录页与正文页眉交叉验证得出，非推测。

## 使用注意（OCR 的固有误差）

1. **形近字误识**：`巧`→`5`（如「0.4~0巧」实为「0.4~0.5」）、`休系`→`体系`、`泌`→`交`、`拼`/`哄`→`公` 等。
   **凡涉及数字，务必回看 `img/` 里对应的页面图片**，或在 `facts-*.txt` 里找已核对过的条目。
2. **表格还原错乱**：多列数值表的表头与数据列会错位。引用表格数值前必须核对图像。
3. **页码**：`===== PAGE n =====` 中的 n 是 **PDF 页序号**；引用书籍原文时建议同时标注换算后的印刷页码。
4. 若某页确实读不通，**如实标注"该页 OCR 不可用"**，不要靠上下文猜测补全。
