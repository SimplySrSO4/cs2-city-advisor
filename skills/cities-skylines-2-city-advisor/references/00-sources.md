# 00 · 来源清单与冲突登记（Cities: Skylines II）

> 检索执行日期：**2026-10-13**（第三轮；全部为实际联网检索，未使用记忆作答）
> 游戏最新版本：**1.6.2f1「Autumn Breeze」2026-09-15**
> 版本分期锚点：1.0.9f1（2023-10-24 首发）→ **1.1.5f1「Economy 2.0」（2024-06-24）** → 1.1.6f1/1.2.0f1（Detailer's Patch #1/#2）→ 1.2.5f1（十周年）→ 1.3.6f1（Bridges & Ports）→ 1.4.2f1（Bike Patch）→ **1.5.2f1（Asset Mods Patch，资产编辑器）** → 1.6.0f1/1.6.2f1
> 本文件用途：任何一条数值结论都可以回溯到具体 URL + 适用版本。**引用时务必带上版本号**，因为 1.1.5f1 与 1.3.6f1 是两次大规模重平衡。
>
> **📌 本文件已包含三轮检索的成果**：
> - **第一轮**（通用机制）：S1–S44、C1–C15。
> - **第二轮（2026-10-12，「税收 × 幸福度 × 土地/交通效率」专题）**：新增 **S36–S38**（官方 Dev Diary ×2 + 补丁归档）、**S50–S54**（官方 Wiki 增量核查）、**S60–S66**（社区与第三方）、**§2c**（尝试但未采信的来源与教训）、**C16–C21**（新冲突）、**§4c R1–R9**（对已有结论的更正/补充）。正文见 **`45-economy-and-happiness.md`**；算法清单见 **`46-algorithm-roadmap.md`**。
> - **第三轮（2026-10-13，「实操攻略与量化经验」专题）**：新增 **S70–S73**（官方 Wiki **原生 wikitext `?action=raw`** —— 本轮最大的方法论突破）、**S80–S86**（社区/第三方实操来源）、**§2d**（尝试但未采信的来源与教训）、**C22–C27**（新冲突）、**§4c R10–R15**（更正/补充）、**§五 规则 15–22**。正文见 **`47-operations-playbook.md`**（实操结论）与 **`48-tuned-thresholds.md`**（阈值校准表）。
> - 🔑 **最重要的方法论收获**：**遇到官方 Wiki 页面正文被导航框架截断时，改用 `https://cs2.paradoxwikis.com/index.php?title=<Page>&action=raw`**，正文会完整返回（必要时用 `&section=N` 定位）。本轮靠这一招一次拿到 `Services` / `Zoning` / `Transportation` / `Policies` / `Roads` / `Service_buildings` 六个页面的完整原文，**并据此结案了 C17 与 C20**。
> - ⛔ **已确认的死路（不要再投预算）**：`S63`（ps1ke 的 MkDocs 镜像，**4 次尝试正文全被 60 KB 导航树吃光** —— 但 `?action=raw` 已能替代其价值）、`S65`（Steam 社区讨论区，**第 3 轮确认整体不可达**）、**Reddit**（域名解析到非公网 IP）、**`chillplacegaming.com` / `modscities2.com`**（403 / Cloudflare 拦截）。详见 §2d。
> - **第四轮（2026-10-13，「官方数值表系统榨取」专题）**：新增 **S90–S99c**（官方 Wiki 数值表 8 页 + 全文检索 + 原始字段转储页）、**§6b**（新增死路：`Budget` 页 404、NGA 403、游研社正文为空、官方 feature 页 404）、**C28–C32**（新冲突）、**§6d 规则 23–30**。正文产出见 **`41-official-data-tables.md`**（新）。本轮把 `Service_buildings` / `Services` / `Economy` / `Progression` / `Roads` / `Policies` / `Citizens` / `Zoning` 八页的**全部数值表**逐列抓出，并首次拿到**噪声 / 耗电 / 耗水 / 垃圾 / 岗位 / 学历要求 / 班次**七列官方数据，以及**电水费率弹性**、**里程碑奖金表**、**服务费默认值与服务贸易价目**、**通行能力字段的第四次缺席确认**。


---

## 一、官方来源（一手）

### 1. 官方 Wiki（wiki.paradoxgame.com 的 Cities: Skylines II 分站）

| # | 标题 | URL | 页面版本标注 / 最后编辑 | 支撑了哪些结论 |
|---|---|---|---|---|
| S1 | Cities Skylines II Wiki（主页） | https://cs2.paradoxwikis.com/Cities_Skylines_II_Wiki | 最后编辑 2026-06-11 | 版本时间线、开发主体由 Colossal Order 转为 Iceflake Studios、官方 Dev Diary 索引 |
| S2 | Patches（版本总表） | https://cs2.paradoxwikis.com/Patches | 更新至 2026-09-15 | 全部版本号 + 日期 + 别称（Economy 2.0 / Detailer's Patch / Anniversary / Bike Patch 等） |
| S3 | Patch 1.0.X | https://cs2.paradoxwikis.com/Patch_1.0.X | 1.0.9f1~1.0.19f1 | 首发状态基线（作为"旧机制"对照） |
| S4 | Patch 1.1.X | https://cs2.paradoxwikis.com/Patch_1.1.X | 1.1.0f1~1.1.12f1 | **Economy 2.0 完整改动清单**、地价系统重构（1.1.0f1）、腐败/无家可归修复、交通路径偏好（1.1.10f1 直线偏好 +0） |
| S5 | Patch 1.2.X | https://cs2.paradoxwikis.com/Patch_1.2.X | 1.2.0f1~1.2.5f1 | Line Tool / Traffic Routes / Service Vehicle Parking 新功能、公共交通按距离上下车优化、公园政策与税率对公司的真实影响 |
| S6 | Patch 1.3.X | https://cs2.paradoxwikis.com/Patch_1.3.X | 1.3.3f1~1.3.6f1 | **工业噪音污染范围扩大**、货车流量上升、City Hall/Central Bank 加成数值、仓库车辆数 3→10、城市专业化加成上限降至 10%、车辆多选生成 |
| S7 | Patch 1.4.X | https://cs2.paradoxwikis.com/Patch_1.4.X | 1.4.2f1（Bike Patch） | **自行车/电动滑板车成为第五种通勤方式**、自行车道与停车设施、升级材料配送改为多目标配送 |
| S8 | Patch 1.5.X | https://cs2.paradoxwikis.com/Patch_1.5.X | 1.5.2f1~1.5.10f1 | 自行车出行削减 80%、Zone toggling、Historic Building、教育系统重平衡、**公交/火车/地铁/电车"永久上下客卡死"修复（1.5.7f1）** |
| S9 | Patch 1.6.X | https://cs2.paradoxwikis.com/Patch_1.6.X | 1.6.0f1、1.6.2f1 | **寻路距离上限按出行目的分类**、合法/非法掉头成本修正（1.6.0f1）、垃圾车逻辑、住宅需求按城市规模修正（1.6.2f1） |
| S10 | Zoning | https://cs2.paradoxwikis.com/Zoning | `{{Version\|1.0}}`，最后编辑 2026-02-10 | 分区类型/密度/地块尺寸表、建筑等级 1–5 的效果、需求成因、**Zone suitability**、地价闭环机制 |
| S11 | Roads | https://cs2.paradoxwikis.com/Roads | 正文 1.0，**自动生成表格标注 1.6** | 全道路类型表（车道/限速/造价/维护/噪音系数）、环岛 4 尺寸造价、**路边停车与停车建筑表（含 comfort / garageMarkerCapacity / 默认停车费 10）**、道路维护站、道路附属物（信号灯/禁转/人行横道/宽人行道/隔音墙） |
| S12 | Traffic | https://cs2.paradoxwikis.com/Traffic | `pre-release` / 1.0，最后编辑 2024-12-15 | **寻路成本四要素 Time / Comfort / Money / Behavior**、服务车辆调度算法、事故机制、城际过境交通 |
| S13 | Transportation | https://cs2.paradoxwikis.com/Transportation | `{{Version\|1.0}}` | 各交通方式定位、depot→站→线的工作流、**Line 面板可调票价/车辆数/运营时段**、使用率百分比、货运终端储运 |
| S14 | Services | https://cs2.paradoxwikis.com/Services | `{{Version\|1.0}}` | **预算 50%–150% 对应效率 25%–125%**、服务费完整清单、服务进出口价格、十二类服务机制 |
| S15 | Service buildings | https://cs2.paradoxwikis.com/Service_buildings | 页头 1.5，**全部自动生成表标注 1.6** | **所有服务建筑的 Service range / Service capacity / Service magnitude**、造价、维护费、车辆数、岗位、学历要求、污染与水电消耗 |
| S16 | Citizens | https://cs2.paradoxwikis.com/Citizens | 1.0 正文 + **1.3.3f1 工资数值** | 五级学历、四段年龄与各自寻路偏好、幸福度因子表、就业与工资、无家可归/犯罪/游客 |
| S17 | Economy | https://cs2.paradoxwikis.com/Economy | `{{Version\|1.0}}` | 税率区间 −10%~30%、服务费默认值、服务贸易价目、贷款与利率减免、公司效率因子、完整产业链表 |
| S18 | Progression | https://cs2.paradoxwikis.com/Progression | `{{Version\|1.1.5f1}}` | 20 个里程碑表（奖金/发展点/扩张许可/贷款上限/解锁内容）、发展树 1/2/4/8 点、**地图 441 格 × 0.4 km²**、购地成本公式 |
| S19 | Info views | https://cs2.paradoxwikis.com/Info_views | `{{Version\|1.0}}` | 33 个信息视图逐条功能 + 各视图的指标口径 |
| S20 | Policies | https://cs2.paradoxwikis.com/Policies | `{{Version\|1.0}}` | 城市/区域/建筑三级政策全表、**路边停车费 ₡1–50 与地块停车费 ₡1–50**、限高/禁行/限速类政策 |
| S21 | Pollution | https://cs2.paradoxwikis.com/Pollution | `{{Version\|1.0}}` | 五类污染（地面/空气/水/地下水/噪音）来源与后果、隔音墙/树木的降噪关系 |

> ⚠️ **重要方法论提示**：S10/S11/S13/S14/S15/S16/S17/S19/S20/S21 的正文散文部分大多仍标注 1.0 或 pre-release，**但其中的建筑/道路数值表格是由 PyHelpersForPDXWikis 从游戏数据自动生成的，标注 1.6**。因此：**表格数值可信度高（1.6），正文描述可能滞后**。引用正文机制描述时请标注"版本可能滞后"。

### 2. 官方开发者日志与功能说明（Paradox / Colossal Order）

| # | 标题 | URL | 日期 | 支撑了哪些结论 |
|---|---|---|---|---|
| S22 | Feature Highlight #3: Public & Cargo Transportation | https://www.paradoxinteractive.com/games/cities-skylines-ii/features/public-cargo-transportation | 2023-07-03 | **交通线工作流 Depot→Stops→Tracks→Lines**、Waypoint 可绕开拥堵路段、同一站点可服务多条线但会拥堵、线路面板可调票价与车辆数、使用率接近 100% 时应加车 |
| S23 | Feature Highlight #9: Economy & Production | https://www.paradoxinteractive.com/games/cities-skylines-ii/features/economy-production | 2023-08-14 | 资金四主体（玩家/家庭/公司/抽象投资人）、税率 −10%~30%、预算 50%–150%、资源 price/weight/space 三因子、专业化工业 9 类、仓库作用。（**注意：本文写于 1.0，其中"政府补贴"后来被 Economy 2.0 移除**） |
| S24 | Feature Highlight #4: Zones & Signature Buildings | https://www.paradoxinteractive.com/games/cities-skylines-ii/features/zones-signature-buildings | 2023-07-10 | S10 中需求/地价/建筑等级段落的原始出处 |
| S25 | Economy 2.0 Development Diary #1 (Colossal Order) | https://colossalorder.fi/news/economy-2-development-diary-1/ | 2024-06-01 | **Economy 2.0 设计意图**：取消补贴、导入服务收费、需求按家庭规模与财富决定密度、教育与就业改动、资源双轨定价 |
| S26 | Patch 1.1.5f1 官方论坛帖（Economy 2.0） | https://forum.paradoxplaza.com/forum/index.php?threads/1687527 | 2024-06-24 | 与 S4 互证；Wiki 版改动清单的原始公告 |
| S27 | Patch 1.2.0f1（Detailer's Patch #2）官方帖 | https://forum.paradoxplaza.com/forum/index.php?threads/1720277 | 2024-12-11 | Line Tool / Traffic Routes / Service Vehicle Parking 新功能 |
| S28 | Patch 1.2.5f1（Anniversary）官方帖 | https://forum.paradoxplaza.com/forum/index.php?threads/1731875 | 2025-03-18 | 犯罪累积修复、无家可归系统、垃圾运输能力提升 |
| S29 | Patch 1.3.6f1（Bridges & Ports）官方帖 | https://forum.paradoxplaza.com/forum/index.php?threads/1864021 | 2025-10-29 | 与 S6 互证；工业噪音扩大的"重要变更"声明 |
| S30 | Patch 1.4.2f1（Bike Patch）官方帖 | https://forum.paradoxplaza.com/forum/index.php?threads/1875459 | 2025-11-19 | 自行车整套系统 |
| S31 | Patch 1.5.2f1（Asset Mods Patch）官方帖 | https://forum.paradoxplaza.com/forum/index.php?threads/1883661 | 2025-12-04 | 资产编辑器开放：玩家可自制并分享资产 |
| S32 | Patch 1.5.7f1「Spring Cleaning」官方帖 | https://forum.paradoxplaza.com/forum/index.php?threads/1918757 | 2026-04-29 | 公共交通卡死修复、商业需求改为"平均备货水平" |
| S33 | Patch 1.6.0f1「Summer Solstice」官方帖 | https://forum.paradoxplaza.com/forum/index.php?threads/1927254 | 2026-06-22 | 寻路距离上限分目的设定（原文："Pathfinding limits are now tailored per trip type: work, school, shopping, and leisure each use a sensible range rather than a shared near-unlimited cap"） |
| S34 | Patch 1.6.2f1「Autumn Breeze」官方帖 | https://forum.paradoxplaza.com/forum/index.php?threads/1940757 | 2026-09-15 | 垃圾车预留容量逻辑、公司按"最紧缺资源"优先租铺、住宅需求按城市规模修正 |

