# 30 · 公共交通全部机制 + 可执行设计准则

> 适用版本：以 **1.6.2f1** 为基准。凡机制改动处标版本。
> 本文件分两部分：**A. 机制（有官方来源）** / **B. 设计准则（由机制推导，或社区经验，已分开标注）**。
> **B 部分的"经验法则"没有游戏内数值支撑，引用给玩家时必须说明它是推导/经验，不是硬机制。**

---

# A 部分 · 机制（官方来源）

## A1. 五种/七种载具方式的定位（官方原文口径）

| 方式 | 官方定位（直译要点） | 解锁 |
|---|---|---|
| **Bus 公交** | 最早解锁，**早期公交网络的骨干**；便宜灵活，但**深受城市交通状况影响**；燃料版与电动版两种 | 里程碑（Grand Village 解锁 Transportation 服务） |
| **Taxi 出租** | 逻辑类似私家车，点到点；**不需要线路**；早期还负责把没有私家车的新市民带进城；**运力低、加剧拥堵、也被拥堵拖累** | 随交通服务 |
| **Tram 有轨电车** | 相对灵活的轻轨选项；**可以铺在已有道路上**（Replace 工具），也可以独立铺在路外从而**完全绕开其他交通**；初期投资高于公交，但**安静、不产生空气污染** | 发展树 |
| **Subway 地铁** | **快速、高运力的本地公共交通**；初期投资高，但因为速度，**深受重视时间的市民欢迎**；地下站入口占地极小 | 发展树 |
| **Passenger train 通勤/城际铁路** | 运力大；**基础设施占地使其更适合城际运输**，但也可用于城内；高初期成本，靠运力回本 | 发展树 |
| **Ferry 渡轮**（1.3.6f1 / B&P） | **城内水上交通**；官方正文明确"**Ferries carry 100 passengers**"，运行于 seaway 上 | DLC |
| **Passenger ship 客船 / Plane 客机** | 城际为主；客机运力小于船与火车，但**用速度弥补** | 发展树 |

（来源：https://cs2.paradoxwikis.com/Transportation ；渡轮 100 人见同页 Ferry 段；https://www.paradoxinteractive.com/games/cities-skylines-ii/features/public-cargo-transportation ）

> ⚠️ **载客量缺口**：官方 Wiki **没有给出 bus / tram / subway / train / ship / plane 的单车载客量**。除渡轮 100 人外全部为 **待验证**。**任何"公交车载 30 人""地铁载 180 人"的说法在本次检索中没有找到官方来源，禁止当作事实引用。**

## A2. 建设工作流（官方定义的强制顺序）

```
Depot（车库/车辆段） → Stops & Stations（站点与车站） → Tracks / Roads（轨道或道路） → Lines（线路）
```
- 每一种**陆上**公共交通都必须先建对应 depot/yard，车辆从 depot 生成并在此维护。
- **每个 depot 能支持的车辆数是固定值**，可通过建筑升级扩充。
- 水上与空中**没有 depot**，而是把港口接 seaway、把机场用航空线工具直接连到 Outside Connections。
（来源：https://cs2.paradoxwikis.com/Transportation ；https://www.paradoxinteractive.com/games/cities-skylines-ii/features/public-cargo-transportation ）
- CS2 相对 CS1 的关键差异：**CS1 里火车与地铁是从车站直接刷车的，CS2 必须建 yard**。（来源：https://www.paradoxinteractive.com/games/cities-skylines-ii/features/public-cargo-transportation ）

## A3. 「间隔（Interval）到底怎么决定」——唯一正确的机制解释

### A3.1 游戏**没有**"设定目标发车间隔 → 系统自动配车"这个功能
可确证的线路面板（Line panel）可调项只有三项：
1. **票价（Ticket price）**
2. **该线路的车辆数（number of vehicles running on the line）**
3. **运营时段（day / night / both）**

货运线路则只有"车辆数 + 运营时段"。
（来源：https://cs2.paradoxwikis.com/Transportation ；https://www.paradoxinteractive.com/games/cities-skylines-ii/features/public-cargo-transportation ）

> **结论**：CSL2 把"间隔"这个目标**交给了玩家**。你要自己保证 `间隔 ≈ 单圈往返时间 ÷ 车辆数`。

