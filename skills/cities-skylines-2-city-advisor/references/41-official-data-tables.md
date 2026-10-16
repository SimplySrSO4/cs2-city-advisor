# 41 · 官方 Wiki 数值表汇总（第四轮：系统性榨取）

> 检索执行日期：**2026-10-13**（第四轮，全部为实际联网抓取）；基准版本 **1.6.2f1**。
> **方法**：全部用官方 Wiki 的**原生 wikitext** `https://cs2.paradoxwikis.com/index.php?title=<Page>&action=raw`（必要时 `&section=N`）。
> 该接口跳过 MediaWiki 导航框架，正文完整返回（超过约 100 KB 时仍会截断，需按 `section` 切片）。
>
> **可信度分级**（每条都标注）：
> - **O1 = 官方一手**（Paradox 官方 Wiki 的**自动生成数值表**，`{{SVersion|1.6|table}}` —— 由 `PyHelpersForPDXWikis` 从游戏数据自动导出）
> - **O2 = 官方一手（散文正文）**（同 Wiki 的机制描述段落，版本标注多为 `{{Version|1.0}}` → **描述可信，数值可能滞后**）
> - **O3 = 官方一手（原始 prefab 字段转储）**（`Service_building_data_test` 页，字段名是真游戏字段名，但**数值与 O1 冲突** → 见 **C28**）
> - **C = 社区/第三方**（本文件不收，除交叉验证注明）
>
> ⚠️ **与 `40-number-tables.md` 的关系**：`40` §3 已有**服务建筑的 range / capacity / magnitude** 主表（第三轮成果）。
> **本文件不重复** 那三列，只补 **本轮新抓到的列**（噪声 / 耗电 / 耗水 / 垃圾 / 岗位 / 学历 / 班次 / 完整造价维护）与其他页面的数值表。
> 两文件冲突时**以本文件（第四轮实测）为准**，并已在 `48` 登记。

---

## 0. 本轮抓取清单

### 0.1 成功抓取（完整正文 / 完整数值表）

| # | 页面 | URL（`?action=raw`） | 版本标注 | 可信度 | 拿到什么 |
|---|---|---|---|---|---|
| **S90** | `Service_buildings`（**全部段落，逐节切片**） | https://cs2.paradoxwikis.com/index.php?title=Service_buildings&action=raw | 页头 1.5；**全部数值表 `{{SVersion\|1.6\|table}}`** | **O1** | 通信/教育/科研/电力/消防/灾害/垃圾/医疗/殡葬/公园/地标/警务/行政/道路/交通（道路·火车·地铁·水运）**全部建筑的 12 列数值表**：Service range / capacity / magnitude / **Noise pollution / Air·Ground pollution / Electricity consumption / Water consumption / Garbage accumulation / Workplaces / Max. needed education / Evening shifts / Night shifts** |
| **S91** | `Services` | https://cs2.paradoxwikis.com/index.php?title=Services&action=raw | `{{Version\|1.0}}` | **O2** | 预算 50–150% ↔ 25–125% 效率；**电/水费率的逐 1% 弹性（本轮最有价值的新数值）**；通信语义（capacity=能服务多少人，range=服务多远）；垃圾与建筑等级/学历的关系；Welfare Office 的**幸福度 < 一半**触发；进口服务**没有被动覆盖**；监狱是生产设施 |
| **S92** | `Economy` | https://cs2.paradoxwikis.com/index.php?title=Economy&action=raw | `{{Version\|1.0}}` | **O2** | 税率区间 −10%~30%、解锁里程碑；**服务费默认值完整表**；**服务贸易价目表**；**贷款 = 月付借出额的 2.3–20%**、上限 ₡100,000–₡26,100,000、City Hall −1% / Central Bank −2%；公司效率因子表（含 `City Production Specialization` 默认上限 **115% @ 10 kt**）；完整产业链输入输出表 |
| **S93** | `Progression` | https://cs2.paradoxwikis.com/index.php?title=Progression&action=raw | `{{Version\|1.1.5f1}}` | **O2** | **20 个里程碑完整表**（奖金 / 发展点 / 扩张许可 / 贷款上限 / 解锁分区·政策·服务·功能）+ **1.1.5f1 前后奖金对照表**（M1 ₡600,000 → ₡25,000）+ 地图格与**购地成本公式**；`Milestones` 页是重定向 |
| **S94** | `Roads` | https://cs2.paradoxwikis.com/index.php?title=Roads&action=raw | 正文 1.0；**道路表 `{{SVersion\|1.6\|table}}`** | **O1（表）/ O2（正文）** | **全道路类型表**（限速+主题差异 / 车道 / XP / 平地·高架·隧道三套造价与维护 / **噪音·空气污染系数**）；**所有非高速道路 40 MW 输电线**；XP 计量口径 **112 m / 14 格**；环岛 4 档造价；**停车场表（Comfort / garageMarkerCapacity / 默认 `Parking Fee: 10.0`）**；`Road Maintenance Depot` 数值；道路附属物清单；**Pedestrian Street 允许"服务与送货车辆"通行** |
| **S95** | `Policies` | https://cs2.paradoxwikis.com/index.php?title=Policies&action=raw | `{{Version\|1.0}}` | **O2** | 城市/区域/建筑三级政策全表 + **所需里程碑**；**`Energy Consumption Awareness` = 用电 −5%**（本轮唯一的政策数值）；`Roadside Parking Fee` ₡1–50（区域·M5）；`Parking Fee` ₡1–50（建筑）；`Heavy Traffic Ban`（M6）原文 |
| **S96** | `Citizens` | https://cs2.paradoxwikis.com/index.php?title=Citizens&action=raw | 正文 1.0 + **1.3.3f1 工资** | **O2** | 五档工资 / `Residential Minimum Earnings` ₡1400 / `Commuter Wage Multiplier` 1.1 / 家庭津贴 ₡400 / 养老金 ₡1200 / 失业救济 ₡800×≤10 天；**幸福度 10 因子表（无权重）**；四段年龄与各自寻路偏好；**学历越高 → 用水用电与垃圾越少** |
| **S97** | `Zoning` | https://cs2.paradoxwikis.com/index.php?title=Zoning&action=raw | `{{Version\|1.0}}` | **O2** | 各分区的**地块尺寸范围 + 解锁里程碑**（含主题/无主题两张表）；专业化工业表（里程碑/所需资源/**三类污染等级**）；**建筑等级 1–5 的逐项效果**（住宅水电子 3/5 级增加户数；商业/工业/办公单位产出耗水耗电下降、垃圾与污染减少） |
| **S98** | `Service_building_data_test` | https://cs2.paradoxwikis.com/index.php?title=Service_building_data_test&action=raw | **无版本标注**（静态转储） | **O3** | **原始 prefab 字段名**：`Service_coverage_range` / `Service_coverage_capacity` / `Service_coverage_magnitude` / **`Circular`** / `Telecom_need` / `Workplace_complexity` / `maintenanceDuration` —— **确认这三个值确实是独立存档字段**；但**数值与 O1 表不一致** → **C28** |
| **S99** | `Special:AllPages`（页面总表） | https://cs2.paradoxwikis.com/index.php?title=Special:AllPages&action=raw | — | **O1** | 全部页面名清单（用于挑"可能有数值表的页面"）；`Building level` / `Efficiency` / `Speed limits` / `Parking` / `Supply Chains` / `Milestone(s)` / `Subway Station Measurements` 等页存在 |
| **S99b** | `Commonly units in the game` | https://cs2.paradoxwikis.com/index.php?title=Commonly_units_in_the_game&action=raw | — | **O1** | ⚠️ **内容极少**：只记录了 `Time :uint`（1 分钟 ≈ `182.0444…`、90 分钟 = `16384`）。**没有长度/服务半径单位说明** → 单位结论仍依赖 **C20 的三条证据** |

