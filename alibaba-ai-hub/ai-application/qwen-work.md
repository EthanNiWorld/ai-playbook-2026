# QwenWork（千问办公）

> 最后更新: 2026-09-17
> 所属厂商: 阿里巴巴（阿里云）
> 产品类别: AI App
> 状态: Published

<!-- SUMMARY_START -->
**定位**: 一站式 AI 生产力平台，自然语言驱动的 AI Agent 办公产品——把日常办公任务从"人工操作"升级为"AI 自动执行"，一句话完成数据分析、PPT 生成、视频剪辑、网页搭建
**产品承接**: 阿里面向 Agent 办公市场的整合型产品，媒体报道整合 QoderWork、悟空、MuleRun 三款 Agent 产品 [来源: 东方财富 2026-07-27，⚠️ 待官方验证]；用户口述确认其代替已下架的 QoderWork（2026-09-17）
**部署形态**: 支持阿里云 VPC 私有化部署（K8s）[来源: 用户口述 2026-09-17，⚠️ 待官方验证]
**适用**: 日常办公自动化（信息整理 / 内容创作 / 数据分析）、Office 全套集成、网页部署、浏览器自动化、定时任务、钉钉生态场景
**不适用**: 深度 Coding 任务（用 Qoder / Qwen Code）；桌面客户端高级能力尚未全量开放（企业版能力以 PC 端和 Web 端为主）
**竞品**: Claude Cowork（Anthropic 桌面通用 Agent）
**常搭配**: Qwen IDE（本地工作目录协同）、钉钉（IM 生态深度融合）
<!-- SUMMARY_END -->

## 产品原理解析

### 一句话定位

千问办公是阿里巴巴旗下以自然语言驱动的 AI Agent 办公产品，用户仅需一句话即可完成数据分析、PPT 生成、视频剪辑、网页搭建等复杂任务 `[来源: aliyun.com/product/qwenwork]`

### 与 QoderWork / MuleRun 的承接关系

| 原产品 | 去向 |
|--------|------|
| QoderWork | 已下架（2026-09 `[来源: 用户口述]`），能力整合进千问办公 |
| MuleRun | 媒体报道称同步整合进千问办公 `[来源: 东方财富 2026-07-27，⚠️ 待官方验证]` |
| 悟空 | 媒体报道称同步整合进千问办公 `[来源: 东方财富 2026-07-27，⚠️ 待官方验证]` |

> 时间线：2026-07-27 千问办公桌面版上线（媒体报道后续将内置钉钉）；2026-08-03 阿里官方公告发布"千问办公"；2026-08-11 帮助文档"工作台-设计"上线（本地目录绑定 + Qwen IDE 协同）。

### 产品形态

| 形态 | 说明 | 来源 |
|------|------|------|
| Web 端 | 一站式 AI 生产力平台入口（qwenwork.cn） | help.aliyun.com/zh/qwenwork/ |
| 桌面端 | AI 智能工作台：自然语言发起任务，结合文件、技能、连接器、电脑操控、IM、Hooks 等能力 | help.aliyun.com/zh/qwenwork/desktop-core/ |
| 钉钉集成 | 深度融入钉钉生态：自然语言完成文件创建、群组对话摘要、日程安排、讯息及电邮发送 | ali-home.alibaba.com 官方公告 2026-08-03 |
| 私有化部署 | 支持阿里云 VPC 内私有化部署（K8s）`[来源: 用户口述 2026-09-17，⚠️ 待官方验证]` | — |

> 桌面端注意：企业版能力目前主要支持 PC 端和 Web 端，桌面客户端的相关能力将在后续版本中逐步开放 `[来源: help.aliyun.com/zh/qwenwork/desktop-core/]`

### 核心能力

`[来源: help.aliyun.com/zh/qwenwork/]`

| 能力 | 说明 |
|------|------|
| 多模态生成 | PPT、文档、表格、视频剪辑等内容生成 |
| 全栈网页部署 | 一句话搭建网页 |
| 专业数据源 | 数据分析类任务支持 |
| 全套 Office 集成 | 与 Office 办公套件打通 |
| 浏览器自动化 | 网页操作自动化 |
| 定时任务 | 任务定时执行 |
| 本地工作目录绑定 | 任务绑定本地目录，工程文件落地方便长期维护，并与 Qwen IDE 协同 `[来源: help.aliyun.com/zh/qwenwork/qw-workbench-design]` |

### 典型场景

| 场景 | 说明 |
|------|------|
| 数据分析 | 一句话完成数据分析任务 |
| 文档创作 | PPT 生成、报告撰写 |
| 视频剪辑 | 多模态视频任务 |
| 网页搭建 | 全栈网页部署 |
| IM 办公 | 钉钉内群组对话摘要、日程安排、讯息/电邮发送 |

## 定价

个人版权益详见官方文档"个人版权益"章节（help.aliyun.com/zh/qwenwork/）`[⚠️ 具体价格待核实]`

## 参考资料

- 产品官网: https://www.aliyun.com/product/qwenwork
- 产品入口: https://qwenwork.cn/
- 帮助文档: https://help.aliyun.com/zh/qwenwork/
- 快速入门: https://help.aliyun.com/zh/document_detail/3047901.html
- 常见问题: https://help.aliyun.com/zh/document_detail/3047945.html
- 官方公告（阿里巴巴集团）: https://ali-home.alibaba.com/document-2021039099929952256
- 关联文档: [QoderWork（已下架）](qoder-work.md) · [MuleRun](mulerun.md)

## Changelog

| 日期 | 变更内容 |
|------|----------|
| 2026-09-17 | 增量：用户口述 - 支持阿里云 VPC 私有化部署（K8s），待官方验证 |
| 2026-09-17 | 初始创建：依据官方帮助文档 + 集团公告 + 媒体报道（2026-07/08）；记录与 QoderWork / 悟空 / MuleRun 的整合关系；用户口述确认代替 QoderWork |