> **【本轮（经济/幸福度专题）新增的官方来源 S36–S38】**
>
> | # | 标题 | URL | 日期 | 支撑了哪些结论 | 可信度 |
> |---|---|---|---|---|---|
> | **S36** | Dev Diary: **Economy 2.0 Part 1**（Paradox 官网） | https://www.paradoxinteractive.com/games/cities-skylines-ii/news/dev-diary-economy-part-one | 2024-06-03 | **本文件最重要的一手来源之一**：政府补贴移除的设计意图；资金四主体（玩家/家庭/公司/抽象投资人）；城市服务建造与维护 + 道路 = "几乎所有钱的去处"；服务维护费显著提高；Import City Services 政策的引入；需求按家庭规模与财富；**"下调所有产品的单位工作量"→ 公司利润下降 → 可征税总额下降**（原文："rebalanced to bring tax income to a more reasonable level"）；资源双轨定价；工资上调 | **高（官方一手）** |
> | **S37** | Dev Diary: **Economy 2.0 Part 2**（Paradox 官网） | https://www.paradoxinteractive.com/games/cities-skylines-ii/news/dev-diary-economy-part-two | 页面标注 2025-06-10（**内容为 Economy 2.0 Part 2，与 1.1.5f1 同期，实际应为 2024-06；站点日期疑为迁移错误 → 待验证**） | **租金公式的官方出处**：`Rent = (LandValue + (ZoneType × Building Level)) × LotSize × SpaceMultiplier`；**虚拟房东移除 → 维护费由所有租户平摊**；**建筑等级 = 租户能否付满 upkeep**（付满→状况按固定步长上升→升级；付不起→同幅下降→倒塌）；**"High Rent" 通知改为基于家庭收入判定**（收入不够才抱怨 → 找便宜房或搬出城）；现有城市加载后的预期变化（失业率上升、高租金通知消失） | **高（官方一手）** |
> | **S38** | Patch 1.3.6f1 官方帖（SteamDB 归档，用于交叉验证 S6/S29） | https://steamdb.info/patchnotes/20207608/ | 2025-10-29 | 与 S6 互证；工业噪音扩大的版本锚点 | 中（第三方归档官方文本） |
>
> **⚠️ 术语更正**：旧来源 S25 是 **colossalorder.fi** 的《Economy 2 Development Diary #1》；S36/S37 是 **paradoxinteractive.com** 的《Economy 2.0 Part 1 / Part 2》。
> 三者是**不同的文章**，不要混为一条。**S37 是租金公式唯一的一手出处**，引用租金公式时必须引 S37。

### 2b. 官方 Wiki 页面 —— 本轮新核查（增量）

> 以下页面上轮**未收录**或未逐页核对。可信度与 C3 同规则：**自动生成表 = 可信度高（1.6）；散文正文 = 可能滞后**。

| # | 页面 | URL | 版本标注 | 本轮用它确认了什么 |
|---|---|---|---|---|
| **S50** | Zoning（**本轮逐页核对，补充了上轮漏掉的三条关键句**） | https://cs2.paradoxwikis.com/Zoning | 正文 1.0，最后编辑 2026-02-10 | ① **"Lower density supports fewer people but provide more taxes from each one"**；② **"High density supports more people but provide fewer taxes from each one"**；③ **Low Rent Housing "The lower rent provides lower tax income as a result."**；④ **"If the rent is higher than the upkeep cost of the building, the residents pool their leftover funds into improving the building which eventually leads to the building leveling up."**；⑤ Mixed Housing = "commercial space on the bottom and apartments on top"；⑥ 地价闭环与平抑手段；⑦ **本地销售永远比出口更赚钱**、持续出口利润递减 |
| **S51** | Roads（**本轮重新抓取完整道路表**） | https://cs2.paradoxwikis.com/Roads | 自动生成表标注 **1.6** | **每条道路的 `Noise pollution factor` 与 `Air pollution factor`**（Two-Lane Road 1×/1×、**Gravel Road 2×/1×**、**Pedestrian Street 2×/1×**）；隧道/高架/平地的三套造价与维护费（Two-Lane Road 隧道 ₡33.5K/km 建 + ₡2.96K/km 维护 vs 平地 ₡4.0K + ₡487）；**官方仍在正文写 "The larger the road, the higher the speed limit and traffic capacity"，没有任何 pcu/h 数字** |
| **S52** | Transportation（**本轮完整抓取**，含全部建筑表与机制段） | https://cs2.paradoxwikis.com/Transportation | 正文 1.0 | ①**线路使用率百分比是官方唯一的加车信号**（"usage percentage close to 100% … shorten passenger wait times … which in turn affect their pathfinding calculations"）；②**Airport +3% Office Efficiency 全城**、+5% Attractiveness；③**International Airport +10% Attractiveness / +10% Interest in University Education / +10% Demand for Software**；④**ChirpX Space Centre +10% Software / +10% Electronics 需求、+60 Indoor Recreation**；⑤**货运终端即使不开线也能当配送中心**；⑥货运终端会产生大量卡车流量 → "crucial to prioritize the road connections"；⑦渡轮 100 人、货船 1000 t、货运终端储位 15.5 kt；⑧**⚠️ depot/车站维护费与 S15 冲突（见 C17）** |
| **S53** | ⚠️ `https://cs2.paradoxwikis.com/Taxes` | — | — | **HTTP 404，该页不存在**（税收内容全在 Economy 与 Citizens 页）。本轮已实测，**不要再找这个页面**；`Zoning` 页里的 `[[Taxes]]` 链接是红链 |
| **S54** | ⚠️ `https://cs2.paradoxwikis.com/Happiness` | — | — | **重定向到 `Citizens`**（`#Happiness` 锚点）。幸福度因子的正式出处是 **Citizens 页**，不是独立页 |

### 3. 官方扩展包/DLC 说明

| # | 标题 | URL | 说明 |
|---|---|---|---|
| S35 | Bridges & Ports 扩展 | https://www.paradoxinteractive.com/games/cities-skylines-ii/add-ons/cities-skylines-ii-bridges-and-ports | 渡轮、港口资产、海上油气、渔业、活动桥/双层桥；S6 的 DLC 内容与之一致 |

### 3b. 【第三轮（实操攻略专题，2026-10-13）新增的官方一手来源 S70–S73】

> 本轮的关键收获：**官方 Wiki 的原生 wikitext（`?action=raw`）比渲染页可读性好得多**，
> 因为它**跳过了 MediaWiki 的导航框架**，正文一次全出。**以后凡遇到页面正文被导航树截断（如 S63），先试 `?action=raw`。**
> 注意：`action=raw` 也会被长度截断，但截断位置**落在正文中间而不是导航里**，可用 `&section=N` 精确定位。

| # | 页面 | URL | 版本标注 | 本轮用它确认了什么 | 可信度 |
|---|---|---|---|---|---|
| **S70** | **`Services`（原生 wikitext）** | https://cs2.paradoxwikis.com/index.php?title=Services&action=raw | 正文 `{{Version\|1.0}}` | **本轮最有价值的一条新机制**：官方明文**预算滑块会改变 "the range of the service coverage"**（"Services will increase their service capacity (trash trucks, police cars, student capacity, etc.) if the budget is increased… Other effects may be less obvious, **such as the range of the service coverage**"）。另确认：50% 预算 = 25% 效率 / 150% = 125% 效率；**通信每人 1 Gbit/s**、信号强度**离源越远越弱**、Well-being 增益随距离下降；**没有 Post Sorting Facility 时本市寄出的邮件全部走外部连接、且只有外部邮件能在市内投递**；专业化工业"车辆不走城市道路"的表述在 `Services#Transportation` 段复现 | **高（官方一手）** |
| **S71** | **`Zoning`（原生 wikitext）** | https://cs2.paradoxwikis.com/index.php?title=Zoning&action=raw | 正文 `{{Version\|1.0}}` | ① **全部地块尺寸范围表**（低密度住宅 4–24 格 2×2~4×6；中密度住宅与**高密度住宅尺寸范围完全相同** 4–36 格 2×2~6×6；混合住宅 4–36 格 2×2~6×6；低密度商业 4–30 格；高密度商业 4–36 格；**低租金住宅 4–36 格**；工业 4–36 格；低/高密度办公 4–36 格）；② **专业化工业完整表**（里程碑 + 所需资源 + 三类污染等级）：**Livestock M3 / Stone M3 是唯二不需要任何自然资源的**；Grain M4（Fertile Land）、Forestry M4（Forest）、Vegetable M5、Coal M5（Ore）、Textile M6、Ore M7、Oil M8（**火灾风险高于其它**）；污染等级 **农业类 = 噪声 Low，林业/石/煤/矿/石油 = Medium（后四者还带地面+空气污染）**；③ **专业化工业建筑永远不会 abandoned**；④ **官方明文 "High Density building generally cause higher traffic, and cause congestion on small roads"**，且低密度 **"needs less services"**；⑤ **仓库的作用原文**："Companies tend to have relatively small storage facilities… **Warehouses allow more flexibility and time to seek suitable new buyers… while still keeping production going**"；⑥ **进口的代价全在路网**："Importing goods **does not affect the revenue** of these industries, but **does affect gameplay by requiring a well-developed roadway grid**"；⑦ **低密度住宅地价风险敞口最大**的原文 | **高（官方一手）** |
| **S72** | **`Transportation`（原生 wikitext）** | https://cs2.paradoxwikis.com/index.php?title=Transportation&action=raw | 正文 `{{Version\|1.0}}` | ① **货运终端即使不开货运线也能当配送中心**（"**Even with no cargo lines**, companies ordering resources can use the station's storage facilities… **working like a distribution center**"）；② **"it can generate a lot of truck traffic. Therefore it is crucial to prioritize the road connections to the terminal"**；③ **"it is cheaper and faster to ship goods on trains than to haul them to the Outside Connections by trucks"**；④ **Cargo Harbor 可升级 Railway Connection**；⑤ **储位 15.5 kt**（Cargo Train Terminal / Cargo Transfer Station / Cargo Harbor）、机场货运 **800 t**（无货运升级时 **0 kg**）、货船 **1000 吨**、渡轮 **100 人**；⑥ **车队上限原始值**：Bus Depot **25 Vehicles**、Tram Depot **10**、Subway Yard **10**、Terminal Subway Yard **5**、Rail Yard **10**、Railway Depot **8**、Taxi Depot **25**、Small Taxi Depot **8**；⑦ **站台数与 Comfort**：Small Bus Station 3 台 50 Comfort、City Bus Station 6 台 40、Bus Station 6 台 50、Small Train Station 2 台 10 Comfort、Train Station / Terminus Station 3–4 台 50、City Central Train Station **14 台**、Harbor 1 泊位 50、Airport **5 Gates 50 Comfort**、International Airport **18 Gates 90 Comfort**；⑧ **默认维护费原始值**（见 **C17 更新**） | **高（官方一手）** |
| **S73** | **`Policies`（原生 wikitext）** | https://cs2.paradoxwikis.com/index.php?title=Policies&action=raw | 正文 `{{Version\|1.0}}` | 三级政策全表（城市/区域/建筑）。本轮新增可用项：**`Roadside Parking Fee` 是"区域政策"（里程碑 5，₡1–50）**；**`Parking Fee` 是"建筑政策"（₡1–50）**；**`Heavy Traffic Ban`（M6）**："Trucks and other heavy vehicles are forbidden from entering the district… **Highways remain unaffected**"；**`Speed Bumps`（M5）"brings noise pollution down significantly"**；**`Advanced Pollution Management`（M6）**降工业空气/地面污染但**产生更多垃圾**；**`High-Speed Highways`（M10）**解除高速限速但**噪声上升 + 事故略增**；**`Gated Community`（M7）**、**`Combustion Engine Ban`（M10）**、**`Import City Services`（M4）**、**`Taxi Minimum Fare`（M4，"This is added to the fare based on the actual distance traveled"）** | **高（官方一手）** |

---

## 二、社区与第三方来源（可信度递减，已逐条标注）

| # | 标题 | URL | 日期 | 支撑了哪些结论 | 可信度 |
|---|---|---|---|---|---|
| S40 | How to Design Efficient Bus, Tram, and Metro Lines in CS2（Chill Place Gaming） | https://chillplacegaming.com/cities-skylines-ii-bus-tram-metro-lines/ | 2026-07-27 | 社区定性经验：公交/电车/地铁分工门槛、支线喂给而非与地铁平行、避免"一条超长线"、用 ridership overlay 找低效站、站距由宽到窄为地铁>电车>公交 | **中**（无游戏内数值，属经验法则；已在 30 文件中与机制结论分开标注） |
| S41 | Public Transport Showdown: Bus vs Tram vs Metro（Chill Place Gaming） | https://chillplacegaming.com/cities-skylines-ii-public-transport/ | — | 尝试获取失败（HTTP 403 Forbidden），**未采信任何内容** | **不可用** |
| S42 | CS2 Modding Guide — Pathfinding & Transit 参考 | https://github.com/BrokeAssSoftware/cs2-modding-guide/blob/integration/reference/game-systems/pathfinding-transit.md | — | 搜索摘要显示存在该文档；本次抓取被 GitHub 前端脚本页替换、raw 域名被跨域重定向拦截，**未能读取正文，未采信任何内容**。列为后续待读来源 | **待读** |
| S43 | Cities Skylines 2 攻略情报 Wiki（日文） | https://csl2wiki.wicurio.com/ | — | 搜索命中"交通AI""警察・行政"页；未抓取正文 | **待读** |
| S44 | 都市天际线2 中文 Wiki（biligame 镜像） | https://wiki.biligame.com/csl2/ | — | 搜索结果中出现与官方 Wiki 一致的服务建筑数值行（如 Large Emergency Shelter 3000/50000/10.0），可作为中文对照 | **中（与官方 Wiki 同源数据）** |

