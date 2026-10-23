# Qwen-Audio-3.1-TTS 三模型新加坡节点实测报告

- 测试时间：2026-10-23 12:11:51
- 地域/端点：新加坡（ap-southeast-1）`https://llm-ablnum2bgfvl34hs.ap-southeast-1.maas.aliyuncs.com/api/v1/services/audio/tts/SpeechSynthesizer`
- 凭证环境变量：`DASHSCOPE_API_KEY_SGP`
- 输出格式：mp3 / 24000Hz

## 测试台词

> （狂笑）哈哈哈哈！曾经有一份真诚的爱情放在我面前，我没有珍惜，等我失去的时候我才后悔莫及，人世间最痛苦的事莫过于此。（停顿，深吸一口气，转为深情/哭腔）如果上天能够给我一个再来一次的机会，我会对那个女孩子说三个字：我爱你。如果非要在这份爱上加个期限，我希望是……一万年。

## 三种提示写法

| 写法 | 说明 |
|------|------|
| raw | 原文提交，保留中文括号表演提示「（狂笑）」「（停顿，深吸一口气，转为深情/哭腔）」 |
| tags | 改写为官方英文方括号标签 `[laughing]` `[gasp]` `[crying]` |
| delivery | 去掉括号的纯台词 + `instruction`（flash/plus）/ prompt 描述（next） |

## 实测结果

| 模型 | 变体 | 音色 | 状态 | 请求耗时(s) | 文件大小(KB) | 音频时长(s) | 计费用量 | 音频文件 |
|------|------|------|------|------------:|-------------:|------------:|----------|----------|
| `qwen-audio-3.1-tts-flash` | raw | longanhuan_v3.1 | ✅ 200 | 2.87 | 519.9 | 26.62 | 465 tokens | qwen-audio-3.1-tts-flash_longanhuan_v3.1_raw.mp3 |
| `qwen-audio-3.1-tts-flash` | tags | longanhuan_v3.1 | ✅ 200 | 2.66 | 587.0 | 30.05 | 490 tokens | qwen-audio-3.1-tts-flash_longanhuan_v3.1_tags.mp3 |
| `qwen-audio-3.1-tts-flash` | delivery | longanhuan_v3.1 | ✅ 200 | 2.35 | 502.6 | 25.73 | 433 tokens | qwen-audio-3.1-tts-flash_longanhuan_v3.1_delivery.mp3 |
| `qwen-audio-3.1-tts-flash` | raw | xunanchuan_v3.1 | ✅ 200 | 2.76 | 546.7 | 27.98 | 482 tokens | qwen-audio-3.1-tts-flash_xunanchuan_v3.1_raw.mp3 |
| `qwen-audio-3.1-tts-flash` | tags | xunanchuan_v3.1 | ✅ 200 | 2.55 | 540.1 | 27.65 | 460 tokens | qwen-audio-3.1-tts-flash_xunanchuan_v3.1_tags.mp3 |
| `qwen-audio-3.1-tts-flash` | delivery | xunanchuan_v3.1 | ✅ 200 | 2.36 | 501.2 | 25.66 | 432 tokens | qwen-audio-3.1-tts-flash_xunanchuan_v3.1_delivery.mp3 |
| `qwen-audio-3.1-tts-plus` | raw | longanlingxin_v3.1 | ✅ 200 | 6.63 | 513.8 | 26.3 | 461 tokens | qwen-audio-3.1-tts-plus_longanlingxin_v3.1_raw.mp3 |
| `qwen-audio-3.1-tts-plus` | tags | longanlingxin_v3.1 | ✅ 200 | 6.61 | 524.6 | 26.86 | 450 tokens | qwen-audio-3.1-tts-plus_longanlingxin_v3.1_tags.mp3 |
| `qwen-audio-3.1-tts-plus` | delivery | longanlingxin_v3.1 | ✅ 200 | 6.35 | 518.5 | 26.54 | 443 tokens | qwen-audio-3.1-tts-plus_longanlingxin_v3.1_delivery.mp3 |
| `qwen-audio-3.1-tts-plus` | raw | xunanchuan_v3.1 | ✅ 200 | 6.97 | 542.0 | 27.74 | 479 tokens | qwen-audio-3.1-tts-plus_xunanchuan_v3.1_raw.mp3 |
| `qwen-audio-3.1-tts-plus` | tags | xunanchuan_v3.1 | ✅ 200 | 7.24 | 576.2 | 29.5 | 483 tokens | qwen-audio-3.1-tts-plus_xunanchuan_v3.1_tags.mp3 |
| `qwen-audio-3.1-tts-plus` | delivery | xunanchuan_v3.1 | ✅ 200 | 5.72 | 463.7 | 23.74 | 408 tokens | qwen-audio-3.1-tts-plus_xunanchuan_v3.1_delivery.mp3 |
| `qwen-audio-3.1-tts-next` | raw | —（无 voice 参数） | ✅ 200 | 23.27 | 149.1 | 20.35 | 4617 tokens | qwen-audio-3.1-tts-next_raw.mp3 |
| `qwen-audio-3.1-tts-next` | tags | —（无 voice 参数） | ✅ 200 | 50.24 | 323.4 | 85.43 | 10562 tokens | qwen-audio-3.1-tts-next_tags.mp3 |
| `qwen-audio-3.1-tts-next` | delivery | —（无 voice 参数） | ✅ 200 | 27.69 | 165.2 | 23.32 | 5674 tokens | qwen-audio-3.1-tts-next_delivery.mp3 |

