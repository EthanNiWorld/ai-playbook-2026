# Qwen-Audio-TTS

> 最后更新: 2026-10-23
> 所属厂商: Alibaba (Alibaba Cloud)
> 产品类别: MaaS（AI 语音合成 / 音频生成）
> 状态: Published

<!-- SUMMARY_START -->
**定位**: 百炼平台当前售前主推的语音产品线，flash / plus 为纯 TTS，具备声音复刻、声音设计、free-style 指令控制与细粒度标签控制能力；3.1 起新增 Next 档——**音频生成（AudioGen）模型而非纯 TTS**，一次生成人声 + 音效 + 环境音的完整音频场景，同时兼容常规 TTS 用法（含多人 voice 播客/对谈）
**当前主推**: qwen-audio-3.1-tts-flash（实时交互）、qwen-audio-3.1-tts-plus（精品音色 / 内容制作）、qwen-audio-3.1-tts-next（音频生成，兼做单人朗读与多人播客）三档，均已在**北京 + 新加坡**双节点上架
**适用**: 实时语音助手、智能客服、多语种/方言内容、有声书、影视配音、品牌声音、多人播客/对谈（Next 多 voice 分角色）、有声剧等带音效的场景音频
**不适用**: 需要 500+ 复刻基础音色的场景（3.1 无基础音色库，仍用 3.0 系列）；需要长音频一次性生成（Next 非流式，单请求上限 120 秒）
<!-- SUMMARY_END -->

## 当前主推模型

| 模型 | 定位 | 地域 | 特点 | 推出时间 |
|------|------|------|------|----------|
| **qwen-audio-3.1-tts-flash** 🚩 | 实时交互 | 北京 + 新加坡 | 74 个系统音色（新加坡可用 4 多语种/方言 + 15 精品英文）、复刻鲁棒性增强 | 2026-09-18（北京）；3.1 系列 2026-09 发布后国际站上架 |
| **qwen-audio-3.1-tts-plus** 🚩 | 精品音色 / 内容制作 | 北京 + 新加坡 | 4 个 v3.1 旗舰系统音色、指令控制 + 标签控制、复刻鲁棒性增强 | 2026-09 系列发布 |
| **qwen-audio-3.1-tts-next** 🚩 | 音频生成（AudioGen，兼做 TTS） | 北京 + 新加坡 | text_prompt + 最多 3 段参考音频（@voice1~3 分角色），一次生成人声 + 音效 + 环境音；也能做单人朗读 / 多人播客；非流式 | 2026-09 系列发布（模型页 2026-10-11 更新） |
| qwen-audio-3.0-tts-plus | 高品质生成（有基础音色库需求时） | 北京 + 新加坡 | 2 个系统音色 + 500 余个复刻基础音色、AA TTS 榜曾居第 2（Elo 1260） | 2026-07 |
| qwen-audio-3.0-tts-flash | 实时交互（存量） | 北京 + 新加坡 | 12 个系统音色（v3.6 系列）+ 500 余个复刻基础音色 | 2026-07 |

### qwen-audio-3.1-tts-flash
- 模型：qwen-audio-3.1-tts-flash
- 公司：Alibaba Cloud（百炼）
- 时间：2026-09-18 上线（北京）；国际站（新加坡）已上架
- 地域：北京 + 新加坡
- 音色：74 个系统音色（4 多语种方言 + 28 精品中文 + 15 精品英文 + 27 其他场景音色），如 longanhuan_v3.1、longanlingxin_v3.1、longanfengyue_v3.1、xunanchuan_v3.1
- 音色地域差异：新加坡仅可用 4 个多语种/方言音色 + 15 个精品英文音色；精品中文与其余场景音色仅北京可用（跨地域调用报 500 InternalError.Algo）
- 语言：4 个音色组原生支持 8 种方言（上海、广东、东北、重庆、陕西、云南、宁波、甘肃）+ 8 种外语（日语、韩语、法语、德语、葡萄牙语、意大利语、越南语、印尼语）
- 场景：实时语音助手、智能客服、实时对话、多语种 / 方言内容
- 特点：声音复刻对含噪声、混响的参考音频鲁棒性更强；支持控制台「模型体验」在线试听
- 计费：按输入 + 输出 tokens 计费（接口同时返回 characters 仅供参考）