### 0.2 尝试但**失败**的页面（如实记录，供下轮避坑）

| 页面 / URL | 结果 | 说明 |
|---|---|---|
| `https://cs2.paradoxwikis.com/index.php?title=Budget&action=raw` | **HTTP 404** | **该页不存在**。预算相关内容全在 `Services#Budget`、`Economy` 与 `Progression`（"Service Budgets" 是里程碑 1 的功能解锁项）。**不要再找这个页面** |
| `https://cs2.paradoxwikis.com/index.php?title=Taxes&action=raw` | **HTTP 404** | 第二轮已确认，本轮复核仍 404 |
| `https://cs2.paradoxwikis.com/index.php?title=Happiness&action=raw` | 重定向到 `Citizens#Happiness` | 第二轮已确认；**幸福度因子的正式出处是 `Citizens` 页** |
| `https://cs2.paradoxwikis.com/index.php?title=Milestones&action=raw` | 重定向到 `Progression#Milestones` | 用 `Progression` 即可 |
| `Service_buildings` **单次全文抓取** | HTTP 200 但**正文在约 100 KB 处截断**（截断点落在 Parks 段中间） | **必须用 `&section=N` 逐节抓**；节号按标题顺序计（本页：0 页首 / 1 Service buildings / 2 Communications / 3 Post / 4 Telecom / 5 Education & Research / 6 Education / 7 Research / 8 Electricity / 9 Fire & Rescue / 10 Fire / 11 Disaster Control / 12 Garbage Management / 13 Healthcare & Deathcare / 14 Healthcare / 15 Deathcare / 16 Parks & Recreation / 17 Park maintenance / 18 Parks and tourist attractions / 19 Landmarks / 20 Police & Administration / 21 Police / 22 Administration / 23 Roads / 24 Transportation …）。⚠️ **同名标题会导致节号错位**（`section=20` 与 `21` 都返回了 Police），**以返回内容为准**，不要盲信节号 |
| `https://www.paradoxinteractive.com/games/cities-skylines-ii/features/city-services` | **HTTP 404** | 猜的 URL，不存在。官方 Feature Highlight 的可用编号只有 #3 #4 #9（见 `00-sources.md` S22–S24） |
| `https://ngabbs.com/read.php?tid=38512883` | **HTTP 403**「访客不能直接访问」 | NGA 需登录 → **不可达，不要再试** |
| `https://www.yystv.cn/n/1012334`（游研社「测试游戏里税收对城市GDP增长和财政收支的影响」） | HTTP 200 但**正文为空**（只剩导航与页脚） | 标题命中但正文抓不到 → **未采信任何内容**。**该站对本抓取器不可达** |
| `https://youtubetranslate.net/fi/watch?v=vIPUNQz0MCU`（"I Tried Running a 0% Tax City… and It Actually Worked"） | HTTP 200，**只拿到前 1/3 字幕** | 内容为"0% 税率城市靠卖电盈利"的挑战视频（15 台风机 + 变压器站外送 ≈ **₡72,000/月**；扩到 160 MW 后 ≈ **₡150,000/月**），**不是税率受控实验** → 见 **C29** |

---

## 1. 服务建筑：本轮新增的官方数值列（`Service_buildings`，表标注 **1.6**，O1）

> **列义**（官方表头逐字）：`Noise pollution` / `Air pollution` / `Ground pollution` / `Electricity consumption` / `Water consumption` / `Garbage accumulation` / `Workplaces` / `Max. needed education` / `Evening shifts` / `Night shifts`。
> **`Service range` / `Service capacity` / `Service magnitude` 三列见 `40-number-tables.md` §3**（本表不重复）。
> `—` = 该表该格为空（**官方就是空**，不是我没抓到）。

### 1.1 医疗 / 殡葬 / 消防 / 警务 / 行政（决策最常用）

| 建筑 | 噪声 | 耗电 | 耗水 | 垃圾 | 岗位 | 学历要求 | 夜班 | 造价 | 维护/月 | 出处 |
|---|---|---|---|---|---|---|---|---|---|---|
| Small Medical Clinic | — | 1250 | 500 | 25 | 6 | Well educated | 25%/20% | ₡30.0K | ₡10.0K | S90 1.6 |
| Medical Clinic | — | 2500 | 1000 | 25 | 18 | Well educated | 25%/20% | ₡60.0K | ₡20.0K | S90 1.6 |
| **Hospital** | — | 10000 | 5000 | 60 | **120** | Highly educated | 25%/20% | ₡1.88M | **₡225.0K** | S90 1.6 |
| Disease Control Center | — | 10000 | 5000 | 50 | 100 | Highly educated | 25%/20% | ₡2.0M | ₡175.0K | S90 1.6 |
| Health Research Institute | — | 10000 | 5000 | 200 | 100 | Highly educated | 25%/20% | ₡1.0M | ₡80.0K | S90 1.6 |
| Crematorium | **5000** | 1300 | 500 | 60 | 20 | Educated | 0%/0% | ₡240.0K | ₡22.5K | S90 1.6（含 **Air pollution 2500**） |
| Small Cemetery | — | 500 | 1000 | 60 | 10 | Educated | 0%/0% | ₡42.0K | ₡12.0K | S90 1.6 |
| Cemetery | — | 800 | 2000 | 60 | 18 | Educated | 0%/0% | ₡114.0K | ₡27.5K | S90 1.6 |
| **Fire House** | **5000** | 1000 | 1000 | 65 | 12 | Poorly educated | 25%/12.5% | ₡120.0K | ₡10.0K | S90 1.6 |
| City Fire House | **6000** | 1200 | 1200 | 65 | 10 | Poorly educated | 25%/12.5% | ₡125.0K | ₡12.0K | S90 1.6 |
| **Fire Station** | **7500** | 3500 | 5000 | 60 | **120** | Educated | 25%/12.5% | ₡2.15M | **₡117.5K** | S90 1.6 |
| Firefighting Helicopter Depot | **25000** | 16000 | 4000 | 110 | 48 | Poorly educated | 25%/12.5% | ₡1.22M | ₡72.5K | S90 1.6 |
| Firewatch Tower | — | 500 | 0 | 0 | — | — | — | ₡46.0K | ₡12.5K | S90 1.6 |
| Small Police Station | 4000 | 1700 | 800 | 45 | 8 | Poorly educated | 30%/30% | ₡100.0K | ₡15.0K | S90 1.6 |
| Police Station | 5000 | 2000 | 1000 | 45 | 18 | Poorly educated | 30%/30% | ₡160.0K | ₡19.0K | S90 1.6 |
| City Police Station | 6000 | 3000 | 1500 | 45 | 20 | Poorly educated | 30%/30% | ₡220.0K | ₡25.0K | S90 1.6 |
| **Police Headquarters** | **20000** | 3500 | 2500 | 40 | **120** | Well educated | 30%/30% | ₡2.1M | **₡155.0K** | S90 1.6 |
| **Prison** | **40000** | 3500 | 5000 | 25 | 80 | Well educated | 30%/30% | ₡650.0K | ₡100.0K | S90 1.6 |
| Central Intelligence Bureau | — | 16000 | 1000 | 100 | **200** | Highly educated | 25%/12.5% | ₡3.2M | ₡160.0K | S90 1.6 |
| Welfare Office | **10000** | 1500 | 1000 | 140 | 50 | Educated | 12.5%/6.25% | ₡110.0K | ₡22.5K | S90 1.6 |
| City Hall | — | 3500 | 1000 | 160 | 50 | Well educated | 25%/10% | ₡1.6M | ₡80.0K | S90 1.6 |
| Central Bank | — | 10000 | 1000 | 240 | 80 | Well educated | 25%/12.5% | ₡2.4M | ₡120.0K | S90 1.6 |
| Small Emergency Shelter | — | 500 | 50 | 10 | — | — | — | ₡35.0K | ₡7.5K | S90 1.6 |
| Large Emergency Shelter | — | 15000 | 5000 | 10 | 28 | Educated | — | ₡315.0K | ₡30.0K | S90 1.6 |
| Early Disaster Warning System | — | 15000 | 7500 | 158 | 40 | Highly educated | — | ₡2.4M | ₡120.0K | S90 1.6 |