### A3.2 系统给出的唯一反馈信号：**线路使用率百分比（line usage percentage）**
> 官方原文："If a line becomes extremely popular i.e. **its usage percentage close to 100%**, increasing the number of vehicles can alleviate the pressure and **shorten passenger wait times at stops and stations which in turn affect their pathfinding calculations as well!**"
（来源：https://cs2.paradoxwikis.com/Transportation ）

### A3.3 候车时间确实进入寻路成本
- 官方明确：票价"影响市民的寻路计算"；缩短候车时间"也会影响他们的寻路计算"。
- 市民在选择出行方式时权衡 **时间、舒适度、金钱**；**金钱可以在公共交通与私家车之间撬动选择**。
（来源：https://cs2.paradoxwikis.com/Transportation ）
- 叠加年龄偏好（见 `10-game-mechanics.md` §3.1）：**Teens 重省钱 → 票价敏感；Adults 重省时 → 候车时间敏感；Seniors 重舒适 → 车站舒适等级（Comfort）敏感。**
（来源：https://cs2.paradoxwikis.com/Citizens ）

### A3.4 车队规模的另一约束：**depot 车辆上限**
线路车辆数**不能超过 depot 提供的车队规模**。1.3.6f1 起官方还加了"**车辆多选生成**"（可一次为一条线生成一辆或多辆车）。（来源：https://cs2.paradoxwikis.com/Transportation ；https://cs2.paradoxwikis.com/Patch_1.3.X ）

### A3.5 车辆会因维护周期性回车库
每个 depot 建筑的 `maintenanceDuration` 字段（例如 Bus Depot **0.01**、Taxi Depot **0.007**、Rail Yard **0.014**、Subway Yard **0.014**）反映**车辆回库维护的频率量纲**。维护期间车辆不在线，因此**有效运营车辆数 < 你设定的车辆数**。官方未给出该字段的换算公式 → **待验证**。
（来源：https://cs2.paradoxwikis.com/Service_buildings ，1.6 表格 `maintenanceDuration` 列）

### A3.6 已修复的"间隔杀手"
**1.5.7f1** 修复："公交、火车、地铁、电车在繁忙站点可能**永久卡在上下客状态**，无法发车，造成车辆排队与消失。" → **1.5.7f1 之前，"线路使用率 100% 但车不来"很可能是这个 bug；之后应归因于真实运力不足。**
（来源：https://cs2.paradoxwikis.com/Patch_1.5.X ）
**1.2.0f1** 把上下车改为**基于距离**，加快拥挤站点的上下客速度。（来源：https://cs2.paradoxwikis.com/Patch_1.2.X ）
**1.2.5f1** 修复公交离站后莫名掉头（保证实际行驶路径符合规划线路）、改进出租车上下客时间。（来源：https://cs2.paradoxwikis.com/Patch_1.2.X ）
**1.5.7f1** 修复"火车/地铁因为寻路偏好直线而在站间绕行"的遗留问题（1.1.10f1 已提高直线偏好）。（来源：https://cs2.paradoxwikis.com/Patch_1.5.X 、https://cs2.paradoxwikis.com/Patch_1.1.X ）

### A3.7 线路效率必须按**单车容量**归一（跨方式比较的唯一正确口径）

**单车容量**（**游戏内可信数值（玩家提供）`[玩家实测]`**；主表见 `40-number-tables.md` 1.3，**以那里为准**）：

| 方式 | 单车容量（人/辆） |
|---|---|
| 公交 | **80** |
| 地铁 | **1080** |
| 客运火车 | **840** |
| 电车 / 单轨 / 渡轮 / 缆车 | **容量未知，不做归一** |

**公式**：`线路效率 = 乘客数 ÷（车辆数 × 单车容量）`
—— 含义 = 每辆车日均承运了相当于"**满载多少趟**"的量，**跨方式可比**。

* ⚠️ **必须同时保留「人/车」原值**：**只按「人/车」横向排序，会把"地铁车大"误读成"地铁低效"** ——
  地铁一辆车 1080 人、公交一辆车 80 人，两者的「人/车」天生差一个数量级，混排排序毫无意义。
* **容量未知的方式（电车 / 单轨 / 渡轮 / 缆车）留空、不参与归一排序**，只做**同方式内部**比较。
* **使用率 / 满载率类判据仍以游戏内 Line 面板的「使用率百分比」为准**（见 A3.2）；
  容量归一只是**排序与横向比较**的口径，**不替代**使用率，也**不替代**「人/车」原值。

