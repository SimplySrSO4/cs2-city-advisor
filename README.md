# csl2-city-advisor · DSH 插件

把工作区的 skill [`cities-skylines-2-city-advisor`](../../skill/cities-skylines-2-city-advisor)（《都市天际线 2》城市规划顾问）
做成 **DeepSeek Harness 插件**，并按需求加了一步**数据前置**：用户传入存档后、开始分析之前，
先用**可视化滑动条面板**收集 **RCIO 四条需求条 + 失业率**，然后把这组读数**转换成标准数据**再进入分析；
面板上同时提供**「跳过，直接分析」**——用户不想补数据时**直接分析**，不会被阻塞。

> ⚠️ **本插件尚未安装进任何 profile**（按你的选择"先别装，只交付插件目录"）。
> 装之前，工具 `csl2_city_readings` 与滑动面板**不会出现**；skill 也仍只有工作区原目录那一份。
> 安装步骤见下面 §3。

## 1. 交付内容

```
plugins/csl2-city-advisor/
├── package.json                 # dsh.bundle.patch + dsh.client（platform: web）
├── cordis.patch.yml             # insert: id csl2-city-advisor -> name 'csl2-city-advisor'
├── CONTRACT.md                  # 内部冻结契约（工具返回结构、档位口径、UI/wire 约定）
├── README.md                    # 本文件
├── lib/
│   ├── index.js                 # Host half：csl2_city_readings 工具 + skill provider + /csl2-readings 端点
│   ├── rcio.js                  # 纯函数口径层：原始读数 -> csl2-rcio-standard/v1（零依赖）
│   └── client.js                # Client half：可视化滑动面板（浏览器 bundle，纯 JS、零构建）
├── tests/
│   ├── client-rcio-parity.mjs   # 口径等价性 + UI/wire 契约自测（作者写的）
│   └── verification/            # 独立验证者的脚本与 REPORT.md
└── skills/cities-skylines-2-city-advisor/   # 完整 skill（含 references/ 与 scripts/）
```

改写后的 skill 与原目录的**唯一差异**（其余 1116 个文件逐字节相同）：

| 文件 | 改动 |
|---|---|
| `SKILL.md` | 新增 **第 0 步**（数据前置，可跳过）+ **铁律 14** + 第 0 栏模板补充 + frontmatter description 追加一句英文 |
| `references/120-rcio-input-step.md` | **新建**：这一步的完整流程、接口示例、档位表、口径与局限、常见错误 |
| `references/46` / `100` / `70` | 各加一处交叉引用 |

**工作区原目录 `skill/cities-skylines-2-city-advisor` 一个字节都没有改动。**

## 2. 新流程（用户视角）

1. 你提供存档 / Carto 导出 / 说"看看我的城"；
2. agent **先**调用 `csl2_city_readings`，界面**弹出模态面板**（全屏居中 + 遮罩 + 页面滚动锁定）：
   **四条竖向滑动条**（住宅 / 商业 / 工业 / 办公，−100…+100，拖动时实时显示带符号数值与档位文字）
   加一个**失业率 %** 输入框；
   > 弹窗是刻意的：不必回到对话流里找那张卡片。遮罩与 `Esc` **不会**关闭它
   > ——面板一旦打开，关掉只会让工具白等到超时；请用两个按钮之一结束。
3. 两种走法：
   - 拖完点**「提交并分析」** → 工具返回标准数据，agent 带着它分析；
   - 点**「跳过，直接分析」**（或在对话里直接说不用补）→ 工具返回 `skipped`，agent **照常分析**，
     只是在报告第 0 栏声明"未提供 RCIO 需求条与失业率，相关排序只能给区间判断"。
   结算后**弹窗消失**，卡片变成一行只读回放（显示四条需求 + 失业率档位），不再挡住结论。
4. 标准数据结构（工具返回值里的 `standard`，`schema = "csl2-rcio-standard/v1"`）：

   | 面板读数 | 标准字段 | 含义 |
   |---|---|---|
   | 滑条 −100…+100 | `standard.rcio.<zone>.bar` / `.percent` / `.normalized` | 原值 / 百分比 / 归一值 |
   | 档位 | `standard.rcio.<zone>.level` / `.levelLabel` | 6 档：`collapse` `negative` `neutral` `weak` `demand` `strong` |
   | 失业率 % | `standard.unemployment.percent` / `.fraction` | 游戏内 Unemployment 读数 |
   | 失业率档 | `standard.unemployment.band` / `.bandLabel` | 4 档：`low` `normal` `high` `severe` |
   | 组合信号 | `standard.flags[]` | `office_strong` / `residential_negative` / `unemployment_severe` / `all_neutral` |

   档位**边界与判据**见 `CONTRACT.md` §4（唯一判据）与 `skills/.../references/120-rcio-input-step.md`。