> **用途**：`Noise pollution` 列让"哪些服务设施本身就是噪音源"第一次变成**可计算**的（消防直升机库 25000 / 监狱 40000 是该表最高量级）；`Workplaces` + `Max. needed education` 让"建这个设施能吸收多少高学历劳动力"可算；**Hospital / Fire Station / Police HQ 各 120 个岗位且要求 Educated 以上** → 大医疗/大消防/大警务同时是**高学历岗位来源**。

### 1.2 教育 / 邮政 / 通信（新增列）

| 建筑 | 噪声 | 耗电 | 耗水 | 垃圾 | 岗位 | 学历要求 | 出处 |
|---|---|---|---|---|---|---|---|
| Small Elementary School | 3500 | 400 | 600 | 5 | 20 | Educated | S90 1.6 |
| Elementary School / City Elementary School | 7500 | 1000 | 1500 | 5 / 3 | 50 | Educated | S90 1.6 |
| Small High School | 3750 | 750 | 750 | 5 | 20 | Educated | S90 1.6 |
| High School / City High School | 7500 | 1500 | 1500 | 5 | 80 / 40 | Educated | S90 1.6 |
| College | 2000 | 1500 | 1500 | 6 | 100 | Well educated | S90 1.6 |
| University | 3000 | 3000 | 3000 | 7 | 170 | Highly educated | S90 1.6 |
| Technical University | 10000 | 2500 | — | 7 | 150 | Highly educated | S90 1.6 |
| Medical University | 8000 | 2500 | — | 7 | 150 | Highly educated | S90 1.6 |
| Large Hadron Collider | 100000 | 250000 | — | 280 | 100 | Highly educated | S90 1.6 |
| Geological Research Center | 15000 | 3500 | 10000 | 120 | 64 | Highly educated | S90 1.6 |
| Radio Telescope | 15000 | 10000 | — | 200 | 30 | Highly educated | S90 1.6 |
| Small Post Office | 2000 | 300 | 100 | 100 | 6 | Educated | S90 1.6 |
| Post Office | 5000 | 500 | 1000 | 100 | 40 | Educated | S90 1.6 |
| **Post Sorting Facility** | **20000** | **8000** | 2500 | 100 | 80 | Educated | S90 1.6 |
| Radio Mast | 2500 | 2500 | 100 | 0 | 10 | Well educated | S90 1.6 |
| **Server Farm** | **20000** | **20000** | **10000** | 300 | 40 | Highly educated | S90 1.6 |
| Telecom Tower | 10000 | 12500 | 1000 | 0 | 30 | Highly educated | S90 1.6 |
| Satellite Uplink | 5000 | 5000 | 500 | 500 | 30 | Highly educated | S90 1.6 |

### 1.3 垃圾 / 电力 / 公园 / 地标（新增列摘录）

| 建筑 | 地面污染 | 空气污染 | 噪声 | 耗水 | 岗位 | 出处 |
|---|---|---|---|---|---|---|
| **Landfill** | — | **20000** | **40000** | 2500 | 30 | S90 1.6 |
| **Incineration Plant** | — | **40000** | **40000** | **25000** | 60 | S90 1.6 |
| Recycling Center | 5000 | 15000 | 2500 | 10000 → 见注 | 60 | S90 1.6 |
| **Industrial Waste Processing Site** | **50000** | **50000** | 15000 | 25000 | **250** | S90 1.6 |
| Small Coal Power Plant | 30000 | 30000 | — | 15000 | 37 | S90 1.6（T10 表头为 `Ground/Air/Noise/Water`） |
| **Coal Power Plant** | 100000 | 100000 | — | **60000** | 140 | S90 1.6 |
| Gas Power Plant | 10000 | 10000 | — | **48000** | 100 | S90 1.6 |
| **Nuclear Power Plant** | **150000** | — | — | **400000** | 300 | S90 1.6 |
| Solar Power Plant | — | — | — | 36000 | 32 | S90 1.6 |
| Hydroelectric Power Plant | 50000 | — | — | 0 | 18 | S90 1.6 |
| Wind Turbine | 20000 | — | — | 0 | 0 | S90 1.6 |
| Windmill | 8000 | — | — | 0 | 0 | S90 1.6 |
| Small Wind Turbine | 14000 | — | — | 0 | 0 | S90 1.6 |
| Wind Turbine **Solar Assisted**（升级） | 0 | — | — | 0 | 0 | S90 1.6 |
| **Cargo Harbor** | — | — | **100000** | 1000 | 75 | S90（水运 extra 表） |
| Harbor | — | — | 25000 | 1000 | 50 | S90 |
| **Shipyard 类：Small Port / Medium Port / Large Port** | — | — | 5000 / 7500 / 7500 | 500 | 15 / 35 / 75 | S90 |
| Railway Depot | — | — | 24000 | 800 | 24 | S90 |
| **Rail Yard** | — | — | **30000** | — | — | S90 |
| **Subway Yard** | — | — | **25000** | 1000 | 30 | S90 |
| Terminal Subway Yard | — | — | 10000 | 500 | 15 | S90 |
| Overground Subway Station | — | — | 10000 | 1000 | 0 | S90 |
| Underground Subway Station | — | — | 5000 | 1000 | 0 | S90 |
| Small Elevated Subway Station | — | — | 10000 | 0 | 0 | S90 |
| Bus Depot | 2500（空气） | — | 10000 | 1000 | 40 | S90 |
| Bus Station | — | — | 10000 | 1000 | 28 | S90 |
| City Bus Station | — | — | 7500 | 750 | 12 | S90 |
| Small Bus Station | — | — | 5000 | 500 | 0 | S90 |
| Taxi Depot | — | — | 5000 | 500 | 25 | S90 |
| Small Taxi Depot | — | — | 2000 | 200 | 8 | S90 |
| **Small / Medium / Large Storage Yard** | — | — | 25000 | 50 | 6 / 12 / 24 | S90（**储位 3.0M / 7.5M / 15.0M**） |
| Park Maintenance Depot | — | — | 5000 | 2000 | 30 | S90 |
| Road Maintenance Depot | — | — | 5000 | 1000 | 30 | S94（道路服务表） |