### A3.8 配车为 0 的线路 = **停用线路**（不做任何客流分析）

* **`Vehicle == 0`**（Carto 的 `Route_Centerline.Vehicle`）→ 一律视为**停用线路**：
  **不做任何客流分析** —— 不参与「人/车」、人·km、估算间隔、效率排序、客流合计与中位数；
* **只做线位分析**：走向、长度、站数、覆盖贡献、是否与既有走廊重复；
* 报告必须**单独列出停用线路清单**，并给两条处方：
  ① **恢复配车**（线位仍有用）② **撤线**（线位已被其它线路覆盖）；
* ⚠️ **不得**把停用线路混进"低效线路"里去批评 —— 它的乘客数低是"没车"造成的，
  **不是需求不足的证据**。
* 同一口径见 `70-carto-data-schema.md` 3.4 与 `46-algorithm-roadmap.md` T6。

## A4. 线路与站点机制

| 机制 | 内容 | 来源 |
|---|---|---|
| **Waypoint 途经点** | 建公交线路时可设置途经点，**控制巴士在站点之间走哪条路**，从而避开繁忙道路或路口；也可事后加设改线 | https://www.paradoxinteractive.com/games/cities-skylines-ii/features/public-cargo-transportation |
| **同站多线** | 同一站点/车站**可以容纳多条线路**，但"车辆增多可能导致拥堵" | 同上 |
| **单向线路** | 与道路一样，交通线路可以是单向或双向 | https://cs2.paradoxwikis.com/Transportation |
| **站台数** | 车站有站台数上限（如 Small Bus Station 3 个公交站台、Bus Station 6 个、City Central Train Station 14 个）；站台不足会成为瓶颈 | https://cs2.paradoxwikis.com/Service_buildings |
| **车站舒适等级 Comfort** | 每个车站有 Comfort 值（公交站 40–50、火车站 10–50、地铁站 25–50、码头 50、机场 50–90）；**升级 Station Services 可 +20 ~ +30 Comfort** | 同上 |
| **城际公交** | 建 Bus Depot 后即可开设城际公交线；城际公交可停靠公交总站，也可在普通公交站上下客 | https://cs2.paradoxwikis.com/Transportation |
| **出租车调度中心** | **未升级 Dispatch Center 前，出租车只能在出租车候客站接客**；升级后可全城接单 | 同上 |
| **机场线** | 机场直接用航空线工具连到外部连接，不需要额外基础设施 | 同上 |
| **渡轮** | 需要水域与 seaway；B&P 提供 Ferry Depot / 2 种渡轮站 / Ferry Terminal / Ferry Line Tool | https://cs2.paradoxwikis.com/Patch_1.3.X |
| **1.5.2f1 修复** | Tram Junction / Parallel / Loop Station 此前**不工作**；已修复，但**已有城市需要重建这些站** | https://cs2.paradoxwikis.com/Patch_1.5.X |

## A5. 票价与补贴

### A5.1 票价
- **每条客运线路单独设置票价**；票价进入寻路成本，因此"可以鼓励或劝退市民使用某种交通方式"。
- 出租车有城市政策 **Taxi Minimum Fare**：每次乘车收取最低起步价，**叠加在按实际距离计算的车费之上**（里程碑 4 解锁）。
（来源：https://cs2.paradoxwikis.com/Services ；https://cs2.paradoxwikis.com/Policies ）
- **0 票价触发专属电台事件 "Free public transport"**（1.1.10f1 修复了该事件在票价设为 0 时不触发的问题）。→ 这意味着"免费公交"是被官方认可的一种玩法路径。（来源：https://cs2.paradoxwikis.com/Patch_1.1.X ）

### A5.2 "补贴（subsidy）"在 CSL2 里的真实含义
- **城市层面没有线路补贴机制**。可用的等价手段是：
  1. 把票价设为 0 或极低（损失票款收入）；
  2. 用**服务预算滑块**调节整个交通服务的成本/效率（**交通服务预算同样在 50%–150% 区间**）；
  3. **1.1.5f1 之后政府补贴已被彻底移除**，所以公共交通的亏损必须由其他税收覆盖。
（来源：https://cs2.paradoxwikis.com/Services ；补贴移除 https://cs2.paradoxwikis.com/Patch_1.1.X ）

