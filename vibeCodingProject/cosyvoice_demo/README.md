# TTS (Qwen-Audio 3.1-tts-plus) & ASR (Qwen-Audio 3.0-ASR) Demo

基于阿里云百炼平台的语音全链路 Demo，集成 **声音复刻**、**声音设计**、**语音合成 (TTS)** 和 **语音识别 (ASR)** 四大能力。

> TTS 引擎已由 CosyVoice v3.5-plus 替换为 **qwen-audio-3.1-tts-plus**（Qwen-Audio-TTS 3.1 系列精品档）；ASR 主推 qwen-audio-3.0-asr-flash，fun-asr 仅作存量对照保留。

## 功能概览

| Tab | 功能 | 模型 |
|-----|------|------|
| 🎤 声音复刻 | 上传音频或输入 URL，克隆音色 | `qwen-audio-3.1-tts-plus` |
| 🎨 声音设计 | 文字描述生成音色，支持 AI 优化提示词 | `qwen-audio-3.1-tts-plus` + `qwen3.8-max` |
| 🔊 语音合成 | 系统音色 / 自定义音色 + 文本 → 合成语音 | `qwen-audio-3.1-tts-plus` |
| 📋 音色管理 | 查询 / 详情 / 删除自定义音色 | — |
| ⚡ Qwen-Audio ASR Flash（主推） | 上传音频或 URL → 识别为文字（同步接口） | `qwen-audio-3.0-asr-flash` |
| 🎙️ Qwen-Audio ASR Filetrans | 上传音频或 URL → 识别为文字（异步任务） | `qwen-audio-3.0-asr-flash-filetrans` |
| 🎧 ASR 语音识别（存量） | 异步转写对照 | `fun-asr` |

## 模型说明

- **qwen-audio-3.1-tts-plus**：3.1 系列精品档，4 个 v3.1 旗舰系统音色（`longanlingxin_v3.1` / `xunanchuan_v3.1` / `longanhuan_v3.1` / `longanfengyue_v3.1`），支持声音复刻、声音设计、free-style 指令与 `[laughing]` / `[crying]` 等标签控制；无 3.0 系列的 500+ 复刻基础音色库（需要时改用 `qwen-audio-3.0-tts-plus`）。
- 同系列另有 `qwen-audio-3.1-tts-flash`（实时交互、首包更低）与 `qwen-audio-3.1-tts-next`（音频生成 AudioGen，参数范式为 `text_prompt`，与本 Demo 的 `text` / `voice` 不同）。
- **音色与模型强绑定**：不得跨模型复用 voice_id。本 Demo 仅展示属于当前模型的自定义音色，旧 CosyVoice 音色已自动隐藏，需重新复刻/设计。

## 核心特性

- **OSS 集成**：本地音频自动上传至阿里云 OSS，获取签名 URL 供 API 调用
- **音色持久化**：
  - `output/voices.json` — 保存音色 ID 及复刻源音频 URL
  - `output/generated_audio.json` — 保存 TTS 合成音频的 OSS URL
- **AI 提示词优化**：声音设计中集成 `qwen3.8-max`，自动将用户口语化描述优化为专业 voice_prompt
- **ASR 音频预览**：支持上传文件播放和 URL 音频下载播放
- **系统音色直选**：TTS Tab 下拉框首屏即 4 个 v3.1 旗舰音色，免复刻即可试听
- **等宽字体渲染**：Voice ID、URL、技术术语等统一使用 monospace 字体

## 快速开始

### 1. 环境准备

```bash
cd vibeCodingProject/cosyvoice_demo
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置环境变量

在项目根目录 `.env` 中配置以下变量：

```env
# DashScope API Key（北京节点）
DASHSCOPE_API_KEY_CN=<your_api_key>

# OSS 配置（用于音频上传）
oss_AccessKey_ID=<your_access_key_id>
oss_AccessKey_key=<your_access_key_secret>
OSS_BUCKET_NAME=<your_bucket_name>
OSS_ENDPOINT=oss-cn-beijing.aliyuncs.com
OSS_UPLOAD_PREFIX=cosyvoice-demo/
```

### 3. 启动

```bash
python app.py
```

访问 `http://localhost:7860` 即可使用。

## 技术架构

```
┌─────────────────────────────────────────────────┐
│                  Gradio Web UI                    │
├──────┬──────┬──────┬──────────┬──────────────────┤
│ 声音  │ 声音  │ 语音  │  音色    │   ASR            │
│ 复刻  │ 设计  │ 合成  │  管理    │   语音识别        │
├──────┴──────┴──────┴──────────┴──────────────────┤
│              DashScope SDK / HTTP API              │
├────────────────────┬────────────────┬────────────┤
│ Qwen-Audio 3.1 TTS │  qwen3.8-max   │ Qwen-Audio │
│     (plus)         │  (提示词优化)   │ 3.0-ASR    │
├────────────────────┴────────────────┴────────────┤
│              阿里云 OSS (音频存储)                   │
└─────────────────────────────────────────────────┘
```

## 项目结构

```
cosyvoice_demo/
├── app.py                    # 主程序（Gradio 界面 + 业务逻辑）
├── requirements.txt          # Python 依赖
├── clone_compare.py          # 历史对照脚本：同音频复刻后 qwen-audio-3.0-tts-plus vs CosyVoice
├── tts_compare.py            # 历史对照脚本：同文本同指令的 TTS 对比
├── README.md                 # 本文件
└── output/                   # 持久化数据目录
    ├── voices.json           # 音色信息（voice_id + 归属模型 + 源音频 URL）
    └── generated_audio.json  # TTS 合成音频（voice_id + 文本 + OSS URL）
```

## API 端点说明

| 用途 | 端点 |
|------|------|
| Qwen-Audio 3.1 TTS 合成（SDK WebSocket） | `wss://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api-ws/v1/inference` |
| 音色复刻 / 声音设计 / 音色管理（HTTP） | `{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1/services/audio/tts/customization` |
| qwen3.8-max 提示词优化 | `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions` |

> ⚠️ Workspace 专属域名仅支持 TTS / 音色管理相关 API，通用 LLM 模型（如 qwen3.8-max）与 qwen-audio ASR 模型必须使用标准 DashScope 端点。

## 依赖

- `dashscope` — 阿里云百炼 SDK（TTS 合成 / 音色复刻 / 音色管理）
- `gradio` — Web UI 框架
- `oss2` — 阿里云 OSS SDK（音频上传）
- `requests` — HTTP 请求（LLM 调用 / 转写结果下载）
- `python-dotenv` — 环境变量加载

## 音频要求

### 声音复刻

| 项目 | 要求 |
|------|------|
| 格式 | WAV / MP3 / M4A |
| 时长 | 推荐 10~20 秒，最长 60 秒 |
| 大小 | ≤ 10MB |
| 采样率 | ≥ 16kHz |
| 内容 | 连续清晰人声，无背景音乐/噪音 |

### ASR 语音识别

- 支持 WAV / MP3 / M4A 等常见格式
- 本地文件自动上传 OSS 后提交识别
- 也支持直接输入公网可访问的音频 URL