> ⚠️ **电力类建筑的表头是 `Ground pollution / Air pollution / Noise pollution / Water consumption / …`**（不是 `Noise + Electricity`），
> 因此本小节的电力行**第三列是"位置顺序"而非同一物理量**，请按表头逐列读；**不要横向直接比大小**（详见 §10 读表纪律）。

### 1.4 服务建筑通用：班次与学历（机制性）

- 所有服务建筑都有 **`Evening shifts` / `Night shifts` 百分比**列（多数主建筑 **25% / 12.5%–25%**，纯白天设施为 **0% / 0%**）。
- `Max. needed education` 是**该建筑岗位所需的最高学历**（Poorly educated → Highly educated 五档）。
- **医疗主建筑要求 Well/Highly educated（岗位多、学历高）**，而**消防/警务主建筑只要求 Poorly educated** → **"用服务建筑吸收高学历劳动力"应按医疗/教育/行政/通信来规划，消防警务不行**。

---

## 2. 服务机制数值（`Services` 页 `?action=raw`，**S91**，正文标 1.0 → O2）

| 项目 | 数值 | 出处 | 版本 | 可信度 | 用途 |
|---|---|---|---|---|---|
| 预算区间 → 效率 | **50% 预算 = 25% 效率；150% = 125% 效率** | S91 `#Budget` | 1.0 | O2 | 预算滑块是"效率 × 容量 × **覆盖半径**"三合一的杠杆 |
| 预算对覆盖的影响 | 官方原文："Services will increase their **service capacity** (trash trucks, police cars, student capacity, etc.) if the budget is increased… **Other effects may be less obvious, such as the range of the service coverage**" | S91 | 1.0 | O2 | **覆盖不足的第一手段是拉预算，不是盖楼** |
| **电/水费率弹性（偏离 100% 每 1%）** | **低于 100%**：用电 **+0.2%**、公司效率 **+0.2%**、市民幸福度 **+0.05**<br>**高于 100%**：用电 **−0.4%**、公司效率 **−0.4%**、市民幸福度 **−0.1** | S91 `#Service fees` | 1.0 | **O2（本轮最有价值的新数值）** | ⚠️ **弹性不对称：涨费率的惩罚是降价收益的 2 倍**（−0.4% vs +0.2%；幸福 −0.1 vs +0.05）。→ **"涨水电费换钱"是负和操作**，除非目的是**压用电量**（涨费率省电效率是降价促耗的 2 倍） |
| **服务容量 vs 覆盖范围的官方语义** | 官方原文（通信段）："each telecom building has a **bandwidth capacity** and **range** describing **how many citizens it can service** and **how far its service reaches**" | S91 `#Telecommunications` | 1.0 | O2 | **`Service capacity` = 能服务多少市民；`Service range` = 服务能到多远** → 这是理解 **C23（半径被密度压缩）** 的官方语义锚点 |
| 通信带宽需求 | **每位市民/员工/学生 1 Gbit/s**；信号强度**离源越远越弱**，幸福度增益随之下降 | S91 | 1.0 | O2 | 通信是唯一官方明说"强度随距离衰减"的服务 |
| 垃圾产生量 | "Various factors can contribute to garbage being accumulated such as: **building and zone type, building level and size** as well as **citizen education level**. **Higher-level buildings generate less garbage as do citizens with a higher education level.**" | S91 `#Garbage management` | 1.0 | O2 | **升级建筑与提升学历 = 直接减少垃圾产生量**（垃圾服务的需求侧可以靠"升级/教育"而非"多建填埋场"解决） |
| **Welfare Office 触发条件** | "boosts their Well-being **if their Happiness is below half**" | S91 `#Administration` | 1.0 | **O2（官方唯一的幸福度阈值数字）** | ⚠️ 这不是"低幸福度报警阈值"，而是**该建筑生效的条件**。但它是官方表里唯一出现的幸福度分界（**50%**） |
| 进口服务没有被动覆盖 | "the imported services **lack the passive service coverage effects** from their respective service buildings, which can otherwise decrease crime and fire hazards respectively" | S91 `#Service trade` | 1.0 | O2 | **`Import City Services` 只能补"事件响应"，补不了"被动覆盖"** → 用进口服务去补覆盖空洞是无效的 |
| 警务巡逻范围 | "**Unless limited by selected districts**, police cars can patrol the entire city." | S91 `#Police` | 1.0 | O2 | 警车**是全城巡逻**的（除非用区域限制）→ "警力覆盖不足"应先看车数与区域设置，不是看半径 |
| 监狱的双重身份 | "Prisons function also as **production facilities**, producing resources used by manufacturing companies in the city." | S91 `#Police` | 1.0 | O2 | 监狱是**生产设施**（除关人外还产出资源） |
| 路网输电容量 | **所有非高速道路 = 40 MW（Low Voltage）输电线；非桥梁道路还自带水管与污水管** | S94（Roads 正文 + 表） | 1.0 / 1.6 表 | O1+O2 | 道路本身就是电网与管网 → "拉一条路"同时解决电水接入 |
| 建筑等级对水电垃圾的作用 | 住宅：**随等级上升，每户耗电耗水下降**；**3 级与 5 级时中/高密度住宅可用公寓数增加**。商业：**单位商品耗电耗水下降、生产更快 → 售价更低**。工业与办公：**单位产出耗电耗水下降、垃圾与污染更少** | S97 `#Building level` | 1.0 | O2 | **"升级建筑"同时是省电/省水/减垃圾/减污染的手段**（不只是涨税基） |
| 学历的间接效果 | "Education … also increase their wages and efficiency and **decreases their water and electricity consumption and garbage production**" | S96 | 1.0 | O2 | 教育 = 同时涨税基 + 降公共事业负荷 |

---

## 3. 经济与预算（`Economy` 页 `?action=raw`，**S92**，正文标 1.0 → O2）

### 3.1 税率与解锁

| 项目 | 数值 | 出处 | 版本 | 可信度 |
|---|---|---|---|---|
| 税率可调区间 | **−10% ~ +30%**（每一类分区一个总滑块，可再按学历/产品细分） | S92 `#Taxation` | 1.0 | O2 |
| 税收解锁 | **里程碑 2（Small Village）** 解锁 Taxation（`Progression` 页写"Tiny Village"解锁 Taxation → **两页不一致，见 C30**） | S92 / S93 | 1.0 / 1.1.5f1 | O2 |
| 官方权衡原话 | "**Lower taxes help buildings level up faster while higher taxes bring more money.**" | S92 | 1.0 | O2 |
| 住宅税基 | 市民**月薪**；可按**学历**分档 | S92 | 1.0 | O2 |
| 商/工/办税基 | 公司**月利润**；可按**产品类型**分档 | S92 | 1.0 | O2 |

### 3.2 服务费默认值（**官方明文，本轮新增**）

| 服务 | 默认费率 | 出处 |
|---|---|---|
| 道路（停车费） | 可调 **₡0 – ₡50** | S92 |
| 电力 | **0.2** | S92 |
| 水 | **0.3** | S92 |
| 医疗 | **₡100 / 月 / 住院市民** | S92 |
| 垃圾 | **1.0** | S92 |
| 教育 | 小学 **₡50** / 月 / 市民；高中 **₡100**；学院与大学 **₡200** | S92（与 S96 一致） |
| 交通 | 由票价决定（每条线路单独可调） | S92 / S91 |

