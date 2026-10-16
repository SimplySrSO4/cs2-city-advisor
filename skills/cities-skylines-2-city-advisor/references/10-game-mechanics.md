# 10 · 《都市天际线 2》机制总览

> 适用版本：以 **1.6.2f1（2026-09-15）** 为基准；凡跨版本变化处均标注版本号。
> 每条结论后附 `（来源：URL）`。数值细节见 `40-number-tables.md`，冲突登记见 `00-sources.md` 第四节。

---

## 0. 一句话总纲

CSL2 的核心循环是：**分区 → 需求 → 人口与学历 → 岗位匹配 → 公司与利润 → 税收与地价 → 建筑升级/衰败**；交通与服务是把这个循环连起来的**物理约束**。
**1.1.5f1「Economy 2.0」是断代点**：政府补贴被彻底移除，租金/地价/建筑升级被绑死在一起，税率对需求的杠杆被显著增强。1.1.5f1 之前的任何经济攻略都不再适用。（来源：https://cs2.paradoxwikis.com/Patch_1.1.X ）

---

## 1. 分区（Zoning）

### 1.1 分区类型与密度（共 5 大类 + 专业化工区）

| 分区 | 子类（解锁里程碑） | 地块尺寸范围（宽×深，单位=格） |
|---|---|---|
| 住宅 Residential | 低密度住宅（M0）、中密度联排（M1）、中密度住宅（M2）、**混合用途住宅 Mixed Housing（M5）**、高密度住宅（M8）、低租金住宅 Low Rent（M4，无主题） | 低密度 4–24 格（2×2~4×6）；中/高/混合 4–36 格（2×2~6×6）；联排 2–6 格（1×2~1×6） |
| 商业 Commercial | 低密度商业（M0）、高密度商业（M9） | 低密度 4–30 格（2×2~5×6）；高密度 4–36 格（2×2~6×6） |
| 工业 Industrial | 工业制造（M0） | 4–36 格（2×2~6×6） |
| 办公 Office | 低密度办公（M4）、高密度办公（M10） | 4–36 格（2×2~6×6） |
| 专业化工区 Specialized Industry | 见 1.3 | 由中心建筑 + 可调矿业/农业多边形定义，范围受中心建筑半径限制 |

（来源：https://cs2.paradoxwikis.com/Zoning ，表格数据 1.0；里程碑号来自同页表格与 https://cs2.paradoxwikis.com/Progression ）

> 注意：专业化工区的解锁里程碑在 **1.1.5f1** 被整体提前——Livestock Farming（畜牧）、Stone Mining（采石）、Grain Farming（谷物）、Forestry（林业）**开局即解锁（milestone 0）**；Vegetable Farming、Coal Mining 在 Tiny Village；Textile Fiber Farming 在 Small Village；Ore Mining 在 Large Village；Oil Drilling 在 Grand Village。（来源：https://cs2.paradoxwikis.com/Progression ）

### 1.2 两套主题（Theme）
European / North American 两套建筑风格，仅影响外观与**限速显示值**，不影响分区可用尺寸。（来源：https://cs2.paradoxwikis.com/Zoning ；限速差异见 https://cs2.paradoxwikis.com/Roads ）

### 1.3 专业化工区（Specialized Industry）
共 9 类：Livestock Farming、Grain Farming、Vegetable Farming、Textile Fiber Farming（棉花）、Forestry、Stone Mining、Coal Mining、Ore Mining、Oil Drilling。1.3.6f1 新增 **Fishing（渔业，含公海养殖）** 与 **Offshore Oil（海上油气）**。（来源：https://cs2.paradoxwikis.com/Zoning ；https://cs2.paradoxwikis.com/Patch_1.3.X ）

关键机制：
- **畜牧与采石不需要自然资源**，其余需要对应资源图层。
- 公司**永远不会**迁入缺少所需资源的专业化工区。专业化工区建筑**不会废弃**（abandoned），但公司会随利润进出。（来源：https://cs2.paradoxwikis.com/Zoning ）
- 专业化工区车辆**不走城市道路**，只在工区内部由模拟生成的路径上行驶。这是"专业化工区不堵路"的原因。（来源：https://www.paradoxinteractive.com/games/cities-skylines-ii/features/economy-production ）
- 专业化工区公司**不会破产**，只会缩产裁员（利润下降时）。（同上）
- 污染：所有采矿/钻油类同时产生 Medium 级噪音+地面+空气污染；林业仅 Medium 噪音；农业类仅 Low 噪音。**Oil Drilling 火灾风险更高**。（来源：https://cs2.paradoxwikis.com/Zoning ）
- Ore / Oil 为有限资源会枯竭；Fertile Land / Forest 会再生但会被污染破坏。（来源：https://www.paradoxinteractive.com/games/cities-skylines-ii/features/economy-production ）

