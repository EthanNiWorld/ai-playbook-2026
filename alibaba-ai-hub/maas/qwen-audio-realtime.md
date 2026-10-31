# Qwen-Audio-Realtime

> 最后更新: 2026-10-30
> 所属厂商: Alibaba (Alibaba Cloud)
> 产品类别: MaaS（实时语音对话 / 双工语音）
> 状态: Published

<!-- SUMMARY_START -->
**定位**: 百炼「端到端实时双工语音对话」产品线——模型直接吃麦克风流式音频、直接吐语音与文本，听 / 理解 / 说由同一个模型完成，不再是 ASR → LLM → TTS 三段拼接
**当前主推**: qwen-audio-3.1-realtime-flash（低延迟主力）、qwen-audio-3.1-realtime-plus（高表现力），北京 + 新加坡双节点；上一代 qwen-audio-3.0-realtime-plus / -flash 仍在售
**适用**: 语音助手、智能客服、AI 伴侣、车载 / 耳机 / 电话等纯语音双工场景，尤其需要「嗯、啊不打断」的语义轮次检测与锁定主说话人的场景
**不适用**: 需要摄像头 / 画面理解的实时交互（用 Qwen3.8-Omni-Flash-Realtime）；只需把文本念出来（用 Qwen-Audio-TTS）；只需把录音转成文字（用 Qwen-Audio-ASR）
<!-- SUMMARY_END -->

## 当前主推模型

| 模型 | 定位 | 地域 | 特点 | 推出时间 |
|------|------|------|------|----------|
| **qwen-audio-3.1-realtime-flash** 🚩 | 低延迟主力（实时双工语音） | 北京 + 新加坡 | 音色覆盖 3.1-TTS 全量音色表；Function Calling 与联网搜索**可同时**启用；音频输出 $1.87/百万 tokens | 3.1 系列 2026-09 发布后上架（模型信息页 2026-10-09 可见） |
| **qwen-audio-3.1-realtime-plus** 🚩 | 高表现力 / 精品交互 | 北京 + 新加坡 | 音频输出 $24/百万 tokens（约 flash 的 12.8 倍）；FC 与联网搜索**不可同时**启用 | 同上 |
| qwen-audio-3.0-realtime-plus / -flash | 存量 | 北京 + 新加坡 | 默认音色 longanqian（无 v3.1 后缀）；11 个语种（缺泰 / 越 / 阿）；定价见官方定价页 [待补充] | [待核实] |

> 命名易混：本页是「双工对话」（输入音频 → 输出语音 + 文本）；`qwen-audio-3.1-tts-flash` 是「语音合成」（文本 → 语音），两者不可互相替代，详见 qwen-audio-tts.md。

### qwen-audio-3.1-realtime-flash
- 模型：qwen-audio-3.1-realtime-flash
- 公司：Alibaba Cloud（百炼）
- 时间：3.1 系列 2026-09 发布后上架（模型信息页 2026-10-09 可见；精确上线日 [待核实]）
- 地域：华北2（北京）+ 新加坡（须用对应地域的 API Key）
- 模态：输入文本 + 流式音频；输出文本 + 音频
- 上下文：上下文长度 262,144 tokens；最大输入 245,760；最大输出 16,384
- 音频历史：最多 50 轮、累计 300 秒（超出自动丢弃更早历史）；`max_history_turns` 默认 20、取值 1–50
- 交互模式：server_vad（声学 VAD）/ smart_turn / **smart_turn_v2（官方推荐）** / push-to-talk
- 说话人增强：smart_turn 系列下支持——传目标用户预录音频后锁定该说话人，屏蔽旁人声音与背景噪声
- 工具：Function Calling + 联网搜索（`enable_search`），**两者可同时启用**
- 音色：默认 longanqian_v3.1；可选 3.1-tts-plus / 3.1-tts-flash 音色表中的全部音色；支持声音复刻音色
- 语种：14 语种（中、英、日、韩、法、德、西、葡、俄、意、泰、越、印尼、阿）+ 22 种中文方言；输入源语种（`session.input_audio_transcription.language`）与输出语种（`session.output_audio.language`）可分别指定
- 计费：按文本输入 / 音频输入 / 文本输出 / 音频输出 tokens 计费；仅输出文本时按文本输出计价，输出音频时**只收音频输出费**，伴随文本不另收
- 限流：RPM 60、TPM 100,000；WebSocket 的 RPM 按建连次数计，无单独并发连接数限制

