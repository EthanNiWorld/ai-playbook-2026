# AgenticFS（Agent 原生文件存储）

> 最后更新: 2026-10-19
> 所属厂商: 阿里云
> 产品类别: 存储 / AI Infra
> 状态: Published

<!-- SUMMARY_START -->
**定位**: 面向 AI Agent 场景的 Serverless 文件存储，把多租户隔离单元从「目录」下沉到「AgenticSpace（独立 inode 空间 + 独立 QoS + 独立配额）」
**适用**: Agent 平台 / Sandbox 服务 / Coding Agent 等需要给成千上万终端用户各分隔离、可配额、可计费 Workspace 的平台方
**不适用**: 纯冷数据归档（用 OSS 更便宜）、训练侧极致吞吐（用 CPFS）、中小规模人为主的共享工作区（传统 NAS 足够）
**竞品**: 对象存储 + FUSE 模拟（OSS + ossfs）、共享文件系统 + 目录配额（传统 NAS）、自建分布式文件系统
**常搭配**: 云栖大会 Agentic Cloud（Agentic OS 负责运行时调度、CPFS 负责训练侧吞吐、AgenticFS 负责 Agent 运行时持久化）
<!-- SUMMARY_END -->

## 产品原理解析

### 一句话定位

AgenticFS 是**按「每个 Agent 一间带独立门禁与独立水电表的工作间」重新设计**的 Serverless 文件存储——用 POSIX 语义服务 Agent 的随机读写与小文件，用 per-Space 独立 inode 与 QoS 解决百万级多租户的隔离与规模问题。

### 底层原理（通俗版）

**两层抽象**：

```
AgenticFS（Region 级文件系统，单系统最高管 50 万 AgenticSpace）
   └── AgenticSpace（AZ 级独立工作空间）
         ├── 独立 inode 空间（元数据隔离，不与其他租户共享）
         ├── 独立容量配额 + 文件数配额（防单个 Agent 写爆）
         ├── 独立权限（RAM + AccessPoint）
         └── 独立吞吐 / IOPS / 元数据 QoS（故障域隔离）
```

**应用模型**：

- 平台开发者管理 1~N 个 AgenticFS；
- 每个终端用户分配一个 AgenticSpace 当作 Workspace；
- 同一用户的多个 Session → 在 Space 下建子目录，存放会话记录、记忆数据、Markdown、Skill 等持久化数据；
- 接入点 AccessPoint 支持 **AgenticFS / AgenticSpace 两种粒度**，配合 RAM 策略做差异化访问控制。

**为什么这样设计**（与 OSS / NAS 的区别）：

| 旧方案的墙 | 根因 | AgenticFS 的解法 |
|-----------|------|-----------------|
| OSS 慢 | 每次 open/read/stat 都是一次跨网络 HTTP 请求；rename 目录退化为逐对象 copy+delete | 原生 POSIX/NFS v3，不靠 FUSE 模拟 |
| NAS 挤 | 一个大文件系统划目录 → 共享 inode 空间/元数据服务/性能包络；单文件系统客户端 ~10 万级成瓶颈 | 每个 Space 独立 inode 空间 + 独立 QoS，单系统可管 50 万 Space |

> 完整的第一性原理推导（用户形态突变 → 抽象重构）见 [Agent Native 存储](../../knowledge/ai-general-notes/agent-native-storage.md)。

### 核心限制

| 限制项 | 具体值 | 说明 |
|--------|--------|------|
| 当前阶段 | **邀测** | 非 GA，需申请 |
| 可用地域 | 北京 / 杭州 / 上海 / 深圳 / 香港 / 新加坡 / 柔佛 / 弗吉尼亚 | 以官方最新公布为准 |
| 客户端 | 兼容 POSIX / NFS v3（Linux） | 非 Linux 客户端适配未提及 |
| 单路延迟 | 同 AZ 4K 读写 2 ms；跨 AZ 3~5 ms | 跨 AZ 场景需评估延迟敏感度 |
| 吞吐模型 | 峰值初始 300 MB/s，每 +1 GiB 增加 0.3 MB/s；读上限 20 GB/s、写上限 5 GB/s | 小容量 Space 吞吐较低，需按容量规划 |
| IOPS | 最大 3 万 | — |
| 挂载延迟 | 1~3 秒 | 秒级 Sandbox 需考虑冷启动挂载开销 |
| 容量上限 | AgenticFS 最大 100 PiB / 5 万亿文件；AgenticSpace 最大 1 PiB / 10 亿文件 | — |
| 扩容方式 | Serverless 自动扩容，步长 4 KiB | 无需预置 |
| SLA | 99.95% | — |
| 计费 | 按每小时存储容量峰值计费 | 容量峰值口径，非平均 |

## 适用边界分析

### ✅ 适用场景

| 场景 | 说明 | 典型客户/案例 |
|------|------|--------------|
| Agent 平台 / Sandbox 服务 | 大量终端用户各自需要隔离、可配额的持久化工作区 | 待补充 |
| Coding Agent | 随机读写、频繁小文件、目录 rename、追加写等 POSIX 密集操作 | 待补充 |
| 会话记忆与产物持久化 | Sandbox 秒级销毁但记忆/产物需长期保留 | 待补充 |
| 多租户 SaaS 式 Agent 产品 | 需要 per-用户容量/文件数限额与计费 | 待补充 |