### 1.4 分区贴邻：官方怎么说、没怎么说
- **官方没有给出"分区贴邻惩罚/加成"的数值表**。可确证的是**软性相互依赖**：商业"靠近住宅区能获得顾客"；工业"优先在本地销售更赚钱"；办公"更重要的是靠近潜在劳动力居住区"。（来源：https://cs2.paradoxwikis.com/Zoning ；https://www.paradoxinteractive.com/games/cities-skylines-ii/features/economy-production ）
- **可确证的硬性相邻惩罚**来自污染与噪音：工业（尤其专业化工业）产生噪音/地面/空气污染，**1.3.6f1 起工业噪音的量与扩散半径都被上调**，官方原话要求"新城市在工业与住宅之间留出更大空间，现有城市可能需要重新分区"。（来源：https://cs2.paradoxwikis.com/Patch_1.3.X ）
- 大型道路本身**降低周边地价并产生噪音**。（来源：https://cs2.paradoxwikis.com/Roads ）
- **结论**：所谓"贴邻惩罚"在 CSL2 里主要是**污染 + 噪音 + 租金**三条通道，而不是一张隐藏的相邻矩阵。**待验证**：是否存在未公开的贴邻权重。

### 1.5 特色建筑（Signature Buildings）
- 按分区类型提供加成，游戏中显示为 "Commercial Efficiency" / "Industrial Efficiency"。（来源：https://cs2.paradoxwikis.com/Economy ）
- 1.3.6f1 修复了 Signature 建筑工业效率加成被**重复求和**的 bug（此前会叠得过高）。（来源：https://cs2.paradoxwikis.com/Patch_1.3.X ）
- 1.5.7f1 修复"签名办公楼被错误标记为可售，导致即使满租办公需求仍然下降"。（来源：https://cs2.paradoxwikis.com/Patch_1.5.X ）
- 1.1.10f1 修复"签名商业建筑无公司时仍播放音效 / 信息视图误显示 Occupied"。（来源：https://cs2.paradoxwikis.com/Patch_1.1.X 、https://cs2.paradoxwikis.com/Patch_1.2.X ）
- 地标（Landmarks，需 Landmark DLC 或成就解锁）如 Notre-Dame、Bell Tower of Xi'an：**吸引力 100–175**，**服务半径 6000–10000 / 容量 10000–20000 / 强度 16–20**，1.2.5f1 起**地标不再成为无家可归者营地**。（来源：https://cs2.paradoxwikis.com/Service_buildings ；https://cs2.paradoxwikis.com/Patch_1.2.X ）

---

## 2. 需求（RCIO Demand）

### 2.1 需求的真实成因（官方口径）
**住宅需求**由以下因素驱动：
1. 新市民想搬入（为工作、为求学、或因为城市宜居）；
2. 工商业/办公岗位增加；
3. **家庭规模与财富决定想要的密度**——1.1.5f1 起"住宅密度取决于家庭财富与家庭人数"；富裕家庭偏爱大房子（低/中密度），单身与学生接受小户型（中/高密度）；
4. 失业率上升 → 需求下降；空置房过多 → 需求下降直到被消化。

搬入家庭的**类型**由：平均市民幸福度、无家可归人数、住宅税率、可用学位、可用岗位共同决定（1.1.5f1）。
（来源：https://cs2.paradoxwikis.com/Zoning ；https://cs2.paradoxwikis.com/Patch_1.1.X ；https://colossalorder.fi/news/economy-2-development-diary-1/ ）

**商业需求**：① 工业产出的商品需要有地方卖；② 本地顾客的购买力；③ 公司能否招到合适员工。**1.5.7f1 起商业需求改为基于"全城商铺的平均备货水平"**（修复了"少数商铺没顾客就把整体需求拖死"的 bug）。
（来源：https://cs2.paradoxwikis.com/Zoning ；https://cs2.paradoxwikis.com/Patch_1.5.X ）

**工业需求**：① 市民需要制造业岗位；② 本地商业需要货源；③ 本地资源开采（专业化工区）会额外提升需求；④ 有仓库可缓冲产销。建筑等级越高，越需要**高学历**员工。
（来源：https://cs2.paradoxwikis.com/Zoning ）

**办公需求**：① 市民想从事办公行业；② 市民与公司对无形商品（Software/Telecom/Financial/Media）的需求；③ 制造业依赖办公区产出的 Software。1.5.6f1 起官方开始"office demand rework"，第一步是**提高办公需求**；1.5.7f1 修正了办公需求取数错误（此前 Software 公司生成过多）。
（来源：https://cs2.paradoxwikis.com/Zoning ；https://cs2.paradoxwikis.com/Patch_1.5.X ）

### 2.2 需求的可操作杠杆
| 杠杆 | 效果 | 来源 |
|---|---|---|
| 调税率 | 1.1.5f1 起税率对需求影响显著增强；住宅税按**学历分级**、商业/工业/办公税按**产品类型**分级 | https://cs2.paradoxwikis.com/Patch_1.1.X ；https://cs2.paradoxwikis.com/Economy |
| 补教育容量 | "可用学位"直接进入搬入家庭类型判定 | https://cs2.paradoxwikis.com/Patch_1.1.X |
| 补岗位 | "可用岗位"直接进入搬入家庭类型判定 | 同上 |
| 降无家可归 | 无家可归人数进入搬入家庭类型判定 | 同上 |
| 分区满足需求 | 地价过高时可"多划该类型分区"以平抑地价 | https://cs2.paradoxwikis.com/Zoning |

