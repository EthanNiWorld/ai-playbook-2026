# 视频中文配音转英文配音 Demo

将视频中一个人的中文说话转换为英文配音，保留原说话人音色（声音克隆）。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt

# 系统依赖（macOS）
brew install ffmpeg
```

### 2. 准备素材

1. 准备一段中文说话的视频（MP4, ≤5分钟，单人说话）
2. 去 [vocalremover.org](https://vocalremover.org) 上传视频，提取纯人声，下载 MP3

### 3. 运行

```bash
python video_dubbing_zh2en.py
```

浏览器打开 http://localhost:7860

### 4. 使用

1. 输入阿里云百炼 API Key（大陆站，`sk-xxx`）
2. 上传视频文件
3. 上传纯人声 MP3
4. 点击「开始转换」
5. 等待处理完成，播放或下载英文配音视频

## 处理流程

```
纯人声MP3 → ASR语音识别 → 中译英翻译 → 声音克隆 → 英文TTS → 替换视频音轨 → 输出
```

## 文件结构

```
video_translation_demo/
├── video_dubbing_zh2en.py   # 主程序（Pipeline + Gradio UI）
├── requirements.txt         # Python依赖
├── SPEC.md                  # 设计规格文档
└── README.md                # 本文件
```

## 前置条件

- Python 3.10+
- ffmpeg（`brew install ffmpeg`）
- 阿里云百炼**大陆站** API Key（[获取方式](https://help.aliyun.com/zh/model-studio/get-api-key)）

## 注意事项

- CosyVoice 声音复刻仅北京地域可用，需使用大陆站 API Key
- fun-asr 是异步任务，长视频可能需等待 1-2 分钟
- 声音复刻有配额限制（1000 个音色），Demo 使用后建议清理