### qwen-audio-3.1-realtime-plus
- 模型：qwen-audio-3.1-realtime-plus
- 公司：Alibaba Cloud（百炼）
- 时间 / 地域 / 模态 / 上下文 / 音频历史 / 交互模式：与 3.1-flash 一致
- 差异点：高表现力档，音频输出单价显著更高；联网搜索**不能**与 Function Calling 同时启用
- 音色：默认 longanqian_v3.1，同款音色体系；支持声音复刻
- 计费：同口径 tokens 计量，但单价按 plus 档

### qwen-audio-3.0-realtime-plus / -flash（存量）
- 默认音色 longanqian；11 语种（德语、英语、西班牙语、法语、印尼语、意大利语、日语、韩语、葡萄牙语、俄语、中文）
- 交互模式与说话人增强说明与 3.1 同套（server_vad / smart_turn / smart_turn_v2 / push-to-talk）
- 新项目建议直接用 3.1 档；3.0 仅在存量兼容时保留

## 核心能力与限制

### 核心能力

| 能力 | 说明 |
|------|------|
| 端到端双工 | 同一模型完成「听 → 理解 → 说」，省略 ASR/LLM/TTS 三段拼接带来的首包叠加延迟与信息损失 |
| 语义轮次检测 | smart_turn / smart_turn_v2 融合声学与语义判断轮次边界，"嗯""啊"等无意义附和声不会打断对话；smart_turn_v2 进一步理解多人场景的交互意图 |
| 说话人增强 | 传入目标用户预录音频后，双工对话中精准锁定该说话人、忽略旁人声音与背景噪声（仅 smart_turn 系列模式） |
| 非有效轮次透传 | VAD 检测到语音但语义判定非有效轮次时，服务端不触发对话轮，而是把 ASR 结果以 `ambient_audio_transcription` 事件透传，且**不写入对话上下文** |
| 工具与联网 | Function Calling 自主调用外部工具；`enable_search` 联网搜索并可返回来源；3.1-flash 支持两者同时开 |
| 上下文管理 | 支持对话项创建 / 查询 / 删除，可注入历史上下文或清理无关对话项 |
| 声音复刻 | 创建音色时 `target_model` 填 realtime 型号，返回的 `voice_id` 填入 `voice` 参数即可用专属音色说话 |
| 高表现力语音 | 依据对话语境动态调整语气、节奏与情感；音色复用 3.1-TTS 音色库 |

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 不支持视频输入 | 仅文本 + 音频 | 需要画面 / 视觉问答的实时交互必须换 Qwen3.8-Omni-Flash-Realtime |
| 无思考模式 | 不支持 `enable_thinking` | 3.1 / 3.0 realtime 均无思考模式，需要推理链场景另配文本模型 |
| 音频历史窗口 | 50 轮 / 300 秒 | 超限自动丢弃最早历史；`max_history_turns` 默认 20 |
| 最大输出 | 16,384 tokens | 同代 Omni realtime 为 65,536，长回答场景需注意 |
| FC 与联网搜索互斥 | 仅 3.1-flash 可同时启用 | 3.1-plus 与 3.0 档二选一，售前配置时勿混写 |
| WebSocket 地址 | 必须使用绑定业务空间的地址 | 需替换 `{WorkspaceId}`，各地域 URL 不同，直接套公网通用地址会失败 |
| 音色与模型强绑定 | realtime 与 TTS 型号的音色表各自绑定 | 换模型需同步核对 voice 合法性；声音复刻的 `target_model` 也必须指向 realtime 型号 |
| 输出语种不保证 | `output_audio.language` 仅作用于 TTS | 会尽量让语音用目标语种，但不保证生效，也不改变回复文本的语种 |
| 打断处理 | `input_audio_buffer.speech_started` 后须清空本地播放缓冲 | 模型侧 `response.done` 返回 `status=cancelled`；客户端不清缓冲会出现语音叠加 |
| 音频分片 | 建议每片 100ms（16 kHz × 16 bit × 单声道 = 3200 字节） | 过小增加网络开销，过大损实时性 |

