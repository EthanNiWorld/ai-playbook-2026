# QoderWork

> 最后更新: 2026-06-02
> 所属厂商: 阿里云
> 产品类别: AI App
> 状态: Published

<!-- SUMMARY_START -->
**定位**: 桌面端通用智能体助手，Qoder IDE 生态衍生产品，将 Agent 能力从代码领域扩展到日常工作场景
**适用**: 文档/表格/PPT 生成、本地文件整理、数据分析、照片管理
**不适用**: 需要 7×24 持续运行的场景（用 MuleRun）、云端跨系统集成、HTML 网站发布
**数据主权**: QoderWork 本身不一定数据不出境；如需数据不出境须选择 **QoderWork CN** 版本
**竞品**: Claude Cowork（Anthropic 桌面通用 Agent，Claude Code 能力扩展到日常办公，2026.01.12）[来源: anthropic.com/product/claude-cowork]
**常搭配**: Qoder（Coding 生态）、MuleRun（云端场景互补）
<!-- SUMMARY_END -->

## 产品原理解析

### 一句话定位

QoderWork 是一款**桌面端智能工作助手**——通过自然语言对话，直接操作本地文件和应用，自动完成任务并交付结果 [来源: help.aliyun.com]

### 核心能力

| 能力 | 说明 | 来源 |
|------|------|------|
| 自主规划执行 | 理解复杂任务意图，自动拆解执行步骤，实时反馈进展 | help.aliyun.com |
| 本地文件直连 | 直接访问授权工作目录，本地处理文件 | help.aliyun.com |
| 沙盒环境 | 预制隔离虚拟环境，面向高隐私要求场景 | zhuanlan.zhihu.com |
| 技能广场 | 内置主流 MCP 工具，支持自定义 Skills | help.aliyun.com |
| 模型分级 | 标准档（轻量任务）/ 旗舰档（深度分析），按需选择降低成本 | zhuanlan.zhihu.com |
| 平台支持 | macOS + Windows（2026.03 全面开放） | zhuanlan.zhihu.com |

### 定价

共享 Qoder Credits [来源: docs.qoder.com]：

| 方案 | 价格 |
|------|------|
| 社区版 | 免费 |
| Pro | $20/月 |
| Pro+ | $60/月 |
| Ultra | 更高额度 |

### 典型场景

| 场景 | 说明 |
|------|------|
| 文件整理 | 自动识别文件类型，智能整理项目文件 |
| 数据分析 | 分析数据结构，生成统计报表与可视化图表 |
| 文档创作 | 撰写报告、制作演示文稿、处理表格数据 |
| 照片管理 | 按时间、地点、主题自动分类 |

## 与 MuleRun 的深度对比分析

详见 [MuleRun 文档 — 深度对比分析](mulerun.md#与-qoderwork-的深度对比分析)

**核心差异一句话**：QoderWork 是本地桌面方案（Qoder IDE 生态衍生），MuleRun 是云端方案（全球版数据出境，骡子快跑 = MuleRun CN 数据不出境）；QoderWork 如需数据不出境须选择 **QoderWork CN**。

> ⚠️ 对比分析中含用户补充信息（HTML 发布/内置生图生视频/骡子快跑 CN 版关系等），已标注 ⚠️ 待官方验证。

## Changelog

| 日期 | 变更内容 |
|------|----------|
| 2026-06-02 | 深度对比分析重构：更新引用链接至增强版对比分析；标注用户补充信息待验证 |
| 2026-06-02 | 增量更新：强化"Qoder IDE 生态衍生"定位；修正数据主权说明（QoderWork 本身不保证数据不出境，须选 QoderWork CN）；不适用场景新增 HTML 网站发布 |
| 2026-06-01 | Draft→Published，补充核心能力、定价、场景（来源：ali-knowledge-miner 校验后入库） |
| 2026-04-20 | 初始 Draft |
