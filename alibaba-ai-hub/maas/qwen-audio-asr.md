# Qwen-Audio-3.1-ASR 系列

> 最后更新: 2026-11-11
> 所属厂商: Alibaba (Alibaba Cloud)
> 产品类别: MaaS（AI 语音识别）
> 状态: Published

<!-- SUMMARY_START -->
**定位**: 百炼 LLM-based ASR 产品线（3.1 代际），LLM 解码带来上下文语句理解、热词干预、原生转写润色与说话人分离，与 Fun-ASR（传统声学路线）、Qwen3-ASR（情感识别）并列在售
**当前主推**: qwen-audio-3.1-asr-flash（≤5 分钟同步）、qwen-audio-3.1-asr-flash-filetrans（≤12 小时异步）、qwen-audio-3.1-asr-flash-streaming（实时持续转写）、qwen-audio-3.1-asr-flash-message（输入法 / 语音消息）
**适用**: 多语种与方言转写、会议纪要、客服分析、中文古诗词 / 文言、多人对话分角色
**不适用**: 要求字对字忠实还原的场景（合规留痕、庭审、逐字字幕）——润色与语义展开倾向仍在，建议 FunASR / Paraformer；需要情感识别改用 qwen3-asr-flash
<!-- SUMMARY_END -->

## 当前主推模型

| 模型 | 定位 | 音频上限 | 调用方式 | 特点 |
|------|------|----------|----------|------|
| qwen-audio-3.1-asr-flash | 🚩 短音频同步 | ≤5 分钟 / ≤2GB | 同步多模态 HTTP（SSE 可选） | 热词 + Prompt 上下文、**说话人分离**、词级时间戳、原生转写润色、URL 或 Base64 |
| qwen-audio-3.1-asr-flash-filetrans | 长音频异步 | ≤12 小时 / ≤2GB（开说话人分离建议 ≤2h） | 异步任务（X-DashScope-Async，轮询/回调） | 仅接受公网 URL，返回结果下载 URL；热词、上下文、说话人分离 |
| qwen-audio-3.1-asr-flash-streaming | 实时持续转写 | 不限时长 | WebSocket 流式 | 会议 / 课堂边转写边出字，中间结果准确率优先 |
| qwen-audio-3.1-asr-flash-message | 实时短语音 | — | WebSocket 流式（16kHz） | 输入法 / 语音消息 / 企业业务，首字与整体延迟最低，即时热词 + 对话上下文 + 文本润色 |

四个变体均在北京（华北2）与新加坡（国际）双节点上线，定价按 Token 计费（见下节）。

