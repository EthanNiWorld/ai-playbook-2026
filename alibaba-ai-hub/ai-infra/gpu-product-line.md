# 阿里云 GPU 产品线选型：ECS GPU vs 灵骏 vs PAI

> 最后更新：2026-04-24
> 所属厂商：阿里云
> 产品类别：AI Infra / AI Platform
> 状态：Published

<!-- SUMMARY_START -->
**定位**：阿里云 GPU 算力供给的三种形态（IaaS 虚拟化、IaaS 裸金属、PaaS 平台）
**适用**：根据网络拓扑需求、管理粒度、运维能力选择对应产品
**不适用**：期望单一产品覆盖所有场景（需根据场景组合使用）
**竞品**：AWS EC2 GPU / Trainium、GCP TPU / Vertex AI
**常搭配**：PAI + 灵骏（平台 + 底座）、ECS GPU + 百炼（推理 + MaaS）
<!-- SUMMARY_END -->

## 产品原理解析

### 一句话定位

GPU 资源的供给形态分为 **IaaS（ECS GPU/灵骏）** 和 **PaaS（PAI）** 两层，核心差异在于**网络拓扑能力**和**管理粒度**。

### 底层原理（通俗版）

#### 1. ECS GPU（虚拟化实例）

- GPU 通过直通或 vGPU 方式挂载到 ECS 实例，网络走 VPC
- 部分规格族支持 NVLink 和 RoCE/eRDMA
- **gn8v**：8 卡间支持 NVLink（900GB/s）
- **gn8is（L20）**：支持 ERI（RoCE v2）
- **限制**：能力因规格族而异，需查证

#### 2. 灵骏智算服务（裸金属 GPU 集群）

- 物理 GPU 服务器 + IB/eRDMA + CPFS 文件系统
- 专为千卡/万卡级分布式训练设计
- 客户可 SSH 登录，自行管理底层
- 适合 H200、H20-141G 等大卡场景

#### 3. PAI 平台（Serverless AI 平台）

- PaaS 层，自动调度底层资源（灵骏/ECS/ACK）
- 提供数据预处理→训练→推理→MLOps 全链路
- 客户管任务不管机器，灵活度受限

### 核心限制

| 限制项 | ECS GPU | 灵骏 | PAI |
|--------|---------|------|-----|
| 网络能力 | 因规格而异 | IB/eRDMA 全支持 | 依赖底层 |
| 管理粒度 | 实例级 | 裸金属级 | 任务级 |
| 运维要求 | 中等 | 高 | 低 |
| 灵活度 | 高 | 最高 | 中等 |

## 适用边界分析

### ✅ 适用场景

| 场景 | 推荐方案 | 说明 |
|------|---------|------|
| L20 单卡/少卡推理 | ECS GPU（gn8is） | 支持 RoCE，开箱即用 |
| 轻量训练/开发测试 | ECS GPU | 成本低，易上手 |
| H200 大规模训练 | 灵骏 + 可选 PAI | 高网底座 + 开发平台 |
| 零运维需求 | PAI | 客户管任务不管机器 |

### ❌ 不适用场景

| 场景 | 原因 | 替代方案 |
|------|------|----------|
| 超大规模训练用 ECS | 网络可能不够 | 改用灵骏 |
| 轻量任务用灵骏 | 成本过高 | 改用 ECS |
| 深度定制用 PAI | 不支持 SSH | 改用灵骏/ECS |

### ⚠️ 常见误解

| 误解 | 事实 |
|------|------|
| ECS 有 GPU 就能跑一切 | 多卡通信受限于网络，需查证规格 |
| 灵骏和 PAI 二选一 | 是底座 vs 平台，常配合使用 |
| 所有 ECS 都支持高网 | NVLink/RoCE 因规格而异 |

## 灵骏 vs PAI 的关系

**不是二选一，而是底座 vs 平台**：

```
灵骏（IaaS 底座）→ 提供算力 + 网络
       ↓
PAI（PaaS 平台）→ 提供开发工具 + 调度
       ↓
客户（提交任务）
```

实际生产中常配合使用：PAI 任务下发到灵骏集群，兼顾效率与性能。

## 竞品快速对照

| 维度 | 阿里云 | AWS | GCP |
|------|--------|-----|-----|
| 虚拟化 GPU | ECS GPU | EC2 GPU | Compute Engine |
| 高速网络 | ERI（RoCE v2） | EFA | TPU Interconnect |
| 裸金属 | 灵骏 | EC2 Bare Metal | - |
| AI 平台 | PAI | SageMaker | Vertex AI |

## 参考资料

- 阿里云 ECS GPU 文档：https://help.aliyun.com/zh/ecs/user-guide/gpu-accelerated-compute-optimized-and-vgpu-accelerated-instance-families-1
- 阿里云 EGS GPU 规格：https://help.aliyun.com/zh/egs/gpu-accelerated-compute-optimized-instance-families

## Changelog

| 日期 | 变更内容 |
|------|----------|
| 2026-04-24 | 初始创建：阿里云 GPU 产品线选型指南（ECS/灵骏/PAI） |
