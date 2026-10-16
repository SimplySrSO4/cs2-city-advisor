# 20 · 道路、路网层级、路口与拥堵、车道连接、停车、货运

> 适用版本：以 **1.6.2f1** 为基准。表格数值来自官方 Wiki 的**自动生成表格（标注 1.6）**。
> 每条重要结论后附 `（来源：URL）`。

---

## 1. 道路分级总览

官方把道路分为 **Small Roads / Medium Roads / Large Roads / Highways** 四类（外加 Pathways 步道、Train/Tram/Subway 轨道）。

**通用规则（可确证）**：
- 除高速外，全部道路自带 **40 MW 低压输电**与**供水/污水管道**；**桥梁不含管线**；高速需加装 **Lighting** 升级才有输电能力。（来源：https://cs2.paradoxwikis.com/Roads ）
- 道路越宽，**限速越高、通行能力越大，但噪音污染越大，且会降低周边地价**。（同上）
- **高速不允许临路分区**。（同上）
- 铺路时按 **zoning cell = 8 m** 吸附（"snap to zoning cell length … snaps every 8 meters"）。→ **1 格 = 8 m**，这是把游戏内距离换算成米的唯一官方锚点。（同上）
- 高程步进可选 **1.25 / 2.50 / 5.00 / 10.00 m**。平行模式偏移 0.25~12 格。（同上）

### 1.1 限速的"双口径"陷阱（必读）
Wiki 表格的限速列按**欧洲主题**显示，脚注给出**内部限速值**，北美主题显示值更低：

| 内部限速 | 欧洲主题显示 | 北美主题显示 |
|---|---|---|
| 200.0 | 100 km/h（高速） | 65 km/h |
| 160.0 | 80 km/h | 55 km/h |
| 80.0 | 40 km/h（普通道路） | 30 km/h |
| 60.0 | 30 km/h（砂石路/巷道） | 25 km/h |
| 40.0 | 20 km/h（步行街） | 12 mph（约 19 km/h） |

（来源：https://cs2.paradoxwikis.com/Roads ，表格脚注）
> **给建议时必须问清主题**：同一张路网在北美主题下的实际通行能力低于欧洲主题。

### 1.2 小道路（Small Roads）关键数值

| 道路 | 车道 | 限速（EU） | 造价/km | 维护/km/月 | 噪音系数 |
|---|---|---|---|---|---|
| Two-Lane Road 双向两车道 | 2 | 40 km/h | ₡4.0K | ₡487 | 1× |
| Three-Lane Asymmetric 三车道不对称（2+1） | 3 | 40 km/h | ₡4.75K | ₡600 | 1× |
| One-Lane One-Way 单车道单向 | 1 | 40 km/h | ₡3.25K | ₡375 | 1× |
| Two-Lane One-Way 双车道单向 | 2 | 40 km/h | ₡4.0K | ₡487 | 1× |
| Three-Lane One-Way 三车道单向 | 3 | 40 km/h | ₡4.75K | ₡600 | 1× |
| **Gravel Road 砂石路** | 2 | 30 km/h | ₡2.5K | ₡412 | **2×** |
| Gravel One-Way 砂石单向 | 1 | 30 km/h | ₡2.0K | ₡262 | 2× |
| **Alley 巷道（无人行道）** | 2 | 30 km/h | ₡3.0K | ₡337 | 1× |
| One-Way Alley 单向巷道 | 1 | 30 km/h | ₡2.25K | ₡225 | 1× |
| Two-Lane Perpendicular Parking Road 垂直停车路 | 2 | 40 km/h | ₡4.0K | ₡487 | 1× |
| Two-Lane Angled Parking Road 斜列停车路 | 2 | 40 km/h | ₡4.0K | ₡487 | 1× |
| Two-Lane Divided Perpendicular Parking Road 带分隔垂直停车 | 2 | 40 km/h | ₡4.0K | ₡487 | 1× |
| One-Lane One-Way Perpendicular/Angled Parking Road | 1 | 40 km/h | ₡3.25K | ₡375 | 1× |
| Perpendicular / Angled Parking Alley | 2 | 30 km/h | ₡4.0K | ₡487 | 1× |
| One-Way Perpendicular/Angled Parking Alley | 1 | 30 km/h | ₡3.25K | ₡375 | 1× |
| **Pedestrian Street 步行街** | 2* | 20 km/h | ₡6.5K | ₡262 | **2×** |
| Small Pedestrian Street 小步行街 | 1* | 20 km/h | ₡4.0K | ₡188 | 2× |
| Medium Quay With Two-Way Road 中等岸壁路 | 2 | 40 km/h | — | — | — |

