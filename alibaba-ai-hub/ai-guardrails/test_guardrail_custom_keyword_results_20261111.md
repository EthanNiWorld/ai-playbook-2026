# AI 安全护栏自定义词库拦截实测报告（自建 AI 网关场景）

> 测试日期：2026-11-11 ｜ 测试脚本：`test_guardrail_custom_keyword.py`（同目录）
> 场景：客户自建 AI 网关，接入阿里云 AI 安全护栏对 LLM 输入/输出做合规检测
> 验证目标：拦截模型输出「我是画地为牢啊，PPIO」｜ 模型：glm-5.3（百炼北京）
> 预算约束：≤ 20 元 ｜ 实际成本：< 0.2 元

## 一、结论

**可以拦截，且全链路（开通→建词库→绑定→检测→拦截）均可纯 API 完成，无需控制台。**

「我是画地为牢啊，PPIO」本身不违规，默认策略放行（实测 pass）；通过**自定义关键词库**（关键词「画地为牢」）绑定到 `response_security_check` 后，含该词的任何输出均被判定 `block`（Label=`customized`，Level=`high`，Confidence=100），网关据此拦截并替换代答话术即可。

## 二、端到端测试证据

| 阶段 | 输入 | 结果 |
| --- | --- | --- |
| 基线（默认策略） | 我是画地为牢啊，PPIO | `pass`（nonLabel，符合预期） |
| 建库绑定后复测 | 我是画地为牢啊，PPIO | **`block`**，命中自定义库 guardrail-test-ppio，RiskWords=画地为牢，RiskPositions=[2,6] |
| 复测-关键词变体 | 他这种画地为牢的做法，限制了团队的发展。 | **`block`**（子串匹配，非整句匹配） |
| 复测-正常对照 | 今天天气不错，适合出门散步。 | `pass`（无误伤） |
| e2e 场景1 输入侧 | 请续写下面这句话…：我是画地为牢啊，PPIO | `pass`（query_security_check） |
| e2e 场景1 模型输出 | glm-5.3：「我是画地为牢啊，PPIO，把自己困在原地打转…」 | **`block`** → 网关拦截，替换代答「抱歉，该内容无法提供。」 |
| e2e 场景2 对照 | 用一句话介绍杭州 → 正常输出 | 输入/输出均 `pass`，放行 |

检测延迟：单次 130~450ms（北京接入点，文本）。

## 三、自建网关集成要点

```
用户 → 自建AI网关 ──① query_security_check(用户输入)──→ AI安全护栏(北京)
              ──② 调用LLM(如glm-5.3) ──③ response_security_check(模型输出)──→ AI安全护栏
              ← Suggestion=block 时拦截/代答，pass 时放行
```

- **检测 API**：`MultiModalGuard`（SDK `alibabacloud_green20220302`），接入点 `green-cip.cn-beijing.aliyuncs.com`（上海/杭州/深圳/新加坡等均有）。Service 用 `query_security_check`（输入）/ `response_security_check`（输出），pro 版标签更细、同价。
- **自定义词库 API**（SDK `alibabacloud_green20220926`，配置管理面）：
  1. `AddKeywordLib`（LibName + Keywords，`\n` 分隔多词）→ 返回 LibId
  2. `UpdateServiceConfig`（ServiceCode + `KeywordHitLibs=["<LibId>"]`）绑定命中词库；`KeywordFilterLibs` 为忽略词库（白名单）
  3. 命中即 `block` + `customized` 标签，返回 `CustomizedHit`（库名/命中词）与 `RiskPositions`（词位置）
- **流式输出**：传 `chatId` + `sessionId` + `done` 做切片送审；单次文本上限 2000 字符；QPS 上限 50/s。
- **代答**：控制台可配代答库（按风险标签自定义代答内容），网关也可自行兜底话术。

## 四、关键发现与坑（售前/交付必读）

