# csl2-city-advisor · DeepSeek Harness 插件

把《都市天际线 2》（Cities: Skylines II）城市规划顾问 skill 做成 **DSH 插件**，并在「用户给了存档 → 开始分析」
之间插入一步**可视化数据前置**：用滑动面板收集 **RCIO 四条需求条 + 失业率**，换算成标准数据后进入分析。
这一步**可以跳过**，任何情况下都不会阻塞分析。

| | |
|---|---|
| 插件包名 | `csl2-city-advisor` |
| 版本 | `0.1.0` |
| 仓库 | <https://github.com/SimplySrSO4/cs2-city-advisor>（仓库名 `cs2-city-advisor`，与包名不同名，属历史原因） |
| 运行环境 | Node ≥ 22.19（DSH 自带运行时） |
| 依赖 | **零第三方依赖、零构建步骤**（Host 与 Client 都是纯 JS） |
| 组成 | Host 半（工具 + 路由 + skill provider）+ Web Client 半（滑动面板）+ 一份完整 skill |

---

## 1. 概述

插件解决的是一个具体的缺口：CSL2 的 **RCIO 四条需求条（住宅 / 商业 / 工业 / 办公）与失业率**，
在 Carto 导出与存档文件里**都没有**，只能问玩家；而「在对话里来回问答 + 玩家再回来」这件事体验很差，
读数还容易漏、口径容易飘。

于是把它做成两步：

1. **Host 半**注册一个模型可见的工具 `csl2_city_readings`，并在 DSH 的 Web 服务器上挂一个同源端点；
2. **Client 半**在浏览器里渲染一个**模态滑动面板**（四条竖向滑条 + 失业率输入框），玩家拖完点一次提交即可。

插件同时把整个 skill（本体的 `SKILL.md`、`references/`、`scripts/`、Carto 工具链）**随包携带**，
因此它既是「面板提供者」，也是「把顾问 skill 一次装到位」的分发单位。

---

## 2. 插件用途

### 2.1 对玩家：一次拖完的模态面板

当 agent 决定开始分析你的城市时，界面会弹出面板（全屏居中 + 遮罩 + 页面滚动锁定）：

- **四条竖向滑动条**：住宅 / 商业 / 工业 / 办公，取值 `−100 … +100`，拖动时实时显示带符号数值与档位文字；
- **一个失业率输入框**：填游戏内 Unemployment 读数（%）；
- **两个按钮**：`提交并分析` 与 `跳过，直接分析`。

两个刻意的设计：弹窗**走 Portal 挂到 `document.body`**（否则卡片折叠时整棵子树不挂载，面板根本看不见，见 §9）；
遮罩与 `Esc` **不会**关闭它 —— 面板一旦打开，关掉只会让工具白等到超时，请用两个按钮之一结束。

### 2.2 两种走法，都不会卡住分析

| 走法 | 工具返回 | agent 的行为 |
|---|---|---|
| 拖完点「提交并分析」 | `status: "submitted"` + `standard` 标准数据 | 带着这组读数分析 |
| 点「跳过，直接分析」，或在对话里直接说不用补 | `status: "skipped"` | **照常分析**，只在报告第 0 栏声明「未提供 RCIO 需求条与失业率，相关排序只能给区间判断」 |

结算后弹窗消失，工具卡片变成一行**只读回放**（四条需求 + 失业率档位），不再挡住结论。

### 2.3 对模型：一个工具

**工具名 `csl2_city_readings`**，参数（全部可选）：

| 参数 | 类型 | 说明 |
|---|---|---|
| `city` | string | 存档 / 城市名，用于面板标题 |
| `savePath` | string | 存档或 Carto 导出目录，仅用于面板展示 |
| `reason` | string | 为什么现在要读数（写进面板副标题） |
| `timeoutSec` | number | 等待上限，默认 `900`，最小 `30` |

### 2.4 降级：任何一环缺了都不报错、不卡死

| 情况 | 行为 |
|---|---|
| 没有 `webServer`、路由没挂上、用户没装客户端插件 | **立即**返回 `status: "unavailable"`（有 `CSL2_NO_CLIENT_MS` 测试钩子） |
| 玩家一直没操作 | 到 `timeoutSec` 返回 `status: "timeout"` |
| 客户端 `apply()` 抛错 | 不会发生：取不到 React 就用内置极简兜底，避免 bundle 被判「loaded without registering」而整张卡片消失 |

