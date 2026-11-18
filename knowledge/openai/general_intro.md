# OpenAI 公司深度分析报告

> 最后更新: 2026-11-18
> **数据时效说明**：以下数据综合截至最新公开披露。由于OpenAI尚未上市，财务与运营数据可能存在估算偏差，**使用前请务必交叉验证**。文中已标注可信度分级。

## 一、公司概况

OpenAI是一家总部位于美国加利福尼亚州旧金山的人工智能研究与部署公司。公司最初于2015年12月11日作为非营利组织成立，2019年转型为"有限利润"（capped-profit）结构，目前正在向完全营利性公司转制。

**成立时间**：2015年12月11日  
**总部**：美国加利福尼亚州旧金山  
**性质**：从非营利组织转型为"有限利润"实体，正在向完全营利性公司转制  
**现任CEO**：萨姆·奥尔特曼（Sam Altman）

## 二、创始团队与核心人物

### 2.1 联合创始人（2015 年创立时的 11 人官方名单）

OpenAI 于 2015 年 12 月 11 日创立时共有 **11 位联合创始人**（名单据 OpenAI 官方创始文与 Business Insider 2024-10 创始人盘点交叉核对）。此前版本将早期投资人 Peter Thiel、后期高管 Mira Murati 混入创始团队表，且"仅剩 2 人"的表述与表中 Brockman、Zaremba 在司记载自相矛盾，本节按权威名单重整：

| 联合创始人 | 创始时角色 | 现状 |
|------|---------|------|
| **萨姆·奥尔特曼（Sam Altman）** | 联合主席（co-chair） | 仍在公司，现任 CEO[reference:0][reference:1] |
| **埃隆·马斯克（Elon Musk）** | 联合主席、早期主要出资人 | 2018 年退出董事会，后创办 xAI，现为竞争对手[来源: Wikipedia] |
| **格雷格·布罗克曼（Greg Brockman）** | CTO，后转任总裁 | 仍在公司（2024–2025 年初曾长期休假，回归后持续在任；2026-07 起 Fidji Simo 卸任应用负责人后统管产品线）[reference:2][reference:7] |
| **伊利亚·苏茨克弗（Ilya Sutskever）** | 研究负责人、前首席科学家 | 已离职，创办 Safe Superintelligence Inc.[reference:0][reference:1] |
| **沃伊切赫·扎伦巴（Wojciech Zaremba）** | 创始研究员（机器人方向起步，后长期领导 Codex 等核心团队） | 仍在核心技术团队[reference:4] |
| **约翰·舒尔曼（John Schulman）** | 创始研究员（RLHF 核心贡献者） | 已离职（2024-08 加入 Anthropic，2025-02 再度离开 Anthropic）[来源: Business Insider 2025-02-06] |
| **安德烈·卡帕西（Andrej Karpathy）** | 创始研究员 | 已离职（2017 年赴 Tesla，2023–2024 年一度回归，后创办 Eureka Labs）[来源: BI 2024-10 盘点] |
| **德克·金马（Durk Kingma）** | 创始研究员 | 已离职（后任职 DeepMind，2024 年宣布加入 Anthropic）[来源: BI 2024-10 盘点] |
| **Trevor Blackwell** | 创始研究员 | 已离职[来源: BI 2024-10 盘点] |
| **Vicki Cheung** | 创始工程师 | 已离职（2017 年前后离开）[来源: BI 2024-10 盘点] |
| **Pamela Vagata** | 创始工程师 | 已离职（早期离开）[来源: BI 2024-10 盘点] |

> 📌 **在司人数口径统一**：原文"11 位联合创始人仅剩 2 人"是 2024–2025 年媒体报道口径，指彼时常驻的 **Altman 与 Zaremba** 两人[reference:0][reference:1]；Brockman 休假回归后持续在任[reference:7]，因此**当前口径为 3 人在司（Altman、Brockman、Zaremba）**，第九章"创始团队流失"条目已同步修正。

### 2.2 早期投资人 / 资助人（非联合创始人）

创始期约 10 亿美元捐资承诺的主要出资人如下，**均不属于 11 位联合创始人名单**（此前版本曾将 Peter Thiel 误标为"早期投资人/联合创始人"，特此更正）[来源: OpenAI 官方创始文 2015-12-11 Funders 名单]：

| 资助人 | 身份 | 说明 |
|------|------|------|
| **彼得·蒂尔（Peter Thiel）** | 早期资助人 | 经 Founders Fund 参与创始期捐资，未担任联合创始人或高管 |
| **里德·霍夫曼（Reid Hoffman）** | 早期资助人 | LinkedIn 创始人 |
| **杰西卡·利文斯顿（Jessica Livingston）** | 早期资助人 | Y Combinator 联合创始人 |
| **达斯汀·莫斯科维茨（Dustin Moskovitz）** | 早期资助人 | Facebook 联合创始人 |
| **Infosys / Amazon Web Services / YC Research** | 机构资助人 | 创始期机构捐资方 |