官方选型口径（[语音识别选型页](https://help.aliyun.com/zh/model-studio/asr-model)）：短段语音输入选 flash-message，持续转写选 flash-streaming，录音文件转写选 flash-filetrans；需要热词 / Prompt 上下文 / 说话人分离一律推荐 3.1 系列。

> **3.0 代际（并售，非主推）**：qwen-audio-3.0-asr-flash / -filetrans / -streaming 仍在售且按"音频秒数"计费，可直接沿用存量代码；新项目与新报价一律以 3.1 为准。两者能力与计费口径差异见「与 3.0 代际的替换要点」。
> 相关产品线：语音合成见 [Qwen-Audio TTS](qwen-audio-tts.md)，实时双工对话见 [Qwen-Audio Realtime](qwen-audio-realtime.md)。

### qwen-audio-3.1-asr-flash
- 模型：qwen-audio-3.1-asr-flash
- 公司：Alibaba Cloud（百炼）
- 时间：2026-10 上线（官方模型页 / 用户指南 2026-10-29 起以 3.1 为示例）
- 尺寸：未公开
- 上下文：支持上下文增强（Prompt 注入对话历史 / 领域背景）；`input.messages` 中音频消息置末
- 场景：≤5 分钟短音频转写、多语种与方言、古诗词 / 文言、多人对话分角色
- 特点：热词（即时 / 预编译）、**说话人分离**（3.0-flash 不支持）、词级时间戳、原生转写润色、方言 ASR/AST 可控输出、标点预测与文本规范化、噪声鲁棒
- 定价：输入 $0.15/M Token、输出 $0.47/M Token（新加坡）；北京 输入 $0.113 / 输出 $0.382

### qwen-audio-3.1-asr-flash-filetrans
- 模型：qwen-audio-3.1-asr-flash-filetrans
- 公司：Alibaba Cloud（百炼）
- 特点：异步任务 + 结果文件下载；热词、Prompt 上下文、说话人分离（返回 `speaker_id`）、句级 / 词级时间戳固定开启
- 场景：长录音批量转写（会议、访谈、通话质检、内容生产）
- 定价：输入 $0.15/M Token、输出 $0.47/M Token（新加坡）；北京 $0.113 / $0.382

### qwen-audio-3.1-asr-flash-streaming
- 模型：qwen-audio-3.1-asr-flash-streaming
- 公司：Alibaba Cloud（百炼）
- 定位：端到端实时流式识别（WebSocket），不限音频时长；支持热词、Prompt 上下文、中英自由切换、方言 AST 可控输出
- 定价：输入 $0.93/M Token、输出 $0.70/M Token（新加坡）；北京 $0.848 / $0.636

### qwen-audio-3.1-asr-flash-message
- 模型：qwen-audio-3.1-asr-flash-message
- 公司：Alibaba Cloud（百炼）
- 定位：面向语音消息、输入法、企业业务优化的短段语音识别，16kHz 输入；一段语音结束后输出整理后的最终结果
- 特点：即时热词（`vocabulary`）、预编译热词（`vocabulary_id`）、对话上下文增强（`input.context`）
- 定价：输入 $0.93/M Token、输出 $0.70/M Token（新加坡）；北京 $0.848 / $0.636

## 核心能力与限制

### 核心能力

| 能力 | 说明 |
|------|------|
| LLM 解码 / 上下文语句理解 | 输出由声学与语言上下文联合决定，支持 Prompt 上下文注入对话历史与领域背景 |
| 热词 | 即时热词（`vocabulary` 带权重）与预编译热词（`vocabulary_id`）；flash-message 同样支持 |
| 说话人分离 | 3.1 代际新增（flash 用 `speaker_diarization_enabled`，filetrans 用 `diarization_enabled`），输出 `speaker_id`；仅单声道 |
| 词级时间戳 | 固定开启，`sentences[].words[]` 含 `begin_time` / `end_time` / `text` |
| 原生转写润色 | 3.1 新增：识别同时清理语气词、口吃、自我纠正 |
| 多语种 / 方言 | 中文七大方言体系（官话 / 吴 / 湘 / 赣 / 客 / 闽 / 粤）+ 20 余种地区官话口音；3.1-flash 较 3.0 新增土耳其语、波斯语、马拉地语等语种 |
| 方言 ASR/AST 可控输出 | 3.1 新增：可按需指定方言转写与方言→文本（AST）输出 |
| 中文古诗词 / 文言 | 3.1 针对韵律、节奏与文言表达优化 |
| 精度代际提升 | 据 Qwen-Audio-3.1-ASR 技术报告（arXiv 2610.28711），GigaSpeechBench 7 语种宏平均 CER 15.09%，相对 3.0 下降 32.9%（厂商自测口径） |

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| flash 音频上限 | ≤5 分钟 / ≤2GB | 长音频改用 filetrans |
| filetrans 音频上限 | ≤12 小时 / ≤2GB | 仅接受公网 URL；开说话人分离建议 ≤2 小时 |
| 说话人分离声道 | 仅单声道 | 多声道需先下混 |
| 情感识别 | 不支持 | 情感识别属 Qwen3-ASR 系列能力（qwen3-asr-flash / -filetrans / -realtime） |
| 响应结构（3.1 flash） | 不含 `choices` 字段 | 识别文本在 `output.text` 与 `output.sentence.text` |
| 时间戳稳定条件（3.1 flash） | 未开说话人分离时读 `words[i].fixed == true`；开分离读 `output.sentences` | 3.0 用 `output.sentence.sentence_end` 判断，迁移时需改判定 |
| 计费口径 | 输入 / 输出 Token 分别计费 | `usage` 返回输入、输出、总 Token 数；与 3.0 的按秒计费不同 |

## 定价概览

按输入 / 输出 Token 分别计费（官方定价页，2026-11-11 核实）：

| 模型 | 新加坡（国际） | 北京（华北2） |
|------|----------------|---------------|
| qwen-audio-3.1-asr-flash | 输入 $0.15 / 输出 $0.47 （每百万 Token） | 输入 $0.113 / 输出 $0.382 |
| qwen-audio-3.1-asr-flash-filetrans | 输入 $0.15 / 输出 $0.47 | 输入 $0.113 / 输出 $0.382 |
| qwen-audio-3.1-asr-flash-streaming | 输入 $0.93 / 输出 $0.70 | 输入 $0.848 / 输出 $0.636 |
| qwen-audio-3.1-asr-flash-message | 输入 $0.93 / 输出 $0.70 | 输入 $0.848 / 输出 $0.636 |

> 定价来源：https://www.alibabacloud.com/help/en/model-studio/model-pricing ，核实日期：2026-11-11。
> 报价注意：Token 单价不能直接换算成"每分钟 / 每小时转写价"，需按实测"每音频秒消耗的输入 + 输出 Token 数"折算；3.0 的 $0.000035/秒 口径不可与 3.1 混用。

## 与 3.0 代际的替换要点

| 维度 | qwen-audio-3.0-asr-flash | qwen-audio-3.1-asr-flash |
|------|--------------------------|--------------------------|
| 计费 | 按音频秒数（$0.000035/秒，新加坡） | 按输入 / 输出 Token |
| 说话人分离 | 不支持 | 支持（flash / filetrans） |
| 语种覆盖 | 30 种语言 + 7 大方言区 | 新增土耳其语、波斯语、马拉地语等，方言 AST 可控输出 |
| 润色 | 官方标注"默认关闭，暂未开放" | 原生转写润色 |
| 响应结构 | 含 `choices` | 不含 `choices`，文本在 `output.text` / `output.sentence.text` |
| 流式时间戳稳定 | 读 `output.sentence.sentence_end` | 读 `words[i].fixed`（未开说话人分离）或 `output.sentences`（开启后） |
| 音频大小上限 | ≤5 分钟 / ≤2GB（官方规格表） | ≤5 分钟 / ≤2GB |

> 存量代码迁移清单：① 计费与预算按 Token 重算；② 响应解析去 `choices`；③ 时间戳稳定判定改 `fixed`；④ 开说话人分离时改读 `sentences`；⑤ `usage` 落库 input/output/total tokens。

## 适用场景

### ✅ 适用

| 场景 | 推荐模型 | 说明 |
|------|----------|------|
| 中英混说办公口语转写 | flash / filetrans | 3.0 实测英文术语（align、schedule、sign-off）无降级 |
| 会议纪要 / 客服分析 | filetrans / flash | 重语义理解，配合热词 + 上下文增强压制幻觉；需要"谁说了什么"用 3.1 说话人分离 |
| 领域专有名词场景 | flash | 热词（HC、BU head 等）纠正语义展开 |
| 实时字幕 / 课堂转写 | streaming | 不限时长，中间结果准确率优先 |
| 输入法 / 语音消息 | message | 首字延迟优先，支持文本润色与对话上下文 |
| 多语种、方言、古诗词 / 文言 | 3.1 全系 | 3.1 代际的核心增量场景 |

### ❌ 不适用

| 场景 | 不适用原因 | 替代方案 |
|------|-----------|----------|
| 字对字忠实转写（合规留痕、庭审、逐字字幕） | 存在插入幻觉与语义展开（3.1 增强润色后倾向需复测） | FunASR / Paraformer |
| 需要情感识别 | Qwen-Audio-ASR 系列不支持 | qwen3-asr-flash / -filetrans / -realtime |

### 🕳️ 实测踩坑记录（3.0 代际，中英混说办公场景，2026-08-04）

| 案例 | 原音 | FunASR | Qwen-Audio-3.0-Flash | 错误类型 |
|------|------|--------|------|------|
| 1 | BU head | bu head（正确） | boohead（错误） | 英文专有短语声学误合 |
| 2 | 很难 catch up | 很难 catch up（精准） | 真的很难 catch up（多字） | 插入幻觉（语言先验在声学间隙填空） |
| 3 | HC | HC | headcount | 语义展开（缩写被还原为全称） |

结论：3.0 上下文理解能力领先（LLM 架构），但字对字保真度不佳；幻觉类问题可通过热词 + 上下文增强缓解。**以上数据属 3.0 代际，3.1 因新增原生润色需重新实测后方可对外引用。**

## 参考资料

- 语音识别选型页：https://help.aliyun.com/zh/model-studio/asr-model
- 非实时语音识别用户指南：https://help.aliyun.com/zh/model-studio/non-realtime-speech-recognition-user-guide
- Qwen-Audio-ASR HTTP API：https://help.aliyun.com/zh/model-studio/qwen-audio-asr-http-api
- 模型页：qwen-audio-3.1-asr-flash / -flash-filetrans / -flash-streaming / -flash-message（help.aliyun.com/zh/model-studio/qwen-audio-3-1-asr-flash*）
- 技术报告：Qwen-Audio-3.1-ASR Technical Report（arXiv 2610.28711）
- 本地实测：cosyvoice_demo（3.0 代际，北京节点 workspace 域名 + 标准 DashScope 端点）

## Changelog
| 日期 | 变更内容 |
|------|----------|
| 2026-11-11 | 代际切换：主推由 qwen-audio-3.0-asr-flash 系列切至 qwen-audio-3.1-asr-flash 四变体（flash / filetrans / streaming / message）；补全 3.1 规格（≤5min/≤2GB、≤12h/≤2GB、实时不限时长）、Token 计费表（新加坡 + 北京）、新增说话人分离 / 原生润色 / 方言 AST / 古诗词优化；修正 flash 音频上限旧口径（≤10MB → 官方 ≤2GB）；新增 3.0→3.1 替换要点与代码迁移清单；3.0 档降为并售过渡 |
| 2026-09-02 | 校验修复（knowledge-verifier 2026-09-02 报告）：填充 filetrans 定价（新加坡 $0.000035/秒、北京 $0.000032/秒）；新增 qwen-audio-3.0-asr-flash-streaming 条目（流式，新加坡 $0.00009/秒）——主推表 / 定价概览 / 独立小节同步 |
| 2026-10-30 | 补充 3.1 代际提示：官方已上架 qwen-audio-3.1-asr-flash / -flash-streaming / -flash-filetrans / -flash-messages（规格待补全，暂不切主推）；新增与 TTS / Realtime 产品线的交叉引用 |
| 2026-08-04 | 补充 qwen-audio-3.0-asr-flash 定价 $0.000035/秒（用户确认，直接入库） |
| 2026-08-04 | 初始创建：基于 inbox/ai-knowledge-by-qoder-ai-native-agent-20260804.md 提炼，含官方口径与中英混说实测对比 |
