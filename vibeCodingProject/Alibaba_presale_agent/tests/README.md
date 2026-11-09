# 测试与验收

分两类：**离线单测**（不依赖网络/服务）与 **联调脚本**（需先启动服务）。

## 1. 离线单测

```bash
.venv/bin/python tests/test_self.py
```

覆盖价格问题识别、模型名提取、BM25 分词与检索、prompt 硬约束、SQLite 落库与反馈回写等纯逻辑，不调 LLM、不打外部搜索。改了 `price_verifier.py` / `knowledge.py` / `store.py` 后先跑它。

## 2. 联调脚本（需服务已在 8000 端口运行）

```bash
python run.py &          # 独立终端启动，或按 README 用 docker compose up -d

.venv/bin/python tests/e2e/test_followup.py    # 追问链：基线价格问 → 「呢？」→「价格。」
.venv/bin/python tests/e2e/test_colloquial_model.py  # 口语模型名：'kimi k3.1 pro' 归一 / 家族词守卫不挪用历史模型
.venv/bin/python tests/e2e/test_product_pricing.py  # 产品定价：Qoder 等非百炼模型产品不注入百炼回落证据
.venv/bin/python tests/e2e/test_price_followup_competitor.py  # 表格追问（China (Beijing) · US 是什么意思）+ 跨云竞品比价（腾讯云缓存价，v3：competitor 工具参数）
.venv/bin/python tests/e2e/test_toolloop_fx_clarify.py  # v3 工具循环：换算题不被缺型号反问劫持；快路径（缺型号反问/纯汇率）秒回回归
.venv/bin/python tests/e2e/test_pitfall_regressions.py  # 历史踩坑原句：汇率折扣互斥双答案 / 折扣口径 / 视频按秒 / 生图按张
.venv/bin/python tests/e2e/test_screenshot_qa.py  # 截图问答：模型读图调 verify_price / 历史重发截图追问 / 纯图回归
.venv/bin/python tests/e2e/test_toolcall_probe.py  # 探针：DashScope 流式 tool_calls 格式验证（直连模型，无需服务）
.venv/bin/python tests/e2e/test_vision_probe.py  # 探针：图像 + tools + enable_thinking 流式共存（直连模型，无需服务）
.venv/bin/python tests/e2e/judge_quality.py    # 回答质量：代码硬指标 + 交叉厂商 LLM 评审
.venv/bin/python tests/e2e/ui_regression.py --mock  # UI 布局与模拟流式回归，不调用模型、不写问答记录
.venv/bin/python tests/e2e/ui_regression.py    # 前端 UI + 真实模型联调（CDP 驱动浏览器）
```

| 脚本 | 依赖 | 副作用 |
|---|---|---|
| `test_followup.py` | 服务 + 有效 `DASHSCOPE_*` | 向 `data/qa.db` 写入回答记录 |
| `test_colloquial_model.py` | 服务 + 有效 `DASHSCOPE_*` | 向 `data/qa.db` 写入回答记录 |
| `test_product_pricing.py` | 服务 + 有效 `DASHSCOPE_*` | 向 `data/qa.db` 写入回答记录 |
| `test_price_followup_competitor.py` | 服务 + 有效 `DASHSCOPE_*` | 向 `data/qa.db` 写入 2 条回答记录；竞品比价需联网搜索 |
| `test_toolloop_fx_clarify.py` | 服务 + 有效 `DASHSCOPE_*` | 向 `data/qa.db` 写 3 条回答记录 |
| `test_pitfall_regressions.py` | 服务 + 有效 `DASHSCOPE_*` | 向 `data/qa.db` 写 4 条回答记录 |
| `test_screenshot_qa.py` | 服务 + 有效 `DASHSCOPE_*` | 向 `data/qa.db` 写 3 条回答记录（含截图） |
| `test_toolcall_probe.py` | 有效 `DASHSCOPE_*`（无需服务） | 无 |
| `test_vision_probe.py` | 有效 `DASHSCOPE_*` + `/tmp/apa_probe.png`（无需服务） | 无 |
| `judge_quality.py` | 服务 + `DASHSCOPE_*` | 每个 case 写 1 条记录；报告落 `data/reports/` |
| `ui_regression.py --mock` | 服务 + 本机 Chrome | 浏览器内模拟问答与反馈；不写数据库；截图落 `/tmp/` |
| `ui_regression.py` | 服务 + 本机 Chrome | 写 1 条回答 + 1 条点踩反馈；截图落 `/tmp/` |

联调脚本默认会真实调用 LLM 并消耗额度。仅改动 `static/` 时优先运行 `ui_regression.py --mock`，覆盖首屏布局、侧栏折叠、流式状态、反馈显隐、价格表横滑、移动端入口、中文输入法保护与异常后的新会话恢复；需要验证模型链路时再运行默认模式。

> `data/` 已在 `.gitignore` 与 `.dockerignore` 中排除，测试产生的记录不会进入仓库或镜像。