以上三种都**照常进入分析**，插件永远不会让分析失败。

### 2.5 随包携带的 skill

`skills/cities-skylines-2-city-advisor/` 是**完整**的顾问 skill：分层建议（先让城市长大 → 再巩固四项基础
→ 最后才谈税收与幸福度）、带出处的游戏机制、真实世界规范（GB/T 51328、CJJ 37、JTG D21、TB 10099、MH/T 5002 等）、
Carto 数据工具链与报告生成脚本。与原工作区目录的逐字节差异**只有 5 个文件**（见 §3.3）。

---

## 3. 交付内容结构

### 3.1 目录树

```
csl2-city-advisor/
├── package.json                 # 插件清单：dsh.bundle.patch + dsh.client（platform: web）、engines.node ≥ 22.19
├── cordis.patch.yml             # 把插件挂进 profile 的 cordis 配置（insert 一行 id/name）
├── README.md                    # 本文件
├── CONTRACT.md                  # 内部冻结契约：工具参数 / 返回结构 / 档位判据 / UI 与 wire 约定
├── lib/
│   ├── index.js                 # Host 半：csl2_city_readings 工具 + skill provider + /csl2-readings 端点
│   ├── rcio.js                  # 口径层：原始读数 → csl2-rcio-standard/v1（纯函数、零依赖、Host/Client 共用）
│   └── client.js                # Client 半：浏览器 bundle 的可视化滑动面板（纯 JS、零构建）
├── tests/
│   ├── client-rcio-parity.mjs   # 口径等价性 + UI/wire 契约自测
│   └── verification/            # 独立验证者脚本 + REPORT.md（run-all.mjs 一把跑 A–E）
└── skills/cities-skylines-2-city-advisor/
    ├── SKILL.md                 # 顾问主文件（1284 行）：分层目标 + 铁律 + 流程
    ├── references/              # 31 个参考文件（机制 / 道路 / 公交 / 经济 / 规范 / 書摘 / 口径）
    ├── scripts/                 # 32 个脚本：Carto 读取、路网与地形、地图与报告生成、OCR 工具链
    └── extract/                 # 书摘中间产物：OCR 文本 / 章节切分（**不含原始页扫描图**，见 §8）
```

### 3.2 四个部件的分工

| 部件 | 职责 | 约束 |
|---|---|---|
| `lib/index.js` | 注册工具、注册 `/csl2-readings` 路由、提供 skill、管理面板会话（Map + 超时 + 取消） | 无第三方依赖 |
| `lib/rcio.js` | 唯一的**口径来源**：原始读数 → `csl2-rcio-standard/v1` | 纯函数；客户端内联同一份口径 |
| `lib/client.js` | 浏览器半：注册 `tool.call.toolview` 槽（key = `csl2_city_readings`），Portal 渲染模态面板，1.5 s 轮询 | **纯 JS，禁止 `import`**，无构建 |
| `cordis.patch.yml` | 把插件插入 profile 的 cordis 行 | 仅 `insert` 一行 |

### 3.3 skill 与原工作区目录的差异

除下列 5 个文件外，其余文件与原目录**逐字节相同**（原目录本身一个字节都没有被改动）：

| 文件 | 改动 |
|---|---|
| `SKILL.md` | 新增**第 0 步**（数据前置，可跳过）+ **铁律 14** + 第 0 栏模板补充 + frontmatter description 追加一句英文 |
| `references/120-rcio-input-step.md` | **新建**：这一步的完整流程、接口示例、档位表、口径与局限、常见错误 |
| `references/46` / `100` / `70` | 各加一处交叉引用 |

---

## 4. 数据口径

面板读数会被换算成标准数据（工具返回值里的 `standard`，`schema = "csl2-rcio-standard/v1"`）：