\* 步行街仅允许步行交通，**服务与配送车辆例外**。
（全部来源：https://cs2.paradoxwikis.com/Roads ，1.6 表格）
- **只有 3 车道及以上的道路可以设置交通信号灯**（表格中 "Can have traffic lights" 标记）。（同上）
- **1.2.0f1 新增**：8 条道路（2 条不对称高速、3 条不对称道路、单向巷道、单向砂石路、小步行街）与 12 条停车道路（6 垂直 + 6 斜列）。（来源：https://cs2.paradoxwikis.com/Patch_1.2.X ）

### 1.3 高速（Highways）
- 限速 100 km/h（EU）/ 65 km/h（NA），车道 3~4，**Highway rules = 是**，不允许临路分区，需 Lighting 升级才输电。
- 高架高速造价约 `₡13.5K + ₡5.25K/高程级`，维护 ₡2.02K/km/月。
- 1.3.6f1（Bridges & Ports）新增 10 座活动桥（含四车道高速双层升降桥）、2 座双层桥、8 座桥，以及 7 种岸壁。
（来源：https://cs2.paradoxwikis.com/Roads ；https://cs2.paradoxwikis.com/Patch_1.3.X ）

### 1.4 单向路：官方明确的代价
> "**Service vehicles cannot go against the flow of traffic** … even if a building next to a fire station is on fire, if it is the wrong way down a one-way road the fire trucks will have to take the long route. Commercial and industrial buildings also require goods to be delivered and picked up; if they are unable to be serviced often enough on a one way road they may stop operating effectively."
（来源：https://cs2.paradoxwikis.com/Roads ）

> **规划结论**：单向微循环只适合**支路级**路网；一旦让消防站、货站、仓库处于单向路的"逆行侧"，会出现隐性服务失败。做单向系统时**必须为每个地块保留至少一条双向或正确方向的进出路径**。

---

## 2. 路口与环岛

### 2.1 环岛
- 4 种尺寸：**Small ₡200 / Medium ₡500 / Large ₡1000 / Very Large ₡1500**（后三种需发展树 "Roundabouts" 节点）。
- 环岛车道数**由接入道路的车道数决定**。
- **官方明确的缺陷**："Vehicles entering the roundabout usually give way to those already on it **but will cut in front of another vehicle already on it if a suitable opportunity arises**."（进入环岛的车辆通常让行，但有机会就会抢行）→ **高流量多车道环岛必然出现抢行与拥堵**。
- 每种尺寸有 3 种中心装饰（草地 / 树丛 / 混凝土+树丛）。
- 1.2.0f1 新增 7 种环岛变体、3 种尽端（cul-de-sac）变体。
（来源：https://cs2.paradoxwikis.com/Roads ；https://cs2.paradoxwikis.com/Patch_1.2.X ）
- 1.2.5f1 修复"车辆在环岛内莫名消失"（多车道繁忙环岛与应急车辆更常见）。（来源：https://cs2.paradoxwikis.com/Patch_1.2.X ）

### 2.2 路口控制工具（Road Attachments）
左键添加 / 右键移除（来源：https://cs2.paradoxwikis.com/Roads ）：
- **Traffic lights 交通信号灯**、**Stop signs 停车让行牌**
- **No turn left / No straight ahead / No turn right** 禁转标志（作用于路段末端）
- **Crosswalks 人行横道**（在路段末端添加/移除过街设施）
- **Wide sidewalks 宽人行道** / **Grass 草地** —— 用**取消路边停车位**换取更多步行空间
- **Trees 行道树** / **Sound barriers 隔音墙** —— 降噪；**树只能放在普通道路、隔音墙只能放在高速**
- **Lighting 照明** —— 只能加在高速段上，作用是夜间安全 + 赋予低压输电能力

