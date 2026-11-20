# 视频中文配音转英文配音 Demo — 设计规格

## Context

用户需要一个demo工具，将视频中一个人的中文说话转换为英文配音。用户提供：
1. **视频文件**（MP4等）
2. **纯人声MP3**（用户通过 vocalremover.org 从视频中提取，无背景音乐/噪音）
3. **阿里云百炼 API Key**（workspace Key，与端点成对）

工具自动处理：语音识别 → 翻译 → 声音克隆 → 英文语音合成 → 替换视频音轨。
输出：英文配音版视频，保留原说话人音色特征。

## 用户输入

| 输入项 | 来源 | 说明 |
|--------|------|------|
| 视频文件 | 用户上传 | MP4/MOV，≤5分钟 |
| 纯人声MP3 | 用户通过 vocalremover.org 提取 | 无背景音乐的干净人声，用于ASR和声音复刻 |
| API Key | 用户输入/环境变量预填 | 与地域配对的 workspace Key（见 REGION_ENV） |

## Pipeline (5步)

> 2026-11 换代：ASR 由 fun-asr（异步任务 + oss:// 临时上传）换为 qwen-audio-3.1-asr-flash（同步多模态接口，Base64 直传），
> 原独立的上传步骤被移除，Pipeline 由 6 步收敛为 5 步；TTS 由 cosyvoice-v3-plus 换为 qwen-audio-3.1-tts-plus。

1. **qwen-audio-3.1-asr-flash ASR** → 带时间戳的中文句子列表
   - 同步多模态 HTTP：POST {api_v1}/services/aigc/multimodal-generation/generation
   - 音频先 ffmpeg 下混为 16kHz 单声道 WAV（说话人分离仅支持单声道），Base64 Data URI 直传
   - 开启 `speaker_diarization_enabled` → 从 `output.sentences` 读句级时间戳（开启后 language_hints 不生效）
   - flash 系列不支持 SDK / 异步 filetrans 接口
2. **qwen-mt-plus翻译** → 每句中文→英文（OpenAI兼容API，质量档）
3. **声音复刻 voice-enrollment** → 用纯人声MP3克隆音色，获得voice_id
   - 使用 HTTP API + Base64 Data URL（接口不支持 oss:// URL）
   - target_model=qwen-audio-3.1-tts-plus（克隆音色与 TTS 模型强绑定）
4. **qwen-audio-3.1-tts-plus TTS** → 用克隆音色合成英文语音
   - 多句合并为一段 SSML（`<break>` 隔开），一次 WebSocket 调用，韵律连贯
   - ffmpeg loudnorm 响度归一
5. **ffmpeg合成** → 整段替换原视频音轨（仅在英文明显长于视频时温和 atempo）

注意：用户提供的纯人声MP3同时用于ASR（识别内容+时间戳）和声音复刻（提取音色），一鱼两吃。

## 关键决策（实现过程中调整）

| 问题 | 解决方案 |
|------|----------|
| sk-ws workspace Key 打标准 dashscope 域名返回 401 | 端点从 REGION_ENV 配对的 *_URL workspace 域名自动推导；未配置时回落标准域名 |
| qwen-audio ASR flash 不支持 SDK / 异步接口 | 改用同步多模态 HTTP（X-DashScope-SSE: disable），音频 Base64 Data URI 直传 |
| 说话人分离（句级时间戳）仅支持单声道 | ASR 前先用 ffmpeg 下混为 16kHz 单声道 WAV |
| 旧 fun-asr 需先上传百炼临时存储获取 oss:// URL | 3.1 同步接口直传 Base64，删除上传环节（含 sanitize_filename/oss_url_to_http/upload_to_dashscope） |
| 声音复刻API仅支持公网HTTP URL | 改用 Base64 Data URL 直接传入音频数据 |
| 语速过快 | 多句合并 SSML 一次合成；仅整段明显超长时温和 atempo |
| 克隆音色与 TTS 模型强绑定 | voice-enrollment 的 target_model 跟随 DEFAULT_TTS_MODEL 常量 |

## 使用说明

- **地域选择**：UI 默认国际站（新加坡 workspace），可切国内站（北京 workspace）
- **环境变量**：Key 与端点成对配置（DASHSCOPE_API_KEY_INTL_SG_TEST + _URL / DASHSCOPE_API_KEY_INTL_BJ_TEST + _URL）

## 技术栈

- **语音识别**: qwen-audio-3.1-asr-flash（同步多模态 HTTP，speaker_diarization 句级时间戳）
- **翻译**: qwen-mt-plus（OpenAI兼容API，质量档）
- **声音复刻**: voice-enrollment（HTTP API + Base64，target_model=qwen-audio-3.1-tts-plus）
- **语音合成**: qwen-audio-3.1-tts-plus（WebSocket SDK，SSML 长文本一次合成）
- **音频处理**: ffmpeg（下混/loudnorm/atempo/adelay+amix）
- **UI**: Gradio Web UI

## 代码结构

```
get_audio_duration()         — ffprobe获取音频时长
VideoDubbingPipeline         — 核心Pipeline类
  .run()                     — 主入口，协调5步流程
  ._run_asr()                — Step 1: qwen-audio-3.1-asr-flash识别（同步HTTP + Base64 + 下混）
  ._translate()              — Step 2: qwen-mt-plus翻译
  ._clone_voice()            — Step 3: 声音复刻（HTTP API + Base64）
  ._synthesize()             — Step 4: qwen-audio-3.1-tts-plus英文TTS（SSML合并 + loudnorm）
  ._compose_video()          — Step 5: ffmpeg合成最终视频
build_ui()                   — Gradio界面
```

## Gradio UI

```
百炼地域:      (🌏 国际站 | 🇨🇳 国内站)  → 切换时自动预填对应环境变量的 Key
API Key:      [sk-xxx          ] (password)
上传视频:      [拖拽上传 MP4/MOV]
纯人声MP3:    [拖拽上传 MP3] (从vocalremover.org提取)
翻译模型:      [qwen-mt-plus ▾]
[🚀 开始转换]

── 处理进度 ──
✅/🔄/⏳ 各步骤状态

── 中间结果(折叠) ──
ASR + 翻译对照

── 输出 ──
[播放] [下载]
```

## 依赖

```bash
python3.12 -m venv .venv
.venv/bin/pip install dashscope openai gradio requests
# 系统依赖
brew install ffmpeg
```

## 验证

1. `.venv/bin/python video_dubbing_zh2en.py` → 浏览器打开 http://localhost:7860
2. 准备: 用 vocalremover.org 从测试视频提取纯人声MP3
3. 输入API Key + 上传视频 + 上传纯人声MP3 → 点击转换
4. 验证: ASR中文识别准确、翻译正确、声音复刻成功、TTS保留原音色、语速自然、输出视频音画同步
5. 命令行端到端: `.venv/bin/python _run_pipeline_test.py`（自动加载仓库 .env，intl 地域）
