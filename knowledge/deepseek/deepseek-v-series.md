# DeepSeek V 系列模型

> 最后更新: 2026-08-17
> 所属厂商: DeepSeek（深度求索）
> 产品类别: MaaS
> 状态: Published

**定位**: DeepSeek 通用旗舰模型系列，MoE 架构创新驱动，强调极致性价比与开源 SOTA
**当前主推**: V4-Pro GA（0813 快照）/ V4-Flash 正式版（0731 快照）——1M 上下文 + 384K 最大输出 + 峰谷分时定价
**适用**: 通用推理、Agentic Coding、长上下文、高并发企业场景
**不适用**: 超低延迟实时对话、需要严格中文合规的场景（需确认）

## 当前主推模型

| 模型 | 定位 | 上下文 | 特点 | 推出时间 |
|------|------|--------|------|----------|
| **DeepSeek-V4-Pro**（GA） | 🚩 全能旗舰 | 100 万 tokens，最大输出 384K | 1.6T MoE（49B 激活）；GA 版 Terminal-Bench 2.1 **87.9** / HLE w/ tools 60.0；原生 Responses API（Codex 适配） | Preview 2026.04.24 / **GA 2026.08.13** |
| **DeepSeek-V4-Flash**（正式版） | 极致轻量 | 100 万 tokens，最大输出 384K | 284B MoE（13B 激活）；0731 版超越 V4-Pro-Preview 全部基准（官方声明）；非峰输出 $0.66/M | Preview 2026.04.24 / **正式版 2026.07.31** |

> 📌 **历史模型**：DeepSeek-V3.2（2025.12，V3 最终版）、V3（2024.12）、V2（2024.05）、V1（2024.01）仍可调用，但已被 V4 系列取代，不建议新项目选用。

### DeepSeek-V4-Pro

- **模型**：deepseek-v4-pro（API 调用名不变，自动指向最新版；当前 GA 快照 0813）
- **公司**：DeepSeek
- **时间**：Preview 2026-04-24；**GA 正式版（0813 快照）2026-08-13** [来源: api-docs.deepseek.com/news/news260813]
- **尺寸**：1.6T MoE（49B 激活参数），GA 与 Preview 架构相同
- **上下文**：100 万 tokens；GA 版最大输出 **384K**（Preview 版 128K → 大幅提升）
- **App/Web**：GA 版"专家模式"可用
- **场景**：全能旗舰、Agentic Coding、重度推理、生产环境 Agent 任务
- **特点**：
  1. **开源 SOTA**：Agentic Coding 超越 Sonnet 4.5，接近 Opus 4.6（Preview 版口径）
  2. **原生 Responses API**（GA 新增）：支持 OpenAI Responses API 格式，专为 Codex 适配，一键配置脚本
  3. **三级 reasoning_effort**：low / high / max（V4-Pro 与 V4-Flash 均支持）
  4. **Agent 能力大幅增强**：GA 版生产环境 Agent 任务显著提升
  5. **华为芯片合作**：国产化推理部署选项
  6. **百炼平台调用**：US 节点，必须通过 dashscope-us.aliyuncs.com 调用

**GA 版 Benchmark** [来源: api-docs.deepseek.com/updates/ 2026-08-13]：

| 基准 | V4-Pro-Preview | V4-Pro-GA (0813) | 提升 |
|------|---------------|------------------|------|
| HLE (w/o tools) | — | **42.7** | — |
| HLE (w/ tools) | 48.2 | **60.0** | +11.8 |
| Terminal-Bench 2.1 | — | **87.9** | — |
| NL2Repo | — | **61.5** | — |
| Cybergym | — | **83.3** | — |
| DeepSWE | — | **62.7** | — |
| Toolathlon-Verified | — | **74.1** | — |
| Agents' Last Exam | — | **25.7** | — |
| AutomationBench (Public) | — | **31.8** | — |
| DSBench-FullStack | — | **71.1** | 内部基准 |
| DSBench-Hard | — | **67.2** | 内部基准 |

### DeepSeek-V4-Flash