> **【本轮（经济/幸福度专题）新增的社区与第三方来源 S60–S66】**
>
> | # | 标题 | URL | 日期 | 内容 | 可信度 |
> |---|---|---|---|---|---|
> | **S60** | 城市天际线 2 物流与仓储机制详细解析（电玩帮 vgover） | https://www.vgover.com/news/88101 | 2024-02-07 | 跨城进出口机制；**"仓储低于 50% 且本地无法补货时开始从外部连接进口"**（唯一见到的进口触发阈值数字）；生产链示例；**"顾客无法抵达购买地点时资源会被'传送'到家中"**（在线购物降级机制）；车辆卡住会消失且资源退回 | **中低**（社区解析，无官方引文；**唯一数字 50% 标 `[社区实证]`，不得当机制引用**） |
> | **S61** | 《都市：天际线 2》交通系统赚钱思路：关闭高速、集中港口客流（造梦城市天际线） | https://citiesskyline.com/citiesskylinesgameguide/cities-skylines2-traffic-profit-guide | 2025-12-02 | 声称：关闭全部外部高速 → 客流被迫走港口/机场 → 地铁衔接市区 → 地铁/船/机票价统一设 **₡50** → 交通收入**超过卖电**；称"一班地铁可挤满八九百人" | **低**（二手转述"有玩家分享"，无截图数值面板；"八九百人/班"与官方未公布载客量冲突 → 见 **C19**，**禁止引用该数字**） |
> | **S62** | 【シティーズスカイライン2】オフィス区の概要と収益性について解説（キラGames） | https://kiragames.jp/?p=770 | 2026-01-30 | 办公区定性：低密度办公**开局就要求平均学历以上**；高密度办公最多约 **300 个岗位**；**"办公区卡车少，但通勤/下班容易堵，必须配公共交通"**；效率 <100% 会直接压低收益；特殊（签名）建筑多提供效率加成 | **低**（日本第三方攻略站；无游戏内数值面板佐证。"300 岗位"与 "卡车少" 两条方向性与官方法定一致，但**数字不得引用**） |
> | **S63** | CS2 Modding documentation（ps1ke 镜像，含 `EconomyPrefab` / `LandValuePrefab` / `PropertyUtils` / `TaxPayer` 等页） | https://ps1ke.github.io/Cities-Skylines-2-Modding-Guide/ | — | **存在 `Game.Agents.TaxPayer`、`Game.Prefabs.EconomyPrefab`、`Game.Prefabs.LandValuePrefab`、`Game.Buildings.PropertyUtils`、`Game.Buildings.BuildingCondition`、`Game.Buildings.BuildingHappinessFactor` 等类型页** —— 这是**从游戏程序集侧确认"税收/地价/建筑状况/幸福度因子确实是独立系统"**的证据 | **待读**：本轮两次抓取均**只得到导航树、正文被截断**（站点是 MkDocs 单页大导航）。**未采信任何字段数值**。列为**下一轮首选突破点**（若能读到 `EconomyPrefab` 正文，C16 的税率系数、C17 的维护费、C20 的 Service range 单位可能一次性解决） |
> | **S64** | GitHub `Noel-leoN/LandValueRemake`（地价重做 Mod） | https://github.com/Noel-leoN/LandValueRemake | — | 搜索结果摘要显示存在一个**重做地价计算的 Mod 仓库**（说明社区认为官方地价公式可被替换/需要修） | **待读**：本轮 **3 次抓取全部失败**（`fetch failed`）。**未采信任何内容** |
> | **S65** | Steam 讨论帖「Code Deep Dive: Residential Rents」 | https://steamcommunity.com/app/949230/discussions/0/3937895062995797379 | — | 搜索结果标题显示该帖是**对住宅租金代码的逆向分析**（若可读，将是 S37 租金公式之外最重要的补充） | **待读**：本轮 **3 次抓取全部失败**（`fetch failed`，Steam 社区对本抓取器不可达）。**未采信任何内容**。**列为下一轮首选突破点**（与 S63 并列） |
> | **S66** | 3DMGAME 论坛帖「不到 3w 人创收 46w 一小时 纯办公室城市」 | https://bbs.3dmgame.com/archiver/tid-6464219.html | — | 搜索结果标题即全部可读内容：**声称 3 万人口以下的纯办公城市时入 46 万** | **不可用**：正文两次抓取失败。**仅登记标题，禁止引用任何数字** |

> **【第三轮（实操攻略专题，2026-10-13）新增的社区与第三方来源 S80–S86】**
>
> | # | 标题 | URL | 日期 | 内容 | 可信度 |
> |---|---|---|---|---|---|
> | **S80** | Cities: Skylines 2 攻略情報Wiki — **医療・葬儀**（日文） | https://csl2wiki.wicurio.com/index.php?%E5%8C%BB%E7%99%82%E3%83%BB%E8%91%AC%E5%84%80 | 最后更新 2025-11-20 | **本轮攻克 C20 的关键来源**：① 小型诊所"**カバーエリアは大体 2km くらい**"（覆盖区约 **2 km**）—— 与官方 `Service range` = **2500** 在数值上吻合，**独立佐证单位是米**；② **"カバーエリア内の人口増加にも弱く、中密度住宅、高密度住宅などの住民数の多い建物が多い区画があると一気にカバーエリアが狭くなる"**（覆盖区对区内人口增长很脆弱，一旦有中/高密度住宅这种住户多的建筑，覆盖区会一下子变窄）→ **服务半径是"需求未饱和时的最大值"，会随密度缩小**；③ 医院"カバーエリアがとんでもなく広く、**高密度住宅等の人口密集地が近くてもエリア減少量が少ない**"（医院覆盖区极大，即使旁边是高密度住宅，缩小量也小）→ **等级越高的服务建筑抗密度压缩能力越强**；④ 疾病管理センター/健康研究所"医療カバー範囲は存在しない"（没有医疗覆盖范围）→ **全城增益型建筑不等于有覆盖**；⑤ 火葬场"5万人都市でも2～3箇所あれば十分"、"処理量100体/月"；⑥ 墓地公园有"周辺300mに福祉度+2"、"2.5km"级别的福祉+5 独特设施 | **中低**（第三方 Wiki，无面板截图；**但服务半径 2 km 与官方 2500 数值互证 → 该条可升为"中等可信"**） |
> | **S81** | Cities: Skylines 2 攻略情報Wiki — **交通**（日文） | https://csl2wiki.wicurio.com/index.php?%E4%BA%A4%E9%80%9A | 最后更新 2025-11-27 | ① **换乘惩罚**："乗り換えになると一定距離以上の徒歩移動を嫌う"（一旦是换乘，超过一定距离的步行就会被嫌弃）→ 自宅/学校/职场到站点的步行可忍，**换乘步行不行**；② **枢纽人车分离**："バスターミナルは車道と歩道を分離するように道路を敷かないと、横断する歩行者が大渋滞を引き起こす"；③ **电车 ≈ 抗堵版公交**："バスより一回の輸送量が多い…渋滞に巻き込まれにくく輸送量が多いバス"；④ **铺电车会吃掉一条车道**："中央分離帯付き道路を路面電車路線にアップグレードすると、**車線が1つ減り**…"；⑤ **电车站自带人行横道与信号灯** → 交通量大处会变堵点；⑥ **地铁有噪声**，"近隣に駐車場等の騒音源があると波及して騒音範囲が広がる"→ 别贴住宅；⑦ **出租车定价在政策里**，且"**安易に安くするとたった300mくらいでも使ったりして渋滞の大きな原因になる**"；⑧ **公交 Extra Garage 性价比不佳**："維持費約1.5倍に対し増加車両は1.4倍と微妙に釣り合っていない"；⑨ **电车扩容只能多建车库**："台数増加のアップグレードはユニーク分しかないので運用数は路面電車車庫の数に比例する"；⑩ **机场噪声意外地小**："空港の敷地外なら無視できる程度"；⑪ **货运港口自 1.1.1f 起改为"和店铺/工业区一样的刷车形式"**，导致"Uターンする無能が大量発生"（大量掉头卡车 → 死锁），**与官方"货运终端会产生大量卡车"的警告一致** | **中**（第三方 Wiki，含具体数值与版本锚点；**每条都在 `47` 中单独标了可信度，作处方依据时必须与官方机制交叉成立**） |
> | **S82** | Cities: Skylines 2 攻略情報局 — **医療カバーエリア・医療施設・病人**（日文） | https://cities-skylines2.com/2024/01/07/%e5%8c%bb%e7%99%82%e6%96%bd%e8%a8%ad%e7%97%85%e4%ba%ba/ | 2024-01-07 | 医疗覆盖面积专题；本轮抓取正文被截断（只有标题可读）→ **未采信任何内容**，仅登记 | **待读** |
> | **S83** | 游侠网（ali213）—《城市天际线2》设施布局分配一览 | https://gl.ali213.net/html/2023-10/1199903.html | 2023-10-28 | ① **公交站数经验区间**："通常 **5~10 个站台**会好一些，太多了会导致等待时间过长"；② **"长短双线"分流法**："同一条路线造两条线路…通常采用的是**大站制（如一条 10 站另一条 5 站）**"；③ 教育/警力/消防"按范围来定，哪里不够放哪里"；④ 回收中心"居民较少时产出并不算高，且需要连接运输线路才能卖垃圾产出" | **低**（中文攻略站，无游戏内数值）。②**与本项目 `SKILL.md` §5.2 反模式 1 冲突 → 登记为 C22** |
> | **S84** | 造梦城市天际线（citiesskyline.com）— 城市天际线 2 堵车解决全攻略：停车场规划与停车费设置 | https://citiesskyline.com/citiesskylinesgameguide/cities-skylines-2-traffic-fix | 2025-12-01 | ① **市民 AI "优先停在路边"** → 车辆在道路上滞留找车位而阻塞交通；② **处方**："在政策面板中大幅拉高路边停车的价格，使其明显高于停车场的收费标准。利用经济杠杆迫使 AI 放弃路边停车…**还能增加一笔不菲的财政收入**"；③ 主张建地下停车场与立交、做主支路分流 | **低**（无任何面板数字）。**但②的方向与官方机制互证**（停车费进入寻路成本 Money 因子、`Roadside Parking Fee` 与 `Parking Fee` 是两级政策）→ **`47` §3.5 已把它降级为"有机制依据但无量化收益"的处方** |
> | **S85** | Ben's Cities — Traffic and Transit Optimisation Part 2 #citiesskylines2 | https://benscities.blog/2023/12/19/traffic-and-transit-optimisation-part-2-citiesskylines2-neo-south-auckland/ | 2023-12-19 | 新西兰规划博主（Talking Auckland 作者）的实测系列（**有过程、无面板数字**）：① 城市 5 万 → 7.3 万 → 8 万 → 8.5 万人口，**全部在既有 footprint 内靠 upzoning 加密**；② 结论："**原本富余的交通设施（尤其公交资产）迅速被吃光，变成赤字**"；③ 做法是**先做"优化计划"（路口升级 + 改公交车道位置）让公交线跑得更顺，而不是直接上电车**；④ 明确把 "**One More Lane Shall Fix It?**" 列为伪命题；⑤ 引用奥克兰交通局街道设计手册的"一条车道在不同模式下能运多少人"图，并主张"**同样的原理适用于 CSL2**" | **中低**（有完整过程与作者署名，**但没有任何游戏内面板数字**；其"同原理适用于 CSL2"是**主张而非实测**） |
> | **S86** | csl2wiki（日文）— **交通（道路・公共交通）子页 / 区画 / エリア** 等 | https://csl2wiki.wicurio.com/index.php?%E5%8C%BA%E7%94%BB | 2025-2026 | 本轮**尝试但未逐页读取**；站点结构清晰、可 `?cmd=diff` 查变更历史 → **列为下一轮可持续挖掘的日文一手社区资源**（该站对服务半径/道路/交通的分类最细） | **待读** |

### 2e. 【第三轮】尝试但**未采信**的来源（教训记录）

> 第二轮的同类记录在下一小节 **2c**（保留原始编号与内容）。

| 来源 | 结果 | 教训 |
|---|---|---|
| `https://steamcommunity.com/app/949230/discussions/...`（`3937895062995797379` 即 **S65「Code Deep Dive: Residential Rents」**，以及本轮新命中的 6 个帖子） | **全部 `fetch failed`** | **第 3 轮确认：Steam 社区讨论区对本抓取器不可达**。`00-sources.md` 里 S65 可以正式从"下一轮首选突破点"**降级为"不可达来源"**；要看内容只能请玩家贴文本或截图 |
| `https://ps1ke.github.io/Cities-Skylines-2-Modding-Guide/Game/Prefabs/EconomyPrefab/`（正确路径，非上轮的 `/api/...`） | **HTTP 200 但正文仍被 60 KB 的 MkDocs 导航树吃光**；`Game/Agents/TaxPayer/`、`Game/Buildings/PropertyUtils/`、`Game/Buildings/ModifiedServiceCoverage/` **同样** | **S63 的"正文被导航截断"是站点结构问题，本轮 4 次尝试全部失败**。→ **这是可确认的死路，不要再投预算**。**替代方案已找到**：官方 Wiki 的 `?action=raw` 能拿到等价或更好的机制原文（见 S70–S73） |
| `https://www.reddit.com/r/CitiesSkylines2/...` | **`URL hostname resolves to a non-public IP address`** | **Reddit 对本抓取器不可达**（与 namu.wiki 同类）。→ 社区实证类证据只能从官方论坛、日文 Wiki、中文攻略站获取 |
| `https://en.namu.wiki/w/시티즈: 스카이라인 II`（第 2 次尝试） | **`fetch failed`** | 与上轮一致。**该来源可正式标记为不可达**；其中"Service range 与前作不同"的线索**已由 S80 完全替代** |
| `https://www.modscities2.com/cities-skylines-2-service-coverage/` | **HTTP 403（Cloudflare 拦截）** | 与 `chillplacegaming.com` 同类 → **记录为新的一般性封锁站** |
| `https://forums.somethingawful.com/showthread.php?threadid=3706710` | **`fetch failed`** | 论坛类站点对本抓取器大多不可达 |
| `https://www.neowin.net/news/cities-skylines-ii-update-delivers-easy-game-mode-...` | **`fetch failed`** | 本想用它核实"Easy 难度模式"的维护费倍率（C17）→ 未读到。**C17 已改由 S72 的原始数值解决，不再需要该来源** |
| `https://www.bilibili.com/read/cv25083101/`（官方 Dev Diary #5 中文翻译） | HTTP 200 但被重定向到验证码页 | **B 站专栏对本抓取器不可达** |
| `https://cities-novacivitas.com/game-info/specialized-industry/`、`/game-info/transportation/`、`https://cities-skylines2.com/2024/01/07/...` | HTTP 200 但**正文被截断（只有标题）** | 日文博客类站点正文抓取不稳定 → **不作为可引用来源** |

### 2c. 本轮尝试但**未采信**的来源（教训记录，避免重复劳动）

| 来源 | 结果 | 教训 |
|---|---|---|
| `https://chillplacegaming.com/cities-skylines-ii-taxes-income/` | **HTTP 403** | 与上轮 S41 同一站点，**同一站点整体对本抓取器不可用**（`chillplacegaming.com` 全站 403）。**以后不要再尝试该域名** |
| `https://steamcommunity.com/app/949230/discussions/...`（3 个不同帖子） | **全部 `fetch failed`** | **Steam 社区讨论区对本抓取器不可达**。要看 Steam 讨论内容需换途径（截图/玩家转述）或直接请玩家贴文本 |
| `https://en.namu.wiki/w/시티즈: 스카이라인 II` | **URL hostname resolves to a non-public IP** | namu.wiki 镜像不可达。搜索摘要里出现过一句关于 Service range 的线索（"In the previous work, the service range was provided to the same extent no matter how many buildings there were within the ser…"），**但正文未读到 → 未采信**；已作为 C20 的下轮线索 |
| `https://raw.githubusercontent.com/BrokeAssSoftware/cs2-modding-guide/...` | **`fetch failed`**（连试 3 种 URL 形式） | 与上轮 S42 同一仓库，**仍未读到正文**。上轮已标"待读"，本轮维持 |
| `https://pttgamer.com/Steam/1brUgLKr`（2000+ 小时 / 200 万人口心得） | HTTP 200 但**正文被截断为 0 字** | 台湾 PTT 长帖，抓取器只取到标题行。**未采信**；线索仍是"公交缺失 → 迁出 + 商业倒闭潮" |

