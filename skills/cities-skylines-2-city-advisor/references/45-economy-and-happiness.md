# 45 · 经济与幸福度机制（税收 / 幸福度 / 地价 / 交通乘数）

> 目标链条：**土地用途与强度 → 岗位/人口/公司利润 → 地价与租金 → 税收**；**交通效率 → 可达性 → 地价/幸福度/公司效率**；**服务与污染 → 幸福度 → 人口留存与需求**。
>
> 本文件检索执行日期：**2026-10-12**（本次实际联网检索，未凭记忆作答）。
> 基准版本：**1.6.2f1「Autumn Breeze」2026-09-15**。断代点：**1.1.5f1「Economy 2.0」**。
> 每条结论后的标记含义：
> - `[游戏机制]` = 有官方一手来源（官方 Wiki 自动生成表 / 官方 Dev Diary / 官方补丁说明）
> - `[社区实证]` = 玩家实测或社区解析，**有数据但未经官方确认**，可信度另行标注
> - `[待验证]` = 无可靠来源，**禁止当机制引用**
>
> 引用格式：`（来源：<URL>，版本 <X>，可信度 <高/中/低>）`
> 来源编号（S##/C##）与 `00-sources.md` 一致。

---

## 0. 一页速答（先看这里）

| 问题 | 结论 | 标记 |
|---|---|---|
| 住宅税的税基是什么 | **市民的月度工资**，且只对超过 `Residential Minimum Earnings` = **₡1400/月**的部分征收 | `[游戏机制]` |
| 商/工/办的税基是什么 | **公司的月度利润**（monthly profits） | `[游戏机制]` |
| 公司"亏损"怎么判 | **`Profit <= 0`（含等于 0）**；**不得再用 `Profit < 0`**（`Profit` 永不为负）。若读得到月收入/月成本，则 **月收入 ≤ 月成本** 亦判亏（Carto 现无此两字段） | `[游戏机制]` + 当前口径 |
| 什么时候能拿"亏损"当证据 | 只有**商业热门时段（日间平峰 10–15 时 + 晚高峰 16–19 时）**的存档；**凌晨（0–5 时）存档的亏损不作证据** | `[经验]`（时段，无官方来源） |
| 税率范围 | **−10% ~ +30%**（四类分区各一个总滑块，可下钻分级） | `[游戏机制]` |
| 有没有官方"甜蜜点" | **没有**。官方只有一句权衡："低税率让建筑升级更快，高税率带来更多钱" | `[游戏机制]`（"无甜蜜点"这一事实本身是机制结论） |
| 单位面积谁最赚 | **官方没有给这个数据**；本次也未找到可复现的玩家实测表 → **明确说"没有"** | `[待验证]` |
| 幸福度是什么构成的 | `Happiness = Well-being + Health`，官方列出 **10 个幸福度因子**（§2.1） | `[游戏机制]` |
| 地价公式 | 有来源清单（服务覆盖/商业可达性/公交站点/污染/岸线，有上限），**没有公布权重公式** | `[游戏机制]`（清单）/ `[待验证]`（权重） |
| 租金公式 | `Rent = (LandValue + (ZoneType × Building Level)) × LotSize × SpaceMultiplier` | `[游戏机制]`（官方 Dev Diary 原文） |
| 城外通勤者 | **完全不向本城缴税**（工资乘数 1.1，但钱不留在城里） | `[游戏机制]` |
| 福利（养老金/失业救济/家庭津贴）谁付 | **不由城市预算支出**，由游戏凭空生成 | `[游戏机制]` |
| 道路通行能力 pcu/h | **官方没有给**。官方只给了道路的 **noise/air pollution factor** 与限速、车道数 | `[待验证]` |

---

## 1. A · 税收（本轮靶心）

### A1. 税种与税基 —— 1.1.5f1 之后的实际公式

#### A1.1 四类分区的税基各不相同（这是最关键的一条）

| 分区 | 税基 | 官方原文 | 分级方式 |
|---|---|---|---|
| **住宅 Residential** | **市民的月度工资** | "Residential taxes are collected from the citizens' monthly wages." | 按 **5 个学历等级**分别设税率 |
| **商业 Commercial** | **公司的月度利润** | "Commercial, Industrial and Office taxes are collected from the companies' monthly profits." | 按 **产品类型**分别设税率 |
| **工业 Industrial** | 公司的月度利润 | 同上 | 按产品类型 |
| **办公 Office** | 公司的月度利润 | 同上 | 按产品类型 |

（来源：https://cs2.paradoxwikis.com/Economy ，正文最后编辑 2025-07-09，页面标注 `Potentially outdated / 1.0`，**可信度 高（机制描述）/ 版本可能滞后**）

#### A1.2 住宅税的**起征点**是精确数值（重要）

- `Residential Minimum Earnings` = **₡1400 / 月**。**只有超过这个数的工资部分被征税**。
- 工资完全由**学历**决定，与岗位层级无关（1.3.3f1 数值）：

| 学历（岗位层级名） | 月薪 |
|---|---|
| Highly Educated（Manager） | ₡2700 |
| Well Educated（Specialist） | ₡2400 |
| Educated（Senior） | ₡2100 |
| Poorly Educated（Basic） | ₡1800 |
| Uneducated（Simple） | ₡1500 |

（来源：https://cs2.paradoxwikis.com/Citizens ，页面明确标注数据版本 **1.3.3f1**，**可信度 高**）

> **可推导的住宅税基公式（本项目的推导，标注为推导而非官方）**：
> ```
> 住宅税基 ≈ Σ_就业市民_学历e  max(0, Wage(e) − 1400) × ResidentCount(e)
> 住宅税收 = 住宅税基 × 住宅税率(学历e)
> ```
> **关键推论**：未受教育者（₡1500）只有 **₡100** 超过起征点；高度受教育者（₡2700）有 **₡1300**。也就是说
> **一个 Highly Educated 市民的应税基础是一个 Uneducated 市民的 13 倍。**
> → **住宅税收的真正杠杆是"学历结构"，不是"人口数量"。** 这一条对算法（§46）影响极大。
> 本文标注：**`[推导]`** —— 起征点与工资是官方数值，但"两者相减即税基"这一步官方未明写。

#### A1.3 商/工/办的税基 = 公司利润 → 税收的**上游**是公司效率

官方的公司效率（Efficiency）因子表（来源：https://cs2.paradoxwikis.com/Economy ，**可信度 高**）：

| 因子 | 正面 | 负面 |
|---|---|---|
| **员工幸福度** | 平均员工幸福度上升 → 效率提升 | 下降 → 效率下降 |
| 员工数量 | — | 人手不足 |
| **城市生产专业化** | 对相关材料产量大的商业/工业给加成；默认上限 **115% @ 10 kt** | — |
| 签名建筑 | "Commercial Efficiency" / "Industrial Efficiency" 全城加成 | — |
| 电费 / 水费 | 降价 → 提升 | 涨价 → 降低 |
| 邮件处理 | 提升 | 降低 |

另有官方加成（1.6 自动生成表，**可信度 高**）：
- **Airport：+3% Office Efficiency（全城）**、+5% Attractiveness
- **International Airport：+10% Attractiveness、+10% Interest in University Education、+10% Demand for Software**
- **ChirpX Space Centre：+10% Demand for Software、+10% Demand for Electronics、+60 Indoor Recreation**
（来源：https://cs2.paradoxwikis.com/Transportation ，**可信度 高**）

> **`[游戏机制]` 因果链**：员工幸福度 ↑ → 公司效率 ↑ → 公司利润 ↑ → **商/工/办税收 ↑**。
> 这条链把"幸福度"和"税收"直接连起来了，是本轮核心目标里**唯一有官方文本支撑的完整链条**。

#### A1.4 公司「亏损」的判据 —— **`Profit <= 0`**（含等于 0）