### A5.3 交通成本本身
- 客运车站/depot 的**维护费极高**（例：Bus Depot ₡31,000/月，1.0 时代为 ₡23,250 → **1.6 表格已上调**；Harbor ₡30,000/月；Rail Yard ₡15,000/月）。→ **"多修枢纽"的财政代价是真实的，不是免费的**。（来源：https://cs2.paradoxwikis.com/Service_buildings ）
- 1.1.5f1 还上调了**大多数城市服务建筑的维护费**。（来源：https://cs2.paradoxwikis.com/Patch_1.1.X ）

## A6. 公交专用道 / BRT 式做法（游戏内可行手段）

| 手段 | 游戏内工具 | 来源 |
|---|---|---|
| 公交专用道（路侧） | **Replace 工具**：从交通菜单给部分道路类型加公交车道 | https://cs2.paradoxwikis.com/Roads |
| **独立公交道路** | 官方原文：可以"create roads **exclusively for public transport vehicles** such as buses" | https://www.paradoxinteractive.com/games/cities-skylines-ii/features/public-cargo-transportation |
| 独立公交道可加照明 | 1.2.5f1 起**独立公交车道可以加装 Lighting 升级**；**未加照明时独立公交道不输电** | https://cs2.paradoxwikis.com/Patch_1.2.X |
| 电车独立路权 | 电车轨道可**独立铺在路外**，"thus bypassing other traffic altogether" | https://cs2.paradoxwikis.com/Transportation |
| 电车可加在道路上 | Replace 工具（**不能加在高速、巷道、砂石路以及部分桥梁上**） | https://cs2.paradoxwikis.com/Roads |
| 信号优先 | 游戏**没有**信号优先功能 | — |
| 交叉口专用转向 | No turn left/right/straight + 单向路 | https://cs2.paradoxwikis.com/Roads |

> **BRT 完整度评估（游戏口径）**：CSL2 给到"专用道 + 独立路权 + 独立站点 + 站台数 + 票价"，但**没有**交叉口信号优先、没有车外售票（只有车站舒适度升级）、没有实时班次信息。因此 CSL2 里能做到的是**"准 BRT"**而不是完整 BRT。**这是机制层面的判断，非官方表述。**

## A7. 多模式换乘 / 枢纽（游戏原生支持）

可确证的"一体化换乘"升级（来源：https://cs2.paradoxwikis.com/Service_buildings ，1.6 表格）：

| 主建筑 | 可集成的换乘方式 | 造价 / 维护 |
|---|---|---|
| City Bus Station | **Subway Interface**（作为地铁站）+ Taxi Stop + Additional Parking Levels | ₡200K / ₡15K；₡12K / ₡3.5K；₡150K / ₡15K |
| Train Station | **Subway Interface** + Taxi Stop + Extra Platforms + Station Services | ₡200K / ₡15K；₡12.5K / ₡3.5K |
| **Terminus Station** | **Bus Terminal** + **Tram Terminal** + Extra Platforms + Station Services | ₡50K / ₡3.5K；₡60K / ₡4K |
| Harbor | **Transit Terminal**（公交 + 出租） + Extra Pier | ₡75K / ₡20K |
| **International Airport** | **内置 2 个火车月台 + 2 个公交月台 + 出租站** | 本体 ₡4.0M / ₡200K |
| Ferry Terminal（B&P） | **Bus Terminal** | ₡75K / ₡14K |
| Cargo Harbor | **Railway Connection**（货运换装） | ₡80K / ₡20K |
| 港口（B&P） | **Intermodal Train Terminal** | ₡80K / ₡20K |

**换乘的机制回报**：
- 车站/站点**提升周边地价**（1.1.0f1 起）→ **TOD 有机制支撑**；
- 换乘站把"候车时间"集中到一处，减少多次候车；
- 机场有全城加成：Airport **+5% 吸引力 / +3% 办公效率**；International Airport **+10% 吸引力 / +10% 大学教育兴趣 / +10% Software 需求**。
（来源：https://cs2.paradoxwikis.com/Patch_1.1.X ；https://cs2.paradoxwikis.com/Transportation ）

## A8. 交通信息视图（诊断用，官方口径）
- 面板给出：**每种方式的线路数、游客数、月客运总量**；货运部分给出**货运线路数 + 各方式月吨位**。
- 地图高亮**所有线路**，并用清晰图标标出**所有在途车辆**。
- **Transportation Overview 面板**：按客运/货运分组的全部线路一览，可改名、启用/停用、改线路颜色。
- **Line 面板**：线路**长度**、**站点数**、**当前乘客数**、**使用率百分比**；可改车型、票价、车辆数、运营时段。
（来源：https://cs2.paradoxwikis.com/Transportation ；https://cs2.paradoxwikis.com/Info_views ）