### 2.3 需求常见误判
- **空置建筑确实会压低需求，但 1.1.10f1 之前"空置建筑在地图上不可见"**，导致玩家看不到真正原因；1.1.10f1 已让 RCIO 信息视图显示空置建筑。（来源：https://cs2.paradoxwikis.com/Patch_1.1.X ）
- 1.3.6f1 前，"降低工业税率会导致工业需求无休止上升"是 bug，已修。（来源：https://cs2.paradoxwikis.com/Patch_1.3.X ）
- 1.6.2f1 起，**住宅需求在计算空置住宅影响时会考虑城市规模**，修复了"超大城市的住宅需求长期为 0"。（来源：https://cs2.paradoxwikis.com/Patch_1.6.X ）

---

## 3. 人口与生命周期

### 3.1 四个年龄段 + 各自的寻路偏好（关键！）
| 年龄 | 能否工作 | 能否升学 | 出行偏好（对寻路成本的主导因子） |
|---|---|---|---|
| Children 儿童 | 否 | 只上小学（有学位就一定会去） | — |
| Teens 青少年 | 是，但多数会继续读书 | 高中（1.1.5f1 起"高概率"去） | **Money（最便宜路线）** |
| Adults 成人 | 是 | 大学/学院 | **Time（最快路线）** |
| Seniors 长者 | 否 | 不能再提升学历 | **Comfort（最舒适路线）** |

（来源：https://cs2.paradoxwikis.com/Citizens ；1.1.5f1 教育改动见 https://cs2.paradoxwikis.com/Patch_1.1.X ）

> 这条表是**公交规划的核心依据**：票价（Money）主要影响青少年与低收入群体；速度（Time）主要影响成人通勤；舒适度（Comfort，含车站舒适等级与换乘体验）主要影响长者。

### 3.2 家庭与搬家
- 家庭找房时综合评估：到各目的地的寻路成本、扣除工作与通勤后的**剩余自由时间**、扣完开支后的**剩余金钱**、以及**与其当前需求匹配的服务**。以此最大化 Happiness。（来源：https://www.paradoxinteractive.com/games/cities-skylines-ii/features/economy-production ）
- 1.1.5f1：**没有成人的家庭会搬走**；富裕家庭偏好高品质社区的大房子，贫困家庭偏好便宜房子且不在乎服务远。（来源：https://cs2.paradoxwikis.com/Patch_1.1.X ）
- 1.1.5f1：失业救济**有领取时限**，领完后市民会抱怨 "High Rent" 并搬离。**失业 → 救济到期 → 搬离**是人口流失的主要链条。（同上）
- 1.2.5f1：市民转为成人后**更不容易立刻变无家可归**，会先在家里住更久，直到攒到启动资金、有工作、且城里有合适住房；若没有合适住房，他们**可以搬出城成为城外通勤者**。（来源：https://cs2.paradoxwikis.com/Patch_1.2.X ）
- 1.6.2f1：青少年成年后延迟搬出，直到**找得到负担得起的房子**；同时修复"用其他方式回家时把车丢在公交站"的问题。（来源：https://cs2.paradoxwikis.com/Patch_1.6.X ）

### 3.3 无家可归（Homelessness）
- 付不起房租、又没有钱搬走或搬出城的市民会成为无家可归者，**住在城市公园里**（1.2.5f1 起地标建筑不再成为营地）。（来源：https://cs2.paradoxwikis.com/Citizens ；https://cs2.paradoxwikis.com/Patch_1.2.X ）
- 1.1.8f1 起无家可归人口计入总人口，并有了独立的搬出逻辑；1.2.5f1 起人口信息视图新增无家可归图层与统计。（来源：https://cs2.paradoxwikis.com/Patch_1.1.X 、https://cs2.paradoxwikis.com/Patch_1.2.X ）

### 3.4 死亡与"死亡潮"
- **1.2.3f1** 重做了死亡概率曲线，并把市民年龄上限限制为 **120 游戏日**；已有长者被"变年轻"。官方明确提示：老城市会经历一次死亡潮，随后稳定。（来源：https://cs2.paradoxwikis.com/Patch_1.2.X ）
- 1.5.4f1 起死亡判定**按一天内 16 次/人**计算（原为 4 次），并纳入时刻因素（此前大部分死亡集中在 0–6 点）。（来源：https://cs2.paradoxwikis.com/Patch_1.5.X ）

---

## 4. 教育、学历与岗位匹配（重点）

### 4.1 五级学历与获取路径
| 等级 | 英文 | 由哪所学校产出 | 招生对象 | 默认学费（月/人） |
|---|---|---|---|---|
| 0 | Uneducated 未受教育 | —（初始状态） | — | — |
| 1 | Poorly Educated 受教育不足 | Elementary School 小学 | 仅 Children | ₡50 |
| 2 | Educated 受教育 | High School 高中 | 仅 Teens | ₡100 |
| 3 | Well Educated 受过良好教育 | College 学院 | Teens + Adults | ₡200 |
| 4 | Highly Educated 高度受教育 | University 大学 | 仅 Adults | ₡200 |