**当前判亏口径有两个，按能读到的数据取用**：

| # | 判据 | 数据来源 | 现状 |
|---|---|---|---|
| ① | **`Profit <= 0`**（**含等于 0**） | Carto 建筑层字段 `Profit`（₡，按栋） | ✅ **现成可用** |
| ② | **`月收入 <= 月成本`** | 游戏内公司面板读数；将来 Carto 若有新字段 | ⚠️ **Carto 现有建筑层没有月收入 / 月成本字段**（已核实字段表） |

* ❌ **不得再用 `Profit < 0` 作为判亏口径。**
* **机制事实**：CSL2 里 `Profit` **永远不会为负** —— 付不起 `upkeep` 的公司**先降级、再废弃**，
  不记负利润（实测 212 栋商业 0 栋为负）。**所以 `<= 0` 在本游戏里实际就等于 `== 0`。**
  这也是 "公司利润" 这项指标在本游戏里**没有负侧信息**的原因：亏损不出现在数值里，
  只出现在"降级 / 废弃"这个**状态变化**里。
* **必须区分两类 0 利润**（否则会把两种完全不同的城市问题混成一张表）：

| 情形 | 含义 | 该怎么处理 |
|---|---|---|
| `Employee == 0` | **空置 / 停业**（没有岗位，店是空壳） | 用地与需求问题 → 看分区规模与需求条，不按"在营亏损"处理 |
| **`Profit <= 0` 且 `Employee > 0`** | **在营但毫无余量**（有人上班、账上不剩钱） | ⭐ **这才是真正要处理的对象**（效率/成本/顾客/税率侧） |

* Carto 建筑层**已核实字段表**（**其中没有月收入、也没有月成本**）：
  `Name` / `Address_*` / `Age` / `Asset` / `Brand` / `Category` / `Elevation` / `Employee` /
  `Household` / `Labor` / `Level` / `Object` / `Product` / `Profit` / `Resident` /
  `SexRatio` / `Theme` / `Zone` / `Zoning`。

> **来源与可信度**：`Profit` 永不为负、付不起 `upkeep` 先降级再废弃 —— `[游戏机制]`
> （官方 Economy / Zoning 的升级-降级-废弃链）；**`Profit <= 0` 判亏、空置与在营的区分 = 当前口径**，
> 依据为 Carto 逐栋实测（`[实测]`：212 栋商业 0 栋为负）。

#### A1.5 商业盈亏的**潮汐性** —— 凌晨存档的"亏损"**不作为证据**

* **商业盈亏随营业时段变化**：**凌晨（0–5 时）的存档大概率读出亏损，日间则不一定**。
  ⇒ **凌晨时段存档里的"亏损"不作为证据**（它反映的是"这个点店没开门"，不是"这家店不行"）。
* **分析重点 = "即使在商业热门时段仍然亏损"的那批店。**
  **热门时段（经验口径，无官方来源）** = **日间平峰 10–15 时 + 晚高峰 16–19 时**
  （两个时段名沿用 `70-carto-data-schema.md` 1.0.1 的游戏内时段划分）。
* **存档时点落在热门时段之外** → 相关结论**降级为「需白天（10–19 时）复导一次再判」**，
  并在结论里**写明本次存档时点**（存档时间可自动读取，不需要玩家输入）。
* **时点敏感性**：**「公司利润 / 亏损公司占比」对商业是时点敏感指标**
  （工业 / 办公 / 住宅的敏感度低得多）⇒ **跨时段比较商业利润时，必须同时报告存档时点**，
  否则两次读数的差异里混着"营业时段差"，会被误读成"商业变差/变好"。

> **来源与可信度**：潮汐性（凌晨亏损、日间不一定）= `[经验]`；
> **热门时段 10–15 时 + 16–19 时 = `[经验]`（无官方来源，不得写成游戏机制）**。

---

### A2. 税率滑块：范围、默认值、有没有"甜蜜点"

| 项 | 值 | 来源 | 标记 |
|---|---|---|---|
| 取值范围 | **−10% ~ +30%**（每一类分区一个总税率，可展开分级） | https://cs2.paradoxwikis.com/Economy | `[游戏机制]` |
| 默认值 | **官方 Wiki 与官方 Dev Diary 均未给出四类税率的默认数字** | — | `[待验证]` |
| 负税率 | = 补贴该产业（政府付钱给该群体） | https://cs2.paradoxwikis.com/Economy | `[游戏机制]` |
| 住宅分级 | **5 个学历等级** | https://cs2.paradoxwikis.com/Economy | `[游戏机制]` |
| 商/工/办分级 | **按产品类型** | https://cs2.paradoxwikis.com/Economy | `[游戏机制]` |
| 解锁里程碑 | **1.1.5f1 起：里程碑 1（Tiny Village）解锁税收与服务页** | https://cs2.paradoxwikis.com/Progression | `[游戏机制]` |

#### A2.1 "甜蜜点"——本轮结论：**官方没有，且官方明确把它设计成一个连续权衡**

官方原文（唯一的机制性表述）：
> "**Lower taxes help buildings level up faster while higher taxes bring more money.**"
> （来源：https://cs2.paradoxwikis.com/Economy ，**可信度 高**）

需求侧的官方表述：
> "Lower taxes will increase demand for residential zones while higher taxes will lower it."
> "Lowering taxes for certain products and increasing them for others is an effective way to specialize the city in a certain field."
> （同上）

1.1.5f1 官方补丁说明：
> "**Taxes now have more effect on demand**"；住宅税率进入"搬入家庭类型"判定。
> （来源：https://cs2.paradoxwikis.com/Patch_1.1.X ，**可信度 高**）

**可确证机制（写成算法可用的形式）**：
```
净效应(税率 τ) = 短期收入 ↑  ∝ τ
              − 升级速度 ↓    （高 τ → upkeep 付不满 → 建筑状况下降 → 长期税基衰减）
              − 需求 ↓        （高 τ → 搬入减少 / 公司利润下降 / 公司搬离）
```
**存在最优 τ\* 的机制条件是**：住宅税率既影响"每个市民交多少"，又影响"建筑等级"（等级高 → 人均应税工资不变，但容纳户数变多、维护费被分摊）。官方**从未给出 τ\* 的数值**。

**`[待验证]`——任何"10% 最优""12% 是甜蜜点"的说法在本次检索中没有找到有官方或可复现数据支撑的来源。禁止引用。**

#### A2.2 唯一一处官方文档给出的"高税率具体用法"（很有价值）

1.1.6f1 的 Known Issues 里，官方给出清理"卡在 5/5 员工的办公公司"的官方 workaround：
> "**Increase office tax to 30%** → Let the simulation run until all office buildings are empty, which may take about **a month** in-game time. … Once all office companies have left your city, set the tax back to your preferred level."
（来源：https://cs2.paradoxwikis.com/Patch_1.1.X ，1.1.6f1 Known Issues，**可信度 高**）

> **机制含义**：官方自己承认 **30% 办公税率会让公司在一个游戏月内全部离场**。
> 这给出了一个**可用的经验边界**：`办公税率 30% ≈ 强制清退`。反过来，日常税率必须显著低于 30%。
> 若把 "空置耗时 ≈ 1 个月" 外推，可粗略理解为"税率对公司的响应时间尺度 = 1 个游戏月"。**外推部分标 `[待验证]`。**

#### A2.3 有"税率容忍度"这个内部参数（但不是数值）

- **Central Bank**（1.3.6f1 重做后）：**−50% 贷款利息 / +1 幸福度税率容忍度**。
（来源：https://cs2.paradoxwikis.com/Patch_1.3.X ，**可信度 高**）

> `[游戏机制]` 游戏内部确实存在"**幸福度税率容忍度**"这一参数（否则 Central Bank 的加成无从谈起）。
> `[待验证]` 它的**基准值是多少、+1 相当于多少个百分点**，官方未公布。

