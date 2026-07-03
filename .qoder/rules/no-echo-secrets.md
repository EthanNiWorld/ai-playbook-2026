# 敏感信息禁止回显明文规则

## 核心约束

**禁止在对话回复中打印 .env、配置文件、环境变量中的密钥、Token、Secret 等敏感值的明文。**

## 详细说明

1. **禁止回显明文**：在回复用户时，不得将 `.env`、`config.json`、环境变量中的实际值完整打印出来，包括但不限于：
   - API Key（如 `sk-xxx`、`ak-xxx`、`LTAI5txxx`）
   - AccessKey Secret
   - Token / Password / Secret
   - 数据库连接串

2. **允许的操作**：
   - 引用**变量名**（如 `DASHSCOPE_API_KEY_CN`、`oss_AccessKey_ID`）
   - 确认配置状态（如「已读取」「配置完整」「缺失 XX 变量」）
   - 调试时仅展示**脱敏格式**：前 6 位 + `****` + 后 3 位（如 `LTAI5t****ntC`）

3. **读取 .env 时的行为**：
   - 可以用工具读取 `.env` 来确认变量是否存在
   - 回复中只说「已确认 `OSS_BUCKET_NAME` 已配置」，不回显实际值
   - 如果需要对比或排查，用脱敏格式或只确认长度/前缀

4. **代码和文件中的处理**：
   - 代码中通过 `os.getenv()` 读取，不硬编码
   - 日志输出中使用脱敏处理
   - 此规则与 `protect-api-keys.md`（禁止提交到 Git）互补

## 脱敏格式示例

```
✅ 正确：oss_AccessKey_ID 已配置（LTAI5t****ntC）
✅ 正确：已读取 OSS_BUCKET_NAME，值为 Bucket_for_ai_project（Bucket 名非密钥，可显示）
❌ 错误：oss_AccessKey_ID=LTAI5tC48mt916eWycUZSntC
❌ 错误：密钥是 sk-ws-H.RPXHHRM.7OJG.MEYCIQD5bnCc...
```

## 背景与解决的问题

> **为什么需要这条规则**：2026-07-03 构建 CosyVoice Demo 时，在对话中直接打印了 `.env` 的完整 OSS 密钥和 DashScope API Key 明文。
> 虽然 `.env` 已在 `.gitignore` 中不会被提交，但对话记录可能被截图、转发或存档，明文密钥一旦泄露后果严重。
> **解决什么问题**：从 Agent 行为层面强制脱敏，杜绝在任何回复中暴露敏感信息的真实值。