### 3.3 服务贸易价目（**官方明文，本轮新增**）

| 服务 | 进口 | 出口 |
|---|---|---|
| 电力 | **₡5000 / MW** | **₡2500 / MW** |
| 水 | ≈ **₡0.1 / m³** | ≈ **₡0.05 / m³** |
| 污水 | **不可进口** | ≈ **₡0.1 / m³** |
| 警务 | **₡50 / 市民** | — |
| 医疗 | **₡25 / 市民** | — |
| 殡葬 | **₡25 / 市民** | — |
| 消防 | **₡50 / 市民** | — |
| 垃圾 | **₡5 / 市民** | — |

> **用途**：进口价是"按人口计价"的**固定月费** → 可以算"建一座医院 vs 进口医疗"的盈亏平衡点（但要记得**进口没有被动覆盖**，见 §2）。

### 3.4 贷款（**官方明文，本轮新增**）

| 项目 | 数值 | 出处 |
|---|---|---|
| 月还款占借款额 | **2.3% – 20%**（随借款规模递增） | S92 |
| 借款上限 | **₡100,000 → ₡26,100,000**（随里程碑上升；`Progression` 逐级给的是**每级 +₡100,000 → +₡4,000,000 的"当前上限"**） | S92 / S93 |
| 利率减免 | **City Hall −1%**、**Central Bank −2%** | S92 |
| ⚠️ 冲突 | `Service_buildings` 表写 **Central Bank = −50% Loan Interest（全城）**；`Services` 页又写 Central Bank 是"降进口成本、升出口利润" → **三处口径不同，见 C28** | S92 / S90 / S91 |

### 3.5 公司效率因子（`Economy#Efficiency`，官方表）

| 因子 | 正/负向 |
|---|---|
| 员工幸福度 | 平均员工幸福度↑ → 效率↑ |
| 员工数量 | 人手不足 → 效率↓ |
| **City Production Specialization** | 对产量大的相关行业给效率加成，**默认上限 115% @ 10 kt 产量** |
| 城市级加成（签名建筑等，游戏内称 "Commercial/Industrial Efficiency"） | ↑ |
| **电费** | 降电费 → 效率↑ |
| **水费** | 降水费 → 效率↑ |
| 邮件处理 | 邮件效率↑ → 效率↑ |

---

## 4. 里程碑（`Progression` 页 `?action=raw`，**S93**，标 **1.1.5f1** → O2）

### 4.1 完整里程碑表（20 级）

| # | 里程碑 | 奖金 | 发展点（累计） | 扩张许可（累计） | 贷款上限 | 关键解锁 |
|---|---|---|---|---|---|---|
| 1 | Tiny Village | **₡25,000** | +1 (1) | +3 (3) | ₡100,000 | 中密度联排住宅、蔬菜/煤矿、**医疗与殡葬**、**垃圾管理**、地图格、**税收**、城市预算、服务预算、**四车道道路** |
| 2 | Small Village | ₡50,000 | +2 (3) | +4 (7) | ₡150,000 | 中密度住宅、纺织农业、**教育**、生产面板 |
| 3 | Large Village | ₡75,000 | +3 (6) | +5 (12) | ₡200,000 | 采矿、**消防**、**警务与行政** |
| 4 | Grand Village | ₡100,000 | +4 (10) | +6 (18) | ₡250,000 | 低租金住宅、低密度办公、石油、**Import City Services**、Taxi Minimum Fare、**交通**、**公园与休闲**、区域工具、政策、交通总览、自然灾害 |
| 5 | Tiny Town | ₡125,000 | +5 (15) | +7 (25) | ₡400,000 | 混合住宅、Pre-Release Programs、**Roadside Parking Fee**、Recycling、Speed Bumps、Energy Consumption Awareness、**通信** |
| 6 | Boom Town | ₡150,000 | +6 (21) | +8 (33) | ₡500,000 | **Heavy Traffic Ban**、Advanced Pollution Management |
| 7 | Busy Town | ₡175,000 | +7 (28) | +9 (42) | ₡600,000 | Gated Community |
| 8 | Big Town | ₡200,000 | +8 (36) | +10 (52) | ₡700,000 | **高密度住宅** |
| 9 | Great Town | ₡225,000 | +9 (45) | +12 (64) | ₡800,000 | **高密度商业** |
| 10 | Small City | ₡250,000 | +10 (55) | +15 (79) | ₡900,000 | **高密度办公**、High-Speed Highways、Combustion Engine Ban、City Promotion |
| 11–20 | Big City → Megalopolis | 每级 **+₡25,000**（₡275,000 → **₡500,000**） | 逐级 **+11/+12/+13/+14/+15/+17/+19/+21/+25/+30**（累计 232） | 逐级 +18/+21/+24/+28/+32/+36/+41/+46/+51/+56（累计 432） | ₡1.1M → **₡4,000,000** | 无新解锁项（纯规模） |

> **官方在页内给了 1.1.5f1 的对照表**：里程碑奖金被**大幅下调**（M1 **₡600,000 → ₡25,000**；M20 ₡7,000,000 → ₡500,000）。
> ⚠️ **任何 1.1.5f1 之前的"靠里程碑奖金周转"建议全部失效。**

### 4.2 发展树与地图格

| 项目 | 数值 | 出处 |
|---|---|---|
| 发展点费用 | Tier 1 = **1 点**、Tier 2 = **2 点**、Tier 3 = **4 点**、Tier 4 = **8 点**；Tier 1 在解锁该服务时**自动获得** | S93 |
| 地图 | **441 格 × 0.4 km² ≈ 176.4 km²**；开局 **9 格**已购；买格需要 **1 张扩张许可 + 金钱** | S93 |
| 购地成本公式（Wiki 标注 `Verification needed`，来源为 1.0.12f1 源码考证） | 每多 1 格 ≈ **+₡125**（待验证）；建筑面积 ≈ **₡1,184 / 10,000 m²（0.1184 ₡/m²）**；资源：Wood/Ore **₡18.6/吨**、Oil **₡55.6/kg**、Groundwater **₡53.9/m³**、Fertile Land **₡16.9/m²** | S93 |
| 里程碑解锁的专业化工业（1.1.5f1 起） | **Livestock / Stone = 开局解锁**；Grain / Forestry 开局解锁（原文并列在开局项）；Vegetable / Coal = Tiny Village(1)；Textile = Small Village(2)；Ore = Large Village(3)；Oil = Grand Village(4) | S93（与 `Zoning` 表的 M3/M4/M5/M6/M7/M8 表述**不完全一致 → 见 C31**） |

---

## 5. 道路（`Roads` 页 `?action=raw`，**S94**；道路表 `{{SVersion|1.6|table}}` → O1）

### 5.1 全道路表关键列（摘录：小道路 / 中大道路 / 高速）

