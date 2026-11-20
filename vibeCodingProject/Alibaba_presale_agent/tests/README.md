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
.venv/bin/python tests/e2e/test_qwen4_alias.py  # qwen4 .0 别名 / 在售目录候选重核 / SG+BJ 缓存读写价与地域隔离
.venv/bin/python tests/e2e/test_param_suffix_models.py  # 参数量后缀：27b/a95b 目录优先裁决 / 详情页缓存价 / 用量拆分计价不拒答
.venv/bin/python tests/e2e/test_product_pricing.py  # 产品定价：Qoder 等非百炼模型产品不注入百炼回落证据
.venv/bin/python tests/e2e/test_price_followup_competitor.py  # 表格追问 + 竞品比价 + 单节点成本汇总（默认 SG / 明确北京仅 BJ）
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
| `test_qwen4_alias.py` | 服务 + 有效 `DASHSCOPE_*` | 向 `data/qa.db` 写 5 条回答记录 |
| `test_param_suffix_models.py` | 服务 + 有效 `DASHSCOPE_*` | 向 `data/qa.db` 写 4 条回答记录 |
| `test_product_pricing.py` | 服务 + 有效 `DASHSCOPE_*` | 向 `data/qa.db` 写入回答记录 |
| `test_price_followup_competitor.py` | 服务 + 有效 `DASHSCOPE_*` | 向 `data/qa.db` 写入 4 条回答记录；竞品比价需联网搜索 |
| `test_toolloop_fx_clarify.py` | 服务 + 有效 `DASHSCOPE_*` | 向 `data/qa.db` 写 3 条回答记录 |
| `test_pitfall_regressions.py` | 服务 + 有效 `DASHSCOPE_*` | 向 `data/qa.db` 写 4 条回答记录 |
| `test_screenshot_qa.py` | 服务 + 有效 `DASHSCOPE_*` | 向 `data/qa.db` 写 3 条回答记录（含截图） |
| `test_toolcall_probe.py` | 有效 `DASHSCOPE_*`（无需服务） | 无 |
| `test_vision_probe.py` | 有效 `DASHSCOPE_*` + `/tmp/apa_probe.png`（无需服务） | 无 |
| `judge_quality.py` | 服务 + `DASHSCOPE_*` | 每个 case 写 1 条记录；报告落 `data/reports/` |
| `ui_regression.py --mock` | 服务 + 本机 Chrome | 浏览器内模拟问答与反馈；不写数据库；截图落 `/tmp/` |
| `ui_regression.py` | 服务 + 本机 Chrome | 写 1 条回答 + 1 条点踩反馈；截图落 `/tmp/` |

联调脚本默认会真实调用 LLM 并消耗额度。本地启动服务时 `DASHSCOPE_API_KEY` 必须与 `DASHSCOPE_BASE_URL` 配对（workspace 密钥 `sk-ws-` 配专属端点，配公网默认端点会 401）；根目录 `.env` 只有带后缀的密钥变量，需显式映射一对再启动。仅改动 `static/` 时优先运行 `ui_regression.py --mock`，覆盖首屏布局、侧栏折叠、流式状态、反馈显隐、价格表横滑、移动端入口、中文输入法保护与异常后的新会话恢复；需要验证模型链路时再运行默认模式。

> `data/` 已在 `.gitignore` 与 `.dockerignore` 中排除，测试产生的记录不会进入仓库或镜像。

## 3. 线上交付只读日报（离线评审，不打线上问答）

```bash
# 手动运行：云助手只读快照 → 私有 OSS → 本地检查；最多抽审 8 条
.venv/bin/python tests/e2e/daily_audit.py --instance-id <ECS_INSTANCE_ID>

# 复用已下载快照，只做确定性检查，不产生评审模型费用
.venv/bin/python tests/e2e/daily_audit.py --skip-sync --no-judge

# daily_audit 自身的离线回归
.venv/bin/python tests/e2e/test_daily_audit.py
```

日报读取 `answers` 中上一游标后的新记录，默认限近 24 小时，排除 `judge-/replay-/diagnose-/daily-audit-` 会话。全量检查踩、价格审计、中断、内部路径、来源和耗时；按风险优先最多抽审 8 条。报告与游标分别落 `data/reports/daily-<时间戳>.md/.json` 和 `data/eval/daily_audit_state.json`，原始问答不进入 Git。

副作用与边界：

- 远端只执行容器内 `VACUUM INTO` 和 OSS 上传，**不停止/重启服务、不改配置、不新增线上问答**；OSS 会覆盖同一个 `presale-agent/eval/remote-qa.db.gz` 快照对象。
- 语义抽审调用 `DAILY_JUDGE_MODEL`（默认 `glm-5.2`、关闭思考）并消耗少量 token；深度 `eval_harness` 仍默认用 `glm-5.3`。`--no-judge` 可完全关闭。未抽审记录标 `unreviewed`，绝不算通过。
- 优化建议只含证据、候选文件、影响和回归入口，**不会自动改代码**。`needs_replay=true` 表示必须带原 history 重放后才能定界，不能用单轮回放代替。

### 每天 08:00（macOS launchd，默认不启用）

模板为 `deploy/com.alibaba.presale-agent.daily-audit.plist`。确认启用时，在项目目录执行（会把模板中的 `__PROJECT_ROOT__` 替换为当前项目路径，并写入当前用户的 LaunchAgents）：

```bash
mkdir -p "$HOME/Library/LaunchAgents"
sed -e "s|__PROJECT_ROOT__|$PWD|g" -e "s|__ECS_INSTANCE_ID__|<ECS_INSTANCE_ID>|g" \
  deploy/com.alibaba.presale-agent.daily-audit.plist \
  > "$HOME/Library/LaunchAgents/com.alibaba.presale-agent.daily-audit.plist"
launchctl bootstrap "gui/$UID" "$HOME/Library/LaunchAgents/com.alibaba.presale-agent.daily-audit.plist"
```

运行环境要求：本机 `.venv`、阿里云 CLI 与 `ecsdeploy` profile 可用，工作区 `.env` 含 OSS 与评审模型配置；实例 ID 在上方安装命令中写入用户级 plist，不进入公开仓库。时间按 Mac 系统时区；睡眠时错过的任务通常会在唤醒后补跑，关机期间不能保证 08:00 准点。日志在 `/tmp/alibaba-presale-agent-daily-audit.log`，成功后发送 macOS 通知。模板和脚本仅入库，安装前不会注册任何定时任务。
