# csl2-city-advisor · 独立验证报告（task-5 / verification-dev）

> 验证人：teammate `verification-dev`（独立于三个作者）。
> 只读被验证文件；**只写** `plugins/csl2-city-advisor/tests/verification/**` 与 `_probe/verify/**`。
> 期望值来源：`_probe/DSH-CONTRACTS.md`（Q1–Q9，781 行）+ `_probe/DSH-CONTRACTS.lead-prior.md`（Q1–Q9）
> + `plugins/csl2-city-advisor/CONTRACT.md`（§1/§2/§4）。**没有**凭直觉改过任何期望值。

## 0. 结论（一句话）

**PASS=124，FAIL=0，UNVERIFIED=1**。A（静态完整性）、B（rcio 口径 + Host/Client 等价 + BUG1 回归）、
C（真 HTTP 往返 + 超时/取消/并发）、D（skill 文本）、E（原目录零改动 + 冻结指纹）全部通过；
唯一未验证项是「默认 `timeoutSec=900` 的总超时未实等 900 秒」，其余 34 项 C 断言全部实跑通过。

| 项 | 脚本 | PASS | FAIL | UNVERIFIED |
|---|---|---|---|---|
| A1–A3 静态完整性 | `static-integrity.mjs` | 13 | 0 | 0 |
| A4 `cordis.patch.yml` | `cordis-patch-assert.mjs` | 1 | 0 | 0 |
| B5 `lib/rcio.js` 口径 | `rcio-cases.mjs` | 43 | 0 | 0 |
| B6 Client/Host 等价 + BUG1 + client wire | `client-rcio-parity.mjs` | 18 | 0 | 0 |
| C Host 工具 + 真 HTTP 往返 | `host-http-roundtrip.mjs` | 34 | 0 | 1 |
| D Skill 文本 | `skill-text.mjs` | 10 | 0 | 0 |
| E 差异审计 + 冻结指纹 | `skill-diff-audit.mjs` | 5 | 0 | 0 |
| **合计** | | **124** | **0** | **1** |

## 1. 复现方式

```powershell
# 一次跑完 A–E（有 FAIL 退出码非 0；本次退出码 0，耗时 34.7 s）
& 'C:\Users\Devcl\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe' `
  'C:\Users\Devcl\Desktop\CSL2\plugins\csl2-city-advisor\tests\verification\run-all.mjs'