| 道路 | 车道 | 限速（欧洲主题显示 / **内部值**；北美主题显示） | 平地造价/km | 平地维护/km | 高架造价/km | **隧道造价/km** | 隧道维护/km | 噪音系数 | 空气系数 |
|---|---|---|---|---|---|---|---|---|---|
| **Two-Lane Road** | 2 | 40 km/h / **80.0** / 30 km/h | **₡4.0K** | **₡487** | ₡14.0K + ₡4.5K/层 | **₡33.5K** | ₡2.96K | 1× | 1× |
| Three-Lane Asymmetric / Three-Lane One-Way | 3 | 40 / 80.0 / 30 | ₡4.75K | ₡600 | ₡15.25K + ₡5.25K | ₡39.25K | ₡3.37K | 1× | 1× |
| One-Lane One-Way | 1 | 40 / 80.0 / 30 | ₡3.25K | ₡375 | ₡12.25K + ₡4.0K | ₡28.75K | ₡2.35K | 1× | 1× |
| **Gravel Road** | 2 | 30 / **60.0** / 25 | ₡2.5K | ₡412 | 与平地同价（**+₡0/层**） | 与平地同价 | ₡412 | **2×** | 1× |
| Gravel One-Way | 1 | 30 / 60.0 / 25 | ₡2.0K | ₡262 | 同平地 | 同平地 | ₡262 | **2×** | 1× |
| Alley | 2 | 30 / 60.0 / 25 | ₡3.0K | ₡337 | ₡9.5K + ₡3.25K | ₡21.5K | ₡1.91K | 1× | 1× |
| One-Way Alley | 1 | 30 / 60.0 / 25 | ₡2.25K | ₡225 | ₡8.25K + ₡3.0K | ₡18.75K | ₡1.65K | 1× | 1× |
| **Pedestrian Street** | 2 | 20 / **40.0** / 12 | **₡6.5K** | ₡262 | ₡17.0K + ₡5.25K | ₡41.0K | ₡3.03K | **2×** | 1× |
| Small Pedestrian Street | 1 | 20 / 40.0 / 12 | ₡4.0K | ₡188 | ₡10.5K + ₡3.25K | ₡22.5K | ₡1.76K | **2×** | 1× |
| 停车场道路（Perpendicular/Angled Parking Road 等） | 2 或 1 | 40 / 80.0 / 30（Alley 型 30 / 60.0 / 25） | ₡4.0K（1 车道 ₡3.25K） | ₡487（₡375） | ₡13.0K–₡16.5K | ₡27.25K–₡44.5K | ₡1.65K–₡3.31K | 1× | 1× |
| **高速（Highways）** | 3–4 | **100 km/h / 200.0 / 65**（部分 80 / **160.0** / 55） | — | — | ₡13.5K–₡14.0K + ₡5.0K–₡5.25K | — | ₡2.02K–₡2.1K | 1× | 1× |

**表内其它官方字段**：
- `XP` = **每 112 m / 14 格** 给的经验值（小道路 1–2、高速 3–4）。
- `Traffic lights`：只有 **3 车道路段**标注了"可以有信号灯"。
- `Highway rules`：仅高速。
- `Services` 列：**所有非高速道路 = `Water & Sewage pipes` + `Low voltage power line with 40.0MW`**。
- ⚠️ **表格仍然没有任何"通行能力 / pcu/h / 饱和流率"字段** —— **C8 第 4 次确认**。

**表外正文（O2）**：
- **环岛**：Small **₡200** / Medium **₡500** / Large **₡1,000** / Very Large **₡1,500**（后三档需发展树 `Roundabouts`）；每种中部有三种装饰。
- **标高步进**：1.25 / 2.50 / 5.00 / 10.00 m（3.75 / 7.50 / 15.00 / 30.00 ft）。
- **平行模式**偏移量 **0.25 – 12 格**。
- **吸附**：**每 8 m 吸附一次**（= 1 格；8.7 码）→ **1 格 = 8 m 的原始出处**。
- **单行道代价**：服务车辆不能逆行；商/工业送货不足会 **"stop operating effectively"**。
- **`Pedestrian Street` 原文**："only foot traffic is allowed, **apart from service and delivery vehicles**" → **官方明确把"服务车"与"送货车辆"列为允许上步行街的例外**（对 C25 的旁证，见 §12）。
- **树木**只能贴在道路上、**隔音墙只能贴在高速上**；宽人行道/草地会**占用路边停车位**。

### 5.2 停车场表（`Roads#Parking spaces`，`{{SVersion|1.6|table}}`，O1）

| 建筑 | 尺寸 | 造价 | 维护/月 | Comfort | **garageMarkerCapacity** | **默认政策** | `defaultProbability` |
|---|---|---|---|---|---|---|---|
| Motorcycle Parking Lot | 2×2 | ₡3.7K | ₡740 | 60.0 | 0 | **Parking Fee: 10.0** | — |
| Tiny Parking Lot | 3×2 | ₡3.7K | ₡740 | 50.0 | 0 | Parking Fee: 10.0 | — |
| Small Single-Row Parking Lot | 6×2 | ₡4.0K | ₡800 | 50.0 | 0 | Parking Fee: 10.0 | — |
| Small Parking Lot | 5×5 | ₡11.0K | ₡2.2K | 50.0 | 0 | Parking Fee: 10.0 | — |
| Very Large Parking Lot | 18×10 | ₡80.0K | ₡16.0K | 50.0 | 0 | Parking Fee: 10.0 | — |
| Small Gravel Parking Lot | 6×2 | ₡3.0K | ₡600 | **30.0** | 0 | Parking Fee: 10.0 | — |
| Multi-Level Parking Building | 8×6 | ₡200.0K | ₡40.0K | 60.0 | 0 | Parking Fee: 10.0 | — |
| **Underground Parking Building** | 6×10 | ₡200.0K | ₡40.0K | 65.0 | **100** | Parking Fee: 10.0 | — |
| **Automated Parking Building** | 13×9 | ₡630.0K | ₡65.0K | **75.0** | **416** | Parking Fee: 10.0 | **100** |
| Bicycle Parking Area | 1×1 | ₡900 | ₡180 | 20.0 | 0 | — | — |
| Small Bicycle Storage | 1×1 | ₡1.5K | ₡300 | 40.0 | 16 | — | — |
| Medium Bicycle Storage | 1×2 | ₡2.6K | ₡520 | 40.0 | 10 | — | — |
| Bicycle Parking Hall | 5×2 | ₡7.2K | ₡1.44K | 50.0 | 60 | — | — |
| Large Bicycle Parking Hall | 5×5 | ₡39.0K | ₡7.8K | 50.0 | **270** | — | — |
| **Underground Bicycle Parking Hall** | 2×3 | ₡54.24K | ₡10.8K | 50.0 | **400** | — | — |

> **`garageMarkerCapacity` = 该建筑的停车位（"车库标记"）数量**；`defaultProbability` 只有自动停车楼有值（100）。
> **所有停车设施的默认建筑政策都是 `Parking Fee: 10.0`**（₡10）。
> ⚠️ **"一个停车位能顶多少路边车位/能减少多少拥堵"官方无数据 → 不得承诺量化收益。**

### 5.3 道路服务（`Roads#Road services`，`{{SVersion|1.6|table}}`，O1）

| 建筑 | 尺寸 | 造价 | 维护/月 | 维护类型 | 维护车 | 车效 | 噪声 |
|---|---|---|---|---|---|---|---|
| **Road Maintenance Depot** | 10×12 | **₡75.0K** | **₡15.0K（`Service_buildings` 表同值）** | Road, Snow, Vehicle | **10** | 1.0 | 5000 |
| Road Maintenance Depot Extra Garage | — | ₡4.0K | ₡7.5K | — | **+5** | — | 2500 |

