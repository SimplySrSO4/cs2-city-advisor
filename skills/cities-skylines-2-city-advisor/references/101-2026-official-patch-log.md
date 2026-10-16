# 101 · 2026 年官方更新日志（**只收 2026-01-01 之后**）

> **可信度等级：全部为最高可信度。**
> 本文件只收**官方通告**（Paradox 官网新闻页 / 官方论坛由官方账号发布的补丁说明 / 官方 Wiki 转录的补丁说明）。
> **⚠️ 本文件不含任何玩家讨论内容** —— 见 §7「本次采集的局限」。
>
> **用途**：`SKILL.md` 与其它 references 里凡涉及版本分期、机制数值、被修掉的 bug，
> **一律以本文件为最新依据**；与本文件冲突的旧结论按本文件更新。
>
> 采集时点：**2026-09 末**。最新补丁 **1.6.2f1 (2026-09-15)**。

---

## 0. 版本时间线（2026-01-01 之后）

| 日期 | 版本 / 期号 | 标题 | 性质 |
|---|---|---|---|
| 2026-01-29 | City Corner #1 | Upcoming Visual Updates | 预告（视觉） |
| 2026-02-12 | City Corner #2 | Upcoming Gameplay Updates | 预告（玩法） |
| 2026-02-18 | **1.5.4f1** | **First Frost** | **正式补丁** |
| 2026-03-12 | City Corner #3 | Free Anniversary Update | 预告（免费更新） |
| 2026-03-18 | — | Office Evolution & City Stations 发售 + 免费补丁 | 内容 + 补丁 |
| 2026-04-09 | City Corner #4 | A Peek into Performance | 预告（性能） |
| 2026-04-23 | City Corner #5 | Spring Cleaning | 预告 |
| 2026-04-29 | **1.5.7f1** | **Spring Cleaning** | **正式补丁** |
| 2026-05-21 | City Corner #6 | Community Chat | 社区 |
| 2026-05-26 | City Corner #7 | Morning Dew | 预告（交通） |
| 2026-05-27 | **1.5.9f1** | **Morning Dew** | **正式补丁** |
| 2026-06-11 | City Corner #8 | Transforming the Terrain | 预告（地形） |
| 2026-06-22 | **1.6.0f1** | **Summer Solstice** | **正式补丁** |
| 2026-07-23 | City Corner #9 | Happy Six Months | 回顾 |
| 2026-08-11 | City Corner #10 | Expanding the Modding Tools | 预告（模组） |
| 2026-08-20 | City Corner #11 | Autumn Breeze | 预告（玩法+视觉） |
| 2026-09-03 | City Corner #12 | Collected Questions | Q&A |
| 2026-09-15 | **1.6.2f1** | **Autumn Breeze** | **正式补丁** |
| 2026-09 | City Corner #13（计划） | — | **下一次补丁在 2026-09 中旬之后**（`#12` 称"mid-September"） |

> ⚠️ **另有 `1.5.8f1` 与 `1.5.10f1` 两个版本号存在**（官方 Wiki 版本导航列出），
> 但本次未取到其补丁说明正文 —— **不要把这两个版本的改动当已知**。

---

## 1. ⭐⭐ 会**直接改变诊断结论**的机制（务必优先读这一节）

### 1.1 幸福度改用「收入」而不是「财富」（1.6.2f1）

> 官方原文：「Citizen happiness, shopping, and leisure choices now use **income rather than wealth**.
> Because citizens adjust their spending to match their financial situation, current wealth is a poor
> measure of how well off they are, making income a much better indicator.」

* **含义**：1.6.2f1 之前，市民的**购物/休闲/幸福度**判断基于**累计财富**（波动大、不代表实际境况）；
  现在基于**收入**。
* **对 skill 的影响**：
  * **幸福度与"收入"挂钩 ⇒ 就业质量（学历→工资档）比"存款"更能解释幸福度**。
    这与 `45` 的「住宅税基 = 工资 × 税率」形成**同一条杠杆**：
    **提高学历结构同时抬升税收与幸福度** —— 这是本 skill 里少见的"两个目标同向"的动作。
  * 诊断"幸福度低"时，**先看就业与工资结构，不要先归因于服务**（服务仍重要，但归因顺序要变）。

### 1.2 住宅需求开始考虑城市规模（1.6.2f1）

