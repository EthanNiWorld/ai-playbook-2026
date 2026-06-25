# MaaS 销售洞察

> 由 ai-knowledge-miner 自动生成，来源为 knowledge/ 文档更新中发现的销售启发。
> 仅供内部参考，禁止外传。

## 2026-05-31
- **HappyHorse vs 字节 Seedance 2.0 定价优势**：百炼 HappyHorse 720P ¥0.9/s，火山引擎 Seedance 2.0 ¥~1.0/s，价格优 10%。且 HappyHorse T2V/I2V 双冠 AA 盲测，可向客户传递"更便宜+更好看"（来源：knowledge/alibaba-cloud/maas/happyhorse.md）
- **音视频联合生成卖点**：HappyHorse 是当前唯一音视频单次生成的商用模型（非先视频后配音），可向短视频/电商客户强调"一条 API 出成品，无需配音流程"（来源：knowledge/alibaba-cloud/maas/happyhorse.md）
- **Wan 2.7 开源 + LoRA 微调是百炼护城河**：Wan 2.7 Apache 2.0 开源 + 百炼官方 LoRA 微调指南，竞品字节 Seedance 2.0 完全不支持微调。对需要定制风格的客户（短剧、游戏、IP 角色），这是不可替代的差异化能力（来源：knowledge/alibaba-cloud/maas/wan.md）
- **双模型覆盖策略话术**：阿里云百炼同时提供 Wan 2.7（全链路企业级）和 HappyHorse（极致质量+速度），可向客户传递“你要稳还是要快？两个我们都有”。这是字节火山（仅 Seedance 2.0）不具备的选型灵活性（来源：knowledge/alibaba-cloud/maas/wan.md, happyhorse.md）
- **Qwen3.7-Max Winback DS-V4-Pro 话术**：DS-V4-Pro 输入 ¥3/M 是 Qwen ¥12/M 的 1/4，但 Agent 场景按“任务完成率”算账——Qwen Terminal-Bench 69.7 + 35h 长时执行，任务 1 轮完成无需人工介入；DS 可能需 3 轮 + 人工干预，综合成本反而更高（来源：knowledge/alibaba-cloud/maas/qwen.md）
- **Qwen3.7-Max Winback GLM-5.1 话术**：GLM-5.1 上下文仅 128K，Agent 场景很快打满导致任务失败。Qwen 1M 上下文是 GLM 的 8 倍，Terminal-Bench 高 6.2 分，1 次任务成功 vs 3 次失败重试，Qwen 综合成本更低（来源：knowledge/alibaba-cloud/maas/qwen.md）
- **Qwen3.7-Max Agentic Coding 接入极简**：Claude Code / Trae CN 等工具只需改 2 个环境变量（base_url + api_key），现有代码零改动即可切换底层模型为 Qwen3.7-Max。主推场景：CC/CodeBuddy/Trae CN/Qwen Code/OpenClaw（来源：knowledge/alibaba-cloud/maas/qwen.md）

## 2026-06-01
- **MuleRun 是百炼模型的"应用层出口"**：客户问"买了百炼模型能做什么？"时，MuleRun 是现成答案——云端 Agent 平台直接消费 Qwen/百炼 API，灵骏→百炼→MuleRun 形成完整商业闭环。可向客户演示 MuleRun 作为百炼模型的应用层价值（来源：knowledge/alibaba-cloud/ai-application/mulerun.md）
- **MuleRun + QoderWork 双产品覆盖企业全场景**：客户需要本地处理→QoderWork（隐私安全），需要 7×24 持续运行→MuleRun（云端电脑）。两个产品互补不竞争，可打包销售覆盖"桌面+云端"全场景（来源：knowledge/alibaba-cloud/ai-application/mulerun.md）

## 2026-06-02
- **数据合规场景选型话术**：客户数据不能出境→推 QoderWork CN 或骡子快跑（CN 版）；客户面向海外市场→推 MuleRun 全球版。一句话：合规选 CN 版，出海选全球版（来源：knowledge/alibaba-cloud/ai-application/mulerun.md）
- **MuleRun 内置生图/生视频是竞品差异化**：Claude Cowork / OpenAI Operator 均无内置多模态生成能力，MuleRun 如确认内置 SOTA 级模型，可向创意/营销客户强调"一个平台搞定 Agent + 生图 + 生视频"（来源：knowledge/alibaba-cloud/ai-application/mulerun.md，⚠️ 待官方确认）