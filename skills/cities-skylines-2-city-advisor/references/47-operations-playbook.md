# 47 · 实操攻略手册（公交运营 / 货运产业链 / 土地利用 / 通行能力）

> 检索执行日期：**2026-10-13**（本轮实际联网检索，全部为 `web_search` / `web_fetch` 实际抓取）
> 基准版本：**1.6.2f1「Autumn Breeze」2026-09-15**；断代锚点 **1.1.5f1「Economy 2.0」**
> 来源编号 S##/C##/R## 与 `00-sources.md` 一致。**本文件新增来源为 S70–S89。**
>
> 标记规则：
> - `[游戏机制]` = 官方一手（官方 Wiki 正文 / 官方 Wiki 自动生成表 / 官方补丁说明 / 官方 Dev Diary）
> - `[社区实证]` = 有可复现方法或数据的社区测试
> - `[攻略经验]` = 攻略站/个人博客的经验法则（可信度最低，需与官方交叉验证）
> - `[待验证]` = 无可靠来源，**禁止当机制引用**
>
> **可信度等级**：`A` = 官方一手；`B` = 可复现社区实证；`C` = 攻略站/视频文字稿。
> 每条结论后附 **"→ 对 CSL2 建议意味着什么"**，直接可落成动作。

---

## 0. 本轮的三个"量纲级"突破（先记这三条）

