# CSL2 顾问插件 · 内部契约 v1（冻结）

> 本文件由 Lead 维护。**任何一方改动本契约前必须先通知 Lead**（send_message）。
> 目标：把工作区 skill `cities-skylines-2-city-advisor` 做成 DSH 插件，并在"用户传入存档之后、
> 开始分析之前"插入一步**可视化滑动输入**：RCIO 需求条 + 失业率；同时提供"跳过（不补数据，直接分析）"。

## 0. 交付物

```
C:\Users\Devcl\Desktop\CSL2\plugins\csl2-city-advisor\
├── package.json                          # dsh.bundle.patch + dsh.client（platform: web）
├── cordis.patch.yml                      # insert: id csl2-city-advisor -> name 'csl2-city-advisor'
├── lib/
│   ├── index.js                          # Host half：tools + skills provider + client RPC 服务端
│   ├── client.js                         # Client half：可视化滑动面板（必须为纯 JS，禁止 import）
│   └── rcio.js                           # 纯函数：RCIO 原始读数 -> 标准数据（Host/Client 共用口径）
└── skills/cities-skylines-2-city-advisor/ # 完整 skill（references/ scripts/ SKILL.md ...）
```

安装目标 profile：`C:\Users\Devcl\.dsh\profiles\desktop`（就是当前 GUI，端口 19387）。

## 1. 工具契约（模型可见）

**工具名：`csl2_city_readings`**

用途：在分析存档**之前**，弹出可视化面板收集 RCIO 需求条与失业率；用户也可以选择跳过。

参数（ParameterSchemaSpec，DSL 形式）：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `city` | string | 否 | 存档/城市名，用于面板标题 |
| `savePath` | string | 否 | 存档或 Carto 导出目录，仅用于面板展示 |
| `reason` | string | 否 | 为什么现在要读数（写进面板副标题） |
| `timeoutSec` | number | 否 | 等待上限，默认 900，最小 30 |

标准返回值（canonical value，`output.schema` 的根）：

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

**规则**
- `status: "skipped"` 时 `raw = null`，`standard = null`；`message` 必须明确写"用户选择不补数据，直接分析"。
- `status: "timeout" | "unavailable"` 时同样是 `raw = null`，模型必须**照常继续分析**，并在报告第 0 栏列出缺项。
- 工具**永不抛错**给模型（除非参数致命）；无客户端时立刻返回 `unavailable`，不要干等。
- `output.render` 只产出简短中文；`output.presentationMeta` 返回 `{ status, standard }` 供卡片回放。
- ⚠️ **档位判定只以 §4 的表为准**（§1 的示例已按 §4 + §4 的 flags 规则**逐条重算**：
  `-0.35 → negative`、`0.12 → neutral`、`0 → neutral`、`0.85 → strong`；
  `office 0.85 ≥ 0.8 → office_strong`、`residential -0.35 < -0.15 → residential_negative`，
  故 `flags = ["office_strong", "residential_negative"]`；失业率 6.5 不触发 `unemployment_severe`，
  四条未全在 ±0.15 内故不触发 `all_neutral`）。
  示例里的 `level/levelLabel/flags` 若与 §4 冲突，**一律以 §4 为准**。

## 2. 客户端 RPC 契约（Host ↔ Client 同包通道）

Host half 通过 `ctx.clientModules`/包私有 host 通道暴露方法；实现细节由 Lead 按运行时实际契约敲定。
方法名与语义冻结如下（若运行时只能换一种承载方式，**方法语义不变**）：

| 方法 | 方向 | 入参 | 返回 |
|---|---|---|---|
| `readings.open` | Client → Host | `{ panelId }` | `{ ok, panel }`，`panel` 见 §3 |
| `readings.submit` | Client → Host | `{ panelId, raw }` | `{ ok, status: "provided" }` |
| `readings.skip` | Client → Host | `{ panelId }` | `{ ok, status: "skipped" }` |
| `readings.poll` | Client → Host | `{ panelId }` | `{ status: "pending" \| "settled", result? }` |

