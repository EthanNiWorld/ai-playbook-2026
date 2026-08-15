# 万相 (Wan)

> 最后更新: 2026-08-14
> 所属厂商: 阿里云
> 产品类别: MaaS

**定位**: 阿里云通义实验室多模态生成模型（视频为主，图像线已移交 Qwen-Image），开源（Apache 2.0）+ 百炼商业 API 双轨
**当前主推**: Wan2.7 视频系列（Wan2.7-T2V / Wan2.7-I2V / Wan2.7-R2V / Wan2.7-VideoEdit），Wan2.6 仍可用
**适用**: AI视频生成、图像创作、营销素材、短视频制作、角色一致性内容
**不适用**: 高精度工业设计、实时视频流处理

## 当前主推模型

| 模型 | 定位 | 新增能力 | 特点 |
|------|------|------|------|
| **Wan2.7-T2V** | 文生视频 | 2-15秒时长，首尾帧控制 | 影视级画质，DiT 架构 |
| **Wan2.7-I2V** | 图生视频 | 9宫格多图输入，首尾帧控制 | 角色/场景一致性大幅提升 |
| **Wan2.7-R2V** | 参考生视频 | 主体+声音参考 | 角色外观+声音一致性 [来源: wavespeed.ai] |
| **Wan2.7-VideoEdit** | 指令编辑 | 自然语言指令修改视频 | 背景替换、光照调整、服装变更 [来源: help.aliyun.com] |

> 📌 **历史模型（已归档）**：Wan*-Image 图像生成线（含 wan2.7-image-pro / wan2.7-image）后续统一由 Qwen-Image 系列（当前 qwen-image-3.0-pro）代替，图像生成需求请直接选用 Qwen-Image，Wan*-Image 不再推荐新项目使用 [来源: 用户口述，2026-08-04] ⚠️ 待官方验证

> Wan2.6 系列（2026.01）仍可通过百炼调用，适合已搭建稳定管线的团队。
>
> 📌 **快照更新**：2026-07-01 上线 `wan2.7-t2v-2026-06-12` / `wan2.7-r2v-2026-06-12`（演绎能力升级快照）；官方口径 R2V 支持最大 5 个图/视频混合参考 + 音频音色参考 [来源: help.aliyun.com 上新页]
>
> 📌 **新一代上线**：wan3.0-video 已于 2026-08-06 上线百炼（All-in-One：统一文生视频/图生视频（首帧/首尾帧）/参考生视频，最长可生成 30 秒视频）；国际站上新表暂未收录，部署节点与定价待确认 [来源: help.aliyun.com 上新页，2026-08-14 核实]

### Wan2.7 核心升级点 vs Wan2.6

| 升级项 | Wan2.6 | Wan2.7 |
|--------|--------|--------|
| 视频时长 | 最长约10秒 | 2-15秒 [来源: help.aliyun.com] |
| I2V 输入 | 单图首帧 | 9宫格多图 + 首尾帧双图 [来源: wavespeed.ai] |
| 角色控制 | R2V 角色扮演 | 主体+声音双参考 [来源: wavespeed.ai] |
| 视频编辑 | 不支持 | 自然语言指令编辑 [来源: help.aliyun.com] |
| 架构 | Diffusion MoE（继承自2.2） | DiT Full Attention（延续2.6），无架构大改 [来源: wavespeed.ai] |
| 开源 | Apache 2.0（Wan2.1/2.2权重） | Apache 2.0，权重在 GitHub/HuggingFace [来源: pinggy.io May 2026] |
| 定价参考 | 按量付费 | 新加坡节点：wan2.7-t2v/i2v 720P $0.10/秒、1080P $0.15/秒 [来源: alibabacloud.com 官方定价页，2026-07-30 核实] |

### 技术架构
- 架构：DiT (Diffusion Transformer)，Full Attention 机制捕捉长程时空依赖 [来源: wavespeed.ai]
- MoE：~27B 总参数 / ~14B 每步激活（继承自 2.2）[来源: pinggy.io May 2026]
- 轻量版：T2V-1.3B 仅需 8.19GB VRAM，消费级 GPU 可跑 [来源: pinggy.io]
- ComfyUI：社区集成已就绪 [来源: alici.ai]

## 核心能力与限制

### 核心能力

| 能力 | 说明 |
|------|------|
| 文生视频 | 文本描述生成影视级视频 |
| 图生视频 | 首帧/参考图驱动视频生成 |
| 角色扮演 | 国内首个支持角色扮演的视频模型 |
| 音画同步 | 视频+音效同步生成 |

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 视频时长 | 2-15 秒 | Wan2.7-T2V；Wan2.6 约 10 秒 |
| 分辨率 | 最高1080P | 与输入图片相关 |
| 图片大小 | ≤ 20MB | Wan2.6系列 |