---

## 三、本次**未**能获取 / 明确为缺口的内容

| 缺口 | 说明 | 状态 |
|---|---|---|
| 各交通方式**单车载客量**（bus / tram / subway / train / ferry / ship / plane） | 官方 Wiki 的 Transportation 与 Service buildings 页面**均未给出载客量字段**；仅渡轮有正文提及"Ferries carry 100 passengers"（S13） | **待验证**：仅有渡轮 100 人有官方正文来源，其余**无来源**，禁止编造。⭐ **但"容量归一"用的取值见 C19 补充**（公交 80 / 地铁 1080 / 客运火车 840，**玩家提供的游戏内可信数值**，只用于归一） |
| 线路**自动发车间隔算法** | 官方全部来源一致表明：玩家手动设定"该线路车辆数"，游戏不暴露"目标间隔"参数 | 见 `30-public-transport.md`，标注为"机制理解+待验证" |
| 公交换乘/候车时间的**具体权重系数** | 未找到官方或可靠社区给出的数字 | **待验证** |
| 各建筑的**具体覆盖半径单位换算**（Service range 数值 → 米） | Service buildings 表给出 `Service range` 数值（如 Small Medical Clinic 2500、Hospital 7500），但**未说明单位**。社区普遍理解为"米"级量纲，但官方无明文 | ✅ **第三轮结案：单位是米**（见 **C20** 更新与 **R10**）：官方 `Roads` 页确认 **1 格 = 8 m**；同表内 km / m / 裸数值混排且量级自洽；社区独立来源把 2500 读作"约 2 km"。**但新增限制见 C23**（该值是"需求未饱和时的最大半径"，会随密度缩小） |
| 税率"甜蜜点"的官方定义 | 官方仅说"低税率加快建筑升级、高税率收入更多"（S17），**没有官方甜蜜点数值** | **待验证**（第三轮**第 2 次确认**：仍未找到可复现的社区实测 → 见 **C16** 更新） |
| 地图可玩面积 159 km² | 用户任务书提到的数字；官方 Wiki 给出 441 格 × 0.4 km² = **176.4 km²**（S18） | **冲突**，见下第四节 |

> **【第二轮（经济/幸福度专题）新增的缺口】**
>
> | 缺口 | 说明 | 状态 |
> |---|---|---|
> | **四类税率的默认值** | Economy 页与两篇官方 Dev Diary 均**未给出四类税率滑块的默认数字** | **待验证**（需玩家在 Economy → Taxation 面板读数） |
> | **租金公式里的 `ZoneType` 系数与 `SpaceMultiplier` 取值** | 公式本身是官方原文（S37），但**两个系数官方都没给**。唯一已知：1.1.5f1 把工业制造的 `space multiplier` 从 **1 提到 5**（S4） | **待验证** |
> | **1.6.0f1 寻路距离上限的四类具体数值** | 官方原文只说 "work, school, shopping, and leisure each use a sensible range"，**没有数字** | **待验证**（算法上只能做敏感性分析，见 `46` T5c） |
> | **各类道路的通行能力（pcu/h 或辆/小时）** | 官方 Roads 页正文只有 "The larger the road, the higher the speed limit and traffic capacity"，**无任何数字**；表格也只给车道数/限速/造价/维护/噪音与空气污染系数 | **待验证**（本轮再次确认） |
> | **各服务方式（bus/tram/subway/train）的单车载客量与票价收入公式** | 官方 Transportation 页只给"票价/车辆数/运营时段"三项可调 + "使用率接近 100% 应加车"，**没有载客量、没有票价收入公式、没有每乘客补贴** | **待验证**。→ **"哪种交通方式每乘客补贴最低"在官方数据下无法回答** |
> | **幸福度 10 因子的相对权重** | 官方列出 10 项因子与正负方向，但**没有权重**。Happiness 视图只显示明细构成 | **待验证**。→ 算法上只能做定性排序 + 因子级缺口，不能做"幸福度分数预测" |
> | **"幸福度过低"的阈值数字** | 官方只有 "Low happiness affects the chance a household will move out of the city"（1.1.5f1），**没有阈值** | **待验证**。→ 禁止设绝对阈值 |
> | **"幸福度税率容忍度"的基准值** | Central Bank 提供 **+1** 税率容忍度（1.3.6f1），说明该参数存在，但**基准值与单位未公布** | **待验证** |
> | **工业/分区污染的扩散半径具体米数** | 1.3.6f1 官方只说"量与扩散半径双双上调"，**没有数字** | **待验证**。→ 算法只能做几何代理（`46` T5） |
> | **每格 / 单位面积的税收与岗位产出实测表** | 官方**没有**；本轮也**没有**找到可复现的社区实测 | **明确为缺口**，见 `45` §C3。**禁止编造数字** |
> | **各难度模式（Easy / Normal）对维护费的具体倍率** | ~~本轮发现同 Wiki 两处 depot 维护费系统性差 0.75 倍（C17），推测与难度模式有关~~ → **第三轮更正：该归因已被推翻**（见 **C17 更新 / R15**），两页数值本身是两套不同的数且不成统一比例 → **本行缺口作废，不再需要核查** | ✅ **已关闭（归因推翻）** |

> **【第三轮（实操攻略专题）新增的缺口】**
>
> | 缺口 | 说明 | 状态 |
> |---|---|---|
> | **各类道路的通行能力（pcu/h 或辆/小时）** | 官方 `Roads` 页正文只有 "The larger the road, the higher the speed limit and traffic capacity"，**无任何数字**；`?action=raw` 全文核对后确认表格也只给车道数/限速/造价/维护/噪音与空气污染系数 | **待验证（第 3 次确认）** |
> | **各交通方式单车载客量** | 官方 `Transportation` 页 `?action=raw` 全文核对：**只有渡轮明确写 "Ferries carry 100 passengers"**，货船 1000 吨；bus / tram / subway / train / ship / plane **均无载客量字段** | **待验证（第 3 次确认）** |
> | **每格 / 每公顷税收产出实测表** | 官方无；第三轮仍未找到可复现实测 | **明确为缺口**（第 3 次确认） |
> | **服务覆盖半径"被密度压缩"的定量关系** | 只有社区定性描述（"一下子变窄"），**没有曲线/公式** | **待验证**（**C23**） |
> | **`Heavy Traffic Ban` 是否影响商铺补货** | 官方原文只禁止重车进入、并说"Highways remain unaffected"，**未说明对送货的影响** | **待验证**（**C24**） |
> | **仓库（Warehouse）的具体储位数与车辆数** | 官方表本轮未抓到；1.3.6f1 已确认车辆 **3→10** | **待验证**（**C27**） |
> | **`Extra Garage` 升级后的车辆数与维护费增量** | 官方只写"可升级"，无数字；社区给了"×1.5 / ×1.4"但可信度低 | **待验证**（**C25**） |
> | **环岛 vs 信号路口的定量通行对比** | 官方只有造价与行为描述（"will cut in front of another vehicle… if a suitable opportunity arises"），无通行量数据；社区无可复现实测 | **待验证** |
> | **Lane Connector 的效果与已知 bug** | 官方 Wiki 无该工具的文档页；社区反馈分散且矛盾 | **待验证** |
> | **公交专用道 / 独立公交道的定量收益** | 官方只提供工具，未给收益数字；社区帖互相矛盾 | **待验证** |
> | **线路长度上限 / 站距建议的具体米数 / "多少人口该上地铁"** | 第三轮仍未找到；**但找到一条可用的替代判据**：`Subway Yard = 10 辆` 的硬上限（官方）→ 所需车辆数超过 10 就该规划第二个 yard | **待验证**（替代判据见 **R 系列 / `48` B6**） |
> | **税率"甜蜜点"** | 第三轮仍未找到可复现实测 | **待验证**（**C16**） |
> | **公共交通"每乘客补贴"与票价弹性** | 官方无；1.1.5f1 起城市层面无补贴机制（只能票价置 0 / 调预算 / 减线路） | **待验证**（机制部分已可回答"不存在这个机制"） |

---

## 四、⚠️ 冲突 / 不确定数值登记表

| 编号 | 冲突点 | 说法 A | 说法 B | 处理建议 |
|---|---|---|---|---|
| C1 | 地图总面积 | 用户任务书：**159 km²** 可玩面积 | 官方 Wiki（1.0.12f1 源码考证）：**441 格 × 0.4 km² ≈ 176.4 km²**，初始已购 9 格（来源：https://cs2.paradoxwikis.com/Progression ） | **以 176.4 km² 为准**；159 km² 可能来自"扣除水域/不可建面积后的实际可建面积"或 CS1 的 9 格×…旧口径。两个口径都列出，标注待验证 |
| C2 | 道路限速显示值 | 官方 Wiki 表格按**欧洲主题**显示（Two-Lane Road 40 km/h，高速 100 km/h） | 同一表格脚注：**内部限速为 80.0 / 200.0**，北美主题显示为 **30 km/h / 65 km/h**（来源：https://cs2.paradoxwikis.com/Roads ） | 引用限速时必须写"主题 + 显示值 + 内部值"。**北美主题下同一路段限速显著更低** |
| C3 | Wiki 正文版本 vs 表格版本 | 多数机制页正文标注 `{{Version\|1.0}}` 或 `pre-release` | 同页自动生成表格标注 `{{SVersion\|1.6\|table}}`，页头标注 1.5 | 数值引表格（1.6），机制描述标"可能滞后于 1.6" |
| C4 | "政府补贴"是否存在 | S23（2023-08-14）："government subsidies which help the city's budget" | S4/S25（2024-06-24）：**政府补贴已被完全移除**；改成"失业救济/养老金/家庭津贴"发给个人而非城市预算 | **1.1.5f1 及以后无城市补贴**。S23 属 1.0 时代文档 |
| C5 | 专业化工业解锁时机 | 1.0 时代：Livestock/Stone/Grain/Forestry 需里程碑解锁（S10 表格，Version 1.0） | 1.1.5f1 起：上述四类**游戏开始即解锁**（milestone 0）（来源：https://cs2.paradoxwikis.com/Progression ） | 以 1.1.5f1 为准 |
| C6 | 城际通勤者是否纳税 | S16（Citizens，含 1.3.3f1 数据）："commuters … do not pay tax at all to either city" | S4（1.1.5f1）："Workers from Outside Connections no longer pay tax" | **不冲突**，是同一事实的两次记录；但 1.0 时代城外劳工**是**纳税的（被 1.1.5f1 改掉），旧攻略可能仍写"吸引城外通勤者收税" |
| C7 | 税率对需求的强度 | 1.0：税率对需求影响较弱（玩家普遍反馈） | S4（1.1.5f1）："Taxes now have more effect on demand"；S6（1.2.5f1）："Industrial and Office zone tax income has lowered following a bug fix that deducts wages from untaxed income" | **1.1.5f1 起税率杠杆明显变强**；1.1.5f1 之前的税率攻略全部失效 |
| C8 | 建筑升级机制 | 1.0：建筑升级 ≈ 住户/公司有闲钱就升级 | 1.1.5f1 起：**"Building level is now based on whether renters can pay the upkeep fee"**，付满则建筑状况上升、付不起则下降；租金公式改为 `Rent = (LandValue + (ZoneType × BuildingLevel)) × LotSize × SpaceMultiplier`；虚拟房东被移除（来源：https://cs2.paradoxwikis.com/Patch_1.1.X ） | **1.1.5f1 起升级与租金/地价强耦合**；1.4.2f1 起建筑升级还需要工业公司/仓库/外部连接**配送资源**才能推进（来源：https://cs2.paradoxwikis.com/Patch_1.4.X ） |
| C9 | "利他/自私寻路"提法 | 用户任务书使用了 CS1 社区术语 | CS2 官方（S12）用的是 **Time / Comfort / Money / Behavior** 四要素，且**按年龄段变化**（Teen 重省钱、Adult 重省时、Senior 重舒适） | **CS2 不存在"利他/自私"参数**。给建议时应改用"按年龄与出行目的的四要素模型"，并说明这是术语迁移错误 |
| C10 | 服务覆盖半径单位 | S15 表头写 `Service range`，数值 500–10000 | 无单位说明 | 相对比较可靠（小诊所 2500 < 医院 7500），**绝对值待验证**，禁止断言"这是米" |
| C11 | 公交"发车间隔"是否存在 | 用户任务书假设"发车间隔（interval）决定车队规模" | 官方（S13/S22）：Line 面板只提供**票价 / 车辆数 / 运营时段**三项；1.3.6f1 增加"车辆多选生成"（S6） | **CS2 中不存在"设定目标间隔→系统自动配车"的机制**。实现间隔目标的方法是：`间隔 ≈ 单圈往返时间 ÷ 车辆数`。官方无明文公式 → 标"机制理解+待验证" |
| C12 | 自行车 | 1.4.2f1 引入自行车，青少年/成人/长者均可使用（S7/S30） | 1.5.4f1 **将自行车出行削减 80%**；1.5.7f1 把 Urban Cycling Initiative 政策的效果从 +20% 提到 **+50%**（S8） | **1.4.2f1 时代的"自行车很强"结论在 1.5.4f1 之后不再成立**，必须按版本区分 |
| C13 | 服务预算效率曲线 | S14：50% 预算 → 25% 效率；150% → 125% 效率 | 未找到第二来源 | 单一来源，**待验证**（但与 S23 的"预算 50%–150%"区间一致） |
| C14 | 地图外区域/水域 | 1.3.6f1 起"Water added outside the playable area"（S6） | 1.0 时代地图外无水体 | 涉水/渡轮规划在 1.3.6f1 前后不同 |
| C15 | 游戏开发主体 | 2023 首发：Colossal Order | 2026 起：**Iceflake Studios**（来源：https://cs2.paradoxwikis.com/Cities_Skylines_II_Wiki ，"developed in Unity3D originally by Colossal Order and since 2026 by Iceflake Studios"） | 引用"官方后续支持"时需注意主体已变更 |

### 4b. ⚠️ 本轮（经济/幸福度专题）新增的冲突与待验证：C16–C21