> 官方原文：「Residential demand now takes the **size of the city** into account when calculating the
> impact of empty residential properties, **fixing the lack of residential demand in very large cities**.」

* **含义**：**1.6.2f1 之前，大城市会出现"住宅需求莫名塌陷"** —— 这是 bug，不是玩家的规划错误。
* **对 skill 的影响**（**这条最重要**）：
  * **遇到"城市很大但住宅需求起不来"，先问玩家的版本号**。
    若 < 1.6.2f1 → 很可能是这个 bug，**不要**据此建议"停止供地/调整税率"。
  * 从 1.6.2f1 起，**住宅需求与"空置住宅数"挂钩** → 「已划未建」和「建成空置」要分开看。
  * 这直接支撑本 skill 的**第 0 层（城市规模持续扩大）**：旧版本上"长不大"可能是引擎 bug。

### 1.3 寻路距离上限**按出行目的分设**（1.6.0f1）

> 官方原文：「Fixed citizens taking absurdly long trips across the entire map. **Pathfinding limits are
> now tailored per trip type: work, school, shopping, and leisure each use a sensible range** rather than
> a shared near-unlimited cap. Citizens who can't find a viable route now handle it gracefully:
> **move-outs teleport off-map, workers drop their job, and leisure-seekers idle at home** before retrying.
> — Note: there is at least one known remaining issue where students may still walk too far.」

* **对 skill 的影响**：
  * `46` T5c 记的这条**已确认成立**，并补充了细节：**找不到路线时 = 搬迁者直接离图、
    工作者辞职、休闲者在家闲置**。⇒ 路网/公交的"不可达"会**直接表现为岗位空缺与人口流失**。
  * **学生仍可能走得过远**（官方已知问题）⇒ 学区类结论要留余地。
  * **"超长通勤"在 1.6.0f1 之前是普遍现象** ⇒ 旧存档的 §18 通勤距离读数**不可与新版本横向比较**。

### 1.4 购物不再"只看库存、无视距离"（1.6.0f1）

> 官方原文：「Fixed a bug where citizens would always travel to the shop with the most stock,
> **completely ignoring distance**.」

* **含义**：1.6.0f1 之前，市民会跑到**库存最多**的商店，**完全不管远近**。
* **对 skill 的影响**：
  * **商业选址/可达性分析在 1.6.0f1 之前基本失效** —— 那时的商业客流与"距离"无关。
  * 1.6.0f1 起，**商业的成败才真正取决于周边需求与可达性** ⇒ 之后才适合用 §9 的
    "每公顷商业产出"做选址建议。
  * 结合 1.5.7f1 的「商业需求改按**平均备货水平**」与 1.6.2f1 的「商业需求小幅下调」，
    **商业相关结论的版本敏感性很高**，必须标版本。

### 1.5 垃圾清运逻辑与幸福度（1.6.2f1）

* 垃圾车**改为为目的地的垃圾预留容量**，跳过沿途垃圾很少的建筑 → 更少"垃圾堆积"警报。
* **「Garbage now has more effect on citizens' happiness」** ⇒ **垃圾处理是幸福度的更强杠杆**（1.6.2f1 起）。
* 官方在 City Corner #11 补充：**「clean homes providing a greater happiness bonus」**。
* **对 skill 的影响**：幸福度诊断里**垃圾/殡葬这类"基础服务"的权重上升**；
  但 1.5.4f1 已修掉"死亡潮"（见 §2.1），**殡葬压力反而下降** —— 两者不要混为一谈。

### 1.6 公司租赁按"资源紧缺度"排序（1.6.2f1）

> 官方原文：「Companies producing the **most-needed resources** in the city are now prioritized when
> renting properties, preventing companies producing less-needed resources from claiming available
> properties before them.」

* **对 skill 的影响**：**划区后出现的公司类型更可能"是城市需要的"**，
  公司类型**多样性上升**，需求条回落更准确。
* ⇒ 1.6.2f1 起，「划了区但公司类型不对」的诊断**优先级下降**；
  若仍出现，先怀疑**本地缺原料/缺进口通道**，而不是"引擎乱刷公司"。

### 1.7 新增官方明文杠杆：`Historical Building` 选项（1.5.7f1）

> 官方原文：「Historic Building - When enabled, **selected buildings will be prevented from leveling up
> or being abandoned**.」