> 另注：**Mira Murati 为 2018 年自 Tesla 加入的后期高管**（历任 VP 应用 AI 与 CTO），并非联合创始人，其去向见下方"近期高管变动"。

### 2.3 当前核心领导层

- **CEO**：萨姆·奥尔特曼（Sam Altman），1985年4月22日出生于芝加哥，曾领导Y Combinator（2014-2019年），以激进的AGI愿景和极强的融资能力著称[reference:5][reference:6]
- **总裁**：格雷格·布罗克曼（Greg Brockman），联合创始人，持续在任（2024–2025 年初长期休假后回归，详见 2.1 节口径说明）[reference:7]
- **CFO**：萨拉·弗莱尔（Sarah Friar），2024 年 6 月加入，负责财务战略与 IPO 筹备[reference:8]
- **首席科学家**：雅库布·帕乔基（Jakub Pachocki），Ilya 离职后接任[reference:9]
- **首席研究官**：马克·陈（Mark Chen），2025 年 3 月进入扩展后的 Chief Research Officer 角色[reference:10]

**近期高管变动**：2025年经历了大规模高管流失，包括前CTO Mira Murati（2025年离职，创办Thinking Machines Lab[reference:3]）、首席科学家Ilya Sutskever等核心人物[reference:11]。2026年1月，Murati创办的Thinking Machines Lab的几位联创回流至OpenAI[reference:12]。

## 三、愿景与使命

### 3.1 使命演变

OpenAI的使命宣言在9年间（2015-2025）历经6次修改[reference:13][reference:14]：

- **2015年创初**：构建安全、普惠、非营利性的通用人工智能
- **2022-2023年**：构建能够 **"安全造福人类、不受财务回报需求限制"** 的通用人工智能[reference:15]
- **2025年底（最新版）** ：简化为 **"确保通用人工智能使全人类受益"** ——删除了"安全"和"不受财务回报需求限制"两个关键表述[reference:16][reference:17]

### 3.2 核心解读

使命表述的转变引发了外界广泛关注。批评者认为，移除"安全"和"不受利润约束"的承诺，反映出公司在商业化压力下的价值重心迁移[reference:18]。同期，负责长期风险评估与价值对齐的专项团队被解散[⚠️ 待验证]。

## 四、企业文化

### 4.1 "Code Red"高压文化

近期多家媒体披露，OpenAI自2025年12月以来处于"Code Red"（红色警戒）状态，员工进入全天候工作模式，深夜食堂排队成为常态[reference:20][reference:21]。韩国代表描述称："公司氛围非常积极和热情，整个组织边加速研究边思考'AI的本质'。"[⚠️ 待验证]

### 4.2 扩张中的组织变化

- **规模扩张**：团队从2015年的11人增长至2025年的600+人
- **使命对齐团队被解散**：原负责向公众和员工传播公司使命的团队于2026年初被解散[⚠️ 待验证]
- **商业化转型**：2026年的招聘重心明显转向B2B销售、企业应用部署和客户成功岗位，纯研究岗位占比下降[⚠️ 待验证]
- **人才回流与流动**：2025年经历大规模管理层出走（联合创始人一度仅剩2人常驻，Brockman 回归后为3人，见2.1节口径说明），同时也出现了一波人才回流潮[reference:12]

## 五、关键产品矩阵

### 5.1 核心模型系列

| 产品 | 发布时间 | 核心特点 |
|------|---------|---------|
| **GPT-5** | 2025年8月7日 | 统一多模态架构，支持文字/图像/音频/视频输入，256K至1M token上下文窗口，专家级推理能力[reference:27] |
| **GPT-5.2** | 2025年12月11日 | 改进"人格"和创意能力[reference:28] |
| **GPT-5.3 Instant** | 2026年Q1 | 专攻"聊天翻车"问题，幻觉率暴降27%[来源: OpenAI 官方发布（详见 gpt-5-series.md）] |
| **GPT-5.3-Codex** | 2026年2月6日 | 编程专项模型[来源: OpenAI 官方发布（详见 gpt-5-series.md）] |
| **GPT-5.4** | 2026年3月 | 首次具备**原生电脑操控能力**（Native Computer Use），可自动执行点击、填表、跨软件导航等操作任务[来源: OpenAI 官方发布（详见 gpt-5-series.md）] |
| **GPT-5.5** | 2026年4月23日 | GPT-5 世代最后一个正式 GA 版本（5.6 为有限预览），面向Plus、Pro、Business和Enterprise用户开放[来源: OpenAI 官方发布（详见 gpt-5-series.md）] |
| **GPT-5.6 系列** | 2026年6月26日 | 三模型分层架构：Sol（旗舰推理）/ Terra（均衡通用）/ Luna（经济轻量），另有 Sol Ultra 高算力模式。**已被 GPT-6 世代取代（09-22）**，Sol 曾于 08-21 降价[来源: OpenAI 官方博客, System Card] |
| **GPT-6 系列** | 2026年9月 | 新世代（代号体系）：Astra（旗舰）/ Sol（workhorse）/ Terra（性价比）/ Luna（轻量，272K 分段计价）四档；GPT-6.1 Sol 于 09-29 点更新、GPT-6.1 Terra 于 10-26 回归性价比档；**2026-11-17 GPT-6.2 Astra（$8/$40）/ GPT-6.2 Sol（$2/$10）分别接任旗舰与 workhorse**，Terra/Luna 档未更新。详见 [GPT-6 系列](gpt-6-series.md) |