### 2.3 拥堵成因与对策（机制层面的可确证项）

> ⚠️⚠️ **先读这段：2026 年的补丁修掉了三个"看着像规划问题"的寻路缺陷。**
> 判断拥堵成因前**必须先对版本号**（详见 `101-2026-official-patch-log.md` §2.3 / §2.4）：
>
> | 版本 | 修掉的缺陷 | 官方原文要点 |
> |---|---|---|
> | **< 1.5.9f1** | **合法掉头成本为 0** | 「Previously, **the cost of a legal U-turn was 0**, so it was always considered a valid option when it came to routing」→ 车辆到处掉头 |
> | **< 1.5.9f1** | **变道太晚** | 「vehicles tend to **switch lanes too late**, which has also caused a lot of traffic jams… **especially noticeable with highway exit behavior**」 |
> | **< 1.6.0f1** | 市民**超长跨图出行** | 1.6.0f1 起「**pathfinding limits are now tailored per trip type**: work, school, shopping, and leisure」 |
> | **< 1.6.0f1** | 购物**无视距离** | 「citizens would always travel to the shop with the most stock, **completely ignoring distance**」 |
> | **< 1.5.7f1** | **公交在繁忙站点永久上客卡死** | 「buses and trams could get stuck in a **permanent boarding state** at busy stops… causing vehicle queues and despawning」 |
>
> **⇒ 在这些版本之前，"掉头多""最后一刻变道""高速出口堵"很可能是引擎行为，不是路网设计缺陷。**
> ⚠️ 另注意 **1.6.0f1 又把掉头成本回调了**（「Fixed legal U-turn costs… and **lowered illegal U-turn costs**」）
> —— 1.5.9f1 与 1.6.0f1 的掉头行为**不同，不要合并叙述**。

| 成因 | 机制依据 | 对策 |
|---|---|---|
| **车道数不足 / 高速匝道溢出** | 道路分级表中车道数决定通行能力 | 升级到更高分级；高速车流不进城 |
| **路口成为瓶颈** | 红绿灯只在 ≥3 车道可设；环岛存在"抢行"逻辑 | 减少路口数、用单向配对、用环岛替代小路口 |
| **左转冲突** | 提供 No turn left 工具，说明左转是设计上要消解的冲突 | 用禁左 + 右进右出（RIRO） |
| **路口过密 / 支路直接接入主干** | 官方未给最小间距数值 | **待验证**（无官方最小路口间距数值） |
| **路况差导致减速与事故** | "Poor road quality or excess snow slow down traffic and increase chance of traffic accidents" | 建 **Road Maintenance Depot** |
| **路边停车占用车道** | 停车路（Parking Road）/巷道会占用路侧空间 | 用停车场/停车楼把车移出道路；或改宽人行道（会取消路侧车位） |
| **事故堵塞车道** | 事故需**警察**勘察 + **道路维护**清障；全部车道被堵则整条路瘫痪 | 提高路况、加路灯、加隔音墙降噪 |
| **公交车造成额外拥堵** | 官方：同一站点服务多条线路时"车辆增多可能导致拥堵" | 用公交专用道/独立公交路；把大站换成枢纽 |
| **商业/工业货车** | 缺少本地工业时商品必须进口 → 需要发达路网 | 本地化产业链 + 货运火车站/码头分流 |
| **掉头 / 变道（**版本相关**）** | 见上方 ⚠️ 表：<1.5.9f1 掉头免费、变道过晚 | **先确认版本**；若已在 1.6.0f1+，才可归因于路网设计 |
| **车辆滞留公交站（**版本相关**）** | 1.6.2f1：「Fixed cars sometimes being left behind, **especially at transit stations**, when a citizen returns home using other means」 | <1.6.2f1 时公交站周边异常车辆**不要**当停车规划问题 |

