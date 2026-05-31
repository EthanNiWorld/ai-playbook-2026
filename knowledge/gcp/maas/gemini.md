# Gemini

> 最后更新: 2026-05-31
> 所属厂商: GCP
> 产品类别: MaaS

**定位**: Google 自研多模态大模型系列，原生支持文本+图像+音频+视频多模态输入输出
**适用**: 多模态理解与生成、企业知识管理、Agent 基础模型、代码生成
**不适用**: 需要私有化部署的场景（Gemini 仅通过 API / GCP 平台提供）
**当前主推**: Gemini 3.x 系列，最新旗舰 Gemini 3 Pro（2026.05.22），I/O 2026 发布 Gemini 3.5 Flash（轻量推理）、Gemini Omni Flash（原生音视频），Gemini 3.5 Pro 预计 2026.06 发布

## 当前主推模型

| 模型 | 定位 | 核心特点 | 推出/更新时间 |
|------|------|------|------|
| **Gemini 3 Pro** | 旗舰（最大能力） | 最复杂推理、编程、多模态深度理解 | 2026.01，最后更新 2026.05.22 |
| **Gemini 3.5 Flash** | 轻量（高速低成本） | I/O 2026 首发，Flash 速度 + Pro 级 benchmark，4x 速度，Agentic Coding 超 3.1 Pro | 2026.05.19 |
| **Gemini Omni Flash** | 原生音视频多模态 | 端到端音频/视频原生理解，实时语音交互 | 2026.05.19 |
| **Gemini 3.1 Pro** | 上代旗舰 | 编程、分析能力强，已被 3 Pro / 3.5 Flash 超越 | 2026.02.19 |
| **Gemini 3.1 Flash** | 上代轻量 | 均衡性价比，适合批量推理 | 2026 Q1 |

> ⚠️ Gemini 2.5 系列（Pro/Flash/Deep Think）为 2025 年中发布，**已非最新代**。2.5 Pro 更新至 2025.06.27，2.5 Flash 更新至 2025.09.26。详见 [Google DeepMind Model Cards](https://deepmind.google/models/model-cards/)

## 核心能力与限制

### 核心能力

| 能力 | 说明 |
|------|------|
| **原生多模态** | 文本+图像+音频+视频统一理解与生成，不需要拼接多个模型 |
| **超长上下文** | 1M+ tokens，支持整仓库代码/超长文档一次性分析 |
| **Agent 基座** | Gemini Enterprise Agent Platform 的核心引擎，ADK 2.0 默认模型 |
| **TPU 原生优化** | 在 TPU 8t/8i 上推理效率极致优化，推理性价比领先 |
| **MCP 原生支持** | 通过 MCP 协议调用 GCP 全系服务 |

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 部署方式 | 仅 API / GCP 平台 | 不支持私有化下载部署 |
| API 双轨 | `google.genai` + `vertexai` 两套 API | 开发者需根据场景选择，Google 已确认将长期共存 |
| 中文能力 | 强但非母语级 | 中文场景优先考虑 Qwen / DeepSeek 作为补充 |

## 适用场景

### ✅ 适用

| 场景 | 推荐模型 | 说明 |
|------|----------|------|
| 多模态企业知识库 | 3 Pro | 图文音视统一理解，配合 Knowledge Catalog |
| Agent 规模化部署 | 3.5 Flash | 高吞吐、低延迟、Pro 级 benchmark，适合多 Agent 并发 |
| 复杂推理/编程 | 3 Pro | 对标 Claude Opus / GPT-5.x |
| 实时音视频交互 | Omni Flash | 原生端到端音频/视频理解 |
| 代码辅助 | 3.5 Flash | Flash 速度 + 超 3.1 Pro 的 Agentic Coding |
| Google Workspace AI | 3.1 Flash / 3 Pro | 内嵌于 Gmail/Docs/Sheets 的 AI 能力 |

## 平台交付方式

Gemini 通过 **Gemini Enterprise Agent Platform** 统一交付（见 [`vertex-ai.md`](../ai-platform/vertex-ai.md)）。开发者可选两种接入路径：

| 路径 | 接口 | 适用 |
|------|------|------|
| **Gemini API / AI Studio** | `google.genai` | 快速原型、单次推理、个人开发者 |
| **Agent Platform** | `vertexai`（原 Vertex AI API） | 企业级 Agent 构建、生产部署、治理优化 |

## Changelog
| 日期 | 变更内容 |
|------|----------|
| 2026-05-31 | 修正：Gemini 2.5→3.x 系列为最新代。新增 Gemini 3 Pro、3.5 Flash、Omni Flash、3.1 Pro/Flash。标注 Gemini 3.5 Pro 预计 2026.06 发布 |