| 编号 | 冲突点 | 说法 A | 说法 B | 处理建议 |
|---|---|---|---|---|
| **C16** | **税率"甜蜜点"的数值** | 官方原话只有权衡："**Lower taxes help buildings level up faster while higher taxes bring more money.**"（Economy 页）；官方**从未给出任何最优税率数值** | 社区大量攻略声称 "10%" 或 "12%" 最优 | **维持 `[待验证]`（第三轮第 2 次确认）。** 本轮额外核查了 `Economy` 页 `?action=raw` 全文、`Policies` 页全文、以及日文/中文攻略站 —— **仍未找到任何"可复现、带数据"的社区实测**。**给玩家建议时不得给出最优税率数字**；改用 §45 §A2.1 的机制式表达（短期收入 ↑ / 升级速度 ↓ / 需求 ↓ 三项权衡）。**可用的唯一经验边界是 C18**（办公税率 30% ≈ 1 个游戏月强制清退）。<br>⚠️ **第四轮更新（2026-10-13，第 3 次确认）**：本轮**专门为这个问题**做了 5 组检索（英/中/日）并逐条尝试抓取，**仍未找到任何"可复现、带前后数据"的受控实验**。新增负面证据：① 唯一命中的中文"实测"文章（游研社 `yystv.cn/n/1012334`）**正文抓取为空**；② 唯一命中的"挑战型实测"视频（0% 税率城市）**只是"不靠税收也能盈利"的挑战**（靠卖电 ≈ ₡72K→₡150K/月），**没有做税率梯度对比** → 见 **C29**；③ NGA / Steam / Reddit 三条路全部不可达。<br>→ **本轮起改为"请玩家做受控实验"**，并在 **`41-official-data-tables.md` §12 / `48` C6** 给出**完整可执行的实验设计**（设什么税率、记录哪些面板、观察几个游戏月、什么结果说明什么）。**仍然禁止给"最优税率"数字。** |
| **C17** | **depot / 车站 / 港口的维护费** | **[W-ServBld]**（`Service_buildings` 自动生成表，标注 **1.6**）：Bus Depot **₡31,000**、Subway Yard **₡24,000**、Rail Yard **₡15,000**、Small Train Station **₡7,500**、Overground Subway Station **₡10,000**、Underground Subway Station **₡20,000**、Harbor **₡30,000**、Airport **₡50,000**、International Airport **₡200,000** | **[S52/S72]**（`Transportation` 页，正文标 1.0；**第三轮用 `?action=raw` 重新核对，与上轮渲染页完全一致**）：同样的建筑分别是 **₡23,250 / ₡18,000 / ₡11,250 / ₡5,625 / ₡7,500 / ₡15,000 / ₡22,500 / ₡37,500 / ₡150,000** | ✅ **第三轮更新（部分解决）**：**"0.75 倍差 = 难度模式"这个假设可以撤销。** 本轮用 `?action=raw` 逐条核对后发现：**两页的数值本身就是两套不同的数**——`Service_buildings` 表给的是**按比例放大过的一组**（Bus Depot 31,000 = 23,250 × 4/3；Taxi Depot **3,500** vs Transportation **7,500**，是 **0.467 倍**，方向都反了；Small Bus Station **10,500** vs **7,000**；Cargo Train Terminal **11,250** vs **7,500**；Cargo Harbor **25,125** vs 另一组），**并非统一的 0.75 倍缩放**。而 `Transportation` 页给出的正是**与官方补丁说明一致的原始值**。<br>→ **新的引用纪律**：**以 `Transportation` 页（`?action=raw`）的数值为准**，或**让玩家在游戏内建筑面板读一次**。**禁止再写"差 0.75 倍是因为难度模式"**（该归因本轮已被推翻）。同时 → 新增 **C26**：**同一张 `Service_buildings` 表的其它列（含 `Service range`）也因此需要打折看待**。`40-number-tables.md` §1.1 需改用 `Transportation` 页口径 |
| **C18** | **"办公税率 30% ≈ 强制清退"** | 1.1.6f1 官方 Known Issues 给出官方 workaround：**"Increase office tax to 30% → let the simulation run until all office buildings are empty, which may take about a month in-game time"**（来源：https://cs2.paradoxwikis.com/Patch_1.1.X ） | C16：官方从未给"甜蜜点" | **不冲突，是本轮新获得的"经验边界"**：`30% ≈ 强制清退，响应时间尺度 ≈ 1 个游戏月`。**日常税率必须显著低于 30%**。"1 个月"的响应时间尺度可直接用于算法（§46 T1 的"税基衰减"时间常数）。**外推部分标 `[待验证]`** |
| **C19** | **单班地铁载客量** | 官方：**从未公布 bus/tram/subway/train/ship/plane 的单车载客量**（`00-sources.md` §三 缺口 #1；官方公开的单车量级参照只有渡轮 **100 人**（`Transportation` 页原文 "Ferries carry 100 passengers"）、货船 **1000 吨**、机场货运 **800 t**） | **[S61]**（社区攻略，2025-12-02）："一班地铁车厢能挤满**八九百人**" | **社区那条维持禁止引用**：它没有来历、单位（"每辆"还是"每班"）也不明，且与官方公开的单车量级不符。<br>⭐ **补充：容量归一另有取值** —— 线路效率做容量归一用的单车容量 = 公交 **80** / 地铁 **1080** / 客运火车 **840** 人/辆（**游戏内可信数值，玩家提供**，标 `[玩家实测]`，见 `40-number-tables.md` 第 1.3 节），**只用于归一与跨方式排序**。它**不改变**"官方从未公布载客量"这一事实，也**不构成**对社区说法的采信。<br>凡涉及"一条线能运多少人"，仍以**游戏内线路面板的乘客数**为准 |
| **C20** | **`Service range` 的单位** | 上一轮结论（C10）：有裸数值（Small Medical Clinic 2500、Hospital 7500），**官方无单位说明** | **第三轮证据（两条独立来源，方向一致）**：① **同一张** `Service_buildings` 表里**同时存在带单位与不带单位的行**：`Radio Mast` = **1 km**、`Server Farm` = **2 km**、`Telecom Tower` = **5 km**、`Radio Mast Wireless Network Antenna` = **250 m**、`Server Farm Fiber Optic Cable` = **500 m**、`Medical University Practice Clinic` 的效应写 **"Health +5% within 1 km"**、`Firewatch Tower` 写 **"within 1 km"**；而同表的医疗/教育/警察/消防仍是裸数值。**裸数值与 km 行混排在同一列** → 说明该列**统一以"米"为量纲**（1 km 写作 1000）。② **独立的社区侧数值互证**：**[S80]**（日文攻略 Wiki，2025-11-20）写小型诊所"**カバーエリアは大体 2km くらい**"（覆盖区约 **2 km**）—— 与官方 `Service range` = **2500** 在数值上吻合；同页还有"**2.5km**"级别的独特设施福祉范围 | ✅ **第三轮结案（部分）：单位是"米"可以确认。** 三条证据合起来足够：**(a)** 官方 `Roads` 页确认 **1 格 = 8 m**（"snaps every 8 meters"）→ 游戏内长度量纲以米为单位；**(b)** 同一张官方表内 km / m / 裸数值混排，裸数值量级与米制自洽（Small Post Office 1000 ≈ 1 km，Post Office 2000 ≈ 2 km，Hospital 7500 ≈ 7.5 km）；**(c)** 社区独立来源把 `Service range` 2500 读作"约 2 km"。<br>⚠️ **但新增限制（→ C23）**：这个数值是**"需求未饱和时的最大半径"**，**区内人口密度上升会把它压缩**。→ **可以写"单位是米"，但仍然不得写"某医院保证覆盖 7.5 km"**。**下一轮突破点 S63 已降级为死路**（见 §2d），本条不再需要它 |
| **C21** | **福利（失业救济/养老金/家庭津贴）是否算城市预算支出** | 常见误解（尤其 CS1 玩家与旧攻略）：把福利当成"城市补贴支出"，主张"削减福利省钱" | 官方 Citizens 页原文：这些福利 **"are created by the game and are not deducted from any company, household, or municipal balance"**（家庭津贴 ₡400、养老金 ₡1200、失业救济 ₡800×最长 10 天）；同时 1.1.5f1 起**政府补贴（Government Subsidies）已被彻底移除** | **已澄清（更正类）**：**城市预算里既没有"政府补贴"收入项，也不承担福利支出。** 支出侧**只有城市服务 + 道路（+1.1.5f1 起的地块维护费）**。**"削减福利"在 CSL2 里不存在这个按钮**；能省的只有**服务预算滑块、服务建筑开关、地块维护费** |
| **C20-verify** | **主控独立复核（第三轮追加）** | — | 主控改用 `?action=raw&section=1` 直接抓官方 `Service_buildings` **原文**，独立读到同一张表：`Small Post Office` Service range = **1000.0**（Service capacity 5000.0 / magnitude 2.0 / Noise 2000）、`Post Office` = **2000.0**（15000.0 / 2.0 / 5000）、`Small Elementary School` = **1500.0**（7500.0 / 10.0 / 3500）；同表 `Radio Mast` 的 Range 列写作 **"1 km"**、`Server Farm` **"2 km"** | ✅ **独立复核一致，C20 结论成立。** 两个追加观察：**(1)** `Post Office`（2000 m）恰好是 `Small Post Office`（1000 m）的 **2 倍**，而月维护费 22.5K 是 7.5K 的 **3 倍** → **大建筑的"覆盖/成本"比在变差**，与"别盲目建大建筑"的判据方向一致；**(2)** 该表还有 **`Service capacity` / `Service magnitude` / `Noise pollution`** 三列，是此前未系统利用的数据（可用于"服务容量够不够"与"哪些设施是噪音源"），建议后续并入覆盖分析 |

### 4b-2. ⚠️【第三轮（实操攻略专题）】新增的冲突与待验证：C22–C27

| 编号 | 冲突点 | 说法 A | 说法 B | 处理建议 |
|---|---|---|---|---|
| **C22** | **"拆分既有干线"到底对不对** | `SKILL.md` §5.2 反模式 1 + §0 铁律：**拆分既有干线会把两条线的间隔都拉长、还多一次换乘 → 总客流下降**。依据是**本项目真实 Carto 数据**（拆分后总量低于拆分前，**实战出现过两次**） | **[S83]**（游侠网攻略，2023-10-28）："**同一条路线造两条线路，在单条线路承载量较大时将分开客流，通常采用的是大站制（如一条 10 站另一条 5 站）**" | **裁定：不采纳 S83，维持 `SKILL.md` 结论。** 依据用户给的裁定顺序（**游戏内实测 ＞ 攻略站**），且 `SKILL.md` 本条有**两次真实数据支撑**，S83 无任何数据。**唯一例外**：单条线**长期使用率 ≥100% 且加车已撞 depot 上限**时，可把"长短双线"作为**最后手段**，并**必须用 `--prev` 增量对比验收总客流** |
| **C23** | **服务覆盖半径是"固定几何"还是"会缩水"** | 官方 `Service_buildings` 表给出**固定数值**：Small Medical Clinic **2500.0**、Medical Clinic **5000.0**、Hospital **7500.0**（表标注 1.6） | **[S80]**（日文攻略 Wiki，2025-11-20）："**カバーエリア内の人口増加にも弱く、中密度住宅、高密度住宅などの住民数の多い建物が多い区画があると一気にカバーエリアが狭くなる**"（覆盖区对区内人口增长很脆弱，区内有中/高密度住宅时会一下子变窄）；且**医院"人口密集地が近くてもエリア減少量が少ない"**（等级越高越抗压缩）；另 **[namu.wiki 摘要]**（上轮线索）称前作"service range 不论区内有多少建筑都是同一范围"，暗示 CS2 与之不同 | **两者不冲突，而是"名义值 vs 有效值"**：官方给的是**需求未饱和时的最大半径**，实际有效半径随区内需求上升而缩小。→ **引用纪律**：**可以写"Service range 的单位是米"（C10/C20 结案）**，但**不得写"某医院保证覆盖 7.5 km"**。覆盖分析用**双口径**：官方 range 作上界、自圈 400/600/800 m 作下界。**"抗密度压缩能力随建筑等级上升"这条只有社区一条来源 → 标 `[攻略经验]`，不作机制**<br>✅ **第四轮更新（部分推进 · 拿到机制语义，仍无曲线）**：<br>**(a) 官方给了 `capacity` 的语义** —— `Services` 页（`?action=raw`，**S91**）原文：通信建筑有 **bandwidth capacity 与 range，"describing how many citizens it can service and how far its service reaches"** → **`Service capacity` = 能服务多少市民、`Service range` = 服务能到多远**。这正是"半径会被压缩"的**机制解释**：当半径内的服务需求超过 `capacity` 时，覆盖不可能还是满半径。<br>**(b) 官方字段名确认** —— `Service_building_data_test` 页（**S98**）转储了游戏原始字段 **`Service_coverage_range` / `Service_coverage_capacity` / `Service_coverage_magnitude` / `Circular`** → 三者是**独立的存档参数**，"容量耗尽的建筑半径缩水"在数据结构上完全成立。<br>**(c) 也解释了 S80 的"医院抗压缩"** —— 用 `capacity ÷ 覆盖面积` 算密度上限：Small Medical Clinic 7500 人 / 19.6 km² ≈ **383 人/km²**；Hospital **50000 人 / 176.7 km² ≈ 283 人/km²**…⚠️ **两者同量级，因此"capacity = 人数"这个换算不能直接当压缩公式**（`capacity` 的**计量口径官方仍未定义**）→ **禁止用它推算"多少人口半径缩到多少米"**。<br>**(d) 定量曲线：仍无。** 本轮专门找了压缩曲线/公式（含 mod 侧的 `ModifiedServiceCoverage` 类型、Paradox Mods 的 Service Coverage mod、日文/中文社区），**均未拿到可引用数据** → **`[待验证]` 维持**。<br>→ **替代判据（本轮落地，见 `48` A11/B7）**：① **游戏内该服务的覆盖着色视图（Info view）有没有空洞** = 第一判据；② **官方 `Service range` 换算出"自圈半径下界"** = 第二判据（只看**下限**，不当承诺）；③ **发现空洞时先拉预算滑块到 150%**（官方明文预算改覆盖半径，S91）—— 若拉满预算洞就补上，说明是**容量不足**（对应 `capacity`），不是**几何不够**。 |
| **C24**<br>⚠️ **编号提示**：`48-tuned-thresholds.md` 与用户任务书把本条称作 **"C25"** —— **两条编号指的是同一件事**（Heavy Traffic Ban 与补货）。本文件统一用 **C24**；真正的 C25 是"Extra Garage 性价比"。 | **`Heavy Traffic Ban` 是否影响商铺补货** | 官方 `Policies` 原文只有一句："**Trucks and other heavy vehicles are forbidden from entering the district.** This reduces noise and air pollution and can help traffic congestion. **Highways remain unaffected.**" | 官方**没有说明**这是否会挡住给商铺/工厂送货的卡车，也没说会不会挡住城市服务车辆 | **维持 `[待验证]`**。**给建议时必须写清**："先在一个小区试点，盯该区商铺的备货水平与公司效率有没有掉"。**禁止承诺"挡货车不影响经济"**<br>❌ **第四轮更新：仍未解决，且已确认"官方没有澄清"** —— 本轮拿到**三条负面证据**：<br>**(a) 官方 Wiki 全文检索**（https://cs2.paradoxwikis.com/index.php?search=%22Heavy+Traffic+Ban%22&fulltext=1 ，**S99c**）显示 `"Heavy Traffic Ban"` 在全站**只出现在 3 个页面**：`Policies`（就是那句原话）、`Progression`（只是一个解锁图标）、`Beginner's guide`（一句"建一个带 Heavy Traffic Ban 的区域有帮助"）。**没有任何一条补丁说明或说明性文字解释它对送货的影响。**<br>**(b) 唯一可能给出答案的讨论全部落在 Steam 讨论区**（`Heavy Traffic Ban Policy` 帖，CS2 与 CS1 各一），**Steam 讨论区对本抓取器不可达**（§2e 已确认死路）。<br>**(c) 官方在别处明确区分了"服务车"与"送货车辆"，但语境不同** —— `Roads` 页（**S94**）对 `Pedestrian Street` 的原文是 "only foot traffic is allowed, **apart from service and delivery vehicles**" → 说明**游戏系统里"service vehicles"与"delivery vehicles"是两个被单独识别的类别**，但**这不能推出 Heavy Traffic Ban 豁免它们**。<br>→ **结论：`[待验证]` 维持，且建议停止追查**（唯一可能的出口是请玩家做一次小区试点，或直接向 Paradox 提问）。**处方模板见 `48` §C6 / `41` §12。** |
| **C25** | **`Extra Garage` 升级的性价比** | 官方 `Transportation` 只给"Bus Depot 25 Vehicles / 可升级"，**没有给升级后的车辆数与维护费增量** | **[S81]**（日文 Wiki）："**追加バス車庫が維持費約1.5倍に対し増加車両は1.4倍と微妙に釣り合っていない**"（额外车库维护费约 ×1.5，车辆只 ×1.4，略不划算） | **`[社区实证]` 可信度低**。**使用方式**：可以告诉玩家"**加车优先加线路车辆数（免费）；撞上限时优先考虑第二个 depot，其次才是 Extra Garage**"，但**必须说明这是社区观察，不是官方数值**。**禁止给"×1.5 / ×1.4"这两个数字当作官方数据** |
| **C26** | **`Service range` 数值本身的可信度层级** | 官方 `Service_buildings` 表的 `Service range` 列（Small Post Office 1000 / Post Office 2000 / Small Elementary School 1500 / Small Medical Clinic 2500 / Medical Clinic 5000 / Hospital 7500 / Police Headquarters 10000） | 同一页的 `Cost` / `Upkeep` 列**已被证明与 `Transportation` 页不一致**（见 **C17 更新**）→ **同表其它列的可信度也应打折** | **口径**：`Service range` 可用于**同表内部横向比较**（诊所 < 医院）与**量级判断**（≈2 km / ≈5 km / ≈7.5 km）；**不宜用于精确的覆盖人口计算**。真正做覆盖分析时**以自圈半径为主口径** |
| **C27** | **`Heavy Traffic Ban` / 专业化工业 / 仓库的"是否影响公司经营"未明确项汇总** | 官方对 `Heavy Traffic Ban`、专业化工业的"车辆不走城市道路"适用范围、以及仓库的具体储位/车辆数**都没给完整说明** | — | **登记为待验证清单**：① `Heavy Traffic Ban` 对商铺补货的影响（C24）；② 仓库（Warehouse）的具体储位数与车辆数（1.3.6f1 只确认车辆 3→10）；③ 专业化工业"车辆不走城市道路"是否对**加工厂之间的运输**也成立 |