（来源：https://cs2.paradoxwikis.com/Citizens ；学费默认值 https://cs2.paradoxwikis.com/Economy ）
- 学院/大学在**城内没有**时，市民可以**出城上学**——但这会显著提高他们**永久搬离**的概率。官方建议：务必提供本地高等教育。（来源：https://cs2.paradoxwikis.com/Services ）
- 市民在"上学 vs 工作"之间做**经济比较**（现在工作的收入 vs 毕业后更高岗位的收入），且部分市民有**天生偏好**即使长期不划算也去工作。（来源：https://cs2.paradoxwikis.com/Citizens ）
- 1.1.5f1：上学与毕业概率均提高；**成人可申请回高中（1% 概率，最多申请 3 次）**；1.5.7f1 进一步平衡小学/高中需求。（来源：https://cs2.paradoxwikis.com/Patch_1.1.X 、https://cs2.paradoxwikis.com/Patch_1.5.X ）

### 4.2 工资（1.3.3f1 实测值，重要基准）
| 学历（层级名） | 月薪 |
|---|---|
| Highly Educated（Manager） | ₡2700 |
| Well Educated（Specialist） | ₡2400 |
| Educated（Senior） | ₡2100 |
| Poorly Educated（Basic） | ₡1800 |
| Uneducated（Simple） | ₡1500 |

- **住宅所得税起征点 `Residential Minimum Earnings` = ₡1400/月**。
- 不工作者的收入来源：儿童 `Family Allowance` ₡400/月（计入家庭）、长者 `Pension` ₡1200/月、其他失业者 `Unemployment Benefit` ₡800/月，**最长 `Unemployment Allowance Max Days` = 10 天**。
- 城外通勤者（住城外、城内工作）有 `Commuter Wage Multiplier` = **1.1**，但**完全不向本城缴税**；城内公共服务岗位员工要缴税。
（来源：https://cs2.paradoxwikis.com/Citizens ，页面明确标注数据版本 1.3.3f1）

### 4.3 学历过剩（overeducated）——官方机制的真实说法
- 员工可以做**任何 ≤ 自己学历**的工作；但**如果高学历者做了低层级岗位，其对公司效率的贡献按"岗位层级"计算，而不是按他本人的学历**——即"才能无法完全发挥"。
- **工资只由市民本人学历决定**，与岗位层级无关，也**不存在"某类专才稀缺就涨薪"**的机制。
- 如果公司**招不到足够高学历的人**，就填不满岗位 → 效率与产出下降。
（来源：https://cs2.paradoxwikis.com/Citizens ）

> 给玩家的直接结论：**学历过剩 ≠ 惩罚性 debuff，而是"高学历者的效率被浪费"**。真正的代价是：你交了教育费、养了高学历人口，但他们在低阶岗位上只贡献低阶效率。对策是**同步提升公司建筑等级/产品复杂度**（等级越高，需要的学历越高），而不是"别办大学"。

### 4.4 学历与公司等级的耦合
- 分区建筑升级时，**岗位的复杂度与构成会变**；等级越高，高学历岗位占比越高。**工业企业不论等级都倾向低学历要求**，商业与办公随等级上移更偏向高学历。（来源：https://cs2.paradoxwikis.com/Citizens ）
- 1.1.5f1 把工业制造用地的 `space multiplier` 从 1 提到 **5**（同一地块容纳更多工人，所需建筑更少）；办公员工数也被调整。（来源：https://cs2.paradoxwikis.com/Patch_1.1.X ）

### 4.5 通勤范围与"通勤过长 → 搬离"
- **1.6.0f1 是关键补丁**：官方原文——"Pathfinding limits are now tailored per trip type: **work, school, shopping, and leisure each use a sensible range** rather than a shared near-unlimited cap."，即**寻路距离上限按出行目的分别设定**；无法找到可行路线的市民会优雅降级：搬离者直接传送出图、工人辞职、休闲需求者在家闲置后重试。（来源：https://cs2.paradoxwikis.com/Patch_1.6.X ）
- **官方没有公布这些上限的具体数值** → **待验证**。
- 搬离的触发条件可确证的有：租金付不起（1.1.5f1 的租金公式）、失业救济到期、幸福度过低（1.1.5f1："Low happiness affects the chance a household will move out of the city"）。（来源：https://cs2.paradoxwikis.com/Patch_1.1.X ）

---

## 5. 幸福度 / Well-being / 健康（Happiness）

### 5.1 幸福度因子（官方表，逐条）
| 因子 | 类型 | 正面 | 负面 |
|---|---|---|---|
| 教育服务 | 质量 | 就近、易达、有余额 | 交通导致难达、满员 |
| 休闲时间 | 充裕度 | 就近快速到达公园/地标 | 公园少、拥挤、太远 |
| 娱乐 | 充裕度 | 易达商业（尤其酒吧/夜店） | 交通不便、缺少交通选择 |
| 医疗覆盖 | 可靠性 | 医疗建筑近或响应快 | 太远、过载、到达太慢 |
| 邮政 | 可靠性 | 附近邮局/邮箱、分拣快 | 无邮局/邮箱；分拣需求超容量 |
| 互联网 | 可靠性 | 网络容量高、覆盖好 | 容量或覆盖不足 |
| 噪音污染 | 量 | 低 | 高（住宅区尤其不可接受） |
| 市民财富 | 量 | 收入/净资产高 | 低 |
| 住房面积 | 量 | 大（低密度） | 小（高密度） |
| 税率 | 量 | 低 | 高 |

（来源：https://cs2.paradoxwikis.com/Citizens ）