#### A2.4 已知的"税收被高估/低估"两个坑

| 版本 | 事实 | 来源 |
|---|---|---|
| **1.2.5f1** | 修复了一个"从免税收入中扣除工资"的 bug，**修复后工业与办公税入下降** | https://cs2.paradoxwikis.com/Patch_1.2.X |
| 1.1.5f1 | "The production chain has been rebalanced **to bring tax income to a more reasonable level**"；同时**下调了所有产品的单位工作量**（→ 公司利润下降 → 可征税总额下降） | https://www.paradoxinteractive.com/games/cities-skylines-ii/news/dev-diary-economy-part-one |

> **含义**：1.2.5f1 之前的"工业/办公税收很高"的攻略**是被 bug 抬高的**，1.2.5f1 之后不再成立。

---

### A3. 什么最赚钱 —— 官方给的结构性答案（没有给数字）

#### A3.1 官方**明文**的三条密度—税收关系（本轮新发现，之前文件未收录）

Wiki 的 Zoning 页（**可信度 高**，正文标注 1.0）：
> "Lower density supports fewer people but **provide more taxes from each one** and are more likely to attract families and seniors.
> High density supports more people but **provide fewer taxes from each one** and are more likely to attract students and single adults."
> （来源：https://cs2.paradoxwikis.com/Zoning ）

> "**Low Rent Housing** — Large apartment buildings with small, affordable apartments. **The lower rent provides lower tax income as a result.**"
> （同上）

**这三条合起来给出官方口径的用地效率权衡表**：

| 分区 | 每格人数 | 人均税收 | 结论 |
|---|---|---|---|
| 低密度住宅 | 少 | **多** | **单位土地税收取决于"每格人数×人均"的乘积**，官方明说二者反向 |
| 中/高密度住宅 | 多 | 少 | 同上 |
| **低租金住宅（Low Rent）** | 多 | **明确更低** | 官方直接点名：低租金 = 低税收 |
| 商业 / 工业 / 办公 | — | 税基是**公司利润** | 与密度无关，与**效率×员工数×产品价值**有关 |

> **`[游戏机制]` 结论**：官方**没有**"哪类分区单位面积税收最高"的答案，而且**故意做了反向权衡**（低密度人均税多/人少，高密度人多/人均税少）。
> **因此"最高效率用地"不是单一答案，而是一个**可计算的乘积**：
> `单位土地住宅税收 ≈ (每格人口密度) × (该密度的应税工资总和) × (税率)`。
> 这条正是 §46 里"税收潜力代理"指标的设计依据。

#### A3.2 办公 vs 商业 vs 工业的官方差异

| 维度 | 办公 | 商业 | 工业 |
|---|---|---|---|
| 产出 | 无形商品 Software/Telecom/Financial/Media | Lodging/Meals/Entertainment/Recreation | 材料品（Metals/Food/Textiles…） |
| 学历需求 | 随等级上移**更偏高学历** | 随等级上移**更偏高学历** | **不论等级都倾向低学历** |
| 可被外部基础设施加成 | **Airport +3% 效率；Int'l Airport +10% Software 需求** | Int'l Airport +10% Attractiveness（拉游客=顾客） | — |
| 供应链 | 1.6.0f1 起**可从外部连接买办公商品**；1.6.2f1 修复"办公无法进口 Software" | 需本地或进口货源 | 需原料（本地开采或进口） |
| 对道路的负担 | 官方：**卡车少，但通勤高峰堵**，必须配公交 | 送货/进货卡车多 | 货车最多，重货运输成本高 |
| 噪声/污染 | — | — | 工业噪音 1.3.6f1 起量与半径双升 |

（来源：https://cs2.paradoxwikis.com/Zoning 、https://cs2.paradoxwikis.com/Citizens 、https://cs2.paradoxwikis.com/Transportation 、https://cs2.paradoxwikis.com/Patch_1.6.X 、https://cs2.paradoxwikis.com/Patch_1.3.X ；办公"卡车少、通勤堵"来自 https://kiragames.jp/?p=770 ，**可信度 低（第三方）**）

#### A3.3 单位面积/单位人口税收产出的**实证对比** —— 本次检索结论

> **明确结论：没有找到任何"官方或可复现"的单位土地税收产出实测表。**
> 社区层面只有两条**方向性**说法，**均不可作为机制引用**：

| 说法 | 来源 | 可信度 | 状态 |
|---|---|---|---|
| "不到 3 万人的**纯办公室城市**，一小时创收 46 万" | https://bbs.3dmgame.com/archiver/tid-6464219.html （3DM 论坛帖标题；正文**本次抓取失败**） | **低** | `[社区实证·未复核]`，仅标题可见，**不得引用具体数字** |
| "关闭全部外部高速 + 港口/机场集中客流 + 地铁/船/机票价统一 ₡50，交通收益可超过卖电；高峰一班地铁可载八九百人" | https://citiesskyline.com/citiesskylinesgameguide/cities-skylines2-traffic-profit-guide （2025-12-02） | **低** | `[社区实证]`；"一班八九百人"与官方"未公布载客量"冲突 → 见 C19 |

> ⚠️ **上表两条都是"低可信度、单点、不可复现"**。按 `00-sources.md` §五 规则，**给玩家建议时不得把它们当作"办公最赚"的证明**。

---

### A4. 财政收支结构

#### A4.1 支出侧

- 官方 Dev Diary 原文：**城市服务建造与维护 + 道路，是"几乎全部"的钱的去处**。
  > "City Service construction and upkeep, along with roads of course, are **where most (if not all) of your money goes**."
  （来源：https://www.paradoxinteractive.com/games/cities-skylines-ii/news/dev-diary-economy-part-one ，2024-06，**可信度 高**）
- 1.1.5f1 起：**服务维护费显著提高**（"significant increase in the upkeep costs"），且**进口服务开始收费、费用随城市人口缩放**，同时新增 **Import City Services** 政策开关（**默认关闭**）。
  （来源：同上；https://cs2.paradoxwikis.com/Patch_1.1.X ，**可信度 高**）
- 1.1.5f1 起新增**地块维护费**（初始 9 格免维护费）；选"解锁全部地块"会取消地块维护费但禁用成就。
  （来源：https://cs2.paradoxwikis.com/Patch_1.1.X ，**可信度 高**）
- **服务预算滑块（50%–150%）会影响服务建筑的工资支出**——1.6.2f1 修复了"Selected Info Panel 的 upkeep 段没有显示预算对工资的影响"。
  （来源：https://cs2.paradoxwikis.com/Patch_1.6.X ，**可信度 高**）
  → `[游戏机制]` **预算 = 成本杠杆 + 容量杠杆，且同时作用于工资**。

#### A4.2 收入侧

| 收入项 | 默认值 / 说明 | 来源 | 标记 |
|---|---|---|---|
| 四类分区税收 | 见 §A1–A2 | [W-Econ] | `[游戏机制]` |
| 电力服务费 | **0.2** | [W-Econ] | `[游戏机制]` |
| 自来水服务费 | **0.3** | [W-Econ] | `[游戏机制]` |
| 医疗费 | **₡100 / 月 / 住院市民** | [W-Econ] | `[游戏机制]` |
| 垃圾费 | **1.0** | [W-Econ] | `[游戏机制]` |
| 教育费 | 小学 ₡50、高中 ₡100、学院/大学 ₡200 / 月 / 人 | [W-Econ] | `[游戏机制]` |
| 停车费 | 路边 ₡1–50（默认 ₡10）；地块 ₡1–50（默认 ₡10） | [W-Roads]、[W-Pol] | `[游戏机制]` |
| 公交票价 | **每条客运线独立设置**，官方未给上下限，**可设为 0** | [W-Trans] | `[游戏机制]` |
| 服务出口 | 电 ₡2500/MW、水 ≈₡0.05/m³、污水 ≈₡0.1/m³ | [W-Econ] | `[游戏机制]` |
| 里程碑奖金 | 1.1.5f1 起大幅削减（M1 ₡600,000 → **₡25,000**；M20 ₡7,000,000 → **₡500,000**） | [W-Prog] | `[游戏机制]` |

