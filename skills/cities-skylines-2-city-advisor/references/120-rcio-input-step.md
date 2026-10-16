# 120 · 第 0 步：先取 RCIO 需求条与失业率（可视化滑动输入；可跳过）

> **配套**：`SKILL.md` §1 **第 0 步**（流程）、§0 **「数据前置」条**（纪律）。
> **上游依据**：`46-algorithm-roadmap.md` §5.2「❌ 算不了的 —— 必须让玩家在游戏内读数」。
> **接口契约**：`../../CONTRACT.md` §1（工具返回值）与 §4（数据转换口径）——字段名与档位名**以契约为准**。
> 本文件**不含任何具体地图的数值**。

## 1. 完整流程：触发 → 面板 → 提交/跳过 → 标准数据 → 写进报告哪一节

| # | 环节 | 具体做什么 |
|---|---|---|
| 1 | **触发** | 用户给了**存档 / Carto 导出目录 / 截图**，或说"看看我的城" → **在跑任何诊断之前**先做这一步 |
| 2 | **弹面板** | 调用 DSH 工具 **`csl2_city_readings`**（参数：`city`、`savePath`、`reason`、`timeoutSec`） |
| 3 | **用户操作** | 拖四条**竖向需求条**（住宅 `residential` / 商业 `commercial` / 工业 `industrial` / 办公 `office`，区间 −100…+100）＋ 可选填**失业率 %**；再点**「提交并分析」**或**「跳过，直接分析」** |
| 4 | **拿标准数据** | 工具返回 `standard`（`schema: "csl2-rcio-standard/v1"`）——**正文直接引用它，不要自己再换算** |
| 5 | **写进报告** | ① **取到数**：写进「诊断（数据说话）」段的**第 1 条**（带档位 + `[经验]`），失业率**不再进第 0 栏**；② **被跳过**：失业率进最终答复的**第 0 栏**，并写明降级损失 |
| 6 | **只问一次** | 同一份存档只弹一次；用户跳过 → 不再追问、不再弹第二轮。用户**后来主动补数** → 重跑第 0 步并用新数更新结论 |

**面板形态**（供核对）：四条**竖向**滑动条，区间 `−100 … +100`、步长 1，刻度 −100 / −50 / 0 / +50 / +100；
颜色 负 `#C0392B` / 零 `#8A93A0` / 正 `#1B4B8C`；拖动时实时显示带符号数值与档位文字。

## 2. 返回结构（**接口示例，不代表任何地图**）

```json
{
  "status": "provided" | "skipped" | "unavailable" | "timeout",
  "source": "slider-panel" | "agent-skip" | "no-client" | "timeout",
  "raw": {
    "rcio": { "residential": -35, "commercial": 12, "industrial": 0, "office": 85 },
    "unemploymentRate": 6.5,
    "confidence": { "residential": "exact", "unemploymentRate": "approx" },
    "notes": "可选自由文本"
  },
  "standard": {
    "schema": "csl2-rcio-standard/v1",
    "rcio": {
      "residential": { "bar": -35, "percent": -35, "normalized": -0.35, "level": "negative", "levelLabel": "负需求" },
      "commercial": { "bar": 12, "percent": 12, "normalized": 0.12, "level": "neutral", "levelLabel": "无需求" },
      "industrial": { "bar": 0, "percent": 0, "normalized": 0, "level": "neutral", "levelLabel": "无需求" },
      "office": { "bar": 85, "percent": 85, "normalized": 0.85, "level": "strong", "levelLabel": "强需求" }
    },
    "unemployment": { "percent": 6.5, "fraction": 0.065, "band": "normal", "bandLabel": "正常范围" },
    "summary": "住宅 −35｜商业 +12｜工业 0｜办公 +85｜失业率 6.5%",
    "flags": ["office_strong", "residential_negative"]
  },
  "message": "给模型看的中文单行结论（跳过时说明"用户选择不补数据"）",
  "panelId": "r-1a2b3c"
}
```

> 说明：示例里 `status` / `source` 的 `|` 表示**取值域**，`message` 一行是**形状说明** ——
> 实际返回的是**一个确定值**，不是这些字面量。上例已按 §4 档位表重算（契约 §1 同）。

**状态机** —— 三种"没拿到数"的 `status`（`skipped` / `unavailable` / `timeout`）处理方式**完全相同**：
`raw` 与 `standard` 均为 `null`，**照常分析、照常出全部建议**，只在第 0 栏声明缺项。

