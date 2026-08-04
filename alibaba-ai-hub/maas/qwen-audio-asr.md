# Qwen-Audio-3.0-ASR 系列

> 最后更新: 2026-08-04
> 所属厂商: Alibaba (Alibaba Cloud)
> 产品类别: MaaS（AI 语音识别）
> 状态: Published

<!-- SUMMARY_START -->
**定位**: 百炼非实时语音识别中的 LLM-based ASR 产品线，引入 LLM 解码带来上下文语句理解、即时热词等能力，与 Fun-ASR（传统声学路线）并列在售
**当前主推**: qwen-audio-3.0-asr-flash（≤5 分钟同步）、qwen-audio-3.0-asr-flash-filetrans（≤12 小时异步）
**适用**: 中英混说办公口语、会议纪要、客服分析、重语义理解与领域适配的转写场景
**不适用**: 要求字对字忠实还原的场景（合规留痕、庭审、逐字字幕）——存在插入幻觉与语义展开，建议用 FunASR/Paraformer
<!-- SUMMARY_END -->

## 当前主推模型

| 模型 | 定位 | 音频上限 | 调用方式 | 特点 |
|------|------|----------|----------|------|
| qwen-audio-3.0-asr-flash | 🚩 短音频同步 | ≤5 分钟 / ≤10MB | 同步多模态 HTTP（不支持 SDK），支持 SSE 流式 | 即时热词（独享）、词级时间戳、URL 或 Base64 输入 |
| qwen-audio-3.0-asr-flash-filetrans | 长音频异步 | ≤12 小时 / ≤2GB | 异步任务（X-DashScope-Async，轮询/回调） | 仅接受公网 URL，任务完成后返回 transcription_url |

两模型均在北京、新加坡地域上线。官方选型建议：5 分钟内短音频用同步模型，超 5 分钟长音频用 filetrans 异步模型。

### qwen-audio-3.0-asr-flash
- 模型：qwen-audio-3.0-asr-flash
- 公司：Alibaba Cloud（百炼）
- 时间：[⚠️ 待补充]
- 尺寸：未公开
- 上下文：上下文增强支持携带 input_text/text 上下文消息，各最多 5 条、每轮总长 ≤400 字符，含音频的 user 消息必须置末
- 场景：≤5 分钟短音频转写、中英混说、需要流式反馈的场景
- 特点：即时热词（权重 [1,5]，50 为超级热词，仅本模型支持）、词级时间戳、Base64 Data URI 输入
- 定价：$0.000035/秒（按音频时长计费）

### qwen-audio-3.0-asr-flash-filetrans
- 模型：qwen-audio-3.0-asr-flash-filetrans
- 公司：Alibaba Cloud（百炼）
- 时间：[⚠️ 待补充]
- 尺寸：未公开
- 上下文：支持上下文增强
- 场景：长录音批量转写（会议、通话）
- 特点：异步任务 + transcription_url 结果下载（URL 默认 24 小时有效）
- 定价：[⚠️ 待补充]（以官方定价页为准）

## 核心能力与限制

### 核心能力

| 能力 | 说明 |
|------|------|
| LLM 解码 / 上下文语句理解 | 输出由声学与语言上下文联合决定，支持上下文增强注入对话历史/领域词表 |
| 即时热词 | vocabulary 键值对直接干预解码，权重 [1,5] 或 50（超级热词），仅 qwen-audio-3.0-asr-flash 支持 |
| 预编译热词 | vocabulary_id 词表，两模型均支持 |
| 词级时间戳 | 固定开启，output.sentence.words 含每词起止时间 |
| 多语种 | language_hints 最多 4 个生效，覆盖 27+ 语种 |
| 流式输出 | flash 同步模型支持 SSE 流式；filetrans 不支持 |
| 润色顺滑 | 官方标注"默认关闭，暂未开放"（识别同时清理语气词/口吃/自我纠正） |

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| flash 同步音频上限 | ≤5 分钟 / ≤10MB | 长音频请改用 filetrans |
| filetrans 音频上限 | ≤12 小时 / ≤2GB | 仅接受公网 URL |
| flash 不支持 SDK | 官方明确"该功能不支持SDK调用" | 需手工构造 HTTP 请求 |
| 调用端点差异 | flash 走 services/aigc/multimodal-generation/generation；filetrans 走 services/audio/asr/transcription | 两模型协议不同，不可混用 |
| 情感识别 | 非实时系列不支持 | 情感识别属 Qwen3-ASR-Flash 系列能力 |
| 上下文消息约束 | 各角色最多 5 条、总长 ≤400 字符 | 超出保留最近 5 条 / 末尾截断 |

## 定价概览

| 模型 | 单价 | 备注 |
|------|------|------|
| qwen-audio-3.0-asr-flash | $0.000035/秒 | 按音频时长计费 |
| qwen-audio-3.0-asr-flash-filetrans | [⚠️ 待补充] | 以官方定价页为准 |

> 定价来源：https://www.alibabacloud.com/help/en/model-studio/model-pricing ，核实日期：2026-08-04。

## 适用场景

### ✅ 适用

| 场景 | 推荐模型 | 说明 |
|------|----------|------|
| 中英混说办公口语转写 | flash / filetrans | 实测英文术语（align、schedule、sign-off）无降级 |
| 会议纪要 / 客服分析 | flash / filetrans | 重语义理解，配合即时热词 + 上下文增强压制幻觉 |
| 领域专有名词场景 | flash | 即时热词（如把 HC、BU head 加入词表权重 5/50）纠正语义展开 |

### ❌ 不适用

| 场景 | 不适用原因 | 替代方案 |
|------|-----------|----------|
| 字对字忠实转写（合规留痕、庭审、逐字字幕） | 存在插入幻觉与语义展开，还原度低于传统 ASR | FunASR / Paraformer |

### 🕳️ 实测踩坑记录（中英混说办公场景，2026-08-04）

| 案例 | 原音 | FunASR | Qwen-Audio-3.0-Flash | 错误类型 |
|------|------|--------|------|------|
| 1 | BU head | bu head（正确） | boohead（错误） | 英文专有短语声学误合 |
| 2 | 很难 catch up | 很难 catch up（精准） | 真的很难 catch up（多字） | 插入幻觉（语言先验在声学间隙填空） |
| 3 | HC | HC | headcount | 语义展开（缩写被还原为全称） |

结论：Qwen-Audio-3.0 系列上下文理解能力领先（LLM 架构），但字对字保真度仍需优化；幻觉类问题可通过即时热词 + 上下文增强缓解。

## 参考资料

- 百炼非实时语音识别用户指南：https://help.aliyun.com/zh/model-studio/non-realtime-speech-recognition-user-guide
- Qwen-Audio-3.0-ASR-Flash/Fun-ASR-Flash API 参考：https://help.aliyun.com/zh/model-studio/non-real-time-speech-recognition-for-fun-asr-flash
- 本地实测：cosyvoice_demo（北京节点 workspace 域名 + 标准 DashScope 端点验证）

## Changelog
| 日期 | 变更内容 |
|------|----------|
| 2026-08-04 | 补充 qwen-audio-3.0-asr-flash 定价 $0.000035/秒（用户确认，直接入库） |
| 2026-08-04 | 初始创建：基于 inbox/ai-knowledge-by-qoder-ai-native-agent-20260804.md 提炼，含官方口径与中英混说实测对比 |