* **对 skill 的影响（重要）**：这是官方给的**直接抑制"升级/废弃"的开关**。
  * 与 `45` 的「升级 = 税收的长期决定因素」配合使用：
    **想保住某片低密度/历史街区**时，用它替代"降税率"或"停止服务"这类副作用大的手段。
  * 也意味着：**"建筑等级不涨"可能是玩家自己开了这个开关** —— 诊断税基停滞时**必须问这一项**。

---

## 2. 逐版本机制与数值改动

### 2.1 `1.5.4f1` First Frost（2026-02-18）

| 改动 | 官方原文要点 | 对 skill 的影响 |
|---|---|---|
| **自行车出行 −80%** | 「Reduced bicycle trips by 80%」 | ⭐ **任何自行车/慢行分析必须用这个前提**。1.5.4f1 前后**不可比较**；旧攻略里"自行车堵路"的建议已失效 |
| **死亡时间修正** | 「Fixed time of day not taken into account when determining death, causing most citizens to die between 0 and 6 o'clock」 | **"死亡潮"是 bug**，不是规划问题。1.5.4f1 前大量市民挤在 0–6 点死亡 → 殡葬设施被瞬时打爆 |
| **死亡计算频次 ×4** | 「Calculate deaths 16 times per citizen per day instead of 4」 | 死亡更平滑 ⇒ **殡葬容量需求下降** |
| **Easy 模式会正常死亡** | 「Previously, about **80% of them never died of old age**」 | ⭐ **Easy 模式的人口结构在 1.5.4f1 前后完全不同**：之前几乎不死亡 → 年龄金字塔失真、人口只增不减 |
| 地形工具预设更精细 | elevation tool 默认预设更精确、更不激进；模式专属笔刷预设 | 整地成本可预测性提升 |
| 树龄保留开关 | 「Tree age preservation toggle」 | 纯视觉 |
| `Urban Cycling Initiative` 政策错字修正 | — | 见 2.2 的实际数值改动 |

> **City Corner #2 补充**：**「less work for your hearses」**（殡葬压力下降）；
> 并列出当时**仍在调查**的问题：pathfinding、**最后一刻变道**、**不必要的掉头**、
> **火车卡在城市边界** —— 前两者在 1.5.9f1 修掉，**火车卡边界在 2026-02 时仍未解决**。

### 2.2 `1.5.7f1` Spring Cleaning（2026-04-29）

| 改动 | 官方原文要点 | 对 skill 的影响 |
|---|---|---|
| **教育系统平衡** | 「The Education system has been balanced to better align elementary and high school demand, **reducing extreme imbalance with elementary schools while high schools remained underused**」 | ⭐ **小学/中学需求失衡是引擎问题**。1.5.7f1 前"小学爆满、中学空置"很常见 |
| **`Urban Cycling Initiative` 政策 20% → 50%** | 「now increases bicycle usage from **20% to 50%**」 | ⭐ **政策数值变了**。旧记录里是 20%，**不要再引用 20%** |
| **混合住宅 bug 修复** | 「Fixed mixed housing causing **commercial and medium-density residential demand to permanently stay low**」 | ⭐ 1.5.7f1 前，**建了混合住宅会让商业与中密度住宅需求永久偏低** —— 这是 bug，别当成规划错误 |
| **甲级办公（signature office）bug** | 「incorrectly treated as available for sale, causing **office demand to drop even while occupied**」 | 1.5.7f1 前"办公需求莫名下降"可能是这个 |
| **办公需求数据源修正** | 移除一个 multiplier workaround，之前**导致 Software 公司刷太多**；**城市生产统计改为更长时段采样**，减少昼夜波动 | ⭐ **"生产统计"现在是长时段采样** —— 与 `70` 里"`Passenger` 是瞬时读数"的告诫**方向相反**：生产统计变得**更稳**，可以更放心用 |
| **商业需求改按备货水平** | 「Commercial demand is now based on **how well-stocked your shops are on average**」；并修掉"少数商业建筑收不到顾客就把需求打死" | ⭐ **商业需求 = 平均备货水平** ⇒ 诊断商业需求时**先查供应链是否通畅**，不是先查人口 |
| **城外连接支持非高速路** | 「Fixed outside connections **not working with non-highway roads**」 | ⭐ **1.5.7f1 前，只有高速能真正连通城外**！这直接影响"必须用高速接城外"这条旧建议 |
| **公交/有轨电车永久上客 bug** | 「buses and trams could get stuck in a **permanent boarding state** at busy stops, preventing departure and causing vehicle queues and despawning」 | ⭐⭐ **"公交在繁忙站点卡死、车辆排队并消失"是 bug** —— 1.5.7f1 前，**公交运力差可能完全不是规划问题**。诊断公交前必须问版本 |
| **建筑升级停滞 bug** | 资源配送处理被跳过时升级卡住、等级指示器不动 | 1.5.7f1 前"等级不涨"可能是这个 |
| **办公停止生产/交易** | 「some offices could stop producing or trading in certain situations」 | — |
| 市民不再打车搬入 | 「Stopped citizens from moving in and out with **taxis** to reduce the move-in traffic」 | 迁入交通量下降 |
| 狗的数量下调 | 调整家庭宠物上限与生成概率 | 噪声/幸福度的微小影响 |
| 港口邮件寻路修正 | — | — |
| 学生只能在"学习时间"参加休闲活动的 bug | — | 与 1.5.4f1 的"幼儿不再上学"相关 |