（来源：https://cs2.paradoxwikis.com/Roads ；https://cs2.paradoxwikis.com/Traffic ；https://cs2.paradoxwikis.com/Zoning ；https://www.paradoxinteractive.com/games/cities-skylines-ii/features/public-cargo-transportation ）

### 2.4 事故与道路维护（可确证数值）
- 事故概率**按路段计算**，受**路况、照明、天气、灾害**影响。
- **Road Maintenance Depot**：造价 ₡75,000，维护 ₡15,000/月，**10 辆维护车**（Road / Snow / Vehicle 三类作业），可加 **Extra Garage**（₡4,000 + ₡7,500/月，**+5 辆**）。
- Road Maintenance 在冬季兼职**除雪**，并在事故后**清障**（警察先封锁现场）。
（来源：https://cs2.paradoxwikis.com/Roads ；https://cs2.paradoxwikis.com/Traffic ）

---

## 3. 交通 AI 与寻路（★ 术语纠正）

> **重要纠正**：用户任务书提到的 CS1 社区术语 **"利他/自私寻路"在 CSL2 中不存在**。CS2 官方模型是**四要素成本**，且**按年龄段改变主导因子**。（来源：https://cs2.paradoxwikis.com/Traffic 、https://cs2.paradoxwikis.com/Citizens ）

### 3.1 四要素（官方原文口径）
1. **Time 时间** —— **成人（Adults）的首要因子**。所有 agent 都倾向最快路线。例：小路更短但限速低，高速更长但更快 → agent 多数情况选高速。
2. **Comfort 舒适** —— **长者（Seniors）的首要因子**。包括路线是否平顺、**避免不必要的路口转弯**、以及**能否找到合适的停车位或公交站点下车**。每一项舒适度代价都直接累加进寻路成本。
3. **Money 金钱** —— **青少年（Teens）的首要因子**。体现为**燃油消耗**与**停车费**。市民会比较"出行+停车成本"与"其他方式"和"步行"。对配送车辆，**距离越远，其运输资源的成本越高**。
4. **Behavior 行为** —— agent 是否愿意做"危险"决策（例如掉头）。市民与配送车辆**不太愿意**为了省成本做危险决策；**应急车辆**的模型更宽松，可以违规掉头，且其他车辆**会在多车道路上变道让行**。

（来源：https://cs2.paradoxwikis.com/Traffic ；年龄与偏好 https://cs2.paradoxwikis.com/Cities 同源，实际见 https://cs2.paradoxwikis.com/Citizens ）

### 3.2 动态变道与路径重算
- agent 会**根据途中事件调整路线**：为避开事故车或停靠的服务车辆而**变道**，为应急车辆**让出空间**。
- 事故清障长时间造成拥堵时，agent 可能**重算路径并掉头**绕行。
（来源：https://cs2.paradoxwikis.com/Traffic ）

### 3.3 服务车辆调度算法（重要，决定"服务看起来不到位"的原因）
> "Service vehicles are ordered based on the **lowest overall pathfinding cost** and when new orders are made, they take into account **the distances of all applicable vehicles now and in the near future**（即这些车完成当前任务后会在哪里）."
（来源：https://cs2.paradoxwikis.com/Traffic ）
> **结论**：城市越大，"最近的空闲车"越不一定是派出去的那辆。看到"垃圾车从城市另一头跑过来"**不是 bug**，是未来位置预测的结果；缓解办法是**分布式布置服务建筑**而不是一座巨型设施。