## 定价概览

USD / 每百万 tokens（国际站新加坡为主口径，北京作参考）：

| 模型 | 地域 | 文本输入 | 音频输入 | 文本输出 | 音频输出 |
|------|------|----------|----------|----------|----------|
| qwen-audio-3.1-realtime-flash | 新加坡 | $0.23 | $0.93 | $0.7 | $1.87 |
| qwen-audio-3.1-realtime-flash | 北京 | $0.212 | $0.848 | $0.636 | $1.696 |
| qwen-audio-3.1-realtime-plus | 新加坡 | $0.8 | $6.4 | $6.4 | $24 |
| qwen-audio-3.1-realtime-plus | 北京 | $0.688 | $5.501 | $5.501 | $20.628 |

- 计费规则：仅输出文本时按文本输出单价计；**同时输出文本和音频时，只对音频收输出费**，伴随文本不另收（与 Omni realtime「音频与对应文本分别计费」不同）
- 限流：两档均为 RPM 60 / TPM 100,000（北京、新加坡一致）
- 定价来源：官方模型信息页（qwen-audio-3-1-realtime-flash / qwen-audio-3-1-realtime-plus）与模型定价页；不含限时折扣，以控制台账单为准，核实日期：2026-10-30

## 适用场景

### ✅ 适用

| 场景 | 推荐模型 | 说明 |
|------|----------|------|
| 纯语音助手 / AI 伴侣 | qwen-audio-3.1-realtime-flash | 语义轮次检测让附和声不打断，对话节奏接近真人 |
| 智能客服 / 电话外呼 | qwen-audio-3.1-realtime-flash | 可同时开 FC + 联网搜索，边查边答 |
| 开放环境（车载、门店、公共空间） | qwen-audio-3.1-realtime-flash | 说话人增强锁定目标说话人，屏蔽旁人干扰 |
| 方言市场 / 出海多语种 | qwen-audio-3.1-realtime-flash | 22 种中文方言 + 14 语种，输入输出语种可分别指定 |
| 品牌音色对话（IP 分身 / 明星音色） | 3.1-realtime-flash 或 -plus | 声音复刻音色可直接用于对话输出 |
| 高表现力品牌交互 | qwen-audio-3.1-realtime-plus | 情感与语气表现优先、对成本不敏感的场景 |

### ❌ 不适用

| 场景 | 不适用原因 | 替代方案 |
|------|-----------|----------|
| 需要看到画面 / 视觉问答 / 直播分析 | 不支持视频与图像帧输入 | Qwen3.8-Omni-Flash-Realtime |
| 只要把长文本转成音频（有声书、播客） | 双工模型按轮对话，不适配整段朗读与多 voice 分角色 | qwen-audio-3.1-tts-plus / tts-next |
| 只要把录音转写成文字（会议、庭审） | 双工模型的 ASR 只服务于对话理解 | qwen-audio-3.0-asr-flash / fun-asr |
| 需要多人会议纪要 / 多声道采集 | 不支持多通道音频输入 | Qwen3.8-Omni-Flash-Realtime（WebSocket 支持 1/2/4 声道） |
| 需要长回答（>16K tokens 输出） | 最大输出 16,384 | Omni realtime（65,536）或文本模型 |

