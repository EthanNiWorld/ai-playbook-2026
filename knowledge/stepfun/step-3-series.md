# Step 3 系列（StepFun）

> 最后更新: 2026-07-27
> 所属厂商: StepFun（阶跃星辰）
> 产品类别: MaaS
> 状态: Published

<!-- SUMMARY_START -->
**定位**: StepFun 语言基模主线，主打"Agent 效率"路线——低激活参数 + 原生多模态 + 工具增强，服务终端/Agent 成本时延敏感场景
**当前主推**: Step 3.7 Flash 🚩（2026-05-29，开源）
**适用**: Agent/Coding 工作流、多模态理解与执行（GUI/文档/图表）、Web+视觉搜索、高吞吐低成本推理
**不适用**: 追求绝对旗舰智力上限的场景（距 GPT 5.5 / Claude Opus 4.7 有差距）
<!-- SUMMARY_END -->

## 当前主推模型

| 模型 | 定位 | 上下文 | 特点 | 推出时间 |
|------|------|--------|------|----------|
| Step 3.7 Flash 🚩 | 旗舰（Flash 效率型） | 256K | 198B MoE / 11B 激活，原生图像+视频理解，开源 | 2026-05-29 |

> 📌 **历史模型**：Step 3（2025-07 WAIC 发布，首个全尺寸原生多模态推理模型）、Step 3.5 Flash（Step 3.7 Flash 前代，各项 benchmark 已被全面超越）。仍可调用，但已被 Step 3.7 Flash 取代，不建议新项目选用。
> 📌 **路线图**：Step 3.5 → Step 4 系列（印奇 2026-01 专访披露）[⚠️ 待验证]
> 📌 **版本代际**：Step-1（2023，千亿参数）→ Step-2 → Step 3（2025-07）→ Step 3.5 Flash → Step 3.7 Flash（当前主推）。

### Step 3.7 Flash

- 模型：step-3.7-flash
- 公司：StepFun（阶跃星辰）
- 时间：2026 年 5 月 29 日
- 尺寸：198B 总参数（196B 语言骨干 + 1.8B ViT），激活 11B。⚠️ 注意"196B"仅指语言骨干，总参数官方口径为 198B
- 上下文：256K tokens
- 场景：生产级 Agent / Coding / 多模态工作流
- 特点：原生图像+视频理解；reasoning_effort 三档（low/medium/high，Messages API 用 `output_config.effort`）；Advisor Mode（小模型主执行 + 大模型拐点顾问）
- 定价：输入 $0.20 / 输出 $1.15 per 1M tokens（缓存命中输入 $0.04）
- 开源：GitHub / HuggingFace / ModelScope

## 核心能力与限制

### 核心能力

| 能力 | 说明 |
|------|------|
| 原生多模态理解与执行 | 图像/视频/GUI/文档/图表理解后直接写代码或调用工具执行 |
| Web + 视觉搜索增强 | 搜索规划、证据过滤、信息合成为原生推理环节；视觉搜索补偿小模型参数知识不足，视觉识别达 5 倍规模模型水平 |
| 可靠工具调用与编排 | 驱动终端/浏览器/Office/搜索，长程运行保持连贯 |
| Agent 生态兼容 | 兼容 Claude Code、OpenClaw、Hermes Agent、KiloCode 等主流 Harness 与 Skills |
| Advisor Mode | 达 Claude Opus 4.6 97% coding 性能，单任务成本约 1/9（$0.19 vs $1.76） |
| 组合泛化涌现 | 视觉工具与非视觉工具组合使用、代码+GUI 自测行为，训练中未显式引导 |

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 旗舰能力差距 | Terminal-Bench 2.1 59.6 vs GPT 5.5 82.7 | Flash 定位换效率，绝对上限不及顶级闭源旗舰 |
| 参数知识容量 | 11B 激活 | 依赖 test-time 搜索/视觉工具补偿，弱网/无工具场景能力受限 |

### 关键 Benchmark（官方博客，2026-05-29）

| Benchmark | Step 3.7 Flash | 参照 |
|-----------|---------------|------|
| SWE-Bench Pro | 56.3 | 超 DeepSeek V4 Flash 55.6、Gemini 3.5 Flash 55.1 |
| Terminal-Bench 2.1 | 59.6 | GPT 5.5 为 82.7 |
| HLE w/ tool | 47.2% | — |
| ClawEval-1.1 | 67.1% | — |
| SimpleVQA w/ tool | 79.2% | 打平 GPT 5.5（79.1%） |

> 完整对比数据见官方博客 benchmark 表。

## 定价概览

| 模型 | 输入价格 | 输出价格 | 缓存价格 | 备注 |
|------|---------|---------|---------|------|
| step-3.7-flash | $0.20 /1M tokens | $1.15 /1M tokens | $0.04 /1M tokens（输入缓存命中） | — |

> 定价来源：https://platform.stepfun.ai/docs/en/guides/models/step-3.7-flash ，核实日期：2026-07-27

## 适用场景

### ✅ 适用

| 场景 | 推荐模型 | 说明 |
|------|----------|------|
| Agentic Coding | Step 3.7 Flash | 兼容主流 Harness，Advisor Mode 进一步提质 |
| 多模态 Agent（GUI/文档/图表） | Step 3.7 Flash | 原生视觉输入 + 工具执行闭环，含 Phone-use GUI 操作 |
| 深度搜索/研究 | Step 3.7 Flash | 搜索类 benchmark 接近更大规模模型 |
| 高并发低成本推理 | Step 3.7 Flash | 11B 激活、Flash 定价，终端/高频调用场景友好 |
| 本地/工作站部署 | Step 3.7 Flash | 128GB 统一内存 Mac Studio/MacBook Pro、NVIDIA DGX Station 等可运行 |

## 部署与生态

- **托管**：StepFun 开放平台（platform.stepfun.ai 全球 / platform.stepfun.com 中国）、OpenRouter、NVIDIA NIM
- **推理框架**：vLLM、SGLang、Hugging Face Transformers、llama.cpp
- **训练/定制**：NVIDIA NeMo 生态（AutoModel、Megatron Core、Megatron Bridge）

## 参考资料

- https://platform.stepfun.ai/docs/en/guides/models/step-3.7-flash （官方文档：参数/上下文/定价/reasoning effort）
- https://static.stepfun.com/blog/step-3.7-flash/ （官方博客：benchmark/Advisor Mode/生态）
- https://github.com/stepfun-ai/Step-3.7-Flash （开源仓库）

## Changelog
| 日期 | 变更内容 |
|------|----------|
| 2026-07-27 | 创建：基于 inbox/ai-knowledge-by-qoder-ai-native-agent-20260727.md 提炼，收录 Step 3.7 Flash 详情与版本代际 |
