# Qwen-Audio-TTS

> 最后更新: 2026-09-20
> 所属厂商: Alibaba (Alibaba Cloud)
> 产品类别: MaaS（AI 语音合成）
> 状态: Published

<!-- SUMMARY_START -->
**定位**: 百炼平台当前售前主推的语音合成（TTS）产品线，具备声音复刻、声音设计、free-style 指令控制与细粒度标签控制能力
**当前主推**: 北京节点 qwen-audio-3.1-tts-flash（2026-09-18 上线）；国际站（新加坡）及高品质场景 qwen-audio-3.0-tts-plus、qwen-audio-3.0-tts-flash
**适用**: 实时语音助手、智能客服、多语种/方言内容、有声书、影视配音、品牌声音、低质录音音色复刻
**不适用**: 新加坡节点部署 3.1-flash（未上架，国际站请用 3.0 系列）；高品质场景选用 3.1（暂无 plus 档）
<!-- SUMMARY_END -->

## 当前主推模型

| 模型 | 定位 | 地域 | 特点 | 推出时间 |
|------|------|------|------|----------|
| **qwen-audio-3.1-tts-flash** 🚩 | 实时交互（北京节点新主推） | 仅北京 | 74 个系统音色（含多语种/方言）、复刻鲁棒性增强 | 2026-09-18 上线 |
| qwen-audio-3.0-tts-plus | 高品质生成（国际站/专业场景） | 北京 + 新加坡 | 指令控制 / 声音复刻、500+ 复刻基础音色库、AA TTS 榜曾居第 2（Elo 1260） | 2026-07 |
| qwen-audio-3.0-tts-flash | 实时交互（国际站） | 北京 + 新加坡 | 12 个系统音色（v3.6 系列）、与 3.1-flash 同价 | 2026-07 |

### qwen-audio-3.1-tts-flash
- 模型：qwen-audio-3.1-tts-flash
- 公司：Alibaba Cloud（百炼）
- 时间：2026-09-18 上线
- 地域：仅华北2（北京）
- 音色：74 个系统音色（4 多语种方言 + 28 精品中文 + 15 精品英文 + 27 其他场景音色），如 longanhuan_v3.1、longanlingxin_v3.1、longanfengyue_v3.1、xunanchuan
- 语言：4 个音色组原生支持 8 种方言（上海、广东、东北、重庆、陕西、云南、宁波、甘肃）+ 8 种外语（日语、韩语、法语、德语、葡萄牙语、意大利语、越南语、印尼语）
- 场景：实时语音助手、智能客服、实时对话、多语种 / 方言内容
- 特点：声音复刻对含噪声、混响的参考音频鲁棒性更强；支持控制台"模型体验"在线试听
- 定价：1 元/万字符

### qwen-audio-3.0-tts-plus
- 模型：qwen-audio-3.0-tts-plus
- 公司：Alibaba Cloud（百炼）
- 时间：2026-07（官方上线新闻 2026-07-19）
- 地域：北京 + 新加坡
- 音色：2 个系统音色 + 500 余个复刻基础音色
- 场景：高品质内容制作（有声书、影视配音、品牌声音设计、高品质语音服务）
- 特点：更强调合成效果与细节表现；Artificial Analysis TTS 榜曾居第 2（Elo 1260）
- 定价：北京 1.4 元/万字符；新加坡 1.49884 元/万字符

### qwen-audio-3.0-tts-flash
- 模型：qwen-audio-3.0-tts-flash
- 公司：Alibaba Cloud（百炼）
- 时间：2026-07（官方上线新闻 2026-07-19）
- 地域：北京 + 新加坡
- 音色：12 个系统音色（v3.6 系列）+ 500 余个复刻基础音色
- 场景：实时交互（国际站 3.1-flash 缺失时的对应版本）
- 特点：与 3.1-flash 同价（1 元/万字符）；国际站可用
- 定价：北京 1 元/万字符；新加坡 1.12413 元/万字符

## 核心能力与限制

### 核心能力

| 能力 | 说明 |
|------|------|
| 声音复刻 | 从参考音频克隆音色；3.1-flash 对含噪声、混响的参考音频鲁棒性更强 |
| 声音设计 | 从文字描述创建音色（3.1-flash / 3.0-plus / 3.0-flash 均支持） |
| 指令控制与标签控制 | free-style 指令遵循 + 细粒度标签控制，灵活控制情绪、语气、角色、语速、音量等表达方式 |
| 多语种与方言 | 复刻音色支持更广语种；3.1 起 4 个系统音色组原生支持 8 方言 + 8 外语，"选音色即用" |
| 流式合成 | 支持流式语音合成；WebSocket（实时）+ HTTP（非实时）双协议，同一模型名同时支持两种协议 |
| 控制台在线试听 | "模型体验"：3.1-flash 支持，3.0 系列不支持 |

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 3.1-flash 地域 | 仅华北2（北京） | 新加坡节点未上架；3.0 系列双节点在售 |
| 音色与模型强绑定 | 不可混用 | 换模型必须同步替换 voice，否则报 InvalidParameter |
| 3.1 基础音色库 | 暂无 | 3.0-plus / 3.0-flash 各有 500 余个复刻基础音色，3.1 暂无 |
| 3.1 无 plus 档 | 仅 flash | 高品质场景（有声书、影视配音）仍依赖 3.0-plus |
| 3.1-flash 限流 | RPS 3（≈180 RPM） | 与 3.0 系列 RPM 180 数值等效（表述单位不同） |
| 官方推荐位 | 选型页"推荐模型"表尚未收录 3.1 | 仍列 3.0-plus / cosyvoice-v3.5-plus |
| 官方技术披露 | 未发布技术报告 | 模型架构细节未披露 |