```

单跑某一项（把脚本名换成下表任一）：

```powershell
$NODE='C:\Users\Devcl\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe'
$V='C:\Users\Devcl\Desktop\CSL2\plugins\csl2-city-advisor\tests\verification'
& $NODE "$V\rcio-cases.mjs"            # B5，快速
& $NODE "$V\client-rcio-parity.mjs"    # B6 + BUG1 + client wire（会顺带跑作者的脚本）
& $NODE "$V\host-http-roundtrip.mjs"   # C，约 35 s（含 30 s 总超时实测）
& $NODE "$V\skill-text.mjs"            # D
& $NODE "$V\skill-diff-audit.mjs"      # E
& $NODE "$V\static-integrity.mjs"      # A1–A3
& $NODE "$V\cordis-patch-assert.mjs"   # A4（≤30 行、零依赖）
```

机读产物：`_probe/verify/run-all-summary.json`（含逐项结论）、`_probe/verify/original-skill-hashes.json`（E14 基线）、
`_probe/verify/run-all-final.log`（**最终一次全量运行**的完整输出，退出码 0）、
`_probe/verify/run-all-full.log`（前一次）、`_probe/verify/mutants/`（变异测试临时副本）。

> 最终一次全量运行（`run-all-final.log`）是在所有源文件冻结、且本报告的断言全部定稿之后跑的：
> `TOTAL: PASS=124 FAIL=0 UNVERIFIED=1`，退出码 0；日志开头与结尾各打印了一次实测哈希，
> 与第 2 节的表逐位一致 —— 即本报告的结论与「验证时的那一版源码」是同一版。

脚本清单（全部零第三方依赖，只用 Node 内建；本机无 `js-yaml`、捆绑 Python 无 PyYAML，
所以 `cordis.patch.yml` 的断言是手写的 24 行文本解析，不是 YAML 解析）：

| 文件 | 作用 |
|---|---|
| `harness.mjs` | 共享小工具：PASS/FAIL 收集、`--json` 汇总、**文件描述符重定向**的子进程捕获（本机沙箱下 `child_process` 默认 `pipe` 会 EPERM） |
| `static-integrity.mjs` | A1–A3 |
| `cordis-patch-assert.mjs` | A4（24 行） |
| `rcio-cases.mjs` | B5 |
| `client-rcio-parity.mjs` | B6 + BUG1 + client wire + 作者脚本退出码 |
| `host-http-roundtrip.mjs` | C7–C10 |
| `skill-text.mjs` | D11–D13 |
| `skill-diff-audit.mjs` | E14–E16 |
| `run-all.mjs` | 入口（依次跑上面 7 个，聚合 PASS/FAIL） |

## 2. 验证时的冻结哈希（本进程实测，与 Lead 的指纹逐位吻合）

> ⚠️ **2026-10-15 追加变更（Lead 要求）**：用户要求把待填写面板改成**弹窗形态**，
> `lib/client.js` 与 `tests/client-rcio-parity.mjs` 被修改；**本节的哈希是弹窗改造之前的那一版**。
> 弹窗改造 + 后续 Portal 修复后的实测（Lead 复跑本套件，结论仍为 **PASS=124 / FAIL=0 / UNVERIFIED=1**）：
> - `lib/client.js`（当前）= `E830CA74D6A053307AFAEA6771D49BB106C59371449641ECBEFA74CB43ABFA7C`
> - `lib/index.js`（当前）= 见下方表格值 + 新增 `action:'diag'` 诊断分支（哈希请以 `Get-FileHash` 复算为准）
> - 其余文件未变。弹窗形态另由作者脚本的 `7f` 回归锁覆盖
>   （start 必须是 `.csl2-modal`（role=dialog + aria-modal + 遮罩 + Esc），result 阶段不得有模态）。
>
> **为什么会有第二次改动（Portal）**：宿主 `GET /csl2-readings?action=diag` 实测
> `{"open":1,"poll":39,"pendingPanels":1}` —— 客户端半已加载并稳定轮询，但用户看不到弹窗：
> 面板渲染在工具卡片内部，**卡片未展开时不渲染 body**，`position:fixed` 也救不了。
> ⇒ 改用 `react-dom` 的 `createPortal` 挂到 `document.body`；并因此把 `react-dom`
> 加入 A2 的允许 require 清单（与 `react` 同属平台共享模块图的内置包，2026-10-15 Lead 裁定）。

| 文件 | 实测 sha256 | bytes | 与 Lead 声明 |
|---|---|---|---|
| `lib/client.js` | `9C02C8B01C7C77DD514C9F48FC2CFD666D5A8F39F298876D9DBDE8C9ED51DBB3` | 48419 | ✓（弹窗改造前） |
| `lib/index.js` | `BA017EAF267CEEF540CBB1A405CF17C3ED7EC1313FD48F1CCC62BDFA74DC1634` | 45571 | ✓ |
| `lib/rcio.js` | `D7F82A9A8EFB83DAA0802B1343797830FFDC4D47627FA867A767D81065CB5A85` | 12669 | ✓ |
| `package.json` | `33FA9C438D843952685A2F1722B1FCF131606A530FD2668315CA6F84548A75F8` | 928 | ✓ |
| `cordis.patch.yml` | `E961F5842914F1041B7A502DB50855CDC734B52EF456D23AF6BCA7CB5B5BD78C` | 244 | ✓ |
| `CONTRACT.md` | `142E12DA538883DC3A0008885961BF353F2236953E5CB4DB5BEABE4210692DCF` | 8717 | ✓ |
| `tests/client-rcio-parity.mjs`（作者的） | `0256275B3F46508A324F8AFB001517D78D83F150115F1437B8A431C34678AF54` | 42867 | ✓ |

**本报告的每一项结论都是针对上表这一版**（作者声明已全部冻结，最终 run-all 在冻结后重跑过一次；
`run-all.mjs` 会在每次运行时把这两条哈希打进日志与 `run-all-summary.json`）。

E16 的 5 个 skill 冻结指纹（sha256 + bytes 双口径，不含行数）全部吻合：

| 文件 | sha256 | bytes | `\n` 数 |
|---|---|---|---|
| `SKILL.md` | `8162BAE4…3F849C` | 153244 | 1209 |
| `references/46-algorithm-roadmap.md` | `B068C3FF…A7D0A` | 36641 | 617 |
| `references/100-worked-example.md` | `227A0CB3…A8EE9` | 7628 | 145 |
| `references/70-carto-data-schema.md` | `17BD758F…6CFD8` | 48846 | 689 |
| `references/120-rcio-input-step.md` | `183D889E…4C308A` | 7933 | 117 |

> 行数口径说明：`SKILL.md` 有 1209 个 `\n`、以换行结尾（物理行 1209；Lead 口径 1210 是把结尾空行算进去），
> 按 Lead 的最新指示**行数不用于判 FAIL**，只作参考。

---

## 3. A. 静态完整性 —— 全部 PASS

**A1 `node --check`**（三条命令 `node --check <file>`，退出码均为 0）

```
PASS A1.node-check.index.js   :: node --check 退出码 0（45571 bytes）
PASS A1.node-check.rcio.js    :: node --check 退出码 0（12669 bytes）
PASS A1.node-check.client.js  :: node --check 退出码 0（48419 bytes）
```

**A2 `lib/client.js` bundle 外壳**

```
PASS A2.shell.firstLine  :: 首行 = "window.__ModuleLoader__.load({"
PASS A2.shell.id         :: bundle id = "csl2-city-advisor" === package.json name "csl2-city-advisor"
INFO bundle 内的 require("…") 字面量：["react"]
PASS A2.noThirdPartyRequire   :: 无第三方裸包 require（允许 react / @deepseek-ai/*）
PASS A2.requireLiteralOnly    :: require() 全部是字符串字面量
PASS A2.noEsmSyntax           :: 无 import( / import x / export 语句（纯脚本 bundle）
INFO bundle 里 exports.* 赋值：["__rcio","apply","inject","__panel"]
```

- 扫描前先把注释替换成空格（保留字符串字面量），所以文件头注释里「无第三方 import」这类**中文说明文字不会误报**。
- 唯一出现的 `require` 是 `require("react")`（`lib/client.js:348`），符合 DSH-CONTRACTS Q3b 的允许集。
- ⚠️ 按要求**没有**断言客户端导出必须有 `name`（真实 `dsh-univer-office` 客户端也只有 `apply` + `inject`），
  只如实记录实际导出：`apply` / `inject` / `__rcio` / `__panel`（后两个是作者声明的测试钩子）。

**A3 `package.json`**

```
PASS A3.bundlePatch   :: dsh.bundle.patch = "./cordis.patch.yml" 指向的文件存在
PASS A3.clientPlatform:: dsh.client.platform = "web"（必须 "web"）
PASS A3.clientInject  :: dsh.client.inject = ["@deepseek-ai/dsh-client-ui-tool"] 含该包
PASS A3.exportsClient :: exports["./client"].default = "./lib/client.js" 指向的文件存在
PASS A3.main          :: main = "./lib/index.js" 指向的文件存在
```

**A4 `cordis.patch.yml`**（`cordis-patch-assert.mjs`，24 行 / 零第三方依赖 / 本机无 YAML 库）

```
PASS A4 cordis.patch.yml：单元素数组 + insert[0].id/name=csl2-city-advisor + 无 tab
```

断言口径：`/^\t/` 无 tab；顶层 `^-\s` 行恰好 1 行且为 `- insert:`；`insert` 下 `- id:` 恰 1 项；
正则取出的 `id` 与 `name` 都 === `csl2-city-advisor`。

---

## 4. B. rcio 口径 —— 全部 PASS

### B5 `lib/rcio.js`（43 项 PASS）

**期望值不是抄代码**：脚本在运行时从 `CONTRACT.md` 文本里抽出 §4 的两张表（表头 + 数据行），
再用另写的一份判定（`expectedLevel` / `expectedBand` / `expectedFlags`）对照 `lib/rcio.js`。

```
PASS B5.contract.tablesFound     :: CONTRACT.md §4 抽出 6 行需求档位 + 4 行失业率档位
PASS B5.contract.levelBoundaries :: ["≤ -0.6","-0.6 < n < -0.15","-0.15 ≤ n ≤ 0.15","0.15 < n < 0.5","0.5 ≤ n < 0.8","≥ 0.8"]
PASS B5.contract.bandBoundaries  :: ["< 3","3 – 8","> 8 – 12","> 12"]
PASS B5.contract.levelOrder      :: LEVELS = ["collapse","negative","neutral","weak","demand","strong"]
PASS B5.contract.levelLabels     :: ["需求崩塌（负）","负需求","无需求","弱正需求","需求","强需求"]
PASS B5.contract.bandOrder       :: BANDS = ["low","normal","high","severe"]
PASS B5.contract.bandLabels      :: ["偏低（劳动力紧张）","正常范围","偏高","严重（税基会自己缩）"]
PASS B5.bar.boundaries  :: 17 个 bar 边界值：level/bar/percent/normalized/levelLabel 全部与 §4 一致
INFO bar 边界映射：-100→collapse -61→collapse -60→collapse -59→negative -16→negative -15→neutral -14→neutral
                    0→neutral 14→neutral 15→neutral 16→weak 49→weak 50→demand 51→demand 79→demand 80→strong 100→strong
PASS B5.band.boundaries :: 11 个失业率用例（含 null）全部与 §4 一致
INFO 失业率映射：0→low 2.9→low 3→normal 7.9→normal 8→normal 8.1→high 11.9→high 12→high 12.1→severe 100→severe null→null
PASS B5.example.deepEqual          :: standardize(§1 示例) 与 §4 重算结果逐字段相等（flags 有序 = ["office_strong","residential_negative"]）
PASS B5.example.contractSummary    :: CONTRACT.md §1 的 summary 与计算结果逐字相同："住宅 −35｜商业 +12｜工业 0｜办公 +85｜失业率 6.5%"
PASS B5.example.contractFlags      :: §1 的 flags（含顺序）= ["office_strong","residential_negative"]
PASS B5.example.contractUnemployment :: §1 的 unemployment = {"percent":6.5,"fraction":0.065,"band":"normal","bandLabel":"正常范围"}
PASS B5.example.contractZones      :: §1 的 4 个 rcio 节点与计算结果逐字相同（4 行命中）
PASS B5.relation.normalizedPercentFraction :: normalized = bar/100、percent = bar、fraction = percent/100
PASS B5.flag.rules :: 四条 flag 规则：只触发自身的输入 + 刚好不触发的边界输入全部符合 §4
PASS B5.signature.classifyLevelTakesBar          :: (-60→collapse, -0.6→neutral, 80→strong, 0.8→neutral)
PASS B5.signature.classifyUnemploymentTakesPercent :: (0.5→low, 3→normal, 13→severe, null→null)
PASS B5.extra.summaryNoUnemployment :: 失业率未提供时 summary 写作「失业率 未提供」
PASS B5.extra.flagsOrderIndependent :: flagsOf 与独立实现（§4 顺序）一致
```

- **§1 示例自洽**：`standardize({residential:-35,commercial:12,industrial:0,office:85}, 6.5)` →
  `negative / neutral / neutral / strong`、`unemployment.band === 'normal'`、
  `flags` 有序等于 `["office_strong","residential_negative"]`、
  `summary === "住宅 −35｜商业 +12｜工业 0｜办公 +85｜失业率 6.5%"`（U+2212 减号 + U+FF5C 竖线，从 §1 文本里抽出后逐字比对）。
- **flag 规则的边界输入**（脚本打印的实测）：
  `office_strong` 触发 80 / 不触发 79；`residential_negative` 触发 -16 / 不触发 -15（-15 时只剩 `all_neutral`）；
  `unemployment_severe` 触发 12.1 / 不触发 12；`all_neutral` 触发全 0 / 不触发（office=16）。
- **函数签名契约**：`classifyLevel` 收 **bar**（`classifyLevel(-0.6)==='neutral'`、`classifyLevel(-60)==='collapse'`
  就是判别式：若收归一值，-0.6 会判成 collapse）；`classifyUnemployment` 收 **percent 或 null**
  （`classifyUnemployment(0.5)==='low'` 证明不是 fraction 口径）。
- **反例（23 项全 PASS，全部不抛错且可判定）**，实测行为：

| 输入 | 实测结果 |
|---|---|
| `describeZone(101)` | `bar=100, level='strong'`（夹取） |
| `describeZone(-101)` | `bar=-100, level='collapse'` |
| `describeZone(NaN)` | `bar=0, level='neutral'`（不可数 → 0） |
| `standardize({residential:-35}, 6.5)` | 缺字段按 0/neutral；residential=-35/negative |
| `standardize(null, null)` | 四条全 0/neutral；unemployment 四字段全 null；`summary="…失业率 未提供"`；`flags=["all_neutral"]` |
| `standardize([1,2,3], 5)` | 数组不是 record → 四条全 0；失业率 5→normal |
| `standardize("abc","abc")` | 四条全 0；失业率 null |
| `standardize({residential:'12',commercial:'abc',industrial:{},office:[]}, '')` | `'12'→12`、其余 0；失业率 null |
| `clampBar(NaN/'abc'/±Infinity)` | 全为 `0`（**非有限数视为「不可数」**，见附注 F3） |
| `classifyLevel(null/'abc')` | `'neutral'` |
| `classifyUnemployment(NaN/'abc')` | `null` |
| `levelLabelOf/bandLabelOf('nope')` | `''` |
| `describeUnemployment(150 / -5)` | `100/severe` / `0/low`（夹取） |

### B6 Host/Client 口径等价（独立实现，不依赖作者的脚本）

`client-rcio-parity.mjs` 用 `window.__ModuleLoader__.load` 桩装载**真实的 `lib/client.js`**，
取出 `exports.__rcio`，与 `lib/rcio.js` 对比：

```
PASS B6.hook.__rcio   :: 客户端 bundle 暴露了 exports.__rcio 测试钩子
PASS B6.const.tables  :: 7 张常量表逐项相等（ZONE_KEYS/ZONE_LABELS/LEVELS/LEVEL_LABELS/BANDS/BAND_LABELS/SCHEMA）
INFO B6 比对点总数 = 3405（含 -100…100 全整数网格 201 点、随机组合 500 组）
PASS B6.random.parity :: 在 3405 个比对点上完全一致（0 个不一致）
PASS AUTHOR.exitcode  :: 作者 tests/client-rcio-parity.mjs 退出码 0（"RESULT PASS（warnings=0）"）
```

- 比对逻辑是我另写的 `deepEqual`（`Object.is` 语义，能区分 `NaN` vs `null`、`-0` vs `0`——用 `JSON.stringify`
  会把 `NaN` 变成 `null` 从而掩盖差异，所以没用它）。
- 覆盖：12 个公开函数逐点 + `standardize` 深度相等（含 `summary`/`flags`），
  ≥200 组随机输入的要求以 **500 组确定性随机（mulberry32，seed=0x5eed2026）+ 201 点整数网格**满足，可复现。
- 作者自己的脚本**单独跑一次**并如实报告退出码（0，`RESULT PASS（warnings=0）`）——但我没有把它当作证据来源。

### BUG1 回归（Lead 追加要求）—— PASS，且做了变异测试

历史上 `lib/client.js` 有一处双重归一（面板档位文字在 −100…100 上除 0 外全显示「无需求」）。三重独立复算：

```
PASS BUG1.static.noDoubleNormalize :: 3 个调用点的实参都不含 /100（["value","value","bar"]）
PASS BUG1.dynamic.sliderCount      :: InteractivePanel 渲染出 4 条竖向滑动条，顺序 ["住宅","商业","工业","办公"]
PASS BUG1.dynamic.levelText        :: VerticalSlider 在 bar = [-100,-60,-35,0,12,50,80,85,100] 上渲染出的档位文字
                                      与 lib/rcio.js 的 levelLabelOf(classifyLevel(bar)) 逐字一致（4×9 = 36 个断言点）
PASS BUG1.dynamic.signedText       :: 带符号数值文字与 formatSignedBar 一致（+48 / −35 / 0，U+2212）
PASS BUG1.dynamic.ariaValueText    :: input[type=range].aria-valuetext = "<带符号数值>，<档位文字>"
PASS BUG1.dynamic.statePath        :: onChange(85) -> InteractivePanel.bars.residential=85 -> 档位文字「强需求」
PASS BUG1.mutation.applied         :: 变异副本已生成
PASS BUG1.mutation.detected        :: 变异副本（classifyLevel(value / 100)）在第 7/9 个 bar 上与正确档位不符
```

- 静态：注释剥离后扫描全部 `classifyLevel(` **调用点**（排除函数定义），实参为 `value`/`value`/`bar`，均无 `/100`。
- 动态：直接调用真实 `VerticalSlider` 组件函数（props 覆盖 `value`），读它渲染出的 `.csl2-zone-level`
  文字节点 —— 4 条滑动条 × 9 个 bar，全部与 Host 的 `levelLabelOf(classifyLevel(bar))` 逐字一致；
  并用 React hook 桩走了一遍 `onChange → changeZone → 重渲染` 的真实状态路径。
- **变异测试**：把 bug 改回临时副本 `_probe/verify/mutants/client-classifyLevel-double-normalize.js`
  （只改 `VerticalSlider` 内那一处，不改仓库文件），重新装载后**9 个 bar 全部渲染成「无需求」**，
  我的动态断言在第 7/9 个 bar 上判 FAIL —— 证明这条断言确实有牙。
  （顺带发现：如果变异改的是 `describeZone` 那一处，卡片文字不会变、只有 `__rcio` 比对能抓到；
  所以两处断言都保留。）

### client wire 形态（Lead 追加要求 2/3）

```
PASS WIRE.open.body :: open: POST /csl2-readings body={"action":"readings.open","callId":"call-from-props"}（带 callId，不带 panelId）
                       url=http://127.0.0.1:19387/csl2-readings，headers.content-type=application/json，credentials=same-origin
PASS WIRE.interval.cadence :: 拿到 panelId 后启动 1 个 setInterval，间隔 1500 ms
PASS WIRE.poll.body :: poll: body={"action":"readings.poll","panelId":"p-from-host"}（用 Host 回填的 panelId）
PASS WIRE.businessFailureIsNotTransportFailure :: HTTP 200 + ok:false(code:no-panel) 未按通道不可用处理
                       （状态行="正在打开面板…"），只触发 1 次业务退避重试（共 2 次 fetch）
PASS WIRE.transportFailureRetries :: HTTP 500 -> 共 3 次 fetch（首试 + 2 次退避重试），
                       之后状态行="面板通道不可用（POST /csl2-readings），本次按未提供处理。"
PASS WIRE.actionNames :: ["readings.open","readings.submit","readings.skip","readings.poll"]
```

即：客户端 `open` body 确实带 `callId: props.callId`；四个动作名是 `readings.*` 全名；
**业务失败 = HTTP 200 + `body.ok === false`**（不触发传输层退避重试），只有非 2xx 才算「通道不可用」。

---

## 5. C. Host 工具可加载性（真 HTTP 往返）—— 34 PASS / 1 UNVERIFIED

### C7 `import()` 导出

```
PASS C7.exports :: name="csl2-city-advisor"；inject=["tools","skills"]（含 tools + skills）；apply 是 function
INFO lib/index.js 导出：["DEFAULT_TIMEOUT_SEC","MIN_TIMEOUT_SEC","ROUTE_PATH","RPC_ACTIONS","TOOL_NAME","__test",
                          "apply","dispatchRpc","inject","name","sanitizeRaw"]
```

### C8 stub ctx 跑 `apply()`

stub 用 Proxy 包住真实对象，**未实现却被访问**的成员会被记录：

```
PASS C8.apply.noThrow :: apply(stub) 未抛错；注册了 1 个工具、1 条路由、1 个 provider；effect 标签 ["csl2: readings http route"]
INFO 未实现却被访问的 stub 成员：（无）
INFO ctx.logger.warn 记录：（无）；ctx.inject 调用：[]
PASS C8.tool.registered              :: name="csl2_city_readings"
PASS C8.tool.parametersRawJsonSchema :: parameters 是原始 JSON Schema：type="object"，properties 含 city/savePath/reason/timeoutSec；required 不存在
PASS C8.tool.output                  :: output.schema 存在（根 type="object"），output.render 是函数，output.presentationMeta 是函数
PASS C8.route      :: 1 条路由：{"kind":"prefix","path":"/csl2-readings","handler":"function"}
PASS C8.skill.registerProvider :: 调用一次；provider.name="csl2-city-advisor"
PASS C8.skill.candidate        :: list() 返回 1 个候选：name="cities-skylines-2-city-advisor"
PASS C8.skill.resourceBase     :: {"kind":"directory","path":"…\plugins\csl2-city-advisor\skills\cities-skylines-2-city-advisor\"}（目录存在）
PASS C8.skill.content          :: content 非空、不以 --- 开头（"# Cities: Skylines II 城市规划顾问…"），含「城市规划顾问」
```

- `parameters` 是**原始 JSON Schema**（`type:'object'` + `properties`），**没有**头要求的
  `required:true` 这类 authoring-DSL 形态；`required` 键整个不存在（若存在则必须是字符串数组——脚本对两种情形都判）。
- `ctx.inject` 未被调用：因为 stub 提供了 `webServer`，`mountRoute()` 直接成功（这也验证了「有 webServer 时不走惰性等待」）。

### C9 真 HTTP 往返（把捕获到的 handler 接到真的 `node:http` server，端口 61998）

```
PASS C9.open.bare        :: HTTP 200 {ok:true, panelId:"r-1rr1c", zones:4}（唯一未结算面板 -> 裸 open 可关联）
PASS C9.open.panelShape  :: 标题="测试市 · 请先补 RCIO 需求条与失业率"；rpc={"path":"/csl2-readings","method":"POST",
                            "actions":["readings.open","readings.submit","readings.skip","readings.poll"]}
PASS C9.poll.pending     :: HTTP 200 {"ok":true,"status":"pending"}
PASS C9.submit.provided  :: HTTP 200 {"ok":true,"status":"provided","panelId":"r-1rr1c"}
PASS C9.execute.provided :: status="provided" source="slider-panel"；standard 与 lib/rcio.js 对同一 raw 的结果深度相等；
                            summary="住宅 −35｜商业 +12｜工业 0｜办公 +85｜失业率 6.5%"
PASS C9.submit.duplicateRejected :: 重复 submit 被拒：HTTP 200 {"ok":false,"code":"already-settled",…}
PASS C9.poll.settled     :: {"status":"settled","result":"provided"}
PASS C9.open.callId      :: open 带 callId -> HTTP 200 panelId="r-2s0zf"
PASS C9.skip.action      :: HTTP 200 {"ok":true,"status":"skipped","panelId":"r-2s0zf"}
PASS C9.execute.skipped  :: status="skipped" raw=null standard=null message="用户选择不补数据，直接分析。…"
PASS C9.concurrent.distinctPanels :: A={"id":"r-3aqr8","title":"甲城…","callId":"call-conc-A"}；B={"id":"r-44522","title":"乙城…","callId":"call-conc-B"}
PASS C9.concurrent.bareOpenAmbiguous :: 有 2 个未结算面板时裸 open 被拒（不猜）：{"ok":false,"code":"ambiguous-panel","panelIds":["r-3aqr8","r-44522"]}
PASS C9.concurrent.noCrossTalk :: A 的 standard 只含 RAW_A（"住宅 −60｜…｜失业率 3%"）；B 的只含 RAW_B（"住宅 0｜…办公 +90｜失业率 12.5%"）
PASS C9.method.notAllowed :: PUT/DELETE/PATCH -> HTTP 405/405/405 {"ok":false,"code":"method-not-allowed","error":"use POST (or GET for diagnostics)"}
PASS C9.path.notFound     :: /nope -> 404 {"code":"not-found"}；/csl2-readings/a/b -> 404
PASS C9.body.malformedJson:: 畸形 JSON body -> HTTP 400 {"code":"bad-request","error":"Expected property name or '}' …"}
PASS C9.action.unknown    :: 未知动作 -> HTTP 200 {"ok":false,"code":"unknown-action"}
PASS C9.action.shortNameAccepted :: 短名 action:'poll' 被接受（等价 readings.poll）
```

- **并发不串数据**（作者新增能力）：两个 `execute()` 各带自己的 `callId` → 两个 panelId、标题各自正确；
  提交后 `execute()` 返回的 `standard` 各自与自己的 raw 深度相等，且两者 `summary` 不同。
  有 2 个未结算面板时**裸 open 不猜**，返回 `ambiguous-panel`（比"随便挑一个"安全）。
- ⚠️ **与清单字面要求的一处差异（如实记录，非缺陷）**：清单写「非 POST 方法 → 405」，
  实测 `PUT/DELETE/PATCH → 405` ✓，但 **`GET /csl2-readings?...` → 200**：
  `lib/index.js:501` 的实现与错误文案（`use POST (or GET for diagnostics)`）都声明 GET 是**诊断通道**，
  所以「非 POST 一律 405」只对 GET/POST 之外的动词成立。按实现者声明的行为判为 PASS。
- 空 body POST → 200 + `{ok:false, code:'unknown-action'}`（未知动作不抛错）。

### C10 超时与取消

```
PASS C10.noClient.fastUnavailable :: CSL2_NO_CLIENT_MS=120 -> 132 ms 返回 status="unavailable" source="no-client"（不抛错，raw/standard 为 null）
PASS C10.cancel.degradedAndCleaned :: signal 取消 -> status="unavailable"（message 含「取消」）；
                                     取消后 poll(panelId)="no-panel" poll(callId)="no-panel"（两张 Map 都已清理）
PASS C10.timeoutClamp :: timeoutSec=5 -> 30（夹到最小 30）；timeoutSec='abc' -> 900（回落默认 900）
PASS C10.totalTimeout :: timeoutSec=30 -> 实测 30005 ms 后 status="timeout"
                         （message="等待读数面板超时（30 秒），未取得…"）
PASS C10.execute.malformedArgsNoThrow :: execute(null, null) 未抛错，134 ms 返回 status="unavailable"
UNVERIFIED C10.default900sNotMeasured :: 默认 timeoutSec=900 与实测的 30 s 走同一条 setTimeout 分支
                         （lib/index.js waitForPanel），按 900 s 实等不可接受，故未实测
```

`CSL2_NO_CLIENT_MS` 是作者提供的合法测试钩子（`lib/index.js:949-952`），只在测试里用，
**没有为跑得快而改动被验证的代码**。

---

## 6. D. Skill 文本 —— 全部 PASS

```
PASS D11.stepOrder :: ### 第 0 步 = 第 362 行 < ### 第 1 步：问清问题与拿到数据 = 第 416 行
PASS D11.rule14    :: 「铁律 14」出现 2 处；§0（第 99 行起）顶格条目 = [1..14] 连续
PASS D11.ref120.existsAndShort :: references/120-rcio-input-step.md 存在，物理行数 117 ≤ 120
PASS D11.toolNameMentions :: 「csl2_city_readings」共 6 处 {"SKILL.md":3,"120-rcio-input-step.md":1,
                             "46-algorithm-roadmap.md":1,"70-carto-data-schema.md":1}（≥4）
PASS D12.name             :: frontmatter name = "cities-skylines-2-city-advisor"（与原目录相同）
PASS D12.description      :: 单行；以原描述为前缀（原 942 字 -> 现 1092 字）；末尾含追加英文句「…(skippable), then analyze.」
PASS D13.jsonExampleIdentical :: CONTRACT.md §1 与 120 的 JSON 示例空白归一后逐字相同（各 24 行）
PASS D13.levelTableRows :: 6 行需求档位数据行两边逐格相同
PASS D13.bandTableRows  :: 4 行失业率档位数据行两边逐格相同
PASS D13.tenRowsBothSides :: 6 档 + 4 档 = 10 行数据行两边同时命中（CONTRACT 6+4，120 6+4）
```

- `§0` 的 1–14 只统计**顶格**的 `N. ` 条目（规则 10 里有缩进的 1–5 子列表不会被误算）。
- frontmatter 按要求**宽松**比对（正则取 `name:` / `description:` 行），**没有**用严格 YAML 解析
  （`Cities: Skylines II` 里的 `: ` 是改动前就有的形态）。

---

## 7. E. 与原工作区 skill 目录的差异审计 —— 全部 PASS

```
INFO 原目录快照：1121 个文件，113256351 bytes，最新 mtime = 2026-10-15T05:53:51.494Z
PASS E14.baselineCreated / E14.originalUnchanged
     :: 基线写于 _probe/verify/original-skill-hashes.json（1121 个文件）；
        最终 run-all 与基线比对：sha256/bytes/mtime 全部未变（无新增/删除/修改）
INFO 文件总数：原目录 1121，插件内 1122（差 1）
PASS E15.noUnexpectedDifference :: 除 5 个允许项外全部逐字节相同：1117 个文件 sha256 相同
PASS E15.newFileIsOnly120  :: 插件内新增文件恰为 ["references/120-rcio-input-step.md"]
PASS E15.allowedSet        :: 允许改动的 4 个文件确实改了：
                              SKILL.md 146647→153244B；100-worked-example 7396→7628B；
                              46-algorithm-roadmap 36363→36641B；70-carto-data-schema 48489→48846B
PASS E16.fingerprints :: 5 个冻结指纹（sha256 + bytes）全部吻合
```

- **E14 的执行方式**：首次运行建立基线（1121 个文件的 `mtime+sha256`，落在 `_probe/verify/original-skill-hashes.json`），
  最终 run-all 再次快照并**与基线逐文件比对**——两者完全一致，即在我整个验证期间原目录**零改动**。
  原目录最新 mtime 是 2026-10-15 05:53:51Z，早于插件内 skill 副本的改写时间。
- 差异集合恰好是清单允许的 5 个文件：4 个已存在文件被改 + 1 个新增 `120-rcio-input-step.md`；
  其余 **1117 个文件逐字节相同**（含 `scripts/**`、`extract/**` 的全部文件）。

---

## 8. 未验证项与原因（逐条）

| # | 未验证项 | 原因 |
|---|---|---|
| U1 | 默认 `timeoutSec=900` 的总超时实际行为 | 与已实测的 `timeoutSec=30` 走同一条 `setTimeout` 分支（`lib/index.js:889`），实等 900 s 不可接受。已实测：`timeoutSec=30 → 30005 ms → status:'timeout'`、`timeoutSec=5 → 夹到 30`、`'abc' → 900`。 |
| U2 | 默认 `CSL2_NO_CLIENT_MS=60000`（用户不打开面板时的 60 s 放弃窗口） | 用合法钩子把它缩到 120 ms 验证了同一分支（132 ms 返回 `unavailable`），60 s 原值未实等。 |
| U3 | `settle` 后 `SETTLED_TTL_MS = 300000` 的延迟回收 | 需要等 5 分钟；已验证的是**取消路径立即清理**（两张 Map 都拿不到）。`poll` 在 TTL 内仍能拿到 `settled` 已实测。 |
| U4 | 真机安装进 `desktop` profile + GUI 端到端（浏览器里真实 `fetch` 打到 `/csl2-readings`、React 真渲染面板） | 不在本任务范围（Lead 的端到端项）；且本会话审批被禁用，`plugin_manager install_bundle` 需要 `danger-full-access` 无法自助执行。本报告证明的是「代码与运行时契约一致 + handler 在真 `node:http` server 上行为正确」。 |
| U5 | 真实 React（18/19）下的挂载、交互与样式注入 | 我用的是自写 hook 桩（非真 React 运行时），只能证明组件是 props/state 的纯函数、渲染文字/无障碍属性正确、wire 形态正确。 |
| U6 | `ctx.slots.register` 在真实 `dsh-client-ui-slots` 里的完整校验表 | `DSH-CONTRACTS.md` 明确把这张表标为 UNVERIFIED（只确认了 keyed 的 `key` 必填）。我验证到的是客户端注册调用形态：`slots.inject('tool.call.toolview', …register({name,key:'csl2_city_readings'}))`。 |
| U7 | `ctx.webServer.register` 的真实挂载语义（重复 path 抛错、最长前缀匹配、是否被浏览器请求到） | 我只验证了注册的 route 对象形状（`kind:'prefix'`、`path`、`handler` 函数）与 handler 在真 http server 上的完整行为。 |

**没有任何"推测被当成结论"的条目**：以上都标注为未验证；已 PASS 的每一项都有命令与实测输出。

---

## 9. 附注：验证过程中发现、但不判 FAIL 的事实（供 Lead 决定是否写进文档）

| # | 事实 | 依据 |
|---|---|---|
| F1 | **业务失败 = HTTP 200 + `body.ok:false`**，不是 4xx。`already-settled` / `no-panel` / `ambiguous-panel` / `unknown-action` 全部 200。客户端据此区分「业务失败」与「通道不可用」。 | C9 实测；Lead 追加要求 3 |
| F2 | `GET /csl2-readings` 是**诊断通道**，返回 200 而不是 405。 | `lib/index.js:491-496, 501` |
| F3 | 非有限数（`NaN` / `±Infinity`）在 `clampBar` 里按「不可数 → 0」处理，**不是**夹取到 ±100；有限越界值才夹取。 | `lib/rcio.js:104-113, 127-134`；B5 反例实测。JSON 线上也传不了 `Infinity`，风险极低 |
| F4 | `describeUnemployment` 的 `fraction` 显式 `round(x,6)`；因此 `2.9/100` 的裸双精度值（0.028999999999999998）与字段值（0.029）**不严格 `===`**，需按 1e-9 容差比较。我的断言已按容差写，并把这一点记录在此。 | `lib/rcio.js:217-224`；B5 首次运行因此报过 2 个假 FAIL，已改正 |
| F5 | `parameters` 里**没有** `required` 键（四个参数全部可选），符合契约 §1 的表格。 | `lib/index.js:293-304` |
| F6 | `apply()` 在有 `webServer` 时不会调用 `ctx.inject`；只有在 `webServer` 缺失时才惰性等待（`carrier.pending`）。路由挂不上时工具**立即**返回 `unavailable`（`lib/index.js:349-351`），不会干等 60 s。 | C8 实测（`ctx.inject 调用：[]`） |
| F7 | `run-all.mjs` 聚合 `cordis-patch-assert.mjs` 时按其退出码折算 1 个结论（该脚本只有 24 行、不产出 `--json`，这是为了满足「≤30 行零依赖」的硬要求）。首次实现曾把它误计为 FAIL，已修正。 | `run-all.mjs` 的 `summary === null` 分支 |
| F8 | 本机沙箱下 Node 的 `child_process` 默认 `'pipe'` stdio 会 `EPERM`，所以所有子进程捕获都走**文件描述符重定向**（`harness.runCapture`）。 | 实测：`spawnSync(...,{encoding:'utf8'})` → `err EPERM` |
| F9 | 验证者未改动任何被验证文件：报告里的 6 个冻结哈希全部等于 Lead 的声明值，且在**最终一次 run-all** 里重新实测过。 | 第 2 节；`run-all-summary.json` |

---

## 10. 结论

清单里 A–E 的全部可验证项通过（124 PASS / 0 FAIL），三个作者声明的"易错点"都被独立复现并确认已修复：

1. `classifyLevel` 的双重归一 bug：静态、动态（36 个渲染断言点）、变异测试三重确认**已修复**；
2. `readings.open` 的 `callId` 并发关联：客户端 body 实测带 `callId`，两个并发面板的 HTTP 往返实测**不串数据**；
3. 动作名 `readings.*` + 业务失败 `HTTP 200 + ok:false`：Host 与 Client 两侧都实测一致。

唯一未验证项是 U1（默认 900 s 总超时未实等），已在第 8 节如实标注。
