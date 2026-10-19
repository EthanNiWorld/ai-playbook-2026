# Agent Native 存储：当文件系统的主要用户从「人」变成「Agent」

> 最后更新: 2026-10-19
> 领域: AI Infra
> 状态: Published

<!-- SUMMARY_START -->
**一句话说明**: 存储抽象必须跟随其主要用户形态重构——当文件系统用户从「人 + 少量应用」变成「百万级不可预测的 Agent」，租户数量、访问模式、隔离粒度、生命周期四个假设同时被打破
**核心价值**: 给出「用户形态突变 → 基础设施抽象重构」的第一性原理框架，解释 OSS 慢、NAS 挤、AgenticFS 出现的必然性；可迁移到数据库、网络、调度等一切基础设施演进判断
**相关产品**: [AgenticFS](../../alibaba-ai-hub/ai-infra/agenticfs.md), [企业自建 AI 推理平台](../../alibaba-ai-hub/ai-industry-solutions/enterprise-ai-platform/overview.md)
<!-- SUMMARY_END -->

## 是什么

Agent Native 存储指**为「Agent 作为主要写入者/读取者」重新设计的存储抽象**。它不是「更快的对象存储」或「更大的 NAS」，而是把多租户隔离单元从「目录/桶」下沉到「独立 inode 空间 + 独立 QoS + 独立配额」。

判断一个存储是否真正 Agent Native，看三条：

1. **POSIX 完整语义**：Agent 写代码需要随机读写、频繁小文件、目录 rename、追加写——HTTP 对象 API 不原生支持。
2. **per-Agent 隔离**：每个 Agent（或终端用户）有独立 inode 空间、独立容量/文件数配额、独立吞吐/IOPS/元数据 QoS。
3. **Serverless 规模化**：租户数从千级走向十万/百万级，不能靠「一个大文件系统划目录」硬撑。

## 核心原理

### 第一性原理：四个底层假设同时被打破

当文件系统的主要用户从「人 + 少量应用」变成「百万级 Agent」，旧设计的四个隐含假设同时失效：

| 维度 | 旧假设 | Agent 时代 |
|------|--------|-----------|
| 租户数量 | 千级 | **百万级**（数量爆炸） |
| 访问模式 | 大块顺序读写 | **海量小文件 + 元数据风暴**（日志/轨迹/checkpoint/git/node_modules） |
| 隔离需求 | 粗粒度（bucket / fs / vpc） | **细粒度 per-Agent**（Agent 行为不可预测、可能失控，必须做故障域隔离） |
| 生命周期 | 计算与数据同生共死 | **解耦**（Sandbox 秒级销毁，记忆/产物长期保留） |

### 三次撞墙的因果链

**OSS 为什么「下载耗时大」**
为「海量对象 + HTTP 访问 + 人类应用」设计。Agent 写代码需要随机读写、频繁小文件、目录 rename、追加写，OSS 均不原生支持；ossfs/FUSE 挂载后每次 open/read/stat 都是一次跨网络 HTTP 请求（几十 ms 级），海量小文件 = 海量 HTTP 往返，rename 目录 = 逐对象 copy+delete。**本质是每次操作都在跨网络搬对象。**

**NAS 为什么「性能不够」**
不是绝对带宽不够，而是「规模化多租户下的元数据性能 + 隔离粒度 + 配额能力」不够。传统 NAS 是「一个大文件系统里划目录」，共享同一 inode 空间/元数据服务/性能包络。Agent 规模化后四个问题同时爆发：
- 单文件系统客户端数撞上限（业界 ~10 万级客户端已成瓶颈，百万级 Sandbox 需求涌现）；
- 海量小文件打爆元数据服务；
- 单 Agent 疯狂读写或 rm 触发 noisy-neighbor；
- 无法为每个终端用户单独设容量 + 文件数限额。