### 5.2 Well-being（精神状态与安全感）与 Health（健康）
- **Well-being** 取决于：可靠供电/清洁水/足够污水处理、垃圾清运、避开空气/地面/噪音污染、良好的服务覆盖（被动加成）、低犯罪概率；以及**邮政、高速互联网、合适的住房面积、能买到商品**。Well-being 低 → 幸福度下降 + 工作效率下降 + **有成为罪犯的风险**。（来源：https://cs2.paradoxwikis.com/Citizens ）
- **Health** 受：医疗可达性（就近被动加成 + 实际治疗）、空气/地面污染、污水倒灌、垃圾堆积影响。1.3.6f1 起**患病会直接削减目标市民 50% 健康值**。（来源：https://cs2.paradoxwikis.com/Citizens ；https://cs2.paradoxwikis.com/Patch_1.3.X ）
- 1.6.2f1 起**垃圾对市民幸福度的影响被加大**。（来源：https://cs2.paradoxwikis.com/Patch_1.6.X ）

### 5.3 休闲（Leisure）
- 获得渠道：城市休闲（公园/广场/球场的 Indoor/Outdoor Recreation）、商业休闲（购物）、娱乐（酒吧/餐厅，需同时消费商品）、以及**出城度假**。（来源：https://cs2.paradoxwikis.com/Citizens ）
- **天气会改变选择**：晴天温暖 → 户外；雨雪寒冷 → 室内购物与娱乐。（同上）
- 公园的价值用三个字段表达：**Attractiveness（吸引力）/ Comfort（舒适）/ maintenancePool（维护池）** + Leisure 加成（如 +1~+20 Outdoor Recreation）。（来源：https://cs2.paradoxwikis.com/Service_buildings ）

---

## 6. 地价（Land Value）

### 6.1 地价从哪来（1.1.0f1 后的官方清单）
1.1.0f1 重做地价系统，明确加入以下来源（来源：https://cs2.paradoxwikis.com/Patch_1.1.X ）：
- **Healthcare、Education、Police、Telecom 的服务覆盖**影响地价；
- **商业服务的可达性**影响地价；
- **公共交通的站点与车站**影响地价（→ **TOD 在 CSL2 里有机制支撑**）；
- **噪音、水、空气、地面污染**影响地价（负向）；
- **岸线（Shorelines）**影响地价；
- 地价加成系数有**上限**。

### 6.2 地价的闭环
市民看重：大房子、靠近商店、所需服务、学校与工作地、无污染。需求被满足 → 愿意付更高租金 → 地价上升。**单纯"把服务建筑堆进社区"不会自动抬地价**，只有居民与公司的需求真的被满足时才会。（来源：https://cs2.paradoxwikis.com/Zoning ）

租金与升级（1.1.5f1 起）：
```
Rent = (LandValue + (ZoneType × BuildingLevel)) × LotSize × SpaceMultiplier
```
- 虚拟房东被移除，**建筑维护费由所有租户平摊**。
- **建筑等级 = 租户能否付得起维护费**：付满 → 建筑状况按固定步长上升（升级）；付不起 → 同幅下降（最终废弃）。
（来源：https://cs2.paradoxwikis.com/Patch_1.1.X ）

### 6.3 密度对地价影响的差异（重要规划结论）
- **低密度住宅最容易"变贵"**：地价上升 → 租金上升，而低密度只有一户承担 → 低收入家庭被迫迁往中密度。
- **中/高密度受影响小**，因为成本在几十户之间分摊。
（来源：https://cs2.paradoxwikis.com/Zoning ）

### 6.4 控制地价的手段
- 调整住宅税率（鼓励或劝退迁入）；多划高需求类型的分区（用供给平抑）；**主动少建服务与休闲设施**（市民能容忍一定欠缺）。（来源：https://cs2.paradoxwikis.com/Zoning ）

### 6.5 建筑升级的额外前置（1.4.2f1 起）
- 建筑升级需要**资源配送**才能推进，配送由**工业公司、资源仓库、外部连接**承担；配送车会尽量多点投送以降低车流。信息视图新增"等待资源的建筑"图标。（来源：https://cs2.paradoxwikis.com/Patch_1.4.X ）
- 1.5.7f1 修复"资源配送在某些帧被跳过后建筑等级卡住不动"。（来源：https://cs2.paradoxwikis.com/Patch_1.5.X ）
- 1.5.7f1 新增 **Historic Building** 选项：可锁定某建筑不再升级、也不会废弃。（同上）

---

## 7. 经济与财政

### 7.1 税率
- 四类分区各自一个总税率滑块，可下钻：**住宅按学历分级，商业/工业/办公按产品类型分级**。
- **区间固定为 −10% ~ +30%**。负税率 = 补贴该产业。
- 低税率加快建筑升级；高税率收入更多。**1.1.5f1 起税率对需求影响显著增强**。
- 税收在里程碑 2 解锁（1.1.5f1 起在里程碑 1 解锁，生产面板在里程碑 2）。
（来源：https://cs2.paradoxwikis.com/Economy ；https://cs2.paradoxwikis.com/Patch_1.1.X ；https://www.paradoxinteractive.com/games/cities-skylines-ii/features/economy-production ）

> **官方从未公布"税率甜蜜点"数值。** 任何声称"10% 是最优"的说法都是社区经验，**待验证**。