### ❌ 不适用场景

| 场景 | 不适用原因 | 替代方案 |
|------|-----------|----------|
| 冷数据 / 海量产物归档 | 文件系统语义与成本结构不匹配 | OSS |
| 训练 / 多模态数据极致吞吐 | 需要百 TB/s 级吞吐与亿级 IOPS | CPFS |
| 中小规模、人为主的共享工作区 | 传统 NAS 已足够，无需 per-Space 隔离 | NAS |
| 强自建能力且已有分布式文件系统 | 迁移成本可能高于收益 | 自建（如 JuiceFS 方案） |

### ⚠️ 常见误解

| 误解 | 事实 |
|------|------|
| 「AgenticFS 就是更快的 NAS」 | 差别的核心是隔离单元从目录下沉到独立 inode 空间 + 独立 QoS，不是绝对带宽 |
| 「对象存储挂 FUSE 就等于 POSIX 兼容」 | 语义兼容 ≠ 性能兼容，每次小文件 syscall 可能都是跨网络请求 |
| 「Space 越多越慢」 | 设计目标就是单系统 50 万 Space，隔离域独立；瓶颈在单 Space 的吞吐/IOPS 配额 |
| 「容量配额只是成本控制」 | 它同时是防写爆（noisy-neighbor）的故障隔离手段 |

## 关键配置与最佳实践

### 配置建议

1. **Space 粒度对齐「终端用户」**：一个终端用户一个 Space，多个 Session 用子目录，而不是一个 Session 一个 Space（避免 Space 数量膨胀且丢失用户级配额）。
2. **容量规划同时看吞吐**：峰值吞吐 = 初始 300 MB/s + 0.3 MB/s/GiB，小容量 Space 的吞吐可能成为瓶颈。
3. **AccessPoint 按粒度授权**：平台层用 AgenticFS 级 AccessPoint，租户层用 AgenticSpace 级 AccessPoint + RAM 策略。
4. **跨 AZ 场景先测延迟**：3~5 ms 与同 AZ 2 ms 的差异，对高频小文件写入是累积成本。
5. **记忆/产物与会话目录分离**：便于按生命周期做备份与归档策略。

### 踩坑记录

| 问题 | 原因 | 解决方案 | 记录日期 |
|------|------|----------|----------|
| 待补充 | — | — | — |

## 竞品快速对照

> 此处为同厂商/替代路线简表，非严格竞品；深度对比请另建文档。

| 维度 | AgenticFS | OSS + ossfs | 传统 NAS |
|------|-----------|-------------|----------|
| 访问语义 | 原生 POSIX / NFS v3 | HTTP 对象 API + FUSE 模拟 | POSIX / NFS |
| 隔离粒度 | per-AgenticSpace（独立 inode + QoS + 配额） | Bucket 级 | 文件系统/目录级（共享 inode） |
| 多租户规模 | 单系统 50 万 Space | 无租户工作区概念 | 客户端 ~10 万级成瓶颈 |
| 小文件/元数据 | 强（独立 inode + 元数据 QoS） | 差（每操作一次 HTTP 往返） | 中（元数据易被打爆） |
| 适用 | Agent 在线工作区 | 冷数据归档、大文件 | 中小规模共享工作区 |

## 参考资料（若有）

- [官方文档] 什么是 AgenticFS - https://help.aliyun.com/zh/nas/product-overview/agenticfs-overview
- [官方] AgenticFS 产品动态 - https://www.aliyun.com/product/news/29981
- [官方] 创建 AgenticFS - https://www.alibabacloud.com/help/zh/nas/user-guide/create-agenticfs
- [官方] 管理 AgenticSpace - https://www.alibabacloud.com/help/zh/nas/user-guide/manage-agenticspace
- [技术博客] JuiceFS《Agent Sandbox 规模化：探索与实践》（独立信源，旁证 NAS 规模墙） - https://juicefs.com/zh-cn/blog/solutions/scaling-agent-sandboxes-juicefs-practice
- [媒体] 云栖大会 Agentic OS 报道 - https://tech.china.com/articles/20260924/202609241962070.html
- [媒体] 阿里云 Agentic Cloud 与新一代 CPFS - https://www.cnstock.com/commonDetail/793843

> ⚠️ 独创性口径：阿里云自称「全球首款 Agent Native 文件存储」，属厂商口径、待第三方佐证；可验证的差异点是 per-Workspace 独立 inode + 独立元数据/性能 QoS + 单系统 50 万级 Serverless 弹性。时间线上，AgenticFS 邀测与开发者文章在 2026 年 6~8 月已出现，云栖大会是其作为 Agentic Cloud 存储层的正式呈现节点，「云栖大会首发」表述待官方发布稿再核实。

## Changelog
| 日期 | 变更内容 |
|------|----------|
| 2026-10-19 | 校验修复（knowledge-verification-2026-10-19）：Agent Native 存储交叉链接修复——../../../knowledge/... → ../../knowledge/...（多一层 ../） |
| 2026-10-19 | 新建：提炼自 inbox/ai-knowledge-by-qoder-ai-native-agent-20261010.md；规格数字以此文档为权威源，概念框架见 knowledge/ai-general-notes/agent-native-storage.md |