## 指标观察

- `qwen-audio-3.1-tts-flash`：请求耗时 2.35~2.87s（均值 2.59s）；音频时长 25.66~30.05s
- `qwen-audio-3.1-tts-plus`：请求耗时 5.72~7.24s（均值 6.59s）；音频时长 23.74~29.5s
- `qwen-audio-3.1-tts-next`：请求耗时 23.27~50.24s（均值 33.73s）；音频时长 20.35~85.43s；时长异常：tags（上报 51.76s / 实际 85.43s）

## 流式首包延迟（SSE）

> 与非流式 `raw` 同音色、同台词对比；首包 = 首个非空 `output.audio.data` 到达时刻（含网络往返）。非流式端到端 = 请求耗时 + 下载耗时。

| 模型 | 音色 | 首个事件(s) | 首个音频块(s) | 完成(s) | 音频块数 | 非流式端到端(s) | 首包提速 |
|------|------|------------:|--------------:|--------:|---------:|----------------:|---------:|
| `qwen-audio-3.1-tts-flash` | longanhuan_v3.1 | 0.713 | 0.713 | 2.864 | 51 | 8.81 | ✅ 12.4x |
| `qwen-audio-3.1-tts-plus` | longanlingxin_v3.1 | 0.836 | 0.839 | 6.646 | 50 | 9.76 | ✅ 11.6x |

> 音频文件位于 `output/tts_qwen_audio_31_sgp_20261023_121151/`（运行时产物，已加入 .gitignore，不入库），明细见同目录 `results.json`。
> flash / plus 按输入+输出 tokens 计费（usage 中同时返回 characters）；next 按音频时长对应的 tokens 计费。

## 试听建议

1. 先对比 `flash` 与 `plus` 同音色同写法的文件，判断音质与情感细腻度差异；
2. 再对比同一模型的 `raw` / `tags` / `delivery`，判断哪种写法最能让模型「演出」狂笑、吸气与哭腔；
3. `next` 是 AudioGen（音频生成）模型，输出为一段完整音频表演（可含环境音/音效），与纯 TTS 的 flash/plus 不属同一任务范式，横向对比时以「表演完整度」为主要观感维度；但它并非不支持 TTS——只写台词、另附参考音频时即为多人 TTS（@voice1~3 分角色，可做播客对谈）。