### 3.4 路径计算的近期重要修正（版本敏感）
| 版本 | 改动 | 来源 |
|---|---|---|
| 1.1.10f1 | **提高车辆寻路对"直线路径"的偏好**，减少公交与电车在站间无谓绕行 | https://cs2.paradoxwikis.com/Patch_1.1.X |
| 1.5.9f1 | 车辆**减少不必要的掉头**；接近高速出口或路口时**更早选择转向车道** | https://cs2.paradoxwikis.com/Patch_1.5.X |
| 1.6.0f1 | **寻路距离上限按出行目的分别设定**（work / school / shopping / leisure 各有合理范围，此前是近乎无限共享上限）；修正合法掉头成本、下调非法掉头成本 | https://cs2.paradoxwikis.com/Patch_1.6.X |
| 1.6.0f1 | 修复"市民总是去备货最多的店，完全无视距离" | 同上 |
| 1.6.2f1 | 修复"市民回家改用其他方式后车被丢在公交站/中转站" | https://cs2.paradoxwikis.com/Patch_1.6.X |

> **1.6.0f1 的"按目的距离上限"是重大改动**：它把"超长通勤"从"可以忍受"变成"找不到路径就优雅失败"（搬离者直接出图、工人辞职、休闲者在家闲置重试）。**规划上必须保证居住—就业—商业—学校在各自合理半径内配对**。（来源：https://cs2.paradoxwikis.com/Patch_1.6.X ）
> **官方未公布具体上限数值 → 待验证。**

### 3.5 城际过境交通（容易被忽视的拥堵源）
- CSL2 模拟**城际之间**的交通（一个外部连接 → 另一个外部连接），**这部分交通不贡献城市经济**。
- 如果你在两个外部连接之间修了更短的路，过境车流会**改走你的城市**。
（来源：https://cs2.paradoxwikis.com/Traffic ）
> **对策**：城外建**绕城高速/外环**，并把入城匝道做成长间距，避免过境车流直接穿城。1.5.7f1 修复了"外部连接无法接非高速公路"的问题，因此**可以用普通道路接外部连接**（但会引入穿城车流）。（来源：https://cs2.paradoxwikis.com/Patch_1.5.X ）

---

## 4. 车道连接与变道（Lane connections）

**CSL2 没有 CS1 的 "Traffic Manager: President Edition 式车道连接矩阵"**。官方提供的车道级控制手段只有：
1. **路口附属物**：Traffic lights / Stop signs / **No turn left/straight/right**；
2. **道路类型本身的车道构成**：如 Three-Lane Asymmetric（2+1）"适合做路口转向车道"；
3. **单向路**：直接规定流向；
4. **1.5.9f1 的 AI 改进**：车辆会更早选择转向车道、减少无意义掉头。（来源：https://cs2.paradoxwikis.com/Patch_1.5.X ）
5. **1.6.0f1 修正合法/非法掉头成本**，让市民更灵活使用专用车道。（来源：https://cs2.paradoxwikis.com/Patch_1.6.X ）

> **实践含义**：想精细控制车道，游戏内只能靠"**换道路类型 + 禁转牌 + 单向 + 修改路口几何**"。需要真正的车道连接编辑必须依赖 Mod → **本次未找到该 Mod 的权威页面，待验证**。

---

## 5. 停车（Parking）

### 5.1 停车如何进入决策链
> "When residents and tourists plan their way around the city, their decision-making is **affected by the availability of parking in a manner similar to public transport options**."
（来源：https://cs2.paradoxwikis.com/Roads ）
具体机制：
- **钱**维度：燃油 + **停车费**（Teens 的首要因子之一）；
- **舒适**维度：**能否找到合适的停车位**（Seniors 首要因子的一部分）。
（来源：https://cs2.paradoxwikis.com/Traffic ）

### 5.2 停车费
| 类型 | 可调范围 | 解锁 |
|---|---|---|
| **Roadside Parking Fee（区域政策）** | ₡1 ~ ₡50 | 里程碑 5 |
| **Parking Fee（建筑级政策，每个停车场/停车楼）** | ₡1 ~ ₡50 | 建即生效 |
| 路边停车位（道路自带） | 由区域政策控制 | — |
| 停车场/停车楼**默认费率** | **10.0** | — |

（来源：https://cs2.paradoxwikis.com/Policies ；默认值 10.0 见 https://cs2.paradoxwikis.com/Roads 的 parking 表 `Default policies` 列）