- `panelId` 由 Host 在工具 `execute()` 中生成，单次调用唯一。
- Host 侧把每次调用存在内存 Map 里；`execute()` 等待 `submit`/`skip` 或超时。
- Client 面板挂载后先 `readings.open`，再每 1.5 s `readings.poll` 一次，拿到 `settled` 就停止轮询。

## 3. 面板 UI（Client half）

- 四条**竖向**滑动条，顺序固定：住宅 `residential` / 商业 `commercial` / 工业 `industrial` / 办公 `office`。
- 每条取值区间 **−100 … +100**，步长 1，刻度显示 −100 / −50 / 0 / +50 / +100。
- 颜色：负值 `#C0392B`、0 `#8A93A0`、正值 `#1B4B8C`（与 skill 交付色系一致）。
- 拖动时实时显示 `+48`、需求档位文字（负需求/无需求/弱正需求/需求/强需求）。
- 下方：失业率数字输入（`%`，0–100，步长 0.1）+ 可选滑条；默认空。
- 两个按钮：**「提交并分析」**（主色 `#1B4B8C`）与 **「跳过，直接分析」**（次要）。
- 面板标题：`<城市名> · 请先补 RCIO 需求条与失业率`；副标题写"这一步只影响建议精度，不影响是否分析"。
- 必须有无障碍属性（`role`、`aria-label`、键盘可调）。
- **纯函数式**：面板不得读文件、不得访问网络；数据只经 §2 的 RPC 通道。

## 4. 数据转换口径（`lib/rcio.js`，Host/Client 共用）

输入 = 用户拖动的 `bar ∈ [-100, 100]` 整数（→ CSL2 需求条百分比）。
换算**只做线性归一与分档，不得引入游戏内没有的机制**：

| 归一值 `normalized = bar / 100` | `level` | `levelLabel` |
|---|---|---|
| `≤ -0.6` | `collapse` | 需求崩塌（负） |
| `-0.6 < n < -0.15` | `negative` | 负需求 |
| `-0.15 ≤ n ≤ 0.15` | `neutral` | 无需求 |
| `0.15 < n < 0.5` | `weak` | 弱正需求 |
| `0.5 ≤ n < 0.8` | `demand` | 需求 |
| `≥ 0.8` | `strong` | 强需求 |

失业率分档（**这是"诊断阈值"不是游戏机制**，须在文档里写明）：

| `percent` | `band` | `bandLabel` |
|---|---|---|
| `< 3` | `low` | 偏低（劳动力紧张） |
| `3 – 8` | `normal` | 正常范围 |
| `> 8 – 12` | `high` | 偏高 |
| `> 12` | `severe` | 严重（税基会自己缩） |

`flags`：`office_strong`（办公 ≥0.8 → 1.5.7f1 起办公需求受学历结构影响，属"结构性信号"）、
`residential_negative`、`unemployment_severe`、`all_neutral`（四条全在 ±15 → 结构僵化提示）。

## 5. 写入范围（互不重叠）

| 任务 | 负责人 | 允许写 |
|---|---|---|
| host-tool | teammate A | `plugins/csl2-city-advisor/lib/index.js`、`lib/rcio.js`、`package.json`、`cordis.patch.yml` |
| client-slider | teammate B | `plugins/csl2-city-advisor/lib/client.js` |
| skill-edit | teammate C | `plugins/csl2-city-advisor/skills/**` |
| verify-install | teammate D | `plugins/csl2-city-advisor/tests/**`、`_probe/**`（只读其余） |

`lib/rcio.js` 由 A 写、B 只读引用（B 在自己的 client.js 内联同一份口径，禁止跨文件 import，
因为客户端 bundle 是独立打包产物）。

## 6. 验收

1. `node -e "import('.../lib/index.js')"` 能加载且 `name`/`inject`/`apply` 齐备（Host）。
2. `lib/client.js` 语法可解析（`new Function` / `node --check`），且以 `window.__ModuleLoader__.load({ id, factory })` 开头。
3. 安装进 `desktop` profile 后 `--dump-config` 能看到该 layer / 或 profile 的 `cordis.yml` 含该行。
4. GUI 里调用该工具能出现滑动面板（Lead 做端到端验证）。
5. skill 文档里"第 0 步：先取 RCIO/失业率（可跳过）"在"第 1 步：问清问题与拿到数据"之前出现。