#### A4.3 ⚠️ **重要更正：福利不由城市预算支出**

官方 Citizens 页原文：
> "People who do not work receive financial benefits that are **created by the game and are not deducted from any company, household, or municipal balance** (presumably paid by the larger government): children receive a `Family Allowance` of **₡400/month** for their household, seniors receive a `Pension` of **₡1200/month**, and other groups of people that are unemployed receive an `Unemployment Benefit` of **₡800/month** up until the `Unemployment Allowance Max Days` of **10**."
（来源：https://cs2.paradoxwikis.com/Citizens ，1.3.3f1，**可信度 高**）

> **必须写清的区分**：
> - **政府补贴（Government Subsidies）**：1.1.5f1 起**被彻底移除**（不再是城市收入项）。
> - **失业救济 / 养老金 / 家庭津贴**：**从来不是城市支出项**，是游戏凭空创造的市民收入。
> - 所以"削减福利来省钱"**在 CSL2 里根本不存在这个按钮**；能省的只有**服务预算、服务建筑开关、地块维护费**。
>
> **对算法的影响**：城市支出侧**只有服务与道路**，没有"福利支出"这一栏。任何"福利支出占预算 X%"的算法都是错的。

#### A4.4 水电费 → 效率/幸福度的**精确传导公式**（官方数值）

> 每**低于**100% 一个百分点：用电 **+0.2%**、公司效率 **+0.2%**、市民幸福度 **+0.05**
> 每**高于**100% 一个百分点：用电 **−0.4%**、公司效率 **−0.4%**、市民幸福度 **−0.1**

（来源：https://cs2.paradoxwikis.com/Services ，**单一来源**，本次仍**未找到第二来源 → 维持 `[待验证]`**）

> `[可用的机制结论]` 即使数值待验证，**方向与不对称性是官方明写的**：
> **降费（<100%）的收益斜率是涨费（>100%）惩罚斜率的一半** → 服务费的"最优"位置偏向"略低于 100%"而不是"越低越好"。
> 因为降费同时**增加用电**（成本）和**增加幸福度/效率**（收益）。

#### A4.5 贷款

| 项 | 值 | 来源 |
|---|---|---|
| 月供占贷款额 | **2.3% – 20%**（随额度上升） | [W-Econ] |
| 额度上限 | **₡100,000 – ₡26,100,000**（随里程碑） | [W-Econ] |
| City Hall | 1.0 时代：**−1% 利率** → **1.3.6f1 起：−5% 城市服务基础维护费 / −15% 城市服务进口成本** | [W-Econ] / [P-1.3.X] |
| Central Bank | 1.0 时代：**−2% 利率** → **1.3.6f1 起：−50% 贷款利息 / +1 幸福度税率容忍度** | [W-Econ] / [P-1.3.X] |

> **`[游戏机制]` 财政结论**：1.3.6f1 之后，City Hall 的价值从"减息"变成"**直接砍 5% 服务维护费 + 15% 进口成本**"——
> 对一个服务维护费占比极高的城市，这比减息值钱得多。**"服务维护费总额"因此成为一个必须先算出来的量**（→ §46 指标 T8）。

---

### A5. 城外通勤者不纳税（1.1.5f1 起）—— 最容易踩的坑

官方 Citizens 页原文：
> "City service workers pay tax, but **commuters (both people working outside the city and people living outside of the city) do not pay tax at all to either city**. Commuters (only people who live outside the city and work in the city) have a `Commuter Wage Multiplier` of **1.1**."
（来源：https://cs2.paradoxwikis.com/Citizens ，1.3.3f1，**可信度 高**）

1.1.5f1 补丁说明：
> "**Workers from Outside Connections no longer pay tax**"
（来源：https://cs2.paradoxwikis.com/Patch_1.1.X ，**可信度 高**）

> **`[游戏机制]` 完整链条**：
> **岗位 >> 本地劳动人口 → 城外通勤者填补 → 公司效率恢复（能招到人）→ 公司利润上升 → 商/工/办税收上升**
> **但：这些人的工资（×1.1）不会产生任何住宅税收，而且钱被带回城外消费。**
>
> **算法含义**：**"岗位数"绝不能当"税收基础"用。**
> 必须先把岗位拆成"本地人填的"与"城外通勤者填的"。
> `本地劳动力自给率 = min(1, 本地可就业人口 / 岗位数)`；**缺口部分对住宅税零贡献**。
> （→ §46 指标 T3）

> ⚠️ 还要注意 Citizens 页的另一句："**people working outside the city**"（住城内、城外上班的人）**也不缴税**。
> 即 1.6.0f1 之后，如果本地岗位不足，**居民出城上班 = 零税收**。

---

### A6. 产业链与货运对税收的影响（速查）

> ⚠️ **范围限制（本小节专用）**：**货运港口、货运铁路、货运航线不与客运数据一并分析。**
> 它们的 `Passenger` 恒为 0，**不进**线路效率 / 走廊重叠 / 车站腹地 / 站点覆盖率 / 线网规模；
> 本节的所有结论只在**工业部分**作辅助分析使用（判据与处方见 `SKILL.md` §2「货运与产业链」
> 与 `47` §2；报告位置在工业小节，排在 §8.2 真实税基之后）。

| 机制 | 内容 | 来源 |
|---|---|---|
| 本地销售 > 出口 | "selling to the local market is **always more profitable**"；持续出口会因"向越来越远的新买家发货"而**利润递减**（市场饱和模拟） | [W-Zone] |
| 专业化工区不堵路 | 专业化工区车辆**不走城市道路**，只在工区内部模拟路径上行驶 | [P-FH9] |
| 专业化工区不破产 | 只缩产裁员，不破产 | [P-FH9] |
| 仓库缓冲 | 1.3.6f1：仓库车辆 **3 → 10**；工业升级所需资源开始"提前配送"→**短期货车流量显著上升**（官方明确提示） | [P-1.3.X] |
| 进口触发阈值 | **仓储低于 50%** 且本地无法补货 → 开始从外部连接进口 | https://www.vgover.com/news/88101 （社区解析，**可信度 中低**）`[社区实证]` |
| 货运终端 = 配送中心 | 货运火车站/码头/机场**即使没开货运线路**也能当配送中心（公司可存取货） | [W-Trans] |
| 货运终端会制造卡车洪流 | 官方原文："it can generate **a lot of truck traffic**. Therefore it is **crucial to prioritize the road connections** to the terminal to avoid traffic jams." | [W-Trans] |
| 储位 | Cargo Train Terminal / Cargo Transfer Station / Cargo Harbor = **15.5 kt**；1.3.6f1 起码头/火车站的**仓库升级**储位下调为 **7500 t** | [W-Trans] / [P-1.3.X] |
| 货船 | **1000 吨** | [W-Trans] |
| 1.6.0f1 | **办公商品可从外部连接购买**（本地无源时的供应链兜底） | [P-1.6.X] |
| 1.6.2f1 | 修复"办公无法从外部连接进口 Software"；**公司按"城市最紧缺资源"优先租铺** | [P-1.6.X] |

---

## 2. B · 幸福度（第二靶心）

### B1. 幸福度的结构：`Happiness = Well-being + Health`

官方原文：
> "Citizen Happiness is the overall value that represents a citizen's satisfaction in their life. **It is the combination of their Well-being and Health** and affects the citizen's behavior and their ability to work."
（来源：https://cs2.paradoxwikis.com/Citizens ，**可信度 高**）