**已退役模型**（2026年2月13日生效）：GPT-4o、GPT-4.1、GPT-4.1 mini、o4-mini、GPT-5 Instant、GPT-5 Thinking等[来源: OpenAI 官方公告（详见 gpt-5-series.md）]

### 5.2 ChatGPT

- 发布：2022年11月30日
- 全球现象级AI应用，目前周活跃用户约**9亿**[reference:34]
- 分层定价策略：Free / Plus（每月$20）/ Pro（每月$100）[reference:35]
- 2026年开始在ChatGPT中测试广告投放，标志收入模式从纯订阅向"订阅+广告"双轮驱动转变[⚠️ 待验证]

### 5.3 API与企业产品

- **开发者API**：按Token计费，支持GPT-6全系列模型（GPT-5 世代已被取代，见 [GPT-5 系列](gpt-5-series.md)）
- **ChatGPT Enterprise / Team**：面向企业的安全合规版本
- **Sora**：文生视频模型——已"静静关闭"，原因是生成5秒视频即耗约2.5美元GPU成本[⚠️ 待验证]

### 5.4 硬件规划

计划于**2026年下半年发布首款硬件设备**，试图通过软硬一体化构建更深的商业护城河[reference:38]

## 六、产品收入、DAU与ARR

### ⚠️ 数据可信度提示
> 以下ARR、用户规模等数据部分来自媒体报道或公司选择性披露，具体数字信源可能存有差异，请作为参考而非最终审计依据。

### 6.1 年化经常性收入（ARR）增长轨迹

| 时间 | ARR | 增长幅度 | 来源 |
|------|-----|---------|------|
| 2022年 | ~0.28亿美元 | — | [⚠️ 待验证] |
| 2023年 | ~20亿美元 | 71× | [reference:40] |
| 2024年 | ~60亿美元 | 3× | [reference:41] |
| **2025年** | **~200亿美元** | **3.3×** | [reference:43] |
| 2026年Q1（估算） | ~250亿美元 | — | [⚠️ 待验证（媒体估算）] |

> 官方CFO Sarah Friar于2026年1月明确披露：2025年ARR突破200亿美元[reference:43][reference:44]

### 6.2 用户与流量数据

| 指标 | 数据 | 说明 |
|------|------|------|
| 周活跃用户（WAU） | **约9亿** | 2026年初数据[reference:45] |
| 全球企业客户 | **突破100万家** | 2026年数据[⚠️ 待验证] |
| 企业收入占比 | **约80%** | 占总收入的最大部分[⚠️ 待验证] |
| 开发者市场份额 | **21%**（对比Anthropic的42%） | 编程工具领域存在差距[⚠️ 待验证] |
| 企业API接口支出份额 | 约27%（低于Anthropic的40%） | 2025年数据，2023年曾为50%[reference:49] |

### 6.3 收入结构

- **订阅与API**：面向个人和团队的订阅服务 + 开发者按量计费API，是核心收入来源
- **广告**：已启动测试，面向免费用户层，目标2026年广告收入达10亿美元[⚠️ 待验证]
- **企业合同**：增长最快的板块，2026年招聘重心全面转向B2B销售和交付团队[⚠️ 待验证]

### 6.4 成本与亏损

- **算力支出**：2026年预计支出约400亿美元，对应收入约260亿美元[⚠️ 待验证]
- **每日现金消耗**：约1.3亿美元[⚠️ 待验证]
- **单位经济模型**：高算力成本使公司尚未实现正向经营利润；此前记录的单位收入成本比例缺少可回溯原始信源，不再保留具体数值[⚠️ 待验证]
- **2029年盈利预期**：据 The Information 报道，OpenAI 预计到 2029 年实现盈利[reference:56]

### 6.5 估值（需核实）