### 4c. 📌 对已有结论的**更正 / 补充**（不删除旧内容，只在这里登记差异）

> **第一轮（通用机制）的更正 R1–R9 见下；第三轮（实操攻略专题）的更正 R10–R14 在表末。**

| # | 旧结论（出处） | 新结论 | 依据 |
|---|---|---|---|
| **R1** | `10-game-mechanics.md` §7.1 / `40-number-tables.md` §5.1：税收"按学历分级 / 按产品类型分级，区间 −10%~30%"——**没有说明税基是什么** | **补充关键缺口**：**住宅税基 = 市民的月度工资**（且只对超过 `Residential Minimum Earnings` = **₡1400/月**的部分征收）；**商/工/办税基 = 公司的月度利润**。→ 由此可推导：**Highly Educated 市民的应税基础 ≈ Uneducated 的 13 倍**（₡1300 vs ₡100） | S17（Economy 页）、S16（Citizens 页，1.3.3f1 工资与起征点） |
| **R2** | `10-game-mechanics.md` §6.3 / `40-number-tables.md` §5.9：租金公式与"低密度最容易被地价推高租金" | **补全升级机制**：`Rent = (LandValue + (ZoneType × Building Level)) × LotSize × SpaceMultiplier` 出自 **S37**；且**建筑升级 = 租户能否付满 `upkeep`**（付满→状况按**固定步长**上升→升级；付不起→**同幅下降**→倒塌）；**"High Rent" 通知改为基于家庭收入判定** → **税率↑ 会通过"付不满 upkeep"把税基自己吃掉**（这是"没有官方甜蜜点但机制上必然存在最优税率"的完整解释） | **S37（一手出处）** |
| **R3** | 之前任何地方都**没有**记录三条密度—税收关系 | **新增（本轮最有价值的机制发现）**：官方 Zoning 页明文 **①"Lower density … provide more taxes from each one"；②"High density … provide fewer taxes from each one"；③Low Rent Housing "The lower rent provides lower tax income as a result."** → 官方**故意**在"人均税收"与"人口容量"之间做了反向权衡 | **S50（Zoning 页）** |
| **R4** | `SKILL.md` §2 用地与岗位结构表只提醒"注意城外通勤者不纳税" | **补充官方原文与算法化**：commuters **"do not pay tax at all to either city"**；且**住城内/城外上班的居民也不缴税**；Commuter Wage Multiplier = 1.1。→ 需要新增可计算指标 **`本地劳动力自给率 = min(1, 本地可就业人口 / 岗位数)`**（见 `46` T3） | S16（Citizens 页，1.3.3f1）、S4（Patch 1.1.X） |
| **R5** | `10-game-mechanics.md` §5.1 幸福度因子表（10 项）成本轮复核**一致** | **补充三条 1.6.x 变更**：① **1.6.2f1 起 "Garbage now has more effect on citizens' happiness"**；② **1.6.2f1 起市民的幸福度/购物/休闲决策从 `wealth` 改为 `income`**（→ 任何用 wealth 做代理的算法都要改）；③ **1.6.0f1 起市民不再"永远去库存最多的店而忽略距离"** | S9（Patch 1.6.X） |
| **R6** | `40-number-tables.md` §1.1 depot 维护费直接采用 `Service_buildings` 表 | **需补脚注**：同 Wiki 的 `Transportation` 页给出**系统性 0.75 倍**的另一组值 → 见 **C17** | S15 vs **S52** |
| **R7** | `20-roads-and-traffic.md` / `40-number-tables.md`：道路表有车道/限速/造价/维护/噪音系数 | **补充可用字段**：官方表同时给出 **`Air pollution factor`**，且 **碎石路（Gravel Road）与步行街（Pedestrian Street）的噪音系数是 2×，高于双车道柏油路的 1×**——这与直觉相反，但是官方数值，可直接写进噪音暴露算法（`46` T5） | **S51（Roads 页，表标注 1.6）** |
| **R8** | 之前无记录 | **新增两条"办公可被基础设施直接加成"的官方数值**：**Airport = +3% Office Efficiency（全城）+5% Attractiveness**；**International Airport = +10% Attractiveness / +10% Interest in University Education / +10% Demand for Software**；**ChirpX Space Centre = +10% Software / +10% Electronics 需求 / +60 Indoor Recreation**。→ 办公区是**唯一能用市政建筑直接加效率**的分区 | **S52（Transportation 页）** |
| **R9** | 之前无记录 | **新增**：1.1.6f1 官方 workaround 证实 **办公税率 30% 可在一个游戏月内清空全部办公公司**；反向使用即"把高税率当拆迁工具"。同时 1.6.0f1 起**办公商品可从外部连接购买**、1.6.2f1 修复"办公无法进口 Software" → **办公区的供应链约束已被放松** | S4（Patch 1.1.X，1.1.6f1 段）、S9（Patch 1.6.X） |

> **【第三轮（实操攻略专题，2026-10-13）对已有结论的更正 R10–R15】**