**AgenticFS 的解法**
把隔离粒度从「目录/子树」下沉到「**独立 inode 空间 + 独立 QoS 域**」。每个 AgenticSpace = 独立 inode（元数据隔离）+ 独立配额（成本可控、防写爆）+ 独立权限（RAM + AccessPoint）+ 独立吞吐/IOPS/元数据 QoS（故障域隔离），从架构上一次解掉规模、隔离、元数据、成本四个问题。具体规格见 [AgenticFS 产品文档](../../alibaba-ai-hub/ai-infra/agenticfs.md)。

### 三段演进对照

| 维度 | OSS（对象存储） | NAS（共享文件系统） | AgenticFS（Agent 原生） |
|------|----------------|-------------------|------------------------|
| 访问语义 | HTTP 对象 API，非 POSIX | POSIX / NFS | POSIX / NFS + Workspace 抽象 |
| 隔离粒度 | Bucket 级 | 文件系统/目录级（共享 inode） | **AgenticSpace 级（独立 inode 空间）** |
| 小文件/元数据 | 差（每次操作一次 HTTP 往返，rename=copy+delete） | 中（文件数/目录配额上限、元数据易被打爆） | 强（独立 inode + 元数据 QoS） |
| 多租户规模 | 无租户工作区概念 | 单文件系统客户端 ~10 万级即成瓶颈 | 单系统管理 50 万 AgenticSpace |
| 性能隔离/配额 | 无 | 共享性能包络、目录配额弱 | 每 Space 独立吞吐/IOPS/元数据 QoS + 独立容量与文件数配额 |

## 关键认知框架

### 核心洞察 1：基础设施抽象必须跟随「主要用户形态」重构

不是「用户变多所以要扩容」，而是**用户形态变了，抽象本身就不对了**。判断信号：当出现「为了适配新用户，所有操作都要绕一层模拟层」（如 FUSE 把对象存储伪装成文件系统）时，说明抽象错配，而不是性能不够。

可迁移场景：
- **数据库**：从人写 SQL → Agent 高并发短事务 + 自动生成查询，连接池/权限/计费模型都要重构；
- **网络**：从服务人 → 服务百万 Agent 的东西向流量，身份与限流粒度要下沉；
- **调度**：从长期驻留服务 → 秒级 Sandbox，调度单位从 Pod 变成 Agent 会话。

### 核心洞察 2：隔离单元的选择，决定了规模上限

`bucket → 目录 → 独立 inode 空间` 的演进，本质是**隔离单元逐级下沉**。隔离单元越粗，规模上来后越会出现「一个租户打爆全系统」的耦合故障；隔离单元越细，单系统可承载的租户数越高。

这与云原生多租户演进同构：进程 → 容器 → 微 VM → 函数。每一次都是把「故障域 + 配额 + 计量」的单位缩小。

### 核心洞察 3：计算与数据生命周期解耦是新存储的隐含要求

Sandbox 秒级创建/销毁，但记忆、产物、会话记录要长期保留。若存储把「工作区」绑定在计算实例上（如本地盘/实例挂载），Agent 一销毁数据即失；若把数据放在只能整块搬运的对象存储里，恢复又太慢。**Agent Native 存储必须同时满足「计算侧秒级挂载」与「数据侧长期独立存活」。**

## 各厂商实现对照

| 实现路线 | 代表 | 做法 | 适用边界 |
|---------|------|------|---------|
| 对象存储 + FUSE 模拟 | OSS + ossfs | 把对象 API 伪装成 POSIX | 冷数据、大文件、归档；不适合高频小文件 |
| 共享文件系统 + 目录配额 | 传统 NAS | 一个文件系统划目录 | 中小规模、人为主的工作区 |
| Agent 原生文件系统 | 阿里云 AgenticFS | per-AgenticSpace 独立 inode + QoS + 配额，Serverless 弹性 | 面向 Agent 平台/Sandbox 服务/Coding Agent 的多租户工作区 |
| 分布式文件系统自建 | 行业实践（如 JuiceFS 方案） | 由平台方自行运维与扩展（JuiceFS 博客分析了小文件/元数据/客户端扩展瓶颈） | 有强自建能力的平台方 |