---

# B 部分 · 可执行设计准则

> ⚠️ **口径范围（本部分专用，不是全局原则）**
> 1. **"站"只指客运站点。** **地铁总站（Terminal Subway Yard / `DepotSubway`）是 depot（车辆段），
>    只负责给线路提供车辆 —— 它不是车站**：不计入车站数，也不参与站距、逐站腹地、站点覆盖率。
>    同理 `DepotBus`（公交总站）/ `DepotTrain`（火车总站）也**不是**站。
>    真正算站的只有 `StopBus` / `StopSubway` / `StopPassengerTrain`
>    （`city_report.py` 的 `PASSENGER_STOP_CATS` 白名单，见 `references/70` §3.6）。
>    总站唯一的"站"用途是 **B5 的车队上限**（10 辆 / 5 辆那个约束来自它）。
> 2. **货运港口、货运铁路、货运航线不与客运数据一并分析。** 本节 A/B 两部分的
>    **线路效率、走廊重叠、站距、间隔、车队规模**都只对**客运线路**
>    （`Route_Centerline.Object = RoutePassenger`）成立；
>    `RouteCargo`（货船/货运火车）的 `Passenger` 恒为 0，混进来会拉偏中位数与合计。
>    货运类的判据（终端选址、海铁联运、储位、仓库缓冲）**放在工业部分**，
>    见 `SKILL.md` §2「货运与产业链」与 `47` §2。

> 标注规则：
> - **[机制]** = 直接由 A 部分官方机制推出，来源可溯。
> - **[经验]** = 社区经验/现实规划类比，**CSL2 官方未给出对应数值**，给玩家时应说明。
> - **[待验证]** = 缺少来源，不要当事实用。

## B1. 多模式分工门槛（"什么人口/什么距离用什么"）

| 方式 | 适用条件 | 依据 |
|---|---|---|
| **公交 Bus** | 低–中密度、新开发片区、需求未定型的走廊、作为**支线喂给**轨道系统 | [机制] 官方定位"早期骨干、便宜灵活、受交通影响"（https://cs2.paradoxwikis.com/Transportation ）；[经验] 支线喂给（https://chillplacegaming.com/cities-skylines-ii-bus-tram-metro-lines/ ） |
| **电车 Tram** | 走廊**已有稳定客流**，值得铺轨但密度还不足以打隧道；中等距离、沿线商业走廊 | [机制] 官方定位"轻轨、可独立路权、安静无空气污染"（同上）；[经验] 走廊门槛（同上） |
| **地铁 Subway** | **最高密度走廊 + 最长距离**，站距最大，站点设在真实需求中心 | [机制] 官方定位"快速高运力、受重视时间的市民欢迎"（同上）；[经验] 站距与选址（同上） |
| **通勤铁路 Train** | 城内长距离大运量（但要牺牲车站占地）**或**城际联系 | [机制] 官方原文"基础设施占地使其更适合城际，但也可本地使用"（同上） |
| **渡轮 Ferry** | 有水域分割、跨水面距离明显长于绕行距离的地图 | [机制] 官方"城内水上交通，单船 100 人"（同上） |
| **出租车 Taxi** | 低密度末梢、夜间、无线路可言的零散需求 | [机制] 官方"不需要线路；运力低、加剧拥堵"（同上） |

> **具体人口数字门槛**：**官方与本次检索到的来源都没有给出"多少人口该上地铁"的门槛值 → 待验证。** 不要引用"5 万人上地铁"这类数字。

## B2. 站距（Stop spacing）