### 7.2 服务预算
- 区间 **50% ~ 150%**；**50% → 25% 效率，150% → 125% 效率**（来源：https://cs2.paradoxwikis.com/Services ，单一来源，**待验证**）。
- 预算影响服务建筑的**容量**（垃圾车数、警车数、学位数…）以及**覆盖范围**等不易察觉的效果。（同上）
- 里程碑 3 解锁服务预算。（同上）

### 7.3 服务费（默认值）
| 服务 | 默认费率 |
|---|---|
| 电力 | 0.2 |
| 自来水 | 0.3 |
| 医疗 | ₡100 / 月 / 住院市民 |
| 垃圾 | 1.0 |
| 教育 | 小学 ₡50、高中 ₡100、学院/大学 ₡200 / 月 / 人 |
| 道路 | 停车费，0 ~ ₡50 |
| 交通 | 票价（按线路单独设置） |

（来源：https://cs2.paradoxwikis.com/Economy ；https://cs2.paradoxwikis.com/Services ）
水电费的传导（精确公式）：**每低于 100% 一个百分点** → 用电 +0.2%、公司效率 +0.2%、市民幸福度 +0.05；**每高于 100% 一个百分点** → 用电 −0.4%、公司效率 −0.4%、幸福度 −0.1。（来源：https://cs2.paradoxwikis.com/Services ）

### 7.4 服务进出口（贸易）
| 服务 | 进口价 | 出口价 |
|---|---|---|
| 电力 | ₡5000/MW | ₡2500/MW |
| 水 | ≈₡0.1/m³ | ≈₡0.05/m³ |
| 污水 | 不可进口 | ≈₡0.1/m³ |
| 警察 | ₡50/市民 | — |
| 医疗 | ₡25/市民 | — |
| 殡葬 | ₡25/市民 | — |
| 消防 | ₡50/市民 | — |
| 垃圾 | ₡5/市民 | — |

（来源：https://cs2.paradoxwikis.com/Economy ）
- **1.1.5f1 起**导入服务要收费且**费用随城市人口缩放**，并新增城市政策 **Import City Services** 作为开关（默认关闭）。（来源：https://cs2.paradoxwikis.com/Patch_1.1.X ；https://colossalorder.fi/news/economy-2-development-diary-1/ ）
- 电力进口价格在 1.1.5f1 被上调。（来源：https://cs2.paradoxwikis.com/Patch_1.1.X ）

### 7.5 贷款
- 单一可调贷款；额度上限随里程碑从 **₡100,000 到 ₡26,100,000**；利率随额度上升（月供占**贷款额的 2.3%–20%**量级）。
- **City Hall** 减息 1%（**1.3.6f1 起改为 −5% 城市服务基础维护费 + −15% 城市服务进口成本**）；**Central Bank** 减息 2%（**1.3.6f1 起改为 −50% 贷款利息 + +1 幸福度税率容忍度**）。
（来源：https://cs2.paradoxwikis.com/Economy ；1.3.6f1 数值来自 https://cs2.paradoxwikis.com/Patch_1.3.X ）
> ⚠️ 上表两套数值冲突的原因是 **1.3.6f1 重做了这两个建筑的加成**。以 1.3.6f1 后为准。

### 7.6 公司效率（Efficiency）因子
正向：员工平均幸福度；城市生产专业化（**1.3.6f1 起上限由 115% 降至 +10%**，且需要生产更多资源才能拿到）；签名建筑的商业/工业效率；降低水电费；邮件处理效率。
负向：员工不足；员工平均幸福度低；水电费上涨。
（来源：https://cs2.paradoxwikis.com/Economy ；上限改动 https://cs2.paradoxwikis.com/Patch_1.3.X ）

### 7.7 产业链（Materials → Material Goods → Immaterial Goods）
- **原材料（9 类）**：Wood、Grain、Livestock、Vegetables、Cotton、Crude Oil、Metal Ore、Coal、Rock。1.3.6f1 新增 Fish。
- **材料品**：Metals、Steel、Minerals、Concrete、Machinery、Petrochemicals、Chemicals、Plastics、Pharmaceuticals、Electronics、Vehicles、Beverages、Convenience Food、Food、Textiles、Timber、Paper、Furniture。
- **无形商品**：Software → Telecom / Financial / Media（办公区产出）；Lodging / Meals / Entertainment / Recreation（商业区产出）。
- 资源有 **price / weight / space** 三因子：**重的（Stone/Steel）运输成本高**，应本地生产；**占地大的产业偏好低地价区**。
（来源：https://cs2.paradoxwikis.com/Economy ；https://www.paradoxinteractive.com/games/cities-skylines-ii/features/economy-production ）
- **1.1.5f1 起资源价格分两段**：工业加工价（折价）+ 商业售价，两者相加才是消费者付的全价。（来源：https://cs2.paradoxwikis.com/Patch_1.1.X ）
- 1.3.6f1：仓库车辆数 **3 → 10**；工业升级所需资源开始"提前配送"，导致**短期内货车流量显著上升**（官方明确提示）。（来源：https://cs2.paradoxwikis.com/Patch_1.3.X ）

