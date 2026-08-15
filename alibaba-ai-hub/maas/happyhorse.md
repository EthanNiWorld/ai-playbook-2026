# HappyHorse

> 最后更新: 2026-08-14
> 所属厂商: 阿里巴巴（淘天集团 ATH 创新单元）
> 产品类别: MaaS

**定位**: 阿里淘天 ATH 创新单元出品的 AI 视频生成模型，15B 单流 Transformer + 8 步 DMD-2 蒸馏，音视频联合单次生成。2026 年 4 月匿名登顶 Artificial Analysis 盲测双榜首后公开身份
**当前主推**: HappyHorse 1.1（T2V / I2V / R2V），百炼已正式商用
**适用**: 电商商品视频、短视频创作、多语言口型同步内容、批量素材生产
**不适用**: 本地自部署（权重未开源）、长视频（单段 3-15 秒）

## 当前主推模型

| 模型 | 定位 | 能力 | 特点 | 推出时间 |
|------|------|------|------|------|
| 🚩 **HappyHorse-1.1-T2V** | 文生视频 | 文本→视频+音频 | 1.1 版全面升级，动态表现力、主体一致性、指令遵循、视觉质感和音频能力系统性升级 | 2026-06-22 |
| 🚩 **HappyHorse-1.1-I2V** | 图生视频 | 图像→视频 | 同上 | 2026-06-22 |
| 🚩 **HappyHorse-1.1-R2V** | 参考生视频 | 多参考图→视频 | 同上 | 2026-06-22 |

> 📌 **历史版本**：HappyHorse 1.0 系列（T2V/I2V/R2V/Video-Edit，2026-04-27 上架）仍可调用，但 1.1 系列在多维度全面升级，推荐新项目使用 1.1 版本。

### HappyHorse 1.1 升级要点（vs 1.0）

| 升级维度 | 说明 |
|----------|------|
| 动态表现力 | 视频运动流畅度与真实感提升 |
| 主体一致性 | 多镜头/参考图生成中角色外观保持更稳定 |
| 指令遵循 | 更精准地执行文本提示词 |
| 视觉质感 | 画面质量与细节渲染提升 |
| 音频能力 | 声音生成质量与音视频同步提升 |

> 来源：https://help.aliyun.com/zh/model-studio/newly-released-models + https://www.qbitai.com/2026/06/437317.html

### 技术架构

- 架构：15B 参数，40 层单流 Self-Attention Transformer，无 Cross-Attention，所有模态编码为统一 token 序列 [来源: remio.ai, help.apiyi.com]
- 推理：DMD-2 蒸馏，仅 8 步去噪（传统 Diffusion 需 50-100 步）[来源: remio.ai]
- 音频：音视频联合单次前向生成，非先视频后配音 [来源: remio.ai]
- 速度：H100 上 5 秒 256p ≈ 2s，1080p ≈ 38s [来源: remio.ai]
- 分辨率：最高 1080p@30fps [来源: jxp.com]
- 时长：3-15 秒 [来源: remio.ai]
- 画幅：16:9, 9:16, 1:1, 4:3 [来源: fal.ai]

### 定价

> 定价标准：阿里云国际站新加坡节点，2026-07-30 核实