> ⭐⭐ **1.6.2f1（2026-09-15）起，幸福度的"财务基础"从「财富」改为「收入」**
> （官方原文：「Citizen happiness, shopping, and leisure choices now use **income rather than wealth**.
> Because citizens adjust their spending to match their financial situation, current wealth is a poor
> measure of how well off they are, making income a much better indicator.」）。
>
> **对诊断的影响（重要）**：
> * **幸福度与"收入"挂钩 ⇒ 就业质量（学历 → 工资档 ₡1500/1800/2100/2400/2700）比"存款"更能解释幸福度。**
> * 这与本文件 §C「住宅税基 = 工资」指向**同一条杠杆**：
>   **提高学历结构会同时抬升税收与幸福度** —— 这是少数"两个目标同向"的动作，应优先用。
> * 诊断"幸福度低"时**归因顺序**：先看**就业与工资结构** → 再看服务/污染/住房面积 → 最后才是其他。
> * 1.6.2f1 **同时加强**了垃圾对幸福度的影响（官方：「Garbage now has more effect on citizens'
>   happiness」；City Corner #11：「clean homes providing a greater happiness bonus」）
>   ⇒ **垃圾/清洁度**这类基础服务的权重上升。
>
> 来源：`101-2026-official-patch-log.md` §1.1 / §1.5（官方补丁说明，**可信度 最高**）

### B2. 官方幸福度因子表（**共 10 项**，本次逐条核对，与官方一致）

| # | 因子 | 类型 | 正面 | 负面 | 可规划控制？ |
|---|---|---|---|---|---|
| 1 | **教育服务** | Quality | 就近、易达、有余额 | 因交通难达、满员 | ✅ 完全可控 |
| 2 | **休闲时间（Leisure）** | Abundance | 就近快速到达公园/地标 | 公园少、拥挤、太远 | ✅ 完全可控 |
| 3 | **娱乐（Entertainment）** | Abundance | 易达商业（尤其酒吧/夜店） | 因交通不便、缺交通选择而难达 | ✅ 完全可控 |
| 4 | **医疗覆盖** | Reliability | 医疗建筑近或响应快 | 太远、过载、到达太慢 | ✅ 完全可控 |
| 5 | **邮政** | Reliability | 附近邮局/邮箱、分拣快 | 无邮局/邮箱；分拣需求超容量 | ✅ 完全可控 |
| 6 | **互联网** | Reliability | 网络容量高、覆盖好 | 容量或覆盖不足 | ✅ 完全可控 |
| 7 | **噪音污染** | Amount | 低 | 高（住宅区尤其不可接受） | ✅ 可控（选址/隧道/隔音墙） |
| 8 | **市民财富** | Amount | 收入/净资产高 | 低 | ⚠️ 间接（岗位与学历结构） |
| 9 | **住房面积** | Amount | 大（低密度） | 小（高密度） | ⚠️ **直接与"高密度=高税收效率"冲突** |
| 10 | **税率** | Amount | 低 | 高 | ✅ 完全可控 |

（来源：https://cs2.paradoxwikis.com/Citizens#Happiness_factors ，**可信度 高**；https://cs2.paradoxwikis.com/Happiness 是**重定向到 Citizens**）

> ⚠️ **官方没有给这 10 项的权重**。Happiness 视图里悬停家庭 Happiness 图标可看到**明细构成**，但**数值权重未公开** → `[待验证]`。
> **算法含义**：只能做**定性排序 + 代理指标**，不能算"幸福度分数预测"。

#### B2.1 ⚠️ 本轮发现的核心冲突：**因子 #9（大房子）与"用地效率最大化"直接对立**

> 官方：`Size of homes` 是幸福度因子，**低密度大房子 = 正面**。
> 同时官方：`Low density supports fewer people but provide more taxes from each one`。
>
> **两条合起来**：低密度住宅在**幸福度**和**人均税收**上双赢，唯一输的是**单位土地的人口容量**。
> **因此本轮的"最高效率用地"目标必须重新表述**为：
> **在给定土地预算下，最大化 `Σ(人口 × 人均应税工资 × 税率) × 留存率(幸福度)`**，
> 而不是"最大化每平方公里税收"。**这是一个含幸福度反馈的优化问题，不是一个密度最大化问题。**

### B3. Well-being 与 Health 的决定因素

**Well-being（精神状态与安全感）**：
- 基础：可靠供电、清洁水、足够污水处理（"so their toilets don't overflow"）
- 叠加：垃圾清运；避开空气/地面/噪音污染；**良好的城市服务覆盖（被动加成）**；低犯罪概率
- 便利设施：邮政、高速互联网、**与家庭需求匹配的住房面积**、**能买到商品**（消费）
- 官方对住房的细分：**家庭偏好低密度住宅与小公寓楼里的大房子；单身与学生在中高密度塔楼与低租金公寓里也能过得很好**
（来源：https://cs2.paradoxwikis.com/Citizens ，**可信度 高**）

**Health（健康）**：
- 正面：医疗可达性（**就近被动加成** + 实际治疗）
- 负面：空气污染、地面污染（**污染越强影响越严重**）、污水倒灌、**垃圾堆积**（同时也影响 Well-being）
- 机制：Health 高 → 生病概率低；一旦生病 **Health 大幅下降**（1.3.6f1 起患病直接削 **50%** 健康值）
（来源：https://cs2.paradoxwikis.com/Citizens ；https://cs2.paradoxwikis.com/Patch_1.3.X ，**可信度 高**）

**低值造成的可确证后果**：
| 状态 | 触发 | 后果（官方原文要点） |
|---|---|---|
| **Unwell** | Well-being 低 | Happiness 下降、**工作贡献下降**、**有成为罪犯的风险** |
| **Weak** | Health 低 | Happiness 下降、工作贡献下降、**高概率生病**、生病后死亡风险高 |
| **Homeless** | 付不起房租且无钱搬走 | 住在城市公园里 |
| **Sick / Injured** | 疾病 / 事故火灾 | **不能工作**（公司效率直接损失） |
（来源：https://cs2.paradoxwikis.com/Citizens#Conditions ，**可信度 高**）

### B4. 幸福度过低的后果与**触发阈值**

**可确证的机制（官方原文）**：
- 1.1.5f1："**Low happiness affects the chance a household will move out of the city**"
  （来源：https://cs2.paradoxwikis.com/Patch_1.1.X ，**可信度 高**）
- Well-being 低 → 工作贡献下降 → 公司效率下降 → 利润下降 → 商/工/办税收下降（`[游戏机制]` 链条）

**`[待验证]`**：**"多低算低"没有官方数值**。Happiness 视图只显示因子明细与着色，不显示阈值。
→ 算法上**不能设"幸福度 < X 就报警"的绝对阈值**；只能用**相对口径**（与本市历史值/与区之间比较）或**因子级缺口**（覆盖率）。

### B5. 服务覆盖半径的**单位问题** —— 本次的进展与结论

- **仍然没有官方单位说明** → `[待验证]`（与上一轮一致，C10 保持）。
- **本次新增的可引用观察**：在**同一张** Service_buildings 自动生成表（标注 1.6）里，
  - **电信类建筑明确写单位**：`Radio Mast` = **1 km**、`Server Farm` = **2 km**、`Telecom Tower` = **5 km**；
  - 而医疗/教育/警察/消防/etc. 写的是**裸数值**：`Small Medical Clinic` = **2500**、`Hospital` = **7500**、`Police Headquarters` = **10000**。
  （来源：https://cs2.paradoxwikis.com/Service_buildings ，**可信度 高（数值本身）**）