> 行业实践参照：JuiceFS《Agent Sandbox 规模化：探索与实践》独立分析了小文件/元数据/客户端扩展瓶颈与隔离问题，可作为理解「NAS 墙」的旁证。

## 最佳实践

### 选型判断（三层各司其职）

| 数据形态 | 推荐 | 原因 |
|---------|------|------|
| 冷数据 / 海量产物归档 | OSS | 成本最低、容量无限 |
| 训练/多模态极致吞吐 | CPFS | 百 TB/s 级吞吐、亿级 IOPS（训练侧） |
| **Agent 在线工作区** | **AgenticFS** | 补「此前用 NAS 硬撑、用 OSS 太慢」的空白 |
| 长短期记忆/会话记录 | AgenticFS（Space 下子目录） | 与 Sandbox 生命周期解耦，可长期保留 |

**适用客户画像**：做 Agent 平台 / Sandbox 服务 / Coding Agent，需要给成千上万终端用户各分一个「隔离、可配额、可计费」Workspace 的团队。

### 可迁移场景

- 任何「从少量长期用户 → 海量短期临时用户」的系统，都要重新检查：隔离单元、配额粒度、计量单位、生命周期绑定。
- 判断旧系统是否该换：不是看峰值性能，而是看**故障是否会被单租户放大到全系统**。

## 常见误区

| 误区 | 事实 |
|------|------|
| 「OSS 慢是因为带宽不够」 | 根因是访问语义错配：每次小文件操作都是一次跨网络 HTTP 往返，rename 退化为 copy+delete |
| 「NAS 性能不够就加带宽/换更高端型号」 | 瓶颈常在元数据服务与共享 inode 空间，加带宽不解决租户隔离与配额问题 |
| 「Agent 存储就是把 NAS 做大」 | 规模化后需要的是「隔离单元下沉」，不是「单系统做大」 |
| 「Sandbox 销毁了数据自然就没了，不需要长期存储」 | 记忆/产物/会话记录必须跨 Sandbox 生命周期存活，否则 Agent 无法积累 |
| 「对象存储 + FUSE 挂载 = POSIX 兼容」 | 语义兼容≠性能兼容：模拟层的每次 syscall 都可能是跨网络请求 |

## 参考资料

- [官方文档] 什么是 AgenticFS - https://help.aliyun.com/zh/nas/product-overview/agenticfs-overview
- [官方] AgenticFS 产品动态 - https://www.aliyun.com/product/news/29981
- [官方] 创建/管理 AgenticFS 与 AgenticSpace - https://www.alibabacloud.com/help/zh/nas/user-guide/create-agenticfs · https://www.alibabacloud.com/help/zh/nas/user-guide/manage-agenticspace
- [官方] Sandbox 实例级动态挂载 OSS（OSS 访问模式参考） - https://help.aliyun.com/zh/agentrun/sandbox-supports-instance-level-dynamic-mount-of-oss-test-invitation-1
- [技术博客] JuiceFS《Agent Sandbox 规模化：探索与实践》 - https://juicefs.com/zh-cn/blog/solutions/scaling-agent-sandboxes-juicefs-practice
- [媒体] 云栖大会 Agentic OS 报道 - https://tech.china.com/articles/20260924/202609241962070.html
- [媒体] 阿里云 Agentic Cloud 与新一代 CPFS - https://www.cnstock.com/commonDetail/793843

## Changelog
| 日期 | 变更内容 |
|------|----------|
| 2026-10-19 | 新建：提炼自 inbox/ai-knowledge-by-qoder-ai-native-agent-20261010.md；建立「用户形态突变 → 抽象重构」框架（四假设打破 / 三次撞墙 / 隔离单元下沉），具体规格与邀测地域分置到 agenticfs.md 以保持信息收敛 |