- **模型**：deepseek-v4-flash（当前正式版快照 0731）
- **公司**：DeepSeek
- **时间**：Preview 2026-04-24；**正式版（0731 快照）2026-07-31** [来源: api-docs.deepseek.com/updates/ 2026-07-31]
- **尺寸**：284B MoE（13B 激活参数），与 Preview 版完全相同，仅重新后训练
- **上下文**：100 万 tokens，最大输出 **384K**
- **场景**：日常推理、轻量任务、高并发低成本场景
- **特点**：
  1. **极致性价比**：非峰输出 $0.66/M tokens（≈¥4.8）
  2. **越级表现**：0731 正式版已超越 V4-Pro-Preview 的全部基准（官方声明）
  3. **三级 reasoning_effort**：low / high / max
  4. **默认 thinking mode**：需注意开启后 TPM 实际吞吐下降 50-80%
  5. **百炼平台调用**：US 节点

**正式版 Benchmark（vs V4-Pro-GA）** [来源: api-docs.deepseek.com/updates/ 2026-07-31]：

| 基准 | V4-Flash-0731 | V4-Pro-GA (0813) |
|------|--------------|------------------|
| Terminal-Bench 2.1 | 82.7 | **87.9** |
| NL2Repo | 54.2 | **61.5** |
| Cybergym | 76.7 | **83.3** |
| DeepSWE | 54.4 | **62.7** |
| Toolathlon-Verified | 70.3 | **74.1** |
| Agents' Last Exam | 25.2 | **25.7** |
| AutomationBench (Public) | 25.1 | **31.8** |
| DSBench-FullStack | 68.7 | **71.1** |
| DSBench-Hard | 59.6 | **67.2** |

### DeepSeek-V3.2

- **模型**：deepseek-v3.2
- **公司**：DeepSeek
- **时间**：2025 年 12 月 1 日
- **尺寸**：671B MoE（37B 激活参数）
- **上下文**：128K+ tokens
- **场景**：通用推理、开源部署
- **特点**：V3 系列最终版，训练成本 557 万美元，开源 SOTA
- **⚠️ 注意**：V3.2 将于 2026.07.24 完全下线（deepseek-chat 路由已切到 V4-Flash）

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
- **特点**：首次引入 MLA + DeepSeekMoE 架构，引发国产大模型“价格战”，被称为“价格屠夫”

### DeepSeek-V1

- **模型**：deepseek-v1
- **公司**：DeepSeek
- **时间**：2024 年 1 月
- **尺寸**：67B
- **上下文**：128K+ tokens
- **场景**：首代开源通用模型
- **特点**：DeepSeek 首代开源模型

## 核心能力与限制

### 核心能力

| 能力 | 说明 |
|------|------|
| **开源 SOTA** | V4 全系列达开源最高水平 |
| **Agent 能力（GA）** | V4-Pro GA Terminal-Bench 2.1 87.9（超越 Qwen3.8-Max 86.6）、Cybergym 83.3、Toolathlon-Verified 74.1，Agent 能力第一梯队 |
| **长上下文** | V4 支持 100 万 tokens，GA 版最大输出 384K |
| **极致性价比** | V3 训练成本仅 557 万美元，对标 5 亿美元级模型；V4 峰谷定价非峰再减半 |
| **思考模式** | 支持 reasoning_effort 三级控制（low / high / max） |
| **Codex 生态兼容** | GA 版原生 Responses API（OpenAI 格式） |
| **架构创新** | MLA（多头潜在注意力）+ DeepSeekMoE 原创架构 |

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 地域限制 | V4 仅 US 节点可用 | V3.2 可通过新加坡（INTL）节点调用 |
| thinking mode 隐性成本 | 默认开启 | V4-Flash 开启后 TPM 实际吞吐下降 50-80% |
| 国内访问 | 需翻墙 | 国内无法直接访问 DeepSeek 官方 API |
| V3.2 已下线 | 2026.07.24 已执行 | deepseek-chat 路由已切至 V4-Flash |

## 适用场景

### ✅ 适用