### 2.3 `1.5.9f1` Morning Dew（2026-05-27）—— 交通

> City Corner #7 给出了**机制层面的解释**（比补丁说明更有价值）：
> * **掉头成本**：官方原文「Previously, **the cost of a legal U-turn was 0**, so it was always considered
>   a valid option when it came to routing. We have now **increased the cost significantly**…
>   We have also done the same for **unsafe U-turns and increased the cost even higher**.」
>   ⇒ ⭐⭐ **"车辆到处掉头"在 1.5.9f1 前是引擎允许的免费操作**，不是规划问题。
> * **变道时机**：官方原文「vehicles tend to **switch lanes too late**, which has also caused a lot of
>   traffic jams… improved the lane merges to be more realistic, so that the vehicles will actually
>   **change lanes at an earlier point. This should be especially noticeable with highway exit behavior**」
>   ⇒ ⭐⭐ **高速出口的"最后一刻变道"是 1.5.9f1 修的**。
>   **在旧版本上做"匝道/交织区"诊断会严重高估问题的严重性**。

| 改动 | 官方原文要点 | 对 skill 的影响 |
|---|---|---|
| 减少不必要的掉头 | Vehicles now make fewer unnecessary U-turns | 见上 |
| 更早选择转向车道 | 「Vehicles now choose their turn lanes **earlier** when approaching highway exits or intersections」 | ⭐ **§19 的"高速出口/交织区"拥堵在 1.5.9f1 前后不可比** |
| **水电费 bug** | 「citizens and companies used the **electricity fee instead of the water fee** when calculating electricity costs」 | ⭐ **电费被按水费算** —— 1.5.9f1 前"调水费影响电费"的观察是 bug 现象 |
| 煤电厂无法派车买煤 | — | 电力供应稳定性 |
| **专业工业（农场等）货车不出门** | 「Delivery trucks now properly leave specialized industry buildings… to export and sell their stock, **preventing cargo from piling up**」 | ⭐ 1.5.9f1 前**专业工业会货物堆积、卖不出去** |
| 自然资源枯竭速度 | Easy 模式下按**预期较慢**速度枯竭 | 与 1.5.4f1 的同一问题延续修复 |
| 教育覆盖层显示错误 | 幼儿不再上学后，覆盖层仍把幼儿算作小学适龄 | 见 2.2 |
| **酒店顾客数** | 「Hotels no longer show the wrong customer count. **The count will reset at midnight**」 | 与"快照读数"同理：**酒店类读数有"当日清零"语义** |
| 分区网格/边线颜色与透明度滑块 | 新增 | 制图相关 |
| 工具参数跨工具保留 | 如道路高程 | 建造体验 |

### 2.4 `1.6.0f1` Summer Solstice（2026-06-22）—— 本年度最重要的模拟改动