> **道路附属物**（可逐路段增删，无需 Mod）：Traffic lights、Stop signs、**No turn left / No straight ahead / No turn right**、Crosswalks、Wide sidewalks、Grass、Trees（降噪）、Sound barriers（**仅高速**）、Lighting（**仅高速**，加装后获得低压输电能力）。

---

## 6. 政策（`Policies` 页 `?action=raw`，**S95**，标 1.0 → O2）

### 6.1 城市政策

| 政策 | 里程碑 | 数值/效果 |
|---|---|---|
| Taxi Minimum Fare | 4 | 每次出租车行程收最低费，**在按实际距离计算的车费之上另加** |
| Import City Services | 4 | 进口警务/医疗/殡葬/垃圾/消防；**费用按城市人口计价**；⚠️ **没有被动覆盖效果**（S91） |
| Pre-Release Programs | 5 | 囚犯出狱前接受教育，降低再犯 |
| **Advanced Pollution Management** | 6 | 工业过滤器降低工业区**空气与地面污染**，但**产生更多垃圾** |
| City Promotion | 10 | 提升吸引力 → 更多游客；**代价：旅游景点周边犯罪率上升** |
| **High-Speed Highways** | 10 | **移除高速限速** → 车流更快，但**噪声上升、事故略增** |

### 6.2 区域政策（District）

| 政策 | 里程碑 | 数值/效果 |
|---|---|---|
| **Energy Consumption Awareness** | 5 | **用电量 −5%**（本轮唯一的政策数值） |
| Recycling | 5 | 减少资源消耗，但**减少市民闲暇** |
| **Roadside Parking Fee** | 5 | **₡1 – ₡50** 滑块（区域级） |
| **Speed Bumps** | 5 | 区内车辆降速 → **事故率下降 + 噪声"显著下降"** |
| **Heavy Traffic Ban** | 6 | "Trucks and other heavy vehicles are forbidden from entering the district. This reduces noise and air pollution and can help traffic congestion. **Highways remain unaffected.**" |
| Gated Community | 7 | 仅本区居住/工作者可进入；提升居民福祉、降低犯罪；**不影响城市服务** |
| Combustion Engine Ban | 10 | 禁燃油车进入，**但本区居民与企业的车除外**；降低噪声与空气污染 |

### 6.3 建筑政策

| 政策 | 数值 |
|---|---|
| **Parking Fee** | **₡1 – ₡50**（建筑级；停车设施默认 ₡10） |

> ⚠️ **全部政策的数值效果只有 `Energy Consumption Awareness` 一个给了百分比**。除它以外，**任何"某政策能提升 X%"的说法都没有官方依据**。

---

## 7. 市民（`Citizens` 页 `?action=raw`，**S96**，正文 1.0 + **1.3.3f1 工资** → O2）

| 项目 | 数值 | 出处 |
|---|---|---|
| 工资（仅由学历决定） | Highly Educated (Manager) **₡2700/月**；Well Educated (Specialist) **₡2400**；Educated (Senior) **₡2100**；Poorly Educated (Basic) **₡1800**；Uneducated (Simple) **₡1500** | S96（1.3.3f1） |
| 住宅税起征点 | `Residential Minimum Earnings` = **₡1400/月**（只对超出部分征税） | S96 |
| 城际通勤者 | **完全不纳税**；`Commuter Wage Multiplier` = **1.1** | S96 |
| 家庭津贴（有孩子家庭） | **₡400/月**（游戏凭空生成，**不从市政预算扣除**） | S96 |
| 养老金 | **₡1200/月**（同上） | S96 |
| 失业救济 | **₡800/月**，最多 `Unemployment Allowance Max Days` = **10 天**（同上） | S96 |
| 幸福度因子（**10 项，无权重**） | 教育服务（Quality）/ 闲暇（Abundance）/ 娱乐（Abundance）/ **医疗覆盖（Reliability）** / **邮政（Reliability）** / **互联网（Reliability）** / **噪音（Amount）** / 财富（Amount）/ **住房面积（Amount：低密度大房子=正面）** / **税率（Amount：低=正面）** | S96 |
| 四段年龄的寻路偏好 | Children 不能工作、必上小学；**Teens = 最便宜路线**；**Adults = 最快路线**；**Seniors = 最舒适路线** | S96 |
| 学历的附带效果 | 提高工资与效率，并**降低用水、用电与垃圾产生** | S96 |
| 学历对应学校与学费 | 小学 Uneducated→Poorly Educated（₡50/月）；高中 Poorly Educated→Educated（₡100）；学院 Educated→Well Educated（₡200）；大学 Well Educated→Highly Educated（₡200） | S96 |
| 犯罪目标选择 | 按各建筑的 `crime probability` 排序后，**在最高组里随机取一个** | S96 |
| 游客 | 住本地酒店；每天决定去哪；**吸引力决定游客数量**；比较"闲暇收益 vs 离酒店距离" | S96 |
| 宠物 | 纯装饰，**不影响幸福度、资源消耗、垃圾或噪音** | S96 |

---

## 8. 分区（`Zoning` 页 `?action=raw`，**S97**，标 1.0 → O2）

### 8.1 分区地块尺寸与解锁（有主题 · 官方表）

| 分区 | 里程碑 | 地块尺寸范围 |
|---|---|---|
| Low Density Housing | 0 | 4–24 格，2×2 ~ 4×6 |
| Medium Density Row Housing | 1 | 2–6 格，1×2 ~ 1×6 |
| Medium Density Housing | 2 | 4–36 格，2×2 ~ 6×6 |
| **High Density Housing** | **8** | 4–36 格，2×2 ~ 6×6 |
| Mixed Housing | 5 | 4–36 格，2×2 ~ 6×6 |
| Low Density Business | 0 | 4–30 格，2×2 ~ 5×6 |
| **High Density Business** | **9** | 4–36 格，2×2 ~ 6×6 |

### 8.2 无主题分区（官方表）

| 分区 | 里程碑 | 地块尺寸 |
|---|---|---|
| **Low Rent Housing** | 4 | 4–36 格，2×2 ~ 6×6（"The lower rent provides lower tax income as a result."） |
| Industrial Manufacturing | 0 | 4–36 格，2×2 ~ 6×6 |
| Low Density Offices | 4 | 4–36 格，2×2 ~ 6×6 |
| **High Density Offices** | **10** | 4–36 格，2×2 ~ 6×6 |

> **密度与税收的官方原文（再次确认）**：低密度 **"supports fewer people but provide more taxes from each one"**；
> 高密度 **"supports more people but provide fewer taxes from each one"**；且**低密度更吸引家庭与长者，高密度更吸引学生与单身成人**。
> 另有官方劝告：**"If you're looking to build a massive city… use low density, as it needs less services, and takes up a larger space."**

### 8.3 专业化工业（官方表，逐字）

| 专业化 | 区域 | 所需里程碑 | 所需资源 | 噪声 | 地面污染 | 空气污染 |
|---|---|---|---|---|---|---|
| Livestock Farming | 农业区 | **3** | **（空）** | Low | — | — |
| Grain Farming | 农业区 | 4 | Fertile Land | Low | — | — |
| Vegetable Farming | 农业区 | 5 | Fertile Land | Low | — | — |
| Textile Fiber Farming | 农业区 | 6 | Fertile Land | Low | — | — |
| Forestry | 林业区 | 4 | Forest | Medium | — | — |
| **Stone Mining** | 矿区 | **3** | **（空）** | Medium | Medium | Medium |
| Coal Mining | 矿区 | 5 | Ore | Medium | Medium | Medium |
| Ore Mining | 矿区 | 7 | Ore | Medium | Medium | Medium |
| Oil Drilling | 石油区 | 8 | Oil | Medium | Medium | Medium（**火灾风险高于其它**） |