### qwen-audio-3.1-tts-plus
- 模型：qwen-audio-3.1-tts-plus
- 公司：Alibaba Cloud（百炼）
- 时间：2026-09 随 Qwen-Audio-3.1 系列发布
- 地域：北京 + 新加坡
- 音色：4 个 v3.1 旗舰系统音色（longanlingxin_v3.1 / xunanchuan_v3.1 / longanhuan_v3.1 / longanfengyue_v3.1）；无 3.0 系列的 500+ 复刻基础音色库
- 场景：精品音色与内容制作（品牌声音、有声内容、影视配音、角色演绎）
- 特点：同时支持 free-style 指令控制与细粒度标签控制，情绪/语气/角色/语速/音量可调；声音复刻对含噪声、混响的参考音频更鲁棒
- 计费：按字符计费

### qwen-audio-3.1-tts-next
- 模型：qwen-audio-3.1-tts-next
- 公司：Alibaba Cloud（百炼）
- 时间：2026-09 随 Qwen-Audio-3.1 系列发布
- 地域：北京 + 新加坡
- 形态：**音频生成（AudioGen）模型，不是纯 TTS**——围绕文本与参考音频生成完整音频场景，人声、音效、环境音可一次产出；同时**保留了 TTS 能力**：只写台词、不带音效描述时即为普通语音合成，故「音频生成」是定位、不是能力上限
- 多人 voice：最多 3 段参考音频分别以 @voice1 / @voice2 / @voice3 指代，每个 voice 可绑定不同说话人 → 天然支持双人 / 三人对谈，用于播客、访谈、多角色有声剧
- 输入：`text_prompt`（≤3000 字符）+ 最多 3 段参考音频（每段 ≤30 秒 / ≤10MB，格式 WAV/MP3/OGG Opus，URL 或 Base64）；**无 voice / instruction 参数**（音色不由预置音色 ID 指定，而由参考音频决定），表演方式写进 prompt
- 输出：非流式；WAV / MP3 / PCM；单请求最长 120 秒（播客类 240 秒）
- 语言：中文、英文
- 场景：播客/对谈（多人 voice 分角色）、有声剧、带环境音/音效的广告与游戏配音、多角色对话，以及需要成品音频直接输出的单人朗读
- 计费：按输入 + 输出 tokens 计费

### qwen-audio-3.0-tts-plus
- 模型：qwen-audio-3.0-tts-plus
- 公司：Alibaba Cloud（百炼）
- 时间：2026-07（官方上线新闻 2026-07-19）
- 地域：北京 + 新加坡
- 音色：2 个系统音色 + 500 余个复刻基础音色
- 场景：高品质内容制作（有声书、影视配音、品牌声音设计、高品质语音服务）
- 特点：更强调合成效果与细节表现；Artificial Analysis TTS 榜曾居第 2（Elo 1260）；基础音色库仍是 3.1 的差异化补充
- 计费：按字符计费

### qwen-audio-3.0-tts-flash
- 模型：qwen-audio-3.0-tts-flash
- 公司：Alibaba Cloud（百炼）
- 时间：2026-07（官方上线新闻 2026-07-19）
- 地域：北京 + 新加坡
- 音色：12 个系统音色（v3.6 系列）+ 500 余个复刻基础音色
- 场景：实时交互（存量场景；新项目建议直接用 3.1-flash）
- 特点：按字符计费，便于与 3.0-plus 口径对齐
- 计费：按字符计费

## 核心能力与限制

### 核心能力