| # | 旧结论（出处） | 新结论 | 依据 |
|---|---|---|---|
| **R10** | `SKILL.md` §2 用地表脚注 / `45` §B5 / `00-sources.md` C10：**"Carto 的 `Service range` 官方未给单位，禁止断言'这是米'"** | ~~禁止断言是米~~ → **单位就是米**。三条证据：**(a)** 官方 `Roads` 页确认 "snaps every **8 meters**"（1 格 = 8 m）→ 游戏内长度量纲以米计；**(b)** 同一张官方 `Service_buildings` 表中 `Radio Mast` = 1 km、`Server Farm` = 2 km、`Telecom Tower` = 5 km、`Radio Mast Wireless Network Antenna` = 250 m 与裸数值（Small Post Office 1000、Small Medical Clinic 2500、Hospital 7500）**混排在同一列**，裸数值量级与米制自洽；**(c)** 社区独立来源把 2500 读作"约 2 km"。<br>⚠️ **但不得写"某医院保证覆盖 7.5 km"** → 见 **C23**（该值是"需求未饱和时的最大半径"） | 官方 [Roads](https://cs2.paradoxwikis.com/Roads)（`?action=raw`）、官方 [Service_buildings](https://cs2.paradoxwikis.com/Service_buildings)、社区 [S80](https://csl2wiki.wicurio.com/index.php?%E5%8C%BB%E7%99%82%E3%83%BB%E8%91%AC%E5%84%80)（**S71/S72/S73 同批核对**） |
| **R11** | `SKILL.md` §2 服务与财政：「预算滑块是**全局效率/成本权衡**」——**只说了一半** | **补充**：官方明文预算滑块**同时改变 "the range of the service coverage"**（服务覆盖半径），并改变服务容量（垃圾车、警车、学位等）。→ 修正为「预算滑块 = **全局成本杠杆 + 容量杠杆 + 覆盖半径杠杆**；**发现覆盖不足时先拉预算再盖楼**」 | 官方 [Services](https://cs2.paradoxwikis.com/Services)（`?action=raw`，**S70**） |
| **R12** | `SKILL.md` §2 / `45` §A6：**没有货运行**；`20-roads-and-traffic.md` 只有零散的货运描述 | **新增整节"货运与产业链"**（6 条硬动作）：① 货运终端**不开线也能当配送中心**（官方原文 "Even with no cargo lines… working like a distribution center"）；② 终端**必然产生大量卡车** → "crucial to prioritize the road connections"；③ **铁路运货比卡车到外部连接更便宜更快**，Cargo Harbor 可升 **Railway Connection**；④ **本地销售永远更赚** + **运输成本随路网距离上升** → **缩短产业上下游距离 = 直接涨税**；⑤ `Heavy Traffic Ban` 隔离重车（高速不受影响）；⑥ **仓库是产销缓冲**（"keeps production going"）。储位：火车终端/转运站/港口 **15.5 kt**、机场货运 **800 t**、货船 **1000 t** | 官方 [Transportation](https://cs2.paradoxwikis.com/Transportation)、[Zoning](https://cs2.paradoxwikis.com/Zoning)、[Traffic](https://cs2.paradoxwikis.com/Traffic)、[Policies](https://cs2.paradoxwikis.com/Policies)（全部 `?action=raw`，**S71/S72/S73**） |
| **R13** | `SKILL.md` §2 用地表 / `45` §C4：**没有"不挑资源的专业化工业"这条** | **新增**：官方 Zoning 表里 **`Livestock Farming`（M3）与 `Stone Mining`（M3）是唯二 `Required Resource` 为空的专业化工业**；且 **专业化工业建筑永远不会 abandoned**、**其车辆不走城市道路**。污染等级：**农业类（Livestock/Grain/Vegetable/Textile）= 噪声 Low**，**林业/石/煤/矿/石油 = Medium**（后四者还带地面+空气污染）；`Oil Drilling` **火灾风险高于其它** | 官方 [Zoning](https://cs2.paradoxwikis.com/Zoning)（`?action=raw`，**S71**） |
| **R14** | `SKILL.md` §0 因果链有"交通效率 → 可达性 → 公司效率↑"，但**没有任何"距离扣利润"的公式**；`45` §D4 只笼统写"进口会产生额外卡车流量" | **补充官方原文**：公司付**原料运进来 + 成品运出去**的钱，**"the cost of resources they transport increases the further away they are delivered"**；**"Transporting resources and goods out of the city is costly and can greatly reduce the profitability of companies"**；且 **"Importing goods does not affect the revenue of these industries, but does affect gameplay by requiring a well-developed roadway grid"**（**进口的代价全在路网，不在钱上**）。→ **`税收与幸福度` 表新增第 9 条** | 官方 [Traffic](https://cs2.paradoxwikis.com/Traffic)、[Zoning](https://cs2.paradoxwikis.com/Zoning)（**S71**） |
| **R15** | `SKILL.md` §2 服务与财政：「depot/车站维护费在 Wiki 上有两套数（**差 0.75 倍，疑为难度模式差异**）」 | ~~疑为难度模式差异~~ → **归因被推翻**：两页的数值**本身就是两套不同的数**，且**不是统一的 0.75 倍缩放**（Taxi Depot 是 0.467 倍、方向都反了；Small Bus Station、Cargo Train Terminal、Cargo Harbor 各自比例不同）。**以 `Transportation` 页（与官方补丁说明一致）为准** → 见 **C17 更新** | 官方 [Transportation](https://cs2.paradoxwikis.com/Transportation)（`?action=raw`，**S72**）、官方 [Service_buildings](https://cs2.paradoxwikis.com/Service_buildings)（`?action=raw`） |

---

## 五、给引用者的硬性规则（写作时请遵守）

1. **每条数值结论必须带 `（来源：URL，版本 X）`**，版本号缺一不可。
2. 涉及以下任一主题时，**必须确认玩家当前版本 ≥ 1.1.5f1**，否则整段策略不适用：税率、租金、地价、需求、公司破产、建筑升级、补贴。
3. 涉及以下主题时，**必须确认版本 ≥ 1.3.6f1**：工业噪音半径、货车流量、仓库车辆数、专业化加成上限、City Hall/Central Bank 加成。
4. 涉及以下主题时，**必须确认版本区间**：自行车（1.4.2f1 引入，1.5.4f1 大幅削弱）。
5. 无法确证的数值一律写 **"待验证"** 并列出冲突双方，**不要给出精确数字**。
6. 区分**游戏机制**（有官方来源）与**社区经验/现实规划标准**（无游戏内来源），两者不得混写。参见 `90-web-vs-book-notes.md`。

### 第二轮（经济/幸福度专题）新增的规则 7–14

7. ~~**引用 depot / 车站 / 港口的维护费时，必须带难度前提**（见 **C17**：同 Wiki 两处数值系统性差 0.75 倍）。不确定难度时，让玩家在游戏内点开建筑面板读一次。~~
   → **第三轮更正（见 C17 更新 / R15）**：**"难度模式"归因已被推翻**。`Service_buildings` 表与 `Transportation` 页是**两套不同的数**，且**不是统一比例**。**引用 depot/车站/港口维护费时以 `Transportation` 页（`?action=raw`）为准**，或让玩家在游戏内建筑面板读一次。**不要再写"差 0.75 倍是因为难度"。**
8. **禁止给出"最优税率"数字**（见 **C16**）。只允许用机制式表达：`短期收入 ↑ / 升级速度 ↓ / 需求 ↓` 三项权衡。唯一可用的经验边界是 **办公税率 30% ≈ 强制清退（C18）**。
9. **凡涉及"每格税收""单位面积税收产出"——一律不得给出数字**。官方没有，本轮也未找到可复现的社区实测（见 `45` §C3）。只能用 `46` 里的**相对指数**，并标注 `[代理]`。
10. ~~**"Service range 的单位是米"这句话禁止出现**（C10 + **C20**：同表内"km 行"与"裸数值行"并存）。~~
    → **第三轮更正（见 C20 结案 / R10）**：**"单位是米"现在可以写**（三条证据：官方 1 格 = 8 m；同表 km/m/裸数值混排且量级自洽；社区独立读作"约 2 km"）。
    **但新的禁止项是**：**不得写"某建筑保证覆盖 X 米/公里"** —— 该数值是**需求未饱和时的最大半径，会随区内人口密度上升而缩小**（**C23**）。覆盖分析用**双口径**（官方 range 上界 + 自圈半径下界）。
11. **禁止设"幸福度 < X 就报警"的绝对阈值**——官方未公布任何幸福度阈值（`45` §B4）。
12. **福利不是城市支出**（**C21**）：城市预算里既没有政府补贴收入，也不承担养老金/失业救济/家庭津贴。不要提"削减福利"。
13. **涉及以下主题时必须确认版本 ≥ 1.6.2f1**：垃圾对幸福度的影响强度、市民幸福度/购物/休闲用 `income` 而非 `wealth`。
     **涉及以下主题时必须确认版本 ≥ 1.6.0f1**：市民是否"只看库存最多的店"、寻路距离上限按出行目的分设、办公商品能否从外部连接购买。
14. **不要把"岗位数"当"税收基础"用**（`45` §A5）：城外通勤者**完全不缴税**，住城内/城外上班的居民**也不缴税**。
     必须先算 `本地劳动力自给率 = min(1, 本地可就业人口 / 岗位数)`，再谈税收潜力。

### 第三轮（实操攻略专题）新增的规则 15–22

15. **`Service range` 的单位是米，但它是"名义最大半径"**（**R10/C20 结案 + C23**）。可以写"诊所 ≈2 km、医院 ≈7.5 km"作为**量级**；**不得写"保证覆盖"**；覆盖分析**必须用双口径**（官方 range 上界 + 自圈 400/600/800 m 下界），并在输出里写清哪个是哪个。
16. **同一张 `Service_buildings` 表的** `Cost` / `Upkeep` / `Service range` **列都要打折看待**（**C17 更新 + C26**）：该表的费用列已被证明与 `Transportation` 页不一致且**不是统一比例**。费用类数值优先用 `Transportation` 页；`Service range` 只用于**同表横向比较与量级判断**，不用于精确覆盖人口计算。
17. **凡涉及"减少卡车 / 货运优化"的建议，必须落到两个可验证机制之一**：**① 缩短实际路网距离**（官方：运输成本随距离上升，直接扣公司利润）；**② 切换运输方式**（铁路/船替代卡车到外部连接）。**禁止写"优化物流"这类空话**（`47` §2.2）。
18. **凡建议"加密 / 升密度 / upzoning"，必须同时给出交通侧配套**（官方明文：High Density **generally cause higher traffic, and cause congestion on small roads**；且低密度 **"needs less services"**）。**只提密度不提交通的建议一律不合格**（`48` A6）。
19. **单行道建议必须先验"双向可达"**（官方明文：**服务车辆不能逆向行驶**；**商/工业送货不足会"停止有效运营"** → 公司利润=税基受损）。→ 凡涉及单行道的处方，必须附一句"逐地块确认送货能到"（`48` A4）。
20. **凡涉及"服务覆盖不足"的处方，第一手段是调该服务的预算滑块**（官方明文预算会改变 **"the range of the service coverage"**），**不是先盖楼**（`48` A2）。
21. **`Heavy Traffic Ban` 对商铺补货的影响未明确**（**C24**）→ 凡推荐该政策必须附"先在一个小区试点，盯该区商铺备货水平与公司效率"。
22. **攻略站（可信度 C）的数字一律不得作为机制引用**：`Extra Garage` 的"×1.5 / ×1.4"、日文 Wiki 的"5–10 个站台"、"大站制 10 站 + 5 站"、公交专用道的任何收益百分比 —— 全部**只能作为"有机制依据的处方方向"**，不得承诺量化收益（`47` §6 规则 2）。

---

## 六、【第四轮（2026-10-13）官方数值表系统榨取】新增来源 S90–S99c

> 本轮方法论：**`?action=raw` 已是标准动作**，新增两条经验：
> ① **大页面必须按 `&section=N` 切片**（`Service_buildings` 单次全文会在约 100 KB 处截断，截断点落在正文中间）；
> ② **同名标题会让 `section=N` 错位**（`section=20` 与 `section=21` 都返回了 Police 段）→ **以返回内容为准，不要盲信节号**。
> ③ **`Special:Search` 的 `?fulltext=1` 可以直接当"某关键词在全站出现过没有"的判据**（本轮用它证明官方从未澄清 Heavy Traffic Ban）。

### 6a. 官方 Wiki 一手数值表（全部 `?action=raw` 实抓）

| # | 页面 | 版本标注 | 本轮拿到什么 | 可信度 |
|---|---|---|---|---|
| **S90** | `Service_buildings`（**逐节切片，拿到 24 段全部数值表**） | 页头 1.5；**所有数值表 `{{SVersion\|1.6\|table}}`** | **全部服务建筑的 12 列官方表**：`Service range / capacity / magnitude` + **`Noise pollution` / `Air pollution` / `Ground pollution` / `Electricity consumption` / `Water consumption` / `Garbage accumulation` / `Workplaces` / `Max. needed education` / `Evening shifts` / `Night shifts`**。另含 `Circular`（原始字段转储页）、通信 `Range + Network Capacity + Penetrate Terrain`、电力 `Goods consumption + Electricity production + maxWind + maxGroundWater + Battery capacity + activationThreshold`、垃圾 `Garbage storage capacity + Garbage trucks + Garbage processing capacity`、消防 `Fire engines + Fire helicopters + disasterResponseCapacity + fire vehicleEfficiency`、停车场 `Comfort + garageMarkerCapacity + defaultProbability`、道路 `Maintenance types + Maintenance vehicles` 等专属列 | **O1（自动生成，最高）** |
| **S91** | `Services` | `{{Version\|1.0}}` | **本轮最有价值的单个数值**：**电/水费率每偏离 100% 1% 的弹性**（低于 100%：用电 **+0.2%** / 公司效率 **+0.2%** / 幸福度 **+0.05**；高于 100%：用电 **−0.4%** / 公司效率 **−0.4%** / 幸福度 **−0.1** → **惩罚是收益的 2 倍**）。另：**`capacity` = 能服务多少市民、`range` = 服务到多远**（通信段原文）；**垃圾产生量随建筑等级与学历上升而下降**；**Welfare Office 在 Happiness 低于一半时生效**（官方唯一的幸福度分界数字）；**进口服务没有被动覆盖效果**；**监狱是生产设施**；**警车默认全城巡逻（除非用区域限制）** | **O2（机制可信，数值可能滞后）** |
| **S92** | `Economy` | `{{Version\|1.0}}` | **服务费默认值表**（电 0.2 / 水 0.3 / 医疗 ₡100 每住院市民每月 / 垃圾 1.0 / 教育 ₡50·100·200）；**服务贸易价目表**（电进口 ₡5000/MW、出口 ₡2500/MW；水 ≈₡0.1/₡0.05 per m³；污水只能出口 ≈₡0.1/m³；警务 ₡50/市民、医疗 ₡25、殡葬 ₡25、消防 ₡50、垃圾 ₡5，**全部按人口计价**）；**贷款 = 月付借出额的 2.3%–20%**、上限 ₡100,000–₡26,100,000、City Hall −1% / Central Bank −2%；**效率因子表**（含 `City Production Specialization` 默认上限 **115% @ 10 kt**）；完整产业链输入输出表 | **O2** |
| **S93** | `Progression`（`Milestones` 为重定向） | `{{Version\|1.1.5f1}}` | **20 级里程碑完整表**（奖金 ₡25,000→₡500,000 / 发展点累计 1→232 / 扩张许可 3→432 / 贷款上限 ₡100,000→₡4,000,000 / 逐级解锁分区·政策·服务·功能）+ **官方给出的 1.1.5f1 前后奖金对照表**（M1 ₡600,000→₡25,000，M20 ₡7,000,000→₡500,000）+ 发展树 1/2/4/8 点 + 地图 441 格 × 0.4 km² + 购地成本公式 | **O2** |
| **S94** | `Roads` | 正文 1.0；**道路表 / 停车场表 `{{SVersion\|1.6\|table}}`** | **全道路表**（限速三口径：欧洲显示值 / **内部值** / 北美显示值；车道数；XP **每 112 m / 14 格**；平地·高架·隧道三套造价与维护；**噪音与空气污染系数**）；**所有非高速道路 = 40 MW 低压输电线 + 水与污水管**；环岛 ₡200/500/1000/1500；标高步进 1.25/2.50/5.00/10.00 m；平行偏移 0.25–12 格；**每 8 m 吸附（1 格 = 8 m 的原始出处）**；**停车场表含 `garageMarkerCapacity`（自动停车楼 416、地下 100、地下自行车库 400）与默认政策 `Parking Fee: 10.0`**；`Road Maintenance Depot` 数值与附属物清单 | **O1（表）/ O2（正文）** |
| **S95** | `Policies` | `{{Version\|1.0}}` | 三级政策全表 + **所需里程碑**；**`Energy Consumption Awareness` = 用电 −5%**（全部政策里唯一的数值效果）；`Roadside Parking Fee`（区域·M5·₡1–50）；`Parking Fee`（建筑·₡1–50）；`Heavy Traffic Ban`（M6）原文；`Gated Community`（M7）"**不影响城市服务**" | **O2** |
| **S96** | `Citizens` | 正文 1.0 + **1.3.3f1 工资** | 五档工资 ₡1500/1800/2100/2400/2700；起征点 ₡1400；`Commuter Wage Multiplier` **1.1**；家庭津贴 ₡400 / 养老金 ₡1200 / 失业救济 ₡800 最长 10 天；**幸福度 10 因子表（无权重）**；年龄四段寻路偏好（Teens 最便宜 / Adults 最快 / Seniors 最舒适）；**学历同时降低用水用电与垃圾产生**；学历—学校—学费对应表；犯罪目标选择规则 | **O2** |
| **S97** | `Zoning` | `{{Version\|1.0}}` | 分区地块尺寸范围 + 解锁里程碑（两张表：有主题 / 无主题）；专业化工业表（里程碑 / 所需资源 / **噪声·地面·空气污染等级**）；**建筑等级 1–5 的逐项效果**（住宅每户水电子升级下降、3/5 级增加公寓数；商业/工业/办公单位产出水电下降、垃圾与污染减少） | **O2** |
| **S98** | `Service_building_data_test` | **无版本标注**（静态转储） | **游戏原始 prefab 字段名**：`Service_coverage_range` / `Service_coverage_capacity` / `Service_coverage_magnitude` / **`Circular`** / `Telecom_need` / `Workplace_complexity` / `maintenanceDuration` / `Building_level` 相关字段 → **确认这三个覆盖参数是独立存档字段，且覆盖形状有"圆 / 非圆"之分**。⚠️ **数值与 S90 的 1.6 表冲突**（公园与地标完全一致；医疗/消防/警务/小学系统性偏小）→ **C28** | **O3（字段名可信；数值疑为旧版本）** |
| **S99** | `Special:AllPages` | — | 全站页面名清单（挑"可能有数值表"的页面的依据）。**确认存在的相关页面**：`Building level`、`Efficiency`、`Speed limits`、`Parking`、`Parking Spaces`、`Supply Chains`、`Development Tree`、`Milestone(s)`、`Subway Station Measurements`、`Landmark Buildings`、`Signature buildings`、`Companies`、`Commercial`、`Industrial`、`Residential`、`Crime`、`Health`、`Education`、`Garbage`、`Healthcare`、`Electricity`、`Sewage`、`Pathfinding`、`Info views` | **O1** |
| **S99b** | `Commonly units in the game` | — | ⚠️ **内容极少**：只有 `Time :uint`（1 分钟 ≈ **182.0444…**、90 分钟 = **16384**）。**没有任何长度/服务半径单位说明** → **C20 的单位结论仍只能靠原三条证据** | **O1（但无内容）** |
| **S99c** | `Special:Search`（`?search=%22Heavy+Traffic+Ban%22&fulltext=1`） | — | **全站全文检索**：`"Heavy Traffic Ban"` 只出现在 **3 个页面**（`Policies` / `Progression` / `Beginner's guide`），**没有任何补丁说明或澄清** → **C24 的负面证据** | **O1** |

---

## 七、【2026 年官方更新日志采集】新增来源 P1–P11

> 采集范围：**只收 2026-01-01 之后**。全部为**官方通告** ⇒ 可信度**最高**（等级 **O1**）。
> 逐条内容与对 skill 的影响见 **`references/101-2026-official-patch-log.md`**。

| 编号 | 来源 | 版本 / 日期 | 内容要点 | 等级 |
|---|---|---|---|---|
| **P1** | Paradox 官网 · Patch 1.5.4f1 First Frost | 2026-02-18 | 自行车出行 **−80%**；死亡潮修正（此前集中在 0–6 点）；**Easy 模式此前约 80% 不老死**；地形工具预设 | **O1** |
| **P2** | Paradox 官网 · Spring Cleaning 1.5.7f1 | 2026-04-29 | **公交繁忙站点永久上客卡死**修正；**混合住宅压制商业/中密度需求**修正；**非高速路无法连通城外**修正；**商业需求改按平均备货水平**；教育系统平衡；`Urban Cycling Initiative` **20% → 50%**；**`Historical Building` 选项**；生产统计改为长时段采样 | **O1** |
| **P3** | Paradox 官网 · Patch 1.5.9f1 Morning Dew | 2026-05-27 | **掉头成本**（此前合法掉头为 **0**）大幅提高；**变道改为更早**（高速出口最明显）；水电费 bug；专业工业货车滞留；酒店顾客数**午夜清零** | **O1** |
| **P4** | Paradox 官网 · City Corner #2 | 2026-02-12 | 死亡潮机制解释；自行车改动说明；**当时仍在调查**：寻路、最后一刻变道、掉头、**火车卡城市边界** | **O1** |
| **P5** | Paradox 官网 · City Corner #7 Morning Dew | 2026-05-26 | **掉头成本为 0** 的机制原文；**变道过晚**的机制原文（"especially noticeable with highway exit behavior"） | **O1** |
| **P6** | Paradox 官网 · City Corner #11 Autumn Breeze | 2026-08-20 | 垃圾车逻辑与**幸福度**；**公司租赁按资源紧缺度排序**；**住宅需求改为考虑城市规模**（此前大城市需求塌陷）；**幸福度/购物/休闲改用收入而非财富** | **O1** |
| **P7** | Paradox 官网 · City Corner #12 Collected Questions | 2026-09-03 | 官方点名玩家影响模拟的三大间接手段（**taxes / subsidies / transportation networks**）；**寻路仍是 CPU 性能主要挑战**；修 bug 方法论 | **O1** |
| **P8** | Paradox 官网 · Office Evolution & City Stations | 2026-03-18 | **道路分区开关（zoning toggle，可移除单侧/双侧）**；**`Iceflake Arena` 在 2 km 半径内提升 attractiveness 与 well-being**；Encyclopedia | **O1** |
| **P9** | Paradox 官网 · 新闻索引 | — | 用于**确定 2026 年全部官方帖**（防止漏采） | **O1** |
| **P10** | 官方 Wiki · `Patch 1.6.X` | 1.6.0f1 2026-06-22 / **1.6.2f1 2026-09-15** | ⭐ **1.6.0f1**：**寻路距离上限按出行目的分设**（工作/上学/购物/休闲）；**购物不再无视距离**；掉头成本回调；办公可从城外购货；商业需求下调；**游戏内等高线开关**；地形材质可绘制。**1.6.2f1**：幸福度用**收入**；住宅需求**考虑城市规模**；**垃圾影响幸福度加强**；公司租赁优先级；青年延迟搬出（年龄金字塔）；**政策滑块取整不一致**；面板不显示预算对工资的影响 | **O1**（转载官方论坛由官方账号发布者） |
| **P11** | 官方 Wiki · `Developer_diaries` | — | **全部 City Corner 期号 / 日期 / 主题索引**（含 #1–#12），用于版本时间线 | **O1** |

> ⚠️ **已知缺口**：**`1.5.8f1` 与 `1.5.10f1` 的补丁说明正文未取到**（仅确认版本号存在）。
> ❌ **未能采集玩家侧内容**：官方论坛本体对所有抓取返回 JS 挑战页，RSS 端点 403
> —— 因此**本文件没有任何"最低可信度"的玩家来源**（详见 `101` §7）。

### 6b. 【第四轮】尝试但**未采信**的来源（新增死路 + 教训）

| 来源 | 结果 | 教训 |
|---|---|---|
| `https://cs2.paradoxwikis.com/index.php?title=Budget&action=raw` | **HTTP 404** | **不存在 Budget 页**。预算内容在 `Services#Budget` / `Economy` / `Progression`（"Service Budgets" 是里程碑解锁项）。**不要再找** |
| `https://www.paradoxinteractive.com/games/cities-skylines-ii/features/city-services` | **HTTP 404** | 猜的 URL。官方 Feature Highlight 可用编号只有 **#3 / #4 / #9**（S22–S24） |
| `https://ngabbs.com/read.php?tid=38512883`（NGA 天际线 2 改功能区影响收入讨论） | **HTTP 403「访客不能直接访问」** | **NGA 需登录 → 不可达，加入死路清单** |
| `https://www.yystv.cn/n/1012334`（游研社「测试游戏里税收对城市GDP增长和财政收支的影响」） | HTTP 200 但**正文为空** | 标题极相关（唯一的"税收实测"命中），但**站点正文抓不到 → 未采信任何内容**。**该站加入不可达清单** |
| `https://youtubetranslate.net/...`（"I Tried Running a 0% Tax City… and It Actually Worked"） | HTTP 200，**只拿到前 1/3 字幕** | 内容是**挑战视频**（0% 税率下靠 15 台风机 + 变压器站外送 ≈ **₡72,000/月**，扩到 160 MW 后 ≈ **₡150,000/月**），**不是税率受控实验** → 只作 **C29** 的旁证，**不得当作"税率甜蜜点"证据** |
| `https://www.modscities2.com/cities-skylines-2-service-coverage/` | 第二轮已确认 **HTTP 403（Cloudflare）**；本轮搜索再次命中但**未重复尝试** | 站点整体 403（与 `chillplacegaming.com` 同类）。**C23 的"覆盖可视化 mod"线索就此中断** |
| `https://ps1ke.github.io/Cities-Skylines-2-Modding-Guide/Game/Buildings/ModifiedServiceCoverage/` | 第三轮已确认**正文被 60 KB 导航树吃光**（4 次失败） | 站点结构问题 → **维持死路**。**但本轮找到了替代**：官方 `Service_building_data_test`（S98）给出了等价的原始字段名 |

### 6c. 【第四轮】新增冲突与待验证：C28–C31

| 编号 | 冲突点 | 说法 A | 说法 B（及 C） | 处理建议 |
|---|---|---|---|---|
| **C28** | **服务覆盖数值 / 维护费到底该信哪一套** | **[S90] `Service_buildings`（`{{SVersion\|1.6\|table}}`）**：Hospital range **7500** / Fire Station **10000** / Police HQ **10000** / Medical Clinic **5000** / Police Station **5000** / Fire House **5000** / Elementary School **3500**；Upkeep Hospital **₡225.0K**、City Hall **₡80.0K**、Bus Depot **₡31.0K** | **[S98] `Service_building_data_test`（无版本标注，疑为 1.0.x 转储）**：同一批建筑分别是 **5000 / 5000 / 5000 / 3500 / 3500 / 3500 / 3000**，Upkeep 为 **₡450K / ₡160K / ₡62K**（**多数恰好是 A 的 2 倍**）。<br>**[S72] `Transportation` 页**：Bus Depot Upkeep **₡23,250**（= A 的 0.75 倍）。<br>**公园与地标三类：A 与 B 完全一致。** | ✅ **裁定**：**覆盖数值与造价一律以 `Service_buildings`（S90，标注 1.6）为准**；[S98] **只用于取字段名与 `Circular` 语义**。**维护费**目前存在**三套数**（S90 / S72 / S98，比例约为 1 : 0.75 : 2）且**不成统一比例** → 维持第三轮纪律：**以玩家在建筑面板读到的一次为准**，或引用时**同时给出两个来源**。⚠️ **"0.75 倍 = 难度模式"的旧假设已彻底作废，不要再复活**。→ 覆盖 **C17 / C26** |
| **C29** | **"0% 税率也能盈利"是否说明税率无关** | **[S99d/视频]**：0% 税率城市靠**卖电**（15 台风机 + 变压器站外送 ≈ **₡72,000/月**；160 MW 后 ≈ **₡150,000/月**）保持盈利 | 官方 `Economy`：**税收是"城市主要收入之一"，但不是唯一**；且 1.1.5f1 起**政府补贴已移除**，卖电/服务贸易成为合法收入源 | **不冲突**：该视频证明的是"**有替代收入源时，0% 税率在早期可行**"，**完全没有测税率与建筑等级/需求的梯度关系** → **不得作为 C16 的证据**。可信度 **低**（视频，无面板对照），仅登记 |
| **C30** | **税收在哪个里程碑解锁** | **[S92] `Economy` 页**："Taxation is unlocked at **Milestone 2**" | **[S93] `Progression` 页**：**Taxation 排在 Tiny Village（第 1 级）的解锁列表里**；且页内 1.1.5f1 变更表写 "Taxation（unlocks at **Tiny Village**, before Small Village）" | **以 `Progression` 为准**（该页版本标注是 1.1.5f1，且明确写了"改动后"）：**1.1.5f1 起税收在第 1 级里程碑（Tiny Village）解锁**；`Economy` 页的"Milestone 2"是 1.0 时代口径。→ 引用"税收何时可用"时必须带版本 |
| **C31** | **专业化工业的解锁里程碑** | **[S93] `Progression`**：Livestock / Stone / Grain / Forestry **开局即解锁**；Vegetable、Coal = 第 1 级；Textile = 第 2 级；Ore = 第 3 级；Oil = 第 4 级 | **[S97] `Zoning` 表**：Livestock **3**、Stone **3**、Grain **4**、Vegetable **5**、Textile **6**、Forestry **4**、Coal **5**、Ore **7**、Oil **8** | **不冲突，是两种口径**：`Zoning` 表是**1.0 时代的"最早可解锁里程碑"**，`Progression` 是**1.1.5f1 之后的实际解锁时机**（该页有专门的变更表）。→ **一律以 `Progression`（1.1.5f1）为准**；引用 `Zoning` 表时必须注明"1.0 口径，已被 1.1.5f1 提前" |
| **C32** | **Central Bank / City Hall 的贷款利息效果** | **[S90] `Service_buildings` 表**：City Hall **−5% 城市服务基础维护费 / −15% 服务进口成本**；Central Bank **−50% Loan Interest（全城）/ +1 Happiness Tax Tolerance** | **[S92] `Economy` 页**：利率 **City Hall −1% / Central Bank −2%**（百分点口径）。**[S91] `Services` 页**：Central Bank 的作用是"**降低进口成本、提高出口利润**" | **三处口径不同（百分点 vs 百分比 vs 功能描述）**。→ **引用时写"具体数值让玩家在建筑面板读一次"**；**不得把三个数混着用**。`Service_buildings` 表的写法（`−50% Loan Interest`）与 `Economy` 的"−2%"**不可能是同一个量**，最可能是"利率 −2 个百分点"与"利息支出 −50%"两种量纲 |
| **C33-verify** | **主控独立复核：电/水费率不对称弹性**（第四轮追加） | — | 主控用 `web_fetch` 抓官方 [`Services`](https://cs2.paradoxwikis.com/index.php?title=Services&action=raw) **正文，逐字读到**：<br>"Every 1% below 100% increases Electricity Consumption by **+0.2%**, Company Efficiency by **+0.2%** and Citizen Happiness by **+0.05**. Every 1% above 100% decreases Electricity Consumption by **−0.4%**, Company Efficiency by **−0.4%** and Citizen Happiness by **−0.1**." | ✅ **逐字一致，结论成立**（惩罚恰为收益的 2 倍）。<br>⚠️ **但主控补了一条 agent 未写全的限制**：官方**只给了"公司效率"的增减，没有给"利润"的净变化**，而官方同页明说这两项费用 **"paid by citizens and companies alike"** → 降费率会让公司多用电（+0.2%/pt）而多付钱，**净利方向取决于"收入随效率的放大系数"，官方未给**。<br>**⇒ 引用纪律：只能说"涨费率的惩罚是降费率收益的 2 倍""100% 是中性基准"；不得断言"降费率一定涨利润"。** 已按此改写 `SKILL.md` §2。 |
| **C34-verify** | **主控复核：`Service range` 数值（第三轮已做，此处并存）** | — | 见上方 **C20-verify**：官方 `Service_buildings` 原文读到 `Small Post Office` 1000.0 / `Post Office` 2000.0 / `Small Elementary School` 1500.0，同表 `Radio Mast` Range 列写作 "1 km"、"Server Farm" "2 km" | ✅ 一致 |

### 6d. 【第四轮】给引用者的新增硬性规则 23–30

23. **`Service range` / `Service capacity` 有官方语义**（**S91**）：`range` = 服务能到多远；`capacity` = 能服务多少市民。**引用覆盖能力时必须同时给这两个数**，不能只给半径（C23）。
24. **`Service magnitude` 官方从未解释单位** → **只能同表横向比较**，**禁止换算成百分比或人数**。
25. **服务建筑的费用类数字（Cost / Upkeep）现在有三套官方来源且不成比例**（**C28**）→ 引用时**必须注明来源页**，或直接让玩家读建筑面板。**不得再提"0.75 倍 = 难度"**。
26. **电/水费率的弹性是不对称的**（**S91**）：涨 1% → 公司效率 **−0.4%**、幸福度 **−0.1**；降 1% → 公司效率 **+0.2%**、幸福度 **+0.05**。→ **"涨水电费换财政收入"默认是负和操作**，只有目标是**压用电量/用水量**时才成立。
27. **进口服务不提供被动覆盖**（**S91**）：`Import City Services` 只能补"事件响应"，**补不了覆盖空洞**。→ **不得建议"用进口服务解决覆盖不足"**。
28. **1.1.5f1 起里程碑奖金被砍掉 90% 以上**（M1 ₡600,000 → ₡25,000，**S93**）→ **任何"靠里程碑奖金周转"的老攻略全部失效**；现金规划必须按 1.1.5f1 后的表。
29. **官方政策里只有 `Energy Consumption Awareness`（M5，用电 −5%）给了数值**（**S95**）→ **其他任何"某政策提升/降低 X%"的说法都没有官方依据**。
30. **`Heavy Traffic Ban` 对送货的影响，官方从未澄清，且已确认无补丁说明**（**C24 / S99c**）→ **`[待验证]` 维持，并建议停止追查**；处方只能写"先在一个小区试点 + 盯该区商铺备货与公司效率"。