- **推论（本文标注 `[推导]`）**：同一张表里"有单位的行"和"没单位的行"**并存**，说明官方在表格里并非统一换算成米；
  裸数值可能是**格（8 m）**、**内部单位**，或**另一种量纲**。
  **绝对禁止断言"Service range 的单位是米"。** 只能做**相对比较**（小诊所 2500 < 医院 7500）。
- **可用的替代方案（算法层面）**：用 **POI 坐标 + 自己圈定的现实标准半径（400/600/800/1000 m）** 做覆盖分析，
  并在输出里明确写"这是现实标准半径，不是游戏的 Service range"。

---

## 3. C · 土地价值与用地效率

### C1. 地价（Land Value）的形成

#### C1.1 官方来源清单（1.1.0f1 重构后，**可信度 高**）

> 1.1.0f1 的地价系统改动，官方逐条列出：
> - **Healthcare、Education、Police、Telecom 的服务覆盖**影响地价
> - **商业服务的可达性**影响地价
> - **公共交通的站点与车站**影响地价（→ **TOD 在 CSL2 里有机制支撑**）
> - **噪音、水、空气、地面污染**影响地价（负向）
> - **岸线（Shorelines）**影响地价
> - **地价加成系数有上限**（"Added a max limit to Land Value bonus factor"）
> - 新增 **"Land Value Source" 信息模式**（显示地价来源）
> - Land Value 视图光标可显示**该处地价的具体金额**
（来源：https://cs2.paradoxwikis.com/Patch_1.1.X ，1.1.0f1 段，**可信度 高**）

#### C1.2 地价的闭环（Zoning 页，**可信度 高**）

- 地价**沿道路扩散**到建筑周边，缓慢抬升整个区域。
- **单纯把服务建筑堆进社区不会自动抬地价**——只有"居民与公司的需求真的被满足"才会。
- 城市服务**间接**影响地价（"City services **indirectly** affect Land Value as they answer the needs of citizens and companies"）。
- **反向**：付不起高租金 → 租金下降 → 地价下降 → 居民搬走 → 建筑失修 → 废弃 → **地价进一步下降**（正反馈下行）。
- **控制地价的手段（官方明写）**：调住宅税率（鼓励/劝退迁入）；**多划高需求类型的分区（用供给平抑地价）**；**主动限制服务与休闲设施的数量**（"Citizens can tolerate some shortcomings… and still live relatively happy lives"）。

#### C1.3 租金公式（**官方 Dev Diary 原文**，可信度 高）

```
Rent = ( LandValue + ( ZoneType × Building Level ) ) × LotSize × SpaceMultiplier
```
（来源：https://www.paradoxinteractive.com/games/cities-skylines-ii/news/dev-diary-economy-part-two ，Colossal Order，Economy 2.0 Part 2）

配套机制（同一篇官方 Dev Diary 原文）：
- **虚拟房东被移除** → 建筑维护费（upkeep）**由所有租户平摊**。
- **"High Rent" 通知改为基于家庭收入判定**：
  > "even if they currently don't have enough money in their balance to pay rent, they won't complain and will instead spend less money on resource consumption. **Only when their income is too low** to be able to pay rent will they complain about 'High Rent' and look for cheaper housing or move out of the city."
- `[待验证]`：公式里的 **`ZoneType` 系数、`SpaceMultiplier` 的取值**官方**没有给**。
  1.1.5f1 只明确了"工业制造用地的 `space multiplier` 从 1 提到 5"（来源：Patch_1.1.X）。
  → **1.1.5f1 起：工业用地同一地块容纳的岗位数约 ×5。**

#### C1.4 密度对地价的非对称影响（重要规划结论，**可信度 高**）

> "Low density housing areas **can quickly become expensive** to live in as the Land Value increases. … since low density housing has only one household per building, **the increased rent falls on the single household entirely.** Thus, lower-income families tend to move out… **Medium and high density housing areas are less affected** as the living costs are divided among many dozen households."
（来源：https://cs2.paradoxwikis.com/Zoning ）

> **算法含义**：**低密度住宅是"地价风险敞口"最大的分区类型**。
> 高税率 + 高地价 + 低密度 = **最快触发搬离的组合**。这构成 §46 的一个风险指标。

### C2. 建筑升级（Level up）的条件 —— 直接决定税收产出

#### C2.1 1.1.5f1 起：**取决于租户能否付满 upkeep**（官方 Dev Diary 原文）

> "Besides rent, households and companies need to pay for the building's **upkeep**, which in turn affects the **level of the building**.
> **When they pay the full upkeep fee, the building condition increases by a constant amount until the building levels up** and the tenants start paying towards the next level.
> Similarly, **if they cannot pay it, the building condition decreases by the same amount** until it's in such poor condition it **collapses**."
（来源：https://www.paradoxinteractive.com/games/cities-skylines-ii/news/dev-diary-economy-part-two ，**可信度 高**）

Wiki 版（Zoning 页）表述一致：
> "**If the rent is higher than the upkeep cost of the building**, the residents pool their leftover funds into improving the building which eventually leads to the building **leveling up**."
（来源：https://cs2.paradoxwikis.com/Zoning ，**可信度 高**）

#### C2.2 1.4.2f1 起：**还需要资源配送**

> 建筑升级需要**资源配送**才能推进，配送由**工业公司、资源仓库、外部连接**承担；信息视图新增"等待资源的建筑"图标。
（来源：https://cs2.paradoxwikis.com/Patch_1.4.X ，**可信度 高**）
> 1.5.7f1 修复"资源配送在某些帧被跳过后建筑等级卡住不动"。（来源：Patch_1.5.X）
> 1.5.7f1 新增 **Historic Building**：可锁定某建筑不再升级、也不会废弃。（同上）

#### C2.3 完整的升级判定链（本文整理，**`[机制综合]`**）

```
公司/家庭现金流  =  收入（工资 / 利润）
                 − 租金 Rent = (LandValue + ZoneType×Level) × LotSize × SpaceMultiplier
                 − 建筑 upkeep
                 − 水费 + 电费（服务费滑块决定）
                 − 垃圾费
        ↓
   现金流转正 → building condition 按固定步长上升 → 升级 → upkeep 上升（进入下一级循环）
   现金流转负 → condition 同幅下降 → 最终倒塌/废弃
        ↓
   （1.4.2f1+）且必须：有工业公司/仓库/外部连接把升级所需资源送到
```

> **`[游戏机制]` 核心结论（对税收最重要的一条）**：
> **税收不是"税率 × 建筑"的静态函数。**
> 税率↑ → 租户/公司现金流↓ → **upkeep 付不满** → **建筑等级↓** → 长期税基↓（甚至建筑废弃）。
> 所以"把税率拉到 30%"在**短期内**收得多，在**中期**会把税基自己吃掉。
> **这正是"没有官方甜蜜点、但机制上必然存在最优税率"的完整解释。**

### C3. 单位土地产出的实证对比 —— **明确结论：没有**

> **本次联网检索未找到任何"官方或可复现"的"低/中/高密度住宅、各类商业办公的每格税收/岗位产出"实测表。**
> 社区层面存在方向性说法（§A3.3），但**均无数据、不可复现**。
> **按 `00-sources.md` §五 规则：给玩家建议时必须说明"这个数据官方没有、社区也没有可靠实测"，不得给出精确数字。**

**可以合法使用的替代口径（有官方依据的**结构性**结论）**：
1. 人均税收：**低密度 > 中/高密度**；低租金住宅 **最低**（官方明文）
2. 每格人数：**高密度 > 低密度**（显然）
3. 商/工/办：税基 = 利润 → **受效率链支配，与密度无直接关系**（官方明文）
4. 工业 1.1.5f1 起 space multiplier = 5 → **同一地块工业岗位数约 ×5**（官方明文）
5. 办公可被 Airport（+3% 效率）/ Int'l Airport（+10% Software 需求）**直接用基础设施加成**（官方明文）

### C4. 混合用途与贴邻

