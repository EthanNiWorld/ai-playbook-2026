# GLM-5.2 国际站→北京节点 性能基准测试 SPEC

> 创建日期: 2026-07-06  
> 测试对象: GLM-5.2（智谱，AI Coding / Agentic Application 场景）  
> 调用路径: 国际站账号 → 百炼北京节点  

---

## 1. 测试目标

### 1.1 延迟指标（TTFT）

| 百分位 | 目标值 | 说明 |
|--------|--------|------|
| P50    | < 4s   | 正常请求 |
| P75    | < 8s   | 一般负载 |
| P90    | < 12s  | 高负载 |
| P99    | < 30s  | 极端情况 |

### 1.2 吞吐指标（TPS，Output Tokens/Second）

| 百分位 | 目标值 | 说明 |
|--------|--------|------|
| P50    | > 70 tok/s | 稳态生成速度 |
| P99    | > 25 tok/s | 极端情况下的下限 |

### 1.3 容量指标（TPM）

- 通过高并发压测获取实际 TPM 上限
- 观察是否触发 429 限流，以此判断配额水位

---

## 2. 测试设计

### 2.1 测试阶段

| 阶段 | 目标 | 并发 | 持续/样本 |
|------|------|------|-----------|
| Phase 1: 延迟测试 | TTFT + TPS 百分位 | 5（可配置） | 200 样本 |
| Phase 2: TPM 压测 | 实际 TPM 上限 | 50（可配置） | 60s |

### 2.2 Prompt 设计原则

场景定位：**AI Coding / Agentic Application**

- **Coding Prompt（5 种）**：代码生成类，要求输出完整可运行代码，预期输出 500~2000 tokens
- **Agentic Prompt（3 种）**：规划/工具调用/架构设计类，预期输出 800~2000 tokens

两类 Prompt 混合随机分配，模拟真实业务流量。

### 2.3 TTFT 测量方法

使用 OpenAI SDK **流式接口**（`stream=True`），精确记录：

- `start_time`：发送请求的时间戳
- `first_token_time`：收到首个非空 `delta.content` 的时间戳
- `last_token_time`：收到最后一个 `delta.content` 的时间戳

```
TTFT = first_token_time - start_time
TPS  = output_tokens / (last_token_time - first_token_time)
```

### 2.4 TPS 统计口径

- 分母：从首 token 到末 token 的生成阶段耗时（不含 TTFT 排队时间）
- 分子：OpenAI usage 中的 `completion_tokens`（若缺失则降级为客户端 token 计数）

---

## 3. 接入配置

### 3.1 Endpoint

```
国际站标准: https://dashscope-intl.aliyuncs.com/compatible-mode/v1
```

> 需确认：国际站调北京节点的实际 base_url，若为其他地址需通过 `GLM52_BASE_URL` 环境变量覆盖。

### 3.2 认证

```
API Key 来源: .env → DASHSCOPE_API_KEY_INTL
Key 格式: sk-xxx（标准百炼 Key）
```

### 3.3 模型名

```
默认: glm-5.2
可通过 GLM52_MODEL 环境变量覆盖（如带日期后缀的快照版本）
```

---

## 4. 验收判定规则

### 4.1 TTFT 验收

- P50/P75/P90/P99 四项指标**全部**低于目标值 → ✅ PASS
- 任一指标超标 → ❌ FAIL，需排查（网络延迟 / 服务端排队 / 模型冷启动）

### 4.2 TPS 验收

- P50/P99 两项指标**全部**高于目标值 → ✅ PASS
- P99 低于目标值 → 说明长尾请求生成速度不稳定，需关注 GPU 调度或 KV cache 压力

### 4.3 TPM 验收

- 实测 TPM 达到客户业务需求水位 → ✅
- 触发 429 → 说明已触及配额上限，可据此推算需多少账号/TPM 预留

---

## 5. 执行步骤

```bash
cd vibeCodingProject/llm_api_perf_benchmark

# 1. 连通性验证（5 样本，串行）
python glm52_benchmark.py --phase latency --samples 5 --concurrency 1

# 2. 正式延迟测试（200 样本，5 并发）
python glm52_benchmark.py --phase latency --samples 200 --concurrency 5

# 3. TPM 压测（60s，50 并发）
python glm52_benchmark.py --phase tpm --duration 60 --tpm-concurrency 50

# 4. 完整测试（延迟 + TPM）
python glm52_benchmark.py --samples 200 --concurrency 5 --tpm-concurrency 50
```

---

## 6. 输出格式

### 延迟测试输出示例

```
TTFT 统计 (成功 200/200, 失败 0)
──────────────────────────────────────────
  指标      实测值     验收标准   结果
  ──────────────────────────────────────
  P50         2.34s     <4s      ✅
  P75         5.12s     <8s      ✅
  P90         9.87s    <12s      ✅
  P99        28.15s    <30s      ✅

TPS (Output Tokens/Second) 统计
──────────────────────────────────────────
  指标      实测值       验收标准     结果
  ─────────────────────────────────────────
  P50        82.3 tok/s   >70 tok/s   ✅
  P99        31.5 tok/s   >25 tok/s   ✅
```

### TPM 测试输出示例

```
TPM 测试结果
──────────────────────────────────────────
  实测持续:       60.2s
  成功请求:       347
  限流次数:       12
  错误次数:       0
  Token 总量:     1,245,678 (入: 412,000, 出: 833,678)
  ★ 实测 TPM:    1,241,560
  推算 RPM:       345

  ⚠️  触发限流 12 次，实测 TPM 接近配额上限
```

---

## 7. 已知风险与注意事项

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 国际站→北京节点跨地域网络延迟 | TTFT 偏高 | 单独记录网络 RTT，与模型处理耗时解耦分析 |
| 模型冷启动（首次请求） | 首 1~3 个请求 TTFT 异常高 | 正式测试前 warm-up 2~3 次 |
| 高并发下 429 限流 | TPM 测试样本减少 | 降低并发或申请临时配额提升 |
| `stream=True` 下 `usage` 字段在末尾返回 | 需等全部 chunk 接收完 | 脚本已处理：最后一个 chunk 含 usage |

---

## 8. 文件结构

```
llm_api_perf_benchmark/
├── SPEC.md                  # 本文档
├── glm52_benchmark.py       # 主测试脚本
└── requirements.txt         # 依赖声明
```