| 改动 | 官方原文要点 | 对 skill 的影响 |
|---|---|---|
| ⭐⭐ **按目的分设寻路上限** | 见 §1.3 | **通勤/上学/购物/休闲各有合理范围**；找不到路 → 辞职/搬离/在家闲置 |
| ⭐ **购物不再无视距离** | 见 §1.4 | 商业选址分析在 1.6.0f1 之后才成立 |
| ⭐ **掉头成本再调整** | 「Fixed legal U-turn costs to allow citizens to use **dedicated lanes** more flexibly and **lowered illegal U-turn costs** to match intended limits」 | ⚠️ **1.5.9f1 把掉头成本大幅提高后，1.6.0f1 又回调了** —— 两个版本的行为**不同**，不能合并叙述 |
| **办公货物可从城外购买** | 「Office goods can now be purchased from outside connections, improving supply chains when local sources are unavailable」 | ⭐ 办公不必再依赖本地货源 |
| **商业需求小幅下调** | 「Adjusted commercial demand slightly lower for balancing」 | ⭐ **商业需求基准变了**，跨版本比商业需求无意义 |
| **升级后丢失道路接入** | 「Fixed buildings sometimes losing road access after leveling up」 | 1.6.0f1 前"升级后建筑废弃"可能是这个 |
| 家庭重新评估搬家频率降低 | 提升大城市性能 | — |
| 游客/通勤者少走高速路肩 | — | — |
| **地形材质可在游戏内绘制与擦除** | 「You can now paint and erase terrain materials in-game」 | ⭐ 地形改造自由度上升（与 §5 制图相关） |
| 地形工具强度随笔刷尺寸缩放 | — | — |

**UI**
| 改动 | 影响 |
|---|---|
| ⭐ **等高线开关 + 可自定义按键**（默认未绑定） | ⭐ **游戏内现在有等高线显示**！本 skill 的 §8.3 高程分析可以在游戏里直观核对 |
| 地形纹理绘制工具（笔刷选择与旋转 Shift+滚轮） | 制图 |
| 生产统计图首个数据点异常小 | 与 1.5.7f1 的长时段采样配套 |

### 2.5 `1.6.2f1` Autumn Breeze（2026-09-15）—— 最新补丁

已在 §1.1 / §1.2 / §1.5 / §1.6 详述的四项之外，还有：

| 改动 | 官方原文要点 | 对 skill 的影响 |
|---|---|---|
| ⭐ **青年不再立即搬出** | 「teens who became adults would often **move out immediately, causing a gap in the age pyramid**. Now fresh adults **delay moving out of their parents' home until they can find a home they can afford**」 | ⭐ **年龄金字塔断层是 bug**。1.6.2f1 前"年轻人大量流失"不要归因于规划 |
| **车辆被遗留在公交站** | 「Fixed cars sometimes being left behind, especially **at transit stations**, when a citizen returns home using other means」 | ⭐ **P+R / 停车换乘类分析**在 1.6.2f1 前会看到异常滞留车辆 |
| 搬家时车辆遗留 / 因无停车位被移到城外再取回 | 同上 | 停车与车流分析 |
| **办公无法从城外进口 Software** | — | 与 1.6.0f1 的"办公可从城外购买"配套 |
| **邮局分拣升级反而禁用本地邮件进口** | 「disabled the ability to import local mail, resulting in too little local mail」 | ⭐ 1.6.2f1 前**建了分拣升级反而邮件不足** |
| 无家可归者与家人协调出行卡死 | — | — |
| **轻微重叠就不能拆/移建筑** | 「Fixed not being able to bulldoze or relocate buildings when their removal would cause **minor overlaps**」 | ⭐ 1.6.2f1 前**改造旧城区常被"轻微重叠"卡住** |
| ⭐ **政策滑块取整 bug** | 「policy slider rounding could result in a **slightly different value being applied than what was displayed**」 | ⭐⭐ **1.6.2f1 前，政策滑块显示值与实际生效值可能不一致** ⇒ 引用玩家报的政策数值时要留余地 |
| ⭐ **面板不显示预算对工资的影响** | 「Selected Info Panel upkeep section **not showing the service budget effect on wages**」 | ⭐ 与 `45` §A4.1「预算同时影响容量与工资支出」呼应 —— 1.6.2f1 前**面板上看不到这一项** |
| 水相关视觉数值修正 | — | — |
| 夜间月光阴影重新启用 | 之前误关 | 纯视觉 |
| 新树：European Spruce | — | — |
| 地形纹理：新增材质、三级 LOD、三轴投影岩石贴图 | 视觉 | 制图观感 |

**City Corner #11 的补充说明（预告即最终内容）**：
* 垃圾车改动「**applies to all buildings**」，垃圾堆积警报会减少，「**这与市民幸福度相关**」。
* 公司租赁优先级改动「**will also act as a foundation for future improvements** on how the resource
  economy works」⇒ **资源经济后续还会改**，相关结论要标版本。