## 适用场景

### ✅ 适用

| 场景 | 推荐模型 | 说明 |
|------|----------|------|
| 短视频创作 | Wan2.7-T2V | 文字直接生成视频，2-15 秒灵活控制 |
| 营销素材（图像） | Qwen-Image 系列 | 图像生成统一由 Qwen-Image 承接（当前 qwen-image-3.0-pro）[来源: 用户口述] |
| 产品展示 | Wan2.7-I2V | 9 宫格多图输入 + 首尾帧控制，角色一致性大幅提升 |
| 创意角色 | Wan2.7-R2V | 主体+声音双参考，角色外观+声音一致性 |

## 接入方式

| 方式 | 说明 | 适用场景 |
|------|------|----------|
| 百炼 API | DashScope API，按秒计费 | 生产集成 |
| 开源权重 | GitHub/HuggingFace 下载，Apache 2.0 | 本地部署、微调、ComfyUI |
| 万相平台 | wanx.biz.aliyun.com 可视化创作 | 非技术用户 |

## 竞品对比

| 维度 | Wan 2.7 | HappyHorse 1.1（同属阿里） |
|------|---------|---------------------------|
| 团队 | 阿里云通义实验室 | 阿里淘天 ATH（前快手 Kling 团队） |
| 架构 | DiT MoE ~27B | 15B 单流 Transformer + 8步蒸馏 |
| 音频 | 需外部模型 | 音视频联合单次生成 |
| AA 盲测（2026-08-14） | Wan2.7-260612 已参赛：T2V（With Audio）#4（Elo 1159） | 曾双冠；1.1 当前 #5（1147） |
| 开源 | ✅ 权重已发布 | ❌ coming soon |
| 百炼商用 | ✅ 新加坡 720P $0.10/s、1080P $0.15/s | ✅ 1.1 720P $0.14/s、1080P $0.18/s，限时 6 折 |
| LoRA 微调 | ✅ 百炼官方指南 | 宣称支持，权重未出不可实操 |

## 参考资料

- [万相2.7 T2V API](https://help.aliyun.com/zh/model-studio/text-to-video-api-reference)
- [万相2.7 I2V API](https://help.aliyun.com/zh/model-studio/image-to-video-general-api-reference)
- [万相2.7 R2V API](https://help.aliyun.com/zh/model-studio/wan-video-to-video-api-reference)
- [万相2.7 视频编辑 API](https://help.aliyun.com/zh/model-studio/wan-video-editing-api-reference)
- [Wan 2.7 功能分析](https://wavespeed.ai/blog/posts/wan-2-7-features-api-upgrade/)
- [Wan 2.7 定价参考](https://evolink.ai/zh/blog/wan-api-pricing-guide)
- [万相官网](https://wanx.biz.aliyun.com/wan)
- [Wan GitHub](https://github.com/Wan-Video)

## Changelog
| 日期 | 变更内容 |
|------|----------|
| 2026-08-14 | 校验修复：补记 wan3.0-video 上线（2026-08-06，All-in-One，最长 30 秒）；AA 盲测更新——Wan2.7-260612 参赛 T2V（With Audio）榜 #4（Elo 1159）反超 HappyHorse-1.1（#5），竞品表同步 |
| 2026-08-04 | 合并：用户口述 — Wan*-Image 图像生成线归档，统一由 Qwen-Image 系列（qwen-image-3.0-pro）代替；移出主推表与能力/场景表，定位描述同步收敛为视频为主 |
| 2026-07-30 | 校验修复：定价切换为国际站新加坡节点官方口径（wan2.7-t2v/i2v 720P $0.10/秒）替换第三方 evolink 价；竞品表 HappyHorse 更新为 1.1 新加坡定价（$0.14/$0.18 限时 6 折）；补记 2026-07-01 新快照与 R2V 官方参考口径 |
| 2026-07-20 | 校验修复：竞品表 HappyHorse 1.0 → 1.1（1.1 系列 2026-06-22 上架，已为当前主推） |
| 2026-06-09 | 修正：核心限制表视频时长与 Wan2.7 一致（2-15 秒）；适用场景表从 Wan2.6 更新为 Wan2.7 系列 |
| 2026-05-31 | 更新至 Wan2.7：新增首尾帧控制、9宫格I2V、指令编辑、主体+声音参考等功能；补充技术架构（DiT/MoE）、竞品对比（vs HappyHorse）、定价参考、官方API文档链接 |
| 2026-04-20 | 按_maas_template重构，Wan2.6-Video/Image拆分 |
