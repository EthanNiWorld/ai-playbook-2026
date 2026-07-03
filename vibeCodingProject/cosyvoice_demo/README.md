# TTS (CosyVoice v3.5-plus) & ASR (fun-asr) Demo

基于阿里云百炼平台的语音全链路 Demo，集成 **声音复刻**、**声音设计**、**语音合成 (TTS)** 和 **语音识别 (ASR)** 四大能力。

## 功能概览

| Tab | 功能 | 模型 |
|-----|------|------|
| 🎤 声音复刻 | 上传音频或输入 URL，克隆音色 | `cosyvoice-v3.5-plus` |
| 🎨 声音设计 | 文字描述生成音色，支持 AI 优化提示词 | `cosyvoice-v3.5-plus` + `qwen3.7-max` |
| 🔊 语音合成 | 选择音色 + 文本 → 合成语音 | `cosyvoice-v3.5-plus` |
| 📋 音色管理 | 查询 / 详情 / 删除自定义音色 | — |
| 🎧 ASR 语音识别 | 上传音频或 URL → 识别为文字 | `fun-asr` |

## 核心特性

- **OSS 集成**：本地音频自动上传至阿里云 OSS，获取签名 URL 供 API 调用
- **音色持久化**：
  - `output/voices.json` — 保存音色 ID 及复刻源音频 URL
  - `output/generated_audio.json` — 保存 TTS 合成音频的 OSS URL
- **AI 提示词优化**：声音设计中集成 `qwen3.7-max`，自动将用户口语化描述优化为专业 voice_prompt
- **ASR 音频预览**：支持上传文件播放和 URL 音频下载播放
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
├─────────────┬─────────────────┬──────────────────┤
│  CosyVoice  │   qwen3.7-max   │    fun-asr       │
│  v3.5-plus  │  (提示词优化)     │  (语音识别)       │
├─────────────┴─────────────────┴──────────────────┤
│              阿里云 OSS (音频存储)                   │
└─────────────────────────────────────────────────┘
```

## 项目结构

```
cosyvoice_demo/
├── app.py                    # 主程序（Gradio 界面 + 业务逻辑）
├── requirements.txt          # Python 依赖
├── README.md                 # 本文件
└── output/                   # 持久化数据目录
    ├── voices.json           # 音色信息（voice_id + 源音频 URL）
    └── generated_audio.json  # TTS 合成音频（voice_id + 文本 + OSS URL）
```

## API 端点说明

| 用途 | 端点 |
|------|------|
| CosyVoice TTS / 音色管理 | `https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1` |
| CosyVoice WebSocket 合成 | `wss://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api-ws/v1/inference` |
| qwen3.7-max 提示词优化 | `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions` |

> ⚠️ Workspace 专属域名仅支持 CosyVoice/TTS 相关 API，通用 LLM 模型（如 qwen3.7-max）必须使用标准 DashScope 端点。

## 依赖

- `dashscope` — 阿里云百炼 SDK（TTS / ASR / 音色管理）
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
