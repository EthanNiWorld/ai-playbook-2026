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
.venv/bin/python tests/e2e/judge_quality.py    # 回答质量：代码硬指标 + 交叉厂商 LLM 评审
.venv/bin/python tests/e2e/ui_regression.py    # 前端 UI 回归（CDP 驱动真实浏览器，42 项）
```

| 脚本 | 依赖 | 副作用 |
|---|---|---|
| `test_followup.py` | 服务 + 有效 `DASHSCOPE_*` | 向 `data/qa.db` 写入回答记录 |
| `test_colloquial_model.py` | 服务 + 有效 `DASHSCOPE_*` | 向 `data/qa.db` 写入回答记录 |
| `judge_quality.py` | 服务 + `DASHSCOPE_*` | 每个 case 写 1 条记录；报告落 `data/reports/` |
| `ui_regression.py` | 服务 + 本机 Chrome | 写 1 条回答 + 1 条点踩反馈；截图落 `/tmp/` |

三者都会真实调用 LLM 并消耗额度，`ui_regression.py` 建议在改动 `static/` 后跑一次。

> `data/` 已在 `.gitignore` 与 `.dockerignore` 中排除，测试产生的记录不会进入仓库或镜像。