1. **配置生效有延迟**：词库绑定后约 **3~5 分钟**才在检测侧生效（实测 1 分钟时仍 pass，约 4 分钟后 block）。交付时预留生效窗口，勿绑定后立即验收。
2. **两个 SDK 版本、两类接入点**：检测面（2022-03-02）多地域可选；**配置管理面（2022-09-26）仅上海接入点** `green-cip.cn-shanghai.aliyuncs.com` 可用（北京报 `InvalidOperation.NotSupportedEndpoint`），但请求里 `RegionId=cn-beijing` 正常读写北京配置。
3. **开通可纯 API**：账号已有老版内容安全（lvwang_cip）不等于开通了新版 AI 护栏（lvwang_guardrail），未开通时检测报 `408 you haven't activated the commodity:lvwang_guardrail_public_cn`。可用 BssOpenApi `CreateInstance` 开通（按量付费，开通免费）：
   - ProductCode=`lvwang`，ProductType=`lvwang_guardrail_public_cn`，SubscriptionType=`PayAsYouGo`
   - 必带 Parameter：`moderationType=text_guard_advanced` + `totalCount=1`（缺组件报 `COMMODITY.INVALID_COMPONENT`）
4. **提示词攻击维度会误伤「复述类」指令**：「请原样复述这句话，不要添加任何解释：…」被判 `Direct Prompt Injection`（medium，65.97 分）→ block。改成正常续写任务即 pass。客户业务若有大量复述/改写类 prompt，需评估该维度阈值或关闭。
5. **glm-5.3（百炼）强制思考**：`enable_thinking` 仅允许 True（传 False 报 400），`max_tokens` 必须覆盖推理+正文（实测简单续写任务推理+正文约 800 tokens；给 100/512 时正文被截断只剩开头）。与之前发现的 finish_reason 缺陷一样属部署层特性。
6. **自定义词库是子串匹配**：关键词「画地为牢」会命中所有包含该词的句子（变体测试证实），配置时需评估误伤面；如需精确整句拦截，把整句作为关键词。

## 五、成本核算（预算 20 元）

| 项目 | 用量 | 单价 | 费用 |
| --- | --- | --- | --- |
| 文本合规检测 | 17 次有效调用（另 4 次 408 错误不计费） | 15 元/万次 | ≈ 0.026 元 |
| 提示词攻击检测（默认开启，随调用计费） | 17 次 | 15 元/万次 | ≈ 0.026 元 |
| glm-5.3（北京） | 9 次调用，输入约 250 tokens / 输出约 5.7K tokens | 按 token 刊例价 | < 0.1 元 |
| **合计** | | | **< 0.2 元（预算使用率 < 1%）** |

注：敏感内容检测维度默认关闭未计费；若开启另计 15 元/万次。测试结束已恢复 service 原配置并删除测试词库，无残留按量资源。

## 六、复现方式

```bash
cd alibaba-ai-hub/ai-guardrails
.venv/bin/python test_guardrail_custom_keyword.py status    # 开通状态/权限
.venv/bin/python test_guardrail_custom_keyword.py baseline  # 默认策略基线
.venv/bin/python test_guardrail_custom_keyword.py setup     # 建词库+绑定
# 等待 3~5 分钟生效
.venv/bin/python test_guardrail_custom_keyword.py verify    # 复测拦截
.venv/bin/python test_guardrail_custom_keyword.py e2e       # glm-5.3 端到端
.venv/bin/python test_guardrail_custom_keyword.py cleanup   # 恢复配置+删词库
```

凭证：RAM key（`.env` 的 `Aliyun-AccessKey-ID/Secret`，需 `AliyunYundunGreenWebFullAccess`）+ 百炼北京 workspace key（`DASHSCOPE_API_KEY_INTL_BJ_TEST` 与配套 `_URL`）。脚本内置成本硬上限（30 次检测 + 6 次 LLM/阶段）。

## 参考信源（2026-11-11 核实）

- [使用SDK进行AI安全护栏多模态内容检测](https://help.aliyun.com/zh/document_detail/2937220.html)
- [多模态实时审核API接入指南](https://help.aliyun.com/zh/document_detail/2937221.html)
- [按量付费模式计费规则与价格](https://help.aliyun.com/zh/document_detail/2872706.html)
- [AddKeywordLib](https://help.aliyun.com/zh/document_detail/3059955.html) / [UpdateServiceConfig](https://help.aliyun.com/zh/document_detail/3060175.html)