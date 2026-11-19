# qwen3-vl-embedding 新加坡节点可用性探测结果

> 测试时间：2026-11-19
> 脚本：[test_qwen3_vl_embedding_probe.py](test_qwen3_vl_embedding_probe.py)
> 端点：DashScope 原生 `/api/v1/services/embeddings/multimodal-embedding/multimodal-embedding` + OpenAI 兼容 `/compatible-mode/v1/embeddings`

## 结论

**qwen3-vl-embedding 在新加坡节点当前不可用（403 AccessDenied），仅中国内地与北京节点可正常调用。**

新加坡节点并未整体关停多模态向量服务，而是 qwen3-vl-embedding 这个 Model ID 在该地域未对本账号开放；同端点下 `tongyi-embedding-vision-plus` 可正常返回向量。

## 实测矩阵

| 节点 | qwen3-vl-embedding | 对照模型 | 说明 |
|------|--------------------|----------|------|
| INTL-SG（ap-southeast-1） | ❌ 403 AccessDenied | tongyi-embedding-vision-plus ✅ 200 dim=1024；qwen3.7-text-embedding ✅ 200 | key 与向量服务均正常，非鉴权配置问题 |
| INTL-BJ（cn-beijing） | ✅ 200 dim=1024 | — | 原生端点正常 |
| CN-TEST（cn-beijing） | ✅ 200 dim=1024 | qwen3.7-text-embedding ✅ 200 | 原生端点正常 |

## 新加坡节点同类模型横向结果

| 模型 | HTTP | 结果 |
|------|------|------|
| tongyi-embedding-vision-plus | 200 | 可用，dim=1024 |
| tongyi-embedding-vision-flash | 400 | 模型存在，但 dimension 仅支持 [64,128,256,512,768] |
| qwen3-vl-embedding | 403 | AccessDenied（非 Model not exist，说明 Model ID 可路由但无权限/未上架本账号） |
| multimodal-embedding-v1 | 400 | Model not exist |
| qwen3-vl-rerank | 404 | Model not exist（新加坡未提供） |
| qwen3-rerank | 200 | 可用 |

## 官方口径交叉验证

国际站定价页 `https://www.alibabacloud.com/help/en/model-studio/model-pricing`（2026-11-19 抓取）Multimodal Embedding 章节：

- Singapore 段：仅列 `tongyi-embedding-vision-plus`（$0.09/M）、`tongyi-embedding-vision-flash`（图像/视频 $0.03、文本 $0.09）
- China (Beijing) 段：`qwen3-vl-embedding`（图像/视频 $0.258、文本 $0.1）、`multimodal-embedding-v1`

即官方定价口径同样未把 qwen3-vl-embedding 列入新加坡，与实测一致。

## 备注

- OpenAI 兼容 `/compatible-mode/v1/embeddings` 调用该模型在北京/中国站返回 400 `url error`，多模态向量须走原生 multimodal-embedding 端点（兼容模式仅 `qwen3.7-text-embedding` 这类文本向量可用）。
- `GET /api/v1/models` 返回的 20 个模型均为 LLM 对话类，不包含 embedding 系列，不能用于判断向量模型的开通状态。
