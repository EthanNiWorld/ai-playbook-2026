"""
DeepSeek 模型多地域调用测试脚本
==============================

限流说明
--------
- RPM: 15,000 (每分钟请求数)
- TPM: 1,200,000 (每分钟 Token 数，含输入与输出)
- 限流按主账号维度统计，超出后通常一分钟内自动恢复
- 如业务需要更高额度，可在百炼控制台 -> 限流提额 页面申请临时提升 TPM

地域路由规则
------------
- DeepSeek V4 (deepseek-v4-pro / deepseek-v4-flash)：
  → 必须调用 US 节点 (dashscope-us.aliyuncs.com)
  → 需要环境变量: DASHSCOPE_API_KEY_US

- DeepSeek V3.2 (deepseek-v3.2)：
  → 优先调用新加坡 (国际) 节点 (dashscope-intl.aliyuncs.com)
    （当前仅 Singapore 国际地域提供 deepseek-v3.2）
  → 需要环境变量: DASHSCOPE_API_KEY_INTL

前置条件
---------
1. 登录 Alibaba Cloud Model Studio 国际站控制台
2. 切换到对应地域（US 或 新加坡）
3. 在模型广场找到对应 DeepSeek 模型，点击「立即开通」完成授权
4. 创建该地域的 API Key
5. 将 API Key 配置到本地环境变量（~/.zshrc 或 ~/.bashrc）

参考文档
---------
- 百炼国际站 DeepSeek 模型授权：
  https://modelstudio.console.alibabacloud.com/ap-southeast-1?tab=doc#/doc/?type=model&url=2840915
- 限流说明：
  https://www.alibabacloud.com/help/en/model-studio/rate-limit
- DeepSeek API 文档：
  https://www.alibabacloud.com/help/en/model-studio/deepseek-api
"""

import os
from openai import OpenAI


def test_model(label, api_key_name, base_url, model_name):
    print(f"\n{'='*60}")
    print(f"测试: [{label}] {model_name}")
    print(f"{'='*60}")
    print(f"  端点: {base_url}")

    api_key = os.getenv(api_key_name)
    if not api_key:
        print(f"  [跳过] 环境变量 {api_key_name} 未设置")
        return

    client = OpenAI(api_key=api_key, base_url=base_url)

    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "system", "content": "You are a helpful assistant."},
                      {"role": "user", "content": "你是谁？请用中文回答。"}],
            stream=True,
            stream_options={"include_usage": True}
        )

        full_response = ""
        usage_info = None
        for chunk in completion:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                print(content, end='', flush=True)
                full_response += content
            if chunk.usage:
                usage_info = chunk.usage

        print()
        if usage_info:
            print(f"\n--- Token 使用 ---")
            print(f"输入 tokens: {usage_info.prompt_tokens}")
            print(f"输出 tokens: {usage_info.completion_tokens}")
            print(f"总 tokens: {usage_info.total_tokens}")
        print()

    except Exception as e:
        print(f"  [错误] {e}")


if __name__ == '__main__':
    # US 地域 - DeepSeek-V4
    test_model("US 地域", "DASHSCOPE_API_KEY_US",
               "https://dashscope-us.aliyuncs.com/compatible-mode/v1",
               "deepseek-v4-pro")
    test_model("US 地域", "DASHSCOPE_API_KEY_US",
               "https://dashscope-us.aliyuncs.com/compatible-mode/v1",
               "deepseek-v4-flash")

    # 新加坡 (INTL) 地域 - DeepSeek-V3.2
    test_model("新加坡", "DASHSCOPE_API_KEY_INTL",
               "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
               "deepseek-v3.2")