- **[经验]** 站距宽窄排序：**公交最密 < 电车较宽 < 地铁最宽**。理由：公交的价值就是"方便、步行可达"；电车的目标是走廊内的点对点速度；地铁站应设在真实需求中心而非"均匀分布"。（来源：https://chillplacegaming.com/cities-skylines-ii-bus-tram-metro-lines/ ）
- **[机制]** 站距过密的直接代价可确证：**每一个"不必要的路口转弯"都直接累加进长者（Seniors）的寻路成本**；且**站点会影响地价（正效应）**，所以密站并非纯负面。（来源：https://cs2.paradoxwikis.com/Traffic ；https://cs2.paradoxwikis.com/Patch_1.1.X ）
- **[机制]** 折返/掉头代价：1.6.0f1 修正了合法/非法掉头成本 → **端头折返式线路在 1.6.0f1 后更可行**（此前掉头成本不合理）。（来源：https://cs2.paradoxwikis.com/Patch_1.6.X ）
- **具体米数建议（如"公交 300–500 m、地铁 800–1200 m"）→ 待验证**：CSL2 官方无此类数值。若引用现实规划标准（中国规范常见的 300–500 m / 500–800 m 公交站距），必须标注为**现实标准**而非游戏机制，见 `90-web-vs-book-notes.md`。

## B3. 线路长度

- **[经验]** 公交线路**不要画成一条横贯全图的长线**。理由：长线脆弱——一个路口阻塞或一辆车故障就会波及下游所有站点，且远端准点率不可靠。建议用**2–3 条较短、可以部分重叠的环线/线**覆盖同一片区域，故意留出交叉重叠以提供冗余。（来源：https://chillplacegaming.com/cities-skylines-ii-bus-tram-metro-lines/ ）
- **[机制]** 与上一条吻合的硬机制：① 线路越长，**同样车辆数下间隔越长**（`间隔 ≈ 单圈往返 ÷ 车辆数`）；② 官方明确"同一站点服务多条线路时，车辆增多可能导致拥堵"；③ **1.5.9f1 之前**车辆会做无意义掉头、1.2.5f1 之前公交离站后会莫名掉头，长线受害更重。（来源：https://cs2.paradoxwikis.com/Transportation ；https://cs2.paradoxwikis.com/Patch_1.5.X 、https://cs2.paradoxwikis.com/Patch_1.2.X ）
- **具体公里数上限 → 待验证**（无官方数值）。

## B4. 间隔目标（Headway）与车队估算

### B4.1 估算公式（由机制推导，**非官方公式**）
```
所需车辆数 ≈ ceil( 单圈往返时间 ÷ 目标间隔 ) + 备用车
单圈往返时间 ≈ 线路长度 × 2 ÷ 平均运营速度 + 站数 × 单站停站时间
```
- 平均运营速度：公交受拥堵影响显著，应取 15–25 km/h 量级（**这是经验取值，非游戏数值 → 待验证**）；有独立路权的电车/地铁可取接近其限速。
- 单站停站时间：官方未给数值 → **待验证**。1.2.0f1 把上下客改为**基于距离**，拥挤站点更快。
- **必须留备用车**：车辆会因 depot 的 `maintenanceDuration` 周期性回库维护，维护期间不在线。1.3.6f1 起可**一次为一条线生成多辆车**，便于快速加车。
（来源：机制部分 https://cs2.paradoxwikis.com/Transportation ；维护字段 https://cs2.paradoxwikis.com/Service_buildings ；1.2.0f1 上下车 https://cs2.paradoxwikis.com/Patch_1.2.X ；1.3.6f1 多选生成 https://cs2.paradoxwikis.com/Patch_1.3.X ）

### B4.2 目标间隔的取法（经验 + 年龄机制）
| 目标乘客群 | 建议策略 | 依据 |
|---|---|---|
| 通勤干线（成人为主，赶时间） | **间隔越短越好**；成人把 Time 放在首位，候车时间直接进成本 | https://cs2.paradoxwikis.com/Citizens |
| 学校/青少年线路 | **低票价杠杆 > 高频**；Teens 把 Money 放在首位 | 同上 |
| 长者/医院/公园线路 | **车站舒适度（Comfort）杠杆 > 频次**；Seniors 把 Comfort 放在首位，且"能否找到合适的站点下车"进入成本 | 同上；https://cs2.paradoxwikis.com/Traffic |
| 旅游/休闲线路 | 运营时段设为 day+night，并接入车站 Station Services（+20~30 Comfort） | https://cs2.paradoxwikis.com/Service_buildings |

### B4.3 用游戏内信号闭环
1. 打开 **Transportation Overview**，找 **使用率接近 100%** 的线路 → **加车**（官方明确建议）。
2. 打开 **Traffic 视图**，看"一天内的流量曲线" → 判断是否需要**分时段**（虽然 CSL2 只能设 day/night/both 三档，不能做小时级排班）。
3. 用 **Population 视图**核对年龄结构 → 决定"省钱型"还是"省时型"策略。
（来源：https://cs2.paradoxwikis.com/Transportation ；https://cs2.paradoxwikis.com/Info_views ）