- 当前私人市场估值约**8,500亿美元**[reference:57]
- IPO前预估：部分机构预估可达万亿级别

## 七、算力部署与规划（GW级别）

> ⚠️ 基础设施数字需以实际部署为准，部分宣传可能包含超前承诺。

### 7.1 现有算力规模

| 时间 | 算力规模 | 增长幅度 |
|------|---------|---------|
| 2023年 | 0.2 GW | — |
| 2024年 | 0.6 GW | 3× |
| **2025年** | **1.9 GW** | **3.2×** |

> 数据来源：CFO Sarah Friar于2026年1月正式披露[reference:58][reference:59]

### 7.2 行业算力基建成本基准

- **1 GW AI 算力中心**（含 GPU、存储、土地）约需 **500 亿美元** [来源: 用户口述] ⚠️ 待官方验证

### 7.3 星际之门（Stargate）项目

OpenAI的超级算力计划，联合**软银、甲骨文**等伙伴：

- **总投资计划**：5,000亿美元（历史上最大规模AI基础设施建设计划之一）[reference:60]
- **目标总规模**：10 GW AI算力基础设施[reference:61]
- **实际进度**：截至2025年底，实际锁定约**7.5 GW**，未达10 GW初始目标[reference:62]
- **2030年算力支出预测**：约6,665亿美元（较原预测4,500亿美元上调）[⚠️ 待验证]

### 7.4 密歇根项目

2026年初动工，在密歇根州萨林镇建设超1 GW数据中心园区，使星际之门总规划容量增至**超8 GW**[reference:64][reference:65]

### 7.5 与英伟达的战略合作

- OpenAI与英伟达签署战略合作：将部署至少**10 GW的英伟达系统**，包含数百万颗GPU[reference:66]
- 英伟达向OpenAI持续投资，总额最高可达**1,000亿美元**[reference:67]

### 7.6 算力战略特点

- **单一供应商依赖风险**：历史上高度依赖微软Azure，当前正在推进多元化策略，与甲骨文、软银等建立独立合作关系
- **算力即飞轮**：CFO明确将商业模式描述为"算力投入→模型能力→产品采用→商业收入"的正向反馈循环[reference:70]

## 八、近期CXO核心观点精选

### 8.1 萨姆·奥尔特曼（Sam Altman，CEO）

1. **"2026年，AI将开始解决复杂的商业问题"** （2025年6月）：预测AI系统将具备发现新颖洞见的能力[reference:71]
2. **"AGI的关键是无限记忆而非推理"** （2025年12月，Big Technology播客）：提出实现AGI需要AI拥有"完美无限的记忆能力"，并表示公司正在2026年推动实现这一目标[reference:72]
3. **承认"搞砸了"** （2026年1月）：就GPT-5.2在牺牲写作能力以换取编程性能的争议做出回应[⚠️ 待验证]
4. **"AI将推动更便宜的生产、更快的经济增长，同时颠覆大量现有工作"** （2026年4月，BlackRock基础设施峰会主题演讲）[⚠️ 待验证]
5. **"温和奇点"（The Gentle Singularity）** （2025年6月博文）：预言2025年已出现能执行真正认知工作的AI Agent，代码编写领域已被永久改变；2026年将看到能发现新颖洞见的系统到来[reference:76]
6. **承认写作体验待改进**（2026年11月）：就 GPT-6.2 发布日社区对叙事过度净化、风格指令不遵循的投诉，承认模型 "nice to work with" 待改进（官方社区帖内引述，UGC 仅方向参考）[来源: OpenAI 官方社区 GPT-6.2 公告帖]

### 8.2 萨拉·弗莱尔（Sarah Friar，CFO）

1. **算力飞轮论**（2026年1月官网博文）："我们的增长得益于计算、前沿研究、产品及变现之间的协同效应。对计算的投入推动了前沿研究，使模型能力实现跨越式提升。更强大的模型能够解锁更优质的产品，推动更广泛采用，采用率提升带来收入增长，收入又为下一波计算提供资金——这一循环不断叠加。"[reference:77][reference:78]

## 九、战略转型动态

### 9.1 2026年关键变化

- **商业模式转型**：从纯订阅+API向 **"订阅+API+广告"** 三支柱转变[⚠️ 待验证]
- **C端到B端的重心转移**：招聘重心从AI研究岗转向B2B销售、企业应用部署和客户成功岗[⚠️ 待验证]
- **考虑新型收入模式**：探讨"客户成功时抽成"等基于AI实际价值创造的定价模型[⚠️ 待验证]
- **硬件发布计划**：2026年下半年发布首款硬件设备[reference:82]

### 9.2 面临的核心挑战

