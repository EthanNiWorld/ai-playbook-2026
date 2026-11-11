# AI 安全护栏（AI Guardrails）

> 最后更新: 2026-11-11
> 所属厂商: Alibaba (Alibaba Cloud)
> 产品类别: AI 安全 / 内容安全
> 状态: Published

<!-- SUMMARY_START -->
**定位**: 阿里云为 AI 系统（大模型 / AI 应用 / AI Agent）设计的输入输出一站式安全防护产品，依托通义大模型（Qwen3Guard）提供内容合规、提示词攻击、敏感数据、恶意文件/URL、模型幻觉、数字水印等风险检测与自定义防护
**适用**: 对话机器人、AI 搜索/RAG、智能客服、AIGC 创作平台、AI Agent 指令防护、自建 AI 网关合规拦截、训练语料去毒、AIGC 内容标识合规
**不适用**: 纯 UGC 审核（发帖/评论/直播弹幕，应选同产品族的「内容安全增强版」）；追求零延迟零成本的场景（护栏是旁路检测，有毫秒级延迟与按次费用）
**竞品**: AWS Bedrock Guardrails、Azure AI Content Safety、百度智能云大模型安全护栏、深信服大模型安全护栏；开源自建替代 Qwen3Guard / Llama Guard
**常搭配**: 百炼平台（header 一键集成）、AI 网关（Higress）、WAF、Dify、OpenClaw 插件
<!-- SUMMARY_END -->

## 一、产品定位与解决的问题

### 一句话定位

在 LLM 的**输入侧（用户 Prompt）和输出侧（模型生成内容）**各加一道旁路检测：风险内容进不来、违规内容出不去，同时满足生成式 AI 内容合规与 AIGC 标识等监管要求。即接即用，也支持自定义检测项、阈值与词库。

### 产品族关系（售前必须先讲清）