> ⚠️ **`Zoning` 表的里程碑与 `Progression` 表的"开局解锁 / 逐级解锁"表述不一致** → **C31**。以 `Progression`（1.1.5f1 版本标注更新）为准理解"什么时候能用"，`Zoning` 表只表示"区域类型最早出现在哪一级"。

### 8.4 建筑等级 1–5 的官方效果

| 类型 | 效果 |
|---|---|
| 通用 | 等级越高 → **upkeep 越高 → 租金越高**（等级反映居民富裕程度）；外观每 2 级变化一次 |
| 住宅 | **每户耗电耗水随等级下降**；**3 级与 5 级时**中/高密度住宅**可用公寓数增加** |
| 商业 | **单位商品耗电耗水下降**；**生产更快 → 可以卖得更便宜** → 市民**优先选择高等级商业** |
| 制造 / 办公 | **单位产出耗电耗水下降**；**垃圾与污染更少**；生产效率更高 |

---

## 9. 原始 prefab 字段名（`Service_building_data_test`，**S98**，无版本标注 → **O3**）

该页是一次**游戏 prefab 原始字段转储**，字段名就是游戏内部名。**这是本轮唯一能确认"字段语义"的官方来源**：

```
{{Service building test
 |Name=… |Circular=0|1 |Width=… |Depth=… |Construction_cost=…
 |Xp_reward=… |Category=… |Subcategory=…
 |Upkeep=… |Electricity_consumption=… |Water_consumption=… |Garbage_accumulation=…
 |Telecom_need=… |Workplaces=… |Workplace_complexity=…
 |Service_coverage_range=… |Service_coverage_capacity=… |Service_coverage_magnitude=…}}
```

**由此确认的语义**：

| 字段 | 含义 | 用途 |
|---|---|---|
| `Service_coverage_range` | **覆盖半径**（米） | = 官方表的 `Service range` |
| `Service_coverage_capacity` | **覆盖容量**（能服务多少市民，见 S91 通信段原文） | = 官方表的 `Service capacity` |
| `Service_coverage_magnitude` | **覆盖强度**（效果量的档位，如 Well-Being / 犯罪率 / 健康的加成大小） | 官方**从未解释**单位 → 只能**同表横向比较** |
| **`Circular`** | **覆盖形状是否为圆形**（1 = 圆形，0 = 方形/矩形） | **新事实**：并非所有服务的覆盖都是圆形 → "半径"对 `Circular=0` 的建筑只是**半个边长**的量级指标 |
| `Workplace_complexity` | 岗位复杂度（0–3，对应学历档） | 与官方表 `Max. needed education` 对应 |
| `Telecom_need` | 该建筑对通信网络的需求 | 官方表未列此列 |
| `maintenanceDuration` | 车辆维护周期（depot 类） | 官方表已列 |

> ⚠️ **数值与 `Service_buildings` 的 1.6 表冲突**（医院 5000 vs 7500、消防站 5000 vs 10000、警察总部 5000 vs 10000、小诊所/诊所 3500 vs 5000、小学 3000 vs 3500；**公园与地标两类完全一致**）。
> 一致与不一致同时存在 → **该页很可能是旧版本（1.0.x）的静态转储，其间医疗/消防/警务/小学的覆盖范围被上调过**。
> **引用纪律**：**覆盖数值一律以 `Service_buildings`（`{{SVersion|1.6|table}}`）为准**；该页**只用于取字段名与 `Circular` 语义**。**C28**。

---

## 10. 读表纪律（防止误用这批数据）

1. **按表头读，不要按位置读**：`Service_buildings` 各段的 extra 表**表头并不相同**（电力段是 `Ground/Air/Noise/Water`，垃圾段是 `Ground/Air/Noise/Electricity/Water`，医疗段是 `Electricity/Water` 无污染）。
   **跨段横向比"第 N 列"必然出错。**
2. **空格 ≠ 0**：官方表大量单元格为空（例如医院没有 `Noise pollution` 值），那是**该建筑没有这一项**，不是"噪声为 0"。
3. **`Cost` / `Upkeep` 列与 `Transportation` 页不一致**（C17 第三轮已证），本轮的 `Service_building_data_test` 又给出第三套（见 **C28**）→ **费用类数字以玩家建筑面板读数为最终依据**。
4. **`Service range` 是"需求未饱和时的最大半径"**（C23），且 **`Circular=0` 的建筑根本不是圆** → **不得写"某建筑保证覆盖 X km"**。
5. **本文件的数字都带版本**：`{{SVersion|1.6|table}}` = 1.6 数据；`{{Version|1.0}}` 正文 = 描述可信、数值可能滞后。**引用时必须带上这两者的区别。**

---

## 11. 本轮未能解决（不建议再花时间）

| 缺口 | 状态 | 建议 |
|---|---|---|
| 道路**通行能力**（pcu/h、饱和流率、车道通行量） | **第 4 次确认官方无此数据**（`Roads` 表只有车道数/限速/造价/维护/污染系数） | **建议停止追查**。用 `53`/`54` 的现实数值做**相对**比较即可，并显式标注"非游戏数值" |
| 各交通方式**单车载客量** | 第 4 次确认无 | **建议停止追查** |
| `Service magnitude` 的**单位与换算** | 字段名已确认（`Service_coverage_magnitude`），**官方无任何解释** | **建议停止追查**（只能横向比较） |
| `Circular` 字段的**实际形状**（矩形？沿路？） | 只知 0/1，**官方无说明** | 可列为下轮低优先级；**不要猜** |
| 覆盖半径被密度压缩的**定量曲线** | **仍无**（见 `00-sources.md` C23） | 见 C23 的处理方案（改用"官方 capacity 语义 + 游戏内着色"的组合口径） |
| 各难度模式对维护费的倍率 | 第三轮已关闭该缺口 | **不再追查** |

---

## 附：本文件用到的页面 URL（全部为 `?action=raw`，可复现）

- `Service_buildings`：https://cs2.paradoxwikis.com/index.php?title=Service_buildings&action=raw （+ `&section=N`）
- `Services`：https://cs2.paradoxwikis.com/index.php?title=Services&action=raw
- `Economy`：https://cs2.paradoxwikis.com/index.php?title=Economy&action=raw
- `Progression`：https://cs2.paradoxwikis.com/index.php?title=Progression&action=raw
- `Roads`：https://cs2.paradoxwikis.com/index.php?title=Roads&action=raw
- `Policies`：https://cs2.paradoxwikis.com/index.php?title=Policies&action=raw
- `Citizens`：https://cs2.paradoxwikis.com/index.php?title=Citizens&action=raw
- `Zoning`：https://cs2.paradoxwikis.com/index.php?title=Zoning&action=raw
- `Service_building_data_test`：https://cs2.paradoxwikis.com/index.php?title=Service_building_data_test&action=raw
- `Special:AllPages`：https://cs2.paradoxwikis.com/index.php?title=Special:AllPages&action=raw
- Wiki 全文检索（用于 C25 的负面证据）：https://cs2.paradoxwikis.com/index.php?search=%22Heavy+Traffic+Ban%22&fulltext=1