> **重要限制（机制）**：CSL2 的运营时段只有 **白天 / 夜间 / 全天** 三档，**没有小时级排班**。（来源：https://cs2.paradoxwikis.com/Transportation ）

## B5. 车队规模（Fleet sizing）与 depot 规划

| 方式 | Depot | 车辆上限 | 扩容升级 | 造价 / 维护 |
|---|---|---|---|---|
| 公交 | Bus Depot | **25** | Extra Garage **+10**；Electric Bus Maintenance（切换电动） | ₡150K / **₡31K** |
| 公交（紧凑） | Compact Bus Depot（City Stations CP） | 10 | — | — |
| 出租 | Taxi Depot | **25** | Taxi Garage **+10**、Dispatch Center、Electric Taxis | ₡100K / ₡10K |
| 出租（小） | Small Taxi Depot | 8 | Garage **+4**、Dispatch Center、Electric Taxis | ₡35K / ₡3.5K |
| 电车 | Tram Depot | **10** | 额外车库 | ₡100K / ₡8.625K |
| 地铁 | Subway Yard | **10** | Extra Rails **+5**、Maintenance Hall | ₡200K / **₡24K** |
| 地铁（终端） | Terminal Subway Yard | **5** | Extra Tracks **+2** ×2 | ₡120K / ₡12K |
| 火车 | Rail Yard | **10** | Extra Rails **+5**、Maintenance Hall | ₡150K / ₡15K |
| 火车（小） | Railway Depot | **8** | Extra Tracks **+8**、Maintenance Hall | ₡120K / ₡12K |
| 渡轮 | Ferry Depot（B&P） | **20** | Extra Hall **+10** | ₡150K / ₡21K |

（来源：https://cs2.paradoxwikis.com/Service_buildings ，1.6 表格）
> **车队规划结论**：**公交 25 辆/库、地铁只有 10 辆/段、电车只有 10 辆/库**。当地铁线路变长、班次变密时，**你很可能先撞到 Subway Yard 的 10 辆上限**，而不是钱。规划地铁时就应预留第二个 Subway Yard 或 Terminal Subway Yard 的位置。
>
> ⚠️ **范围限制（本小节专用）**：车队上限表里的 **Subway Yard / Terminal Subway Yard / Rail Yard
> 都是 depot（车辆段/车库），不是车站** —— 它们只用来解释"为什么加车加不上去"，
> **不得用于站点计数、站距、腹地或覆盖率**（见本部分开头的口径范围）。
> `Terminal Subway Yard` 的中文名是**地铁总站**，但它**不是地铁站**。
> `Maintenance Hall` / `Maintenance Hall - Terminal` 的作用是把 `maintenanceDuration` **降低 0.0046**（负值 = 缩短维护时间）→ **保留更多车辆在线**，是提升有效运力的隐性手段。（来源：同上）

## B6. 票价与补贴策略

- **[机制]** 每条线路独立定价，票价进入寻路成本，"可以鼓励或劝退市民使用某种交通方式"。（来源：https://cs2.paradoxwikis.com/Transportation ）
- **[机制]** 出租车有最低起步价政策（Taxi Minimum Fare，里程碑 4）。（来源：https://cs2.paradoxwikis.com/Policies ）
- **[机制]** 票价归零会触发官方电台事件"Free public transport"——说明免费公交是被设计者预期的玩法。
- **[机制]** 1.1.5f1 后城市**没有政府补贴**，交通亏损只能靠其他税收填；且 1.1.5f1 上调了**大多数城市服务建筑的维护费**。（来源：https://cs2.paradoxwikis.com/Patch_1.1.X ）
- **[经验]** 策略组合建议：
  1. **干线高票价 + 高频**（成人愿为时间付费）；
  2. **学校/青少年线低价或免费**（Teens 价格敏感）；
  3. **长者可及性靠 Comfort 而非票价**（Seniors 重舒适）；
  4. **城际线（火车/船/飞机）用高票价**，因为城际乘客没有替代方案且能带来游客收入。
  5. 免费公交是"用财政换道路容量"的合法手段——拥堵的边际成本往往高于票款。
  以上 1–5 为**推导/经验**，官方没有给出最优票价数值 → **待验证**。