### 5.3 停车设施（Roads 服务下的 Parking Areas）
按 `garageMarkerCapacity`（可理解为"建筑本体提供的车位/标记容量"）与尺寸分级（来源：https://cs2.paradoxwikis.com/Roads ，1.6 表格）：

| 设施 | 尺寸 | 造价 | 维护/月 | Comfort | garageMarkerCapacity |
|---|---|---|---|---|---|
| Motorcycle Parking Lot | 2×2 | ₡3.7K | ₡740 | 60 | 0 |
| Tiny Parking Lot | 3×2 | ₡3.7K | ₡740 | 50 | 0 |
| Small Single-Row Parking Lot | 6×2 | ₡4.0K | ₡800 | 50 | 0 |
| Modest Parking Lot | 5×3 | ₡9.0K | ₡1.8K | 50 | 0 |
| Canopy-Covered Parking Lot | 6×2 | ₡9.0K | ₡1.8K | 60 | 0 |
| Small Solar Panel-Covered Parking Lot | 3×6 | ₡14.0K | ₡2.8K | 60 | 0 |
| Small Parking Lot | 5×5 | ₡11.0K | ₡2.2K | 50 | 0 |
| Long Parking Lot | 3×8 | ₡11.0K | ₡2.2K | 50 | 0 |
| Medium Single-Row Parking Lot | 12×2 | ₡8.0K | ₡1.6K | 50 | 0 |
| Medium Parking Lot | 7×5 | ₡15.0K | ₡3.0K | 50 | 0 |
| Medium Solar Panel-Covered Parking Lot | 7×6 | ₡22.0K | ₡4.4K | 60 | 0 |
| Moderate Parking Lot | 9×5 | ₡20.0K | ₡4.0K | 50 | 0 |
| Wide Parking Lot | 16×3 | ₡17.0K | ₡3.4K | 50 | 0 |
| Large Parking Lot | 10×8 | ₡35.0K | ₡7.0K | 50 | 0 |
| Very Large Parking Lot | 18×10 | ₡80.0K | ₡16.0K | 50 | 0 |
| Small / Medium Gravel Parking Lot | 6×2 / 3×6 | ₡3.0K / ₡7.0K | ₡600 / ₡1.4K | **30** | 0 |
| Small Parking Building（2 层） | 3×6 | ₡40.0K | ₡8.0K | 60 | 0 |
| Multi-Level Parking Building（可加层） | 8×6 | ₡200.0K | ₡40.0K | 60 | 0 |
| Overground Parking Building（可加 Car Wash） | 12×14 | ₡150.0K | ₡30.0K | 60 | 0 |
| **Underground Parking Building** | 6×10 | ₡200.0K | ₡40.0K | 65 | **100** |
| **Automated Parking Building（塔式自动化）** | 13×9 | ₡630.0K | ₡65.0K | 75 | **416** |

**停车建筑的工作岗位与通勤**（同表）：
- 大部分停车设施 **Workplaces = 0**；Small Parking Lot / Large Parking Lot / Very Large Parking Lot / 停车楼类有 2–24 个岗位；Automated Parking Building 需 **Educated** 学历、12 个岗位。
- **全部停车设施都有 Evening shifts 25% / Night shifts 12.5%**（Automated 与部分升级项为 0%）。
- **噪音**：小型停车场 1000–2500，停车楼 3500–5000，Very Large 5000，摩托车停车 1500。
（来源：https://cs2.paradoxwikis.com/Roads ，1.6 表格）

### 5.4 自行车停车（1.4.2f1 引入）
| 设施 | 尺寸 | 造价 | 维护/月 | garageMarkerCapacity |
|---|---|---|---|---|
| Bicycle Parking Area / Small Bicycle Shelter | 1×1 | ₡900 / ₡1,000 | ₡180 / ₡200 | 0 |
| Small Bicycle Storage | 1×1 | ₡1.5K | ₡300 | 16 |
| Bicycle Parking Hall（可升级） | 5×2 | ₡7.2K | ₡1.44K | 60 |
| Large Bicycle Parking Hall（5×5） | 5×5 | ₡39.0K | ₡7.8K | 270 |
| **Underground Bicycle Parking Hall** | 2×3 | ₡54.24K | ₡10.8K | **400** |

