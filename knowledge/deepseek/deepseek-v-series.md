# DeepSeek V 系列模型

> 最后更新: 2026-06-04
> 所属厂商: DeepSeek（深度求索）
> 产品类别: MaaS
> 状态: Published

**定位**: DeepSeek 通用旗舰模型系列，MoE 架构创新驱动，强调极致性价比与开源 SOTA
**当前主推**: V4-Pro / V4-Flash（2026.04）
**适用**: 通用推理、Agentic Coding、长上下文、高并发企业场景
**不适用**: 超低延迟实时对话、需要严格中文合规的场景（需确认）

## 当前主推模型

| 模型 | 定位 | 上下文 | 特点 | 推出时间 |
|------|------|--------|------|----------|
| **DeepSeek-V4-Pro** | 🚩 全能旗舰 | 100 万 tokens | 开源 SOTA，1.6T MoE（49B 激活），Agentic Coding 超越 Sonnet 4.5 | 2026.04.24 |
| **DeepSeek-V4-Flash** | 极致轻量 | 100 万 tokens | 284B MoE（13B 激活），性价比极高 | 2026.04.24 |

> 📌 **历史模型**：DeepSeek-V3.2（2025.12，V3 最终版）、V3（2024.12）、V2（2024.05）、V1（2024.01）仍可调用，但已被 V4 系列取代，不建议新项目选用。

### DeepSeek-V4-Pro

- **模型**：deepseek-v4-pro
- **公司**：DeepSeek
- **时间**：2026 年 4 月 24 日
- **尺寸**：1.6T MoE（49B 激活参数）
- **上下文**：100 万 tokens，支持思考模式（reasoning_effort 参数）
- **场景**：全能旗舰、Agentic Coding、重度推理任务
- **特点**：
  1. **开源 SOTA**：Agentic Coding 超越 Sonnet 4.5，接近 Opus 4.6
  2. **华为芯片合作**：明确与华为芯片合作，国产化推理部署选项
  3. **百炼平台调用**：US 节点，必须通过 dashscope-us.aliyuncs.com 调用

### DeepSeek-V4-Flash

- **模型**：deepseek-v4-flash
- **公司**：DeepSeek
- **时间**：2026 年 4 月 24 日
- **尺寸**：284B MoE（13B 激活参数）
- **上下文**：100 万 tokens，支持思考模式
- **场景**：日常推理、轻量任务、高并发低成本场景
- **特点**：
  1. **极致性价比**：适合高并发低延迟场景
  2. **默认 thinking mode**：需注意开启后 TPM 实际吞吐下降 50-80%
  3. **百炼平台调用**：US 节点

### DeepSeek-V3

- **模型**：deepseek-v3
- **公司**：DeepSeek
- **时间**：2024 年 12 月
- **尺寸**：671B MoE（37B 激活参数）
- **上下文**：128K+ tokens
- **场景**：通用推理、开源 SOTA
- **特点**：训练成本仅 557 万美元，对标 GPT-4o/Claude 3.5

### DeepSeek-V2

- **模型**：deepseek-v2
- **公司**：DeepSeek
- **时间**：2024 年 5 月
- **尺寸**：236B MoE（21B 激活参数）
- **上下文**：128K+ tokens
- **场景**：通用推理
- **特点**：首次引入 MLA + DeepSeekMoE 架构，引发国产大模型"价格战"，被称为"价格屠夫"

### DeepSeek-V1

- **模型**：deepseek-v1
- **公司**：DeepSeek
- **时间**：2024 年 1 月
- **尺寸**：67B
- **上下文**：128K+ tokens
- **场景**：首代开源通用模型
- **特点**：DeepSeek 首代开源模型

### DeepSeek-V3.2

- **模型**：deepseek-v3.2
- **公司**：DeepSeek
- **时间**：2025 年 12 月 1 日
- **尺寸**：671B MoE（37B 激活参数）
- **上下文**：128K+ tokens
- **场景**：通用推理、开源部署
- **特点**：V3 系列最终版，训练成本 557 万美元，开源 SOTA
- **⚠️ 注意**：V3.2 将于 2026.07.24 完全下线（deepseek-chat 路由已切到 V4-Flash）

## 核心能力与限制

### 核心能力

| 能力 | 说明 |
|------|------|
| **开源 SOTA** | V4 全系列达开源最高水平 |
| **长上下文** | V4 支持 100 万 tokens |
| **极致性价比** | V3 训练成本仅 557 万美元，对标 5 亿美元级模型 |
| **思考模式** | 支持 reasoning_effort 参数控制推理强度 |
| **架构创新** | MLA（多头潜在注意力）+ DeepSeekMoE 原创架构 |

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 地域限制 | V4 仅 US 节点可用 | V3.2 可通过新加坡（INTL）节点调用 |
| thinking mode 隐性成本 | 默认开启 | V4-Flash 开启后 TPM 实际吞吐下降 50-80% |
| 国内访问 | 需翻墙 | 国内无法直接访问 DeepSeek 官方 API |
| V3.2 下线 | 2026.07.24 | 需迁移至 V4 系列 |

## 适用场景

### ✅ 适用

| 场景 | 推荐模型 | 说明 |
|------|----------|------|
| Agentic Coding（重度） | V4-Pro | 超越 Sonnet 4.5，接近 Opus 4.6 |
| 日常推理 / 高并发 | V4-Flash | 极致性价比 |
| 开源部署 / 研究 | V3.2 / V3 | MIT 许可，完全开源 |
| 长上下文任务 | V4-Pro/Flash | 100 万 tokens 支持 |
| 企业高并发 | V4-Flash | 百炼 US 节点调用 |

### ❌ 不适用

| 场景 | 原因 |
|------|------|
| 超低延迟实时对话 | thinking mode 增加延迟 |
| 国内直接访问 | 需通过百炼平台绕道 |
| V3.2 持续使用 | 即将于 2026.07.24 下线 |

## 关键技术论文

| 论文 | 核心观点 | 影响 |
|------|----------|------|
| DeepSeek-V2 Paper | MLA + DeepSeekMoE 架构创新 | 引发国产大模型"价格战" |
| DeepSeek-V3 Paper | 557 万美元训练成本对标 5 亿级模型 | 颠覆"暴力堆算力"范式 |

## 参考资料

- [DeepSeek API 文档](https://www.alibabacloud.com/help/en/model-studio/deepseek-api)
- [DeepSeek 官网](https://www.deepseek.com)
- [百炼国际站 DeepSeek 授权](https://modelstudio.console.alibabacloud.com/ap-southeast-1?tab=doc#/doc/?type=model&url=2840915)

## Changelog

| 日期 | 变更内容 |
|------|----------|
| 2026-06-04 | 主推模型表精简：仅保留 V4-Pro + V4-Flash 为主推，V3.2/V3/V2/V1 移入历史模型标注 |
| 2026-05-28 | 新建文档，首次提炼 V 系列模型系列信息 |