| `status` | `source` | 含义 | 必须做什么 |
|---|---|---|---|
| `provided` | `slider-panel` | 用户提交了读数 | 引用 `standard`，写进「诊断」段第 1 条 |
| `skipped` | `agent-skip` | 用户点了「跳过」或在对话里说不补 | `raw`/`standard` 为 `null` → 照常出建议，第 0 栏声明 |
| `unavailable` | `no-client` | 没有客户端，面板弹不出来 | 同上；**不要干等**（无客户端时立刻返回） |
| `timeout` | `timeout` | 超过 `timeoutSec`（默认 900 s，最小 30）仍在等待 | 同上 |

## 3. 档位表与失业率分档表（与契约 §4 **逐字一致**）

需求条（输入 = 用户拖动的 `bar ∈ [-100, 100]` 整数 → CSL2 需求条百分比；**只做线性归一与分档**）：

| 归一值 `normalized = bar / 100` | `level` | `levelLabel` |
|---|---|---|
| `≤ -0.6` | `collapse` | 需求崩塌（负） |
| `-0.6 < n < -0.15` | `negative` | 负需求 |
| `-0.15 ≤ n ≤ 0.15` | `neutral` | 无需求 |
| `0.15 < n < 0.5` | `weak` | 弱正需求 |
| `0.5 ≤ n < 0.8` | `demand` | 需求 |
| `≥ 0.8` | `strong` | 强需求 |

失业率分档（**这是"诊断阈值"，不是游戏机制** —— 官方**没有给过**任何阈值）：

| `percent` | `band` | `bandLabel` |
|---|---|---|
| `< 3` | `low` | 偏低（劳动力紧张） |
| `3 – 8` | `normal` | 正常范围 |
| `> 8 – 12` | `high` | 偏高 |
| `> 12` | `severe` | 严重（税基会自己缩） |

`flags`（组合信号，**原样引用，不要另起名字**）：

* `office_strong` —— 办公 `normalized ≥ 0.8`（1.5.7f1 起办公需求受学历结构影响 → **结构性信号**）；
* `residential_negative` —— 住宅落入 `negative` / `collapse`（`normalized < -0.15`）；
* `unemployment_severe` —— 失业率 `band = severe`（`percent > 12`）；
* `all_neutral` —— 四条需求条**全在 ±0.15 内**（均为 `neutral`）→ **结构僵化提示**。

> 逐条换算关系（同一个数只换单位，**不引入游戏里没有的机制**）：
> `normalized = bar / 100`、`percent = bar`、`unemployment.fraction = unemployment.percent / 100`。

## 4. 口径与局限（引用时必须照实说）

* **需求条是"玩家在游戏内看到的读数"**（主界面需求条）——**不是 Carto 字段**（图层里没有对应字段），
  **也不是**现实规划指标；正文引用时按面板读数 / `[经验]` 口径标注。
* **噪声来自"截图估计"**：用户若凭截图或记忆估读，`raw.confidence.<zone>` 会标 `approx`（或 `unknown`）；
  正文引用**要写"约"**，不要当精确值用（例：「住宅需求条约 −35（`negative`）」）。
* **失业率分 4 档是诊断阈值**（社区 / 项目经验），**官方没有给过阈值** ——
  与 §2 速查卡里 `[经验]` 的写法一致：**可以当判据用，但不要说成"游戏规则"**。
* **它是第 1 层 ② 的唯一直接读数**：Carto 只能给「岗位 ÷ 劳动力」的**供需代理**，
  测不出结构性失业（学历与岗位不匹配）；所以 §0.5 第 ② 项与"该往哪扩 / 该补哪类用地"的排序
  都以它为输入。
* **它只影响建议精度，不影响是否分析**：跳过**不减少**建议条数，只降低"确定度"。

## 5. 常见错误（三条）

1. **因为有工具就默认用户必须填** —— 面板上「跳过，直接分析」是**正当选项**；
   用户跳过之后**不许重复追问、不许第二轮再弹**，更不许说"数据不全、无法分析"。
2. **跳过之后仍在正文里假装有失业率**（或拿"岗位 ÷ 劳动力"的供需代理冒充游戏内 Unemployment）——
   这直接违反**「数据前置」条**；跳过就必须在第 0 栏声明，并列出哪几条建议降级为"区间"。
3. **拿需求条当"人口增速"用**（或反过来说"需求高 = 人口在涨"）——
   需求条是**当期用地供需信号**，与人口增速是两回事；它只与 T4（已划未建）交叉验证：
   **划了区但需求仍高 = 有阻塞**。