（来源：https://cs2.paradoxwikis.com/Roads ；功能引入 https://cs2.paradoxwikis.com/Patch_1.4.X ）

### 5.5 服务车辆停车（1.2.0f1 新增）
1.2.0f1 新增 **Service Vehicle Parking**：服务建筑自带服务车辆停车位。**已知问题：已有的服务建筑需要重建才能获得新的服务车辆停车位。**（来源：https://cs2.paradoxwikis.com/Patch_1.2.X ）

---

## 6. 货运（Cargo）

> ⚠️ **范围限制（本节专用）：货运港口、货运铁路、货运航线不与客运数据一并分析。**
> 本节的车数 / 站数 / 储位 / 终端数据**只在工业部分做辅助分析**
> （`SKILL.md` §2「货运与产业链」、`47` §2；报告里排在 §8.2 真实税基之后的工业小节）。
> **不得**并入客运口径（§4 线路效率 / §5 走廊重叠 / §6 车站腹地 / §15 站点覆盖），
> 也**不得**用客运数据（乘客数 / 配车数 / 站距）论证货运与工业布局。
> 数据口径：货运线路 = `Route_Centerline.Object == RouteCargo`；货运终端 = `StopCargoTrain` /
> `StopCargoShip` / `BuildingCargo*`（**同一座设施常有多条 POI 记录，须按距离归并**）。

### 6.1 货运通道的定位
| 方式 | 容量 | 特点 |
|---|---|---|
| 货车 / 面包车 | 按资源与车种 | 受城市交通影响；短途配送主力 |
| **货运火车** | 火车 | 陆上资源运输骨干；从外部连接拉货到终端，再由本地货车配送；**比卡车拖到外部连接更便宜更快** |
| **货船** | **1000 吨** | 比火车慢，但**完全不受道路交通影响** |
| **货机** | 相对小 | 最快，不受城内交通影响、不依赖水道 |

（来源：https://cs2.paradoxwikis.com/Transportation ；1,000 吨见 https://www.paradoxinteractive.com/games/cities-skylines-ii/features/public-cargo-transportation ）

### 6.2 货运建筑与储位
| 建筑 | 造价 | 维护/月 | 储位 |
|---|---|---|---|
| Cargo Train Terminal 货运火车站 | ₡150K | ₡15K | **15.5 kt** |
| Cargo Transfer Station 货运中转站（贯通式） | ₡200K | ₡20K | 15.5 kt |
| Cargo Harbor 货运码头 | ₡490K | ₡33.5K | 15.5 kt |
| Airport Cargo Train Terminal 机场货运火车终端（升级） | ₡500K | ₡31K | 7.2 kt |
| International Airport 内部货运储位 | — | — | 800 t |
| Hotel/仓库升级（Terminal / Harbor Warehouse） | ₡50K / ₡100K | ₡6K / ₡12.5K | **7.5 kt（1.3.6f1 下调，原为更大）** |

（来源：https://cs2.paradoxwikis.com/Service_buildings ；下调见 https://cs2.paradoxwikis.com/Patch_1.3.X ）
- **Cargo Harbor 可以升级 Railway Connection**，让火车直接进出码头。**Cargo Train Terminal 与 Cargo Harbor 即使不开线路也能当配送中心用。**（来源：https://cs2.paradoxwikis.com/Transportation ）
- **Bridges & Ports（1.3.6f1）** 新增 3 种规模的港口（Small ₡100K / Medium ₡200K / Large ₡400K）与 **23 种港口升级**：集装箱堆场、仓库、罐区、散货堆场、集装箱起重机、**多式联运火车终端（Intermodal Train Terminal，需 50,000,000 吨海运货物解锁）**、客运码头、员工食堂、港口安保、应急响应、辅助闸口。（来源：https://cs2.paradoxwikis.com/Service_buildings ；DLC 内容 https://cs2.paradoxwikis.com/Patch_1.3.X ）
- **港口的路侧储存升级**（Storage Yard / Container Yard / Warehouse / Tank Farm / Bulk Storage Yard）**储位差异巨大**：Small Container Yard 3,000,000 → Large Bulk Storage Yard 34,400,000（单位同表格 `Storage limit` 字段）。（来源：https://cs2.paradoxwikis.com/Service_buildings ）