#### C4.1 混合用途住宅（Mixed Housing，里程碑 5）

- 官方定义：**"Apartment buildings with commercial space on the bottom and apartments on top."**
（来源：https://cs2.paradoxwikis.com/Zoning ，**可信度 高**）
- **`[游戏机制]` 算法含义**：这类建筑同时产生 `Resident`、`Employee`（商业岗位）与商业销售。
  **Carto 的 `Zoning` 字段会把它记为 `Residential, Commercial`** —— 因此
  **统计住宅面积/人口时如果只用 `Zoning == 'Residential'`，会漏掉混合用途**。
  `70-carto-data-schema.md` 已把 `Residential, Commercial` 单列，但 `city_report.py` 的分区结构表**没有把它并入住宅口径**，这是一个需要修的口径问题（→ §46 T9）。

#### C4.2 分区贴邻：官方**没有**权重矩阵

- 官方**没有给出"分区贴邻惩罚/加成"的数值表**。可确证的是**软性相互依赖**：
  - 商业"靠近住宅区能获得顾客"
  - 工业"优先在本地销售更赚钱"
  - 办公"更重要的是靠近潜在劳动力居住区"
- **可确证的硬性相邻惩罚只有三条通道**：**污染（地面/空气/噪音）+ 大型道路降地价 + 租金**。
（来源：https://cs2.paradoxwikis.com/Zoning 、https://cs2.paradoxwikis.com/Economy 、https://cs2.paradoxwikis.com/Roads ）

#### C4.3 工业污染的影响半径

- **1.3.6f1 起**：分区工业与专业化工区的**噪音量与扩散半径双双上调**，且**住宅适宜度开始考虑空气与噪音污染**，市民对噪音的惩罚也略微加大。官方原话要求"新城市在工业与住宅之间**留出更大空间**，现有城市可能需要重新分区"。
（来源：https://cs2.paradoxwikis.com/Patch_1.3.X ，**可信度 高**）
- **具体半径数值官方没有给** → `[待验证]`。
- **可用的精确规则（官方明文，非常适合写进算法）**：
  - **地下道路（隧道）的噪音被完全抑制**；**高架道路的噪音被放大**
  - **树木只有很弱的对数级降噪**；高速公路需要**隔音墙**
  - **Speed Bumps 政策"大幅降噪音"**
  （来源：https://cs2.paradoxwikis.com/Pollution 、https://cs2.paradoxwikis.com/Policies ）
- **1.1.8f1 修复**："道路隧道生成噪音和空气污染"（此前隧道在地表也会产生污染）→ 修复后隧道确实是**干净的穿越方式**。
（来源：https://cs2.paradoxwikis.com/Patch_1.1.X ，**可信度 高**）
- 官方道路表给出**每条道路的 `Noise pollution factor` 与 `Air pollution factor`**（如 Two-Lane Road 1×/1×；**Gravel Road 2×/1×**；**Pedestrian Street 2×/1×**）。
（来源：https://cs2.paradoxwikis.com/Roads ，自动生成表标注 **1.6**，**可信度 高**）
  > 注意：**碎石路与步行街的噪音系数（2×）比双车道柏油路（1×）更高**——这与直觉相反，但对算法是可直接使用的官方权重。

---

## 4. D · 交通效率（税收的乘数）

### D1. 通勤时间对地价 / 幸福度 / 公司效率的影响

#### D1.1 三条已确证的通道

| 通道 | 机制 | 来源 | 标记 |
|---|---|---|---|
| **地价** | 1.1.0f1 起：**公交站点与车站直接影响地价**（TOD 有机制支撑） | [P-1.1.X] | `[游戏机制]` |
| **地价** | 1.1.0f1 起：**商业服务的可达性影响地价** | [P-1.1.X] | `[游戏机制]` |
| **幸福度** | 幸福度因子表里，"教育服务""娱乐""医疗覆盖"的**负面描述全部包含"因交通难达/缺交通选择"** → 交通是这些因子的**可达性乘数** | [W-Cit] | `[游戏机制]` |
| **公司效率** | 效率因子表里**没有"通勤时间"这一项**；但有"**员工数量不足**"与"**员工幸福度**"。员工能否接受岗位受寻路成本影响 → **间接** | [W-Econ]、[W-Cit] | `[游戏机制]`（间接） |

#### D1.2 1.6.0f1 的寻路距离上限（官方原文，**可信度 高**）

> "Fixed citizens taking absurdly long trips across the entire map. **Pathfinding limits are now tailored per trip type: work, school, shopping, and leisure each use a sensible range** rather than a shared near-unlimited cap.
> Citizens who can't find a viable route now handle it gracefully: **move-outs teleport off-map, workers drop their job, and leisure-seekers idle at home before retrying.**"
> 已知遗留问题：**学生仍可能走得过远**。
（来源：https://cs2.paradoxwikis.com/Patch_1.6.X ，1.6.0f1，**可信度 高**）

> **`[游戏机制]` 结论**：**"超长通勤"从"能忍"变成"致命"**——直接从"辞职/搬离"这一端触发。
> **`[待验证]`**：**四种出行的具体距离上限数值，官方没有公布**（原文只说 "a sensible range"）。

**1.6.0f1 另外两条与商业/交通直接相关的修复（**可信度 高**）**：
- "Fixed a bug where citizens would **always travel to the shop with the most stock, completely ignoring distance**." → 商业选址逻辑改为**距离参与决策**。
- "Fixed legal U-turn costs… and **lowered illegal U-turn costs** to match intended limits." → 掉头成本改变，路口微观行为变化。

#### D1.3 寻路成本模型（四要素，按年龄变化）—— 官方

| 年龄 | 主导因子 |
|---|---|
| Teens 青少年 | **Money（最便宜路线）** |
| Adults 成人 | **Time（最快路线）** |
| Seniors 长者 | **Comfort（最舒适路线）** |
（来源：https://cs2.paradoxwikis.com/Citizens 、https://cs2.paradoxwikis.com/Traffic ，**可信度 高**）

> 票价（Money）主要影响青少年与低收入群体；速度（Time）主要影响成人通勤；舒适度（Comfort，含车站 Comfort 等级与换乘体验）主要影响长者。

### D2. 道路通行能力 —— **官方没有 pcu/h**

#### D2.1 官方只给了这些（**可信度 高**，数值表标注 1.6）

| 官方给出的字段 | 说明 |
|---|---|
| **车道数（Car lanes）** | 1–6（道路表逐条给出） |
| **限速（Speed limit）** | 双口径：EU 主题显示值 + 内部值（如内部 80.0 → EU 40 km/h / NA 30 km/h） |
| **Noise pollution factor** | 1× / 2×（**碎石路与步行街是 2×**，比双车道柏油路更高） |
| **Air pollution factor** | 1× |
| **造价 / 维护费（平地 / 高架 / 隧道三套）** | 如 Two-Lane Road：平地 ₡4.0K/km 建 + ₡487/km 维护；**隧道 ₡33.5K/km 建 + ₡2.96K/km 维护** |
| 是否可分区 | "some of the higher capacity roads such as highways **do not even allow zoning** next to them" |
| 是否自带水电 | 除高速外全部 **40 MW 低压输电**；非桥梁还带水管与污水管 |
| 官方原话 | "**The larger the road, the higher the speed limit and traffic capacity.**" —— **没有数字** |

（来源：https://cs2.paradoxwikis.com/Roads ，**可信度 高**）

> **`[待验证]`（维持上一轮结论）**：**各类道路的 pcu/h 通行能力官方没有给**。任何"四车道 = X 辆/小时"的数字都是社区估计。

#### D2.2 官方明确的定性规则（可写进算法）