| 规格 | 列表价 | 限时 6 折后 | 5秒视频成本（折后） | 来源 |
|------|--------|-----------|--------------------|------|
| 1.1 T2V/I2V 720P | $0.14/秒 | $0.084/秒 | $0.42 | [官方定价页](https://www.alibabacloud.com/help/en/model-studio/model-pricing) |
| 1.1 T2V/I2V 1080P | $0.18/秒 | $0.108/秒 | $0.54 | 同上 |
| 1.0 T2V/I2V 720P | $0.14/秒 | 限时 8 折 $0.112/秒 | $0.56 | 同上 |
| 1.0 T2V/I2V 1080P | $0.24/秒 | 限时 8 折 $0.192/秒 | $0.96 | 同上 |

> 计费公式：总费用 = 生成数量 × 视频时长(秒) × 单价。失败不收费。限时折扣截止日期以控制台为准。
> 💡 1.1 不仅能力升级，1080P 列表价还从 1.0 的 $0.24/秒降至 $0.18/秒，叠加 6 折后性价比显著优于 1.0。

## 核心能力与限制

### 核心能力

| 能力 | 说明 |
|------|------|
| **音视频联合生成** | 同一 pass 出视频+音频，天然同步，无需后处理配音 [来源: remio.ai] |
| **7语言口型同步** | 中/英/粤/日/韩/德/法，Word Error Rate 14.60% [来源: remio.ai] |
| **多镜头叙事一致性** | ~87% 多镜头角色/光照/风格一致性，当前公开模型最高 [来源: jxp.com] |
| **AA 盲测历史双冠** | 2026 年 4-6 月口径：T2V Elo 1357 / I2V Elo 1415 双榜 #1；2026-08-14 核实 T2V（With Audio）榜 1.1 已回落至 #5（Elo 1147），前四为 Gemini Omni Flash（1241）/ MiniMax H3（1238）/ Seedance 2.0（1222）/ Wan2.7-260612（1159）[来源: Artificial Analysis] |
| **VBench 高分** | 综合 84.32，较前代榜首提升 7.8% [来源: remio.ai] |
| **多平台商用** | 百炼 API + fal.ai API + 千问App 三通道 [来源: developer.aliyun.com, fal.ai] |

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 权重开源 | ❌ coming soon | 自 4 月承诺以来未发布 [来源: wavespeed.ai 2026.04.08] |
| 本地部署 | 不可行 | 15B 参数，即便放权重也需专业 GPU |
| 音频场景 | 略逊 Seedance 2.0 / MiniMax H3 | AA T2V 带音频榜当前 #5（2026-08-14 核实）[来源: Artificial Analysis] |
| 长视频 | 单段 ≤15 秒 | 更长内容需手动拼接 |
| 液体物理 | 较弱 | 水流/流体模拟效果不佳 [来源: jxp.com] |

## 适用场景

### ✅ 适用

| 场景 | 推荐模型 | 说明 |
|------|----------|------|
| 电商商品展示 | I2V | 静态商品图转动图（AA I2V 曾 #1，最新排名待复核） |
| 纯视觉短视频 | T2V | AA T2V 曾登顶（2026-04~06），当前 #5，画面质量仍属第一梯队 |
| 多语言营销 | T2V | 7语言口型同步，一条素材覆盖多市场 |
| 批量素材生产 | T2V 720P | 5秒约 $0.42/条（6 折后，新加坡节点），成本可精确预估 |
| 创作者快速迭代 | 千问App | 免费体验额度 |

### ❌ 不适用

| 场景 | 原因 | 替代方案 |
|------|------|----------|
| 带对话的长内容 | 音频略逊，≤15秒 | Seedance 2.0 或 Veo 3.1 |
| 本地微调部署 | 权重未开源 | Wan 2.7（已开源+LoRA指南） |
| 专业影视后期 | 无 Runway 级别控制面 | Runway Gen-4.5 |

## 接入方式

| 方式 | 说明 | 适用场景 |
|------|------|----------|
| 百炼 API | DashScope，按秒计费 | 企业生产集成 |
| fal.ai API | 4 端点（T2V/I2V/Ref/Edit），Python/JS SDK | 国际开发者 |
| 千问 App | 首页 HappyHorse 胶囊入口，有免费额度 | 个人体验 |

## 竞品对比

| 维度 | HappyHorse 1.0 | Wan 2.7（同属阿里） | Seedance 2.0（字节） |
|------|---------------|-------------------|---------------------|
| 团队 | 淘天 ATH | 阿里云通义 | 字节跳动 |
| AA T2V Elo（2026-08-14） | 1.1 #5（1147）/ 1.0 #6（1126），曾双榜 #1 | #4（1159，Wan2.7-260612） | #3（1222） |
| AA I2V Elo | 1.1 曾 #1 1415（最新排名待复核） | 已参赛（排名待复核） | 待复核 |
| 音频 | 单次联合生成 | 需外部模型 | 双分支+Cross-Attention |
| 开源 | ❌ coming soon | ✅ Apache 2.0 | ❌ |
| 百炼定价（新加坡） | 1.1 720P $0.14/s 限时 6 折 | 按量付费 | 火山引擎 ¥~1.0/s |
| LoRA | 宣称支持，不可实操 | ✅ 官方指南 | ❌ |

## 团队背景

HappyHorse 由张迪团队开发，该团队此前在快手主导了 Kling AI（2024-2025 年国内最流行的 AI 视频工具之一）。2025 年底团队整体加入阿里淘天集团 ATH 创新单元，用更大资源重建了视频模型。[来源：remio.ai, CNBC]

HappyHorse 与 Wan（万相）分属阿里不同事业群——淘天 vs 阿里云，是阿里内部"赛马机制"的体现。HappyHorse 承诺 Apache 2.0 开源，但截至 2026 年 5 月 31 日，GitHub 和 HuggingFace 仍显示 "coming soon"。[来源：wavespeed.ai]

## 参考资料

- [HappyHorse T2V API 官方文档](https://help.aliyun.com/zh/model-studio/happyhorse-text-to-video-api-reference)
- [HappyHorse I2V API 官方文档](https://help.aliyun.com/zh/model-studio/happyhorse-image-to-video-api-reference)
- [HappyHorse 参考生视频 API 官方文档](https://help.aliyun.com/zh/model-studio/happyhorse-reference-to-video-api-reference)
- [百炼产品月刊 2026年4月 - HappyHorse 上架](https://developer.aliyun.com/article/1732596)
- [HappyHorse 上架百炼公告](https://developer.aliyun.com/article/1731495)
- [Artificial Analysis Video Arena](https://artificialanalysis.ai/video/leaderboard/text-to-video)
- [HappyHorse 定价分析](https://help.apiyi.com/en/happyhorse-pricing-vs-seedance-2-comparison-en.html)
- [HappyHorse 技术架构分析](https://help.apiyi.com/en/happyhorse-model-mystery-ai-video-lmarena-analysis-en.html)
- [HappyHorse 开源状态追踪](https://wavespeed.ai/blog/posts/is-happyhorse-1-0-open-source-2026/)
- [fal.ai HappyHorse 官方发布](https://www.prnewswire.com/news-releases/fal-launches-happyhorse-1-0--the-1-ranked-ai-video-model-as-official-api-partner-302755003.html)

## Changelog
| 日期 | 变更内容 |
|------|----------|
| 2026-08-14 | 校验修复：AA 盲测排名更新（T2V With Audio 榜 1.1 #5 / 1.0 #6，Wan2.7-260612 反超至 #4，前三 Gemini Omni Flash / MiniMax H3 / Seedance 2.0），“双冠”改为历史口径；核心能力/限制/场景/竞品表同步 |
| 2026-07-30 | 校验修复：定价切换为国际站新加坡节点官方口径（1.1 720P $0.14/1080P $0.18 限时 6 折），替换第三方信源旧价 ¥0.9/¥1.6（1.0 口径）；批量成本与竞品表同步更新 |
| 2026-06-22 | 合并：百炼上新架与量子位报道 — 新增 HappyHorse 1.1 系列（T2V/I2V/R2V，2026-06-22 百炼上架），五维度系统升级；更新主推表为 1.1 系列，1.0 移入历史版本 |
| 2026-05-31 | 初始创建：团队背景、技术架构、AA/VBench 评测、百炼定价、4个API端点、竞品对比、限制与适用场景 |