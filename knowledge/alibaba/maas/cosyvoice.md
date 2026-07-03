# CosyVoice

> 最后更新: 2026-07-03
> 所属厂商: Alibaba (Alibaba Cloud)
> 产品类别: AI 语音合成（TTS）
> 状态: Published

<!-- SUMMARY_START -->
**定位**: 百炼平台主推的多语言大语音生成模型，具备声音复刻、声音设计、指令控制三大高级能力，将替代 Qwen-TTS
**适用**: 智能客服、语音助手、有声阅读、品牌专属音色、虚拟主播、情感化内容制作
**不适用**: 仅需基础 TTS 且预算极低的场景（可用 Qwen-TTS 旧版过渡）
**竞品**: OpenAI gpt-4o-tts、Google Chirp 3、ElevenLabs Multilingual v3
**常搭配**: FunASR（语音识别）、百炼平台（MaaS）、Qwen 系列（LLM）
<!-- SUMMARY_END -->

## 产品原理解析

### 一句话定位

阿里 FunAudioLLM 团队研发的多语言大语音生成模型，百炼平台当前**主推的 TTS 引擎**，官方已标注 Qwen-TTS 为"旧版"。

### 底层原理（通俗版）

CosyVoice 基于 LLM 的流式语音合成架构（CosyVoice 2），支持双向流式——文本边输入、音频边输出，延迟低至 150ms。不仅能"念文字"，还能从音频样本克隆音色（声音复刻）、从文字描述创建全新音色（声音设计）、用自然语言控制语速情绪风格（指令控制）。

论文：[CosyVoice 2: Scalable Streaming Speech Synthesis with Large Language Models](https://arxiv.org/abs/2412.10117)（arxiv:2412.10117）

### 百炼平台模型矩阵

| 模型 ID | API 接入 | 声音复刻 | 声音设计 | 指令控制 | 状态 |
|---------|----------|----------|----------|----------|------|
| **cosyvoice-v3.5-plus** | WebSocket + HTTP | ✅ | ✅ | ✅ | 🚩 当前旗舰 |
| **cosyvoice-v3.5-flash** | WebSocket + HTTP | ✅ | ✅ | ✅ | 🚩 轻量旗舰 |
| cosyvoice-v3-plus | WebSocket + HTTP | ✅ | ✅ | ❌ | 在售 |
| cosyvoice-v3-flash | WebSocket + HTTP | ✅ | ✅ | ✅ | 在售 |
| cosyvoice-v2 | WebSocket + HTTP | ✅ | ❌ | ❌ | 在售 |
| cosyvoice-v1 | WebSocket | ✅ | ❌ | ❌ | 在售 |

> **Qwen-TTS 系列**仍可在百炼调用，但文档已标注为"旧版，按 Token 计费"，官方推荐迁移到 CosyVoice。

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 声音设计语言 | 仅中文（普通话）、英文 | 声音复刻支持更多语种 |
| v3-plus 指令控制 | 不支持 | 需升级到 v3.5-plus 或 v3-flash |
| 方言实现方式 | 通过指令控制功能设置 | 非系统音色直接支持 |

## 语言覆盖

**cosyvoice-v3.5-plus / v3.5-flash：**
- 声音复刻音色：中文（普通话 + 18 种方言：广东话、东北话、四川话、闽南话等）、英文、法语、德语、日语、韩语、俄语、葡萄牙语、泰语、印尼语、越南语
- 声音设计音色：中文（普通话）、英文

**cosyvoice-v3-plus：**
- 系统音色：中文（普通话）、英文
- 声音复刻音色：中文（普通话 + 18 种方言）、英文、法语、德语、日语、韩语、俄语

## 定价

| 模型 | 服务区域 | 单价 | 免费额度 |
|------|----------|------|----------|
| cosyvoice-v3-plus | 国际（新加坡） | $0.26/万字符 | 1 万字符 |
| cosyvoice-v3-flash | 国际（新加坡） | $0.13/万字符 | 100 万 Token |
| cosyvoice-v3.5-plus | 国内（华北2-北京） | $0.22/万字符 | 无 |
| cosyvoice-v3.5-flash | 国内（华北2-北京） | $0.116/万字符 | 无 |

## 适用边界分析

### ✅ 适用场景

| 场景 | 说明 | 典型客户/案例 |
|------|------|--------------|
| 品牌专属音色 | 声音复刻品牌代言人/主播音色 | 品牌营销、虚拟主播 |
| 情感化内容制作 | 指令控制语速/情绪/风格 | 有声读物、专业播报 |
| 智能客服/语音助手 | WebSocket 实时流式，150ms 延迟 | 呼叫中心、智能音箱 |
| 多语言内容出海 | 18 种方言 + 11 种外语 | 跨境电商、全球化产品 |

### ❌ 不适用场景

| 场景 | 不适用原因 | 替代方案 |
|------|-----------|----------|
| 仅需基础 TTS、成本敏感 | CosyVoice 功能过剩 | Qwen-TTS 旧版（按 Token 计费，可过渡） |
| 声音设计需多语种 | 声音设计仅支持中文+英文 | 等待后续版本扩展 |

### ⚠️ 常见误解

| 误解 | 事实 |
|------|------|
| CosyVoice = Qwen-TTS 新版 | 两者是独立模型系列，CosyVoice 来自 FunAudioLLM 团队，Qwen-TTS 来自千问团队 |
| 方言是系统内置音色 | 方言通过指令控制功能设置，非系统音色直接支持 |

## 关键配置与最佳实践

- **WebSocket vs HTTP**：实时交互场景（客服/助手）选 WebSocket，批量内容制作选 HTTP
- **同一模型名称同时支持两种协议**，无需切换模型
- **SDK 支持**：DashScope SDK（Java/Python）、Android/iOS SDK
- **从 Qwen-TTS 迁移**：切换模型名称即可，API 协议兼容

## 竞品快速对照

| 维度 | CosyVoice v3.5-plus | OpenAI gpt-4o-tts | ElevenLabs v3 |
|------|---------------------|-------------------|---------------|
| 声音复刻 | ✅ | ❌ | ✅ |
| 声音设计 | ✅ | ❌ | ❌ |
| 指令控制 | ✅ 自然语言控制 | ❌ | 有限 |
| 流式延迟 | 150ms | [⚠️ 待补充] | [⚠️ 待补充] |
| 方言覆盖 | 18 种中文方言 | 有限 | 有限 |
| 开源 | ✅ GitHub | ❌ | ❌ |

## 参考资料

- 百炼 TTS 模型选型：https://help.aliyun.com/zh/model-studio/tts-model/
- 百炼模型定价：https://www.alibabacloud.com/help/zh/model-studio/model-pricing
- CosyVoice 2 论文：https://arxiv.org/abs/2412.10117
- GitHub 开源仓库：https://github.com/FunAudioLLM/CosyVoice

## Changelog

| 日期 | 变更内容 |
|------|----------|
| 2026-07-03 | 初始创建：基于 inbox/ai-knowledge-by-qoder-ai-native-agent-20260703.md 提炼 |