## 与 Qwen3.8-Omni-Flash-Realtime 的分工

官方全模态选型页已按场景切分，两条线**并列而非替代**：

| 官方场景描述 | 推荐模型 |
|---|---|
| 实时语音**/视频**对话：麦克风 + 摄像头（语音助手、智能客服、视觉问答、直播分析） | Qwen3.8-Omni-Flash-Realtime |
| 实时语音对话（**语义 VAD**）：端到端语音交互，smart_turn / smart_turn_v2，附和声不打断，支持 FC | Qwen-Audio（本页） |

| 维度 | qwen-audio-3.1-realtime-flash | qwen3.8-omni-flash-realtime |
|---|---|---|
| 输入模态 | 文本 + 音频 | 文本 + 流式音频 + **视频（连续图像帧）** |
| 多通道音频 | 不支持 | WebSocket 支持 1 / 2 / 4 声道 |
| 输出计费 | 输出音频时**只收音频输出费**，文本不另收 | 音频与对应文本**分别计费** |
| 上下文 / 最大输出 | 262,144 / 16,384 | 输入总数 196,608 / **65,536** |
| 历史窗口 | 音频 50 轮 / 300 秒 | 音频 100 轮 / 600 秒 + 视频 50 轮 / 240 秒 |
| 轮次检测 | server_vad / **smart_turn / smart_turn_v2** / push-to-talk | server_vad / semantic_vad 等 |
| 说话人增强 | 支持 | 文档未列 |
| 工具生态 | FC + 联网搜索 + 对话上下文管理 | FC + **远程 MCP** + 联网搜索 |
| 默认音色 | longanqian_v3.1 | Tina |
| 语种 / 方言 | 14 语种 + 22 中文方言 | 113 种输入语言 / 方言 |
| 限流 | 60 RPM / 100,000 TPM | 60 RPM / **2,000,000 TPM** |
| 价格（新加坡） | 0.23 / 0.93 / 0.7 / 1.87 | **逐项相同** |

**售前一句话**：只看/听人说话、要把"谁在说、什么时候该接话"做准 → Qwen-Audio Realtime；要"看见"（摄像头、屏幕共享、直播画面、多声道会议）+ 要 MCP 生态 → Omni-Flash-Realtime。两者价格相同，差异全在模态与对话体验细节。

## 参考资料

- qwen-audio-3.1-realtime-flash 模型信息页：https://www.alibabacloud.com/help/zh/model-studio/qwen-audio-3-1-realtime-flash
- qwen-audio-3.1-realtime-plus 模型信息页：https://www.alibabacloud.com/help/zh/model-studio/qwen-audio-3-1-realtime-plus
- Qwen-Audio 实时语音对话指南（交互模式 / 说话人增强 / 事件）：https://www.alibabacloud.com/help/zh/model-studio/qwen-audio-realtime-user-guides
- Qwen-Omni-Realtime 指南（协议与 WebRTC 说明）：https://help.aliyun.com/zh/model-studio/realtime
- qwen3.8-omni-flash-realtime 模型信息页：https://www.alibabacloud.com/help/zh/model-studio/qwen3-8-omni-flash-realtime
- 全模态模型选型（Qwen-Audio 与 Omni 的场景切分）：https://help.aliyun.com/zh/model-studio/omni
- Qwen-Audio-TTS 音色列表（realtime 复用该音色表）：https://help.aliyun.com/zh/model-studio/qwen-audio-tts-voice-list
- 百炼模型定价页：https://help.aliyun.com/zh/model-studio/model-pricing

## Changelog
| 日期 | 变更内容 |
|------|----------|
| 2026-10-30 | 初始创建：补录 qwen-audio-3.1-realtime-flash / -plus 与 3.0 存量档；含规格、双节点定价（国际站 USD 口径）、交互模式与说话人增强、能力限制，以及与 Qwen3.8-Omni-Flash-Realtime 的官方场景切分与逐项对比（核实日期 2026-10-30） |