---

## 3. 内容包 / DLC（2026 年）

### 3.1 `Office Evolution`（2026-03-18，Creator Pack）
* 为**高密度办公区**新增**签名建筑**（signature buildings），"blend heritage character and modern design"。
* ⇒ §8.2 的"建筑等级/签名建筑"分析里会出现这些资产。

### 3.2 `City Stations`（2026-03-18，Creator Pack）
* 紧凑车库（compact depots）、**详细铁路站场（rail yards）**、替代车站设计、新地标。
* 与基础游戏的公交/轨道资产并存 ⇒ **站点计数类分析要按资产名区分**。

### 3.3 免费补丁（同日）
* **道路分区开关（zoning toggle）**：可移除道路**任一侧或两侧**的分区 —— 灵感来自社区 mod。
  ⇒ ⭐ **本 skill 的"用地/分区"建议多了一个官方工具**：可以在保留道路的同时**精确控制沿街可建面**。
* **`Iceflake Arena`**：签名商业建筑，**在城市 2 km 半径内提升 attractiveness 与 well-being**。
  ⇒ ⭐ 这是**有明确半径的官方幸福度设施**，可纳入 §16 的服务覆盖分析（半径 2000 m）。

---

## 4. `City Corner #12`（2026-09-03）官方表态

虽然不含硬数值，但有**两条对 skill 有用的官方立场**：

1. **玩家影响模拟的三个间接手段被官方点名**：
   「players influencing them indirectly through things like **taxes, subsidies and their transportation
   networks**」⇒ 与 `45` 的杠杆清单一致，可作为"官方承认的三大杠杆"引用。
2. **性能现状**：「On the CPU side, **pathfinding still remains one of the bigger challenges**」
   ⇒ 大城市卡顿**主要来自寻路**，不是玩家规划错误。
3. **官方修 bug 的方法论**：先修底层问题 → 观察系统行为 → 再决定是否平衡性调整。
   ⇒ 意味着**同一系统的数值可能被反复调整**，引用时务必带版本。

---

## 5. 与本 skill 现有内容的关系（**需要改的地方**）

| 现有位置 | 原内容 | 应改为 |
|---|---|---|
| `SKILL.md` 版本相关表述 | 以 1.1.x / 1.6 为参照 | **以 1.6.2f1 (2026-09-15) 为最新**；1.5.4f1 是"机制分水岭"（自行车、死亡） |
| `45` / `40` 自行车政策数值 | `Urban Cycling Initiative` 20% | **50%**（1.5.7f1 起） |
| 任何"死亡潮/殡葬压力"结论 | 视为规划问题 | **1.5.4f1 前是 bug**；Easy 模式 1.5.4f1 前约 80% 不老死 |
| "必须用高速接城外" | 旧结论 | **1.5.7f1 起非高速路也可连通城外** |
| 公交运力差 → 规划问题 | — | **先排除 1.5.7f1 的"站点永久上客"bug** |
| 掉头/变道 → 规划问题 | — | **1.5.9f1 前掉头成本为 0、变道过晚**；且 1.6.0f1 又回调了掉头成本 |
| 通勤距离跨期比较 | — | **1.6.0f1 起寻路上限按目的分设** ⇒ 跨版本不可比 |
| 商业客流/选址分析 | 直接用 §9 | **1.6.0f1 前"购物无视距离"**；商业需求口径在 1.5.7f1、1.6.0f1 各改过一次 |
| 幸福度归因 | 服务/污染优先 | **1.6.2f1 起幸福度基于"收入"** ⇒ 先看就业与工资结构；垃圾的影响也加强了 |
| 建筑等级停滞 | 视为经济问题 | **先问是否开了 `Historical Building`** 开关 |
| 政策数值引用 | 直接引用玩家报的数 | **1.6.2f1 前滑块取整可能不一致** |
| 制图 | 自己算等高线 | **游戏内已有等高线开关（1.6.0f1）**，可与 §8.3 互校 |

---

## 6. 术语：官方把"可靠度"的两种来源分开

官方在 City Corner 系列里稳定区分两类表述，本 skill 引用时也应区分：