## B7. 换乘枢纽设计准则

1. **[机制]** 优先使用**原生一体化车站**（Terminus Station 的 Bus+Tram Terminal、Train Station 的 Subway Interface、International Airport 内置火车与公交月台），而不是靠"两个站靠在一起"。
2. **[机制]** 枢纽选址要吃到 **1.1.0f1 的地价加成**：把枢纽放在你**想要抬升地价**的位置（例如待更新的旧城区）。
3. **[机制]** 枢纽必须有**足够停车位**——"停车可用性以类似公交选项的方式进入寻路决策"，所以 P+R 是真实有效的。（来源：https://cs2.paradoxwikis.com/Roads ）
4. **[机制]** 枢纽站台数是硬瓶颈：Small Bus Station 只有 **3 个**公交站台、Bus Station **6 个**、City Central Train Station **14 个**火车月台。多条线路挤 3 个站台会堵。（来源：https://cs2.paradoxwikis.com/Service_buildings ）
5. **[机制]** 枢纽会带来**大量车辆集中**：官方明确"同一站点服务多条线路 + 车辆增多 → 可能拥堵"。→ 枢纽周边应做**公交专用进出通道**（可用独立公交道，1.2.5f1 起可加照明以输电）。
6. **[经验]** 支线应当**穿越**干线而不是**平行于**干线：与地铁平行的长公交线会把客流分流掉，两边都吃不饱；把平行线改成"跨线喂给"通常能同时提升两套系统的载客量。（来源：https://chillplacegaming.com/cities-skylines-ii-bus-tram-metro-lines/ ）

## B8. 公共交通的落位检查清单（可直接给玩家用）

- [ ] **每个 depot 是否有道路/轨道连接？**（无连接则车出不来）
- [ ] **线路车站是否都在同一套网络里？**（地铁站需要 Subway Yard + 轨道；火车站需要 Rail Yard + 轨道且与地图既有铁路连通）
- [ ] ⚠️ **有没有把 depot 当车站？**（**地铁总站 / 公交总站 / 火车总站不是站** ——
      站点统计、站距、腹地、覆盖率里只能出现 `StopBus` / `StopSubway` / `StopPassengerTrain`）
- [ ] **线路使用率是否 <100%？**（≥100% 必加车）
- [ ] **有没有配车为 0 的停用线路？**（要么**恢复配车**、要么**撤线** —— 别把它当"低效线路"批评，见 A3.8）
- [ ] **跨方式比效率时是否按单车容量归一？**（公交 **80** / 地铁 **1080** / 客运火车 **840** 人/辆；只比「人/车」会误判地铁，见 A3.7）
- [ ] **终点站是否需要折返？**（1.6.0f1 后掉头成本已合理化，但环形线路仍更稳）
- [ ] **是否与地铁/铁路平行抢客？**（改成跨线喂给）
- [ ] **枢纽站台数够吗？**（对照 A7 表）
- [ ] **票价是否符合目标客群的年龄结构？**（对照 §3.1 年龄表）
- [ ] **运营时段是否覆盖夜间岗位？**（只有 day/night/both 三档）
- [ ] **是否给通勤站配了自行车停车/停车场？**（1.4.2f1 起有自行车；停车影响寻路）
- [ ] **车辆是否周期性回库导致实际班次低于预期？**（考虑 Maintenance Hall 升级或加车）
- [ ] **版本是否 ≥ 1.5.7f1？**（否则"车不来"可能是上下客卡死 bug）

---

## 附：本文件涉及的"待验证"清单（给下游 AI 用）

1. **电车 / 单轨 / 渡轮 / 缆车 / 客船 / 客机**的单车载客量（**官方来源只有渡轮 100 人**；
   公交 80 / 地铁 1080 / 客运火车 840 人/辆来自**游戏内可信数值（玩家提供）`[玩家实测]`**，仍无官方来源 → 见 A3.7）。
2. **候车时间在寻路成本中的权重系数**。
3. **`maintenanceDuration` 与"车辆离线时间占比"的换算**。
4. 各方式的**平均运营速度**、**单站停站时间**。
5. **站距建议的具体米数**、**线路长度的具体公里上限**。
6. **"多少人口该上地铁/电车"的门槛值**。
7. **票价的最优值**。
8. 官方是否曾公布过**"目标间隔"或"班次"概念**（本次检索未发现）。