| 面板读数 | 标准字段 | 含义 |
|---|---|---|
| 滑条 −100…+100 | `standard.rcio.<zone>.bar` / `.percent` / `.normalized` | 原值 / 百分比 / 归一值 |
| 档位 | `standard.rcio.<zone>.level` / `.levelLabel` | 6 档：`collapse` `negative` `neutral` `weak` `demand` `strong` |
| 失业率 % | `standard.unemployment.percent` / `.fraction` | 游戏内 Unemployment 读数 |
| 失业率档 | `standard.unemployment.band` / `.bandLabel` | 4 档：`low` `normal` `high` `severe` |
| 组合信号 | `standard.flags[]` | `office_strong` / `residential_negative` / `unemployment_severe` / `all_neutral` |

`<zone>` ∈ `residential` / `commercial` / `industrial` / `office`。**档位边界与判据的唯一来源**是
`CONTRACT.md` §4，流程与示例见 `skills/.../references/120-rcio-input-step.md`。

---

## 5. 安装 / 卸载 / 更新

### 5.1 安装

安装会写 `~/.dsh/profiles/<profile>`（依赖 + `dsh.profile.bundles` + 一层 cordis patch）。

**GUI 内首选**：让 agent 执行 `plugin_manager` 的 `install_bundle`，target 用插件目录的**绝对路径**，批准一次即可。

**CLI 备选**（必须**先完全退出** DeepSeek Harness，否则 profile 被占用）：

```powershell
& 'C:\Users\Devcl\AppData\Local\Programs\DeepSeek Harness\resources\runtime\cli\bin\dsh.cmd' `
  plugin --profile desktop add 'C:\Users\Devcl\Desktop\CSL2\plugins\csl2-city-advisor'