| 能力 | 说明 |
|------|------|
| 声音复刻 | 从参考音频克隆音色；3.1-flash 对含噪声、混响的参考音频鲁棒性更强 |
| 声音设计 | 从文字描述创建音色（3.1-flash / 3.1-plus / 3.0-plus / 3.0-flash 均支持） |
| 指令控制与标签控制 | free-style 指令遵循 + 细粒度标签控制，灵活控制情绪、语气、角色、语速、音量等表达方式 |
| 多语种与方言 | 复刻音色支持更广语种；3.1 起 4 个系统音色组原生支持 8 方言 + 8 外语，"选音色即用" |
| 流式合成 | 支持流式语音合成；WebSocket（实时）+ HTTP（非实时）双协议，同一模型名同时支持两种协议 |
| 音频创作（3.1 新增） | Next 为 AudioGen 模型：围绕文本与参考音频生成完整音频场景，人声、音效、环境音可一次产出，支持 @voice1~3 指代参考音频 |
| 情绪与非语言标签 | 3.1-flash / 3.1-plus 及 3.0 系列支持在 text 内直接写控制标签（[excited] [crying] [whispering] 等）与非语言标签（[laughing] [gasp] [sighing] [clears throat] 等），无需额外参数 |
| 控制台在线试听 | "模型体验"：3.1-flash 支持；3.1-plus / 3.0 系列不支持（官方标注 Model playground 不支持） |

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 3.1 音色地域差异 | flash：新加坡仅 4 多语种/方言 + 15 精品英文音色；plus：4 个旗舰音色双节点可用 | 精品中文与其他场景音色仅北京；跨地域调用报 500 InternalError.Algo（而非 InvalidParameter，排障时勿误判为服务故障） |
| 音色与模型强绑定 | 不可混用 | 换模型必须同步替换 voice，否则报 InvalidParameter |
| 3.1 基础音色库 | 暂无 | 500+ 复刻基础音色仍属 3.0-plus / 3.0-flash |
| Next 无 voice / instruction 参数 | 音色改由参考音频决定（@voice1~3，最多 3 人） | 表演方式写进 text_prompt；非流式；≤3000 字符；单请求 ≤120 秒（播客 ≤240 秒）。注意：无 voice 参数 ≠ 不能做 TTS，也 ≠ 只支持单人 |
| 限流 | RPM 180（北京 / 新加坡一致） | 3.0 与 3.1 各档数值相同 |
| 计费口径不一 | flash / next 按 tokens；plus 与 3.0 系列按字符 | 报价与成本测算时不可直接按单价横向比较 |
| 官方推荐位 | 选型页推荐表以官方页面实时口径为准 | 3.1 三档已发布，推荐位排序可能滞后，售前引用前重查 tts-model 选型页 |
| 官方技术披露 | 未发布技术报告 | 模型架构细节未披露 |

## 定价概览

| 模型 | 计费维度 | 新加坡 | 北京 |
|------|----------|--------|------|
| qwen-audio-3.1-tts-flash | 输入 / 输出 tokens（每百万） | $0.23 / $1.87 | $0.212 / $1.696 |
| qwen-audio-3.1-tts-plus | 每万字符 | $0.30 | $0.20 |
| qwen-audio-3.1-tts-next | 输入 / 输出 tokens（每百万） | $0.93 / $1.87 | $0.848 / $1.696 |
| qwen-audio-3.0-tts-plus | 每万字符 | $0.20 | $0.19253 |
| qwen-audio-3.0-tts-flash | 每万字符 | $0.15 | $0.137521 |

> 定价来源：各模型国际站页面（qwen-audio-3-1-tts-flash / 3-1-tts-plus / 3-1-tts-next / 3-0-tts-plus / 3-0-tts-flash）与 https://help.aliyun.com/zh/model-studio/model-pricing；不含限时折扣，以控制台账单为准，核实日期：2026-10-23。

## 适用场景

### ✅ 适用

| 场景 | 推荐模型 | 说明 |
|------|----------|------|
| 实时交互（语音助手/智能客服/实时对话） | qwen-audio-3.1-tts-flash（北京 + 新加坡） | 面向实时交互优化；新加坡需选多语种/方言或精品英文音色 |
| 多语种 / 方言内容 | qwen-audio-3.1-tts-flash | 4 个系统音色组原生支持 8 方言 + 8 外语，选音色即用（双节点均可用） |
| 高品质内容制作 | qwen-audio-3.1-tts-plus | 有声书、影视配音、品牌声音；需 500+ 基础音色库时退回 3.0-plus |
| 低质录音音色复刻 | qwen-audio-3.1-tts-flash / -plus | 3.1 对含噪声、混响的参考音频鲁棒性更强 |
| 播客 / 有声剧 / 带音效场景 | qwen-audio-3.1-tts-next | AudioGen：人声 + 音效 + 环境音一次生成；@voice1~3 分别定声，支持双人/三人对谈 |
| 出海 / 新加坡节点 | 3.1 三档均可直接使用 | 不再需要为出海退回 3.0 系列 |

### ❌ 不适用

| 场景 | 不适用原因 | 替代方案 |
|------|-----------|----------|
| 需要 500+ 复刻基础音色 | 3.1 无基础音色库 | qwen-audio-3.0-tts-plus / 3.0-tts-flash |
| 单次生成长音频（>120 秒非播客、>240 秒播客） | Next 单请求时长上限 | 分段生成后用音频工具拼接 |
| 需要极低首包延迟的流式交互 | Next 为非流式（一次性返回完整音频） | qwen-audio-3.1-tts-flash（支持流式） |
| 新加坡节点使用 flash 精品中文音色 | 该批音色仅北京可用，跨地域报 500 InternalError.Algo | 改用 SG 可用的多语种/方言或精品英文音色 |