### 7.8 货运外部连接
- 货运火车/货船/货机都能大幅降低重货的运输成本；**货船 1000 吨**、**货运火车站/货运码头储位 15.5 kt**（1.3.6f1 起码头/火车站的仓库升级储位下调为 **7500 t** 以匹配视觉）。（来源：https://cs2.paradoxwikis.com/Transportation ；https://cs2.paradoxwikis.com/Patch_1.3.X ）
- 货运终端无论是否开设货运线路，都可作为**配送中心**使用（公司可存取货）。（来源：https://cs2.paradoxwikis.com/Transportation ）
- 1.5.7f1：修复 B&P 港口未被本地商业/工业用于进口的问题。（来源：https://cs2.paradoxwikis.com/Patch_1.5.X ）

### 7.9 水电与污染
- 道路（除高速外）自带 **40 MW 低压输电**与**水管/污水管**；桥梁不含管线；高速需加装 Lighting 升级才有输电能力。（来源：https://cs2.paradoxwikis.com/Roads ）
- 五类污染：**地面 / 空气 / 水 / 地下水 / 噪音**。地面污染会杀死树木、破坏肥沃土地、污染地下水；空气污染随风扩散、下雨减轻；噪音降低住宅 Well-being；**地下道路的噪音被完全抑制，高架道路的噪音被放大**；**树木只有很弱的对数级降噪**，高速公路需隔音墙。（来源：https://cs2.paradoxwikis.com/Pollution ）
- **1.1.10f1 起空气污染整体增加、扩散略增、消散更慢**，并重平衡了道路噪音（非高速道路基本持平，高速略增）。（来源：https://cs2.paradoxwikis.com/Patch_1.1.X ）
- **1.3.6f1 起分区工业与专业化工区的噪音量与扩散半径双双上调**，且**住宅适宜度开始考虑空气与噪音污染**，市民对噪音的惩罚也略微加大。（来源：https://cs2.paradoxwikis.com/Patch_1.3.X ）

---

## 8. 地图、里程碑与解锁

### 8.1 地图
- 每张地图 **441 格**，每格 **0.4 km²** → 全图 ≈ **176.4 km²**；新城市**初始已购 9 格**，其余需扩张许可 + 金钱购买。
- 购地成本估算（1.0.12f1 源码考证，**待验证**）：每多解锁一格约 +₡125；建筑用地约 **₡1,184 / 万 m²**（0.1184 ₡/m²）；资源附加：木材/矿石 ₡18.6/吨、石油 ₡55.6/kg、地下水 ₡53.9/m³、肥沃土地 ₡16.9/m²。
- **1.1.5f1 起购地成本上升，并新增"地块维护费"**（初始 9 格免维护费），同时提供"解锁全部地块"选项（会禁用成就、取消地块维护费）。
（来源：https://cs2.paradoxwikis.com/Progression ；https://cs2.paradoxwikis.com/Patch_1.1.X ）

### 8.2 里程碑
共 **20 级**（Tiny Village → Megalopolis），每级给金钱、发展点、扩张许可，提升贷款上限，解锁分区/政策/服务/功能。
- **1.1.5f1 把里程碑奖金大幅削减**：第 1 级从 **₡600,000 → ₡25,000**，第 20 级从 **₡7,000,000 → ₡500,000**。（来源：https://cs2.paradoxwikis.com/Progression ）
- 关键解锁节点（1.1.5f1 口径）：税收/预算/统计 = Tiny Village；教育 = Small Village；消防/警察 = Large Village；交通 + 公园 + 政策 + 区域工具 + 交通总览 + 自然灾害 = Grand Village；通信 = Tiny Town；重车禁行/高级污染管理 = Boom Town；高密度住宅 = Big Town；高密度商业 = Great Town；高密度办公 + 高速政策 + 燃烧引擎禁行 + 城市推广 = Small City。
（来源：https://cs2.paradoxwikis.com/Progression ）

### 8.3 发展树
- 4 个层级，节点费用 **Tier1=1 点、Tier2=2 点、Tier3=4 点、Tier4=8 点**；服务的 Tier1 基础节点在解锁该服务时自动获得。
- 分支间**不必全买**即可推进（例：不点水运/电车/地铁也能直接点到国际机场）。（来源：https://cs2.paradoxwikis.com/Progression ）

### 8.4 难度模式
- **1.2.5f1** 引入 Easy / Normal 两种模式。1.3.3f1 调整了 Easy 模式的电力/水/垃圾消耗与失业救济、养老金、家庭津贴；**Easy 模式下自然资源枯竭更慢**（1.5.9f1）；**Easy 模式原本约 80% 市民不会老死，1.5.4f1 修正**。
（来源：https://cs2.paradoxwikis.com/Patch_1.2.X 、https://cs2.paradoxwikis.com/Patch_1.3.X 、https://cs2.paradoxwikis.com/Patch_1.5.X ）

### 8.5 气候与季节
- 影响通勤与休闲选择（晴暖→户外，雨雪冷→室内），影响交通事故概率（天气 + 光照 + 路况），影响空气污染（下雨减轻）。
- 1.2.5f1 大幅调整气候表现，并把多张地图的云量与降雨**下调约 20%**；闪电概率平衡为 **5%**、需雨量阈值 **0.3**。
- **自建地图可自定义气候**（1.1.10f1 支持自定义气候；1.1.12f1 修复自定义气候在分享地图中丢失）。
（来源：https://cs2.paradoxwikis.com/Citizens ；https://cs2.paradoxwikis.com/Traffic ；https://cs2.paradoxwikis.com/Patch_1.2.X 、https://cs2.paradoxwikis.com/Patch_1.1.X ）