```

> 实测：应用正在运行时该命令会以 `EPERM … package.json.lock` 失败 —— 这是「profile 被占用」，
> 不是插件有问题；退出应用后重跑即可。

从 GitHub 装的话，先 clone 再按上面用**本地路径**安装：

```powershell
git clone https://github.com/SimplySrSO4/cs2-city-advisor.git
& 'C:\...\dsh.cmd' plugin --profile desktop add '<clone 出来的目录>\cs2-city-advisor'
```

### 5.2 装完怎么确认可用

1. **刷新页面**（F5 / Ctrl+R）或重启 DSH —— 客户端半是在**页面启动期**通过 `window.__DSH_BOOT__` 装载的，
   安装前打开的页面看不到面板（此时工具会等 30 s 返回 `timeout` 并照常继续，这是设计内的降级，不是坏了）；最稳的是重启应用。
2. 新开一轮，让它「分析我给的存档」→ 应出现 `csl2_city_readings` 工具调用，且界面**弹出模态面板**。
3. 面板里应有四条竖向滑条 + 失业率输入 + 两个按钮 —— 这是**唯一能证明端到端打通**的一步。
4. 拉一条滑条，确认档位文字随数值变化。
5. 点「跳过，直接分析」，确认弹窗消失、agent 继续分析而不是重复追问。

### 5.3 卸载与更新

- 卸载：`plugin_manager` 的 `remove_bundle`（target `csl2-city-advisor`），或 CLI
  `dsh plugin --profile desktop remove csl2-city-advisor` —— 会同时摘掉依赖与那层 patch。
- 更新：本机以 `link:` 方式安装，**改 `lib/**` 不需要重装**即生效；只有浏览器半需要刷新页面重新装载。

---

## 6. 验证状态

`tests/verification/run-all.mjs` 一把跑完 A–E：**PASS=124 / FAIL=0 / UNVERIFIED=1，退出码 0**（约 35 s）。
逐项证据、命令与输出见 `tests/verification/REPORT.md`。要点：

- **口径正确**：`CONTRACT.md` §4 的两张表在运行时**从文本抽出**再对照（不是硬编码）；500 组确定性随机 + 201 点整数网格，共 **3405 个比对点 0 不一致**。
- **真 HTTP 往返 34 项**：`open`（裸）/`poll`/`submit`/`skip`、重复提交拒绝、405/404/400、**并发两面板各带 `callId` 不串数据**、`CSL2_NO_CLIENT_MS=120 → 132 ms` 返回 `unavailable`、取消后两张 Map 均清理、总超时实测 30005 ms。
- **历史 bug 已修且有牙**：`lib/client.js` 曾把档位算成 `classifyLevel(value / 100)`（双重归一，档位文字永远显示「无需求」）；现静态无 `/100`、动态 4×9=36 个渲染断言逐字一致，且**变异副本**（把 bug 改回去）会让断言 FAIL。
- **原目录零改动**：工作区 `skill/cities-skylines-2-city-advisor` 的 1121 个文件 sha256/bytes/mtime 与开工前基线**全未变**。

---

## 7. 已知未验证项

如实列出，不做过度承诺：

- **面板的「视觉」未在无头环境截图确认** —— 竖向滑条的朝向（`writing-mode`）与 `accent-color` 着色属于观感项；
  若发现朝向不对，改 `lib/client.js` 里 `csl2-track` 的 CSS 即可。
- **`900 s` 默认等待上限只实测了同类定时器的 `30 s` 分支**。
- **自定义路由没有服务级鉴权**（`dsh-host-webserver` 明文如此）：该端点只吞吐「面板读数」这一种数据，
  不回显文件系统内容，也不做通用数据出口。

---

## 8. 仓库内容与逐字节约定

仓库根就是插件包根（`package.json` 在最外层），当前共 **629 个文件 / 约 9.3 MB**：

| 内容 | 是否入库 |
|---|---|
| `lib/`、`tests/`、`package.json`、`cordis.patch.yml`、`CONTRACT.md`、`README.md` | ✅ |
| `skills/.../SKILL.md`、`references/`（31）、`scripts/`（32） | ✅ |
| `skills/.../extract/` 的文本与示例产物：`ocr/` 识别文本、`chapters/` 章节切分、`*-full.*.txt/json`、3 张示例地图 PNG（共 545 个 = 542 文本/JSON + 3 PNG） | ✅ |
| `skills/.../extract/img/`（514 张整页 JPEG，约 99 MB） | ❌ 已 `.gitignore`：这些是出版书籍的整页扫描件，公开有版权风险，且只是 OCR 前的中间产物；需要重跑 OCR 时请自备原书页 |
| `__pycache__/`、`*.py[cod]` | ❌ 已 `.gitignore` |

**换行约定**：`.gitattributes` 里是 `* -text`，即**禁止任何换行转换**。
原因是 `tests/verification/` 用 **sha256 + bytes 冻结文件指纹**，而 Git for Windows 默认 `core.autocrlf=true`
会在检出时把 LF 换成 CRLF、直接弄坏指纹。仓库里存的是什么字节，检出后就是什么字节。

---

## 9. 实现要点（便于后续维护）

- **Host ↔ Client 通道**：`ctx.webServer.register({ kind:'prefix', path:'/csl2-readings', handler })`
  + 客户端同源 `fetch(window.location.origin + '/csl2-readings')`。这是本机真实运行的第三方插件
  `dsh-univer-office` 的同构做法，**不是** `host.call`（后者只存在于动态 Cordis 包）。
  四个动作：`readings.open` / `poll` / `submit` / `skip`；`open` 可选带 `callId` 以消除并发串面板。
- **卡片渲染**：客户端注册 keyed 槽 `tool.call.toolview`（`key: 'csl2_city_readings'`），不声明 `locale`，
  文案全部 `React.createElement` 自绘；组件是 props 的纯函数（流式与回放都会调起）。`phase` 三种：
  `preparing`（无 `argsRaw`）/ `start` / `result`。
- **弹窗为什么必须走 Portal（实测结论）**：面板最初渲染在**工具调用卡片内部**，而「未展开的工具行」不渲染 body ——
  宿主 `GET /csl2-readings?action=diag` 实测显示 `{"open":1,"poll":39,"pendingPanels":1}`：客户端半确实已加载、
  已 `open`、已每 1.5 s 稳定轮询，但卡片折叠时整棵子树（连同 `position:fixed` 的模态）**根本没被挂载**。
  现在用 `react-dom` 的 `createPortal` 把模态挂到 `document.body`；取不到 `react-dom` 时**退回内联模态**，不白屏。
  `?action=diag` 作为「浏览器有没有来敲门」的常驻证据保留。
- **零依赖**：Host 与 Client 都不 import 任何第三方包；`lib/rcio.js` 是口径的规范来源，客户端内联同一份，
  并用 `tests/client-rcio-parity.mjs` 锁住等价性。

---

## 10. 许可

本仓库暂未附许可证文件。`skills/` 下的书籍摘录仅作个人学习与研究用途；
如需公开发布或再分发，请先自行确认相关材料的授权情况。