## 版本演进与售前替代建议

### 3.1 版本升级要点（vs 3.0-flash）

1. **音色体系全面换代（最大差异）**：74 个 v3.1 系统音色 vs 12 个 v3.6 音色；音色与模型强绑定、不能混用
2. **多语种与方言音色（系列首次）**：4 个音色组原生支持 8 种方言 + 8 种外语，此前方言/多语种需通过指令控制设置；精品英文音色细分英式/美式口音
3. **声音复刻鲁棒性增强**：官方表述聚焦为"在声音复刻场景中，对含有噪声、混响的参考音频具有更强的鲁棒性"
4. **档位补齐**：3.1 从单一 flash 扩展为 flash / plus / next 三档，并同步上架国际站（新加坡）；3.0 不再承担“出海唯一选择”角色
5. **其他**：新增控制台「模型体验」在线试听；限流统一按 RPM 180 口径

### 技术亮点与独创性分级

- 🔧 **组合创新**：多语种/方言能力从"复刻音色 + 指令控制"下沉为原生系统音色；系统音色矩阵扩展至 74 个，覆盖广告、有声书、客服、新闻播报、社交陪伴、儿童等场景
- ⚙️ **工程优化**：声音复刻对噪声/混响参考音频的鲁棒性提升
- 📋 **跟进对齐**：原生多语言系统音色对齐 MiniMax（40+ 语言）/ ElevenLabs（29 语言）等多语言 TTS 竞品
- 无 🌟 首创级技术公开；官方未发布技术报告

### 成本归因

- 3.1-flash / next 改用 tokens 计费，与 3.0 的字符计费不可直接单价对比；按实测样本（251 字符 ≈ 输入 133 + 输出 332 tokens）折算，3.1-flash 每万字符合成成本约 $0.026，低于 3.0-flash 新加坡 $0.15/万字符的列表价 → 属定价策略降本（促销属性、可回调），非架构内禀降本
- 3.1-plus 新加坡 $0.30/万字符，仍高于两个 flash 档，对位精品内容制作

### 迁移注意

- flash / plus 的 API 协议与 3.0 完全兼容（HTTP / WebSocket 同一端点，改 model 参数即可），但 voice 必须同步替换为 v3.1 音色（如 longanhuan_v3.6 → longanhuan_v3.1），长期使用旧音色将报错 InvalidParameter
- next 与 flash / plus 任务范式不同（音频生成，兼容 TTS 用法）：参数从 `text` / `voice` 改为 `text_prompt`（+ 可选 `references` 参考音频，用 @voice1~3 引用），请求体无法直接迁移；多人场景靠多段 references 分角色

### 售前替代建议

| 客户场景 | 建议 |
|----------|------|
| 国内新项目（实时交互 / 多语种 / 方言） | qwen-audio-3.1-tts-flash 直接替代 3.0-flash，首选 |
| 国际站（新加坡）客户 | 直接用 3.1 三档（flash / plus / next 均已上架）；注意 flash 的精品中文音色仍仅北京可用 |
| 高品质内容制作（有声书 / 影视配音 / 品牌声音） | qwen-audio-3.1-tts-plus；需 500+ 基础音色库或需 A/B 对比时再评估 3.0-plus |
| 播客 / 有声剧 / 需要环境音与音效 | qwen-audio-3.1-tts-next（AudioGen）单一请求即可生成完整音频场景；多说话人对谈用 @voice1~3 分角色 |
| 存量 3.0 项目 | 无强制迁移；仅在需要 3.1 音色体系或新增新加坡节点时迁移 |

## 节点可用性实测（2026-10-23）

针对新加坡节点三档 3.1 模型的实测验证（脚本与原始数据均在 `alibaba-ai-hub/maas/maas-solution-and-api-sample/`）：

| 验证项 | 结果 |
|--------|------|
| 模型可用性 | flash / plus / next 均 HTTP 200，17 次调用（含 2 次 SSE 流式）全部成功 |
| 非流式请求耗时 | flash 2.35~2.87s；plus 5.72~7.24s；next 23~50s（与生成长度正相关） |
| 流式首包（SSE） | flash 首个音频块 **0.71s**、plus **0.84s**，均 <1s；差异主要在生成吞吐：全量完成 flash 2.86s vs plus 6.65s → flash 的“实时”优势体现在持续合成速度而非首包 |
| plus 音色 | 4 个 v3.1 旗舰音色（longanlingxin / xunanchuan / longanhuan / longanfengyue）新加坡均可用 |
| flash 音色地域限制 | 多语种/方言 4 个 + Emily_v3.1 可用；精品中文（如 yuxiaoyun_v3.1）与其他场景音色（如 longanyuanfei_v3.1）报 500 InternalError.Algo |
| next 提示词写法 | 同一台词用英文方括号标签（[laughing][gasp][crying]）两轮实测均超长：142s（上报 90s）/ 85s（上报 52s）；改用自然语言描述表演层次仅 20~23s → next 建议用自然语言而非标签 |
| 标签订阅 | flash / plus 接受 [laughing] / [gasp] / [crying] 等英文标签（写在 text 内），也接受中文括号表演提示 |