| 场景 | 推荐模型 | 说明 |
|------|----------|------|
| Agentic Coding（重度） | V4-Pro GA | Terminal-Bench 2.1 87.9（超越 Qwen3.8-Max 86.6）、HLE w/ tools 60.0 |
| 日常推理 / 高并发 | V4-Flash | 极致性价比，非峰输出 $0.66/M（≈¥4.8） |
| 批量任务调度 | V4-Pro / V4-Flash | 非峰时段（UTC 01-04 / 06-10 以外）价格减半 |
| 开源部署 / 研究 | V3.2 / V3 | MIT 许可，完全开源 |
| 长上下文任务 | V4-Pro/Flash | 100 万 tokens 支持 |
| 企业高并发 | V4-Flash | 百炼 US 节点调用 |

### ❌ 不适用

| 场景 | 原因 |
|------|------|
| 超低延迟实时对话 | thinking mode 增加延迟 |
| 国内直接访问 | 需通过百炼平台绕道 |
| V3.2 持续使用 | 已于 2026.07.24 下线 |

## 定价（API，峰谷分时模式）

> 2026-08-16 16:00 UTC 生效 [来源: api-docs.deepseek.com/quick_start/pricing]。**峰时段 = 01:00-04:00 和 06:00-10:00 UTC，其余为非峰；非峰价 = 峰时价的一半**——鼓励将批量任务调度到非峰时段，优化资源利用

| 模型 | 类别 | 非峰 ($/M tokens) | 峰时 ($/M tokens) |
|------|------|-------------------|-------------------|
| **V4-Pro** | 输入（cache hit） | $0.022 | $0.044 |
| **V4-Pro** | 输入（cache miss） | $0.66 | $1.32 |
| **V4-Pro** | 输出 | $1.98 | $3.96 |
| **V4-Flash** | 输入（cache hit） | $0.007 | $0.014 |
| **V4-Flash** | 输入（cache miss） | $0.22 | $0.44 |
| **V4-Flash** | 输出 | $0.66 | $1.32 |

## 关键技术论文

| 论文 | 核心观点 | 影响 |
|------|----------|------|
| DeepSeek-V2 Paper | MLA + DeepSeekMoE 架构创新 | 引发国产大模型"价格战" |
| DeepSeek-V3 Paper | 557 万美元训练成本对标 5 亿级模型 | 颠覆"暴力堆算力"范式 |

## 参考资料

- [DeepSeek API 更新日志](https://api-docs.deepseek.com/updates/)（V4-Pro GA 0813 / V4-Flash 0731 发布与 benchmark 来源）
- [DeepSeek V4-Pro GA 发布公告](https://api-docs.deepseek.com/news/news260813)
- [DeepSeek API 定价页](https://api-docs.deepseek.com/quick_start/pricing)（2026-08-16 峰谷定价生效）
- [DeepSeek API 文档](https://www.alibabacloud.com/help/en/model-studio/deepseek-api)
- [DeepSeek 官网](https://www.deepseek.com)
- [百炼国际站 DeepSeek 授权](https://modelstudio.console.alibabacloud.com/ap-southeast-1?tab=doc#/doc/?type=model&url=2840915)

## Changelog

| 日期 | 变更内容 |
|------|----------|
| 2026-08-17 | 合并：inbox 四模型调研 - V4-Pro GA（0813：最大输出 384K、TB 2.1 87.9、HLE w/ tools 60.0、原生 Responses API、完整 benchmark 表）；V4-Flash 正式版（0731：仅重后训练、超越 V4-Pro-Preview 全部基准、benchmark 表）；新增峰谷分时定价章节（2026-08-16 生效）；V3.2 下线时态更新；核心能力/适用场景表同步 |
| 2026-06-29 | 模型演进时间倒序修正：V3.2（2025.12）移至 V3 前面，与知识库其他模型系列文档保持一致 |
| 2026-06-04 | 主推模型表精简：仅保留 V4-Pro + V4-Flash 为主推，V3.2/V3/V2/V1 移入历史模型标注 |
| 2026-05-28 | 新建文档，首次提炼 V 系列模型系列信息 |