「AI 安全护栏」是产品族名，下挂**两个独立商品**（[产品概述](https://help.aliyun.com/zh/document_detail/2573826.html)）：

| 商品 | 定位 | 典型场景 |
| --- | --- | --- |
| **安全护栏（Guardrails）** | AI 场景一体化防护 | 文生文、图片理解、AI 绘画、AI Agent、审核智能体、OpenClaw 运行时防护 |
| **内容安全（Content Moderation）** | UGC 场景多模态审核 | 发帖评论、游戏聊天、直播弹幕、电商商品发布；含 OSS 违规检测 |

- 综合场景按主场景选：AI 伴聊 → 安全护栏；社交 App 用户上传 AI 图 → 内容安全。
- 内容安全增强版（2.0）相比 1.0：标签 100+（1.0 仅 40+ 且单标签）、价格约为 1.0 的 22%~48%、预置业务场景。**老版内容安全已开通 ≠ 新版护栏已开通**（商品码独立，详见坑 1）。

### 解决什么问题

| 风险 | 检测能力 | 业务后果 |
| --- | --- | --- |
| 内容合规 | 涉政敏感、色情低俗、暴恐违禁、偏见歧视、不良价值观、广告法极限词等 100+ 细分标签 | 监管处罚、应用下架（生成式 AI 合规底线） |
| 提示词攻击 | 越狱指令、角色扮演诱导、系统指令篡改、Direct Prompt Injection | Agent 被劫持越权、系统提示词泄露 |
| 敏感数据泄露 | 个人隐私 / 企业敏感数据识别，S0~S3 分级，支持脱敏（mask） | 训练数据外溢、对话泄露隐私（医疗/金融/知识库问答刚需） |
| 恶意文件 / URL | 文档宏病毒、WebShell、钓鱼链接、信息盗取 | 文档上传场景被注入、AI 搜索/RAG 成为攻击传播媒介 |
| 模型幻觉 | 输出与 referenceContent 参考内容比对，识别编造/矛盾信息（公测） | RAG/客服答错事实 |
| AIGC 标识合规 | 图片数字水印（可见/不可见），对应《人工智能生成合成内容标识办法》 | AIGC 内容不可追溯、版权纠纷 |
| 业务自定义风险 | 自定义词库（如竞品名拦截）、自定义检测 Agent（自然语言描述风险） | 通用策略覆盖不到的业务红线 |

## 二、检测能力与 Service 矩阵

### 防护维度（返回字段 `Detail[].Type`）

| Type | 维度 | 开关默认状态 | 商业化状态 |
| --- | --- | --- | --- |
| contentModeration | 内容合规 | 默认开启 | 商用，单独计费 |
| promptAttack | 提示词攻击 | 官方口径需手动开启；实测账号默认已开（以控制台为准） | 商用（2026-01-22 起收费） |
| sensitiveData | 敏感内容 | 默认关闭 | 商用，单独计费 |
| customLabel | 自定义检测 Agent | 需配置 | 商用，按所选模型分档计费 |
| modelHallucination | 模型幻觉 | 默认关闭 | 公测（当前不计费） |
| maliciousFile | 恶意文件 | 默认关闭 | 公测（当前不计费） |
| maliciousUrl | 恶意 URL | 默认关闭 | 公测（当前不计费） |
| waterMark | 数字水印标识 | 默认关闭 | 公测（当前不计费） |

### Service（检测场景编码）

| 模态 | Service | 说明 |
| --- | --- | --- |
| 文本 | `query_security_check` / `response_security_check` | 输入 / 输出标准版 |
| 文本 | `query_security_check_pro` / `response_security_check_pro` | pro 版已 GA：内容合规标签细粒度显著增加，**与标准版同价**，新接入建议直接用 pro |
| 文本 | `response_security_check_hp` | 高性能版，面向流式切片，官方目标单切片服务端 <100ms |
| 文本 | `query_security_check_cb` / `response_security_check_cb` | 出海版（中国站）；国际站对应命名为 `_intl` 后缀 |
| 图片 | `img_query_security_check` / `img_response_security_check` | AIGC 输入/输出图片检测（输出可叠加水印） |
| 文图 | `text_img_security_check` | 多模态文本+图片 |
| 文件 | `file_security_sync_check` / `text_file_sec_sync_check` | 文件实时检测 / 文本文件实时检测 |
| 音频 | `audio_security_check` | AIGC 音频检测 |
| 百炼集成 | `bl_query_guard` / `bl_response_guard`；`qwen_query_check` / `qwen_response_check`（Qwen3Guard，主推）；`_pro` 版；`bl_img_query_guard` / `bl_img_response_guard` | 百炼内按模型自动匹配，无需手动指定 |

### 返回结构与处置口径

- **Suggestion**：`block`（阻断）/ `pass`（放行）/ `watch`（观察）/ `mask`（脱敏）；多维度结果合并优先级 **block > mask > watch > pass**；仅敏感内容维度支持 watch/mask，其余只有 block/pass。
- **Level**：high / medium / low / none；**命中自定义词库默认 high + block**；敏感数据用 S0~S3（S0 未检出，数字越大越敏感）。
- **Result**：Label（处置依据）+ Confidence（0~100，部分标签无分值）+ Description（中文解释，**可能变更，禁止基于它做处置逻辑**）；命中词库返回 `Ext.CustomizedHit`（库名+命中词）与 RiskPositions。
- 官方建议：high 直接处置，medium 人工复查，low 日常按无风险处理（高召回需求时再处置）。

## 三、如何配置（接入全流程）

### 1. 开通与授权

1. 账号完成实名认证 → [开通页](https://www.aliyun.com/product/content-moderation/guardrail)免费开通按量付费（开通不收费、不调用不计费）。
2. RAM 用户授权系统策略 **`AliyunYundunGreenWebFullAccess`**，创建 AccessKey。
3. 也可纯 API 开通（实测）：BssOpenApi `CreateInstance`，`ProductCode=lvwang`、`ProductType=lvwang_guardrail_public_cn`、`SubscriptionType=PayAsYouGo`，必带组件参数 `moderationType=text_guard_advanced` + `totalCount=1`。

### 2. 控制台防护配置

路径：**防护配置 > 模型防护 > 目标 Service > 配置**：

- **防护维度开关**：内容合规 / 敏感内容 / 提示词攻击 / 恶意 URL / 模型幻觉 / 检测 Agent，按维度独立计费，按需开启。
- **自定义检测项与阈值**：细分标签逐个开关；置信分阈值 0~100、步长 1（幻觉检测阈值范围 60~100、默认 60）。
- **自定义词库**：命中词库（KeywordHitLibs）+ 忽略词库/白名单（KeywordFilterLibs）；**子串匹配**，命中即 block。
- **代答库**：按风险标签配置自定义代答话术（网关也可自行兜底）。
- **生效延迟**：配置保存后约 2~5 分钟生效（实测词库绑定约 3~5 分钟），勿保存后立即验收。

### 3. API 接入（自建网关 / 多云场景）

**两个调用面、两套 SDK，混用直接报错**（实测验证）：

| 调用面 | SDK | 接入点 | 用途 |
| --- | --- | --- | --- |
| 检测面 | `alibabacloud_green20220302` | 多地域可选（见下表） | `MultiModalGuard` 实时检测 |
| 配置管理面 | `alibabacloud_green20220926` | **仅上海** `green-cip.cn-shanghai.aliyuncs.com` | AddKeywordLib / UpdateServiceConfig / GetServiceConfig / GetCipStats；用请求参数 `RegionId` 指定生效地域 |

检测面接入点（[API 接入指南](https://help.aliyun.com/zh/document_detail/2937221.html)）：上海/北京/杭州/深圳/成都/中国香港/杭州·上海·深圳金融云/新加坡/法兰克福/弗吉尼亚；上海、北京、杭州、深圳、新加坡、法兰克福、弗吉尼亚有 VPC 内网地址（`green-cip-vpc.<region>.aliyuncs.com`），同地域部署可省公网 RTT。

请求要点：`Service` + `ServiceParameters`（JSON 字符串）；文本 `content` ≤2000 字符；`imageUrls` 单图、`fileUrls` 单文件；幻觉检测必传 `referenceContent`；`accountId` 跨请求上下文审核需单独申请开通。

### 4. 流式输出审核（推荐方案）

- 必传 `chatId`（标识一轮问答）+ `done`（本轮终止切片标识），建议传 `sessionId`。
- **按字符切片**：每累计 N 字符送检一次（推荐 hp 版，100~200 字/片）；**滑动窗口**（每 X 字送检最近 N 字）保留上下文但调用次数放大、费用更高。
- 检出风险：立即停止后续输出，撤回已透出内容或替换代答。
- 官方方案文档：[流式审核](https://help.aliyun.com/zh/document_detail/2980054.html)。

### 5. 百炼集成接入（百炼用户最省事）

1. 开通 AI 安全护栏 → 百炼控制台 **安全管理 > 去授权**（SLR）。
2. 调用百炼时加请求头：`X-DashScope-DataInspection: {"input":"cip","output":"cip"}`（仅 Python SDK 与 HTTP 支持）。
3. 按模型自动匹配 Service：Qwen3-Max / Qwen-Max / Qwen-VL-Max 走 `_pro`，其余主流模型走标准/Qwen3Guard 版。
4. 命中违规：返回 **400 `data_inspection_failed`**（OpenAI 兼容与 DashScope 协议均是），业务侧需捕获该错误做代答。
5. 百炼平台红线标签不可关闭，其余标签可在护栏控制台按需开关。
6. 文档：[面向百炼用户的 AI 安全护栏](https://help.aliyun.com/zh/document_detail/2923687.html)。

### 6. 其他接入方式

AI 网关（统一多模型审核策略）、WAF、百炼智能体、Dify 智能体、OpenClaw 运行时插件（[产品概述](https://help.aliyun.com/zh/document_detail/2573826.html)）。

## 四、怎么计费

### 计费规则要点

- **按量后付费**：开通免费、不调用不计费；**开通后不支持关闭/退订**，停止调用即停止计费。
- **仅 HTTP 200 的成功请求计费**，错误请求（408/588 等）不计费（实测验证）。
- **按维度独立计费**：同一次调用开启内容合规+提示词攻击 = 2 次计费；文本单次 ≤2000 字符同价，与长度无关。
- **流式每个切片 = 1 次独立计费调用**；文件审核按 2000 字符/切片计量。
- 计费周期窗口 5 分钟（中国站口径）；欠费停服，补缴后 5 分钟内恢复。
- 用量对账：`GetCipStats` API（当日数据 T+1）；账单实例 ID 格式 `UID;服务类型`，不支持按实例拆分费用明细。

### 国际站新加坡节点 USD 列表价（主口径）

来源：[国际站定价页](https://www.alibabacloud.com/zh/product/content-moderation/pricing)（2026-11-11 核实）。**国际站护栏分表仅新加坡节点，无北京 USD 分表**；中国内地节点为人民币计价（见下表参考）。

| 审核类型 | 计量项 | 单价（USD） |
| --- | --- | --- |
| 文本审核-高级 text_guard_advanced | query/response_security_check_intl | $6 / 万次 |
| 敏感内容审核 text_sddp_advanced | 同上 | $6 / 万次 |
| 提示词攻击审核 | 同上 | $6 / 万次 |
| 检测 Agent-基础 text_guard_llm_standard | Qwen3Guard-Gen-4B（内置提示词） | $8 / 万次（与提示词长度无关） |
| 检测 Agent-基础 | Qwen3.0-Flash/极速版 | $8 / 万条切片 |
| 检测 Agent-高级 text_guard_llm_advanced | Qwen3.0-Plus | $16 / 万条切片 |
| 检测 Agent-大模型 36-level1 / level2 | Qwen3.6-Flash / Qwen3.6-Plus | $24 / $40 万条切片 |

- 检测 Agent 切片规则：按**自定义提示词**总字符 3000 字符/切片计量（不足 3000 按 3000）；另有入华版（`_ec` service）$3.1~$15.5/万条切片、图像检测 Agent $6~$40/万条切片，详见[检测 Agent 计费方案](https://www.alibabacloud.com/help/zh/content-moderation/latest/detecting-agent-billing-schemes)。
- 图片/文图/文件审核未列入国际站护栏分表（中国站有售，见下表）。

### 中国内地节点 CNY 列表价（参考口径）

来源：[按量付费计费规则与价格](https://help.aliyun.com/zh/document_detail/2872706.html)（2026-11-11 核实）。

| 接入方式 | 审核类型 | 单价（CNY） |
| --- | --- | --- |
| API / AI 网关 | 文本审核-高级（含 pro/出海版，同价） | 15 元/万次 |
| API / AI 网关 | 敏感内容审核 | 15 元/万次 |
| API / AI 网关 | 提示词攻击审核 | 15 元/万次 |
| API | 图片审核-高级 | 30 元/万次 |
| API | 文图审核-高级 | 45 元/万次 |
| API | 文件同步审核（2000 字符/切片） | 20 元/万条切片 |
| 百炼集成 | 文本合规/敏感内容-基础（bl_*_guard、qwen_*_check） | 0.0004 元/千 Token |
| 百炼集成 | 文本合规/敏感内容-pro（*_pro） | 0.003 元/千 Token |
| 百炼集成 | 提示词攻击审核 | 15 元/万次（以次计，不按 token） |
| 百炼集成 | 图片审核 | 30 元/万次 |

- 百炼集成按 token 计费时**不足 1000 Token 按 1000 计**。
- hp 高性能版未在价格表单列，按文本高级类目计（以账单为准，实测口径）。
- 恶意文件 / 恶意 URL / 模型幻觉 / 数字水印：公测期当前不计费。
- 资源包：内容安全增强版已支持；安全护栏资源包概述页标注"即将支持"，以购买页为准。**QPS 扩容包**可购（默认 QPS + 购买 QPS，超出仍按量），需商务经理或工单核对配置。

### 成本量级示例（自建网关，CNY 实测口径）

内容合规 + 提示词攻击双开 = 0.003 元/次检测。一次对话 = 输入 1 次 + 输出 3 切片 = 4 次调用 → **0.012 元/对话**；日均 1 万对话 ≈ **120 元/天**。切片越细费用越高，滑动窗口再放大。

## 五、限制与配额

| 限制项 | 值 | 说明 |
| --- | --- | --- |
| 文本长度 | 单次 ≤2000 字符 | 超长需切片；文件审核同按 2000 字符切片计量 |
| QPS | 单用户 50 次/秒；含文件模态 10 次/秒 | 超限返回 588；扩容需购 QPS 包（商务/工单） |
| 图片 | 单张 ≤20MB，边长 ≤30000px，总像素 ≤2.5 亿 | 建议 >200×200px；URL 下载 3s 超时；GIF 取首帧 |
| 文件 | 单个 ≤10MB | 单次请求单文件/单图 |
| 检测延迟 | 同步秒级（文本实测约 200ms）；异步约 30s | 官方口径；hp 版服务端目标 <100ms/切片 |
| 上下文审核 | 默认关闭 | accountId 跨请求累积需申请开通；默认各请求独立送检，拆分发送可能漏检 |
| 幻觉检测 | 仅文本类 Service | 必传 referenceContent，否则静默不生效（不报错） |
| 控制台地域 | 上海 / 中国香港 / 新加坡 / 法兰克福 / 弗吉尼亚 | 检测接入地域更多（含北京/杭州/深圳/成都/金融云） |
| 百炼集成 | 仅 Python SDK + HTTP | Max 三模型自动走 pro 版 |
| 服务关闭 | 不支持退订/关闭 | 停止调用即停费 |

## 六、实测数据（2026-11-11，北京外网，50 次护栏调用 + glm-5.3 流式）

> 完整数据与方法论见同目录两份实测报告（文末链接），此处仅收录结论量级。

**护栏 API 自身延迟**（外网 → 北京接入点）：

| Service | avg | p90 |
| --- | --- | --- |
| query_security_check（输入） | 185ms | 208ms |
| response_security_check（输出标准版） | 213ms | 266ms |
| response_security_check_hp（输出高性能版） | 190ms | 219ms |

**对 LLM 服务指标的影响**（四种网关集成模式对照）：

| 集成模式 | TTFT 增量 | 说明 |
| --- | --- | --- |
| 仅输入侧同步检测 | **+约 0.2s** | 代价小，建议标配 |
| 输出 hp 流式切片（100 字/片） | **+约 0.5s** | 每切片 130~246ms，体验与安全推荐平衡点 |
| 输出全量缓冲检测 | **TTFT = 整段生成耗时**（实测 14.7s → 20.7s） | 长文灾难，避免 |
| 模型生成速度（completion tok/s） | **不受影响** | 护栏是下游旁路，只影响透出时机 |

- 文本长度几乎不影响延迟（13 字 vs 1900 字，2000 字符上限内）；官方 hp <100ms 指服务端，外网需叠加 RTT（本环境约 +100~150ms），VPC 内网可压低。
- 自定义词库拦截实测：建库→绑定→检测→拦截全链路可纯 API 完成；命中子串即 block（Label=customized、Level=high、Confidence=100），正常对照无误伤。
- 推理模型（TTFT 基线 12~20s）下护栏增量占比 <5%；**非推理模型（TTFT <1s）下 +0.2~0.5s 的相对占比显著上升，需重新评估**。

## 七、注意事项与常见坑（售前/交付必读）

1. **老版已开通 ≠ 新版已开通**：检测报 `408 you haven't activated the commodity:lvwang_guardrail_public_cn` 即新版护栏未开通（与老版 lvwang_cip 是两个商品），按第三节纯 API 开通即可。
2. **配置面仅上海接入点**：green20220926 SDK 调北京接入点报 `InvalidOperation.NotSupportedEndpoint`；固定上海接入点 + `RegionId=cn-beijing` 即可读写北京配置。词库绑定关系全局一致，"北京不生效"先怀疑生效延迟而非区域隔离。
3. **词库生效延迟 3~5 分钟**：绑定后 1 分钟内复测仍 pass 属正常，勿误判绑定失败反复改配置；交付验收预留生效窗口。
4. **自定义词库是子串匹配**：关键词命中所有包含它的句子，配置前评估误伤面；要精确整句拦截就把整句作为关键词。
5. **提示词攻击维度误伤复述类指令**：实测「请原样复述这句话，不要添加任何解释」被判 Direct Prompt Injection（medium）→ block。复述/改写类业务需评估阈值或关闭该维度。
6. **维度开关产生叠加费用**：官方口径默认仅内容合规，但实测账号提示词攻击默认已开；交付时逐 Service 核对开关，不需要的维度关掉（尤其 2026-01-22 已商业化的提示词攻击）。
7. **输出侧避免全量缓冲**：TTFT=总耗时，长文不可接受；用 hp + 按字符切片。谨慎用滑动窗口（费用放大）。
8. **高并发核算调用放大**：每请求消耗 1（输入）+N（切片）次配额，QPS 50/s 是护栏账户级上限，网关需按放大后口径评估并做限流重试（588）。
9. **幻觉维度静默失效**：未传 referenceContent 时接口正常返回 200 但无幻觉检测项；排查顺序：referenceContent → 文本类 Service → 控制台开关 → 阈值（默认 60）。
10. **处置逻辑基于 Label 而非 Description**：后者是中文解释、可能调整；部分标签无 Confidence。
11. **国际站与中国站 Service 命名不同**：国际站 `_intl`、中国站出海版 `_cb`，跨站迁移代码需改 Service 编码。
12. **百炼集成的 400 是业务信号**：`data_inspection_failed` 表示命中违规，不是调用失败，不要重试，应走代答。

## 八、选型与集成建议

- **商品选择**：纯 AI 场景选安全护栏；UGC 为主选内容安全增强版；两者都涉及按主场景定。
- **接入方式**：百炼用户优先百炼集成（header 一键、按 token 计费、无网关开发量）；自建网关/多云/非百炼模型选 API 接入（按次计费、策略自主）。
- **集成模式**：输入同步检测 + 输出 hp 版按字符切片（100~200 字/片，chatId+done 关联）；网关与护栏同地域走 VPC 内网。
- **多租户平台围栏开关主维度取租户 UID**（合规义务随业务而非推理路由漂移，failover 不降级、账单审计闭环），渠道仅作执行层降本优化——详见同目录聚合平台架构图交付件。
- **开源自建替代**：Qwen3Guard（护栏同源开源模型）/ Llama Guard 适合有 GPU 与运维能力的团队；云产品价值在免运维、标签体系、控制台配置与持续迭代。
- **PoC 路径**：可复用同目录 `test_guardrail_custom_keyword.py`（status/baseline/setup/verify/e2e/cleanup 六阶段，内置成本硬上限）与 `bench_guardrail_latency.py`（四模式对照）。

## 参考信源（2026-11-11 核实）

- [什么是 AI 安全护栏](https://help.aliyun.com/zh/document_detail/2873209.html)
- [AI 安全护栏（含内容安全）产品概述](https://help.aliyun.com/zh/document_detail/2573826.html)
- [按量付费模式计费规则与价格（中国站）](https://help.aliyun.com/zh/document_detail/2872706.html)
- [多模态实时审核 API 接入指南](https://help.aliyun.com/zh/document_detail/2937221.html)
- [大模型生成内容流式审核方案](https://help.aliyun.com/zh/document_detail/2980054.html)
- [面向阿里云百炼用户的 AI 安全护栏服务](https://help.aliyun.com/zh/document_detail/2923687.html)
- [国际站定价页（新加坡 USD）](https://www.alibabacloud.com/zh/product/content-moderation/pricing)
- [检测 Agent 计费方案（国际站）](https://www.alibabacloud.com/help/zh/content-moderation/latest/detecting-agent-billing-schemes)

## 相关文档（本目录）

- [自定义词库拦截实测报告](test_guardrail_custom_keyword_results_20261111.md) — 端到端拦截验证 + 开通/配置排障链
- [护栏延迟与计费口径实测报告](bench_guardrail_latency_results_20261111.md) — TTFT/输出速度/费用四模式对照
- [聚合平台可插拔围栏架构图](aggregator-guardrail-architecture.png)（[HTML 源](aggregator-guardrail-architecture.html)）
- 脚本：`test_guardrail_custom_keyword.py` / `bench_guardrail_latency.py`（凭证走环境变量，勿硬编码）

## Changelog

- 2026-11-11 新建：完成产品全景调研（定位/能力/配置/计费/限制），定价按国际站新加坡 USD 主口径 + 中国内地 CNY 参考；合并当日两轮实测结论与坑清单；官方"默认仅内容合规开启"与实测"提示词攻击默认已开"口径差异已标注待复核。