## 3. 安装（你决定何时做）

安装会写 `~/.dsh/profiles/desktop`（依赖 + `dsh.profile.bundles`），是**一次需要更高权限的操作**。

**首选（GUI 内的官方入口）**：在对话里让我执行 `plugin_manager` 的 `install_bundle`，
target 用绝对路径 `C:\Users\Devcl\Desktop\CSL2\plugins\csl2-city-advisor`，你批准一次权限即可。

**备选（CLI，需要先完全退出 DeepSeek Harness，否则 profile 被占用）**：

```powershell
& 'C:\Users\Devcl\AppData\Local\Programs\DeepSeek Harness\resources\runtime\cli\bin\dsh.cmd' `
  plugin --profile desktop add 'C:\Users\Devcl\Desktop\CSL2\plugins\csl2-city-advisor'
```

（实测：应用正在运行时该命令会以 `EPERM … package.json.lock` 失败——这是"profile 被占用"，
不是插件有问题；退出应用后重跑即可。装完**必须重启 DeepSeek Harness**：
客户端 bundle 的扫描发生在启动期。）

**装完怎么确认可用**：
1. **先刷新页面**（F5 / Ctrl+R）或重启 DeepSeek Harness —— 客户端半是在**页面启动期**通过
   `window.__DSH_BOOT__` 装载的；在安装前打开的页面不会看到面板（实测：不刷新时工具会等 30 s 后
   返回 `timeout` 并照常继续，这是设计内的优雅降级，不是插件坏了）。最稳的是重启应用。
2. 新开一轮，让它"分析我给的存档"，应看到 `csl2_city_readings` 工具调用，并且界面**弹出模态面板**；
3. 面板里应有四条竖向滑条 + 失业率输入 + 两个按钮 —— 这是**唯一能证明端到端打通**的一步；
4. 拉一条滑条看档位文字是否随数值变化（曾有一个"双重归一"bug 会让它永远显示「无需求」，已修并有回归锁）；
5. 点「跳过，直接分析」，确认弹窗消失、agent 继续分析而不是重复追问。

## 3. 安装状态：**已装**（本机 `desktop` profile）

已通过 DSH 官方入口 `plugin_manager` 的 `install_bundle`（target = 本目录绝对路径）安装完成，实测：

| 检查 | 实测结果 |
|---|---|
| 安装结果 | `application: "applied"`（pnpm 退出码 0） |
| profile 依赖 | `"csl2-city-advisor": "link:C:/Users/Devcl/Desktop/CSL2/plugins/csl2-city-advisor"` |
| node_modules | junction 指向本目录 |
| bundles 列表 | `dsh.profile.bundles` 末位已追加 `csl2-city-advisor` |
| patch 生效 | profile `cordis.yml` 出现 `- id: csl2-city-advisor` / `name: csl2-city-advisor` |
| Host 半 | **已激活** —— 会话中已出现 `csl2_city_readings` 工具，并被实际调用过一次 |
| 浏览器半 | 需**刷新页面 / 重启应用**后才装载（见下） |

更新代码后**不需要重装**：`link:` 是软链，改 `lib/**` 即生效；只有浏览器半需要刷新页面重新装载。

### 卸载

`plugin_manager` 的 `remove_bundle`（target `csl2-city-advisor`），或 CLI
`dsh plugin --profile desktop remove csl2-city-advisor` —— 会同时摘掉依赖与那一层 patch。

## 4. 实现要点（便于后续维护）

- **Host ↔ Client 通道**：`ctx.webServer.register({ kind:'prefix', path:'/csl2-readings', handler })`
  + 客户端同源 `fetch(window.location.origin + '/csl2-readings')`。
  这是本机真实运行的第三方插件 `dsh-univer-office` 的同构做法（客户端 `lib/client.js:21949`、
  Host `lib/index.js:13171`），**不是** `host.call` —— 后者只存在于动态 Cordis 包。
  四个动作：`readings.open` / `poll` / `submit` / `skip`；`open` 可选带 `callId` 以消除并发串面板。
- **卡片渲染**：客户端注册 keyed 槽 `tool.call.toolview`（`key: 'csl2_city_readings'`），
  不声明 `locale`，文案全部 `React.createElement` 自绘；组件是 props 的纯函数（流式与回放都会调起）。
  `phase` 三种：`preparing`（无 `argsRaw`）/ `start` / `result`。
- **弹窗为什么必须走 Portal（实测得出的结论）**：交互面板最初渲染在**工具调用卡片内部**，
  而"未展开的工具行"不渲染 body —— 宿主 `GET /csl2-readings?action=diag` 实测显示
  `{"open":1,"poll":39,"pendingPanels":1}`：客户端半确实已加载、已 `open`、已每 1.5 s 稳定轮询，
  但用户看不到弹窗，因为卡片折叠时整棵子树（连同 `position:fixed` 的模态）**根本没被挂载**。
  ⇒ 现在用 `react-dom` 的 `createPortal` 把模态挂到 `document.body`
  （`react-dom` 与 `react` 同属平台共享模块图的内置包，多个官方客户端包都直接 require 它）；
  取不到 `react-dom` 时**退回内联模态**，不白屏。`?action=diag` 作为"浏览器有没有来敲门"的常驻证据保留。
- **降级**：没有 `webServer`、路由没挂上、用户没装客户端插件时，工具**立即**返回
  `status:'unavailable'`（有 `CSL2_NO_CLIENT_MS` 测试钩子），agent 照常分析，不卡死、不抛错。
  客户端 `apply()` 也**永不抛错**（React 取不到就用内置极简兜底），避免运行时把 bundle 判为
  "loaded without registering" 而整张卡片消失。
- **零依赖**：Host 与 Client 都是纯 JS、无构建步骤、不 import 任何第三方包；
  `lib/rcio.js` 是口径的规范来源，客户端内联同一份并用 `tests/client-rcio-parity.mjs` 锁住等价性。

## 5. 验证状态（独立复算）

`tests/verification/run-all.mjs` 一把跑完 A–E：**PASS=124 / FAIL=0 / UNVERIFIED=1，退出码 0**（约 35 s）。
逐项证据、命令与输出见 `tests/verification/REPORT.md`。要点：

- **rcio 口径**：`CONTRACT.md` §4 的两张表在**运行时从文本抽出**再对照（不是硬编码）；500 组确定性随机 + 201 点整数网格共 **3405 个比对点 0 不一致**。
- **真 HTTP 往返 34 项**：`open`(裸)/`poll`/`submit`/`skip`、重复提交拒绝、405/404/400、**并发两面板各带 `callId` 不串数据**、`CSL2_NO_CLIENT_MS=120 → 132 ms` 返回 `unavailable`、取消后两张 Map 均清理、总超时实测 30005 ms。
- **历史 bug 已修并有牙**：`lib/client.js` 曾有 `classifyLevel(value / 100)` 双重归一（面板档位文字永远「无需求」）；现静态无 `/100`、动态 4×9=36 个渲染断言逐字一致，且**变异副本**（把 bug 改回去）会让断言 FAIL。
- **原目录零改动**：`skill/cities-skylines-2-city-advisor` 的 1121 个文件 sha256/bytes/mtime 与开工前基线**全未变**（`SKILL.md` 仍为 `275F7A58…9409B`）；插件副本除允许的 5 个文件外，其余 **1117 个文件逐字节相同**。

## 6. 已知未验证项（如实列出）

- **端到端"看到弹窗"这一步未完成** —— 插件已按你批准的路线 A 装进本机 `desktop` profile
  （`link:` 依赖 + `dsh.profile.bundles` + `cordis.yml` 里的 row 都已核实），Host 半已激活
  （工具 schema 已进入会话）；但**安装前的那个页面**没有新的客户端图，所以还看不到弹窗。
  刷新页面或重启应用后即可验证。
- 竖向滑条的**视觉**（`writing-mode` 朝向、`accent-color` 着色）在无头环境里无法截图确认；
  若刷新后发现朝向不对，改 `lib/client.js` 里 `csl2-track` 的 CSS 即可。
- `900 s` 默认等待上限只实测了同类定时器的 `30 s` 分支。
- 自定义路由**没有**服务级鉴权（`dsh-host-webserver` 明文如此）：本端点只吞吐"面板读数"这一种数据，
  不回显文件系统内容，也不做通用数据出口。
