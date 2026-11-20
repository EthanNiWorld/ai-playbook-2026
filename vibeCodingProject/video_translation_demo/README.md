# 视频中文配音转英文配音 Demo

将视频中一个人的中文说话转换为英文配音，保留原说话人音色（声音克隆）。

## 快速开始

### 1. 安装依赖

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 系统依赖（macOS）
brew install ffmpeg
```

### 2. 准备素材

1. 准备一段中文说话的视频（MP4, ≤5分钟，单人说话）
2. 去 [vocalremover.org](https://vocalremover.org) 上传视频，提取纯人声，下载 MP3

### 3. 运行

```bash
.venv/bin/python video_dubbing_zh2en.py
```

浏览器打开 http://localhost:7860

### 4. 使用

1. 选择地域（默认国际站），API Key 自动从对应环境变量预填
2. 上传视频文件
3. 上传纯人声 MP3
4. 点击「开始转换」
5. 等待处理完成，播放或下载英文配音视频

## 处理流程

```
纯人声MP3 → ASR语音识别(qwen-audio-3.1-asr-flash) → 中译英翻译(qwen-mt-plus)
→ 声音克隆(voice-enrollment) → 英文TTS(qwen-audio-3.1-tts-plus) → 替换视频音轨 → 输出
```

## 模型清单（2026-11 换代）

| 环节 | 当前模型 | 说明 |
|------|----------|------|
| 语音识别 | qwen-audio-3.1-asr-flash | 同步多模态接口，开启说话人分离获取句级时间戳；本地 Base64 直传，无需先上传百炼临时存储 |
| 翻译 | qwen-mt-plus | OpenAI 兼容 API，质量档 |
| 声音复刻 | voice-enrollment（target_model=qwen-audio-3.1-tts-plus） | 克隆音色与 TTS 模型强绑定 |
| 语音合成 | qwen-audio-3.1-tts-plus | 精品音色 / 内容制作档，SSML `<break>` 合并多句一次合成 |

> 旧模型（fun-asr 异步转写 + CosyVoice TTS）已于 2026-11 按主推口径换代。

## 文件结构

```
video_translation_demo/
├── video_dubbing_zh2en.py   # 主程序（Pipeline + Gradio UI）
├── _run_pipeline_test.py    # 端到端测试脚本（不走 UI）
├── requirements.txt         # Python依赖
├── SPEC.md                  # 设计规格文档
├── testfile/                # 测试素材与历史输出
└── README.md                # 本文件
```

## 前置条件

- Python 3.10+（推荐 3.12）
- ffmpeg（`brew install ffmpeg`）
- 阿里云百炼 API Key（见下方环境变量）

## 环境变量与端点配对

地域 → Key/端点配对（`sk-ws` 开头的 workspace Key **必须**与其配套 workspace 域名成对使用，打到标准 `dashscope.aliyuncs.com` 域名会返回 401）：

| 地域 | Key 环境变量 | 端点环境变量 |
|------|--------------|--------------|
| intl（默认） | DASHSCOPE_API_KEY_INTL_SG_TEST | DASHSCOPE_API_KEY_INTL_SG_TEST_URL |
| cn | DASHSCOPE_API_KEY_INTL_BJ_TEST | DASHSCOPE_API_KEY_INTL_BJ_TEST_URL |

程序从 `*_URL` 的 workspace 域名自动推导 API/WS/兼容模式端点；未配置时回落标准域名（需标准 `sk-` Key）。

## 注意事项

- ASR 同步接口上限 5 分钟音频，与视频时长上限一致
- 声音复刻有配额限制（1000 个音色），Demo 使用后建议清理
- 克隆音色与 TTS 模型强绑定，换 TTS 模型须重新复刻