| # | 突破 | 依据 | 影响 |
|---|---|---|---|
| **1** | **`Service range` 的单位是"米"（游戏内单位 → 米），且它是"最大半径"** | 官方 Wiki 在**同一张**自动生成表里混用 km / m（`Radio Mast` = 1 km、`Radio Mast Wireless Network Antenna` = 250 m）；而 `Hospital` 的 Service range = **7500.0**，与"7.5 km 服务半径"在数值上完全吻合（来源：[S15 Service_buildings](https://cs2.paradoxwikis.com/Service_buildings)，表标注 1.6）。**社区侧独立互证**：日文攻略 Wiki 明确写小型诊所"カバーエリアは**大体 2km** くらい"（≈ Service range 2500）（来源：[S80 csl2wiki 医療・葬儀](https://csl2wiki.wicurio.com/index.php?%E5%8C%BB%E7%99%82%E3%83%BB%E8%91%AC%E5%84%80)，2025-11-20） | **C10/C20 可以结案**：可以写"Service range 单位是米"。但见下条限制 |
| **2** | **服务覆盖半径不是固定的——它随区域内需求被"吃满"而缩小** | 日文 Wiki 同一段原文："カバーエリアは大体2kmくらいと狭いうえ、**カバーエリア内の人口増加にも弱く**、中密度住宅、高密度住宅などの住民数の多い建物が多い区画があると**一気にカバーエリアが狭くなる**"（服务区约 2 km，而且**对区内人口增长很脆弱**，一旦有中/高密度住宅这种住户多的建筑，**覆盖区会一下子变窄**）（来源：[S80](https://csl2wiki.wicurio.com/index.php?%E5%8C%BB%E7%99%82%E3%83%BB%E8%91%AC%E5%84%80)，可信度 **C**） | **禁止把 Service range 当"服务人口上限"以外的固定几何**。密度越高，**实际覆盖半径越小** → 高密度区必须**加密服务点**，不是"一个医院管一大片" |
| **3** | **预算滑块会改变"服务覆盖半径"**（不只是车辆数与容量） | 官方 Services 页原文："Services will increase their service capacity (trash trucks, police cars, student capacity, etc.) if the budget is increased… **Other effects may be less obvious, such as the range of the service coverage.**"（来源：[S81 Services](https://cs2.paradoxwikis.com/Services)，正文标注 1.0，可信度 **A**） | **"服务覆盖不足"可以通过提高该服务的预算滑块直接缓解（半径变大）**，而不是必须先盖楼。这是本轮**最便宜的一条覆盖修复手段** |

> ⚠️ **突破 1 的引用纪律**：虽然可以确认单位是米，但**不要把 `Service range` 的绝对值当作"保证覆盖"**（突破 2）。
> 算法上仍应保留"自己圈定的现实标准半径"作为**下界**校验，用 Service range 作为**上界**。

---

## 1. 公共交通：线网优化与运营实操

> ⚠️ **范围限制（本节专用）**：本节是**客运**口径 —— 只适用于
> `Route_Centerline.Object = RoutePassenger` 的线路，站点只指
> `StopBus` / `StopSubway` / `StopPassengerTrain`。
> * **地铁总站 / 公交总站 / 火车总站（`DepotSubway` / `DepotBus` / `DepotTrain`）是 depot（车辆段），
>   只负责给线路提供车辆 —— 不是车站**：不计入站点数、站距、逐站腹地、覆盖率。
> * **货运港口、货运铁路、货运航线不与本节数据一并分析**（见 §2 范围限制）。

### 1.1 官方机制补充（本轮新抓到的，之前 30 文件未收录）

| 机制 | 原文要点 | 来源 | 标记/可信度 | → 对 CSL2 建议意味着什么 |
|---|---|---|---|---|
| **同站换乘的步行距离惩罚** | 官方只在 Traffic 页说 Comfort 包含"finding a suitable parking spot or public transport stop to get off at"，但**社区实测补充**：自宅↔站点、学校/职场↔站点的步行可以忍，**"乗り換えになると一定距離以上の徒歩移動を嫌う"（一旦是换乘，超过一定距离的步行就会讨厌）**（来源：[S82 csl2wiki 交通](https://csl2wiki.wicurio.com/index.php?%E4%BA%A4%E9%80%9A)，2025-11-27，可信度 **C**） | S12 / S82 | `[攻略经验]` C | **枢纽设计的第一原则不是"两条线有站"，而是"两站台之间步行 ≤ 1 个街区"**。宁可拆掉一个站台、把两条线塞进同一个原生一体化车站（Terminus Station / Subway Interface），也不要"两个站隔 300 m" |
| **枢纽周边行人横穿 = 拥堵源** | "バスターミナルは車道と歩道を分離するように道路を敷かないと、**横断する歩行者が大渋滞を引き起こす原因になる**"（公交总站如果不把车道和人行道用道路分隔开，横穿的行人会引发大堵车）（来源：[S82](https://csl2wiki.wicurio.com/index.php?%E4%BA%A4%E9%80%9A)，可信度 **C**） | S82 | `[攻略经验]` C | **公交总站/枢纽必须做"人车分离"**：进出车道独立成路，站台只接人行道（wide sidewalk），不要让乘客从车道上穿行 |
| **公交与电车的"一次运量"差** | "（电车）**バスより一回の輸送量が多い**ため、うまく使えば**渋滞に巻き込まれにくく輸送量が多いバス**として使える"（电车单次运量比公交大，用得好就等于"不会被堵、运量更大的公交"）（来源：[S82](https://csl2wiki.wicurio.com/index.php?%E4%BA%A4%E9%80%9A)，可信度 **C**） | S82 | `[攻略经验]` C | 走廊**已经有稳定客流但还打不起隧道**时，**电车=公交的严格升级**：同样受路网影响但自有路权时可完全绕开。**不要把电车当"更贵的地铁"**，它是"抗堵版公交" |
| **电车把车道吃掉一条** | 用 Replace 工具把带中央分隔带的道路升级成电车线路时，"**車線が1つ減り**、中央部分に路面電車専用路が作られる"（车道减少 1 条，中央变成电车专用路）（来源：[S82](https://csl2wiki.wicurio.com/index.php?%E4%BA%A4%E9%80%9A)，可信度 **C**） | S82 | `[攻略经验]` C | **在主干道上铺电车 = 用 1 条汽车道换 1 条电车专用道**。若该走廊小汽车已接近饱和，这会**恶化**拥堵；先算车道余额再铺 |
| **电车站会自带人行横道与信号灯** | "駅もセットできるが、**横断歩道と信号が発生してしまう**ため、交通量の多い場所だと渋滞の原因と化す"（可以连带设置车站，但会产生人行横道和信号灯，在交通量大的地方会变成拥堵原因）（来源：[S82](https://csl2wiki.wicurio.com/index.php?%E4%BA%A4%E9%80%9A)，可信度 **C**） | S82 | `[攻略经验]` C | **每加一个电车站就是加一个信号路口**。站距过密会直接惩罚整条走廊的机动车通行 → 与"站距要密"（可达性）形成**可量化的取舍** |
| **地铁噪声不可忽略** | "騒音発生がそれなりにあり、近隣に駐車場等の騒音源があると**波及して騒音範囲が広がったりする**ので、設置場所は住宅に寄せすぎないよう注意"（地铁有相当噪声，附近若有停车场等噪声源会叠加、噪声范围扩大，选址别太靠住宅）（来源：[S82](https://csl2wiki.wicurio.com/index.php?%E4%BA%A4%E9%80%9A)，可信度 **C**） | S82 | `[攻略经验]` C | **"地铁站抬地价"与"地铁站有噪声"同时成立**。TOD 加密时地铁站口应与住宅**隔一栋楼**，或把住宅地块放在站口背面 |
| **出租车定价是"政策"不是"线路"** | 出租车没有线路面板；**价格由城市政策 `Taxi Minimum Fare` 决定**（里程碑 4），是"起步价 + 按距离计费"的叠加（来源：[S83 Policies](https://cs2.paradoxwikis.com/Policies)，正文标注 1.0，可信度 **A**） | S13/S83 | `[游戏机制]` A | **出租车调价要进 Policies 面板改，不是 Transportation 面板**。给玩家写动作时要写对面板 |
| **出租车太便宜会反噬** | "他の交通機関と異なり、**安易に安くするとたった300mくらいでも使ったりして渋滞の大きな原因になる**ので要注意"（与其它交通方式不同，草率地调便宜，市民连 300 m 都会叫车，成为大堵车的主因）（来源：[S82](https://csl2wiki.wicurio.com/index.php?%E4%BA%A4%E9%80%9A)，可信度 **C**） | S82 | `[攻略经验]` C | **出租车起步价能定高就别定低**。出租车是"低密度末梢/夜间"的补丁，不是公交替代品 |

### 1.2 公交线路长度与站距（本轮能确认 / 不能确认的）

| 问题 | 结论 | 来源 | 标记 |
|---|---|---|---|
| 线路长度的**具体公里上限** | **仍无官方数值 → 维持 `[待验证]`** | — | `[待验证]` |
| 站距的**具体米数** | **仍无官方数值 → 维持 `[待验证]`** | — | `[待验证]` |
| **站数的经验区间** | `[攻略经验]` 中文攻略站给出"公交等道路运输设施通常 **5~10 个站台会好一些**，太多了会导致等待时间过长"（来源：[S84 游侠网 设施布局分配一览](https://gl.ali213.net/html/2023-10/1199903.html)，2023-10-28，可信度 **C**） | S84 | `[攻略经验]` C |
| **"长短双线"分流法** | 同一走廊"**造两条线路，单条线路承载量较大时分开客流，通常采用大站制（一条 10 站另一条 5 站）**"（来源：[S84](https://gl.ali213.net/html/2023-10/1199903.html)，可信度 **C**） | S84 | `[攻略经验]` C |
| **"不要一条超长线"的机制理由** | **官方机制侧独立成立**：`间隔 ≈ 单圈往返 ÷ 车辆数`（车数有 depot 上限），且"同一站点服务多条线路 + 车辆增多 → 可能拥堵"（来源：[S13 Transportation](https://cs2.paradoxwikis.com/Transportation)、[S22](https://www.paradoxinteractive.com/games/cities-skylines-ii/features/public-cargo-transportation)） | S13/S22 | `[游戏机制]` A |

> ⚠️ **冲突登记（→ C22）**：`[攻略经验]` 的"长短双线分流"与本项目 `SKILL.md` §5.2 反模式 1「**拆分既有干线**」**方向相反**。
> **裁定**：`SKILL.md` 的反模式基于**本项目真实 Carto 数据**（拆分后总量低于拆分前，出现两次）→ 按裁定顺序"游戏内实测 > 攻略站"，**维持 `SKILL.md` 结论，不采纳"长短双线"作为通用处方**；仅在"单条线使用率长期 ≥100% 且加车已撞 depot 上限"时作为**最后手段**考虑。

### 1.3 每辆车 / 每乘客的补贴与票价敏感度

| 问题 | 本轮结论 | 来源 | 标记 |
|---|---|---|---|
| 城市层面**每乘客补贴**是否存在 | **不存在**。1.1.5f1 起政府补贴被彻底移除；公共交通亏损只能由其它税收覆盖。可用的等价手段只有：票价置 0 / 交通服务预算滑块 / 减少线路与 depot | [S4 Patch 1.1.X](https://cs2.paradoxwikis.com/Patch_1.1.X)、[S81](https://cs2.paradoxwikis.com/Services) | `[游戏机制]` A |
| **票价敏感度**的具体弹性 | **官方没有；本轮也未找到可复现实测 → `[待验证]`** | — | `[待验证]` |
| 票价进入寻路成本的**机制** | 官方明文："Ticket price affects citizens' pathfinding calculations… **money can sway them between public transportation and private vehicle usage**"（来源：[S13 Transportation](https://cs2.paradoxwikis.com/Transportation)） | S13 | `[游戏机制]` A |
| **票价 0 的官方定位** | 触发官方电台事件 "Free public transport"（1.1.10f1 修复）→ 免费公交是官方预期玩法路径 | [S4](https://cs2.paradoxwikis.com/Patch_1.1.X) | `[游戏机制]` A |
| 出租车**最低起步价**政策 | `Taxi Minimum Fare`（里程碑 4）"A minimum charge is applied for each taxi ride. **This is added to the fare based on the actual distance traveled.**" | [S83](https://cs2.paradoxwikis.com/Policies) | `[游戏机制]` A |
| 各车型**单车成本**（车辆本身月费） | **官方没有"每辆车每月多少钱"这一项**；官方只给 depot/车站的建造费与月维护费 + `maintenanceDuration` 字段。→ `[待验证]` | [S15](https://cs2.paradoxwikis.com/Service_buildings) | `[待验证]` |
| **各方式单车载客量** | **官方仍未公布**（`00-sources.md` §三 缺口 #1）。唯一官方数字仍是**渡轮 100 人**（[S13](https://cs2.paradoxwikis.com/Transportation)）。⭐ **但"容量归一"另有一套取值**：公交 **80** / 地铁 **1080** / 客运火车 **840** 人/辆 = **游戏内可信数值（玩家提供，`[玩家实测]`）**，**只用于线路效率的容量归一与跨方式排序**，不得当作官方数值引用；电车 / 单轨 / 渡轮 / 缆车 / 客船 / 客机**容量未知 → 不做归一**（见 `40-number-tables.md` 第 1.3 节）。**社区"一班地铁八九百人"仍禁止引用**（`00-sources.md` C19） | [S13](https://cs2.paradoxwikis.com/Transportation)、[S82](https://csl2wiki.wicurio.com/index.php?%E4%BA%A4%E9%80%9A) | `[玩家实测]`（归一用）／`[待验证]`（官方口径） |

### 1.4 车队规模的"隐藏约束"（本轮新证据，可直接改算法）

| 约束 | 数值 | 来源 | → 对 CSL2 建议意味着什么 |
|---|---|---|---|
| **额外车库的性价比** | 公交：`Extra Garage` 让维护费约 ×1.5，车辆数只 ×1.4 → **"微妙に釣り合っていない"（略不划算）**（来源：[S82](https://csl2wiki.wicurio.com/index.php?%E4%BA%A4%E9%80%9A)，可信度 **C**） | S82 | **加车优先加"线路车辆数"（免费），撞到 depot 上限再考虑升级车库**；建**第二个 depot** 往往比升级 Extra Garage 更划算（新 depot 还多一个车辆刷新点、位置更近） |
| **电车扩容手段极少** | "**台数増加のアップグレードはユニーク分しかない**ので運用数は路面電車車庫の数に比例する"（增加车辆数的升级只有独特建筑那一份，所以可运营车辆数与电车车库数量成正比）（来源：[S82](https://csl2wiki.wicurio.com/index.php?%E4%BA%A4%E9%80%9A)，可信度 **C**） | S82 | **电车扩容 = 必须多建 Tram Depot**（每个 10 辆，官方）。规划电车走廊时**先预留第二个车库的地** |
| **电车车库的占地** | 车库本身占地 = "公交库宽度 × 约两倍进深"，却只能提供不到一半的车辆数（来源：[S82](https://csl2wiki.wicurio.com/index.php?%E4%BA%A4%E9%80%9A)，可信度 **C**） | S82 | **电车的"每公顷运力"低于公交**，在土地紧张的城市要慎用 |

### 1.5 公交专用道 / 公交优先 —— 诚实结论

- **官方给的工具**：Replace 工具加公交车道；官方明文可以"create roads **exclusively for public transport vehicles** such as buses"；独立公交道 1.2.5f1 起可加照明（未加照明时不输电）。
- **官方的效果表述**：**无任何定量收益**。官方从未给出"专用道能提速多少 / 提升多少客流"。
- **社区侧**：搜索结果里反复出现"公交车道没用 / 大家都在用公交车道"这类**互相矛盾的主观帖**（Steam 讨论区，本抓取器不可达，未采信）。
- **`[待验证]`：公交专用道 / 独立公交道的定量收益，本轮仍未找到可复现实测。**
- → **对 CSL2 建议意味着什么**：可以推荐"给公交做专用道/独立公交道"，但**必须说明这是机制推导（公交受拥堵影响、独立路权不受），不是实测收益**；并且**验收方式只能是"改动前后同一条线的月乘客数 + 使用率"**，不能承诺百分比。

### 1.6 环线 vs 往返线

| 结论 | 依据 | 标记 |
|---|---|---|
| **1.6.0f1 起掉头成本被合理化**："Fixed legal U-turn costs to allow citizens to use dedicated lanes more flexibly and **lowered illegal U-turn costs** to match intended limits."（来源：[S9 Patch 1.6.X](https://cs2.paradoxwikis.com/Patch_1.6.X)，可信度 **A**） | S9 | `[游戏机制]` A |
| → **1.6.0f1 之前，端头折返式线路在掉头处被额外惩罚；之后折返更可行但仍然不是零成本**。 | 同上 | `[机制推导]` |
| 环线/往返的**定量对比**：**无来源 → `[待验证]`** | — | `[待验证]` |

---

## 2. 货运与产业链（本轮补齐最薄的一环）

> ⚠️ **范围限制（本节专用）：货运港口、货运铁路、货运航线不与客运数据一并分析。**
> * 本节的所有动作与判据都**只在工业部分作辅助分析**使用（报告的「**工业部分 · 货运终端与产业链**」
>   小节，排在 §8.2 真实税基与建筑等级之后）。
> * **不得把本节数据（货运线路的车辆/站数/储位/终端数）写成客运运力、客运站点或线网规模**；
>   也不得把它们并入 §4 线路效率、§5 走廊重叠、§6 车站腹地、§15 站点覆盖率、§0.5 基础体检。
> * **反过来也成立**：**不得用客运数据（乘客数 / 配车数 / 站距）为货运与工业布局辩护或否定**。
> * 数据口径：货运线路 = `Route_Centerline.Object == RouteCargo`；货运站点/终端 =
>   `StopCargoTrain` / `StopCargoShip` / `BuildingCargo*`（**同一座设施常有多条 POI 记录，须按距离归并**）。
> * 本节内容与 **§1 公交线网运营**（客运）**不共用任何数字**。

### 2.1 官方机制（一手，全部可引用）

| 机制 | 原文要点 | 来源 | → 对 CSL2 建议意味着什么 |
|---|---|---|---|
| **货运终端 = 免费配送中心** | "**Even with no cargo lines**, companies ordering resources can use the station's storage facilities to drop off and pick up resources and goods, **the facility working like a distribution center**." | [S13](https://cs2.paradoxwikis.com/Transportation) `[游戏机制]` A | **"建一个 Cargo Train Terminal 但先不开货运线"是投产比最高的一步**：立刻给周边工业/商业多一个取货点，不增加线路运营成本 |
| **货运终端必然制造卡车洪流** | "Due to large amounts of resources being transported to and from the terminal, **it can generate a lot of truck traffic**. Therefore it is **crucial to prioritize the road connections** to the terminal to avoid traffic jams." | [S13](https://cs2.paradoxwikis.com/Transportation) `[游戏机制]` A | **货运终端的选址第一约束不是"离工业近"，而是"离主干道/高速匝道近且不需穿城"**。建在城边 + 专用联络道 |
| **铁路运货比卡车便宜且快** | "companies send their goods to the terminal as **it is cheaper and faster to ship goods on trains than to haul them to the Outside Connections by trucks**." | [S13](https://cs2.paradoxwikis.com/Transportation) `[游戏机制]` A | **出口走铁路/船，不要走卡车**。卡车只做"最后一公里"（终端↔厂/店） |
| **本地销售永远更赚** | "**selling to the local market is always more profitable**"；持续出口"will further decrease the profit as they have to ship the goods **further and further to new buyers**, simulating the eventual oversaturation of the market." | [S10 Zoning](https://cs2.paradoxwikis.com/Zoning) `[游戏机制]` A | **别把城市做成"出口加工区"**。每一份"本地生产→本地消费"的配对都在提高公司利润=税基 |
| **运输成本随距离上升（官方寻路侧）** | "the cost of resources they transport **increases the further away they are delivered**. As a result, selling resources and goods locally is more cost-efficient… **Transporting resources and goods out of the city is costly and can greatly decrease the profitability of companies.**" | [S12 Traffic](https://cs2.paradoxwikis.com/Traffic) `[游戏机制]` A | **工业与它的下游（加工厂/仓库/商店）之间的实际路网距离，直接扣公司利润** → **"缩短路网距离"就是涨税**。这是本轮最硬的一条因果 |
| **仓库的作用（官方明文）** | "Companies tend to have **relatively small storage facilities** and seek to sell all their products as quickly as possible. **Warehouses allow more flexibility and time to seek suitable new buyers** if no one is currently available, **while still keeping production going**." | [S10 Zoning](https://cs2.paradoxwikis.com/Zoning) `[游戏机制]` A | **仓库不是"物流装饰"，它是公司的"现金流缓冲垫"**：没有仓库，工厂会因为找不到买家而停产 → 利润↓ → 税收↓。**在专业化工区与加工区之间一定要有仓库** |
| **进口会压垮路网** | "industries and commercial zones contribute to traffic congestion, **especially if goods must be imported from outside the town due to a lack of local industrial zones**. Importing goods **does not affect the revenue** of these industries, but **does affect gameplay by requiring a well-developed roadway grid**." | [S10 Zoning](https://cs2.paradoxwikis.com/Zoning) `[游戏机制]` A | **进口的代价全在路网上，不在钱上** → "缺工业用地"最终表现为**堵车**而不是**亏损**。诊断"为什么堵"时要把"进口比例"列进嫌疑清单 |
| **专业化工业的硬性选址规则** | ① 必须先放**中心建筑**，再放**开采区的角点**，角点"**limited to a ring around the central building**"（被限制在中心建筑周围的一圈内）；② **Companies will never move into a specialized industry zone that requires a resource the zone does not have access to**；③ **Livestock Farming 与 Stone Mining 不需要任何自然资源**；④ 专业化建筑**不会变成 abandoned** | [S10 Zoning](https://cs2.paradoxwikis.com/Zoning) `[游戏机制]` A | **Livestock（牲畜）与 Stone（石矿）是唯一两个"不看资源点就能开"的专业化工业** → **前期涨岗位/涨材料的最便宜选择**，尤其在地图上找不到肥力/森林/矿点时 |
| **专业化工业的里程碑与污染** | 完整表（本轮首次完整抓取）：Livestock M3（噪声低）/ Stone M3（噪声中+地面中+空气中）/ Grain M4（需 Fertile Land，噪声低）/ Forestry M4（需 Forest，噪声中）/ Vegetable M5（需 Fertile Land）/ Coal M5（需 Ore）/ Textile Fiber M6（需 Fertile Land）/ Ore M7（需 Ore）/ Oil M8（需 Oil，**火灾风险高于其它**） | [S10 Zoning](https://cs2.paradoxwikis.com/Zoning) `[游戏机制]` A | **农业类（Livestock/Grain/Vegetable/Textile）噪声只有 Low**，可以更贴近住宅；**矿业/石油/林业是 Medium**，必须留缓冲区 |
| **专业化加成上限** | **City Production Specialization**：对相关材料产量大的商业/工业给加成，**默认上限 115% @ 10 kt**（来源：[S17 Economy](https://cs2.paradoxwikis.com/Economy)） | S17 `[游戏机制]` A | **10 kt 是专业化加成的封顶产量**。超过 10 kt 再堆同类产量，**看不到额外效率** → 应该把资源投到**另一条产业链**或**加工环节** |
| **公司按"最紧缺资源"优先租铺** | 1.6.2f1："**Companies producing the most-needed resources in the city are now prioritized when renting properties**"（来源：[S9 Patch 1.6.X](https://cs2.paradoxwikis.com/Patch_1.6.X)） | S9 `[游戏机制]` A | 1.6.2f1 起**空置商铺会自动被"城市最缺的东西"填满** → 缺什么就别手动划，等待即可；**反过来，想引导产业结构就用税收分级**（按产品类型调税） |
| **货运终端储位** | Cargo Train Terminal / Cargo Transfer Station / Cargo Harbor = **15.5 kt**；International Airport 的货运终端 = **800 t**；Airport 无货运终端时 = **0 kg**。货船 **1000 吨**（船），飞机货运"relatively low capacity but the fastest"（来源：[S13](https://cs2.paradoxwikis.com/Transportation)） | S13 `[游戏机制]` A | **空运货运是"轻贵急"专用，别用来扛大宗**。大宗一律走**铁路/港口（15.5 kt 储位）** |
| **Cargo Harbor 可升级铁路连接** | "the Cargo Harbor can be upgraded with a **railway connection**, allowing trains to transport cargo directly to and from the harbor."（来源：[S13](https://cs2.paradoxwikis.com/Transportation)） | S13 `[游戏机制]` A | **港口 + 铁路连接 = 海铁联运**，把港口的卡车需求转成铁路 → **直接削减穿城卡车** |
| **进口触发阈值（社区）** | "当这些建筑仓储**低于 50%** 且本地无法补货时，它们会开始从外部连接进口资源"（来源：[S60 vgover 物流与仓储机制](https://www.vgover.com/news/88101)，2024-02-07，可信度 **C**） | S60 `[社区实证]` C | 仍标 `[社区实证]`。**可用作"为什么突然多了一堆卡车"的解释**，不得当机制引用 |

### 2.2 减少卡车穿城的可执行清单（全部有依据）

| 动作 | 依据 | 标记 |
|---|---|---|
| ① 把 Cargo Train Terminal / Cargo Harbor 建在**城市边缘 + 直连高速匝道**，不要建在城中心 | 官方："crucial to prioritize the road connections to the terminal"；且运输成本随距离上升 | `[游戏机制]` A |
| ② 给货运终端**单独开一条联络道**，不让货车与通勤车共用主干道 | 同上（"a lot of truck traffic"） | `[机制推导]` |
| ③ 出口改走**铁路 / 港口**（15.5 kt 储位），卡车只跑最后一公里 | 官方："cheaper and faster to ship goods on trains than to haul them to the Outside Connections by trucks" | `[游戏机制]` A |
| ④ **港口加 Railway Connection 升级**，做海铁联运 | 官方原文 | `[游戏机制]` A |
| ⑤ 用**区域政策 `Heavy Traffic Ban`**（里程碑 6）把重车挡在住宅/老城区外（"Trucks and other heavy vehicles are forbidden from entering the district… **Highways remain unaffected**"） | [S83 Policies](https://cs2.paradoxwikis.com/Policies) `[游戏机制]` A | `[游戏机制]` A |
| ⑥ **补齐本地产业链**，减少进口（进口的代价是路网） | 官方 Zoning 页明文 | `[游戏机制]` A |
| ⑦ 公司之间**用仓库做缓冲**，避免"找不到买家就停产 → 疯狂找外部连接" | 官方 Zoning 页明文 | `[游戏机制]` A |
| ⑧ 用**区域政策 `Advanced Pollution Management`**（里程碑 6）压低工业空气/地面污染（代价：垃圾变多） | [S83](https://cs2.paradoxwikis.com/Policies) | `[游戏机制]` A |

> ⚠️ **陷阱**：`Heavy Traffic Ban` 会**同时挡住城市服务车辆与送货**吗？官方原文只说 "Trucks and other heavy vehicles are forbidden from entering the district"。**"是否影响商业补货"官方未明确 → `[待验证]`**，建议玩家**先在一个小区试，观察该区商铺的备货/效率有没有掉**。

---

## 3. 土地利用效率的实操

### 3.1 尺度基准（本轮首次拿到官方精确值，可写进算法）

| 项 | 官方值 | 来源 | → 对 CSL2 建议意味着什么 |
|---|---|---|---|
| **1 个分区格 = 8 m** | "Snap to zoning cell length: Allows snapping to the zoning cell length, in other words **snaps every 8 meters (8.7 yards)**." | [S11 Roads](https://cs2.paradoxwikis.com/Roads) `[游戏机制]` A | **1 格 = 8×8 = 64 m²**；`Service range 2500` → **约 39 格**。从此"格/米"可以互换，**城市报告里的"格"可以直接换算成公顷** |
| **地块尺寸范围（官方表）** | 低密度住宅 4–24 格，2×2 ~ 4×6；中密度联排 2–6 格，1×2 ~ 1×6；中密度住宅 4–36 格，2×2 ~ 6×6；**高密度住宅 4–36 格，2×2 ~ 6×6**；混合住宅 4–36 格，2×2 ~ 6×6；低密度商业 4–30 格，2×2 ~ 5×6；**高密度商业 4–36 格，2×2 ~ 6×6**；低租金住宅 4–36 格，2×2 ~ 6×6；工业 4–36 格，2×2 ~ 6×6；低密度办公 4–36 格，2×2 ~ 6×6；高密度办公 4–36 格，2×2 ~ 6×6 | [S10 Zoning](https://cs2.paradoxwikis.com/Zoning)（`action=raw` 原文） | **"中密度住宅"与"高密度住宅"的地块尺寸范围完全相同（2×2 ~ 6×6）** → 单从地块看不出密度差，**密度差体现在建筑等级与户数**。报告中不要用地块尺寸推断密度 |
| **高密度必然带来拥堵** | "**High Density building generally cause higher traffic, and cause congestion on small roads.** If you're looking to build a massive city, and not crammed into one space, **use low density, as it needs less services, and takes up a larger space than the high density**." | [S10 Zoning](https://cs2.paradoxwikis.com/Zoning) `[游戏机制]` A | **官方直接给了"低密度服务需求更少"这条**：低密度不只是"人均税多 + 大房子幸福"，还**更省服务**。三条同向 → **低密度的真实优势被严重低估** |

### 3.2 混合用途（Mixed Housing）

- 官方定义："**Apartment buildings with commercial space on the bottom and apartments on top.**"（里程碑 5，地块 2×2 ~ 6×6）（来源：[S10 Zoning](https://cs2.paradoxwikis.com/Zoning)）`[游戏机制]` A
- **官方没有给出 Mixed Housing 的税收/岗位产出数字** → `[待验证]`。
- → **对 CSL2 建议意味着什么**：混合住宅是**唯一"一块地同时产生住宅税基 + 商业税基"**的分区类型，且**底层商业的顾客就在楼上**（商业的官方加分项"thrive close to residential areas as they provide them with customers"直接命中）。**在主城中心区用它替代纯高密度住宅**是最直接的"单位土地税基"提升手段。**但注意**：`city_report.py` 目前没把 `Residential, Commercial` 并入住宅口径（见 `46` T9），所以**报告会低估混合用途地块的价值**。

### 3.3 污染与噪声的影响半径（诚实结论）

| 项 | 结论 | 来源 | 标记 |
|---|---|---|---|
| 工业地面/空气污染的**具体米数半径** | **官方从未给出 → 维持 `[待验证]`**。1.3.6f1 只说"量与扩散半径双双上调" | [S6](https://cs2.paradoxwikis.com/Patch_1.3.X) | `[待验证]` |
| 噪声对住宅的影响 | "Noise lowers the citizens' **well-being** if near **residential** zones"；"On roads, a general rule is '**the heavier the traffic, the heavier the noise**'。**Each type of vehicle has a noise pollution rating**… **Large trucks will typically create more noise**。" | [S21 Pollution](https://cs2.paradoxwikis.com/Pollution) `[游戏机制]` A | `[游戏机制]` A |
| **卡车噪声 > 小汽车噪声（官方）** | 同上。→ **货运走廊旁边放住宅，比通勤走廊旁边放住宅更糟** | S21 | `[游戏机制]` A |
| 降噪手段（官方） | ① 带树的路 + 高速隔音墙；② **地下道路的车辆噪声被完全抑制**；③ **高架道路会放大噪声**；④ 树木只有"很弱的对数级"降噪 | [S21](https://cs2.paradoxwikis.com/Pollution) | `[游戏机制]` A |
| **`Speed Bumps` 政策"大幅降噪"** | "Reduces the speed of vehicles driving within the district. This lowers the chance of accidents and **brings noise pollution down significantly**."（里程碑 5，区域政策） | [S83](https://cs2.paradoxwikis.com/Policies) | `[游戏机制]` A |
| **机场噪声意外地小** | "意外と騒音範囲が小さく、飛行機で発生する騒音も**空港の敷地外なら無視できる程度**"（噪声范围意外地小，机场场地外基本可忽略）（可信度 **C**） | [S82](https://csl2wiki.wicurio.com/index.php?%E4%BA%A4%E9%80%9A) | `[攻略经验]` C |
| **大型道路降低周边地价** | 官方 Roads 页："Vehicles on larger roads also tend to generate more noise pollution and **decrease the land value around them**." | [S11](https://cs2.paradoxwikis.com/Roads) `[游戏机制]` A | `[游戏机制]` A |
| **低密度住宅是地价风险敞口最大的** | 官方 Zoning 页："Low density housing areas **can quickly become expensive**… since low density housing has **only one household per building, the increased rent falls on the single household entirely**." | [S10](https://cs2.paradoxwikis.com/Zoning) `[游戏机制]` A | `[游戏机制]` A |

### 3.4 高密度 vs 低密度的"每格税基"——本轮仍无实测

> **明确结论（维持 `45` §C3）**：官方**没有**每格税收数字，本轮**第 3 次**检索仍未找到任何**可复现**的"每格/每公顷税收"实测表。
> 能合法使用的仍只有官方的**方向性**结论 + 本项目的**代理指数**。
> → **给玩家建议时禁止给"高密度每格收 ₡X"这类数字。**

### 3.5 停车场与停车费（本轮拿到官方政策数值）

| 机制 | 官方值 / 原文 | 来源 | → 对 CSL2 建议意味着什么 |
|---|---|---|---|
| **路边停车费范围** | 区域政策 `Roadside Parking Fee`（里程碑 5）："The cost of parking can be adjusted with the slider from **₡1 to ₡50**" | [S83 Policies](https://cs2.paradoxwikis.com/Policies) `[游戏机制]` A | **路边停车费是"区域政策"，不是全局** → **可以只对市中心/堵点区收高费，外围保持免费**。这是**精细的空间杠杆** |
| **地块停车费范围** | 建筑政策 `Parking Fee`："A fee is charged for parking on this lot. The cost… from **₡1 to ₡50**" | [S83](https://cs2.paradoxwikis.com/Policies) `[游戏机制]` A | **停车场/停车楼可以逐个定价** → **路边费 > 地块费**是官方允许的"把车赶进停车场"组合 |
| **停车费进入寻路成本** | 官方 Traffic 页：Money 因子"comes into pathfinding choices in the form of **fuel usage and potential parking fees**. Citizens **weigh travel and parking costs and compare them to other travel options as well as walking**" | [S12 Traffic](https://cs2.paradoxwikis.com/Traffic) `[游戏机制]` A | **停车费是"停车 + 步行 + 其它方式"三者比价的一个输入项** → 提高路边停车费**真的会改变出行决策**（机制上有依据），不只是收钱 |
| **加宽人行道会吃掉路边停车位** | "Wide sidewalks or grass can be added… to create more space for pedestrians **at the cost of removing roadside parking spaces**." | [S11](https://cs2.paradoxwikis.com/Roads) `[游戏机制]` A | **"宽人行道"与"路边停车"是互斥的** → 在需要人行道容量的枢纽周边，等于自动消灭路边停车 |
| **停车可用性影响寻路** | "finding a suitable **parking spot** or public transport stop to get off at" 是 Comfort 的一部分（长者最看重） | [S12](https://cs2.paradoxwikis.com/Traffic) | `[游戏机制]` A |
| **"路边停车费拉高 → 逼进停车场 → 释放车道 + 增收入"** | 中文攻略站主张"市民 AI 倾向优先停在路边…把路边停车费拉高到明显高于停车场，用经济杠杆迫使 AI 放弃路边停车…还能增加财政收入"（来源：[S85 citiesskyline.com 堵车解决全攻略](https://citiesskyline.com/citiesskylinesgameguide/cities-skylines-2-traffic-fix)，2025-12-01，可信度 **C**） | S85 | **该主张的方向与官方机制一致（停车费进寻路成本），但"释放多少车道 / 增多少收入"无数据 → 只能作为"有机制依据的处方"，不得承诺量化收益** |

---

## 4. 交通通行能力的量化

### 4.1 官方**从未**给出通行能力数字（本轮第 3 次确认）

- 官方 Roads 页正文只有一句："**The larger the road, the higher the speed limit and traffic capacity.**" —— **无任何 pcu/h 或辆/小时数字**。
- 官方道路表只给：车道数、限速（双口径）、造价/维护（平地/高架/隧道三套）、**Noise / Air pollution factor**、是否可分区、是否带水电。
- → **`[待验证]` 维持**：任何"四车道 = X 辆/小时"都是社区估计，**禁止引用**。

### 4.2 官方明确、可写进算法的通行相关规则

| 规则 | 原文要点 | 来源 | → 对 CSL2 建议意味着什么 |
|---|---|---|---|
| **单行道 + 服务车辆** | "**Service vehicles cannot go against the flow of traffic** and so even if a building next to a fire station is on fire if it is the wrong way down a one-way road the fire trucks will have to take the long route. **Commercial and industrial buildings also require goods to be delivered and picked up, if they are unable to be serviced often enough on a one way road they may stop operating effectively.**" | [S11](https://cs2.paradoxwikis.com/Roads) `[游戏机制]` A | **单行道做"成对单行环路"时，必须双向都可达**。单行网里出现"只能出不能进"的商铺/工厂 → **它们会停止有效运营 → 利润↓ → 税收↓**。这是**单行道最容易被忽略的税收代价** |
| **单行道能减堵（官方也这么说）** | "One-way roads allow traffic in one direction only and **can decrease traffic congestion**… **Two-way roads** allow travel in both directions. These roads **can increase traffic congestion** but allow for less restricted pathing… so **small two-way roads make for ideal low traffic roads**." | [S11](https://cs2.paradoxwikis.com/Roads) `[游戏机制]` A | **低流量社区路用双向小路（官方推荐）**；**高流量走廊才用单行对**。别把整个社区做成单行网 |
| **路口可加装的官方工具** | Traffic lights / stop signs / No turn left、no straight、no turn right / Crosswalks / Wide sidewalks / Grass / Trees / Sound barriers（**只能加在高速上**）/ Lighting（**加在高速段上，并给低压输电能力**） | [S11](https://cs2.paradoxwikis.com/Roads) `[游戏机制]` A | **"禁左/禁直/禁右"是逐路段设置的** → 治堵不需要 Mod，官方工具够用。**隔音墙只能上高速**（干道旁边想要降噪只能用树，而树的效果是"很弱的对数级"） |
| **环岛** | 4 种尺寸：Small ₡200 / Medium ₡500 / Large ₡1000 / Very Large ₡1500（后三种需 Roundabouts 发展点）。官方行为描述："Vehicles entering the roundabout **usually give way** to those already on it but **will cut in front of another vehicle already on it if a suitable opportunity arises**." | [S11](https://cs2.paradoxwikis.com/Roads) `[游戏机制]` A | **官方承认环岛里有"插队"行为** → **环岛不是无条件优于信号路口**。`[待验证]`：环岛 vs 信号路口的定量对比，本轮未找到可复现实测 |
| **道路状况影响车速与事故** | "Road condition decreases over time… resulting in **slower travel speeds and a higher chance of traffic accidents**"；需要 Road Maintenance Depot（₡75.0K 建 / **₡15.0K/月**，10 辆维护车，"Poorly educated" 岗位 30） | [S11](https://cs2.paradoxwikis.com/Roads)、[S81 Services](https://cs2.paradoxwikis.com/Services) `[游戏机制]` A | **路况是"隐性通行能力"**：城市变大后，**不修路 = 全网限速打折 + 事故率上升**。一个 Road Maintenance Depot 是 ₡15K/月的"全网提速"投资，**通常比修一条新路便宜** |
| **事故概率的放大因子** | "increased by features such as **road conditions, lighting conditions, weather, and disasters**"；高速 `High-Speed Highways` 政策"accidents are **slightly more likely**" | [S12](https://cs2.paradoxwikis.com/Traffic)、[S83](https://cs2.paradoxwikis.com/Policies) `[游戏机制]` A | **高速提速政策有事故副作用** → 只在你真的需要城际高速通行时开 |
| **事故的处理链** | 事故现场需要**警察封锁 + 道路维护清理**；"Traffic will be blocked on the lanes that are affected… **potentially blocking the road if all lanes are blocked**"；堵久了 agent 会重算路径掉头绕行 | [S12](https://cs2.paradoxwikis.com/Traffic) `[游戏机制]` A | **一次事故能吃掉一整条路的全部车道** → 关键走廊必须有**平行备份路径**，这比"多一条车道"更抗事故 |

### 4.3 1.6.x 之后寻路与拥堵的改动（全部官方原文）

| 版本 | 改动 | → 对 CSL2 建议意味着什么 |
|---|---|---|
| **1.6.0f1** | **寻路距离上限按出行目的分设**：work / school / shopping / leisure 各用"a sensible range"；找不到路线的市民**搬离者直接传送出图、工人辞职、休闲者在家待着稍后重试** | **"超长通勤"从能忍变致命**。任何"住得远但能忍"的假设都失效 → **职住比与就近配比的权重必须上调** |
| **1.6.0f1** | 修复"市民**总是去库存最多的店，完全无视距离**" | 商业选址逻辑改为**距离参与决策** → **社区型商铺重新有生存空间**，"全城最大卖场通吃"的时代结束 |
| **1.6.0f1** | 修正合法掉头成本、**下调非法掉头成本** | 端头折返线更可行；路口微观行为变化 |
| **1.6.0f1** | **办公商品可从外部连接购买** | 办公区供应链松绑 |
| **1.6.0f1** | 商业需求略微下调（balancing） | 不要用旧版本的商业需求强度做基线 |
| **1.6.2f1** | **公司按"城市最紧缺资源"优先租铺** | 空置商铺自动补短板；**产业结构引导要靠税收分级，不是手动划区** |
| **1.6.2f1** | **垃圾车会更聪明地为目的地预留容量**、跳过垃圾极少的建筑 | 垃圾服务效率提升 |
| **1.6.2f1** | **垃圾对幸福度影响加大** | 垃圾成为幸福度的**更重要因子** → 垃圾覆盖的优先级上调 |
| **1.6.2f1** | **市民幸福度/购物/休闲从 `wealth` 改为 `income`** | 任何用财富做代理的算法都要改 |
| **1.6.2f1** | 住宅需求计算**纳入城市规模**（修复超大城住宅需求不足） | 大城市的住宅需求条不再"假性枯竭" |

### 4.4 车道连接（Lane Connector）

- **`[待验证]`**：本轮**未找到**任何可复现的"车道连接前后通行量对比"实测；官方 Wiki 的 Roads/Traffic 页**没有 Lane Connector 章节**（官方把它放在游戏内工具里，没有 Wiki 文档）。
- **可确证的相邻事实**：官方提供了**逐路段的禁左/禁直/禁右**标志（Road Attachments），这与 Lane Connector 是**同一类"限制转向"手段**，且有官方文档。
- → **对 CSL2 建议意味着什么**：**优先用官方的"禁转标志"解决转向冲突**（有官方文档、行为可预期、无需 Mod）；Lane Connector 只在"禁转标志解决不了"时用，且**必须先备份存档**（社区长期反馈其行为不稳定，但本轮无可靠来源 → 不写成结论）。

### 4.5 路网层级（社区口径，低可信度）

- `[攻略经验]`：中文攻略主张"**道路分流**：规划主干道与支路系统，将过境车辆与抵达车辆分离"、"**地下停车场**减少路面违停"、"**立体交叉**处理复杂路口"（来源：[S85](https://citiesskyline.com/citiesskylinesgameguide/cities-skylines-2-traffic-fix)，可信度 **C**）。
- `[攻略经验]`：新西兰规划博客实测记录（**有过程、无面板数字**）：把城市从 5 万加到 8 万人口"在既有footprint内加密（upzoning）"，**原本富余的交通设施迅速变成赤字**；作者的做法是**先做"优化计划"（路口升级 + 改公交车道位置），而不是直接上电车**，并明确写"one more lane shall fix it?"是伪命题（来源：[S86 Ben's Cities Traffic and Transit Optimisation Part 2](https://benscities.blog/2023/12/19/traffic-and-transit-optimisation-part-2-citiesskylines2-neo-south-auckland/)，2023-12-19，可信度 **C**）
- → **对 CSL2 建议意味着什么**：**加密（upzoning）会先把交通设施的余量吃光**。给玩家做"加密/提升密度"建议时，**必须同时给出交通侧的配套升级**，否则加密本身会把城市推入拥堵 → 幸福度↓ → 人口流失 → 税基崩。

---

## 5. 本轮**未攻克**的项（诚实登记）

| # | 缺口 | 状态 |
|---|---|---|
| 1 | **各类道路的 pcu/h 通行能力** | 官方无，社区无可复现实测 → `[待验证]`（第 3 次确认） |
| 2 | **各交通方式单车载客量**（bus/tram/subway/train/ship/plane） | 官方无（仅渡轮 100 人）→ `[待验证]`。⭐ **容量归一值**：公交 **80** / 地铁 **1080** / 客运火车 **840** 人/辆（**游戏内可信数值，玩家提供**，见 `40-number-tables.md` 第 1.3 节）；其余方式**不做归一** |
| 3 | **每格/每公顷税收产出实测表** | 官方无，社区无可复现实测 → `[待验证]`（第 3 次确认） |
| 4 | **环岛 vs 信号路口的定量通行对比** | 未找到 → `[待验证]` |
| 5 | **Lane Connector 的定量效果与已知 bug 清单** | 官方无文档，本轮无可信来源 → `[待验证]` |
| 6 | **公交专用道的定量收益** | 未找到 → `[待验证]` |
| 7 | **仓库（Warehouse）的具体储位数与车辆数** | 本轮未抓到官方表；1.3.6f1 已确认车辆 3→10 → 储位 `[待验证]` |
| 8 | **`Heavy Traffic Ban` 是否影响商业补货** | 官方未明确 → `[待验证]` |
| 9 | **税率"甜蜜点"** | 仍未找到可复现实测（见 `48` 的 C16 结论） |
| 10 | 官方**难度模式**对维护费的具体倍率 | 本轮**部分解决**：C17 的 0.75× 差已被证明**不是难度**，是 Wiki 两处数字本身不一致 → 见 `00-sources.md` C17 更新 |

---

## 6. 引用本文件时的硬性规则

1. **不要再用"Service range 单位不明"当借口**（C20 已结案：单位是米）；但**也不要把 Service range 当固定几何**——它随区内人口密度上升而缩小。
2. **`[攻略经验]`（可信度 C）一律不得单独作为处方依据**；必须能与官方机制交叉成立，否则只能写成"某个攻略站主张…，无游戏内数据支撑"。
3. **凡涉及"每格税收""通行能力 pcu/h""专用道提速百分比"——一律不得给数字**；**单车载客量只许用三个归一值**（公交 **80** / 地铁 **1080** / 客运火车 **840** 人/辆，**玩家提供**），且**只用于线路效率的容量归一**，不得当官方数值、也不得换算成"人次/h"型运能目标。
4. **凡涉及"减少卡车/货运"的建议，必须落到"路网距离"或"运输方式切换"这两个可验证的机制上**，不要写"优化物流"。
5. **凡涉及 1.6.0f1 起的寻路改动，必须写清版本前提**：1.6.0f1 之前"超长通勤"是可忍的，之后是致命的。