- 测试脚本：`alibaba-ai-hub/maas/maas-solution-and-api-sample/test_qwen_audio_31_tts_sgp.py`
- 测试报告：`alibaba-ai-hub/maas/maas-solution-and-api-sample/test_qwen_audio_31_tts_sgp_results_20261023.md`

## 参考资料

- qwen-audio-3.1-tts-flash 模型页：https://help.aliyun.com/zh/model-studio/qwen-audio-3-1-tts-flash
- qwen-audio-3.1-tts-plus 模型页：https://www.alibabacloud.com/help/en/model-studio/qwen-audio-3-1-tts-plus
- qwen-audio-3.1-tts-next 模型页：https://www.alibabacloud.com/help/en/model-studio/qwen-audio-3-1-tts-next
- 音频生成（示例与提示词指南）：https://www.alibabacloud.com/help/en/model-studio/audio-generation
- 音频生成 API（next 参数）：https://www.alibabacloud.com/help/en/model-studio/audio-generation-api
- Qwen-Audio-TTS HTTP API：https://www.alibabacloud.com/help/en/model-studio/qwen-audio-tts-http-api
- 非实时语音合成指南（标签/指令/地域）：https://www.alibabacloud.com/help/en/model-studio/non-realtime-tts-user-guide
- qwen-audio-3.0-tts-flash 模型页：https://help.aliyun.com/zh/model-studio/qwen-audio-3-0-tts-flash
- qwen-audio-3.0-tts-plus 模型页：https://help.aliyun.com/zh/model-studio/qwen-audio-3-0-tts-plus
- 百炼模型定价页：https://help.aliyun.com/zh/model-studio/model-pricing
- Qwen-Audio-TTS 音色列表：https://help.aliyun.com/zh/model-studio/qwen-audio-tts-voice-list
- TTS 模型选型页：https://help.aliyun.com/zh/model-studio/tts-model/
- 实时语音合成指南（地域/指令/方言规则）：https://help.aliyun.com/zh/model-studio/realtime-tts-user-guide
- 语音合成模型列表：https://help.aliyun.com/zh/model-studio/model-list-speech-synthesis/
- Qwen-Audio-3.0-TTS 上线新闻（2026-07-19）：https://www.aliyun.com/product/news/29864
- Artificial Analysis TTS 榜单：https://artificialanalysis.ai/text-to-speech/leaderboard/provider-voice

## Changelog
| 日期 | 变更内容 |
|------|----------|
| 2026-09-20 | 初始创建：基于 inbox/ai-knowledge-by-qoder-ai-native-agent-20260920.md 提炼（qwen-audio-3.1-tts-flash 于 2026-09-18 上线；含 3.1 vs 3.0 版本对比、独创性分级与售前替代建议） |
| 2026-09-20 | 移除全文「免费额度」信息（用户规范：材料不再考虑免费额度，价值低属噪音） |
| 2026-10-23 | 修正地域与档位口径：3.1 已扩为 flash / plus / next 三档并均上架新加坡（删除“3.1-flash 仅北京”“3.1 无 plus 档”旧结论）；新增 Next 的 AudioGen 参数范式与时长/字符上限；定价改为国际站 USD 口径并补全三档与 3.0 双档；补充新加坡节点音色地域差异（跨地域报 500 InternalError.Algo）与 2026-10-23 实测数据 |
| 2026-10-23 | 实测方法补充：新增 SSE 流式首包延迟测试（flash 0.71s / plus 0.84s），记录“首包相近、plus 慢在生成吞吐”的结论 |
| 2026-10-23 | 修正 Next 定位口径：明确其为音频生成（AudioGen）模型而非纯 TTS，但保留 TTS 用法；补充多人 voice 能力（@voice1~3 分别定声，可做双人/三人播客、对谈、多角色有声剧），并澄清“无 voice 参数 ≠ 不能做 TTS / 只支持单人” |
