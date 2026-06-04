# 视频中文配音转英文配音 Demo — 设计规格

## Context

用户需要一个demo工具，将视频中一个人的中文说话转换为英文配音。用户提供：
1. **视频文件**（MP4等）
2. **纯人声MP3**（用户通过 vocalremover.org 从视频中提取，无背景音乐/噪音）
3. **阿里云DashScope API Key**（大陆站 AIGC权限）

工具自动处理：语音识别 → 翻译 → 声音克隆 → 英文语音合成 → 替换视频音轨。
输出：英文配音版视频，保留原说话人音色特征。

## 用户输入

| 输入项 | 来源 | 说明 |
|--------|------|------|
| 视频文件 | 用户上传 | MP4/MOV，≤5分钟 |
| 纯人声MP3 | 用户通过 vocalremover.org 提取 | 无背景音乐的干净人声，用于ASR和声音复刻 |
| API Key | 用户输入 | 阿里云百炼大陆站 API Key（需AIGC权限，环境变量 `DASHSCOPE_API_KEY_CN_AIGC`） |

## Pipeline (6步)

1. **百炼临时上传** → 将纯人声MP3上传获得 oss:// URL（分别为ASR和声音复刻上传）
   - 文件名安全化：移除空格、方括号等特殊字符（OSS 兼容性）
2. **fun-asr ASR** → 对纯人声MP3做语音识别，获得带时间戳的中文句子列表
   - 使用 HTTP API + `X-DashScope-OssResourceResolve: enable` header（SDK 不支持 oss:// URL）
3. **qwen-mt-plus翻译** → 每句中文→英文（OpenAI兼容API，质量档）
4. **CosyVoice声音复刻** → 用纯人声MP3克隆音色，获得voice_id
   - 使用 HTTP API + Base64 Data URL（API 不支持 oss:// URL）
5. **CosyVoice v3-plus TTS** → 用克隆音色合成英文语音（plus 档音质优于 flash）
   - 动态 rate 参数：根据目标时长自动调整语速
   - ffmpeg atempo 微调时长对齐
6. **ffmpeg合成** → 将各句英文音频按时间戳放置 → 替换原视频音轨

注意：用户提供的纯人声MP3同时用于ASR（识别内容+时间戳）和声音复刻（提取音色），一鱼两吃。

## 关键决策（实现过程中调整）

| 问题 | 解决方案 |
|------|----------|
| 文件名含空格/方括号导致OSS失败 | 添加 `sanitize_filename()` 安全化文件名 |
| ASR SDK不支持oss:// URL | 改用 HTTP API + `X-DashScope-OssResourceResolve: enable` header |
| 声音复刻API仅支持公网HTTP URL | 改用 Base64 Data URL 直接传入音频数据 |
| TTS WebSocket连接不稳定 | 改用 HTTP API 非流式合成，返回音频URL后下载 |
| 语速过快 | 动态计算 rate 参数，根据目标时长匹配语速 |
| CosyVoice需要AIGC权限 | 使用 `DASHSCOPE_API_KEY_CN_AIGC` 环境变量 |

## 使用说明

- **地域选择**：UI 默认国际站，可切国内站。CosyVoice v3-plus / qwen-mt-plus / fun-asr 在两个站均可用
- **环境变量**：根据所选地域使用 `DASHSCOPE_API_KEY_INTL_AIGC` 或 `DASHSCOPE_API_KEY_CN_AIGC`

## 技术栈

- **语音识别**: fun-asr（HTTP API，北京地域）
- **翻译**: qwen-mt-plus（OpenAI兼容API，质量档）
- **声音复刻**: CosyVoice voice-enrollment（HTTP API + Base64）
- **语音合成**: CosyVoice v3-plus TTS（HTTP API，动态 rate）
- **音频处理**: ffmpeg（atempo时长对齐、adelay+amix合成）
- **UI**: Gradio Web UI

## 代码结构

```
sanitize_filename()           — 文件名安全化（移除特殊字符）
oss_url_to_http()            — oss:// URL 转 HTTP URL（备用）
upload_to_dashscope()        — 上传本地文件至百炼临时存储，返回oss://URL
get_audio_duration()         — ffprobe获取音频时长
VideoDubbingPipeline         — 核心Pipeline类
  .run()                     — 主入口，协调6步流程
  ._upload_files()           — Step 1: 上传纯人声MP3（返回oss URL + 本地路径）
  ._run_asr()                — Step 2: fun-asr语音识别（HTTP API + header）
  ._translate()              — Step 3: qwen-mt-plus翻译
  ._clone_voice()            — Step 4: CosyVoice声音复刻（HTTP API + Base64）
  ._synthesize()             — Step 5: CosyVoice v3-plus英文TTS（HTTP API + 动态rate + atempo）
  ._compose_video()          — Step 6: ffmpeg合成最终视频
build_ui()                   — Gradio界面
```

## Gradio UI

```
API Key (AIGC): [sk-xxx          ] (password, 需CosyVoice权限)
上传视频:      [拖拽上传 MP4/MOV]
纯人声MP3:    [拖拽上传 MP3] (从vocalremover.org提取)
翻译模型:      [qwen-mt-plus ▾]
[▶ 开始转换]

── 处理进度 ──
✅/🔄/⏳ 各步骤状态

── 中间结果(折叠) ──
ASR + 翻译对照

── 输出 ──
[播放] [下载]
```

## 依赖

```bash
pip install dashscope openai gradio requests
# 系统依赖
brew install ffmpeg
```

## 环境变量

```bash
# ~/.zshrc 或 ~/.bashrc
export DASHSCOPE_API_KEY_CN_AIGC=sk-xxx  # 需要CosyVoice权限
```

## 验证

1. `python video_dubbing_zh2en.py` → 浏览器打开 http://localhost:7860
2. 准备: 用 vocalremover.org 从测试视频提取纯人声MP3
3. 输入API Key + 上传视频 + 上传纯人声MP3 → 点击转换
4. 验证: ASR中文识别准确、翻译正确、声音复刻成功、TTS保留原音色、语速自然、输出视频音画同步