| 类型 | 官方措辞 | 本 skill 的可信度标注 |
|---|---|---|
| **已实装** | 补丁说明（Patch Notes）里的条目 | **最高**（可写进报告作为事实） |
| **预告/计划** | City Corner 里的 "upcoming / we are planning / we have been thinking about" | **次高**（写明"官方预告，尚未实装"，并注明官方自述的预计版本） |
| **已知未修** | "Known Issues" 段落 | **最高**（可写进报告作为"这不是你的规划问题"的依据） |
| **仍在调查** | "we are still investigating" | 中（写明"官方在调查中"） |

> ⚠️ **不要**把 City Corner 的预告当已实装机制写进报告 —— 本次采集里
> City Corner #11 的内容在 1.6.2f1 全部实装，但**并非所有预告都会按期实装**。

---

## 7. 本次采集的局限（**必须如实告知用户**）

1. **⚠️ 未能采集到玩家讨论内容。** 官方论坛
   `forum.paradoxplaza.com/forum/forums/cities-skylines-2.1147/` **对所有抓取尝试返回
   "Validating browser…"（JS 挑战页）**；其 RSS 端点返回 **HTTP 403**。
   因此**本文件只含官方通告，不含任何玩家帖**。
   若后续需要玩家侧的"最低可信度"信息，需要用户在浏览器中协助导出，或提供可访问的镜像。

2. **`1.5.8f1` 与 `1.5.10f1` 的补丁说明正文未取到**（仅从官方 Wiki 版本导航确认其存在）。

3. **官方 Wiki 的补丁转载属"官方账号发布内容的转录"**：
   1.6.0f1 / 1.6.2f1 两节的正文来自官方 Wiki，其页脚标注的原始出处是
   **官方论坛由 `Official Cities: Skylines Account` 与 `ifs_Blu`（Iceflake 社区经理）发布的帖子**，
   因此按**最高可信度**处理；但严格说是"转载"，若需绝对权威请以论坛原帖为准。

4. **版本号之后还会变**：City Corner #12 明确下一次补丁在 2026-09 中旬之后；
   公司租赁与资源经济官方已说明「还会继续改」。

---

## 8. 数据来源（官方，全部为最高可信度）

| # | 来源 | URL | 日期 |
|---|---|---|---|
| P1 | Paradox 官网 · Patch 1.5.4f1 First Frost | https://www.paradoxinteractive.com/games/cities-skylines-ii/news/patch-notes-first-frost | 2026-02-18 |
| P2 | Paradox 官网 · Spring Cleaning 1.5.7f1 | https://www.paradoxinteractive.com/games/cities-skylines-ii/news/patch-notes-spring-cleaning | 2026-04-29 |
| P3 | Paradox 官网 · Patch 1.5.9f1 Morning Dew | https://www.paradoxinteractive.com/games/cities-skylines-ii/news/patch-notes-morning-dew | 2026-05-27 |
| P4 | Paradox 官网 · City Corner #2 Upcoming Gameplay Updates | https://www.paradoxinteractive.com/games/cities-skylines-ii/news/upcoming-gameplay-updates | 2026-02-12 |
| P5 | Paradox 官网 · City Corner #7 Morning Dew | https://www.paradoxinteractive.com/games/cities-skylines-ii/news/morning-dew | 2026-05-26 |
| P6 | Paradox 官网 · City Corner #11 Autumn Breeze | https://www.paradoxinteractive.com/games/cities-skylines-ii/news/autumn-breeze | 2026-08-20 |
| P7 | Paradox 官网 · City Corner #12 Collected Questions | https://www.paradoxinteractive.com/games/cities-skylines-ii/news/collected-questions | 2026-09-03 |
| P8 | Paradox 官网 · Office Evolution & City Stations Available Now | https://www.paradoxinteractive.com/games/cities-skylines-ii/news/office-evolution-and-city-stations-available-now | 2026-03-18 |
| P9 | Paradox 官网 · 新闻索引（用于确定 2026 年全部官方帖） | https://www.paradoxinteractive.com/games/cities-skylines-ii/news | — |
| P10 | 官方 Wiki · Patch 1.6.X（转录官方论坛 1.6.0f1 / 1.6.2f1 补丁说明） | https://cs2.paradoxwikis.com/Patch_1.6.X | 2026-06-22 / 2026-09-15 |
| P11 | 官方 Wiki · Developer diaries 索引（含全部 City Corner 期号与日期） | https://cs2.paradoxwikis.com/Developer_diaries | — |