### 6.3 货运对交通的影响与对策
- **货运终端会产生大量货车流量**；官方明确要求"优先处理通往终端的道路连接，避免堵车"。（来源：https://cs2.paradoxwikis.com/Transportation ）
- **1.3.6f1 起建筑升级需要资源配送**，导致**短期内货车流量显著上升**（官方明确提示"这是预期的，会随升级消化而正常化"）。（来源：https://cs2.paradoxwikis.com/Patch_1.3.X ）
- **1.4.2f1** 把升级材料的配送改为"一车多点、途中接受新请求"，并把 warehouses 数量从 3 提到 10 辆（1.3.6f1）。（来源：https://cs2.paradoxwikis.com/Patch_1.4.X 、https://cs2.paradoxwikis.com/Patch_1.3.X ）
- **1.6.2f1** 改进垃圾车逻辑（预留目的地容量、跳过垃圾极少的建筑）。（来源：https://cs2.paradoxwikis.com/Patch_1.6.X ）

### 6.4 货运规划清单
1. **重货本地化**（Stone / Steel / Coal / Ore 等）——官方说明"重的资源运输成本高，最好本地生产"。（来源：https://www.paradoxinteractive.com/games/cities-skylines-ii/features/economy-production ）
2. **入城货运节点外置**：把 Cargo Train Terminal / Cargo Harbor 放在**城市边缘 + 高速匝道直连 + 独立货车通道**，避免货车穿越居住区。
3. **用"重车禁行"政策保护居住区**（里程碑 6，高速不受影响）。（来源：https://cs2.paradoxwikis.com/Policies ）
4. **产业链就近配对**：公司的资源订购会按"运输距离 × 重量"扣利润，因此**把加工厂放在原料产地附近**能实质提高利润与税收。（来源：https://www.paradoxinteractive.com/games/cities-skylines-ii/features/economy-production ）
5. **用 Surplus/Deficit 面板定产**：经济面板生产页显示每种资源的盈余/赤字；不需要的资源不要过度生产（超产会出口并承担越来越高的运输成本）。（同上）

---

## 7. 路网规划的机制依据速查

| 建议 | 机制依据 | 来源 |
|---|---|---|
| 高速不贴住宅、不做临路分区 | 高速禁止临路分区；大型道路降地价 + 高噪音 | https://cs2.paradoxwikis.com/Roads |
| 住宅区用 40 km/h 以下小道路 | 小道路噪音系数 1×（砂石路/步行街为 2×） | 同上 |
| 主干道 ≥3 车道才设信号灯 | 只有 3 车道及以上能设信号灯 | 同上 |
| 路口优先用环岛替代小路口 | 环岛工具造价低（₡200 起）；但官宣"抢行"缺陷 | 同上 |
| 单向路只用于支路 | 服务车辆不能逆行，会绕远甚至导致商铺停业 | 同上 |
| 城外必须做绕城通道 | 城际过境交通会改走更短路径且**不贡献经济** | https://cs2.paradoxwikis.com/Traffic |
| 公交站点与车站是地价工具 | 1.1.0f1 起公交站点/车站影响地价 | https://cs2.paradoxwikis.com/Patch_1.1.X |
| 大站要配停车场 | 停车可用性以"类似公交选项"的方式进入寻路决策 | https://cs2.paradoxwikis.com/Roads |
| 别把服务设施堆成一个巨无霸 | 服务车按"当前+未来位置"综合调度 | https://cs2.paradoxwikis.com/Traffic |