## 定价概览

| 模型 | 地域 | 单价（每万字符） | 备注 |
|------|------|------------------|------|
| qwen-audio-3.1-tts-flash | 北京 | 1 元 | 新加坡未上架 |
| qwen-audio-3.0-tts-flash | 北京 | 1 元 | |
| qwen-audio-3.0-tts-flash | 新加坡 | 1.12413 元 | 国际站 |
| qwen-audio-3.0-tts-plus | 北京 | 1.4 元 | |
| qwen-audio-3.0-tts-plus | 新加坡 | 1.49884 元 | 国际站 |

> 定价来源：https://help.aliyun.com/zh/model-studio/model-pricing（新加坡节点以人民币列示；国际站 USD 定价以 alibabacloud.com 定价页为准），核实日期：2026-09-20。

## 适用场景

### ✅ 适用

| 场景 | 推荐模型 | 说明 |
|------|----------|------|
| 实时交互（语音助手/智能客服/实时对话） | qwen-audio-3.1-tts-flash（北京）/ qwen-audio-3.0-tts-flash（国际） | 面向实时交互场景优化，Flash 版重点优化实时合成体验 |
| 多语种 / 方言内容 | qwen-audio-3.1-tts-flash | 4 个系统音色组原生支持 8 方言 + 8 外语，选音色即用 |
| 高品质内容制作 | qwen-audio-3.0-tts-plus | 有声书、影视配音、品牌声音（3.1 暂无 plus 档） |
| 低质录音音色复刻 | qwen-audio-3.1-tts-flash | 对含噪声、混响的参考音频鲁棒性更强 |
| 出海 / 新加坡节点 | qwen-audio-3.0-tts-plus / qwen-audio-3.0-tts-flash | 3.1-flash 未上架新加坡 |

### ❌ 不适用

| 场景 | 不适用原因 | 替代方案 |
|------|-----------|----------|
| 新加坡节点使用 3.1 能力 | 3.1-flash 仅北京上架 | qwen-audio-3.0-tts-flash / qwen-audio-3.0-tts-plus |
| 高品质场景选用 3.1 | 3.1 暂无 plus 档 | qwen-audio-3.0-tts-plus（可用控制台"模型体验"试听 A/B） |

## 版本演进与售前替代建议

### 3.1 版本升级要点（vs 3.0-flash）

1. **音色体系全面换代（最大差异）**：74 个 v3.1 系统音色 vs 12 个 v3.6 音色；音色与模型强绑定、不能混用
2. **多语种与方言音色（系列首次）**：4 个音色组原生支持 8 种方言 + 8 种外语，此前方言/多语种需通过指令控制设置；精品英文音色细分英式/美式口音
3. **声音复刻鲁棒性增强**：官方表述聚焦为"在声音复刻场景中，对含有噪声、混响的参考音频具有更强的鲁棒性"
4. **其他**：新增控制台"模型体验"在线试听；限流改用 RPS 3 口径

### 技术亮点与独创性分级

- 🔧 **组合创新**：多语种/方言能力从"复刻音色 + 指令控制"下沉为原生系统音色；系统音色矩阵扩展至 74 个，覆盖广告、有声书、客服、新闻播报、社交陪伴、儿童等场景
- ⚙️ **工程优化**：声音复刻对噪声/混响参考音频的鲁棒性提升
- 📋 **跟进对齐**：原生多语言系统音色对齐 MiniMax（40+ 语言）/ ElevenLabs（29 语言）等多语言 TTS 竞品
- 无 🌟 首创级技术公开；官方未发布技术报告

### 成本归因

- 与 3.0-flash 同价、低于 3.0-plus（1 元 vs 1.4 元/万字符）→ 定价策略降本（促销属性、可回调），非架构内禀降本

### 迁移注意

- API 协议与 3.0 完全兼容（改 model 参数即可），但 voice 必须同步替换为 v3.1 音色（如 longanhuan_v3.6 → longanhuan_v3.1），长期使用旧音色将报错 InvalidParameter

### 售前替代建议

| 客户场景 | 建议 |
|----------|------|
| 国内新项目（实时交互 / 多语种 / 方言） | qwen-audio-3.1-tts-flash 直接替代 3.0-flash（同价升级），首选 |
| 高品质内容制作（有声书 / 影视配音 / 品牌声音） | 维持 qwen-audio-3.0-tts-plus，可控制台"模型体验"试听后再定 |
| 国际站（新加坡）客户 | 维持 3.0 系列（3.1 未上架） |

## 参考资料

- qwen-audio-3.1-tts-flash 模型页：https://help.aliyun.com/zh/model-studio/qwen-audio-3-1-tts-flash
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