---

## 9. 信息视图（Infoviews）——共 33 个

玩家最常用的（按用途分类）：

**交通类**
- **Traffic**：面板给"一天内交通流量图 + 流量百分比"；地图可切"交通流量"或"交通量"。（来源：https://cs2.paradoxwikis.com/Info_views ）
- **Roads**：显示**停车设施可用度（已停 vs 容量）**与**停车收入（₡/月）**；道路按状况绿→红着色；高亮停车场/停车楼、道路维护站与维护车。（同上）
- **Transportation**：各方式的线路数、游客数、月客运量；货运线路数与吨位；地图上高亮全部线路与车辆。（同上）

**服务覆盖类**：Healthcare & Deathcare（含救护车/灵车、道路覆盖着色、平均健康）、Garbage（建筑垃圾堆积着色）、Fire & Rescue（火灾风险 + 消防覆盖 + 火警瞭望塔半径）、Police（犯罪概率 + 警力覆盖 + 监狱容量）、Administration（福利覆盖 + Well-being）、Education（四类学位总容量 + 各学历人口占比 + 道路覆盖）、Post（邮件堆积 + 覆盖）、Telecom（网络质量 + 覆盖）。

**分区与发展类**：Residential / Commercial / Industrial / Office 各自的 **Suitability（适宜度）**；**Building Level**（各分区各等级建筑占比）；**Land Value**（1.1.0f1 起同时给出 "Land Value Source" 模式与光标处的具体地价金额）；**Company Profitability**；**Natural Resources**（含肥沃土地/森林的再生率）。

**人口类**：**Population**（年龄结构 + 人口密度）、**Happiness**（幸福度因子）、**Citizen Wealth**、**Workplace Availability**（按学历的岗位数）。

**污染类**：Air / Ground / Noise / Water Pollution（均带地形热力图，空气污染视图还带风向箭头）。

（来源：https://cs2.paradoxwikis.com/Info_views ）
> 实用提醒：**Happiness 视图的道路着色实际显示的是医疗覆盖**（官方页面如此描述），这是个容易误读的点。

---

## 10. Mod 与数据导出

- **官方 Mod 平台**：Paradox Mods（游戏内集成）。**1.1.0f1** 起支持代码 Mod 与编辑器（地图制作）。**1.5.2f1（Asset Mods Patch，2025-12-04）** 起支持**创建并分享资产**。1.5.7f1 起有**统一 Mod 按钮**与播放集分享（Playset Sharing）。（来源：https://cs2.paradoxwikis.com/Patch_1.1.X 、https://cs2.paradoxwikis.com/Patch_1.5.X ）
- **断网/离线**：1.5.7f1 起订阅、退订、管理播放集无需等待下载完成；支持排除标签、自动下载开关。（同上）
- **游戏内自带的"数据导出"能力极弱**——官方没有内置 GIS 导出。玩家常用的外部方案是 **Carto**（把城市导出为 GeoTIFF + Shapefile：Area_Boundary / Building_Boundary / Network_Boundary / Network_Centerline / POI_Location / Route_Centerline / Zoning_Boundary，并附带 QGIS 样式 .qml）。**Carto 的版本适配与官方支持状态本次未能找到权威页面 → 待验证**。（说明：本判断基于工作目录 `C:\Users\Devcl\Desktop\CSL2\Carto\` 中实际存在的导出文件结构与 `styles/Plan`、`styles/Street` 两套 QML 样式；未找到可引用的官方或社区文档 URL，因此**不作为已核实来源**）
- **信息视图 + 官方统计面板（City Statistics，里程碑 1 解锁）是游戏内唯一的"原生数据"来源**；1.3.6f1 起生产面板给出了更完整的产业链信息。（来源：https://cs2.paradoxwikis.com/Progression 、https://cs2.paradoxwikis.com/Patch_1.3.X ）

---

## 11. 城市规划范式（机制允许什么）

以下四类是**现实规划范式在 CSL2 机制下的可行映射**，其中标注了游戏机制支撑点：

1. **路网层级（高速—主干—次干—支路）**：CSL2 的道路表按 Small / Medium / Large / Highway 分级，限速与车道数递增，且**大型道路会降低周边地价并增加噪音**——这为"主干道不贴住宅"提供了机制依据。（来源：https://cs2.paradoxwikis.com/Roads ）
2. **TOD（站点周边开发）**：1.1.0f1 起**公交站点与车站直接影响地价**，这是 CSL2 中 TOD 的机制支撑。（来源：https://cs2.paradoxwikis.com/Patch_1.1.X ）
3. **单向微循环**：游戏提供 1/2/3 车道单向路、单行巷道；但官方提示**服务车辆不能逆行**，单向路可能导致消防/送货绕远。（来源：https://cs2.paradoxwikis.com/Roads ）
4. **树形/环路**：游戏没有直接对应工具，靠"高速不入城 + 主干道成环 + 支路断头"实现；注意 1.6.0f1 的**按目的设定寻路距离上限**会惩罚过长的支路绕行。（来源：https://cs2.paradoxwikis.com/Patch_1.6.X ）