1. **高算力成本与现金流压力**：边际成本下降速度慢于传统软件业，每次对话背后都有 GPU 的实时算力消耗
2. **创始团队流失**：11位联合创始人一度仅剩2人常驻（媒体口径，见2.1节），Brockman 回归后当前为3人；核心管理层在2025年经历大震荡[reference:84]
3. **微软的"金主+对手"双重身份**：微软持有27%股权，既是云基础设施依赖方，也是企业市场的直接竞争者[reference:85]
4. **安全承诺被淡化**：使命陈述删除"安全"和"不受利润约束"的表述，引发伦理争议[reference:86]
5. **竞争对手Anthropic在编程市场的反超**：开发者偏好从OpenAI大幅转向Claude

## 十、数据使用建议

1. **ARR、DAU、估值等核心运营数据**未经独立审计，建议标注"媒体报道估算"，并以OpenAI官方披露、以及Bloomberg/Reuters等权威财经媒体的报道为最终依据。
2. **算力规划数字**可能因项目推进延迟、资金约束等存在偏差，建议以实际交付进度为准。
3. **估值数据**（8,500亿美元等）属私人市场估值，IPO定价可能有较大差异。
4. **若用于正式投资报告**，建议附上所有数据来源链接，并明确区分"已确认事实"与"市场传闻/估算"。

---

## 十一、OpenAI 技术演进与研究影响力

### 模型技术创新演进

> 独创性分级：🌟 首创 / 🔧 组合创新 / ⚙️ 工程优化 / 📋 跟进对齐（口径同 ai-native-expert「新模型发布分析框架」）。官方宣称的"首个"均标注"官方称"。GPT-6 世代逐项拆解与详细参数见 [gpt-6-series.md](gpt-6-series.md)，GPT-5 世代见 [gpt-5-series.md](gpt-5-series.md)。

| 版本 | 时间 | 核心技术创新 | 独创性 | 能力/成本影响 |
|------|------|-------------|--------|--------------|
| **GPT-3** | 2020 | 1750 亿参数 + few-shot 上下文学习，无需微调即可完成多类 NLP 任务 | 🌟 首创 | 改写 NLP 研究范式，大模型进入主流视野 |
| **InstructGPT / RLHF** | 2022 | 确立基于人类反馈的强化学习（RLHF）标准对齐流程 | 🌟 首创 | 行业对齐标准范式，ChatGPT 的直接技术前身 |
| **GPT-5** | 2025.08 | 统一多模态架构（文字/图像/音频/视频输入），256K–1M 上下文 | 🔧 组合创新 | 单一路由取代多模型选择，专家级推理 |
| **GPT-5.4** | 2026.03 | 原生电脑操控（Native Computer Use）融入旗舰 | 🔧 组合创新 | 点击/填表/跨软件导航成为模型原生能力 |
| **GPT-6 Astra** | 2026.09 | 前代模型监督训练新一代（官方称首例，待技术报告佐证）；首个触及 Preparedness Framework Critical 级（cyber）；monitorability 作为继续 scaling 前置条件 | 🌟 首创 ×3 | 生产级 computer use + 1M 级 agent 记忆；Daybreak 门控改变发布形态（分阶段 + 高级 cyber 受限访问） |
| **GPT-6 Sol / Luna** | 2026.09 | 缓存与 effort/工具变更解耦；Luna 272K 分段定价 | 🔧 组合创新 | 永久价 + cached 最高 90% 折扣，直击 agent 多轮会话真实成本结构 |
| **GPT-6.2 Astra / Sol** | 2026.11 | token 效率作为一等优化目标（同分下 xhigh 输出 token 仅 max 的 41%）；LLM 驱动生成式视频后期（Higgsfield Miracle） | ⚙️ 工程优化 + 🔧 组合创新 | 官方称每任务成本 < GPT-6 Astra 的 1/3；旗舰降价对齐竞品锚点价；本次无可验证 🌟 首创 |

### 技术方向研判

- **技术主线**：Scaling Laws（2020）→ RLHF 对齐（2022）→ 多模态统一（2025）→ agent 原生能力（computer use / 长程记忆，2026）→ token 效率与每任务成本（GPT-6.2）。从"炼更大模型"演化为"炼更省任务的模型"
- **持续押注**：超大规模训练 run（GPT-6 Astra 用 Stargate Texas 10 万+ GPU）、1M 级家族统一上下文 shape、reasoning effort 分档
- **路线转向**：①定价叙事从绝对智力溢价转向 price-per-task——GPT-6 Astra $10/$50 溢价未获第三方成本数据支持，6.2 以降单价 + token 效率双管齐下；②训练监督从人工/外部评估器转向模型监督模型；③安全策略从使命宣言承诺转向工程化门控（Daybreak 准入、monitorability 前置），与使命文本删除"安全"表述形成对照
- **差异化定位**：闭源旗舰 + "能力越强→门控越紧"的分级发布模式（Critical 级 cyber 能力仅向可信防御者开放），区别于 Anthropic 的对齐叙事与开源阵营的自托管路线