| 规则 | 官方原文要点 | 来源 |
|---|---|---|
| 单行道 | "**Service vehicles cannot go against the flow of traffic**" → 单行道可能让消防车走远路；**商业/工业建筑如果收货不够频繁会"停止有效运营"** | [W-Roads] |
| 高架 vs 隧道 | **隧道噪音被完全抑制；高架噪音被放大** | [W-Pollution] |
| 大型道路 | **降低周边地价 + 增加噪音污染** | [W-Roads] |
| 道路状况 | 随时间下降 → **车速下降、事故概率上升**；需要 Road Maintenance Depot | [W-Serv] |
| 环岛 | 4 个尺寸：Small ₡200 / Medium ₡500 / Large ₡1000 / Very Large ₡1500（后三种需 Roundabouts 发展点） | [W-Roads] |
| 路口间距 | **官方没有任何规定** | `[待验证]` |

### D3. 公共交通的财政性

#### D3.1 官方给的三项可调参数与两项反馈

- **可调**：票价（每条客运线独立，**可为 0**）、**车辆数**、**运营时段（day / night / both）**；货运线可调车辆数与运营时段。
- **反馈**：**线路使用率百分比** —— 官方原话："If a line becomes extremely popular i.e. its **usage percentage close to 100%**, increasing the number of vehicles can alleviate the pressure and **shorten passenger wait times** at stops and stations **which in turn affect their pathfinding calculations as well**!"
（来源：https://cs2.paradoxwikis.com/Transportation ，**可信度 高**）

#### D3.2 `[待验证]` —— 官方**没有**给的东西

- **各方式的单车载客量**：官方 Wiki 的 Transportation 与 Service buildings 页**均未给出载客量字段**。唯一有来源的是**渡轮 100 人**与**货船 1000 吨**。
- **票价收入公式**、**每乘客补贴**、**线路盈亏**：官方**完全没有给**。
  → 因此"哪种交通方式每乘客补贴最低"**在官方数据下无法回答**。
- **线路自动发车间隔算法**：不存在。官方只提供"车辆数"。

#### D3.3 depot / yard 的维护费 —— ⚠️ **本次发现同一 Wiki 两处数据冲突**

> ⚠️ **口径提醒（本表专用）**：**Subway Yard / Terminal Subway Yard（地铁总站）等是 depot（车辆段），不是车站** ——
> 它们只解释"为什么加车加不上去"和维护费，**不得用于站点计数、站距、腹地、覆盖率**。
> **货运段（Cargo Train Terminal / Cargo Harbor）属工业部分的辅助分析**，不并入客运口径。

| 建筑 | Service_buildings 表（标注 1.6） | Transportation 页（正文标 1.0） |
|---|---|---|
| Bus Depot | **₡31,000/月** | **₡23,250/月** |
| Subway Yard | **₡24,000/月** | **₡18,000/月** |
| Rail Yard | **₡15,000/月** | **₡11,250/月**（客运段）/ **₡15,000/月**（货运段） |
| Tram Depot | ₡8,625/月 | ₡8,625/月 ✅ 一致 |
| Small Train Station | ₡7,500/月 | **₡5,625/月** |
| Overground Subway Station | ₡10,000/月 | **₡7,500/月** |
| Underground Subway Station | ₡20,000/月 | **₡15,000/月** |
| Harbor（客运码头） | ₡30,000/月 | **₡22,500/月** |
| Airport | ₡50,000/月 | **₡37,500/月** |
| International Airport | ₡200,000/月 | **₡150,000/月** |

> **规律观察（`[推导]`）**：Transportation 页的数值**恰好是 Service_buildings 表的 0.75 倍**（31,000×0.75=23,250；24,000×0.75=18,000；15,000×0.75=11,250；7,500×0.75=5,625；20,000×0.75=15,000；30,000×0.75=22,500；50,000×0.75=37,500；200,000×0.75=150,000）。
> **这是一个系统性比例，不是随机差异** → 极可能是 **Easy 难度模式**（1.3.3f1 起 Easy 模式调整了消耗与维护）或某次平衡改动的"打折"。
> **`[待验证]`**：哪一组对应当前默认难度。**建议：引用 depot 维护费时必须带难度前提，或直接让玩家在游戏内建筑面板读一次。**
> 已登记为冲突 **C17**。
> （来源：https://cs2.paradoxwikis.com/Service_buildings ；https://cs2.paradoxwikis.com/Transportation ）

#### D3.4 线路效率的**非官方**实证

- 本次**未找到**任何"加多少车能提多少客流"的定量实证。
- 唯一相关的社区说法（**可信度 低**）：关闭全部外部高速 + 港口/机场集中客流 + 地铁/船/机票价统一 ₡50，交通收入可超过卖电。
（来源：https://citiesskyline.com/citiesskylinesgameguide/cities-skylines2-traffic-profit-guide ）
  > ⚠️ 这条说法里的"**一班地铁车厢能挤满八九百人**"与官方"未公布载客量"直接冲突，且数字大得不合常理 → 登记为 **C19**，**不得引用**。

### D4. 货运效率

见 §A6 的速查表。补充三条对本轮目标最直接的：

1. **货运终端无论是否开设货运线路都可作为配送中心**——这是**最便宜的"提升工业/商业效率"手段**，因为它不要求开线。
   （来源：https://cs2.paradoxwikis.com/Transportation ，**可信度 高**）
2. **本地货源替代进口**：官方明确"本地销售永远更赚钱"，且**进口会在城市道路上产生额外卡车流量**（"Importing goods does not affect the revenue of these industries, but does affect gameplay by requiring a well-developed roadway grid"）。
   （来源：https://cs2.paradoxwikis.com/Zoning ，**可信度 高**）
3. **1.6.0f1 起办公商品也能从外部连接购买**，1.6.2f1 修复了办公 Software 进口 → **办公区不再被本地供应链卡死**。
   （来源：https://cs2.paradoxwikis.com/Patch_1.6.X ，**可信度 高**）

---

## 5. 本轮需要登记的冲突 / 待验证（已同步进 `00-sources.md`）

| 编号 | 内容 | 状态 |
|---|---|---|
| **C16** | **税率"甜蜜点"** —— 官方无任何数值；本次仍未找到可复现的社区实测 | `[待验证]`（维持） |
| **C17** | **depot/车站维护费**：Service_buildings 表 vs Transportation 页 = **系统性 0.75 倍差** | **新冲突** |
| **C18** | **办公税率 30% ≈ 强制清退**（官方 workaround）vs "税率对需求影响"的强度 | **新发现，可作经验边界** |
| **C19** | **"一班地铁载八九百人"**（社区）vs **官方未公布载客量** | **新冲突** |
| **C20** | **Service range 单位**：同表内"km 行"与"裸数值行"并存 | **新证据，仍未定论** |
| **C21** | **福利是否算城市支出**：官方明文"不由市政预算扣除" | **已澄清（更正类）** |

---

## 6. 引用本文件时的硬性规则

1. **涉及税收/租金/地价/升级/需求/补贴——必须先确认玩家版本 ≥ 1.1.5f1**，否则整段不适用。
2. **涉及工业噪音半径/仓库车辆数/专业化加成/City Hall 与 Central Bank 加成——必须 ≥ 1.3.6f1。**
3. **涉及垃圾对幸福度的影响权重——必须 ≥ 1.6.2f1**（该版加大了影响）。
4. **涉及"市民购物/休闲用 income 而非 wealth"——必须 ≥ 1.6.2f1。**
5. **涉及"市民不再只看库存最多的店"——必须 ≥ 1.6.0f1。**
6. **涉及办公商品进口——必须 ≥ 1.6.0f1（购买）/ 1.6.2f1（Software）。**
7. **任何"每格税收""单位面积税收"的数字——一律不得给出**，除非是玩家自己在游戏内实测并说明了测量口径。
8. **"Service range 是米"这句话禁止出现。**
9. **depot 维护费引用时必须带难度前提**（见 C17）。