###  核心研究脉络与关键数据

OpenAI的研究体系围绕“规模扩展（Scaling）→ 能力涌现（Emergence）→ 范式统一（Unification）”展开，核心贡献者包括：

| 关键人物 | 影响力数据 | 代表贡献 |
|----------|-----------|----------|
| **Alec Radford** | 论文总被引超**19万-22万次**，GPT-1、GPT-2第一作者，CLIP第一作者，Whisper第一作者 | 被评价为“爱因斯坦级天才”“现代生成式AI之父”[⚠️ 待验证] |
| **Ilya Sutskever** | 上榜全球高被引科学家TOP 10 | AlexNet、GPT系列、超级对齐框架[来源: 36kr 2025-08 高被引报道] |
| **OpenAI整体** | 2020-2022年间，全球引用次数前100的AI论文中，OpenAI**高引用转化率排名全球第一**[⚠️ 待验证] | 论文数量虽不算最多，但篇均影响力极高 |

###  标志性论文

| 论文 | 时间 | 核心贡献 |
|------|------|----------|
| **GPT-3 / Language Models are Few-Shot Learners** | 2020年 | 参数量达1750亿，证明通过提示词（Prompt）即可在无需微调的情况下完成翻译、问答、算术等多种NLP任务，彻底改写了AI研究范式[论文: arXiv 2005.14165] |
| **GPT-2 / Language Models are Unsupervised Multitask Learners** | 2019年 | 展示了大规模语言模型在零样本设置下执行多种任务的潜力 |
| **Scaling Laws for Neural Language Models** | 2020年 | 系统阐述了模型大小、数据集规模和计算量之间的幂律关系，为“大模型信仰”提供了理论基石[论文: arXiv 2001.08361] |
| **CLIP (Learning Transferable Visual Models)** | 2021年 | 连接文本与图像，推动了DALL-E、Stable Diffusion等跨模态生成模型的爆发 |
| **Training language models to follow instructions with human feedback（InstructGPT）** | 2022年 | OpenAI 通过监督微调与基于人类反馈的强化学习（RLHF）训练指令遵循模型[[论文: arXiv 2203.02155](https://arxiv.org/abs/2203.02155)] |
| **GPT-5.2** | 2026年2月 | 发表预印本，报道GPT-5.2**独立发现并证明了全新的胶子振幅数学公式**，首次证明大模型可做出原创性理论物理贡献[⚠️ 待验证] |

> GPT-5/5.3/5.4 等产品能力迭代不在此重复，见上方「模型技术创新演进」节与第五章产品矩阵。

### 行业影响力

- **商业化发动机**：从GPT-3开始，系列成果彻底改变了自然语言处理的研究与应用格局，并将大模型带入主流视野
- **ChatGPT 效应**：2022年11月30日ChatGPT发布后，5天内用户破百万，2个月破亿，成为史上增长最快的应用，引发了全球性的生成式AI竞赛
- **技术路径定义者**：从LLM到RLHF到多模态大一统，OpenAI定义了大量AI行业的技术路径和标准实践
- **顶级会议存在感**：论文常年入选NeurIPS、ICML、ICLR，并发表在Nature等顶刊
- **科研溢出效应**：学术影响力辐射效果显著，仅ChatGPT一项就已合著超过42篇学术论文，累计被引1952次，覆盖12个领域和6种语言[⚠️ 待验证]

---

## 参考来源

> 正文 `[reference:N]` 编号的可追溯映射（编号—标题—URL）。链接于 2026-11-18 经检索确认存在；无法可靠回溯的编号已在正文改为命名来源或 [⚠️ 待验证] 标注，不在上表（清单见文末）。

- **[reference:0][reference:1]** Business Insider, "Here's Where OpenAI's 11 Cofounders Are Now"（2024-10-03）— https://www.businessinsider.com/where-openai-cofounders-are-now-sam-altman-2024-10
- **[reference:2][reference:7]** CNBC, "OpenAI power consolidates under co-founder Greg Brockman ahead of IPO"（2026-07-10）— https://www.cnbc.com/2026/07/10/openai-power-consolidates-under-co-founder-greg-brockman-ahead-of-ipo.html；Wikipedia, "Greg Brockman" — https://en.wikipedia.org/wiki/Greg_Brockman
- **[reference:3]** Forbes, "Thinking Machines Lab" 公司页（Murati 创办、融资与人员流动）— https://www.forbes.com/companies/thinking-machines-lab/
- **[reference:4]** Wikipedia, "Wojciech Zaremba"（co-founder of OpenAI, 2016–present）— https://en.wikipedia.org/wiki/Wojciech_Zaremba
- **[reference:5][reference:6]** Business Insider, "The career rise of OpenAI's billionaire CEO, Sam Altman" — https://www.businessinsider.com/sam-altman
- **[reference:8]** Wikipedia, "Sarah Friar"（2024-06 加入 OpenAI 任 CFO）— https://en.wikipedia.org/wiki/Sarah_Friar；Reuters（2024-06-10）— https://ca.finance.yahoo.com/news/openai-hires-sarah-friar-cfo-173823543.html
- **[reference:9]** 36kr 英文版, "Two Post-1990s Individuals Prop Up Core Research at OpenAI After Ilya"（2025-08）— https://eu.36kr.com/en/p/3404179793006217
- **[reference:10]** Digidai, "Mark Chen at OpenAI: research leadership, documented"（2025-11，含 2025-03 CRO 角色扩展）— https://digidai.github.io/2025/11/08/mark-chen-openai-cro-deep-analysis/
- **[reference:11]** The Information, "The Rising Guard at OpenAI"（2024-08）— https://www.theinformation.com/newsletters/ai-agenda/the-rising-guard-at-openai
- **[reference:12]** Built In, "Inside Thinking Machines Lab, Mira Murati's New AI Startup"（含 2026-01 联创回流 OpenAI 记录）— https://builtin.com/articles/what-is-thinking-machines-lab
- **[reference:13][reference:14][reference:15]** Fortune, "OpenAI changed its mission statement 6 times in 9 years..."（2026-02-23）— https://fortune.com/2026/02/23/openai-mission-statement-changed-restructuring-forprofit-business/
- **[reference:16][reference:17][reference:18][reference:86]** The Conversation, "OpenAI has deleted the word 'safely' from its mission..."（2026-02）— https://theconversation.com/openai-has-deleted-the-word-safely-from-its-mission-and-its-new-structure-is-a-test-for-whether-ai-serves-society-or-shareholders-274467
- **[reference:20]** The Information, "OpenAI CEO Declares 'Code Red' to Combat Threats to ChatGPT, Delays Ads Effort"（2025-12）— https://www.theinformation.com/articles/openai-ceo-declares-code-red-combat-threats-chatgpt-delays-ads-effort
- **[reference:21]** Fortune, "Inside OpenAI's fragile AI lead, and the 8-week 'code red' to fend off a rival"（2025-12-17）— https://fortune.com/2025/12/17/sam-altman-chatgpt-openai-versus-google-gemini-code-red-strategy/
- **[reference:27]** OpenAI 官方, "Introducing GPT-5"（2025-08-07）— https://openai.com/index/introducing-gpt-5/
- **[reference:28]** OpenAI 官方, "Introducing GPT-5.2"（2025-12-11）— https://openai.com/index/introducing-gpt-5-2/
- **[reference:34][reference:45]** OpenAI 官方, "Scaling AI for everyone"（2026-02-27，900M WAU / 5,000万+ 消费订阅）— https://openai.com/index/scaling-ai-for-everyone/
- **[reference:35]** OpenAI 官方定价页 "Plans and Pricing" — https://chatgpt.com/pricing/
- **[reference:38][reference:82]** Wikipedia, "Io (company)"（io 收购与 2026 年设备计划）— https://en.wikipedia.org/wiki/Io_(company)；ROIC, "OpenAI Targets Late 2026 for Screenless AI Device Launch"（2026-01-19）— https://www.roic.ai/news/openai-targets-late-2026-for-screenless-ai-device-launch-powered-by-upgraded-audio-models-01-19-2026
- **[reference:40][reference:41][reference:43][reference:44][reference:58][reference:59][reference:70][reference:77][reference:78]** OpenAI 官方, "A business that scales with the value of intelligence"（CFO Sarah Friar 博文：$2B(2023)/$6B(2024)/$20B+(2025) ARR、算力与增长口径）— https://openai.com/index/a-business-that-scales-with-the-value-of-intelligence/；Reuters 转述（2026-01-19）— https://www.reuters.com/business/openai-cfo-says-annualized-revenue-crosses-20-billion-2025-2026-01-19/
- **[reference:49]** Menlo Ventures, "2025: The State of Generative AI in the Enterprise"（企业 LLM 支出：Anthropic 40% / OpenAI ~27%）— https://menlovc.com/perspective/2025-the-state-of-generative-ai-in-the-enterprise/
- **[reference:56]** Reuters 转述 The Information, "OpenAI expects business to burn $115 billion through 2029"（2025-09-05/06，2029 年现金消耗与盈利时点口径）— https://www.reuters.com/technology/openai-expects-business-burn-115-billion-through-2029-information-reports-2025-09-06/
- **[reference:57]** OpenAI 官方, "OpenAI raises $122 billion to accelerate the next phase of AI"（2026-03-31，投后估值 $8,520 亿）— https://openai.com/index/accelerating-the-next-phase-ai/；Bloomberg（2026-02-19，~$8,500 亿口径）— https://www.bloomberg.com/news/newsletters/2026-02-19/openai-nears-100-billion-funding-at-850-billion-valuation
- **[reference:60][reference:61]** OpenAI 官方, "OpenAI, Oracle, and SoftBank expand Stargate with five new AI data center sites"（2025-09-23，$500B / 10GW 目标）— https://openai.com/index/five-new-stargate-sites/；SoftBank 官方公告（2025-01-22）— https://group.softbank/en/news/press/20250122
- **[reference:62]** Epoch AI, "OpenAI Stargate: where the US sites stand"（2026-04，站点进度对照；"7.5 GW 已锁定"具体口径 ⚠️ 待验证）— https://epoch.ai/publications/openai-stargate-where-the-us-sites-stand
- **[reference:64][reference:65]** OpenAI 官方, "Expanding Stargate to Michigan"（2025-10-30，Saline 镇 1+ GW 园区）— https://openai.com/index/expanding-stargate-to-michigan/
- **[reference:66][reference:67]** NVIDIA 官方新闻, "OpenAI and NVIDIA Announce Strategic Partnership to Deploy 10GW of NVIDIA Systems"（2025-09-22，含最高 1,000 亿美元投资）— https://nvidianews.nvidia.com/news/openai-and-nvidia-announce-strategic-partnership-to-deploy-10gw-of-nvidia-systems；OpenAI 版 — https://openai.com/index/openai-nvidia-systems-partnership/
- **[reference:71][reference:76]** Sam Altman 博客, "The Gentle Singularity"（2025-06-10）— https://blog.samaltman.com/the-gentle-singularity
- **[reference:72]** Big Technology, "Sam Altman on OpenAI's Plan to Win, AI Personalization, Infrastructure Math"（2025-12-18）— https://www.bigtechnology.com/p/sam-altman-on-openais-plan-to-win；The Independent（2025-12-26，"infinite, perfect memory" 转述）— https://www.independent.co.uk/tech/openai-sam-altman-ai-breakthrough-chatgpt-b2890125.html
- **[reference:84]** 同 [reference:0][reference:1]（"仅剩 2 人"原始口径来源），正文已按 2.1 节统一口径修正为当前 3 人在司
- **[reference:85]** Microsoft 官方博客, "The next chapter of the Microsoft–OpenAI partnership"（2025-10-28）— https://blogs.microsoft.com/blog/2025/10/28/the-next-chapter-of-the-microsoft-openai-partnership/；Bloomberg, "OpenAI Gives Microsoft 27% Stake"（2025-10-28）— https://www.bloomberg.com/news/articles/2025-10-28/microsoft-to-get-27-of-openai-access-to-ai-models-until-2032

> 📌 **无法回溯编号清单**（正文已改为命名来源 / [⚠️ 待验证]，不在上表）：19、22、23、24、25、26、29–33、36、37、39、42、46–48、50–54、63、68、69、73–75、79–81、83；第十一章原编号 12–22 与第二/三章编号冲突，已就地改为 arXiv / 命名来源。

---

## Changelog

| 日期 | 变更内容 |
|------|----------|
| 2026-11-18 | 复核修复：RLHF 标志性论文更正为 OpenAI InstructGPT 原论文，移除误挂的 Anthropic 论文归属 |
| 2026-11-18 | 校验修复（需更新项6–7）：第二章按「联合创始人/早期资助人/后期高管」三层重整，更正 Thiel/Murati 误入创始团队，统一"仅剩2人"口径为当前3人在司（Altman/Brockman/Zaremba）；新增编号—标题—URL 参考来源映射，无法回溯编号改为命名来源或待验证标注 |
| 2026-11-18 | 校验修复：移除无法回溯的单位经济比例，统一 2029 年盈利预期并保留成本压力的定性表述 |
| 2026-11-18 | 同步+回填：产品矩阵与 API 行同步 GPT-6.2 旗舰换代（详情见 gpt-6-series.md）；CXO 观点补 Altman 写作体验回应（UGC 方向参考）；第十一章按新模板回填两子节并更名，标志性论文表去重产品行；修复公司概况节格式缺陷 |
| 2026-11-03 | 校验修复+补研（knowledge-verification-2026-11-03）：产品矩阵 GPT-6 行补记 GPT-6.1 Terra（2026-10-26 回归性价比档，单价约 Sol 50%）；主文档 gpt-6-series.md 已含专章 |
| 2026-06-11 | 合并：openAI CFO 口径 - 新增 7.2 行业算力基建成本基准（1GW AI 算力中心约 500 亿美元） |
